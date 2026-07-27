# Spark + Docker 실습 환경 (Phase 1: 단일 컨테이너 / Phase 2: Standalone 클러스터) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 직접 작성한 Dockerfile로 PySpark 단일 컨테이너 실습 환경(Jupyter + spark-submit)을 만들고, 같은 이미지를 재사용해 Docker Compose로 Spark Standalone 클러스터(Master 1 + Worker 2)를 띄워 Driver/Executor/Cluster Manager 분리를 직접 확인한다.

**Architecture:** 하나의 Dockerfile(Java 17 + Spark 3.5.4 + Jupyter)을 기반으로, Phase 1은 이 이미지를 단일 컨테이너로 실행해 노트북/스크립트 실습을 진행하고, Phase 2는 같은 이미지를 `docker-compose.yml`에서 재사용해 `spark-class`를 포그라운드로 직접 실행하는 Master/Worker 컨테이너 3개로 확장한다.

**Tech Stack:** Docker, Spark 3.5.4 (Standalone), PySpark, JupyterLab, Python 3(stdlib만 사용하는 데이터 생성 스크립트)

이 스펙은 `docs/superpowers/specs/2026-07-27-spark-docker-practice-design.md`의 Phase 1과 Phase 2만 다룬다. Phase 3(SQL 튜닝)/Phase 4(YARN, Kubernetes)는 별도 계획 문서로 진행한다.

## Global Constraints

- 베이스 이미지: `eclipse-temurin:17-jdk-jammy` (고정 태그, Alpine 사용 안 함)
- Spark 버전: `3.5.4` (Hadoop 3 바이너리, `archive.apache.org`에서 고정 버전 다운로드, `latest` 태그 금지)
- `requirements.txt`: `jupyterlab==4.2.5`, `ipykernel==6.29.5` (고정 버전)
- 로컬 개발 이미지 태그: `spark-practice:dev` (이 태그로 태그 재사용, `latest` 금지)
- 모든 명령은 `wiki/W5/study/0727/code/` 디렉토리에서 실행한다고 가정한다
- `data/*.csv`, `*.log`, `.ipynb_checkpoints/`는 `.gitignore` 처리 — 커밋하지 않는다
- Standalone 클러스터 구성: Master 1 + Worker 2, Worker당 `SPARK_WORKER_CORES=1`, `SPARK_WORKER_MEMORY=1g`
- 호스트에 Docker Desktop(또는 호환 엔진)과 Compose v2(≥2.17, `docker compose up --wait` 지원)가 설치되어 있다고 가정한다

---

## File Structure

```
wiki/W5/study/0727/code/
├── Dockerfile                  # Task 2
├── docker-compose.yml          # Task 9
├── requirements.txt            # Task 1
├── .gitignore                  # Task 1
├── data/
│   └── generate_data.py        # Task 3
└── exercises/
    ├── 01_dataframe_basics.ipynb   # Task 4
    ├── 02_lazy_eval.ipynb          # Task 5
    ├── 03_shuffle_join.py          # Task 6
    ├── 04_cache_persist.ipynb      # Task 7
    ├── 05_spark_ui_tour.md         # Task 8
    └── 06_cluster_mode.md          # Task 11
```

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `wiki/W5/study/0727/code/.gitignore`
- Create: `wiki/W5/study/0727/code/requirements.txt`

**Interfaces:**
- Produces: `.gitignore`, `requirements.txt` (Task 2가 `requirements.txt`를 이미지 빌드에 사용)

- [ ] **Step 1: `.gitignore` 작성**

```
data/*.csv
*.log
**/.ipynb_checkpoints/
```

- [ ] **Step 2: `requirements.txt` 작성**

```
jupyterlab==4.2.5
ipykernel==6.29.5
```

- [ ] **Step 3: 확인**

Run: `cat wiki/W5/study/0727/code/.gitignore wiki/W5/study/0727/code/requirements.txt`
Expected: 위에서 작성한 두 파일 내용이 그대로 출력됨

- [ ] **Step 4: Commit**

