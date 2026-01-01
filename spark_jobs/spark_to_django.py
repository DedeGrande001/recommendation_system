"""
Spark + Django integration script
Uses Spark for processing, then saves to Django database
"""
import os
import sys
import pandas as pd

# Set Java environment before importing PySpark
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, count, regexp_extract, when, lit, desc
)
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, LongType

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from app.models import Movie, RecommendationData


class SparkDjangoProcessor:
    def __init__(self):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName("MovieLensSparkDjango") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")
        print(f"\n{'='*60}")
        print(f"Spark + Django MovieLens Processor")
        print(f"Spark Version: {self.spark.version}")
        print(f"{'='*60}\n")

    def process_movielens(self, data_path, min_ratings=100, top_n=1000):
        """Process MovieLens data with Spark and save to Django"""

        # File paths
        movies_file = os.path.join(data_path, "movies.csv")
        ratings_file = os.path.join(data_path, "ratings.csv")

        # Read movies
        print(f"📂 Reading movies from: {movies_file}")
        movies_schema = StructType([
            StructField("movieId", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("genres", StringType(), True)
        ])
        movies_df = self.spark.read.csv(movies_file, header=True, schema=movies_schema)

        # Extract year (handle empty strings)
        movies_df = movies_df.withColumn(
            "year",
            when(regexp_extract(col("title"), r"\((\d{4})\)", 1) != "",
                 regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType()))
            .otherwise(None)
        )

        print(f"✓ Loaded {movies_df.count():,} movies")

        # Read ratings
        print(f"📂 Reading ratings from: {ratings_file}")
        ratings_schema = StructType([
            StructField("userId", IntegerType(), True),
            StructField("movieId", IntegerType(), True),
            StructField("rating", FloatType(), True),
            StructField("timestamp", LongType(), True)
        ])
        ratings_df = self.spark.read.csv(ratings_file, header=True, schema=ratings_schema)
        print(f"✓ Loaded {ratings_df.count():,} ratings")

        # Calculate statistics
        print(f"\n📊 Calculating movie statistics...")
        stats_df = ratings_df.groupBy("movieId").agg(
            avg("rating").alias("avg_rating"),
            count("rating").alias("rating_count")
        )
        print(f"✓ Calculated statistics for {stats_df.count():,} movies")

        # Join movies with stats
        movies_with_stats = movies_df.join(stats_df, "movieId", "left") \
            .fillna({"avg_rating": 0.0, "rating_count": 0})

        # Generate top recommendations
        print(f"\n⭐ Generating top-rated movies...")
        print(f"   Minimum ratings threshold: {min_ratings}")
        print(f"   Top N movies: {top_n}")

        # Filter by minimum rating count
        filtered = movies_with_stats.filter(col("rating_count") >= min_ratings)

        # Calculate weighted rating (Bayesian average)
        mean_rating = stats_df.agg(avg("avg_rating")).collect()[0][0]

        filtered = filtered.withColumn(
            "weighted_rating",
            ((col("rating_count") / (col("rating_count") + lit(min_ratings))) * col("avg_rating") +
             (lit(min_ratings) / (col("rating_count") + lit(min_ratings))) * lit(mean_rating))
        )

        # Get top N movies
        top_movies = filtered.orderBy(desc("weighted_rating")).limit(top_n)

        print(f"✓ Generated {top_movies.count():,} recommendations")

        # Show sample
        print(f"\n📋 Top 10 Recommendations:")
        top_movies.select("title", "genres", "avg_rating", "rating_count", "weighted_rating") \
            .show(10, truncate=False)

        # Convert to Pandas for Django import
        print(f"\n💾 Saving to Django database...")
        print(f"   Converting Spark DataFrames to Pandas...")

        movies_pandas = movies_with_stats.toPandas()
        recommendations_pandas = top_movies.toPandas()

        print(f"   Clearing old data...")
        Movie.objects.all().delete()
        RecommendationData.objects.all().delete()

        # Save movies
        print(f"   Saving {len(movies_pandas):,} movies...")
        movies_to_create = []
        for _, row in movies_pandas.iterrows():
            movies_to_create.append(Movie(
                movie_id=int(row['movieId']),
                title=row['title'],
                genres=row['genres'] if row['genres'] else '',
                year=int(row['year']) if row['year'] and not pd.isna(row['year']) else None,
                avg_rating=float(row['avg_rating']),
                rating_count=int(row['rating_count'])
            ))

        Movie.objects.bulk_create(movies_to_create, batch_size=1000)
        print(f"✓ Saved {len(movies_to_create):,} movies")

        # Save recommendations
        print(f"   Saving {len(recommendations_pandas):,} recommendations...")
        recommendations_to_create = []
        for _, row in recommendations_pandas.iterrows():
            try:
                movie = Movie.objects.get(movie_id=int(row['movieId']))
                recommendations_to_create.append(RecommendationData(
                    movie=movie,
                    recommendation_score=float(row['weighted_rating']),
                    popularity_score=float(row['avg_rating'])
                ))
            except Movie.DoesNotExist:
                continue

        RecommendationData.objects.bulk_create(recommendations_to_create, batch_size=1000)
        print(f"✓ Saved {len(recommendations_to_create):,} recommendations")

        print(f"\n{'='*60}")
        print("✅ PROCESSING COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        print(f"\n📊 Summary:")
        print(f"   Total movies: {len(movies_pandas):,}")
        print(f"   Total ratings: {ratings_df.count():,}")
        print(f"   Recommendations: {len(recommendations_pandas):,}")
        print(f"\n🌐 Access system: http://127.0.0.1:8000")
        print()

    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("\n🛑 Spark session stopped\n")


def main():
    """Main execution"""
    data_path = r"D:\myproject\project\recommendation_system\data\archive\ml-25m"

    processor = SparkDjangoProcessor()

    try:
        processor.process_movielens(
            data_path=data_path,
            min_ratings=100,
            top_n=1000
        )
    finally:
        processor.stop()


if __name__ == "__main__":
    main()
