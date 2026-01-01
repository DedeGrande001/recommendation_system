"""
Spark job for processing MovieLens dataset
Processes movies, ratings, and generates recommendations
"""
import os
import sys

# Set Java environment before importing PySpark
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, count, explode, split, trim, lower,
    regexp_extract, when, lit, desc, row_number
)
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, LongType
from datetime import datetime


class MovieLensProcessor:
    def __init__(self, app_name="MovieLensProcessor"):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")
        print(f"\n{'='*60}")
        print(f"MovieLens Data Processing Pipeline Started")
        print(f"Spark Version: {self.spark.version}")
        print(f"{'='*60}\n")

    def read_movies(self, file_path):
        """Read movies.csv file"""
        print(f"📂 Reading movies data from: {file_path}")

        schema = StructType([
            StructField("movieId", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("genres", StringType(), True)
        ])

        df = self.spark.read.csv(file_path, header=True, schema=schema)

        # Extract year from title (handle empty strings)
        df = df.withColumn(
            "year",
            when(regexp_extract(col("title"), r"\((\d{4})\)", 1) != "",
                 regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType()))
            .otherwise(None)
        )

        print(f"✓ Loaded {df.count():,} movies")
        return df

    def read_ratings(self, file_path):
        """Read ratings.csv file"""
        print(f"📂 Reading ratings data from: {file_path}")

        schema = StructType([
            StructField("userId", IntegerType(), True),
            StructField("movieId", IntegerType(), True),
            StructField("rating", FloatType(), True),
            StructField("timestamp", LongType(), True)
        ])

        df = self.spark.read.csv(file_path, header=True, schema=schema)
        print(f"✓ Loaded {df.count():,} ratings")
        return df

    def calculate_movie_statistics(self, ratings_df):
        """Calculate average rating and count for each movie"""
        print(f"\n📊 Calculating movie statistics...")

        stats_df = ratings_df.groupBy("movieId").agg(
            avg("rating").alias("avg_rating"),
            count("rating").alias("rating_count")
        )

        print(f"✓ Calculated statistics for {stats_df.count():,} movies")
        return stats_df

    def generate_top_rated_movies(self, movies_df, stats_df, min_ratings=100, top_n=1000):
        """
        Generate top-rated movies with sufficient ratings
        """
        print(f"\n⭐ Generating top-rated movies...")
        print(f"   Minimum ratings threshold: {min_ratings}")
        print(f"   Top N movies: {top_n}")

        # Join movies with statistics
        movies_with_stats = movies_df.join(stats_df, "movieId", "inner")

        # Filter by minimum rating count
        filtered = movies_with_stats.filter(col("rating_count") >= min_ratings)

        # Calculate weighted rating (Bayesian average)
        # Formula: (v/(v+m)) * R + (m/(v+m)) * C
        # v = number of ratings for the movie
        # m = minimum ratings required
        # R = average rating for the movie
        # C = mean rating across all movies

        mean_rating = stats_df.agg(avg("avg_rating")).collect()[0][0]

        filtered = filtered.withColumn(
            "weighted_rating",
            ((col("rating_count") / (col("rating_count") + lit(min_ratings))) * col("avg_rating") +
             (lit(min_ratings) / (col("rating_count") + lit(min_ratings))) * lit(mean_rating))
        )

        # Get top N movies
        top_movies = filtered.orderBy(desc("weighted_rating")).limit(top_n)

        print(f"✓ Generated {top_movies.count():,} top-rated recommendations")
        return top_movies

    def generate_genre_recommendations(self, movies_df, stats_df, min_ratings=50):
        """
        Generate top movies for each genre
        """
        print(f"\n🎬 Generating genre-based recommendations...")

        # Explode genres (split pipe-separated genres)
        movies_with_stats = movies_df.join(stats_df, "movieId", "inner")

        # Filter by minimum ratings
        filtered = movies_with_stats.filter(col("rating_count") >= min_ratings)

        # Explode genres
        exploded = filtered.withColumn("genre", explode(split(col("genres"), "\\|")))

        # Get top movies per genre
        window = Window.partitionBy("genre").orderBy(desc("avg_rating"), desc("rating_count"))

        genre_recommendations = exploded.withColumn("rank", row_number().over(window)) \
            .filter(col("rank") <= 50) \
            .select("movieId", "title", "genre", "avg_rating", "rating_count")

        print(f"✓ Generated genre-based recommendations")
        return genre_recommendations

    def prepare_for_mysql(self, movies_df, stats_df, top_movies_df):
        """
        Prepare data for MySQL insertion
        """
        print(f"\n💾 Preparing data for MySQL...")

        # Prepare movies table data
        movies_for_db = movies_df.join(stats_df, "movieId", "left") \
            .select(
                col("movieId").alias("movie_id"),
                col("title"),
                col("genres"),
                col("year"),
                col("avg_rating").cast(FloatType()),
                col("rating_count").cast(IntegerType())
            ).fillna({"avg_rating": 0.0, "rating_count": 0})

        # Prepare recommendations table data
        recommendations_for_db = top_movies_df.select(
            col("movieId").alias("movie_id"),
            col("weighted_rating").alias("recommendation_score"),
            col("avg_rating").alias("popularity_score")
        )

        print(f"✓ Prepared {movies_for_db.count():,} movies")
        print(f"✓ Prepared {recommendations_for_db.count():,} recommendations")

        return movies_for_db, recommendations_for_db

    def write_to_mysql(self, df, table_name, db_config, mode="append"):
        """
        Write DataFrame to MySQL database
        """
        try:
            print(f"\n📤 Writing to MySQL table: {table_name}")

            jdbc_url = f"jdbc:mysql://{db_config['host']}:{db_config['port']}/{db_config['database']}?useSSL=false&allowPublicKeyRetrieval=true"

            df.write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", table_name) \
                .option("user", db_config['user']) \
                .option("password", db_config['password']) \
                .option("driver", "com.mysql.cj.jdbc.Driver") \
                .mode(mode) \
                .save()

            print(f"✓ Successfully wrote {df.count():,} records to {table_name}")
            return True

        except Exception as e:
            print(f"✗ Error writing to MySQL: {e}")
            return False

    def save_to_csv(self, df, output_path, filename):
        """Save DataFrame to CSV for inspection"""
        try:
            full_path = os.path.join(output_path, filename)
            print(f"\n💾 Saving to CSV: {full_path}")

            df.coalesce(1).write.mode("overwrite").option("header", "true").csv(full_path)
            print(f"✓ Saved successfully")
            return True
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
            return False

    def process_movielens(self, data_path, db_config=None, save_csv=True):
        """
        Main processing pipeline for MovieLens dataset
        """
        print("\n" + "="*60)
        print("STARTING MOVIELENS PROCESSING PIPELINE")
        print("="*60)

        # File paths
        movies_file = os.path.join(data_path, "movies.csv")
        ratings_file = os.path.join(data_path, "ratings.csv")

        # Step 1: Read data
        movies_df = self.read_movies(movies_file)
        ratings_df = self.read_ratings(ratings_file)

        # Step 2: Calculate statistics
        stats_df = self.calculate_movie_statistics(ratings_df)

        # Step 3: Generate recommendations
        top_movies_df = self.generate_top_rated_movies(movies_df, stats_df, min_ratings=100, top_n=1000)

        # Step 4: Show sample results
        print(f"\n📋 Sample Top Recommendations:")
        top_movies_df.select("title", "genres", "avg_rating", "rating_count", "weighted_rating") \
            .show(10, truncate=False)

        # Step 5: Prepare for MySQL
        movies_for_db, recommendations_for_db = self.prepare_for_mysql(movies_df, stats_df, top_movies_df)

        # Step 6: Save to CSV (optional)
        if save_csv:
            output_dir = os.path.join(os.path.dirname(data_path), "processed_output")
            os.makedirs(output_dir, exist_ok=True)

            self.save_to_csv(movies_for_db, output_dir, "movies_processed")
            self.save_to_csv(recommendations_for_db, output_dir, "recommendations_processed")

        # Step 7: Write to MySQL (if configured)
        if db_config:
            print(f"\n{'='*60}")
            print("WRITING TO MYSQL DATABASE")
            print(f"{'='*60}")

            # Write movies
            self.write_to_mysql(movies_for_db, "movies", db_config, mode="append")

            # Note: We need to write recommendations after movies are inserted
            # because recommendations have foreign key to movies
            print("\n⚠️  Note: Recommendations need to be written after movies are in DB")
            print("   Run the recommendation insertion separately after movies are loaded")

        print(f"\n{'='*60}")
        print("✅ PROCESSING COMPLETED SUCCESSFULLY")
        print(f"{'='*60}\n")

        return {
            'movies': movies_for_db,
            'recommendations': recommendations_for_db,
            'stats': stats_df
        }

    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("\n🛑 Spark session stopped\n")


def main():
    """
    Example usage
    """
    # Configuration
    data_path = r"D:\myproject\project\recommendation_system\data\archive\ml-25m"

    db_config = {
        'host': 'localhost',
        'port': '3306',
        'database': 'recommendation_db',
        'user': 'root',
        'password': 'your_password'  # Change this!
    }

    # Process data
    processor = MovieLensProcessor()

    try:
        # Process without MySQL (just generate CSV files)
        results = processor.process_movielens(
            data_path=data_path,
            db_config=None,  # Set to db_config to write to MySQL
            save_csv=True
        )

        print("\n📊 Processing Summary:")
        print(f"   Movies processed: {results['movies'].count():,}")
        print(f"   Recommendations generated: {results['recommendations'].count():,}")

    finally:
        processor.stop()


if __name__ == "__main__":
    main()