```bash
cd wiki/W5/study/0727/code
git add .gitignore requirements.txt
git commit -m "chore: Spark+Docker 실습 프로젝트 스캐폴딩"
```

---

### Task 2: Dockerfile 작성 및 이미지 빌드 검증

**Files:**
- Create: `wiki/W5/study/0727/code/Dockerfile`

**Interfaces:**
- Consumes: `requirements.txt` (Task 1)
- Produces: 로컬 이미지 태그 `spark-practice:dev` (Task 3~10에서 재사용), 컨테이너 내 `SPARK_HOME=/opt/spark`, `spark-submit`/`pyspark`/`jupyter lab` 실행 가능

- [ ] **Step 1: `Dockerfile` 작성**

```dockerfile
FROM eclipse-temurin:17-jdk-jammy

ARG SPARK_VERSION=3.5.4
ARG HADOOP_VERSION=3
ARG PY4J_VERSION=0.10.9.7

ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${SPARK_HOME}/sbin:${PATH}"
ENV PYSPARK_PYTHON=python3
ENV PYTHONPATH="${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-${PY4J_VERSION}-src.zip"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" \
        -o /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C /opt \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" "${SPARK_HOME}" \
    && rm /tmp/spark.tgz

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /opt/spark-apps

EXPOSE 8888 4040 8080 8081 8082 7077

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=", "--ServerApp.root_dir=/opt/spark-apps"]
```

- [ ] **Step 2: 이미지 빌드**

Run:
```bash
cd wiki/W5/study/0727/code
docker build -t spark-practice:dev .
```
Expected: `Successfully tagged spark-practice:dev`로 종료 (exit code 0)

- [ ] **Step 3: Spark 설치 검증**

Run: `docker run --rm spark-practice:dev spark-submit --version`
Expected: 출력에 `version 3.5.4` 문자열 포함

- [ ] **Step 4: PySpark import 경로 검증**

Run: `docker run --rm spark-practice:dev python3 -c "import pyspark; print(pyspark.__version__)"`
Expected: `3.5.4` 출력 (실패 시 `PY4J_VERSION` ARG 값이 실제 Spark 배포판의 `python/lib/py4j-*.zip` 파일명과 일치하는지 확인)

- [ ] **Step 5: Jupyter 서버 기동 검증**

Run:
```bash
docker run -d --rm --name spark-practice-jupyter-check -p 8888:8888 spark-practice:dev
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/lab
docker stop spark-practice-jupyter-check
```
Expected: HTTP 상태 코드 `200` 출력 (토큰 없이 `/lab`에 바로 접속 가능함을 의미)

- [ ] **Step 6: Commit**

```bash
git add Dockerfile
git commit -m "feat: Spark 3.5.4 + Jupyter 단일 컨테이너 Dockerfile 추가"
```

---

### Task 3: `generate_data.py` 작성 및 데이터 생성 검증

**Files:**
- Create: `wiki/W5/study/0727/code/data/generate_data.py`

**Interfaces:**
- Consumes: `spark-practice:dev` (Task 2, 실행 환경으로 사용 — Python stdlib만 쓰므로 사실상 아무 Python3 환경에서도 동작)
- Produces: `data/users.csv`(스키마: `user_id,name,country`), `data/orders.csv`(스키마: `order_id,user_id,amount`) — 이후 모든 실습 노트북/스크립트가 이 두 파일을 `/opt/spark-data/`에서 읽는다. `--skew` 플래그는 Phase 3 계획에서 사용한다.

- [ ] **Step 1: `data/generate_data.py` 작성**

