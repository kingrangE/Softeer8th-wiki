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
2. `docker compose exec -T spark-master spark-submit --master spark://spark-master:7077 --deploy-mode client /opt/spark-apps/03_shuffle_join.py /opt/spark-data 2>&1 | tee /tmp/shuffle_join_cluster.log`를 실행한다.
3. 실행 로그에서 `Registering block manager <IP>:...` 줄이 두 개(각 워커 하나씩) 나오는 것을 확인한다 — Executor가 진짜 별도 프로세스라는 증거다. 흥미로운 점: Spark는 이 등록 로그를 `spark-worker-1`처럼 Spark가 인식하는 호스트명이 아니라 **컨테이너의 실제 IP**로 남긴다. `docker compose exec -T spark-worker-1 hostname -i`, `docker compose exec -T spark-worker-2 hostname -i`로 각 컨테이너의 IP를 확인하면 로그의 어느 줄이 어느 워커인지 알 수 있다.
4. Master UI(`http://localhost:8080`)에서 Worker 2개가 등록된 것을, 실행 중이라면 App UI(`http://localhost:4040`)의 Executors 탭에서 executor 2개를 확인한다 (이쪽은 IP가 아니라 Worker ID/호스트 정보로 보기 편하게 표시된다).
