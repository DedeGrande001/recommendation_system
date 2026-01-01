"""
Import ALS-trained recommendation results into Django database
使用训练好的 ALS 推荐结果导入到 Django 数据库
"""
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from app.models import Movie, RecommendationData
from django.db import transaction


class RecommendationImporter:
    """导入 ALS 推荐结果到 Django"""

    def __init__(self, output_dir="output"):
        """初始化导入器"""
        self.output_dir = Path(output_dir)
        self.stats_file = self.output_dir / "movie_statistics.csv"
        self.recs_file = self.output_dir / "user_recommendations.csv"

    def validate_files(self):
        """验证文件是否存在"""
        print("\n" + "="*60)
        print("验证数据文件")
        print("="*60)

        if not self.stats_file.exists():
            print(f"❌ 文件不存在: {self.stats_file}")
            return False

        if not self.recs_file.exists():
            print(f"❌ 文件不存在: {self.recs_file}")
            return False

        print(f"✓ 电影统计文件: {self.stats_file}")
        print(f"✓ 推荐结果文件: {self.recs_file}")
        return True

    def import_movies(self):
        """导入电影数据和统计信息"""
        print("\n" + "="*60)
        print("导入电影数据")
        print("="*60)

        # Read movie statistics
        print(f"\n⏳ 读取电影统计数据...")
        df = pd.read_csv(self.stats_file)
        print(f"✓ 读取 {len(df):,} 部电影")

        # Show sample
        print("\n电影数据示例:")
        print(df.head(5))

        # Clear existing data
        print(f"\n⏳ 清空旧数据...")
        Movie.objects.all().delete()
        print("✓ 旧数据已清空")

        # Import movies
        print(f"\n⏳ 导入电影数据到数据库...")
        movies_to_create = []

        for _, row in df.iterrows():
            # Handle NaN values
            year = None
            if pd.notna(row.get('year')):
                try:
                    year = int(row['year'])
                except (ValueError, TypeError):
                    year = None

            genres = row.get('genres', '')
            if pd.isna(genres):
                genres = ''

            movies_to_create.append(Movie(
                movie_id=int(row['movieId']),
                title=str(row['title']),
                genres=genres,
                year=year,
                avg_rating=float(row['avg_rating']),
                rating_count=int(row['rating_count'])
            ))

        # Bulk create with transaction
        with transaction.atomic():
            Movie.objects.bulk_create(movies_to_create, batch_size=1000)

        print(f"✓ 成功导入 {len(movies_to_create):,} 部电影")

        # Show top rated movies
        print("\n评分最高的 10 部电影:")
        top_movies = Movie.objects.order_by('-avg_rating', '-rating_count')[:10]
        for i, movie in enumerate(top_movies, 1):
            print(f"  {i}. {movie.title} - {movie.avg_rating:.2f} ({movie.rating_count} ratings)")

        return len(movies_to_create)

    def import_recommendations(self):
        """导入用户推荐数据"""
        print("\n" + "="*60)
        print("导入推荐数据")
        print("="*60)

        # Read recommendations
        print(f"\n⏳ 读取推荐数据...")
        df = pd.read_csv(self.recs_file)
        print(f"✓ 读取 {len(df):,} 条推荐")

        # Show sample
        print("\n推荐数据示例:")
        print(df.head(5))

        # Clear existing recommendations
        print(f"\n⏳ 清空旧推荐数据...")
        RecommendationData.objects.all().delete()
        print("✓ 旧推荐数据已清空")

        # Get all movie IDs for validation
        print(f"\n⏳ 验证电影数据...")
        movie_ids_in_db = set(Movie.objects.values_list('movie_id', flat=True))
        print(f"✓ 数据库中有 {len(movie_ids_in_db):,} 部电影")

        # Import recommendations
        print(f"\n⏳ 导入推荐数据到数据库...")
        recs_to_create = []
        skipped = 0

        for _, row in df.iterrows():
            movie_id = int(row['movieId'])

            # Skip if movie doesn't exist
            if movie_id not in movie_ids_in_db:
                skipped += 1
                continue

            try:
                movie = Movie.objects.get(movie_id=movie_id)
                recs_to_create.append(RecommendationData(
                    movie=movie,
                    user_id=int(row['userId']),
                    recommendation_score=float(row['predicted_rating']),
                    popularity_score=movie.avg_rating  # Use movie's avg_rating
                ))
            except Movie.DoesNotExist:
                skipped += 1
                continue

        # Bulk create with transaction
        print(f"⏳ 批量创建推荐记录...")
        with transaction.atomic():
            RecommendationData.objects.bulk_create(recs_to_create, batch_size=1000)

        print(f"✓ 成功导入 {len(recs_to_create):,} 条推荐")
        if skipped > 0:
            print(f"⚠ 跳过 {skipped:,} 条推荐 (电影不存在)")

        # Show sample recommendations
        print("\n用户 1 的推荐 (Top 5):")
        user1_recs = RecommendationData.objects.filter(user_id=1).order_by('-recommendation_score')[:5]
        for i, rec in enumerate(user1_recs, 1):
            print(f"  {i}. {rec.movie.title} - 预测评分: {rec.recommendation_score:.2f}")

        return len(recs_to_create)

    def show_statistics(self):
        """显示导入统计信息"""
        print("\n" + "="*60)
        print("导入统计")
        print("="*60)

        total_movies = Movie.objects.count()
        total_recs = RecommendationData.objects.count()
        unique_users = RecommendationData.objects.values('user_id').distinct().count()

        print(f"\n✓ 电影总数: {total_movies:,}")
        print(f"✓ 推荐总数: {total_recs:,}")
        print(f"✓ 用户总数: {unique_users:,}")
        print(f"✓ 平均每用户推荐数: {total_recs / unique_users if unique_users > 0 else 0:.1f}")

        # Top rated movies
        print("\n评分最高的 5 部电影:")
        for movie in Movie.objects.order_by('-avg_rating', '-rating_count')[:5]:
            print(f"  • {movie.title}")
            print(f"    平均评分: {movie.avg_rating:.2f} | 评分数: {movie.rating_count:,}")

    def run(self):
        """运行完整导入流程"""
        print("\n" + "="*60)
        print("ALS 推荐结果导入 Django 数据库")
        print("="*60)

        try:
            # Validate files
            if not self.validate_files():
                return False

            # Import movies
            movies_count = self.import_movies()

            # Import recommendations
            recs_count = self.import_recommendations()

            # Show statistics
            self.show_statistics()

            # Success
            print("\n" + "="*60)
            print("✅ 导入完成！")
            print("="*60)
            print(f"\n📊 导入结果:")
            print(f"   • 电影: {movies_count:,}")
            print(f"   • 推荐: {recs_count:,}")
            print(f"\n🌐 访问系统: http://127.0.0.1:8000")
            print()

            return True

        except Exception as e:
            print(f"\n❌ 导入失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    importer = RecommendationImporter(output_dir="output")
    success = importer.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
