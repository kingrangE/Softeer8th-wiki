# Spark + Docker 실습 환경 Phase 3: Spark SQL / 성능 튜닝 심화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 2에서 만든 Spark Standalone 클러스터(Master 1 + Worker 2)를 그대로 재사용해, Broadcast vs Sort-Merge Join, AQE의 셔플 파티션 재조정, repartition vs coalesce, Catalyst 4단계 explain을 노트북으로 직접 확인한다.

**Architecture:** 새 인프라 없이 기존 `docker-compose.yml`(Phase 2, 이미 커밋됨)로 클러스터를 띄우고, 각 노트북은 `SparkSession.builder.master("spark://spark-master:7077")`로 로컬 모드가 아니라 실제 클러스터에 연결한다. 노트북 실행은 `docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace`로 마스터 컨테이너 안에서 수행한다 (Phase 1+2에서 이미 검증된 `docker compose exec` 패턴 재사용).

**Tech Stack:** 기존 `spark-practice` 이미지(Java 17 + Spark 3.5.4 + JupyterLab, Dockerfile 변경 없음), 기존 `docker-compose.yml` Standalone 클러스터

이 계획은 `docs/superpowers/specs/2026-07-27-spark-docker-practice-design.md`의 Phase 3만 다룬다. Phase 1/2는 `docs/superpowers/plans/2026-07-27-spark-docker-phase1-2.md`로 이미 구현 완료되었다 (`wiki/W5/study/0727/code/`에 Dockerfile, docker-compose.yml, exercises/01~06 존재). Phase 4(YARN, Kubernetes)는 별도 계획으로 진행한다.

## Global Constraints

- 새 Dockerfile/이미지 변경 없음 — 기존 `spark-practice` 이미지와 `docker-compose.yml`(Master 1 + Worker 2, `SPARK_WORKER_CORES=1`/`SPARK_WORKER_MEMORY=1g`)을 그대로 재사용한다
- 모든 노트북은 `SparkSession.builder.master("spark://spark-master:7077")`로 실제 클러스터에 연결한다 (Phase 1/2 노트북처럼 `local[*]` 기본값에 맡기지 않는다)
- 모든 명령은 `wiki/W5/study/0727/code/` 디렉토리에서 실행한다고 가정한다
- 노트북 실행은 `docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace /opt/spark-apps/<file>.ipynb`로 수행한다
- 각 태스크는 클러스터가 떠 있는지 확인하고, 없으면 `docker compose up -d --wait`로 띄운다 (멱등적으로 재실행 가능해야 함)
- 마지막 태스크(Task 4)에서 `docker compose down`으로 클러스터를 정리한다
- `data/skewed/*.csv`도 `data/*.csv`와 마찬가지로 커밋 대상이 아니다 (Task 1에서 `.gitignore` 패턴을 `data/**/*.csv`로 확장한다)
- 실행 시간(elapsed) 비교는 참고용으로만 쓰고, 자동 검증은 구조적으로 확정 가능한 신호(explain() 출력의 연산자 이름, `getNumPartitions()`, 설정값)에만 의존한다 — Phase 1+2 최종 리뷰에서 `02_lazy_eval.ipynb`가 타이밍만으로 결론을 주장하다 실제 실행 결과와 모순됐던 문제를 반복하지 않기 위함

---

## File Structure

```
wiki/W5/study/0727/code/
├── .gitignore                              # Task 1에서 패턴 확장
├── data/
│   └── skewed/
│       ├── users.csv                       # Task 1에서 생성 (gitignored)
│       └── orders.csv                      # Task 1에서 생성 (gitignored)
└── exercises/
    ├── 07_broadcast_vs_sortmerge.ipynb      # Task 1
    ├── 08_aqe_demo.ipynb                    # Task 2
    ├── 09_partitioning_strategy.ipynb       # Task 3
    └── 10_sql_catalog_explain.ipynb         # Task 4
```

---

### Task 1: `.gitignore` 확장 + `07_broadcast_vs_sortmerge.ipynb`

**Files:**
- Modify: `wiki/W5/study/0727/code/.gitignore`
- Create: `wiki/W5/study/0727/code/exercises/07_broadcast_vs_sortmerge.ipynb`

