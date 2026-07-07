"""
데이터 엔지니어링 기술어휘

1. 기술 화이트리스트로 노이즈 억제
2. 동의어 정규화 (ex,PySpark / Apache Spark -> Spark)
3. 채용공고 본문 텍스트에서 기술 토큰을 매칭해 카운트

설계 노트:
- 매칭은 직무 1건당 기술 1회로 집계
- 다단어구("apache spark")와 축약형("k8s") 인식
- 오탐이 큰 단어(bare, go, r)는 제외 (기술을 언급한게 아닐 수도 있어서)
"""

import re

TECH_ALIASES = {
    # --- 데이터 웨어하우스 / 경쟁 기술 ---
    "Snowflake":   ["snowflake"],
    "Databricks":  ["databricks"],
    "BigQuery":    ["bigquery", "big query", "google bigquery"],
    "Redshift":    ["redshift", "amazon redshift"],
    "Synapse":     ["synapse", "azure synapse"],
    "ClickHouse":  ["clickhouse"],
    "DuckDB":      ["duckdb"],
    # --- 오케스트레이션 / 변환 ---
    "Airflow":     ["airflow", "apache airflow"],
    "Dagster":     ["dagster"],
    "Prefect":     ["prefect"],
    "dbt":         ["dbt"],
    # --- 처리 / 스트리밍 ---
    "Spark":       ["spark", "pyspark", "apache spark"],
    "Flink":       ["flink", "apache flink"],
    "Kafka":       ["kafka", "apache kafka"],
    "Beam":        ["apache beam"],
    # --- 테이블 포맷 / 레이크 ---
    "Iceberg":     ["iceberg", "apache iceberg"],
    "Hudi":        ["hudi", "apache hudi"],
    "DeltaLake":   ["delta lake", "deltalake"],
    # --- 적재(ingestion) ---
    "Fivetran":    ["fivetran"],
    "Airbyte":     ["airbyte"],
    # --- 쿼리엔진 / DB ---
    "Trino":       ["trino", "presto"],
    "Postgres":    ["postgres", "postgresql"],
    "MySQL":       ["mysql"],
    "MongoDB":     ["mongodb", "mongo"],
    "Cassandra":   ["cassandra"],
    "Redis":       ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    # --- 클라우드 / 인프라 ---
    "AWS":         ["aws", "amazon web services"],
    "GCP":         ["gcp", "google cloud"],
    "Azure":       ["azure"],
    "Kubernetes":  ["kubernetes", "k8s"],
    "Terraform":   ["terraform"],
    "Docker":      ["docker"],
    # --- 언어 ---
    "Python":      ["python"],
    "Scala":       ["scala"],
    "Java":        ["java"],
    "SQL":         ["sql"],
    "Golang":      ["golang"],
    "Rust":        ["rust"],
    # --- ML 인프라 (인접 카테고리) ---
    "PyTorch":     ["pytorch"],
    "TensorFlow":  ["tensorflow"],
    "Ray":         ["ray"],
    "MLflow":      ["mlflow"],
    "Kubeflow":    ["kubeflow"],
}

# 데이터 웨어하우스/레이크하우스 카테고리
WAREHOUSE_COMPETITORS = ["Snowflake", "Databricks", "BigQuery", "Redshift", "Synapse"]

# 워드클라우드에서 제외할 범용 기술.
# 거의 모든 DE 공고에 등장해 차별 신호가 없고, 클라우드를 지배해 특화 도구를 가린다.
# (원본 mentions 데이터는 유지하고 '렌더 시점'에만 제외 — 필요시 이 집합만 수정)
COMMODITY_TECH = {
    "Python", "SQL", "Java", "Scala", "Golang", "Rust",   # 범용 프로그래밍 언어
    "Kubernetes", "Docker", "Terraform",                   # 범용 인프라/IaC
    "AWS", "GCP", "Azure",                                  # 범용 클라우드 플랫폼
}

# 화이트리스트 밖이라 어차피 세지 않지만, 혹시 lexicon 확장 시 걸러낼 보일러플레이트
BOILERPLATE_STOPWORDS = {
    "data", "pipeline", "experience", "team", "engineer", "engineering",
    "work", "build", "scale", "platform", "system", "product", "company",
}


def _compile_alias_map(alias_dict):
    """{canonical: [별칭...]} → (별칭->canonical 맵, 별칭 전체를 잡는 정규식). 긴 별칭 우선."""
    alias_to_canon = {}
    for canon, aliases in alias_dict.items():
        for a in aliases:
            alias_to_canon[a.lower()] = canon
    aliases_sorted = sorted(alias_to_canon, key=len, reverse=True)
    # 영숫자 경계로 감싸 부분단어 오탐 방지(spark != sparkling). 특수문자(/)는 escape로 처리.
    pattern = r"(?<![a-zA-Z0-9])(" + "|".join(re.escape(a) for a in aliases_sorted) + r")(?![a-zA-Z0-9])"
    return alias_to_canon, re.compile(pattern, re.IGNORECASE)


