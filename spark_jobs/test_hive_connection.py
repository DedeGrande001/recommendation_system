"""
Test Spark connection to Hive Metastore
Quick script to verify Hive integration works
"""
import os

# Set Java environment
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession

def test_hive_connection():
    """Test basic Hive connectivity"""
    print("\n" + "="*60)
    print("Testing Spark - Hive Connection")
    print("="*60 + "\n")

    try:
        # Create Spark session with Hive support
        print("⏳ Creating Spark session with Hive support...")
        spark = SparkSession.builder \
            .appName("Hive-Connection-Test") \
            .config("spark.sql.catalogImplementation", "hive") \
            .config("spark.hadoop.hive.metastore.uris", "thrift://localhost:9083") \
            .config("spark.sql.hive.metastore.version", "2.3.2") \
            .config("spark.sql.hive.metastore.jars", "maven") \
            .enableHiveSupport() \
            .getOrCreate()

        spark.sparkContext.setLogLevel("ERROR")

        print(f"✓ Spark session created successfully")
        print(f"✓ Spark version: {spark.version}\n")

        # Test 1: Show databases
        print("Test 1: Show databases")
        print("-" * 60)
        spark.sql("SHOW DATABASES").show()

        # Test 2: Use movielens_db
        print("\nTest 2: Use movielens_db")
        print("-" * 60)
        spark.sql("USE movielens_db")
        print("✓ Database selected\n")

        # Test 3: Show tables
        print("Test 3: Show tables in movielens_db")
        print("-" * 60)
        spark.sql("SHOW TABLES").show()

        # Test 4: Query cleaned_movies
        print("\nTest 4: Query cleaned_movies (first 5 rows)")
        print("-" * 60)
        movies_df = spark.sql("""
            SELECT movieId, title, year, genres
            FROM cleaned_movies
            WHERE is_valid = TRUE
            LIMIT 5
        """)
        movies_df.show(truncate=False)

        # Test 5: Count records
        print("\nTest 5: Count records")
        print("-" * 60)

        movies_count = spark.sql("SELECT COUNT(*) as count FROM cleaned_movies").collect()[0]['count']
        ratings_count = spark.sql("SELECT COUNT(*) as count FROM cleaned_ratings").collect()[0]['count']

        print(f"✓ cleaned_movies: {movies_count:,} records")
        print(f"✓ cleaned_ratings: {ratings_count:,} records")

        # Test 6: Query with partition filter
        print("\nTest 6: Query ratings by partition (year=2015, month=1)")
        print("-" * 60)
        ratings_df = spark.sql("""
            SELECT userId, movieId, rating, rating_date
            FROM cleaned_ratings
            WHERE rating_year = 2015 AND rating_month = 1
            LIMIT 5
        """)
        ratings_df.show(truncate=False)

        # Success!
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("✅ Spark can successfully connect to Hive")
        print("✅ Ready to process MovieLens data from Hive")
        print("="*60 + "\n")

        spark.stop()
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_hive_connection()
    exit(0 if success else 1)
