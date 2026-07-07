"""
scrape_signals.py  —  [Extract]
seed_companies.csv 의 회사들에 대해 채용 공고를 **웹 스크래핑**으로 수집한다.

세 가지 소스 어댑터:
- greenhouse : Greenhouse 공개 **임베드 HTML 보드**를 스크래핑.
      목록  GET https://boards.greenhouse.io/embed/job_board?for={token}&page={n}
            페이지 HTML 안에 임베드된 jobPosts 블록(id·title·location·published_at·부서)
      본문  GET https://boards.greenhouse.io/embed/job_app?for={token}&token={jid}
            HTML 의 div.job__description 을 BeautifulSoup 로 파싱
  이 임베드 보드는 어느 사이트에나 삽입되도록 설계된 공개 HTML 이라 ToS-friendly 하고,
  자체 도메인으로 리다이렉트해 job-boards 루트가 막힌 회사(coinbase·figma 등)도 커버한다.
- greeting   : 그리팅(greetinghr) 채용 페이지의 SSR HTML(__NEXT_DATA__) 스크래핑(ats_greeting).
- html       : 위 플랫폼이 없는 회사의 **자체 채용 페이지**를 직접 크롤링(scrape_html).

특징:
- 멱등적: 파싱 결과를 data/raw/{token}.json, 원본 HTML 을 data/raw/html/{token}/ 에 캐시.
  둘 다 있으면 다시 받지 않는다(W1 build_w3schools_db.py 의 "없을 때만" 패턴). --force 로 강제.
- 회사 단위 실패(구조 변경/네트워크/봇차단)는 skip + 로그 → 전체 파이프라인 중단 안 함.
- 캐시가 있으면 오프라인에서도 후속 분석이 결정적으로 재현된다.

사용법:
    python scrape_signals.py            # 캐시에 없는 회사만 수집
    python scrape_signals.py --force    # 전부 새로 수집
"""

import collections
import concurrent.futures as cf
import csv
import json
import os
import sys

from bs4 import BeautifulSoup

from analyze import is_tech_role
from ats_greeting import fetch_greeting
from scrape_html import (BROWSER_UA, DETAIL_WORKERS, balanced_json, fetch_html,  # noqa: F401
                         scrape_career_page)
from radar_util import RAW_DIR, RAW_HTML_DIR, SEED_CSV, ensure_dirs, log_etl

GH_BOARD = "https://boards.greenhouse.io/embed/job_board?for={token}&page={page}"
GH_JOBAPP = "https://boards.greenhouse.io/embed/job_app?for={token}&token={jid}"
SUPPORTED_ATS = ("greenhouse", "greeting", "html")
GREENHOUSE_DETAIL_CAP = 40   # 회사당 본문 수집 상한(부하·예의; 초과분은 로그)


