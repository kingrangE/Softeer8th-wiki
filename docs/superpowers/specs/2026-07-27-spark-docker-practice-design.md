# Spark + Docker 실습 환경 설계

날짜: 2026-07-27
작성 위치: `wiki/W5/study/0727/code/`

## 배경

Spark 내부 개념(Driver/Executor/Cluster Manager, DAG, lazy evaluation, shuffle,
Catalyst/Tungsten, RDD vs DataFrame)은 `wiki/W4/study/0726.md`에서 이미 정리했지만
실제로 Spark를 실행해본 적은 없다. Docker로 로컬 실습 환경을 구축해, 이미 아는
개념을 손으로 직접 확인하는 것이 목표다.

## 목표

1. 직접 작성한 Dockerfile로 PySpark 단일 컨테이너 환경을 만들고, DataFrame API와
   lazy evaluation/캐싱을 실습한다.
2. 같은 이미지를 재사용해 Docker Compose로 Spark Standalone 클러스터
   (Master 1 + Worker 2)를 띄우고, Driver/Executor/Cluster Manager가 실제 별도
   프로세스(컨테이너)로 분리되는 것을 확인한다.

## 범위 밖

- Kubernetes/YARN 클러스터 매니저 (Standalone만 다룬다)
- Spark Streaming, MLlib, GraphX
- 실제 프로덕션 배포/보안 설정

## 디렉토리 구조

```
wiki/W5/study/0727/
├── README                          # 학습 요약 (실습 후 작성)
└── code/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── .gitignore                  # data/*.csv, spark 로그 제외
    ├── data/
    │   └── generate_data.py
    └── exercises/
        ├── 01_dataframe_basics.ipynb
        ├── 02_lazy_eval.ipynb
        ├── 03_shuffle_join.py
        ├── 04_cache_persist.ipynb
        ├── 05_spark_ui_tour.md
        └── 06_cluster_mode.md
```

## Phase 1: 단일 컨테이너

### Dockerfile

- 베이스: `eclipse-temurin:17-jdk-jammy` (Debian 기반. Alpine은 glibc 이슈로
  Spark/Java 조합에서 문제가 잦아 제외)
- Spark 3.5.4 (Hadoop 3 바이너리) 직접 다운로드/설치 — 구현 시점에 다운로드가
  깨져 있으면 최신 3.5.x patch로 대체하되 버전을 고정하고 `latest` 태그는
  사용하지 않는다
- Python3 + pip로 `pyspark`, `jupyterlab` 설치 (requirements.txt)
- `spark-submit`, `pyspark` 쉘, Jupyter가 같은 이미지 안에서 모두 동작 →
  노트북으로 탐색한 코드를 그대로 `.py`로 옮겨 spark-submit 실행 가능
- 포트: 8888(Jupyter), 4040(Spark Application UI)

### 데이터

`generate_data.py`가 파라미터로 `users.csv`(수천 행), `orders.csv`(수십만 행)를
생성한다. 파티션/Task가 여러 개로 보일 만큼 크되 노트북 환경에서 부담 없는 크기.
`user_id`로 두 테이블을 조인할 수 있게 설계.

### 실습 예제

- **01_dataframe_basics.ipynb**: `StructType`으로 명시적 스키마 지정 후 CSV 읽기,
  `select`/`filter`/`show`/`printSchema`. `collect()`를 큰 데이터에 걸어보고
  `show()`/`take(n)`과 비교해 왜 위험한지 체감.
- **02_lazy_eval.ipynb**: transformation 체인을 쌓아도 실행되지 않는 것 확인 →
  `.explain()`으로 실행 전 계획 확인 → action 호출 → **action을 두 번 호출**해
  매번 처음부터 재실행되는 것을 실행 시간으로 체감.
- **03_shuffle_join.py** (spark-submit 실행): `users`/`orders`를 `join` +
  `groupBy`로 집계, `df.explain(True)`로 셔플 경계 확인, Spark UI Stages 탭에서
  셔플이 새 Stage를 만드는 것 확인.
- **04_cache_persist.ipynb**: 02번과 같은 재실행 문제를 `.cache()`/`.persist()`로
  해결 → 두 번째 action이 빨라지는 것을 시간으로 비교, `.unpersist()`까지 확인.
- **05_spark_ui_tour.md**: 코드 없는 텍스트 가이드. Jobs/Stages/SQL 탭을 열어
  Application→Job→Stage→Task 개념을 0726 노트의 실행 모델과 1:1 매칭.

### 검증 기준 (Phase 1)

- `docker build` 성공
- 컨테이너 실행 후 `localhost:8888`에서 Jupyter 접속, 01/02/04 노트북이 에러 없이
  끝까지 실행됨
- `docker exec <container> spark-submit /opt/spark-apps/03_shuffle_join.py`가
  정상 종료하고 콘솔에 예상된 row count/집계 결과 출력
- `.explain(True)` 출력에서 셔플 경계(Exchange)가 보임

## Phase 2: Docker Compose 클러스터

같은 이미지를 재사용해 Spark Standalone 클러스터를 구성한다.

- **spark-master**: `start-master.sh` 실행. 7077(master RPC), 8080(Master Web UI)
- **spark-worker-1, spark-worker-2**: `start-worker.sh spark://spark-master:7077`로
  master에 등록. `SPARK_WORKER_CORES=1`, `SPARK_WORKER_MEMORY=1g`로 가볍게 구성
- **볼륨 공유**: `exercises/`, `data/`를 모든 컨테이너에 `/opt/spark-apps`,
  `/opt/spark-data`로 마운트
- **의존성**: `depends_on` + worker 시작 시 master 준비 확인 (재시도 로직 또는
  compose healthcheck)

### 실행 방법

```
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 --deploy-mode client \
  /opt/spark-apps/03_shuffle_join.py
```

spark-submit이 client 모드로 Driver가 되고(마스터 컨테이너 안에서 별도 프로세스로
동작), 두 worker 컨테이너가 Executor가 된다. Master UI(`localhost:8080`)에서
Worker 2개가 등록된 것을, App UI(`localhost:4040`)의 Executors 탭에서 Task가
Executor 2개로 분배되는 것을 확인한다.

### 06_cluster_mode.md

Phase 1에서는 Driver/Executor가 한 프로세스 안에서 로컬로 동작했지만, 이제는 진짜
별도 컨테이너(별도 JVM)로 분리된다는 점을 0726 노트의 Driver/Executor/Cluster
Manager 개념과 매칭해 설명하는 텍스트 가이드.

### 검증 기준 (Phase 2)

- `docker compose up` 후 Master UI(`localhost:8080`)에 Worker 2개가 "ALIVE"로 표시
- `03_shuffle_join.py`를 spark-submit으로 실행 시 App UI Executors 탭에 executor
  2개가 잡히고 Job이 정상 완료
- Stages 탭에서 Task가 두 executor에 분산 실행됨을 확인

## 에러 처리 / 운영 고려사항

- 이미지 버전(Java, Spark)은 모두 고정 태그 사용 — `latest` 드리프트로 인한
  재현 불가 문제 방지
- `data/*.csv`, Spark 이벤트 로그는 `.gitignore` 처리 (재생성 가능한 산출물이라
  커밋 대상 아님)
- worker가 master보다 먼저 뜨는 race condition 방지를 위해 compose에 재시도/
  healthcheck 반영

## 테스트 방법

코드 자체에 대한 unit test는 두지 않는다 (학습용 실습 스크립트). 대신 각 Phase의
"검증 기준"에 명시된 수동 확인 절차(빌드/실행/UI 확인)를 완료 기준으로 삼는다.
