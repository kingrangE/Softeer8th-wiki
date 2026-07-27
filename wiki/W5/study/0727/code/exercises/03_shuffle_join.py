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