**Interfaces:**
- Consumes: `docker-compose.yml`(Phase 2, Standalone 클러스터), `data/users.csv`/`data/orders.csv`(Phase 1, 기본 비-스큐 데이터)
- Produces: 클러스터가 이후 태스크에서도 계속 사용할 수 있도록 기동된 상태로 남는다

- [ ] **Step 1: `.gitignore` 패턴 확장**

현재 `data/*.csv`는 `data/` 바로 아래 파일만 잡고 `data/skewed/*.csv`처럼 하위 디렉토리는 안 잡는다. Task 2에서 스큐 데이터를 `data/skewed/`에 생성하므로 패턴을 확장한다.

```
data/**/*.csv
*.log
**/.ipynb_checkpoints/
```

- [ ] **Step 2: 클러스터 기동 확인**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose up -d --wait
curl -s http://localhost:8080/json/ | grep -o '"state" : "ALIVE"' | wc -l
```
Expected: `2` (Worker 2개 모두 ALIVE)

- [ ] **Step 3: `exercises/07_broadcast_vs_sortmerge.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 07. Broadcast Join vs Sort-Merge Join\n",
    "\n",
    "`users`(작은 테이블)와 `orders`(큰 테이블)를 join할 때, `spark.sql.autoBroadcastJoinThreshold` 기본값에서는 작은 테이블이 자동으로 Broadcast되어 셔플을 피한다. threshold를 낮춰 강제로 Sort-Merge Join을 유도하고 두 물리 계획을 비교한다. AQE가 런타임에 join 전략을 바꿀 수도 있으므로, 이 노트북에서는 AQE를 꺼서 threshold 설정만으로 결정되는 순수한 비교를 본다."
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
    "spark = (\n",
    "    SparkSession.builder\n",
    "    .appName(\"07_broadcast_vs_sortmerge\")\n",
    "    .master(\"spark://spark-master:7077\")\n",
    "    .config(\"spark.sql.adaptive.enabled\", \"false\")\n",
    "    .getOrCreate()\n",
    ")\n",
    "\n",
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
    "orders = spark.read.csv(\"/opt/spark-data/orders.csv\", header=True, schema=orders_schema)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(f\"autoBroadcastJoinThreshold={spark.conf.get('spark.sql.autoBroadcastJoinThreshold')}\")\n",
    "print(\"=== 기본 threshold: 자동 Broadcast Join ===\")\n",
    "joined_default = orders.join(users, on=\"user_id\")\n",
    "joined_default.explain()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.conf.set(\"spark.sql.autoBroadcastJoinThreshold\", \"-1\")\n",
    "print(\"=== threshold=-1: 강제 Sort-Merge Join ===\")\n",
    "joined_forced = orders.join(users, on=\"user_id\")\n",
    "joined_forced.explain()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "첫 번째 `explain()`은 `BroadcastHashJoin`을 물리 연산자로 선택한다 — `users.csv`가 threshold(기본 10MB)보다 훨씬 작아서 셔플 없이 모든 Executor에 복사된다. threshold를 `-1`로 낮추면 Broadcast 후보가 사라져 양쪽을 셔플 후 정렬-병합하는 `SortMergeJoin`으로 바뀐다."
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

- [ ] **Step 4: 노트북 실행**

Run:
```bash
docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace /opt/spark-apps/07_broadcast_vs_sortmerge.ipynb
```
Expected: exit code 0

- [ ] **Step 5: 출력 검증**

Run:
```bash
grep -c "BroadcastHashJoin" exercises/07_broadcast_vs_sortmerge.ipynb
grep -c "SortMergeJoin" exercises/07_broadcast_vs_sortmerge.ipynb
```
Expected: 두 명령 모두 `1` 이상 (기본 threshold에서는 Broadcast, threshold=-1에서는 Sort-Merge로 서로 다른 물리 연산자가 선택됨)

- [ ] **Step 6: Commit**

```bash
git add .gitignore exercises/07_broadcast_vs_sortmerge.ipynb
git commit -m "feat: Broadcast vs Sort-Merge Join 비교 노트북 추가"
```

(클러스터는 Task 2에서 계속 사용하므로 여기서 `docker compose down` 하지 않는다.)

---

### Task 2: 스큐 데이터 생성 + `08_aqe_demo.ipynb`

