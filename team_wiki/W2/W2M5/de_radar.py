"""
de_radar.py  —  파이프라인 오케스트레이터 (E → T → L → Render)
전체 파이프라인을 한 번에 실행한다.

  Extract   : scrape_signals.extract()   — 채용 보드/페이지 웹 스크래핑 
  Transform : analyze.transform()        — 직무 필터 + 기술어휘 매칭
  Load      : analyze.load()             — SQLite(data/radar.db)
  Render    : render.render_all()        — view

사용법:
    python de_radar.py            # 캐시 재사용
    python de_radar.py --force    # 웹 스크래핑으로 새로 수집
"""

import sys

from scrape_signals import extract
from analyze import transform, load
from render import render_all
from radar_util import OUT_DIR, log_etl

def run(force=False):
    log_etl("START-Pipeline", "DE Tech Adoption Radar 파이프라인 시작")
    extract(force=force)                          # E
    jobs_df, mentions_df, granular_df = transform()  # T
    load(jobs_df, mentions_df, granular_df)        # L
    render_all()                                  # Render
    log_etl("END-Pipeline", "완료. PNG → %s" % OUT_DIR)
    return jobs_df, mentions_df, granular_df


if __name__ == "__main__":
    run(force="--force" in sys.argv)
