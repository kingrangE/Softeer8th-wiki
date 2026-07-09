"""캐시된 채용 공고를 읽어 DE 기술 언급을 집계하고 SQLite에 적재한다.

Transform: 기술직 필터 → 본문 정제/기술 토큰 매칭(공고당 기술 1회) → 분기 버킷.
Load: jobs / mentions / granular_mentions 세 테이블을 data/radar.db에 기록.
"""

import csv
import html
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

from de_lexicon import techs_in_text, granular_products_in_text, job_category
from radar_util import DB_PATH, RAW_DIR, SEED_CSV, ensure_dirs, log_etl

TECH_ROLE_KEYWORDS = [
    "data engineer", "analytics engineer", "data platform", "data infrastructure",
    "data infra", "dataops", "machine learning", "ml engineer", "ml platform",
    "mlops", "data scientist", "data science", "big data", "data warehouse",
    "platform engineer", "infrastructure engineer", "backend", "back-end",
    "software engineer", "devops", "site reliability", "sre", "data analyst",
    "데이터", "엔지니어", "개발",
]


def is_tech_role(title):
    t = (title or "").lower()
    return any(k in t for k in TECH_ROLE_KEYWORDS)


def clean_html(raw):
    """Greenhouse content(엔티티 이스케이프된 HTML)를 평문으로."""
    return BeautifulSoup(html.unescape(raw or ""), "html.parser").get_text(" ")


def quarter_of(iso_ts):
    """'2025-11-19T..' → '2025-Q4'. 파싱 실패 시 None."""
    if not iso_ts:
        return None
    try:
        d = datetime.fromisoformat(iso_ts)
        return "%d-Q%d" % (d.year, (d.month - 1) // 3 + 1)
    except ValueError:
        return None


def read_seed(path=SEED_CSV):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def transform():
    """캐시를 읽어 jobs / mentions / granular DataFrame 세 개로 반환."""
    log_etl("START-Transform", "직무 필터 + 기술어휘/세분제품 매칭 시작")
    job_rows, mention_rows, granular_rows = [], [], []
    for c in read_seed():
        token = c["token"]
        path = os.path.join(RAW_DIR, "%s.json" % token)
        if not os.path.exists(path):
            continue
        jobs = json.load(open(path, encoding="utf-8"))
        for j in jobs:
            title = j.get("title", "").strip()
            tech_role = is_tech_role(title)
            q = quarter_of(j.get("first_published"))
            cat = (job_category(title) or "기타 기술직") if tech_role else "비기술직"
            job_rows.append(dict(company=c["name"], country=c["country"],
                                 segment=c["segment"], token=token,
                                 job_id=j.get("id"), title=title,
                                 quarter=q, category=cat, is_tech_role=int(tech_role)))
            if not tech_role:
                continue
            text = clean_html(j.get("content"))
            meta = dict(company=c["name"], country=c["country"], segment=c["segment"],
                        token=token, quarter=q, category=cat)
            for tech in techs_in_text(text):
                mention_rows.append(dict(meta, tech=tech))
            for product in granular_products_in_text(text):
                granular_rows.append(dict(meta, product=product))

    jobs_df = pd.DataFrame(job_rows)
    mentions_df = pd.DataFrame(mention_rows)
    granular_df = pd.DataFrame(granular_rows)
    n_tech_roles = int(jobs_df["is_tech_role"].sum()) if len(jobs_df) else 0
    log_etl("END-Transform", "직무 %d건(기술직 %d건) → 기술언급 %d건 · 세분제품 %d건 추출" %
            (len(jobs_df), n_tech_roles, len(mentions_df), len(granular_df)))
    return jobs_df, mentions_df, granular_df


def load(jobs_df, mentions_df, granular_df, db=DB_PATH):
    ensure_dirs()
    log_etl("START-Load", "SQLite 적재 시작 → %s" % os.path.basename(db))
    con = sqlite3.connect(db)
    jobs_df.to_sql("jobs", con, if_exists="replace", index=False)
    mentions_df.to_sql("mentions", con, if_exists="replace", index=False)
    granular_df.to_sql("granular_mentions", con, if_exists="replace", index=False)
    con.commit()
    con.close()
    log_etl("END-Load", "적재 완료. jobs=%d, mentions=%d, granular=%d" %
            (len(jobs_df), len(mentions_df), len(granular_df)))


def crawl_summary(db=DB_PATH):
    """국가별 규모 요약(회사수·원본공고·기술직공고·기술언급·세분제품언급)."""
    con = sqlite3.connect(db)
    jobs = pd.read_sql("SELECT * FROM jobs", con)
    men = pd.read_sql("SELECT country, COUNT(*) n FROM mentions GROUP BY country", con)
    gran = pd.read_sql("SELECT country, COUNT(*) n FROM granular_mentions GROUP BY country", con)
    con.close()
    g = jobs.groupby("country")
    df = pd.DataFrame({
        "회사수": g["company"].nunique(),
        "원본공고": g.size(),
        "기술직공고": g["is_tech_role"].sum(),
        "기술언급": men.set_index("country")["n"],
        "세분제품언급": gran.set_index("country")["n"],
    }).fillna(0).astype(int)
    df.loc["합계"] = df.sum()
    return df


def run():
    jobs_df, mentions_df, granular_df = transform()
    load(jobs_df, mentions_df, granular_df)
    return jobs_df, mentions_df, granular_df


if __name__ == "__main__":
    run()
