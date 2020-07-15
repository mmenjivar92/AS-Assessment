from commonFunctions.helpers import create_spark_session
from pyspark.sql.functions import *
import datetime
import configparser

def main():
    """
    Steps
    Incremental Load:
    1. Read current version of dimension
    2. Get all the distinct values from the stagingProducts DataFrame
    3. Identify possible new values (left anti join with current dim)
    4. Generate Unique Identifier for new departmens
    5. Union current dimension with new values
    6. Write new version of the dimension to S3 Bucket => Presentation Layer
    """

    # Reading Config file
    config = configparser.ConfigParser()
    config.read('dl.cfg')
    s3 = config.get('HEADER', 'AWS_ACCESS_KEY_ID')

    # Getting Spark Session
    spark = create_spark_session()

    #Reading Datasets
    currentDim = spark.read.parquet(s3 + "/presentation_layer/dim_department")
    stagingProducts= spark.read.parquet(s3 + "/staging_layer/products")

    distinctDepartments = stagingProducts.select("department").distinct() \
        .withColumnRenamed("department", "department_name") \
        .withColumn("inserted_date", current_date()) \
        .select("department_name", "inserted_date")

    newDepartments=distinctDepartments.join(currentDim,distinctDepartments["department_name"]==currentDim["department_name"],"leftanti")\
        .withColumn("department_key", expr("uuid()"))\
        .select("department_key","department_name","inserted_date")

    newDim = currentDim.union(newDepartments)

    #Writting to a temp location
    newDim.write.parquet(s3 + "/presentation_layer/dim_department_tmp", mode="overwrite")

    #Writting in final location
    spark.read.parquet(s3 + "/presentation_layer/dim_department_tmp") \
        .write.parquet(s3 + "/presentation_layer/dim_department", mode="overwrite")

if __name__ == "__main__":
    main()