```python
import argparse
import csv
import random

COUNTRIES = ["KR", "US", "JP", "DE", "FR"]


def generate_users(path, n_users, seed, skew):
    random.seed(seed)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "name", "country"])
        for user_id in range(1, n_users + 1):
            if skew and random.random() < 0.8:
                country = COUNTRIES[0]
            else:
                country = random.choice(COUNTRIES)
            writer.writerow([user_id, f"user_{user_id}", country])


def generate_orders(path, n_orders, n_users, seed):
    random.seed(seed + 1)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "user_id", "amount"])
        for order_id in range(1, n_orders + 1):
            user_id = random.randint(1, n_users)
            amount = round(random.uniform(1.0, 500.0), 2)
            writer.writerow([order_id, user_id, amount])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=5000)
    parser.add_argument("--orders", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skew", action="store_true")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    users_path = f"{args.out_dir}/users.csv"
    orders_path = f"{args.out_dir}/orders.csv"

    generate_users(users_path, args.users, args.seed, args.skew)
    generate_orders(orders_path, args.orders, args.users, args.seed)

    print(f"wrote {args.users} users to {users_path}")
    print(f"wrote {args.orders} orders to {orders_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 기본 파라미터로 데이터 생성**

Run:
```bash
cd wiki/W5/study/0727/code
docker run --rm -v "$(pwd)/data:/opt/spark-data" spark-practice:dev \
  python3 /opt/spark-data/generate_data.py --out-dir /opt/spark-data
```
Expected:
```
wrote 5000 users to /opt/spark-data/users.csv
wrote 200000 orders to /opt/spark-data/orders.csv
```

- [ ] **Step 3: 행 개수 검증**

Run: `wc -l data/users.csv data/orders.csv`
Expected:
```
    5001 data/users.csv
  200001 data/orders.csv
```
(헤더 1줄 포함)

- [ ] **Step 4: `--skew` 옵션 동작 검증**

Run:
```bash
docker run --rm -v "$(pwd)/data:/opt/spark-data" spark-practice:dev \
  python3 /opt/spark-data/generate_data.py --skew --users 100 --orders 10 --out-dir /tmp/skew-check
docker run --rm -v "$(pwd)/data:/opt/spark-data" -v /tmp/skew-check:/tmp/skew-check spark-practice:dev \
  bash -c "cut -d, -f3 /tmp/skew-check/users.csv | tail -n +2 | sort | uniq -c | sort -rn | head -1"
```
Expected: 가장 많이 나온 country가 `KR`이고 빈도가 100개 중 대략 60개 이상 (80% 확률 스큐)

- [ ] **Step 5: Commit**

```bash
git add data/generate_data.py
git commit -m "feat: users/orders 샘플 CSV 생성 스크립트 추가"
```

---

### Task 4: `01_dataframe_basics.ipynb` 작성 및 실행 검증

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/01_dataframe_basics.ipynb`

**Interfaces:**
- Consumes: `spark-practice:dev`(Task 2), `data/users.csv`/`data/orders.csv`(Task 3)
- Produces: 실행 완료된 노트북 (셀 출력에 `collect() rows=200000`, `take(5) rows=5` 포함)

- [ ] **Step 1: `exercises/01_dataframe_basics.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 01. DataFrame 기본 조작\n",
    "\n",
    "`users.csv`/`orders.csv`를 명시적 스키마로 읽고 select/filter/show, printSchema를 실습하고 `collect()`와 `show()`/`take(n)`의 차이를 실행 시간으로 비교한다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from pyspark.sql import SparkSession\n",
    "from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType\n",
    "\n",
    "spark = SparkSession.builder.appName(\"01_dataframe_basics\").getOrCreate()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "users_schema = StructType([\n",
    "    StructField(\"user_id\", IntegerType(), False),\n",
    "    StructField(\"name\", StringType(), True),\n",
    "    StructField(\"country\", StringType(), True),\n",
    "])\n",
    "orders_schema = StructType([\n",
    "    StructField(\"order_id\", IntegerType(), False),\n",
    "    StructField(\"user_id\", IntegerType(), False),\n",
    "    StructField(\"amount\", DoubleType(), False),\n",
    "])\n",
    "\n",
    "users = spark.read.csv(\"/opt/spark-data/users.csv\", header=True, schema=users_schema)\n",
    "orders = spark.read.csv(\"/opt/spark-data/orders.csv\", header=True, schema=orders_schema)\n",
    "\n",
    "users.printSchema()\n",
    "orders.printSchema()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "users.select(\"user_id\", \"country\").filter(users.country == \"KR\").show(5)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import time\n",
    "\n",
    "start = time.time()\n",
    "all_orders = orders.collect()\n",
    "print(f\"collect() rows={len(all_orders)} elapsed={time.time() - start:.2f}s\")\n",
    "\n",
    "start = time.time()\n",
    "sample = orders.take(5)\n",
    "print(f\"take(5) rows={len(sample)} elapsed={time.time() - start:.2f}s\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "`collect()`는 모든 파티션의 데이터를 Driver JVM 힙 하나로 모은다. 지금은 20만 행이라 안전하지만, 실무 데이터(수억 행)에서는 Driver OOM으로 이어진다. `show()`/`take(n)`은 필요한 만큼만 Driver로 가져오므로 안전하다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.stop()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: 노트북 실행**

Run:
```bash
cd wiki/W5/study/0727/code
docker run --rm \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  -w /opt/spark-apps \
  spark-practice:dev \
  jupyter nbconvert --to notebook --execute --inplace 01_dataframe_basics.ipynb
