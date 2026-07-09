"""공용 유틸 — ETL 로깅과 경로 상수."""

import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
RAW_HTML_DIR = os.path.join(RAW_DIR, "html")
OUT_DIR = os.path.join(DATA_DIR, "out")
DB_PATH = os.path.join(DATA_DIR, "radar.db")
SEED_CSV = os.path.join(HERE, "seed_companies.csv")
LOG_PATH = os.path.join(HERE, "etl_project_log.txt")


def ensure_dirs():
    for d in (DATA_DIR, RAW_DIR, RAW_HTML_DIR, OUT_DIR):
        os.makedirs(d, exist_ok=True)


def log_etl(stage, message):
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    line = "%s, [%s] %s" % (ts, stage, message)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)
