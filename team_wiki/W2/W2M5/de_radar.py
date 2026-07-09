"""파이프라인 오케스트레이터: Extract → Transform → Load → Render.

    python de_radar.py            # 캐시 재사용
    python de_radar.py --force    # 새로 수집
"""

import sys

from scrape_signals import extract
from analyze import transform, load
from render import render_all
from radar_util import OUT_DIR, log_etl


def run(force=False):
    log_etl("START-Pipeline", "DE Tech Adoption Radar 파이프라인 시작")
    extract(force=force)
    jobs_df, mentions_df, granular_df = transform()
    load(jobs_df, mentions_df, granular_df)
    render_all()
    log_etl("END-Pipeline", "완료. PNG → %s" % OUT_DIR)
    return jobs_df, mentions_df, granular_df


if __name__ == "__main__":
    run(force="--force" in sys.argv)