```
Expected: exit code 0, 에러 없음

- [ ] **Step 3: 출력 검증**

Run:
```bash
grep -o 'collect() rows=[0-9]*' exercises/01_dataframe_basics.ipynb
grep -o 'take(5) rows=[0-9]*' exercises/01_dataframe_basics.ipynb
```
Expected:
```
collect() rows=200000
take(5) rows=5
```

- [ ] **Step 4: Commit**

```bash
git add exercises/01_dataframe_basics.ipynb
git commit -m "feat: DataFrame 기본 조작 실습 노트북 추가"
```

---

### Task 5: `02_lazy_eval.ipynb` 작성 및 실행 검증

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/02_lazy_eval.ipynb`

**Interfaces:**
- Consumes: `spark-practice:dev`, `data/orders.csv`
- Produces: 실행 완료된 노트북 (두 번의 `count=` 출력값이 동일함을 검증)

- [ ] **Step 1: `exercises/02_lazy_eval.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 02. Lazy Evaluation\n",
    "\n",
    "transformation은 호출 시점에 실행되지 않고 계획(DAG)만 쌓인다. `explain()`으로 실행 전 계획을 확인하고, action을 두 번 호출했을 때 캐시 없이는 매번 처음부터 재계산된다는 것을 확인한다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from pyspark.sql import SparkSession\n",
    "from pyspark.sql.types import StructType, StructField, IntegerType, DoubleType\n",
    "\n",
    "spark = SparkSession.builder.appName(\"02_lazy_eval\").getOrCreate()\n",
    "\n",
    "orders_schema = StructType([\n",
    "    StructField(\"order_id\", IntegerType(), False),\n",
    "    StructField(\"user_id\", IntegerType(), False),\n",
    "    StructField(\"amount\", DoubleType(), False),\n",
    "])\n",
    "orders = spark.read.csv(\"/opt/spark-data/orders.csv\", header=True, schema=orders_schema)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "chain = orders.filter(orders.amount > 100.0).select(\"user_id\", \"amount\")\n",
    "print(\"transformation 호출 직후 - 아직 아무 계산도 일어나지 않는다\")\n",
    "chain.explain()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import time\n",
    "\n",
    "start = time.time()\n",
    "first_count = chain.count()\n",
    "print(f\"count={first_count} elapsed={time.time() - start:.2f}s\")\n",
    "\n",
    "start = time.time()\n",
    "second_count = chain.count()\n",
    "print(f\"count={second_count} elapsed={time.time() - start:.2f}s\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "캐시가 없으므로 두 번째 `count()`도 첫 번째와 비슷한 시간이 걸린다 — action마다 `orders.csv`를 처음부터 다시 읽고 filter를 재계산한다는 뜻이다. 04_cache_persist.ipynb에서 `.cache()`로 이 문제를 해결한다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.stop()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: 노트북 실행**

Run:
```bash
docker run --rm \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  -w /opt/spark-apps \
  spark-practice:dev \
  jupyter nbconvert --to notebook --execute --inplace 02_lazy_eval.ipynb