def read_seed(path=SEED_CSV):
    """seed_companies.csv 를 dict 리스트로 읽는다."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _job_description(html_text):
    """job_app 임베드 HTML 에서 JD 본문(div.job__description)을 추출."""
    soup = BeautifulSoup(html_text, "html.parser")
    node = soup.select_one("div.job__description") or soup.select_one("div.body")
    return str(node) if node else ""


def scrape_greenhouse(token, force=False):
    """Greenhouse 임베드 HTML 보드를 스크래핑해 공고 리스트(본문 포함)를 반환.
    목록은 임베드된 jobPosts 블록에서, 본문은 기술직 제목만 job_app 페이지에서 긁는다."""
    cache_dir = os.path.join(RAW_HTML_DIR, token)
    metas, page, total_pages = [], 1, 1
    while page <= total_pages:
        html_text = fetch_html(GH_BOARD.format(token=token, page=page),
                               os.path.join(cache_dir, "list_p%d.html" % page), force)
        blob = balanced_json(html_text, '"jobPosts":')
        if not blob or "data" not in blob:
            if page == 1:
                raise RuntimeError("임베드 보드에 jobPosts 블록 없음(빈 보드/구조 변경)")
            break
        total_pages = int(blob.get("total_pages") or page)
        metas.extend(blob["data"])
        page += 1

    tech = [j for j in metas if is_tech_role(j.get("title", ""))]
    if len(tech) > GREENHOUSE_DETAIL_CAP:
        log_etl("STATS-Extract", "%s: 기술직 %d건 중 상위 %d건만 본문 수집(부하/예의 상한)"
                % (token, len(tech), GREENHOUSE_DETAIL_CAP))
        tech = tech[:GREENHOUSE_DETAIL_CAP]

    def one(j):
        jid = j.get("id")
        try:
            html_text = fetch_html(GH_JOBAPP.format(token=token, jid=jid),
                                   os.path.join(cache_dir, "job_%s.html" % jid), force)
            return _job_description(html_text)
        except Exception:  # noqa: BLE001 - 개별 공고 실패는 빈 본문으로 관용
            return ""

    content_by_id = {}
    if tech:
        with cf.ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
            for j, body in zip(tech, ex.map(one, tech)):
                content_by_id[j.get("id")] = body

    jobs = []
    for j in metas:
        jid = j.get("id")
        jobs.append({
            "id": jid,
            "title": (j.get("title") or "").strip(),
            "content": content_by_id.get(jid, ""),        # 기술직만 본문 있음
            "first_published": j.get("published_at"),
            "location": {"name": j.get("location") or ""},
        })
    return jobs


def fetch_jobs(company, force=False):
    """seed 한 행(company dict)에 대해 ATS 별 어댑터로 공고 리스트를 받는다.
    형식은 Greenhouse 호환(title, content, first_published, location)으로 통일."""
    ats, token = company["ats"], company["token"]
    if ats == "greenhouse":
        return scrape_greenhouse(token, force=force)
    if ats == "greeting":
        return fetch_greeting(token)
    if ats == "html":
        return scrape_career_page(company["name"], company["list_url"], token, force=force)
    raise ValueError("미지원 ATS: %s" % ats)


def raw_path(token):
    return os.path.join(RAW_DIR, "%s.json" % token)


def extract(force=False):
    """seed 회사별로 채용 공고를 스크래핑·캐시한다. 성공 토큰 목록을 반환."""
    ensure_dirs()
    companies = read_seed()
    log_etl("START-Extract", "채용 공고 웹 스크래핑 시작. 대상 %d개사 (force=%s)" % (len(companies), force))

    ok_tokens, total_jobs = [], 0
    by_country_jobs = collections.Counter()   # 국가별 수집 공고 수
    by_country_cos = collections.Counter()    # 국가별 성공 회사 수
    for c in companies:
        token, ats, country = c["token"], c["ats"], c.get("country", "??")
        if ats not in SUPPORTED_ATS:
            log_etl("SKIP-Extract", "%s: ATS '%s' 미지원(%s)" % (c["name"], ats, "/".join(SUPPORTED_ATS)))
            continue

        path = raw_path(token)
        n = None
        if os.path.exists(path) and not force:
            n = len(json.load(open(path, encoding="utf-8")))
            log_etl("CACHE-Extract", "%s[%s]: 캐시 사용 (%d건)" % (c["name"], country, n))
        else:
            try:
                jobs = fetch_jobs(c, force=force)
                json.dump(jobs, open(path, "w", encoding="utf-8"), ensure_ascii=False)
                n = len(jobs)
                log_etl("OK-Extract", "%s[%s/%s]: %d건 스크래핑·캐시" % (c["name"], country, ats, n))
            except Exception as e:  # noqa: BLE001 - 회사 단위로 격리
                log_etl("FAIL-Extract", "%s[%s] (token=%s) 실패: %s" % (c["name"], country, token, e))
        if n is not None:
            ok_tokens.append(token)
            total_jobs += n
            by_country_jobs[country] += n
            by_country_cos[country] += 1

    # 국가별 크롤링 규모 요약
    breakdown = " · ".join("%s %d개사 %d건" % (ctry, by_country_cos[ctry], by_country_jobs[ctry])
                           for ctry in sorted(by_country_jobs))
    log_etl("STATS-Extract", "국가별 수집: %s" % (breakdown or "없음"))
    log_etl("END-Extract", "수집 완료. 성공 %d/%d개사, 총 %d건" %
            (len(ok_tokens), len(companies), total_jobs))
    return ok_tokens


if __name__ == "__main__":
    extract(force="--force" in sys.argv)
