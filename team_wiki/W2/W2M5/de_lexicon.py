"""데이터 엔지니어링 기술어휘.

기술 화이트리스트로 노이즈를 억제하고, 동의어를 정규화하며(PySpark/Apache Spark → Spark),
채용공고 본문에서 기술 토큰을 매칭한다. 매칭은 공고 1건당 기술 1회로 집계한다.
"""

import re

TECH_ALIASES = {
    "Snowflake":   ["snowflake"],
    "Databricks":  ["databricks"],
    "BigQuery":    ["bigquery", "big query", "google bigquery"],
    "Redshift":    ["redshift", "amazon redshift"],
    "Synapse":     ["synapse", "azure synapse"],
    "ClickHouse":  ["clickhouse"],
    "DuckDB":      ["duckdb"],
    "Airflow":     ["airflow", "apache airflow"],
    "Dagster":     ["dagster"],
    "Prefect":     ["prefect"],
    "dbt":         ["dbt"],
    "Spark":       ["spark", "pyspark", "apache spark"],
    "Flink":       ["flink", "apache flink"],
    "Kafka":       ["kafka", "apache kafka"],
    "Beam":        ["apache beam"],
    "Iceberg":     ["iceberg", "apache iceberg"],
    "Hudi":        ["hudi", "apache hudi"],
    "DeltaLake":   ["delta lake", "deltalake"],
    "Fivetran":    ["fivetran"],
    "Airbyte":     ["airbyte"],
    "Trino":       ["trino", "presto"],
    "Postgres":    ["postgres", "postgresql"],
    "MySQL":       ["mysql"],
    "MongoDB":     ["mongodb", "mongo"],
    "Cassandra":   ["cassandra"],
    "Redis":       ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    "AWS":         ["aws", "amazon web services"],
    "GCP":         ["gcp", "google cloud"],
    "Azure":       ["azure"],
    "Kubernetes":  ["kubernetes", "k8s"],
    "Terraform":   ["terraform"],
    "Docker":      ["docker"],
    "Python":      ["python"],
    "Scala":       ["scala"],
    "Java":        ["java"],
    "SQL":         ["sql"],
    "Golang":      ["golang"],
    "Rust":        ["rust"],
    "PyTorch":     ["pytorch"],
    "TensorFlow":  ["tensorflow"],
    "Ray":         ["ray"],
    "MLflow":      ["mlflow"],
    "Kubeflow":    ["kubeflow"],
}

WAREHOUSE_COMPETITORS = ["Snowflake", "Databricks", "BigQuery", "Redshift", "Synapse"]

# 거의 모든 DE 공고에 등장해 차별 신호가 없는 범용 기술. 렌더 시점에만 제외한다.
COMMODITY_TECH = {
    "Python", "SQL", "Java", "Scala", "Golang", "Rust",
    "Kubernetes", "Docker", "Terraform",
    "AWS", "GCP", "Azure",
}

BOILERPLATE_STOPWORDS = {
    "data", "pipeline", "experience", "team", "engineer", "engineering",
    "work", "build", "scale", "platform", "system", "product", "company",
}


def _compile_alias_map(alias_dict):
    """{canonical: [별칭...]} → (별칭→canonical 맵, 별칭 전체를 잡는 정규식). 긴 별칭 우선."""
    alias_to_canon = {}
    for canon, aliases in alias_dict.items():
        for a in aliases:
            alias_to_canon[a.lower()] = canon
    aliases_sorted = sorted(alias_to_canon, key=len, reverse=True)
    # 영숫자 경계로 감싸 부분단어 오탐 방지(spark != sparkling).
    pattern = r"(?<![a-zA-Z0-9])(" + "|".join(re.escape(a) for a in aliases_sorted) + r")(?![a-zA-Z0-9])"
    return alias_to_canon, re.compile(pattern, re.IGNORECASE)


_ALIAS_TO_CANON, _TECH_RE = _compile_alias_map(TECH_ALIASES)


def techs_in_text(text):
    """text 안에 등장한 canonical 기술들의 집합."""
    found = set()
    for m in _TECH_RE.finditer(text or ""):
        found.add(_ALIAS_TO_CANON[m.group(1).lower()])
    return found


def all_techs():
    return list(TECH_ALIASES.keys())