```
Expected: exit code 0

- [ ] **Step 3: 두 번의 count 결과가 동일한지 검증**

Run: `grep -o 'count=[0-9]*' exercises/02_lazy_eval.ipynb | sort -u | wc -l`
Expected: `1` (두 count 값이 같으므로 중복 제거 후 1개)

- [ ] **Step 4: Commit**

```bash
git add exercises/02_lazy_eval.ipynb
git commit -m "feat: lazy evaluation 실습 노트북 추가"
```

---

### Task 6: `03_shuffle_join.py` 작성 및 spark-submit 실행 검증

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/03_shuffle_join.py`

**Interfaces:**
- Consumes: `spark-practice:dev`, `data/users.csv`/`data/orders.csv`. CLI 인자로 데이터 디렉토리 경로(`sys.argv[1]`, 기본값 `/opt/spark-data`)를 받는다.
- Produces: Task 8(UI 투어), Task 10(클러스터 제출)이 이 스크립트를 그대로 재사용한다.

- [ ] **Step 1: `exercises/03_shuffle_join.py` 작성**

```python
import sys

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType


def main():
    spark = SparkSession.builder.appName("03_shuffle_join").getOrCreate()

    users_schema = StructType([
        StructField("user_id", IntegerType(), False),
        StructField("name", StringType(), True),
        StructField("country", StringType(), True),
    ])
    orders_schema = StructType([
        StructField("order_id", IntegerType(), False),
        StructField("user_id", IntegerType(), False),
        StructField("amount", DoubleType(), False),
    ])

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/opt/spark-data"
    users = spark.read.csv(f"{data_dir}/users.csv", header=True, schema=users_schema)
    orders = spark.read.csv(f"{data_dir}/orders.csv", header=True, schema=orders_schema)

    joined = orders.join(users, on="user_id")
    by_country = (
        joined.groupBy("country")
        .sum("amount")
        .withColumnRenamed("sum(amount)", "total_amount")
    )

    by_country.explain(True)
    by_country.show()

    print(f"user rows: {users.count()}")
    print(f"order rows: {orders.count()}")

    spark.stop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 단일 컨테이너에서 spark-submit 실행**

Run:
```bash
docker run --rm \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  spark-practice:dev \
  spark-submit /opt/spark-apps/03_shuffle_join.py /opt/spark-data \
  | tee /tmp/shuffle_join_local.log
```
Expected: exit code 0

- [ ] **Step 3: 출력 검증**

Run:
```bash
grep -c "user rows: 5000" /tmp/shuffle_join_local.log
grep -c "order rows: 200000" /tmp/shuffle_join_local.log
grep -c "Exchange" /tmp/shuffle_join_local.log
```
Expected: 세 명령 모두 `1` 이상 (Exchange는 groupBy로 인한 셔플 경계가 물리 계획에 나타남을 의미)

- [ ] **Step 4: Commit**

```bash
git add exercises/03_shuffle_join.py
git commit -m "feat: join+groupBy 셔플 실습 스크립트 추가"
```

---

### Task 7: `04_cache_persist.ipynb` 작성 및 실행 검증

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/04_cache_persist.ipynb`

**Interfaces:**
- Consumes: `spark-practice:dev`, `data/orders.csv`
- Produces: 실행 완료된 노트북 (`.cache()`/`.unpersist()` 흐름, `elapsed=` 출력 2회)

