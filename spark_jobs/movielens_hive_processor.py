"""
Spark job for processing MovieLens dataset from Hive
Reads cleaned data from Hive and generates recommendations
"""
import os
import sys

# Set Java environment before importing PySpark
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, count, explode, split, trim, lower,
    regexp_extract, when, lit, desc, row_number, size
)
from pyspark.sql.window import Window
from datetime import datetime


class MovieLensHiveProcessor:
    def __init__(self, app_name="MovieLensHiveProcessor", hive_metastore_uri="thrift://localhost:9083"):
        """Initialize Spark session with Hive support"""
        print(f"\n{'='*60}")
        print(f"Initializing Spark with Hive Integration")
        print(f"Metastore URI: {hive_metastore_uri}")
        print(f"{'='*60}\n")

        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
            .config("hive.metastore.uris", hive_metastore_uri) \
            .enableHiveSupport() \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        print(f"✓ Spark Version: {self.spark.version}")
        print(f"✓ Hive Support: Enabled")
        print(f"{'='*60}\n")

    def read_from_hive(self, database="movielens_db"):
        """Read cleaned data from Hive tables"""
        print(f"\n📂 Reading data from Hive database: {database}")

        try:
            # Use the database
            self.spark.sql(f"USE {database}")

            # Show available tables
            print("\n📋 Available tables:")
            self.spark.sql("SHOW TABLES").show()

            # Read cleaned movies
            print(f"\n📽️  Reading cleaned_movies...")
            movies_df = self.spark.sql("""
                SELECT
                    movieId,
                    title,
                    year,
                    genres,
                    genres_array,
                    is_valid
                FROM cleaned_movies
                WHERE is_valid = TRUE
            """)

            movies_count = movies_df.count()
            print(f"✓ Loaded {movies_count:,} valid movies")

            # Read cleaned ratings
            print(f"\n⭐ Reading cleaned_ratings...")
            ratings_df = self.spark.sql("""
                SELECT
                    userId,
                    movieId,
                    rating,
                    rating_date,
                    timestamp,
                    is_valid
                FROM cleaned_ratings
                WHERE is_valid = TRUE
            """)

            ratings_count = ratings_df.count()
            print(f"✓ Loaded {ratings_count:,} valid ratings")

            # Show sample data
            print(f"\n📋 Sample Movies Data:")
            movies_df.select("movieId", "title", "year", "genres").show(5, truncate=False)

            print(f"\n📋 Sample Ratings Data:")
            ratings_df.select("userId", "movieId", "rating", "rating_date").show(5, truncate=False)

            return movies_df, ratings_df

        except Exception as e:
            print(f"\n❌ Error reading from Hive: {str(e)}")
            raise

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
        Uses Bayesian average for weighted rating
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

    def generate_genre_recommendations(self, movies_df, stats_df, min_ratings=50, top_per_genre=50):
        """
        Generate top movies for each genre
        """
        print(f"\n🎬 Generating genre-based recommendations...")
        print(f"   Minimum ratings: {min_ratings}")
        print(f"   Top movies per genre: {top_per_genre}")

        # Join movies with statistics
        movies_with_stats = movies_df.join(stats_df, "movieId", "inner")

        # Filter by minimum ratings
        filtered = movies_with_stats.filter(col("rating_count") >= min_ratings)

        # Explode genres array (Hive already split genres into array)
        exploded = filtered.withColumn("genre", explode(col("genres_array")))

        # Get top movies per genre
        window = Window.partitionBy("genre").orderBy(desc("avg_rating"), desc("rating_count"))

        genre_recommendations = exploded.withColumn("rank", row_number().over(window)) \
            .filter(col("rank") <= top_per_genre) \
            .select("movieId", "title", "genre", "year", "avg_rating", "rating_count", "rank")

        genre_count = genre_recommendations.select("genre").distinct().count()
        print(f"✓ Generated recommendations for {genre_count} genres")

        return genre_recommendations

    def analyze_data_quality(self, movies_df, ratings_df):
        """
        Analyze data quality improvements from Hive cleaning
        """
        print(f"\n🔍 Data Quality Analysis")
        print(f"{'='*60}")

        # Movies analysis
        print(f"\n📽️  Movies Data Quality:")
        print(f"   Total movies: {movies_df.count():,}")

        movies_with_year = movies_df.filter(col("year").isNotNull()).count()
        print(f"   Movies with year: {movies_with_year:,} ({movies_with_year/movies_df.count()*100:.1f}%)")

        movies_with_genres = movies_df.filter(size(col("genres_array")) > 0).count()
        print(f"   Movies with genres: {movies_with_genres:,} ({movies_with_genres/movies_df.count()*100:.1f}%)")

        # Ratings analysis
        print(f"\n⭐ Ratings Data Quality:")
        print(f"   Total ratings: {ratings_df.count():,}")

        unique_users = ratings_df.select("userId").distinct().count()
        unique_movies = ratings_df.select("movieId").distinct().count()

        print(f"   Unique users: {unique_users:,}")
        print(f"   Unique movies: {unique_movies:,}")

        rating_stats = ratings_df.agg(
            avg("rating").alias("avg"),
            count("rating").alias("count")
        ).collect()[0]

        print(f"   Average rating: {rating_stats['avg']:.2f}")
        print(f"   Ratings per user: {ratings_df.count()/unique_users:.1f}")
        print(f"   Ratings per movie: {ratings_df.count()/unique_movies:.1f}")

        print(f"{'='*60}\n")

    def save_recommendations_to_csv(self, top_movies_df, genre_recs_df, output_dir):
        """Save recommendations to CSV files"""
        print(f"\n💾 Saving recommendations to CSV...")

        os.makedirs(output_dir, exist_ok=True)

        # Save top movies
        top_movies_path = os.path.join(output_dir, "top_movies_from_hive")
        top_movies_df.coalesce(1).write.mode("overwrite") \
            .option("header", "true").csv(top_movies_path)
        print(f"✓ Saved top movies to: {top_movies_path}")

        # Save genre recommendations
        genre_path = os.path.join(output_dir, "genre_recommendations_from_hive")
        genre_recs_df.coalesce(1).write.mode("overwrite") \
            .option("header", "true").csv(genre_path)
        print(f"✓ Saved genre recommendations to: {genre_path}")

    def process_from_hive(self, database="movielens_db", save_csv=True, output_dir=None):
        """
        Main processing pipeline using Hive cleaned data
        """
        print("\n" + "="*60)
        print("STARTING MOVIELENS PROCESSING FROM HIVE")
        print("="*60)

        # Step 1: Read cleaned data from Hive
        movies_df, ratings_df = self.read_from_hive(database)

        # Step 2: Analyze data quality
        self.analyze_data_quality(movies_df, ratings_df)

        # Step 3: Calculate statistics
        stats_df = self.calculate_movie_statistics(ratings_df)

        # Step 4: Generate top-rated recommendations
        top_movies_df = self.generate_top_rated_movies(
            movies_df, stats_df,
            min_ratings=100,
            top_n=1000
        )

        # Step 5: Generate genre-based recommendations
        genre_recs_df = self.generate_genre_recommendations(
            movies_df, stats_df,
            min_ratings=50,
            top_per_genre=50
        )

        # Step 6: Show sample results
        print(f"\n📋 Top 10 Recommended Movies:")
        top_movies_df.select("title", "year", "genres", "avg_rating", "rating_count", "weighted_rating") \
            .show(10, truncate=False)

        print(f"\n📋 Sample Genre Recommendations:")
        genre_recs_df.filter(col("genre") == "Action") \
            .select("title", "year", "avg_rating", "rating_count", "rank") \
            .show(10, truncate=False)

        # Step 7: Save to CSV (optional)
        if save_csv and output_dir:
            self.save_recommendations_to_csv(top_movies_df, genre_recs_df, output_dir)

        print(f"\n{'='*60}")
        print("✅ HIVE PROCESSING COMPLETED SUCCESSFULLY")
        print(f"{'='*60}\n")

        return {
            'movies': movies_df,
            'ratings': ratings_df,
            'stats': stats_df,
            'top_movies': top_movies_df,
            'genre_recommendations': genre_recs_df
        }

    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("\n🛑 Spark session stopped\n")


def main():
    """
    Example usage
    """
    # Output directory for CSV files
    output_dir = r"D:\myproject\project\recommendation_system\data\hive_processed_output"

    # Create processor
    processor = MovieLensHiveProcessor(
        app_name="MovieLens-Hive-Processor",
        hive_metastore_uri="thrift://localhost:9083"
    )

    try:
        # Process data from Hive
        results = processor.process_from_hive(
            database="movielens_db",
            save_csv=True,
            output_dir=output_dir
        )

        print("\n📊 Processing Summary:")
        print(f"   Movies: {results['movies'].count():,}")
        print(f"   Ratings: {results['ratings'].count():,}")
        print(f"   Top recommendations: {results['top_movies'].count():,}")
        print(f"   Genre recommendations: {results['genre_recommendations'].count():,}")

    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        processor.stop()


if __name__ == "__main__":
    main()
