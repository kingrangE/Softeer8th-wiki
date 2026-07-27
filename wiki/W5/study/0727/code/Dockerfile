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