- [ ] **Step 1: `exercises/04_cache_persist.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 04. Cache / Persist\n",
    "\n",
    "02_lazy_eval.ipynb에서 본 재계산 문제를 `.cache()`/`.persist()`로 해결하고, 두 번째 action이 빨라지는 것을 확인한다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from pyspark.sql import SparkSession\n",
    "from pyspark.sql.types import StructType, StructField, IntegerType, DoubleType\n",
    "\n",
    "spark = SparkSession.builder.appName(\"04_cache_persist\").getOrCreate()\n",
    "\n",
    "orders_schema = StructType([\n",
    "    StructField(\"order_id\", IntegerType(), False),\n",
    "    StructField(\"user_id\", IntegerType(), False),\n",
    "    StructField(\"amount\", DoubleType(), False),\n",
    "])\n",
    "orders = spark.read.csv(\"/opt/spark-data/orders.csv\", header=True, schema=orders_schema)\n",
    "chain = orders.filter(orders.amount > 100.0).select(\"user_id\", \"amount\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "chain.cache()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import time\n",
    "\n",
    "start = time.time()\n",
    "first_count = chain.count()\n",
    "print(f\"first count={first_count} elapsed={time.time() - start:.2f}s (캐시를 채우는 첫 실행)\")\n",
    "\n",
    "start = time.time()\n",
    "second_count = chain.count()\n",
    "print(f\"second count={second_count} elapsed={time.time() - start:.2f}s (캐시에서 바로 읽음)\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Spark UI의 Storage 탭에서 이 DataFrame이 메모리에 캐시된 것을 확인할 수 있다. 두 번째 `count()`의 elapsed 시간이 눈에 띄게 줄어든다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "chain.unpersist()\n",
    "spark.stop()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: 노트북 실행**

Run:
```bash
docker run --rm \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  -w /opt/spark-apps \
  spark-practice:dev \
  jupyter nbconvert --to notebook --execute --inplace 04_cache_persist.ipynb
```
Expected: exit code 0

- [ ] **Step 3: 출력 검증**

Run: `grep -c 'elapsed=' exercises/04_cache_persist.ipynb`
Expected: `2` 이상

- [ ] **Step 4: Commit**

```bash
git add exercises/04_cache_persist.ipynb
git commit -m "feat: cache/persist 실습 노트북 추가"
```

---

### Task 8: `05_spark_ui_tour.md` 작성

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/05_spark_ui_tour.md`

**Interfaces:**
- Consumes: `exercises/03_shuffle_join.py` (Task 6)의 실행을 안내 대상으로 참조

- [ ] **Step 1: `exercises/05_spark_ui_tour.md` 작성**

```markdown
# 05. Spark UI 투어

`03_shuffle_join.py`를 실행하는 동안 `http://localhost:4040`을 열어 아래 흐름을 직접 확인한다.

## 실행 방법

단일 컨테이너에서 4040 포트를 열어 실행한다:

\`\`\`bash
docker run --rm -p 4040:4040 \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  spark-practice:dev \
  spark-submit /opt/spark-apps/03_shuffle_join.py /opt/spark-data
\`\`\`

Job이 끝나기 전에 브라우저로 `http://localhost:4040`에 접속한다.

## Jobs 탭

- 실행된 Action(`count()`, `show()`) 하나당 Job이 하나씩 보인다.
- 0726 노트: "실행된 Action 개수 == Job 개수"를 여기서 직접 확인한다.

## Stages 탭

- 각 Job이 셔플 경계 기준으로 여러 Stage로 나뉜 것을 확인한다.
- `groupBy("country")`가 있는 Stage 앞뒤로 Stage 번호가 끊기는 것 = 셔플 경계.
- Stage를 클릭하면 Task 개수 = 그 Stage의 파티션 개수인 것을 확인한다.

## SQL 탭

- DataFrame 연산이 SQL 쿼리 플랜으로 어떻게 시각화되는지 확인한다.
- 노드를 클릭하면 `03_shuffle_join.py`에서 `explain(True)`로 봤던 것과 동일한 물리 연산자(Exchange, HashAggregate 등)가 그래프로 보인다.

## 확인 체크리스트

