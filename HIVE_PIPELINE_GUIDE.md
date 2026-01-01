# Hive 数据清洗管道使用指南

## 📋 概述

本指南帮助你运行 Hive 数据清洗管道，将 MovieLens 原始 CSV 数据清洗并存储到 Hive 数据仓库中。

## 🔧 前提条件

### 1. 确保 Docker 服务运行正常

```bash
# 检查所有服务状态
docker-compose ps

# 应该看到以下服务都在运行：
# - namenode
# - datanode
# - hive-metastore-postgresql
# - hive-metastore
# - hive-server
```

### 2. 准备数据文件

确保以下文件存在于 `data/` 目录：

- `data/movies.csv` - 电影数据
- `data/ratings.csv` - 评分数据

如果文件不存在，请从 [MovieLens](https://grouplens.org/datasets/movielens/25m/) 下载 ml-25m 数据集。

### 3. 验证 Hive 连接

```bash
# 测试 HiveServer2 是否可用
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"
```

## 🚀 运行数据管道

### 方式一：运行完整管道（推荐）

```bash
# 运行完整的数据清洗管道
python hive_data_pipeline.py
```

管道会自动执行以下步骤：
1. 创建 HDFS 目录结构
2. 上传 CSV 文件到 HDFS
3. 创建 Hive 表
4. 运行数据质量检查
5. 执行数据清洗
6. 验证最终结果

### 方式二：分步执行

如果需要单独执行某个步骤：

```python
from hive_data_pipeline import HiveDataPipeline

pipeline = HiveDataPipeline()

# 步骤 1: 创建 HDFS 目录
pipeline.create_hdfs_directories()

# 步骤 2: 上传数据
pipeline.upload_data_to_hdfs()

# 步骤 3: 创建表
pipeline.create_hive_tables()

# 步骤 4: 质量检查
pipeline.run_data_quality_check()

# 步骤 5: 数据清洗
pipeline.run_data_cleaning()

# 步骤 6: 验证结果
pipeline.verify_results()
```

## 📊 验证结果

### 1. 查看 Hive 表

```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
SHOW TABLES;
"
```

应该看到以下表：
- `raw_movies` - 原始电影数据
- `raw_ratings` - 原始评分数据
- `cleaned_movies` - 清洗后电影数据
- `cleaned_ratings` - 清洗后评分数据
- `data_quality_report` - 数据质量报告

### 2. 检查数据量

```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
SELECT 'Cleaned Movies' as table_name, COUNT(*) as count FROM cleaned_movies
UNION ALL
SELECT 'Cleaned Ratings' as table_name, COUNT(*) as count FROM cleaned_ratings;
"
```

### 3. 查看清洗后的样例数据

```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
SELECT * FROM cleaned_movies LIMIT 10;
"
```

### 4. 查看数据质量报告

```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
SELECT * FROM data_quality_report;
"
```

## 📁 输出数据结构

### cleaned_movies 表结构

| 字段名 | 类型 | 说明 |
|--------|------|------|
| movieId | INT | 电影 ID |
| title | STRING | 电影标题（已去除空格） |
| year | INT | 发行年份（从标题提取） |
| genres_array | ARRAY<STRING> | 类型数组 |
| genres | STRING | 原始类型字符串 |
| is_valid | BOOLEAN | 数据有效性标记 |

### cleaned_ratings 表结构

| 字段名 | 类型 | 说明 |
|--------|------|------|
| userId | INT | 用户 ID |
| movieId | INT | 电影 ID |
| rating | DOUBLE | 评分（0.5-5.0） |
| rating_date | STRING | 评分日期时间 |
| timestamp | BIGINT | Unix 时间戳 |
| is_valid | BOOLEAN | 数据有效性标记 |
| rating_year | INT | 评分年份（分区字段） |
| rating_month | INT | 评分月份（分区字段） |

## 🔍 数据清洗规则

### 电影数据清洗

1. **去除空格** - 清理标题首尾空格
2. **提取年份** - 使用正则表达式从标题中提取年份 `(YYYY)`
3. **拆分类型** - 将 `Action|Adventure|Sci-Fi` 拆分为数组
4. **有效性标记** - 过滤掉 movieId、title、genres 为空的记录

### 评分数据清洗

1. **去重** - 对于同一用户对同一电影的多次评分，保留最新的
2. **范围验证** - 评分必须在 0.5-5.0 之间
3. **时间转换** - 将 Unix 时间戳转换为可读日期
4. **动态分区** - 按年份和月份分区存储
5. **有效性标记** - 过滤掉不符合条件的记录

## 🛠️ 故障排查

### 问题 1: "FileNotFoundError: 脚本文件不存在"

**解决方案**：确保 `hive_scripts/` 目录下存在以下文件：
- `01_create_tables.sql`
- `02_data_quality_check.sql`
- `03_data_cleaning.sql`

### 问题 2: "本地文件不存在"

**解决方案**：检查 `data/` 目录是否包含 `movies.csv` 和 `ratings.csv`

### 问题 3: "HDFS 命令执行失败"

**解决方案**：
```bash
# 检查 NameNode 是否运行
docker ps | grep namenode

# 重启 NameNode
docker-compose restart namenode
```

### 问题 4: "Hive 脚本执行超时"

**解决方案**：
- 脚本默认超时 5 分钟
- 如果数据量很大，可以在 `hive_data_pipeline.py` 中增加 timeout 参数
- 检查 HiveServer2 日志：`docker logs hive-server`

### 问题 5: 分区数据查询为空

**解决方案**：
```bash
# 修复分区
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
MSCK REPAIR TABLE cleaned_ratings;
"
```

## 📈 性能优化建议

1. **Parquet 格式** - 清洗后的数据使用 Parquet 列式存储，查询性能更好
2. **分区策略** - 评分数据按年月分区，可以提高时间范围查询效率
3. **数据压缩** - Parquet 自动压缩，节省存储空间

## 🔗 下一步

数据清洗完成后，可以：

1. **在 Spark 中使用清洗后的数据**
   ```python
   from pyspark.sql import SparkSession

   spark = SparkSession.builder \
       .appName("MovieLens") \
       .config("hive.metastore.uris", "thrift://localhost:9083") \
       .enableHiveSupport() \
       .getOrCreate()

   # 读取清洗后的数据
   movies_df = spark.sql("SELECT * FROM movielens_db.cleaned_movies WHERE is_valid = true")
   ratings_df = spark.sql("SELECT * FROM movielens_db.cleaned_ratings WHERE is_valid = true")
   ```

2. **更新 Django 应用** - 使用清洗后的数据进行推荐

3. **数据分析** - 在 Hive 中进行 SQL 分析

## 📝 日志文件

管道运行时会输出详细日志，包括：
- 每个步骤的执行状态
- HDFS 操作结果
- Hive 脚本执行输出
- 错误信息和堆栈跟踪

查看完整日志可以帮助诊断问题。

## ✅ 检查清单

运行管道前请确认：

- [ ] Docker 服务全部运行（namenode, datanode, hive-metastore, hive-server）
- [ ] HiveServer2 端口 10000 可访问
- [ ] data/movies.csv 文件存在
- [ ] data/ratings.csv 文件存在
- [ ] Python 环境已安装（Python 3.6+）

运行管道后请验证：

- [ ] movielens_db 数据库已创建
- [ ] 所有表已创建（raw_movies, raw_ratings, cleaned_movies, cleaned_ratings）
- [ ] cleaned_movies 有数据
- [ ] cleaned_ratings 有数据且已分区
- [ ] data_quality_report 显示质量指标

---

**提示**: 首次运行管道可能需要几分钟时间，具体取决于数据文件大小。25M 数据集包含约 2500 万条评分记录，预计需要 5-10 分钟完成清洗。