**Files:**
- Create: `wiki/W5/study/0727/code/data/skewed/users.csv` (gitignored, 커밋 안 함)
- Create: `wiki/W5/study/0727/code/data/skewed/orders.csv` (gitignored, 커밋 안 함)
- Create: `wiki/W5/study/0727/code/exercises/08_aqe_demo.ipynb`

**Interfaces:**
- Consumes: `data/generate_data.py`(Phase 1, `--skew` 플래그 지원), 기동된 클러스터(Task 1)
- Produces: 실행 완료된 노트북

- [ ] **Step 1: 클러스터 기동 확인**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose up -d --wait
curl -s http://localhost:8080/json/ | grep -o '"state" : "ALIVE"' | wc -l
```
Expected: `2`

- [ ] **Step 2: 스큐 데이터 생성**

Run:
```bash
docker run --rm -v "$(pwd)/data:/opt/spark-data" spark-practice:dev \
  bash -c "mkdir -p /opt/spark-data/skewed && python3 /opt/spark-data/generate_data.py --skew --out-dir /opt/spark-data/skewed"
wc -l data/skewed/users.csv data/skewed/orders.csv
```
Expected:
```
    5001 data/skewed/users.csv
  200001 data/skewed/orders.csv
```

- [ ] **Step 3: `exercises/08_aqe_demo.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 08. AQE(Adaptive Query Execution) 데모\n",
    "\n",
    "`--skew`로 만든, 특정 country에 데이터가 쏠린 데이터셋으로 join+groupBy를 실행한다. AQE를 끄고 켠 두 explain() 출력을 비교해 AQE가 물리 계획에 `AdaptiveSparkPlan`이라는 별도 래퍼를 추가해 런타임에 셔플 파티션을 재조정할 수 있게 하는 것을 확인한다."
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
    "spark = (\n",
    "    SparkSession.builder\n",
    "    .appName(\"08_aqe_demo\")\n",
    "    .master(\"spark://spark-master:7077\")\n",
    "    .config(\"spark.sql.shuffle.partitions\", \"200\")\n",
    "    .getOrCreate()\n",
    ")\n",
    "\n",
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
    "users = spark.read.csv(\"/opt/spark-data/skewed/users.csv\", header=True, schema=users_schema)\n",
    "orders = spark.read.csv(\"/opt/spark-data/skewed/orders.csv\", header=True, schema=orders_schema)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.conf.set(\"spark.sql.adaptive.enabled\", \"false\")\n",
    "print(\"=== AQE off ===\")\n",
    "agg_off = orders.join(users, on=\"user_id\").groupBy(\"country\").sum(\"amount\")\n",
    "agg_off.explain()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.conf.set(\"spark.sql.adaptive.enabled\", \"true\")\n",
    "print(\"=== AQE on ===\")\n",
    "agg_on = orders.join(users, on=\"user_id\").groupBy(\"country\").sum(\"amount\")\n",
    "agg_on.explain()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "AQE off일 때는 물리 계획이 셔플/집계 연산자로 바로 시작하지만, AQE on일 때는 `AdaptiveSparkPlan`이 전체를 감싼다. 이 래퍼가 있어야 Spark가 실행 중 수집한 실제 셔플 write 통계를 보고 파티션 수를 줄이거나(coalesce) 스큐 파티션을 쪼개는 등 런타임 재조정을 할 수 있다. `agg_on`을 실제로 실행하는 동안 `http://localhost:4040`의 Stages 탭을 보면 스큐된 country로 인해 파티션 크기가 고르지 않다가 AQE가 재조정하는 것을 직접 볼 수 있다."
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

- [ ] **Step 4: 노트북 실행**

Run:
```bash
docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace /opt/spark-apps/08_aqe_demo.ipynb
```
Expected: exit code 0

- [ ] **Step 5: 출력 검증**

Run: `grep -c "AdaptiveSparkPlan" exercises/08_aqe_demo.ipynb`
Expected: `1` 이상 (AQE on의 explain() 출력에만 나타나고, AQE off의 explain() 출력에는 나타나지 않는다 — 두 물리 계획이 구조적으로 다르다는 증거)

- [ ] **Step 6: Commit**

```bash
git add exercises/08_aqe_demo.ipynb
git status --short data/skewed/  # data/skewed/*.csv가 untracked로만 보이고 staged 안 됐는지 확인
git commit -m "feat: AQE 셔플 파티션 재조정 데모 노트북 추가"
```

