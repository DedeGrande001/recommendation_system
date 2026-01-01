"""
Spark job for data cleaning and processing
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, trim, lower, regexp_replace, count
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType
import os
import sys


class DataCleaner:
    def __init__(self, app_name="RecommendationDataCleaner"):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

    def read_csv(self, file_path, header=True, infer_schema=True):
        """Read CSV file into Spark DataFrame"""
        try:
            df = self.spark.read.csv(
                file_path,
                header=header,
                inferSchema=infer_schema
            )
            print(f"✓ Successfully loaded: {file_path}")
            print(f"  Rows: {df.count()}, Columns: {len(df.columns)}")
            return df
        except Exception as e:
            print(f"✗ Error reading file: {e}")
            return None

    def clean_data(self, df):
        """
        Clean and transform the data
        Customize this method based on your dataset structure
        """
        print("\n--- Data Cleaning Started ---")

        # 1. Remove duplicates
        initial_count = df.count()
        df = df.dropDuplicates()
        duplicates_removed = initial_count - df.count()
        print(f"✓ Removed {duplicates_removed} duplicate rows")

        # 2. Handle missing values
        # Drop rows where all values are null
        df = df.dropna(how='all')

        # Fill missing values for specific columns (customize based on your data)
        # Example: fill missing string columns with 'Unknown'
        for column in df.columns:
            dtype = df.schema[column].dataType
            if isinstance(dtype, StringType):
                df = df.fillna({column: 'Unknown'})

        print(f"✓ Handled missing values")

        # 3. Clean string columns
        for column in df.columns:
            dtype = df.schema[column].dataType
            if isinstance(dtype, StringType):
                # Trim whitespace and convert to lowercase
                df = df.withColumn(column, trim(col(column)))
                # Remove special characters (optional)
                # df = df.withColumn(column, regexp_replace(col(column), r'[^a-zA-Z0-9\s]', ''))

        print(f"✓ Cleaned string columns")

        # 4. Show data quality report
        print("\n--- Data Quality Report ---")
        print(f"Total rows after cleaning: {df.count()}")
        print(f"Total columns: {len(df.columns)}")

        return df

    def transform_for_recommendation(self, df):
        """
        Transform data into recommendation format
        Customize based on your specific recommendation algorithm
        """
        print("\n--- Data Transformation Started ---")

        # Example transformation: calculate scores, normalize data, etc.
        # This is a placeholder - customize based on your actual data structure

        # Add or rename columns to match RecommendationData model
        # Required columns: item_id, item_name, category, score, description

        print("✓ Data transformed for recommendations")
        return df

    def write_to_mysql(self, df, db_config):
        """
        Write DataFrame to MySQL database
        """
        try:
            print("\n--- Writing to MySQL ---")

            jdbc_url = f"jdbc:mysql://{db_config['host']}:{db_config['port']}/{db_config['database']}"

            df.write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", db_config['table']) \
                .option("user", db_config['user']) \
                .option("password", db_config['password']) \
                .option("driver", "com.mysql.cj.jdbc.Driver") \
                .mode("append") \
                .save()

            print(f"✓ Successfully wrote {df.count()} records to MySQL table: {db_config['table']}")
            return True

        except Exception as e:
            print(f"✗ Error writing to MySQL: {e}")
            return False

    def process_data(self, input_file, db_config):
        """
        Main processing pipeline
        """
        print("\n" + "="*50)
        print("Starting Data Processing Pipeline")
        print("="*50)

        # Step 1: Read data
        df = self.read_csv(input_file)
        if df is None:
            return False

        # Step 2: Clean data
        df_cleaned = self.clean_data(df)

        # Step 3: Transform for recommendations
        df_transformed = self.transform_for_recommendation(df_cleaned)

        # Step 4: Show sample
        print("\n--- Sample Data (First 5 rows) ---")
        df_transformed.show(5, truncate=False)

        # Step 5: Write to MySQL
        success = self.write_to_mysql(df_transformed, db_config)

        print("\n" + "="*50)
        if success:
            print("✓ Data Processing Completed Successfully!")
        else:
            print("✗ Data Processing Failed")
        print("="*50 + "\n")

        return success

    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("Spark session stopped")


def main():
    """
    Example usage
    """
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': '3306',
        'database': 'recommendation_db',
        'table': 'recommendation_data',
        'user': 'root',
        'password': 'your_password'  # Change this
    }

    # Input file
    input_file = "data/sample_data.csv"  # Change this to your file path

    # Process data
    cleaner = DataCleaner()
    try:
        cleaner.process_data(input_file, db_config)
    finally:
        cleaner.stop()


if __name__ == "__main__":
    main()
