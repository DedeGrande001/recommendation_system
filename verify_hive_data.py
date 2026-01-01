#!/usr/bin/env python3
"""
Hive 数据验证脚本
验证数据清洗结果并生成报告
"""

import subprocess
import sys
from datetime import datetime


class HiveDataVerifier:
    """Hive 数据验证器"""

    def __init__(self):
        self.results = []

    def run_hive_query(self, query):
        """执行 Hive 查询"""
        command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 --silent=true --showHeader=false -e "{query}"'

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"ERROR: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "ERROR: Query timeout"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def check_database_exists(self):
        """检查数据库是否存在"""
        print("=" * 60)
        print("检查 1: 验证数据库")
        print("=" * 60)

        query = "SHOW DATABASES;"
        output = self.run_hive_query(query)

        if "movielens_db" in output:
            print("✓ movielens_db 数据库存在")
            self.results.append(("Database", "PASS", "movielens_db exists"))
            return True
        else:
            print("✗ movielens_db 数据库不存在")
            self.results.append(("Database", "FAIL", "movielens_db not found"))
            return False

    def check_tables_exist(self):
        """检查表是否存在"""
        print("\n" + "=" * 60)
        print("检查 2: 验证表结构")
        print("=" * 60)

        query = "USE movielens_db; SHOW TABLES;"
        output = self.run_hive_query(query)

        expected_tables = [
            'raw_movies',
            'raw_ratings',
            'cleaned_movies',
            'cleaned_ratings',
            'data_quality_report'
        ]

        all_exist = True
        for table in expected_tables:
            if table in output:
                print(f"✓ {table} 表存在")
                self.results.append(("Table", "PASS", f"{table} exists"))
            else:
                print(f"✗ {table} 表不存在")
                self.results.append(("Table", "FAIL", f"{table} missing"))
                all_exist = False

        return all_exist

    def check_data_counts(self):
        """检查数据量"""
        print("\n" + "=" * 60)
        print("检查 3: 验证数据量")
        print("=" * 60)

        tables = [
            ('raw_movies', 'Raw Movies'),
            ('raw_ratings', 'Raw Ratings'),
            ('cleaned_movies', 'Cleaned Movies'),
            ('cleaned_ratings', 'Cleaned Ratings')
        ]

        for table, display_name in tables:
            query = f"USE movielens_db; SELECT COUNT(*) FROM {table};"
            count = self.run_hive_query(query)

            try:
                count_int = int(count.strip())
                if count_int > 0:
                    print(f"✓ {display_name}: {count_int:,} 条记录")
                    self.results.append(("Count", "PASS", f"{table}: {count_int}"))
                else:
                    print(f"✗ {display_name}: 0 条记录（数据为空）")
                    self.results.append(("Count", "FAIL", f"{table} is empty"))
            except ValueError:
                print(f"✗ {display_name}: 无法获取计数 ({count})")
                self.results.append(("Count", "ERROR", f"{table}: {count}"))

    def check_data_quality(self):
        """检查数据质量"""
        print("\n" + "=" * 60)
        print("检查 4: 验证数据质量")
        print("=" * 60)

        # 检查清洗后电影数据的有效性
        query = """
        USE movielens_db;
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_valid = TRUE THEN 1 ELSE 0 END) as valid,
            SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) as invalid
        FROM cleaned_movies;
        """
        output = self.run_hive_query(query)

        if "ERROR" not in output:
            parts = output.strip().split()
            if len(parts) >= 3:
                total, valid, invalid = parts[0], parts[1], parts[2]
                print(f"电影数据质量:")
                print(f"  - 总记录数: {total}")
                print(f"  - 有效记录: {valid}")
                print(f"  - 无效记录: {invalid}")

                valid_pct = (int(valid) / int(total) * 100) if int(total) > 0 else 0
                if valid_pct >= 95:
                    print(f"  ✓ 有效率: {valid_pct:.2f}% (优秀)")
                    self.results.append(("Quality", "PASS", f"Movies: {valid_pct:.2f}% valid"))
                else:
                    print(f"  ⚠ 有效率: {valid_pct:.2f}% (需要改进)")
                    self.results.append(("Quality", "WARN", f"Movies: {valid_pct:.2f}% valid"))

        # 检查清洗后评分数据的有效性
        query = """
        USE movielens_db;
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_valid = TRUE THEN 1 ELSE 0 END) as valid,
            SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) as invalid,
            MIN(rating) as min_rating,
            MAX(rating) as max_rating,
            AVG(rating) as avg_rating
        FROM cleaned_ratings;
        """
        output = self.run_hive_query(query)

        if "ERROR" not in output:
            parts = output.strip().split()
            if len(parts) >= 6:
                total, valid, invalid, min_r, max_r, avg_r = parts[:6]
                print(f"\n评分数据质量:")
                print(f"  - 总记录数: {total}")
                print(f"  - 有效记录: {valid}")
                print(f"  - 无效记录: {invalid}")
                print(f"  - 评分范围: {float(min_r):.1f} - {float(max_r):.1f}")
                print(f"  - 平均评分: {float(avg_r):.2f}")

                valid_pct = (int(valid) / int(total) * 100) if int(total) > 0 else 0
                if valid_pct >= 95:
                    print(f"  ✓ 有效率: {valid_pct:.2f}% (优秀)")
                    self.results.append(("Quality", "PASS", f"Ratings: {valid_pct:.2f}% valid"))
                else:
                    print(f"  ⚠ 有效率: {valid_pct:.2f}% (需要改进)")
                    self.results.append(("Quality", "WARN", f"Ratings: {valid_pct:.2f}% valid"))

    def check_partitions(self):
        """检查分区"""
        print("\n" + "=" * 60)
        print("检查 5: 验证分区")
        print("=" * 60)

        query = """
        USE movielens_db;
        SHOW PARTITIONS cleaned_ratings;
        """
        output = self.run_hive_query(query)

        if "ERROR" not in output and output.strip():
            partitions = output.strip().split('\n')
            partition_count = len(partitions)
            print(f"✓ 找到 {partition_count} 个分区")
            print(f"  示例分区:")
            for p in partitions[:5]:
                print(f"    - {p}")
            if partition_count > 5:
                print(f"    ... 还有 {partition_count - 5} 个分区")

            self.results.append(("Partitions", "PASS", f"{partition_count} partitions found"))
        else:
            print("✗ 未找到分区或查询失败")
            self.results.append(("Partitions", "FAIL", "No partitions found"))

    def check_sample_data(self):
        """检查样例数据"""
        print("\n" + "=" * 60)
        print("检查 6: 验证样例数据")
        print("=" * 60)

        # 查看电影样例
        query = """
        USE movielens_db;
        SELECT movieId, title, year, genres FROM cleaned_movies WHERE is_valid = TRUE LIMIT 3;
        """
        output = self.run_hive_query(query)

        if "ERROR" not in output and output.strip():
            print("电影数据样例:")
            for line in output.strip().split('\n'):
                print(f"  {line}")
            self.results.append(("Sample", "PASS", "Movies sample data OK"))
        else:
            print("✗ 无法获取电影样例数据")
            self.results.append(("Sample", "FAIL", "Cannot fetch movie samples"))

        # 查看评分样例
        query = """
        USE movielens_db;
        SELECT userId, movieId, rating, rating_date FROM cleaned_ratings WHERE is_valid = TRUE LIMIT 3;
        """
        output = self.run_hive_query(query)

        if "ERROR" not in output and output.strip():
            print("\n评分数据样例:")
            for line in output.strip().split('\n'):
                print(f"  {line}")
            self.results.append(("Sample", "PASS", "Ratings sample data OK"))
        else:
            print("✗ 无法获取评分样例数据")
            self.results.append(("Sample", "FAIL", "Cannot fetch rating samples"))

    def generate_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("验证报告摘要")
        print("=" * 60)

        pass_count = sum(1 for r in self.results if r[1] == "PASS")
        fail_count = sum(1 for r in self.results if r[1] == "FAIL")
        warn_count = sum(1 for r in self.results if r[1] == "WARN")
        error_count = sum(1 for r in self.results if r[1] == "ERROR")

        print(f"\n总检查项: {len(self.results)}")
        print(f"  ✓ 通过: {pass_count}")
        print(f"  ✗ 失败: {fail_count}")
        print(f"  ⚠ 警告: {warn_count}")
        print(f"  ⚠ 错误: {error_count}")

        if fail_count == 0 and error_count == 0:
            print("\n🎉 所有验证检查通过！数据清洗成功！")
            return True
        else:
            print("\n❌ 部分验证检查失败，请检查详细信息")
            print("\n失败项目:")
            for category, status, detail in self.results:
                if status in ["FAIL", "ERROR"]:
                    print(f"  - [{category}] {detail}")
            return False

    def run_all_checks(self):
        """运行所有验证检查"""
        print("🔍 Hive 数据验证工具")
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        try:
            # 执行所有检查
            self.check_database_exists()
            self.check_tables_exist()
            self.check_data_counts()
            self.check_data_quality()
            self.check_partitions()
            self.check_sample_data()

            # 生成报告
            success = self.generate_report()

            print("\n" + "=" * 60)

            return success

        except Exception as e:
            print(f"\n❌ 验证过程中出错: {str(e)}")
            return False


def main():
    """主函数"""
    verifier = HiveDataVerifier()
    success = verifier.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