# 상위 기술명("AWS","Python")보다 한 단계 구체적인 제품/서비스명.
GRANULAR_ALIASES = {
    "Tableau":       ["tableau", "tableau server", "tableau cloud", "tableau prep", "tableau desktop"],
    "Looker":        ["looker", "lookml", "google looker"],
    "Power BI":      ["power bi", "powerbi", "power bi service", "power bi premium", "power bi desktop"],
    "Qlik":          ["qlik", "qlik sense", "qliksense", "qlikview", "qlik cloud"],
    "Grafana":       ["grafana", "grafana cloud", "grafana labs"],
    "Kibana":        ["kibana", "elastic kibana"],
    "Datadog":       ["datadog"],
    "Monte Carlo":   ["monte carlo data", "montecarlo", "getmontecarlo"],
    "Atlan":         ["atlan"],
    "DataHub":       ["datahub", "acryl datahub"],
    "OpenMetadata":  ["openmetadata", "open metadata"],
    "Microsoft Purview": ["microsoft purview", "azure purview", "purview"],
    "Amazon DynamoDB":  ["amazon dynamodb", "dynamodb"],
    "Amazon Aurora":    ["amazon aurora", "aurora serverless", "aurora postgresql", "aurora mysql"],
    "Amazon RDS":       ["amazon rds", "relational database service"],
    "Amazon SageMaker": ["sagemaker", "amazon sagemaker", "sagemaker studio"],
    "Amazon Kinesis":   ["kinesis", "amazon kinesis", "kinesis data streams", "kinesis firehose"],
    "Amazon EMR":       ["amazon emr", "elastic mapreduce", "emr serverless"],
    "Amazon OpenSearch": ["amazon opensearch", "opensearch", "amazon opensearch service"],
    "Amazon DocumentDB": ["documentdb", "amazon documentdb", "docdb"],
    "Dataflow":      ["dataflow", "cloud dataflow", "google cloud dataflow"],
    "Bigtable":      ["bigtable", "cloud bigtable", "google cloud bigtable"],
    "Pub/Sub":       ["pub/sub", "pubsub", "cloud pub/sub"],
    "Vertex AI":     ["vertex ai", "google vertex ai"],
    "Snowpark":      ["snowpark", "snowpark for python"],
    "Unity Catalog": ["unity catalog", "databricks unity catalog"],
    "Confluent":     ["confluent", "confluent cloud", "confluent kafka"],
    "Fivetran":      ["fivetran"],
    "Hightouch":     ["hightouch"],
    "Spark Structured Streaming": ["spark structured streaming", "structured streaming", "spark streaming"],
    "Apache Hive":   ["apache hive", "hive", "hiveql", "hive sql"],
    "Apache Hadoop": ["hadoop", "hdfs", "mapreduce"],
}

MODERN_STACK = ["Unity Catalog", "Snowpark", "Monte Carlo", "Atlan", "Confluent",
                "Fivetran", "Hightouch", "DataHub", "OpenMetadata"]
LEGACY_STACK = ["Apache Hive", "Apache Hadoop"]

_G_ALIAS_TO_CANON, _G_RE = _compile_alias_map(GRANULAR_ALIASES)


def granular_products_in_text(text):
    """text 안에 등장한 세분 제품(canonical)들의 집합."""
    found = set()
    for m in _G_RE.finditer(text or ""):
        found.add(_G_ALIAS_TO_CANON[m.group(1).lower()])
    return found


def all_granular_products():
    return list(GRANULAR_ALIASES.keys())


# 채용 공고 제목을 직무로 분류한다. 규칙은 우선순위 순, 제목 소문자 부분일치.
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
    """제목을 직무로 분류. 매칭 없으면 None."""
    t = (title or "").lower()
    for category, keywords in JOB_CATEGORY_RULES:
        if any(k in t for k in keywords):
            return category
    return None


def all_job_categories():
    return [c for c, _ in JOB_CATEGORY_RULES] + ["기타 기술직"]


if __name__ == "__main__":
    sample = "We use PySpark and Apache Spark with Airflow, dbt, and Snowflake on k8s."
    got = techs_in_text(sample)
    assert "Spark" in got, "PySpark/Apache Spark -> Spark 정규화 실패"
    assert "Airflow" in got and "dbt" in got and "Snowflake" in got
    assert "Kubernetes" in got, "k8s -> Kubernetes 정규화 실패"
    assert "Spark" not in techs_in_text("sparkling water java_script scalable"), "부분단어 오탐"

    g = granular_products_in_text("We run Apache Hive on Hadoop, moving to Snowpark and Unity Catalog with Fivetran; BI in Power BI and Looker.")
    assert {"Apache Hive", "Apache Hadoop", "Snowpark", "Unity Catalog", "Fivetran",
            "Power BI", "Looker"} <= g, "세분 제품 매칭 실패"

    assert job_category("Senior Data Engineer") == "데이터 엔지니어링"
    assert job_category("[토스] 백엔드 개발자") == "백엔드"
    assert job_category("Machine Learning Engineer, Ranking") == "ML/AI 엔지니어링"
    assert job_category("데이터 분석가 (Growth)") == "데이터 분석/사이언스"
    assert job_category("Frontend Engineer") == "프론트엔드"
    assert job_category("Site Reliability Engineer (SRE)") == "DevOps/인프라/SRE"
    assert job_category("Android Developer") == "모바일"
    assert job_category("법무팀 담당자") is None, "비기술직은 None 이어야"
