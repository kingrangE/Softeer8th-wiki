# 05. Spark UI 투어

`03_shuffle_join.py`를 실행하는 동안 `http://localhost:4040`을 열어 아래 흐름을 직접 확인한다.

## 실행 방법

단일 컨테이너에서 4040 포트를 열어 실행한다:

```bash
docker run --rm -p 4040:4040 \
  -v "$(pwd)/exercises:/opt/spark-apps" \
  -v "$(pwd)/data:/opt/spark-data" \
  spark-practice:dev \
  spark-submit /opt/spark-apps/03_shuffle_join.py /opt/spark-data
```

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
