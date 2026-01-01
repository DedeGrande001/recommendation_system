"""
MovieLens Recommendation System - HDFS Direct Access
直接从 HDFS 读取 Hive 清洗后的数据进行推荐模型训练
"""
import os
from datetime import datetime

# Set Java environment
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
os.environ['PATH'] = r'C:\Program Files\Java\jdk-21\bin' + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, explode, split, desc
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator


class MovieLensHDFSProcessor:
    """MovieLens 推荐系统处理器 - 直接读取 HDFS"""

    def __init__(self, app_name="MovieLens-HDFS-Processor"):
        """初始化 Spark Session"""
        print("\n" + "="*60)
        print("初始化 Spark Session")
        print("="*60)

        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .config("spark.executor.memory", "4g") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("ERROR")

        print(f"✓ Spark Session 创建成功")
        print(f"✓ Spark 版本: {self.spark.version}\n")

        self.movies_df = None
        self.ratings_df = None

    def read_from_hdfs(self):
        """从 HDFS 直接读取 Hive 清洗后的数据"""
        print("="*60)
        print("从 HDFS 读取 Hive 清洗后的数据")
        print("="*60)

        try:
            # 读取电影数据 (Parquet 格式)
            print("\n⏳ 读取电影数据...")
            movies_path = "hdfs://localhost:9000/user/hive/warehouse/cleaned/movies"

            self.movies_df = self.spark.read.parquet(movies_path)

            # 过滤有效数据，并选择需要的列（排除 genres_array）
            self.movies_df = self.movies_df \
                .filter(col("is_valid") == True) \
                .select("movieId", "title", "year", "genres")

            movies_count = self.movies_df.count()
            print(f"✓ 成功读取 {movies_count:,} 部电影")

            # 显示示例
            print("\n电影数据示例:")
            self.movies_df.show(5, truncate=False)

            # 读取评分数据 (ORC 格式，带分区)
            print("\n⏳ 读取评分数据...")
            ratings_path = "hdfs://localhost:9000/user/hive/warehouse/cleaned/ratings"

            self.ratings_df = self.spark.read.orc(ratings_path)

            # 过滤有效数据
            self.ratings_df = self.ratings_df \
                .filter(col("is_valid") == True) \
                .select("userId", "movieId", "rating", "rating_date", "timestamp")

            ratings_count = self.ratings_df.count()
            print(f"✓ 成功读取 {ratings_count:,} 条评分")

            # 显示示例
            print("\n评分数据示例:")
            self.ratings_df.show(5, truncate=False)

            # 显示数据统计
            print("\n" + "="*60)
            print("数据统计")
            print("="*60)

            unique_users = self.ratings_df.select("userId").distinct().count()
            unique_movies = self.ratings_df.select("movieId").distinct().count()

            print(f"✓ 独立用户数: {unique_users:,}")
            print(f"✓ 独立电影数: {unique_movies:,}")
            print(f"✓ 总评分数: {ratings_count:,}")

            return True

        except Exception as e:
            print(f"\n❌ 读取数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def analyze_data_quality(self):
        """分析数据质量"""
        print("\n" + "="*60)
        print("数据质量分析")
        print("="*60)

        # 评分分布
        print("\n评分分布:")
        rating_dist = self.ratings_df.groupBy("rating") \
            .agg(count("*").alias("count")) \
            .orderBy("rating")
        rating_dist.show()

        # 最活跃用户
        print("\n最活跃的 10 位用户:")
        top_users = self.ratings_df.groupBy("userId") \
            .agg(count("*").alias("rating_count")) \
            .orderBy(desc("rating_count")) \
            .limit(10)
        top_users.show()

        # 最受欢迎电影
        print("\n评分最多的 10 部电影:")
        top_rated_movies = self.ratings_df.groupBy("movieId") \
            .agg(count("*").alias("rating_count")) \
            .join(self.movies_df, "movieId") \
            .select("movieId", "title", "year", "rating_count") \
            .orderBy(desc("rating_count")) \
            .limit(10)
        top_rated_movies.show(truncate=False)

    def calculate_movie_statistics(self):
        """计算电影统计信息"""
        print("\n" + "="*60)
        print("计算电影统计信息")
        print("="*60)

        movie_stats = self.ratings_df.groupBy("movieId") \
            .agg(
                count("rating").alias("rating_count"),
                avg("rating").alias("avg_rating")
            ) \
            .join(self.movies_df, "movieId") \
            .select("movieId", "title", "year", "genres", "rating_count", "avg_rating")

        # 缓存结果
        movie_stats.cache()

        total_stats = movie_stats.count()
        print(f"✓ 计算了 {total_stats:,} 部电影的统计信息")

        # 评分最高的电影（至少100个评分）
        print("\n评分最高的 10 部电影 (至少100个评分):")
        top_movies = movie_stats \
            .filter(col("rating_count") >= 100) \
            .orderBy(desc("avg_rating")) \
            .limit(10)
        top_movies.show(truncate=False)

        return movie_stats

    def train_als_model(self, rank=10, maxIter=10, regParam=0.1):
        """训练 ALS 协同过滤模型"""
        print("\n" + "="*60)
        print("训练 ALS 协同过滤模型")
        print("="*60)

        # 准备训练数据
        print("\n⏳ 准备训练数据...")
        training_data = self.ratings_df.select("userId", "movieId", "rating")

        # 分割训练集和测试集
        train, test = training_data.randomSplit([0.8, 0.2], seed=42)

        train_count = train.count()
        test_count = test.count()
        print(f"✓ 训练集: {train_count:,} 条")
        print(f"✓ 测试集: {test_count:,} 条")

        # 训练模型
        print(f"\n⏳ 训练 ALS 模型 (rank={rank}, maxIter={maxIter}, regParam={regParam})...")
        als = ALS(
            rank=rank,
            maxIter=maxIter,
            regParam=regParam,
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy="drop"
        )

        model = als.fit(train)
        print("✓ 模型训练完成")

        # 评估模型
        print("\n⏳ 评估模型性能...")
        predictions = model.transform(test)

        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )

        rmse = evaluator.evaluate(predictions)
        print(f"✓ 测试集 RMSE: {rmse:.4f}")

        return model

    def generate_recommendations(self, model, num_recommendations=10):
        """生成推荐结果"""
        print("\n" + "="*60)
        print("生成推荐结果")
        print("="*60)

        # 为所有用户生成推荐
        print(f"\n⏳ 为每位用户生成 {num_recommendations} 个推荐...")
        user_recs = model.recommendForAllUsers(num_recommendations)

        print("✓ 推荐生成完成")

        # 显示示例推荐
        print(f"\n前 5 位用户的推荐结果:")

        # 展开推荐结果并关联电影信息
        user_recs_expanded = user_recs \
            .select("userId", explode("recommendations").alias("rec")) \
            .select("userId", col("rec.movieId").alias("movieId"), col("rec.rating").alias("predicted_rating")) \
            .join(self.movies_df, "movieId") \
            .select("userId", "movieId", "title", "year", "genres", "predicted_rating")

        # 显示前5个用户的推荐
        for user_id in range(1, 6):
            print(f"\n用户 {user_id} 的推荐:")
            user_recs_expanded.filter(col("userId") == user_id) \
                .orderBy(desc("predicted_rating")) \
                .show(num_recommendations, truncate=False)

        return user_recs_expanded

    def save_results(self, recommendations, movie_stats, output_dir="output"):
        """保存结果到本地"""
        print("\n" + "="*60)
        print("保存结果")
        print("="*60)

        import os
        os.makedirs(output_dir, exist_ok=True)

        # 保存推荐结果
        print("\n⏳ 保存推荐结果...")
        rec_output = os.path.join(output_dir, "user_recommendations.csv")
        recommendations.coalesce(1).write.mode("overwrite").csv(rec_output, header=True)
        print(f"✓ 推荐结果已保存: {rec_output}")

        # 保存电影统计
        print("\n⏳ 保存电影统计...")
        stats_output = os.path.join(output_dir, "movie_statistics.csv")
        movie_stats.coalesce(1).write.mode("overwrite").csv(stats_output, header=True)
        print(f"✓ 电影统计已保存: {stats_output}")

    def stop(self):
        """停止 Spark Session"""
        self.spark.stop()
        print("\n✓ Spark Session 已停止")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("MovieLens 推荐系统 - HDFS 直接访问")
    print("="*60)

    processor = MovieLensHDFSProcessor()

    try:
        # 1. 读取数据
        if not processor.read_from_hdfs():
            return False

        # 2. 分析数据质量
        processor.analyze_data_quality()

        # 3. 计算电影统计
        movie_stats = processor.calculate_movie_statistics()

        # 4. 训练推荐模型
        model = processor.train_als_model(rank=10, maxIter=10, regParam=0.1)

        # 5. 生成推荐
        recommendations = processor.generate_recommendations(model, num_recommendations=10)

        # 6. 保存结果
        processor.save_results(recommendations, movie_stats)

        print("\n" + "="*60)
        print("✅ 推荐系统处理完成！")
        print("="*60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        processor.stop()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