- [ ] Jobs 탭에 Job이 최소 2개 이상 보인다 (count 1회 + show 1회 이상)
- [ ] Stages 탭에서 셔플이 있는 Stage와 없는 Stage가 구분된다
- [ ] SQL 탭 그래프에 Exchange 노드가 존재한다
```

- [ ] **Step 2: 필수 섹션 존재 검증**

Run:
```bash
grep -c "Jobs" exercises/05_spark_ui_tour.md
grep -c "Stages" exercises/05_spark_ui_tour.md
grep -c "SQL" exercises/05_spark_ui_tour.md
```
Expected: 세 명령 모두 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add exercises/05_spark_ui_tour.md
git commit -m "docs: Spark UI 투어 가이드 추가"
```

---

### Task 9: `docker-compose.yml` 작성 및 Standalone 클러스터 기동 검증

**Files:**
- Create: `wiki/W5/study/0727/code/docker-compose.yml`

**Interfaces:**
- Consumes: `Dockerfile`(Task 2, `build: .`로 재사용), `exercises/`·`data/` 디렉토리(볼륨 마운트)
- Produces: 실행 중인 Standalone 클러스터(`spark-master`, `spark-worker-1`, `spark-worker-2`) — Task 10, 11이 이 클러스터를 사용한다

- [ ] **Step 1: `docker-compose.yml` 작성**

```yaml
services:
  spark-master:
    build: .
    hostname: spark-master
    command: ["/opt/spark/bin/spark-class", "org.apache.spark.deploy.master.Master", "--host", "spark-master", "--port", "7077", "--webui-port", "8080"]
    ports:
      - "8080:8080"
      - "7077:7077"
    volumes:
      - ./exercises:/opt/spark-apps
      - ./data:/opt/spark-data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 5s
      timeout: 3s
      retries: 20

  spark-worker-1:
    build: .
    hostname: spark-worker-1
    command: ["/opt/spark/bin/spark-class", "org.apache.spark.deploy.worker.Worker", "spark://spark-master:7077", "--webui-port", "8081"]
    environment:
      SPARK_WORKER_CORES: "1"
      SPARK_WORKER_MEMORY: "1g"
    depends_on:
      spark-master:
        condition: service_healthy
    ports:
      - "8081:8081"
    volumes:
      - ./exercises:/opt/spark-apps
      - ./data:/opt/spark-data

  spark-worker-2:
    build: .
    hostname: spark-worker-2
    command: ["/opt/spark/bin/spark-class", "org.apache.spark.deploy.worker.Worker", "spark://spark-master:7077", "--webui-port", "8082"]
    environment:
      SPARK_WORKER_CORES: "1"
      SPARK_WORKER_MEMORY: "1g"
    depends_on:
      spark-master:
        condition: service_healthy
    ports:
      - "8082:8082"
    volumes:
      - ./exercises:/opt/spark-apps
      - ./data:/opt/spark-data
```

- [ ] **Step 2: 클러스터 기동**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose up -d --wait
```
Expected: exit code 0, 세 서비스 모두 기동 (healthcheck 통과까지 대기)

- [ ] **Step 3: Worker 등록 검증**

Run: `curl -s http://localhost:8080/json/ | grep -o '"status" : "ALIVE"' | wc -l`
Expected: `2`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: Spark Standalone 클러스터(master+worker×2) docker-compose 추가"
```

(클러스터는 Task 10에서 계속 사용하므로 여기서 `docker compose down` 하지 않는다.)

---

### Task 10: 클러스터에 `03_shuffle_join.py` 제출 및 분산 실행 검증

**Files:**
- (신규 파일 없음 — Task 6/9 산출물을 조합해 실행)

**Interfaces:**
- Consumes: `docker-compose.yml`(Task 9)로 기동된 클러스터, `exercises/03_shuffle_join.py`(Task 6)

- [ ] **Step 1: client 모드로 spark-submit 제출**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose exec -T spark-master spark-submit \
  --master spark://spark-master:7077 --deploy-mode client \
  /opt/spark-apps/03_shuffle_join.py /opt/spark-data \
  | tee /tmp/shuffle_join_cluster.log
```
Expected: exit code 0

- [ ] **Step 2: 두 Executor 모두 참여했는지 검증**

