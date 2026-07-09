"""그리팅(greetinghr) 채용 페이지 스크래핑.

Next.js SSR의 __NEXT_DATA__ 안 React-Query 캐시를 파싱해 공고 목록/본문을 얻는다.
반환 형식은 Greenhouse 어댑터와 동일하다.
"""

import concurrent.futures as cf
import json
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 DE-Radar/0.1 (course prototype)"}
TIMEOUT = 15
DETAIL_WORKERS = 8

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
    """그리팅 보드 공고를 Greenhouse 호환 형식으로 반환. 본문은 기술직 제목만 채운다."""
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
            "content": details.get(oid, ""),
            "first_published": o.get("openDate"),      # 종종 None
            "location": {"name": "KR"},
        })
    return jobs
