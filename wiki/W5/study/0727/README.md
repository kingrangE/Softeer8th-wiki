# 7월 27일 학습 내용 정리

1. [수업 내용 정리](#수업-내용-정리)
2. [W5M1](#w5m1)

## 수업 내용 정리

## Spark RDD

### RDD를 왜 만들었을까?
> MapReduce에서 Redundancy, 메모리 Reuse 부족 문제 극복
- RDD 지원
    1. In memory caching, Reuse
    2. 복제 대신 lineage를 이용한 fault tolerance

### Task로 쪼개진다고 했는데, 그러면 이게 뭔가 변환 이런거 작업 한 개가 1 Task가 되는건가? 아니면 데이터가 나눠진 단위(partition)이 task가 되는건가

### Executor에게 Task를 할당해주는 것은 무조건 RM
- RM이 모든 것을 관장하고 AM은 그냥 갖다 꼽기만한다. 이 구조는 불변

- 안 예뻐도 된다.
- Data Engineering적 관점에서 보고서 작성
- Context 잘 정하기
- 발표 보고서를 미리 써보고 맞춰서 힘을 줄 때를 정하고 거기 부분 개발을 잘하기


### 화요일 저녁까지 계획 작성
- waterfall 말고 좀 더 Iterative하게 하던 뭔가 나름의 방식 고안

## W5M1

### PySpark 실행용 Dockerfile/compose file

1. Dockerfile
    ```docker
    FROM python:3.11-slim-bookworm

    ARG TARGETARCH

    RUN apt-get update \
        && apt-get install --no-install-recommends -y openjdk-17-jre-headless \
        && rm -rf /var/lib/apt/lists/*

    ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-${TARGETARCH}
    ENV PYSPARK_PYTHON=python3
    ENV PYTHONUNBUFFERED=1

    WORKDIR /workspace

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    CMD ["bash"]
    ```
2. docker-compose.yaml
    ```docker
    services:
    spark:
        build:
        context: .
        working_dir: /workspace
        volumes:
            - .:/workspace
        ports:
            - "4040:4040"
        environment:
            PYSPARK_PYTHON: python3
    ```

- 참고
    1. workdir : Container 내의 작업 경로
        - 지금 Dockerfile처럼 COPY를 하는 경우 WORKDIR 설정을 안하면, Container Root 폴더로 복사된다.
            - 일반적으론 괜찮지만, Application을 만드는 경우 복잡해지면, 파일을 덮어씌우거나 Root 경로가 복잡해지는 등 문제가 생길 수 있다.

### 과제 요구 사항
- [X] 지정된 경로에서 데이터셋 읽어오기
    - [X] 사용자가 지정한 여러 형식 처리 가능
    - [X] 데이터셋 RDD에 로드
- [ ] 누락된 데이터가 있는 행 식별 후 제거
- [ ] 유효하지 않은 데이터가 있는 행 식별 후 제거
    - [ ] 요금이 0원이거나 음수인 TRIP 제외
- Transformation
    - [ ] Transformation 최소 5개 진행
    - [ ] 총 수익, 총 trip 횟수 계산
    - [ ] 날짜별 그룹화, 일별 지표 계산
    - [ ] 관련된 Column 추출을 위한 데이터 매핑
    - [ ] 추출된 Column 데이터를 적절한 데이터 타입으로 변환
- Aggregation
    - [ ] 총 이동 횟수 계산
    - [ ] 발생한 총 수익 계산
    - [ ] 평균 이동 거리 계산
    - [ ] 일일 운행 횟수 계산
    - [ ] 일일 총 수익 계산
- 성능 최적화
    - [ ] Spark 내장 함수와 기능 활용
        - [ ] Python으로 Spark Application 작성
        - [ ] Transformation & Action에 RDD API 사용
    - [ ] 작업 성능 최적화를 위한 적절한 Spark 구성 사용
- 결과 저장
    - [ ] 지정된 위치에 최종 결과 저장
        - [ ] 사용자가 이해하기 쉬운 형식으로 저장
    - [ ] 영구 저장소 지원 (HDFS, S3, 로컬 파일 시스템)
- [ ] DAG Visualization 화면 캡처 후, 첨부

### Jupyter Notebook을 활용한 기능 테스트

1. Spark Session 만들기
    ```python
    from pyspark.sql import SparkSession
    session = SparkSession.builder.appName("애플리케이션명").config("key","value").getOrCreate()
    ```

2. Data Input 여러 형식 받기
    - 아래를 이용하면 `DataFrame`으로 읽어진다.
    ```python
    # CSV 읽기
    spark.read.option("header",True).option("mode","PERMISSIVE").csv("경로")
    # parquet 읽기
    spark.read.parquet("경로")
    ```

3. 데이터셋 RDD 로드
    - 일단 데이터를 불러왔으니까, load 부분에서 최적화는 끝났다.
    - RDD로 변환하면 다양한 파싱과 같은 것이 가능해지는 장점이 있다.
        - 다만, off-heap이 안 되고, 스키마를 알 수 없다는 단점도 있음

    ```python
    # df => 아까 위에서 읽은 데이터
    rows = df.select("Column1","Column2",...).rdd
    ```
    - 위와 같이 작성하면, row 객체들의 RDD를 받게 된다.
4. RDD 파싱
    - RDD는 객체이므로, 더 쉬운 파싱을 위해 Tuple로 변환
        ```python
        tuple_row = rows.map(
            lambda x : (x[0],x[1],...) # 속성 개수만큼
        )
        ```
    - pickup : Date로 변환
        ```python
        from datetime import datetime,date
        if isinstance(pickup,datetime):
            trip_date = pickup.date() # datetime -> date로 바꿔 저장
        elif isinstance(pickup,str):
            trip_date = datetime.fromisoformat(pickup.strip()).date()
        elif isinstance(pickup,date):
            trip_date = pickup
        else :
            return None
        ```
    - fare,distance : float으로 변환
        ```python
        fare_amount = float(fare)
        trip_distance = float(distance)
        ```
5. float 무한대 및 이상치 예외처리
    - 0이거나 무한대면 None
        ```python
        import math
        if not math.isfinite(fare_amount) or not math.isfinite(trip_distance):
            return None
        if fare_amount <= 0 or trip_distance <= 0 :
            return None
        ```
    - None이 있는 행 filter 처리
        ```python
        cleaned = parsed.filter(lambda record: record is not None) 
        ```
6. 파티션 개수 맞춰주기
    - 원하는 파티션 개수가 10개라 가정
    ```python
    cur_par_cnt = cleaned.getNumPartitions()
    if cur_par_cnt < 10 :
        # 원하는 개수보다 작으면 repartition으로 늘림
        cleaned = cleaned.repartition(10)
    elif cur_par_cnt > 10 : 
        # 원하는 개수보다 많으면 coalesce로 줄임(인접 파티션 합치는 것 -> 셔플 없음)
        cleaned = cleaned.coalesce(10)
    ```

7. RDD 결과 저장 (persist, cache)
    - 결과를 저장하지 않으면, 매 action마다 lineage에 따라 연산을 진행한다.
    - 저장하는 위치를 설정하는 다양한 옵션 존재 ([공식 문서](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.StorageLevel.html))
    ```python
    # data 메모리에만 저장, cache의 default 값
    cleaned.persist(StorageLevel.MEMORY_ONLY)
    # data 메모리 우선 저장, 만약 파티션이 메모리 초과하면, local disk로 spill
    cleaned.persist(StorageLevel.MEMORY_AND_DISK)
    # 데이터를 serialized 방식으로 저장 (메모리 효율성 높지만, CPU 오버헤드 큼)
    cleaned.persist(StorageLevel.MEMORY_ONLY_SER)
    # MEMORY_ONLY_SER과 동일한데 spill 있는 버전
    cleaned.persist(StorageLevel.MEMORY_AND_DISK_SER)
    # off-heap에 저장 -> GC pause 감소
    cleaned.persist(StorageLevel.OFF_HEAP)
    ```
8. 일 단위 집계 계산
    ```python
    cleaned.map(lambda record: (record.trip_date, (1, record.fare_amount)))
        .reduceByKey(add_daily_metric, numPartitions=partitions) # 같은 값끼리 합쳐 계산
        .sortByKey(numPartitions=partitions) # 정렬
    ```
    - `lambda record: (record.trip_date, (1, record.fare_amount))`
        - PairRDD로 만들어서, ByKey 연산을 할 수 있게 하는 과정
        - 각 행의 trip_date 컬럼 값과, fare_amount 컬럼 값을 기반으로 다음과 같이 만듦
            - ex) (2025-01-01,(1,1000))
            - 1이 있는 이유는 count로 몇 행을 계산했는지 확인하기 위함
    - `.reduceByKey(add_daily_metric, numPartitions=partitions)`
        - `add_daily_metric` : reduce 함수
            ```python
            def add_daily_metric(
                left: tuple[int, float], right: tuple[int, float]
            ) -> tuple[int, float]:
                return left[0] + right[0], left[1] + right[1]
            ```
        - `numPartitions` : 파티션 개수
            - reduce는 셔플이 발생함 -> 셔플 이후, 몇 개 파티션으로 나눌지 설정
    - `.sortByKey(numPartitions=partitions)`
        - key로 정렬

9. 총 집계 계산
    ```python
    def compute_summary(cleaned: RDD) -> tuple[int, float, float]:
        metric = cleaned.map(
            lambda record: (1, record.fare_amount, record.trip_distance)
        ).aggregate((0, 0.0, 0.0), add_metric, add_metric)
        return finalize_summary(metric)
    def finalize_summary(metric: tuple[int, float, float]) -> tuple[int, float, float]:
        count, revenue, distance_sum = metric
        average_distance = distance_sum / count if count else 0.0
        return count, revenue, average_distance
    ```
    - `lambda record: (1, record.fare_amount, record.trip_distance)`
        - 각 행의 fare_amount, trip_distance 값을 갖고 aggregate 계산
    - `.aggregate((0, 0.0, 0.0), add_metric, add_metric)`
        - `aggregate`: 초기값 있고, 입력값과 누적값 타입이 다른 경우 유리, 파티션 별 계산(seq0p)과 파티션들 누적 계산(comb0p)이 다를 때 사용
            - 파티션 별 계산과 누적 계산이 다르다의 의미
                - `seq0p` : 나뉜 파티션에서 누적값을 집계하는 데 이용하는 함수
                - `comb0p` : 나뉜 파티션들을 모두 모아 집계하는데 이용하는 함수
            - 대안 : fold (but, fold는 파티션 별 계산과 누적 계산을 분리하지 못한다.)
                - 하지만, 여기선 동일하므로 `.fold((0,0.0,0.0),add_metric)`으로 해도 동일
    - `finalize_summary`: 계산 결과 기반으로 3개 튜플 반환해주는 함수

10. 결과 작성
    ```python
    def write_results(
        spark: SparkSession,
        output_path: str,
        output_format: str,
        summary: tuple[int, float, float],
        daily_metrics: RDD,
    ) -> None:
        # Output Format 제한
        if output_format not in {"csv", "parquet"}:
            raise ValueError("output_format must be one of: csv, parquet")

        # SCHEMA에 맞게 일별, 총합 DataFrame 생성
        summary_frame = spark.createDataFrame([summary], SUMMARY_SCHEMA)
        daily_rows = daily_metrics.map(
            lambda item: (item[0], item[1][0], item[1][1])
        )
        daily_frame = spark.createDataFrame(daily_rows, DAILY_SCHEMA)

        # 형식에 따라 저장
        if output_format == "csv":
            summary_frame.write.option("header", True).csv(
                f"{output_path}/summary"
            )
            daily_frame.write.option("header", True).csv(
                f"{output_path}/daily_metrics"
            )
        else:
            summary_frame.write.parquet(f"{output_path}/summary")
            daily_frame.write.parquet(f"{output_path}/daily_metrics")
    ```

11. 사용 후, persist 해제
    ```python
    daily_metrics.unpersist()
    cleaned.unpersist()
    ```

12. 사용 후, spark 종료
    ```python
    spark.stop()
    ```