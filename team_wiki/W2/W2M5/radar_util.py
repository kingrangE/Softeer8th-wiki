"""
radar_util.py
=============
공용 유틸 — W1 스타일 ETL 로깅과 경로 상수.

etl_project_log.txt 포맷은 missions/W1 의 것을 그대로 따른다:
    YYYY-MM-DD-HH-MM-SS, [START-Extract] 메시지
"""

import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")          # 파싱된 공고 JSON 캐시(Transform 입력)
RAW_HTML_DIR = os.path.join(RAW_DIR, "html")     # 스크래핑 원본 HTML 캐시(회사별 하위폴더)
OUT_DIR = os.path.join(DATA_DIR, "out")          # word cloud PNG 산출
DB_PATH = os.path.join(DATA_DIR, "radar.db")
SEED_CSV = os.path.join(HERE, "seed_companies.csv")
LOG_PATH = os.path.join(HERE, "etl_project_log.txt")


def ensure_dirs():
    for d in (DATA_DIR, RAW_DIR, RAW_HTML_DIR, OUT_DIR):
        os.makedirs(d, exist_ok=True)


def log_etl(stage, message):
    """[STAGE] 메시지를 타임스탬프와 함께 etl_project_log.txt 에 append + 화면 출력."""
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    line = "%s, [%s] %s" % (ts, stage, message)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)
