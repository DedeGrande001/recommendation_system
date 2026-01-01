# Hive 数据清洗 - 快速开始

## 🚀 一键运行

### Windows 用户

```bash
# 直接运行批处理脚本
run_hive_pipeline.bat
```

### Linux/Mac 用户

```bash
# 运行 Python 脚本
python hive_data_pipeline.py
```

## 📋 准备工作

### 1. 确保 Docker 服务运行

```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

应该看到以下服务都在运行：
- ✅ namenode
- ✅ datanode
- ✅ hive-metastore-postgresql
- ✅ hive-metastore
- ✅ hive-server

### 2. 准备 MovieLens 数据

确保以下文件存在：
- `data/movies.csv`
- `data/ratings.csv`

**下载地址**: https://grouplens.org/datasets/movielens/25m/

### 3. 创建数据库

```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "CREATE DATABASE IF NOT EXISTS movielens_db;"
```

## 📊 验证结果

运行管道后，验证数据清洗结果：

```bash
# 使用验证脚本（推荐）
python verify_hive_data.py

# 或手动查询
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
SHOW TABLES;
SELECT COUNT(*) FROM cleaned_movies;
SELECT COUNT(*) FROM cleaned_ratings;
"
```

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `hive_data_pipeline.py` | 主管道脚本，自动执行所有清洗步骤 |
| `run_hive_pipeline.bat` | Windows 一键启动脚本 |
| `verify_hive_data.py` | 数据验证工具 |
| `hive_scripts/01_create_tables.sql` | 创建 Hive 表结构 |
| `hive_scripts/02_data_quality_check.sql` | 数据质量检查 |
| `hive_scripts/03_data_cleaning.sql` | 数据清洗逻辑 |
| `HIVE_PIPELINE_GUIDE.md` | 详细使用指南 |

## 🔄 管道执行流程

```
1. 创建 HDFS 目录
   ↓
2. 上传 CSV 到 HDFS
   ↓
3. 创建 Hive 表
   ↓
4. 数据质量检查
   ↓
5. 执行数据清洗
   ↓
6. 验证清洗结果
```

## ✅ 预期结果

成功运行后，你应该看到：

```
============================================================
✅ 数据管道执行完成！
============================================================
```

验证脚本输出示例：

```
检查 1: 验证数据库
============================================================
✓ movielens_db 数据库存在

检查 2: 验证表结构
============================================================
✓ raw_movies 表存在
✓ raw_ratings 表存在
✓ cleaned_movies 表存在
✓ cleaned_ratings 表存在
✓ data_quality_report 表存在

检查 3: 验证数据量
============================================================
✓ Cleaned Movies: 62,423 条记录
✓ Cleaned Ratings: 25,000,095 条记录

🎉 所有验证检查通过！数据清洗成功！
```

## 🛠️ 常见问题

### Q1: 运行时提示 "HiveServer2 未运行"

**A**: 检查服务状态
```bash
docker-compose ps
docker logs hive-server
```

如果服务未运行，重启：
```bash
docker-compose restart hive-server
```

### Q2: 数据文件不存在

**A**: 从 MovieLens 下载 ml-25m 数据集，解压后将 `movies.csv` 和 `ratings.csv` 复制到 `data/` 目录。

### Q3: 管道执行超时

**A**: 25M 数据集包含 2500 万条评分，首次运行可能需要 5-10 分钟。如果超过 10 分钟，检查：
- HiveServer2 日志: `docker logs hive-server`
- HDFS 状态: `docker exec namenode hdfs dfsadmin -report`

### Q4: 分区数据为空

**A**: 运行分区修复：
```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "
USE movielens_db;
MSCK REPAIR TABLE cleaned_ratings;
"
```

## 📖 更多信息

详细文档请参阅 [HIVE_PIPELINE_GUIDE.md](HIVE_PIPELINE_GUIDE.md)

## 🔗 下一步

数据清洗完成后：

1. **在 Spark 中使用清洗后的数据**
   - 配置 Spark 连接 Hive Metastore
   - 读取 `cleaned_movies` 和 `cleaned_ratings`

2. **集成到推荐系统**
   - 更新 Spark 推荐模型训练脚本
   - 使用清洗后的高质量数据

3. **数据分析**
   - 在 Hive 中进行 SQL 分析
   - 生成数据统计报告

---

**需要帮助？** 查看完整文档或检查 Docker 日志