Run:
```bash
grep -c "Registering block manager spark-worker-1" /tmp/shuffle_join_cluster.log
grep -c "Registering block manager spark-worker-2" /tmp/shuffle_join_cluster.log
grep -c "user rows: 5000" /tmp/shuffle_join_cluster.log
```
Expected: 세 명령 모두 `1` 이상 (두 워커 컨테이너 모두 block manager를 등록했고, Job이 정상 완료됨)

- [ ] **Step 3: 클러스터 정리**

Run: `docker compose down`
Expected: 세 컨테이너 모두 정상 종료

- [ ] **Step 4: Commit**

이 태스크는 새 파일을 만들지 않으므로 커밋할 변경 사항이 없다 — 검증만 수행하고 다음 태스크로 진행한다.

---

### Task 11: `06_cluster_mode.md` 작성

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/06_cluster_mode.md`

**Interfaces:**
- Consumes: Task 9/10에서 확인한 클러스터 동작을 설명 대상으로 참조

- [ ] **Step 1: `exercises/06_cluster_mode.md` 작성**

```markdown
# 06. 단일 컨테이너 vs 클러스터: Driver/Executor가 실제로 분리된다

## Phase 1(단일 컨테이너)에서는

`spark-submit`을 실행한 컨테이너 하나 안에서 Driver 프로세스와 (로컬 모드) Executor 스레드가 모두 동작했다. `--master local[*]` 기본값이 이걸 의미한다 — Cluster Manager도, Executor도 전부 한 JVM 프로세스 안의 논리적 개념이었다.

## Phase 2(Docker Compose 클러스터)에서는

- **Cluster Manager**: `spark-master` 컨테이너의 `Master` 프로세스. Worker 등록을 받고 자원을 배분한다.
- **Executor**: `spark-worker-1`, `spark-worker-2` 컨테이너 안에서 뜬 별도의 JVM 프로세스. 각각 독립된 컨테이너이므로 진짜 별도의 메모리 공간, 별도의 네트워크 엔드포인트를 가진다.
- **Driver**: `docker compose exec spark-master spark-submit ...`으로 실행한 `spark-submit` 프로세스 자체. Master 데몬과는 다른 별도 프로세스로, 마스터 컨테이너 안에서 동작한다 (client 모드).

## 0726 노트와 매칭

| 개념 | Phase 1 | Phase 2 |
|---|---|---|
| Driver | 컨테이너 안 `spark-submit` 프로세스 | `spark-master` 컨테이너 안 별도 프로세스 (client 모드) |
| Executor | 같은 프로세스 안 로컬 스레드 | `spark-worker-*` 컨테이너의 별도 JVM |
| Cluster Manager | 없음 (`local[*]`) | `spark-master`의 `Master` 데몬 (Standalone) |

## 확인 방법

1. `docker compose up -d --wait`로 클러스터를 띄운다.
2. `docker compose exec spark-master spark-submit --master spark://spark-master:7077 --deploy-mode client /opt/spark-apps/03_shuffle_join.py /opt/spark-data`를 실행한다.
3. 실행 로그에서 `Registering block manager spark-worker-1:...`, `Registering block manager spark-worker-2:...` 두 줄이 각각 다른 컨테이너에서 온 것을 확인한다 — Executor가 진짜 별도 프로세스라는 증거다.
4. Master UI(`http://localhost:8080`)에서 Worker 2개가 등록된 것을, 실행 중이라면 App UI(`http://localhost:4040`)의 Executors 탭에서 executor 2개를 확인한다.
```

- [ ] **Step 2: 필수 키워드 존재 검증**

Run:
```bash
grep -c "Driver" exercises/06_cluster_mode.md
grep -c "Executor" exercises/06_cluster_mode.md
grep -c "Cluster Manager" exercises/06_cluster_mode.md
```
Expected: 세 명령 모두 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add exercises/06_cluster_mode.md
git commit -m "docs: 단일 컨테이너 vs 클러스터 Driver/Executor 분리 가이드 추가"
```