_ALIAS_TO_CANON, _TECH_RE = _compile_alias_map(TECH_ALIASES)


def techs_in_text(text):
    """text 안에 등장한 canonical 기술들의 집합을 반환(중복 제거 = job-level presence)."""
    found = set()
    for m in _TECH_RE.finditer(text or ""):
        found.add(_ALIAS_TO_CANON[m.group(1).lower()])
    return found


def all_techs():
    """정의된 canonical 기술 전체 목록."""
    return list(TECH_ALIASES.keys())



# ----------------------------------------------------------------------
# 세분화된 제품
# 상위 기술명("AWS","Python")보다 한 단계 구체적인 제품/서비스명.

GRANULAR_ALIASES = {
    # --- BI / 시각화 ---
    "Tableau":       ["tableau", "tableau server", "tableau cloud", "tableau prep", "tableau desktop"],
    "Looker":        ["looker", "lookml", "google looker"],
    "Power BI":      ["power bi", "powerbi", "power bi service", "power bi premium", "power bi desktop"],
    "Qlik":          ["qlik", "qlik sense", "qliksense", "qlikview", "qlik cloud"],
    "Grafana":       ["grafana", "grafana cloud", "grafana labs"],
    "Kibana":        ["kibana", "elastic kibana"],
    # --- 관측성 / 품질 / 카탈로그 ---
    "Datadog":       ["datadog"],
    "Monte Carlo":   ["monte carlo data", "montecarlo", "getmontecarlo"],
    "Atlan":         ["atlan"],
    "DataHub":       ["datahub", "acryl datahub"],
    "OpenMetadata":  ["openmetadata", "open metadata"],
    "Microsoft Purview": ["microsoft purview", "azure purview", "purview"],
    # --- AWS ---
    "Amazon DynamoDB":  ["amazon dynamodb", "dynamodb"],
    "Amazon Aurora":    ["amazon aurora", "aurora serverless", "aurora postgresql", "aurora mysql"],
    "Amazon RDS":       ["amazon rds", "relational database service"],
    "Amazon SageMaker": ["sagemaker", "amazon sagemaker", "sagemaker studio"],
    "Amazon Kinesis":   ["kinesis", "amazon kinesis", "kinesis data streams", "kinesis firehose"],
    "Amazon EMR":       ["amazon emr", "elastic mapreduce", "emr serverless"],
    "Amazon OpenSearch": ["amazon opensearch", "opensearch", "amazon opensearch service"],
    "Amazon DocumentDB": ["documentdb", "amazon documentdb", "docdb"],
    # --- GCP ---
    "Dataflow":      ["dataflow", "cloud dataflow", "google cloud dataflow"],
    "Bigtable":      ["bigtable", "cloud bigtable", "google cloud bigtable"],
    "Pub/Sub":       ["pub/sub", "pubsub", "cloud pub/sub"],
    "Vertex AI":     ["vertex ai", "google vertex ai"],
    # --- 모던 데이터 스택 (Snowflake/Databricks/ELT) ---
    "Snowpark":      ["snowpark", "snowpark for python"],
    "Unity Catalog": ["unity catalog", "databricks unity catalog"],
    "Confluent":     ["confluent", "confluent cloud", "confluent kafka"],
    "Fivetran":      ["fivetran"],
    "Hightouch":     ["hightouch"],
    "Spark Structured Streaming": ["spark structured streaming", "structured streaming", "spark streaming"],
    # --- 레거시 Hadoop 계열 ---
    "Apache Hive":   ["apache hive", "hive", "hiveql", "hive sql"],
    "Apache Hadoop": ["hadoop", "hdfs", "mapreduce"],
}

# "모던 데이터 스택" vs "레거시 Hadoop" — 스택 성숙도 KPI 정의(제품수준 스토리)
MODERN_STACK = ["Unity Catalog", "Snowpark", "Monte Carlo", "Atlan", "Confluent",
                "Fivetran", "Hightouch", "DataHub", "OpenMetadata"]
LEGACY_STACK = ["Apache Hive", "Apache Hadoop"]

_G_ALIAS_TO_CANON, _G_RE = _compile_alias_map(GRANULAR_ALIASES)


def granular_products_in_text(text):
    """text 안에 등장한 세분 제품(canonical)들의 집합(job-level presence)."""
    found = set()
    for m in _G_RE.finditer(text or ""):
        found.add(_G_ALIAS_TO_CANON[m.group(1).lower()])
    return found


def all_granular_products():
    return list(GRANULAR_ALIASES.keys())



