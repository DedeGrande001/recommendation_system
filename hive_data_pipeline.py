#!/usr/bin/env python3
"""
Hive 数据清洗管道
自动化数据上传、清洗和验证流程
"""

import os
import sys
import subprocess
from pathlib import Path
import logging
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HiveDataPipeline:
    """Hive 数据处理管道"""

    def __init__(self, base_dir=None):
        """初始化"""
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.hive_scripts_dir = self.base_dir / 'hive_scripts'
        self.data_dir = self.base_dir / 'data'
        self.progress_file = self.base_dir / 'hive_cleaning_progress.json'

        # 初始化进度
        self.update_progress(0, "初始化", "准备开始数据清洗...")

    def update_progress(self, percentage, current_step, message, status="running"):
        """更新进度信息到文件"""
        progress_data = {
            'percentage': percentage,
            'current_step': current_step,
            'message': message,
            'status': status,  # running, completed, error
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"无法更新进度文件: {e}")

    def run_hdfs_command(self, command):
        """执行 HDFS 命令"""
        full_command = f"docker exec namenode hdfs dfs {command}"
        logger.info(f"执行 HDFS 命令: {command}")

        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"HDFS 命令执行成功")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"HDFS 命令执行失败: {e.stderr}")
            raise

    def run_hive_script(self, script_path):
        """执行 Hive SQL 脚本"""
        script_file = self.hive_scripts_dir / script_path

        if not script_file.exists():
            raise FileNotFoundError(f"脚本文件不存在: {script_file}")

        logger.info(f"执行 Hive 脚本: {script_path}")

        # 首先复制脚本到容器中
        container_script_path = f"/tmp/{script_path}"
        copy_cmd = f"docker cp {script_file} hive-server:{container_script_path}"

        try:
            subprocess.run(copy_cmd, shell=True, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"复制脚本到容器失败: {e.stderr}")
            raise

        # 使用 beeline -f 参数从文件执行 SQL
        command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f {container_script_path}'

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800  # 30 分钟超时 (数据清洗步骤需要更长时间)
            )

            if result.returncode == 0:
                logger.info(f"Hive 脚本执行成功: {script_path}")
                return result.stdout
            else:
                logger.error(f"Hive 脚本执行失败: {result.stderr}")
                raise Exception(result.stderr)

        except subprocess.TimeoutExpired:
            logger.error(f"Hive 脚本执行超时: {script_path}")
            raise
        except Exception as e:
            logger.error(f"执行 Hive 脚本时出错: {str(e)}")
            raise

    def create_hdfs_directories(self):
        """创建 HDFS 目录结构"""
        self.update_progress(5, "步骤 1/6", "创建 HDFS 目录结构...")
        logger.info("=" * 60)
        logger.info("步骤 1: 创建 HDFS 目录")
        logger.info("=" * 60)

        directories = [
            '/user/hive/warehouse',
            '/user/hive/warehouse/raw',
            '/user/hive/warehouse/raw/movies',
            '/user/hive/warehouse/raw/ratings',
            '/user/hive/warehouse/cleaned',
            '/user/hive/warehouse/cleaned/movies',
            '/user/hive/warehouse/cleaned/ratings',
        ]

        for directory in directories:
            try:
                # 检查目录是否存在
                self.run_hdfs_command(f"-test -d {directory}")
                logger.info(f"  ✓ 目录已存在: {directory}")
            except:
                # 目录不存在，创建它
                self.run_hdfs_command(f"-mkdir -p {directory}")
                logger.info(f"  ✓ 创建目录: {directory}")

        # 设置权限
        self.run_hdfs_command("-chmod -R 777 /user/hive/warehouse")
        logger.info("  ✓ 设置目录权限完成")
        self.update_progress(15, "步骤 1/6", "HDFS 目录创建完成")

    def upload_data_to_hdfs(self):
        """上传数据文件到 HDFS"""
        self.update_progress(20, "步骤 2/6", "上传数据文件到 HDFS...")
        logger.info("=" * 60)
        logger.info("步骤 2: 上传数据到 HDFS")
        logger.info("=" * 60)

        # 数据文件映射
        data_files = {
            'movies.csv': '/user/hive/warehouse/raw/movies/',
            'ratings.csv': '/user/hive/warehouse/raw/ratings/',
        }

        for local_file, hdfs_path in data_files.items():
            local_path = self.data_dir / local_file

            if not local_path.exists():
                logger.warning(f"  ⚠ 本地文件不存在: {local_path}")
                logger.info(f"     请确保 {local_file} 在 {self.data_dir} 目录中")
                continue

            try:
                # 检查 HDFS 中是否已有文件
                file_in_hdfs = hdfs_path + local_file
                try:
                    self.run_hdfs_command(f"-test -f {file_in_hdfs}")
                    logger.info(f"  ⚠ 文件已存在于 HDFS: {file_in_hdfs}")
                    # 删除旧文件
                    self.run_hdfs_command(f"-rm {file_in_hdfs}")
                    logger.info(f"  ✓ 删除旧文件")
                except:
                    pass

                # 上传文件（从容器内部上传）
                # 首先复制文件到容器
                copy_cmd = f"docker cp {local_path} namenode:/tmp/{local_file}"
                subprocess.run(copy_cmd, shell=True, check=True)

                # 然后从容器上传到 HDFS
                self.run_hdfs_command(f"-put /tmp/{local_file} {hdfs_path}")

                logger.info(f"  ✓ 上传成功: {local_file} -> {hdfs_path}")

            except Exception as e:
                logger.error(f"  ✗ 上传失败: {local_file}, 错误: {str(e)}")
                raise

        self.update_progress(35, "步骤 2/6", "数据文件上传完成")

    def create_hive_tables(self):
        """创建 Hive 表"""
        self.update_progress(40, "步骤 3/6", "创建 Hive 表结构...")
        logger.info("=" * 60)
        logger.info("步骤 3: 创建 Hive 表")
        logger.info("=" * 60)

        try:
            output = self.run_hive_script('01_create_tables.sql')
            logger.info("  ✓ Hive 表创建成功")
            self.update_progress(50, "步骤 3/6", "Hive 表创建完成")
            return output
        except Exception as e:
            logger.error(f"  ✗ 创建 Hive 表失败: {str(e)}")
            raise

    def run_data_quality_check(self):
        """运行数据质量检查"""
        self.update_progress(55, "步骤 4/6", "执行数据质量检查...")
        logger.info("=" * 60)
        logger.info("步骤 4: 数据质量检查")
        logger.info("=" * 60)

        try:
            output = self.run_hive_script('02_data_quality_check.sql')
            logger.info("  ✓ 数据质量检查完成")
            self.update_progress(65, "步骤 4/6", "数据质量检查完成")
            return output
        except Exception as e:
            logger.error(f"  ✗ 数据质量检查失败: {str(e)}")
            raise

    def run_data_cleaning(self):
        """运行数据清洗"""
        self.update_progress(70, "步骤 5/6", "正在清洗数据（这可能需要几分钟）...")
        logger.info("=" * 60)
        logger.info("步骤 5: 数据清洗")
        logger.info("=" * 60)

        try:
            output = self.run_hive_script('03_data_cleaning.sql')
            logger.info("  ✓ 数据清洗完成")
            self.update_progress(85, "步骤 5/6", "数据清洗完成")
            return output
        except Exception as e:
            logger.error(f"  ✗ 数据清洗失败: {str(e)}")
            raise

    def verify_results(self):
        """验证最终结果"""
        self.update_progress(90, "步骤 6/6", "验证清洗结果...")
        logger.info("=" * 60)
        logger.info("步骤 6: 验证结果")
        logger.info("=" * 60)

        verify_sql = """
        USE movielens_db;
        SELECT 'Tables in database:' as info;
        SHOW TABLES;

        SELECT '' as separator;
        SELECT 'Cleaned Movies Count:' as info;
        SELECT COUNT(*) as count FROM cleaned_movies;

        SELECT '' as separator;
        SELECT 'Cleaned Ratings Count:' as info;
        SELECT COUNT(*) as count FROM cleaned_ratings;

        SELECT '' as separator;
        SELECT 'Sample Cleaned Movies (first 5):' as info;
        SELECT * FROM cleaned_movies LIMIT 5;
        """

        try:
            command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "{verify_sql}"'
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            logger.info("  ✓ 验证完成")
            print("\n" + result.stdout)
            self.update_progress(95, "步骤 6/6", "验证完成")
            return result.stdout
        except Exception as e:
            logger.error(f"  ✗ 验证失败: {str(e)}")
            raise

    def run_full_pipeline(self):
        """运行完整的数据管道"""
        logger.info("🚀 启动 Hive 数据清洗管道")
        logger.info("=" * 60)

        try:
            # 步骤 1: 创建 HDFS 目录
            self.create_hdfs_directories()

            # 步骤 2: 上传数据
            self.upload_data_to_hdfs()

            # 步骤 3: 创建表
            self.create_hive_tables()

            # 步骤 4: 质量检查
            self.run_data_quality_check()

            # 步骤 5: 数据清洗
            self.run_data_cleaning()

            # 步骤 6: 验证结果
            self.verify_results()

            logger.info("=" * 60)
            logger.info("✅ 数据管道执行完成！")
            logger.info("=" * 60)

            # 标记为完成
            self.update_progress(100, "完成", "所有数据清洗步骤已完成！", status="completed")

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ 数据管道执行失败: {str(e)}")
            logger.error("=" * 60)
            # 标记为错误
            self.update_progress(0, "错误", f"清洗失败: {str(e)}", status="error")
            sys.exit(1)


def main():
    """主函数"""
    pipeline = HiveDataPipeline()

    # 运行完整管道
    pipeline.run_full_pipeline()


if __name__ == '__main__':
    main()
