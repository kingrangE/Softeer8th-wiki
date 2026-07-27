# Spark + Docker 실습 환경 설계

날짜: 2026-07-27
작성 위치: `wiki/W5/study/0727/code/`

## 배경

Spark 내부 개념(Driver/Executor/Cluster Manager, DAG, lazy evaluation, shuffle,
Catalyst/Tungsten, RDD vs DataFrame)은 `wiki/W4/study/0726.md`에서 이미 정리했지만
실제로 Spark를 실행해본 적은 없다. Docker로 로컬 실습 환경을 구축해, 이미 아는
개념을 손으로 직접 확인하는 것이 목표다.

## 목표

1. **Phase 1**: 직접 작성한 Dockerfile로 PySpark 단일 컨테이너 환경을 만들고,
   DataFrame API와 lazy evaluation/캐싱을 실습한다.
2. **Phase 2**: 같은 이미지를 재사용해 Docker Compose로 Spark Standalone 클러스터
   (Master 1 + Worker 2)를 띄우고, Driver/Executor/Cluster Manager가 실제 별도
   프로세스(컨테이너)로 분리되는 것을 확인한다.
3. **Phase 3**: Phase 2의 클러스터를 그대로 이용해 Spark SQL 최적화(Broadcast vs
   Sort-Merge Join, AQE, 파티셔닝 전략, Catalyst 단계별 explain)를 심화 실습한다.
4. **Phase 4**: 같은 Spark 애플리케이션(`03_shuffle_join.py`)을 Standalone이 아닌
   다른 Cluster Manager(YARN, Kubernetes) 위에서 제출해보고 차이를 비교한다.

## 범위 밖

- Spark Streaming, MLlib, GraphX
- 실제 프로덕션 배포/보안 설정, 멀티 테넌시, 오토스케일링
- Hadoop/Kubernetes 클러스터 자체의 구축·운영 학습 (검증된 이미지/도구로 빠르게
  띄우고, Spark를 그 위에서 "사용"하는 데 집중 — 아래 Phase 4 참고)
- 장애/복구 시나리오 (Worker/NodeManager/Executor Pod를 강제 종료해 재시도
  동작을 보는 것) — 필요해지면 별도 스펙으로 진행

## 디렉토리 구조