# ----------------------------------------------------------------------
# 직무 분류
# 부트캠프 커리큘럼 기획을 위해 채용 공고 제목을 직무로 분류한다.
# "어떤 직무를 타겟으로 열까 / 그 직무에서 뭘 가르칠까"에 답하기 위한 축.
# 규칙은 우선순위 순. 제목 소문자 부분일치.
# 모호하거나 오탐이 큰 짧은 토큰은 의도적으로 배제.
JOB_CATEGORY_RULES = [
    ("데이터 엔지니어링", [
        "data engineer", "analytics engineer", "data platform", "data infrastructure",
        "data infra", "dataops", "big data", "data warehouse", "data pipeline",
        "데이터 엔지니어", "데이터엔지니어", "데이터 플랫폼", "데이터플랫폼",
        "빅데이터", "데이터 웨어하우스",
    ]),
    ("ML/AI 엔지니어링", [
        "machine learning", "ml engineer", "ml platform", "mlops", "ai engineer",
        "ai/ml", "ai 엔지니어", "deep learning", "recommendation", "nlp",
        "머신러닝", "인공지능", "딥러닝", "추천 시스템", "추천시스템",
    ]),
    ("데이터 분석/사이언스", [
        "data scientist", "data science", "data analyst", "data analytics",
        "analytics", "business analyst",
        "데이터 분석", "데이터분석", "데이터 사이언", "분석가",
    ]),
    ("백엔드", [
        "backend", "back-end", "back end", "server engineer", "server developer",
        "백엔드", "서버 개발", "서버개발", "서버 엔지니어",
    ]),
    ("프론트엔드", [
        "frontend", "front-end", "front end", "web developer", "web engineer",
        "ui engineer", "ui/ux",
        "프론트엔드", "프론트 엔드", "프론트", "웹 개발", "웹개발", "웹 프론트",
    ]),
    ("DevOps/인프라/SRE", [
        "devops", "sre", "site reliability", "infrastructure", "infra engineer",
        "platform engineer", "cloud engineer", "system engineer", "network engineer",
        "인프라", "클라우드 엔지니어", "시스템 엔지니어", "데브옵스",
    ]),
    ("모바일", [
        "android", "ios developer", "ios engineer", "mobile", "flutter",
        "react native", "안드로이드", "모바일", "앱 개발", "앱개발",
    ]),
]


def job_category(title):
    """제목을 직무로 분류. 매칭 없으면 None(호출부에서 '기타 기술직'/'비기술직' 처리)."""
    t = (title or "").lower()
    for category, keywords in JOB_CATEGORY_RULES:
        if any(k in t for k in keywords):
            return category
    return None


def all_job_categories():
    """정의된 직무 카테고리 목록 + fallback 라벨."""
    return [c for c, _ in JOB_CATEGORY_RULES] + ["기타 기술직"]


if __name__ == "__main__":
    # 간단한 자가검증: 동의어 정규화가 실제로 묶이는지
    sample = "We use PySpark and Apache Spark with Airflow, dbt, and Snowflake on k8s."
    got = techs_in_text(sample)
    print("입력:", sample)
    print("추출:", sorted(got))
    assert "Spark" in got, "PySpark/Apache Spark -> Spark 정규화 실패"
    assert "Airflow" in got and "dbt" in got and "Snowflake" in got
    assert "Kubernetes" in got, "k8s -> Kubernetes 정규화 실패"
    # 부분단어 오탐 방지: 'sparkling'은 Spark 로 잡히면 안 됨
    assert "Spark" not in techs_in_text("sparkling water java_script scalable"), "부분단어 오탐"

    # 세분 제품 티어 검증
    g = granular_products_in_text("We run Apache Hive on Hadoop, moving to Snowpark and Unity Catalog with Fivetran; BI in Power BI and Looker.")
    print("세분 추출:", sorted(g))
    assert {"Apache Hive", "Apache Hadoop", "Snowpark", "Unity Catalog", "Fivetran",
            "Power BI", "Looker"} <= g, "세분 제품 매칭 실패"
    print("세분 제품 %d종 정의됨. 자가검증 통과 ✔" % len(GRANULAR_ALIASES))

    # 직무 분류 검증
    assert job_category("Senior Data Engineer") == "데이터 엔지니어링"
    assert job_category("[토스] 백엔드 개발자") == "백엔드"
    assert job_category("Machine Learning Engineer, Ranking") == "ML/AI 엔지니어링"
    assert job_category("데이터 분석가 (Growth)") == "데이터 분석/사이언스"
    assert job_category("Frontend Engineer") == "프론트엔드"
    assert job_category("Site Reliability Engineer (SRE)") == "DevOps/인프라/SRE"
    assert job_category("Android Developer") == "모바일"
    assert job_category("법무팀 담당자") is None, "비기술직은 None 이어야"
    print("직무 %d종 분류 자가검증 통과 ✔" % len(JOB_CATEGORY_RULES))
