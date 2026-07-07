"""
ats_greeting.py  —  그리팅(greetinghr) 채용 페이지 웹 스크래핑
(Greenhouse/Lever/Ashby를 안 쓰는 국내 회사를 커버하기 위함)

채용 페이지 HTML 을 받아, Next.js SSR로 __NEXT_DATA__ 안에 실려오는 
React-Query 캐시를 파싱해 공고 목록/본문을 얻음

반환 형식은 Greenhouse 어댑터와 동일 (Transform에서 일관되게 동작하도록)

요청 최소화를 위해 공고 제목이 기술직 힌트에 걸리는 것만 상세 본문을 받음.
"""

import concurrent.futures as cf
import json
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 DE-Radar/0.1 (course prototype)"}
TIMEOUT = 15
DETAIL_WORKERS = 8

# 제목만으로 기술/엔지니어링 직무를 대략 거르는 힌트(상세 요청 최소화용, 한/영)
_TECH_HINT = ("개발", "엔지니어", "데이터", "서버", "인프라", "플랫폼", "머신러닝", "소프트웨어",
              "보안", "engineer", "developer", "backend", "frontend", "fullstack", "data",
              "devops", "sre", "platform", "ml", "ai", "security", "qa", "sw", "tech")


def _nextdata(url):
    r = requests.get(url, timeout=TIMEOUT, headers=UA)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
    return json.loads(m.group(1)) if m else None


def _queries(nd):
    return (nd or {}).get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])


def _openings(nd):
    for q in _queries(nd):
        if q.get("queryKey") == ["openings"]:
            return q.get("state", {}).get("data") or []
    return []


def _detail_html(slug, opening_id):
    """상세 페이지에서 openingsInfo.detail(JD 본문 HTML)을 반환. 실패 시 ''."""
    try:
        nd = _nextdata("https://%s.career.greetinghr.com/ko/o/%s" % (slug, opening_id))
        for q in _queries(nd):
            if q.get("queryKey", [])[:2] == ["career", "getOpeningById"]:
                info = q.get("state", {}).get("data", {}).get("data", {}).get("openingsInfo", {})
                return info.get("detail", "") or ""
    except Exception:  # noqa: BLE001
        pass
    return ""


def _is_tech_title(title):
    t = (title or "").lower()
    return any(h in t for h in _TECH_HINT)


def fetch_greeting(slug):
    """그리팅 보드에서 공고 리스트를 Greenhouse 호환 형식으로 반환.
    (전체 공고는 목록에서, 본문은 기술직 제목만 상세 요청해 채운다)"""
    openings = _openings(_nextdata("https://%s.career.greetinghr.com/ko/home" % slug))
    tech_ids = [o["openingId"] for o in openings if _is_tech_title(o.get("title"))]

    details = {}
    if tech_ids:
        with cf.ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
            for oid, html in zip(tech_ids, ex.map(lambda i: _detail_html(slug, i), tech_ids)):
                details[oid] = html

    jobs = []
    for o in openings:
        oid = o["openingId"]
        jobs.append({
            "id": oid,
            "title": o.get("title", "").strip(),
            "content": details.get(oid, ""),          # 기술직만 본문 있음
            "first_published": o.get("openDate"),      # 종종 None
            "location": {"name": "KR"},
        })
    return jobs