```
wiki/W5/study/0727/
├── README                          # 학습 요약 (실습 후 작성)
└── code/
    ├── Dockerfile                  # Phase 1~4a 공통 Spark 이미지
    ├── docker-compose.yml          # Phase 2/3: Standalone (master + worker×2)
    ├── docker-compose-yarn.yml     # Phase 4a: Hadoop(bde2020) + 우리 Spark 이미지
    ├── kind-config.yaml            # Phase 4b: control-plane 1 + worker 2
    ├── requirements.txt
    ├── .gitignore                  # data/*.csv, spark 로그, kind 클러스터 상태 제외
    ├── data/
    │   └── generate_data.py        # users.csv, orders.csv (+ skew 옵션)
    └── exercises/
        ├── 01_dataframe_basics.ipynb
        ├── 02_lazy_eval.ipynb
        ├── 03_shuffle_join.py
        ├── 04_cache_persist.ipynb
        ├── 05_spark_ui_tour.md
        ├── 06_cluster_mode.md
        ├── 07_broadcast_vs_sortmerge.ipynb
        ├── 08_aqe_demo.ipynb
        ├── 09_partitioning_strategy.ipynb
        ├── 10_sql_catalog_explain.ipynb
        ├── 11_yarn_submit.md
        └── 12_k8s_submit.md
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
`user_id`로 두 테이블을 조인할 수 있게 설계. Phase 3(AQE 데모)에서 쓸 수 있도록
특정 `country` 값에 데이터가 쏠리는 스큐 옵션(`--skew`)도 지원한다.

### 실습 예제

- **01_dataframe_basics.ipynb**: `StructType`으로 명시적 스키마 지정 후 CSV 읽기,
  `select`/`filter`/`show`/`printSchema`. `collect()`를 큰 데이터에 걸어보고
  `show()`/`take(n)`과 비교해 왜 위험한지 체감.
- **02_lazy_eval.ipynb**: transformation 체인을 쌓아도 실행되지 않는 것 확인 →
  `.explain()`으로 실행 전 계획 확인 → action 호출 → **action을 두 번 호출**해
  매번 처음부터 재실행되는 것을 실행 시간으로 체감.
- **03_shuffle_join.py** (spark-submit 실행): `users`/`orders`를 `join` +
  `groupBy`로 집계, `df.explain(True)`로 셔플 경계 확인, Spark UI Stages 탭에서
  셔플이 새 Stage를 만드는 것 확인. Phase 2~4에서 이 스크립트를 그대로 재사용한다.
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

## Phase 2: Docker Compose 클러스터 (Standalone)

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

## Phase 3: Spark SQL / 성능 튜닝 심화

새 인프라 없이 Phase 2의 Standalone 클러스터를 그대로 재사용한다.

- **07_broadcast_vs_sortmerge.ipynb**: `users`(작은 테이블) ↔ `orders`(큰 테이블)
  join. 기본 `spark.sql.autoBroadcastJoinThreshold`로 자동 Broadcast Join 되는
  것을 `explain()`으로 확인 → threshold를 `-1`로 낮춰 강제로 Sort-Merge Join
  유도 → 두 물리 계획과 실행 시간 비교.
- **08_aqe_demo.ipynb**: `generate_data.py --skew`로 만든 스큐 데이터셋으로
  `spark.sql.adaptive.enabled` on/off 비교 → AQE가 셔플 파티션을 런타임에
  재조정하는 것을 Stages 탭에서 확인.
- **09_partitioning_strategy.ipynb**: `repartition` vs `coalesce` 차이,
  `spark.sql.shuffle.partitions` 기본값(200)이 2-executor 클러스터에서 오히려
  오버헤드가 되는 걸 확인하고 튜닝.
- **10_sql_catalog_explain.ipynb**: `createOrReplaceTempView` + `spark.sql()`로
  SQL 실행, `explain(True)` 출력을 0726 노트의 Catalyst 4단계(Unresolved→
  Analyzed→Optimized→Physical)와 한 줄씩 매칭.

### 검증 기준 (Phase 3)

- 07: Broadcast Join과 Sort-Merge Join의 `explain()` 출력이 서로 다른 물리 연산자
  (`BroadcastHashJoin` vs `SortMergeJoin`)를 보여줌
- 08: AQE on/off 시 Stages 탭의 셔플 파티션 수가 달라짐
- 10: `explain(True)` 4단계 출력에 각 단계 이름이 실제로 표시됨

## Phase 4: 다른 Cluster Manager 체험

같은 `03_shuffle_join.py`를 Standalone이 아닌 다른 Cluster Manager 위에서
제출해 차이를 비교한다. Hadoop/Kubernetes 클러스터 자체는 검증된 이미지/도구로
빠르게 띄우고, "Spark 애플리케이션을 그 위에 제출하는 워크플로"에 집중한다
(클러스터 운영 자체는 실무에서도 별도 역할/매니지드 서비스가 담당하는 영역).

### Phase 4a: YARN

- `docker-compose-yarn.yml` (Phase 2와 별도 compose 파일)에 `bde2020/hadoop`
  계열 검증된 이미지(예: `bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8` 및
  대응 datanode/resourcemanager/nodemanager 이미지 — 구현 시점에 최신 안정
  태그로 고정)로 `namenode`, `datanode`, `resourcemanager`, `nodemanager` × 2
  구성 — HDFS/YARN 부트스트랩은 이미지에 맡긴다.
- 우리가 만든 Spark 이미지(Phase 1 Dockerfile)를 "제출 클라이언트"로 재사용.
  `HADOOP_CONF_DIR`을 이 Hadoop 클러스터의 `core-site.xml`/`yarn-site.xml`이
  담긴 볼륨으로 연결.
- **11_yarn_submit.md** + `03_shuffle_join.py` 재사용:
  `spark-submit --master yarn --deploy-mode client /opt/spark-apps/03_shuffle_join.py`
  실행. ResourceManager UI(`localhost:8088`)에서 애플리케이션이 RUNNING→FINISHED
  되는 것과 NodeManager에 컨테이너(=Executor) 2개가 할당되는 것 확인.

#### 검증 기준 (Phase 4a)

- ResourceManager UI에 애플리케이션이 FINISHED 상태로 표시
- NodeManager 컨테이너 2개가 할당되어 Job이 정상 완료

### Phase 4b: Kubernetes

- `kind-config.yaml`로 로컬 k8s 클러스터 생성 (control-plane 1 + worker node 2).
  kind 노드 이미지(`kindest/node`)도 구현 시점의 kind 최신 stable release가
  명시하는 태그로 고정한다.
- Spark 배포판에 포함된 `docker-image-tool.sh`로 우리 `SPARK_HOME` 기준 k8s
  전용 이미지를 빌드 (`kubernetes/dockerfiles/spark/Dockerfile` 사용,
  `exercises/`·`data/`를 이미지에 COPY해서 `local://` 경로로 접근 가능하게),
  `kind load docker-image`로 클러스터에 로드.
- Spark 드라이버가 Executor Pod를 만들 수 있도록 ServiceAccount + RoleBinding
  생성 (Spark-on-Kubernetes 표준 RBAC 요구사항).
- **12_k8s_submit.md** + `03_shuffle_join.py` 재사용:
  `spark-submit --master k8s://<kind-api-server> --deploy-mode cluster --conf spark.executor.instances=2 ...`.
  `kubectl get pods`로 driver pod + executor pod 2개 확인, `kubectl port-forward`로
  Spark UI 접속.

#### 검증 기준 (Phase 4b)

- `kubectl get pods`에 driver 1개 + executor 2개가 Running→Completed로 표시
- 포트포워딩한 Spark UI의 Executors 탭에서 executor 2개 확인

### 사전 요구사항 (Phase 4b 전용)

Phase 1~4a는 Docker만 있으면 되지만, Phase 4b는 호스트에 `kind`, `kubectl` CLI
설치가 필요하다 (kind는 k8s 노드를 Docker 컨테이너로 띄우지만, 클러스터를
생성/조작하는 CLI 자체는 호스트에 있어야 함).

## 에러 처리 / 운영 고려사항

- 이미지 버전(Java, Spark, Hadoop 이미지, kind 노드 이미지)은 모두 고정 태그
  사용 — `latest` 드리프트로 인한 재현 불가 문제 방지
- `data/*.csv`, Spark 이벤트 로그, kind 클러스터 상태는 `.gitignore` 처리
  (재생성 가능한 산출물이라 커밋 대상 아님)
- worker/nodemanager가 master/resourcemanager보다 먼저 뜨는 race condition
  방지를 위해 compose에 재시도/healthcheck 반영
- Phase 4b에서 `spark.kubernetes.container.image`가 kind 클러스터에 로드된
  태그와 정확히 일치해야 함 (불일치 시 `ImagePullBackOff`) — 실행 스크립트에서
  태그를 한 곳에서만 관리하도록 구성

## 테스트 방법

코드 자체에 대한 unit test는 두지 않는다 (학습용 실습 스크립트). 대신 각 Phase의
"검증 기준"에 명시된 수동 확인 절차(빌드/실행/UI 확인)를 완료 기준으로 삼는다.
