"""
Test Spark connection to HiveServer2 via JDBC
Alternative approach using JDBC instead of Metastore
"""
import os

# Set Java environment
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession

def test_hiveserver_jdbc():
    """Test connection to HiveServer2 via JDBC"""
    print("\n" + "="*60)
    print("Testing Spark - HiveServer2 JDBC Connection")
    print("="*60 + "\n")

    try:
        # Create Spark session (without Hive support)
        print("⏳ Creating Spark session...")
        spark = SparkSession.builder \
            .appName("HiveServer2-JDBC-Test") \
            .getOrCreate()

        spark.sparkContext.setLogLevel("ERROR")

        print(f"✓ Spark session created successfully")
        print(f"✓ Spark version: {spark.version}\n")

        # JDBC connection parameters
        jdbc_url = "jdbc:hive2://localhost:10000/movielens_db"
        connection_properties = {
            "driver": "org.apache.hive.jdbc.HiveDriver"
        }

        # Test 1: Read from cleaned_movies
        print("Test 1: Read cleaned_movies via JDBC")
        print("-" * 60)

        # Read directly from table, then select specific columns
        movies_df_all = spark.read.jdbc(
            url=jdbc_url,
            table="cleaned_movies",
            properties=connection_properties
        )

        # Filter out the genres_array column which causes issues
        movies_df = movies_df_all.drop("genres_array")

        movies_count = movies_df.count()
        print(f"✓ Successfully read {movies_count:,} movies\n")

        # Show sample
        print("Sample movies data:")
        movies_df.show(5, truncate=False)

        # Test 2: Read from cleaned_ratings
        print("\nTest 2: Read cleaned_ratings via JDBC")
        print("-" * 60)

        # Use SQL query to select specific columns
        ratings_query = """
            (SELECT userId, movieId, rating, rating_date, timestamp, is_valid
             FROM cleaned_ratings) AS ratings_table
        """

        ratings_df = spark.read.jdbc(
            url=jdbc_url,
            table=ratings_query,
            properties=connection_properties
        )

        ratings_count = ratings_df.count()
        print(f"✓ Successfully read {ratings_count:,} ratings\n")

        # Show sample
        print("Sample ratings data:")
        ratings_df.show(5, truncate=False)

        # Test 3: Execute SQL query
        print("\nTest 3: Execute SQL query via JDBC")
        print("-" * 60)

        # Rename columns to remove table prefix for easier SQL
        movies_clean = movies_df.select(
            movies_df.columns[0].split(".")[-1] if "." in movies_df.columns[0] else movies_df.columns[0],
            *[movies_df[col].alias(col.split(".")[-1]) for col in movies_df.columns[1:]]
        )

        ratings_clean = ratings_df.select(
            *[ratings_df[col].alias(col.split(".")[-1]) for col in ratings_df.columns]
        )

        # Create temporary views with clean column names
        movies_clean.createOrReplaceTempView("movies")
        ratings_clean.createOrReplaceTempView("ratings")

        # Calculate movie statistics
        stats_df = spark.sql("""
            SELECT
                m.movieid,
                m.title,
                m.year,
                COUNT(r.rating) as rating_count,
                AVG(r.rating) as avg_rating
            FROM movies m
            LEFT JOIN ratings r ON m.movieid = r.movieid
            WHERE m.is_valid = TRUE AND r.is_valid = TRUE
            GROUP BY m.movieid, m.title, m.year
            HAVING rating_count >= 100
            ORDER BY avg_rating DESC
            LIMIT 10
        """)

        print("Top 10 movies by average rating (min 100 ratings):")
        stats_df.show(truncate=False)

        # Success!
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("✅ Spark can successfully read from HiveServer2 via JDBC")
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
    success = test_hiveserver_jdbc()
    exit(0 if success else 1)