(클러스터는 Task 3에서 계속 사용하므로 여기서 `docker compose down` 하지 않는다.)

---

### Task 3: `09_partitioning_strategy.ipynb`

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/09_partitioning_strategy.ipynb`

**Interfaces:**
- Consumes: 기동된 클러스터(Task 1/2), `data/users.csv`/`data/orders.csv`(Phase 1, 기본 비-스큐 데이터 — 이 노트북은 스큐가 아니라 파티셔닝 자체를 다루므로 기본 데이터를 쓴다)

- [ ] **Step 1: 클러스터 기동 확인**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose up -d --wait
curl -s http://localhost:8080/json/ | grep -o '"state" : "ALIVE"' | wc -l
```
Expected: `2`

- [ ] **Step 2: `exercises/09_partitioning_strategy.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 09. Partitioning 전략: repartition vs coalesce\n",
    "\n",
    "`repartition()`은 항상 셔플을 일으켜 파티션을 재분배하고, `coalesce()`는 파티션 수를 줄일 때 셔플 없이 인접 파티션을 합친다. `spark.sql.shuffle.partitions` 기본값(200)이 2-executor 클러스터에서 오히려 과도한 분할이 되는 것도 함께 확인한다. AQE의 자동 파티션 재조정과 섞이지 않도록 이 노트북에서는 AQE를 끈다."
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
    "spark = (\n",
    "    SparkSession.builder\n",
    "    .appName(\"09_partitioning_strategy\")\n",
    "    .master(\"spark://spark-master:7077\")\n",
    "    .config(\"spark.sql.adaptive.enabled\", \"false\")\n",
    "    .config(\"spark.sql.shuffle.partitions\", \"200\")\n",
    "    .getOrCreate()\n",
    ")\n",
    "\n",
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
    "agg = orders.join(users, on=\"user_id\").groupBy(\"country\").sum(\"amount\")\n",
    "print(f\"default shuffle.partitions={spark.conf.get('spark.sql.shuffle.partitions')}\")\n",
    "print(f\"agg partitions={agg.rdd.getNumPartitions()}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"=== repartition(2): 셔플 발생 ===\")\n",
    "agg.repartition(2).explain()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"=== coalesce(2): 셔플 없이 파티션만 병합 ===\")\n",
    "agg.coalesce(2).explain()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "`repartition(2)`의 물리 계획에는 `RoundRobinPartitioning`을 사용하는 새 `Exchange` 노드가 추가된다 — 파티션을 줄이는데도 데이터를 다시 셔플한다는 뜻이다. `coalesce(2)`의 물리 계획에는 그런 노드가 없다 — 기존 파티션들을 셔플 없이 그대로 합치기만 한다 (narrow dependency). 데이터를 늘리는 방향으로는 `coalesce`를 쓸 수 없다 — 병합만 가능하다."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "spark.conf.set(\"spark.sql.shuffle.partitions\", \"4\")\n",
    "agg_tuned = orders.join(users, on=\"user_id\").groupBy(\"country\").sum(\"amount\")\n",
    "print(f\"tuned shuffle.partitions={spark.conf.get('spark.sql.shuffle.partitions')}\")\n",
    "print(f\"tuned agg partitions={agg_tuned.rdd.getNumPartitions()}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "이 클러스터는 Worker 2개, Worker당 코어 1개라 동시에 처리 가능한 Task는 최대 2개다. `shuffle.partitions` 기본값 200은 이 클러스터엔 과도하다 — 대부분의 파티션이 거의 비어서 스케줄링 오버헤드만 늘어난다. `4`처럼 클러스터 코어 수에 맞춘 값이 더 적절하다. (실행 시간 차이는 시스템 상황에 따라 들쭉날쭉할 수 있어 참고용일 뿐이고, 확실한 증거는 `getNumPartitions()`로 확인한 파티션 수 자체다.)"
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

- [ ] **Step 3: 노트북 실행**

Run:
```bash
docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace /opt/spark-apps/09_partitioning_strategy.ipynb
```
Expected: exit code 0

- [ ] **Step 4: 출력 검증**

Run:
```bash
grep -c "agg partitions=200" exercises/09_partitioning_strategy.ipynb
grep -c "RoundRobinPartitioning" exercises/09_partitioning_strategy.ipynb
grep -c "tuned agg partitions=4" exercises/09_partitioning_strategy.ipynb
```
Expected: 세 명령 모두 `1` 이상 (기본 200 파티션 확인, repartition만 RoundRobinPartitioning 셔플 노드를 만듦, 튜닝 후 4 파티션으로 줄어듦)

- [ ] **Step 5: Commit**

```bash
git add exercises/09_partitioning_strategy.ipynb
git commit -m "feat: repartition/coalesce 및 shuffle.partitions 튜닝 노트북 추가"
```

(클러스터는 Task 4에서 계속 사용하므로 여기서 `docker compose down` 하지 않는다.)

---

### Task 4: `10_sql_catalog_explain.ipynb`

**Files:**
- Create: `wiki/W5/study/0727/code/exercises/10_sql_catalog_explain.ipynb`

**Interfaces:**
- Consumes: 기동된 클러스터(Task 1/2/3), `data/users.csv`/`data/orders.csv`(Phase 1)

- [ ] **Step 1: 클러스터 기동 확인**

Run:
```bash
cd wiki/W5/study/0727/code
docker compose up -d --wait
curl -s http://localhost:8080/json/ | grep -o '"state" : "ALIVE"' | wc -l
```
Expected: `2`

- [ ] **Step 2: `exercises/10_sql_catalog_explain.ipynb` 작성**

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 10. Spark SQL과 Catalyst 4단계\n",
    "\n",
    "`createOrReplaceTempView`로 임시 뷰를 만들고 `spark.sql()`로 SQL을 실행한 뒤, `explain(True)` 출력을 0726 노트에서 정리한 Catalyst 4단계(Unresolved/Parsed → Analyzed → Optimized → Physical)와 한 줄씩 매칭한다."
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
    "spark = (\n",
    "    SparkSession.builder\n",
    "    .appName(\"10_sql_catalog_explain\")\n",
    "    .master(\"spark://spark-master:7077\")\n",
    "    .getOrCreate()\n",
    ")\n",
    "\n",
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
    "users.createOrReplaceTempView(\"users_view\")\n",
    "orders.createOrReplaceTempView(\"orders_view\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "result = spark.sql(\"\"\"\n",
    "    SELECT u.country, SUM(o.amount) AS total_amount\n",
    "    FROM orders_view o\n",
    "    JOIN users_view u ON o.user_id = u.user_id\n",
    "    GROUP BY u.country\n",
    "\"\"\")\n",
    "result.explain(True)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "`explain(True)`는 4개 섹션을 순서대로 출력한다.\n",
    "\n",
    "1. `Parsed Logical Plan` — SQL 문자열을 뼈대 트리로만 변환. Column/Table이 실존하는지는 아직 확인 안 함 (0726 노트의 Unresolved Logical Plan).\n",
    "2. `Analyzed Logical Plan` — Catalog와 대조해 Column/Table 존재 여부와 타입을 확정.\n",
    "3. `Optimized Logical Plan` — Predicate/Projection Pushdown, Constant Folding 같은 규칙 기반 재작성 적용.\n",
    "4. `Physical Plan` — Broadcast/Sort-Merge Join 선택 등 비용 기반으로 실행 전략을 확정."
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

- [ ] **Step 3: 노트북 실행**

Run:
```bash
docker compose exec -T spark-master jupyter nbconvert --to notebook --execute --inplace /opt/spark-apps/10_sql_catalog_explain.ipynb
```
Expected: exit code 0

- [ ] **Step 4: 출력 검증**

Run:
```bash
grep -c "Parsed Logical Plan" exercises/10_sql_catalog_explain.ipynb
grep -c "Analyzed Logical Plan" exercises/10_sql_catalog_explain.ipynb
grep -c "Optimized Logical Plan" exercises/10_sql_catalog_explain.ipynb
grep -c "Physical Plan" exercises/10_sql_catalog_explain.ipynb
```
Expected: 네 명령 모두 `1` 이상 (explain(True)의 4단계 헤더가 모두 실제로 출력됨)

- [ ] **Step 5: 클러스터 정리**

Run: `docker compose down`
Expected: 세 컨테이너 모두 정상 종료

- [ ] **Step 6: Commit**

```bash
git add exercises/10_sql_catalog_explain.ipynb
git commit -m "feat: Spark SQL Catalyst 4단계 explain 노트북 추가"
```
