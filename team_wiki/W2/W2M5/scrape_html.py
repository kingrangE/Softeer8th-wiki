"""
scrape_html.py  —  개별 채용 페이지 웹 스크래핑 
플랫폼 어댑터(Greenhouse 임베드 보드 / 그리팅)가 커버하지 못하는 회사의
자체 채용 페이지를 requests + BeautifulSoup 로 직접 크롤링
"""

import concurrent.futures as cf
import json
import os
import random
import re
import time

import requests

from radar_util import RAW_HTML_DIR, log_etl

BROWSER_UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/124.0.0.0 Safari/537.36")}
TIMEOUT = 20
SLEEP = 0.4            
DETAIL_WORKERS = 3    
FALLBACK_CAP = 30     

RETRYABLE = {403, 429, 500, 502, 503, 504}
BACKOFF_BASE = 3.0

_LD_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_ASHBY_POST_RE = re.compile(r'\{"id":"([0-9a-f-]{36})","title":"((?:[^"\\]|\\.)*)"')


# ---------------------------------------------------------------- 공용 유틸
def fetch_html(url, cache_path=None, force=False, retries=4):
    """URL 을 GET 해 HTML 텍스트 반환. cache_path 있으면 멱등 캐시(있으면 재사용).
    403/429/5xx 는 지수 백오프로 재시도(Greenhouse 임베드의 짧은 rate-limit 회복).
    최종 실패는 예외를 올린다."""
    if cache_path and os.path.exists(cache_path) and not force:
        with open(cache_path, encoding="utf-8") as f:
            return f.read()
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=BROWSER_UA, allow_redirects=True)
            if r.status_code in RETRYABLE:
                r.raise_for_status()
            r.raise_for_status()
            text = r.text
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(text)
            time.sleep(SLEEP + random.uniform(0, 0.3))
            return text
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            if attempt < retries:
                time.sleep(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1.0))
    raise last


def balanced_json(text, marker):
    """text 에서 marker(예: '"jobPosts":') 뒤의 균형 잡힌 {..} 객체를 dict 로 파싱.
    문자열/이스케이프를 존중하는 중괄호 카운터. 못 찾거나 깨지면 None."""
    i = text.find(marker)
    if i < 0:
        return None
    i = text.find("{", i)
    if i < 0:
        return None
    depth = 0
    in_str = esc = False
    for k in range(i, len(text)):
        ch = text[k]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:k + 1])
                except json.JSONDecodeError:
                    return None
    return None


def jsonld_jobposting(html_text):
    """페이지의 JSON-LD 블록들 중 @type=JobPosting 인 첫 dict 반환(없으면 None)."""
    for m in _LD_RE.finditer(html_text):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if isinstance(obj, dict) and obj.get("@type") == "JobPosting":
                return obj
    return None


def _ld_location(ld):
    """JobPosting.jobLocation → 간단한 지역 문자열(없으면 '')."""
    loc = ld.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    addr = (loc or {}).get("address", {}) if isinstance(loc, dict) else {}
    return addr.get("addressCountry") or addr.get("addressLocality") or ""


def _looks_tech(title):
    """폴백용 경량 기술직 판별(analyze.is_tech_role 지연 import)."""
    from analyze import is_tech_role
    return is_tech_role(title)


# ------------------ Ashby 어댑터
def _scrape_ashby(name, url, token, force):
    """Ashby 보드 → 기술직 posting 별 JSON-LD JobPosting 을 긁어 job dict 리스트로."""
    cache_dir = os.path.join(RAW_HTML_DIR, token)
    board = fetch_html(url, os.path.join(cache_dir, "board.html"), force)

    posts = []
    for pid, raw_title in _ASHBY_POST_RE.findall(board):
        try:
            title = json.loads('"%s"' % raw_title)   # JSON 이스케이프 해제
        except json.JSONDecodeError:
            title = raw_title
        posts.append((pid, title))

    tech = [(pid, t) for pid, t in posts if _looks_tech(t)]
    capped = tech[:FALLBACK_CAP]
    if len(tech) > FALLBACK_CAP:
        log_etl("STATS-Extract", "%s[html]: 기술직 %d건 중 상위 %d건만 상세 수집(폴백 상한)"
                % (name, len(tech), FALLBACK_CAP))
    base = url.rstrip("/")

    def one(pt):
        pid, title = pt
        try:
            ph = fetch_html("%s/%s" % (base, pid),
                            os.path.join(cache_dir, "p_%s.html" % pid), force)
            ld = jsonld_jobposting(ph)
            if not ld:
                return None
            return {"id": pid,
                    "title": ld.get("title", title) or title,
                    "content": ld.get("description", "") or "",
                    "first_published": ld.get("datePosted"),
                    "location": {"name": _ld_location(ld)}}
        except requests.RequestException:
            return None

    with cf.ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
        jobs = [j for j in ex.map(one, capped) if j]
    if not jobs:
        raise RuntimeError("Ashby 보드에서 기술직 공고 본문을 못 얻음")
    return jobs


# --------------- 진입점
def scrape_career_page(name, url, token, force=False):
    """자체 채용 페이지에서 Greenhouse 호환 job dict 리스트를 반환.
    실패(JS-SPA/봇차단/구조 불명)는 예외를 올려 상위에서 회사 단위 skip"""
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)

    # Ashby 보드
    if "ashbyhq.com" in host:
        return _scrape_ashby(name, url, token, force)

    # 일반 사이트: 페이지 자체에 JSON-LD JobPosting 이 있으면 사용(단일 공고 페이지 등)
    cache_dir = os.path.join(RAW_HTML_DIR, token)
    html_text = fetch_html(url, os.path.join(cache_dir, "page.html"), force)
    ld = jsonld_jobposting(html_text)
    if ld:
        return [{"id": token,
                 "title": ld.get("title", "") or "",
                 "content": ld.get("description", "") or "",
                 "first_published": ld.get("datePosted"),
                 "location": {"name": _ld_location(ld)}}]

    raise RuntimeError("스크래핑 가능한 공고 구조를 못 찾음(JS-SPA/봇차단 가능성)")
