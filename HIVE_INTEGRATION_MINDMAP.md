# Hive数据清洗功能集成思维导图

## 1. 整体架构设计

### 1.1 数据流向
- 用户上传数据（CSV文件）
  - Django接收文件
  - 存储到临时目录
  - 记录上传日志
- 数据源选择
  - 方案A：Spark直接处理（现有流程）
    - 适用场景：小数据集、快速原型
    - 优点：简单快速
    - 缺点：每次重复清洗
  - 方案B：Hive清洗后处理（新增流程）⭐
    - 适用场景：大数据集、需要数据质量管控
    - 优点：清洗结果可重用、SQL易维护
    - 缺点：初始配置复杂

### 1.2 技术栈
- Hadoop HDFS
  - 分布式文件存储
  - 高容错性
  - 支持大文件存储
- Apache Hive
  - SQL-like数据仓库
  - 元数据管理（Metastore）
  - 支持分区表和索引
- Apache Spark
  - 内存计算引擎
  - 集成Hive（enableHiveSupport）
  - 读取Hive表进行分析
- Django
  - Web框架
  - 任务调度
  - 结果展示

---

## 2. 第一阶段：数据导入Hive

### 2.1 上传到HDFS
- 使用HDFS命令行
  - `hdfs dfs -put movies.csv /user/hive/warehouse/raw/`
  - `hdfs dfs -put ratings.csv /user/hive/warehouse/raw/`
- 使用Python hdfs3库
  - 代码自动化上传
  - 错误处理机制
  - 上传进度监控
- 目录结构设计
  - `/user/hive/warehouse/raw/movies/`
  - `/user/hive/warehouse/raw/ratings/`
  - `/user/hive/warehouse/cleaned/`

### 2.2 创建Hive外部表
- raw_movies表
  - 字段：movieId, title, genres
  - 格式：CSV with header
  - 存储位置：HDFS raw目录
  - 表属性：skip.header.line.count=1
- raw_ratings表
  - 字段：userId, movieId, rating, timestamp
  - 格式：CSV with header
  - 存储位置：HDFS raw目录
- 外部表优点
  - 不移动原始数据
  - 删除表不影响HDFS文件
  - 便于多个任务共享数据

### 2.3 验证数据导入
- 行数统计：`SELECT COUNT(*) FROM raw_movies`
- 数据抽样：`SELECT * FROM raw_movies LIMIT 10`
- 检查元数据：`DESCRIBE FORMATTED raw_movies`

---

## 3. 第二阶段：Hive数据清洗（核心）

### 3.1 数据质量检查

#### 3.1.1 空值检测
- 统计各字段空值数量
  - `SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END)`
  - `SUM(CASE WHEN genres IS NULL THEN 1 ELSE 0 END)`
- 空值比例分析
  - 计算空值百分比
  - 生成质量报告
- 处理策略
  - 必填字段：删除空值记录
  - 可选字段：填充默认值

#### 3.1.2 重复数据识别
- 使用ROW_NUMBER窗口函数
  - `ROW_NUMBER() OVER (PARTITION BY movieId ORDER BY timestamp DESC)`
  - 保留最新记录
- 重复统计
  - `GROUP BY movieId HAVING COUNT(*) > 1`
  - 输出重复记录详情

#### 3.1.3 数据类型验证
- Rating范围检查
  - `WHERE rating >= 0.5 AND rating <= 5.0`
  - 识别异常评分
- 日期格式验证
  - Timestamp转换测试
  - `CAST(timestamp AS BIGINT)`
- MovieId存在性检查
  - 外键关联验证
  - 孤立评分识别

#### 3.1.4 异常值检测
- 统计分析
  - 评分分布直方图
  - 识别离群值
- 业务规则验证
  - 标题长度检查
  - Genres格式验证

### 3.2 数据清洗转换

#### 3.2.1 去重操作
- INSERT INTO SELECT DISTINCT
  - 基于主键去重
  - 保留最新/最完整记录
- 分区去重
  - 按年份分区去重
  - 提高处理效率

#### 3.2.2 缺失值处理
- COALESCE函数
  - `COALESCE(genres, '(no genres listed)')`
- CASE WHEN逻辑
  - 条件填充
  - 基于业务规则补全

#### 3.2.3 字段标准化
- TRIM清理空格
  - `TRIM(title)`
  - `TRIM(genres)`
- 大小写转换
  - `UPPER(genres)` 统一大写
  - `LOWER(title)` 统一小写
- 特殊字符清理
  - `regexp_replace(title, '[^a-zA-Z0-9\\s]', '')`

#### 3.2.4 数据类型转换
- String to Int
  - `CAST(year AS INT)`
- Timestamp转换
  - Unix时间戳转日期
  - `FROM_UNIXTIME(timestamp)`

#### 3.2.5 派生字段计算
- 提取年份
  - `regexp_extract(title, '\\((\\d{4})\\)', 1)`
- 分割genres
  - `split(genres, '\\|')` 转数组
- 计算decade
  - `FLOOR(year / 10) * 10`

### 3.3 清洗后数据存储

#### 3.3.1 创建清洗表
- cleaned_movies表
  - movie_id INT
  - title STRING
  - year INT
  - genres ARRAY<STRING>
  - title_clean STRING
- cleaned_ratings表
  - user_id INT
  - movie_id INT
  - rating FLOAT
  - rating_date DATE

#### 3.3.2 分区表设计
- 按年份分区
  - `PARTITIONED BY (year INT)`
  - 提高查询效率
- 按类型分区
  - `PARTITIONED BY (decade INT, genre STRING)`
  - 支持细粒度查询

#### 3.3.3 存储格式优化
- ORC格式
  - 列式存储
  - 高压缩比
  - 支持谓词下推
- Parquet格式
  - 跨平台兼容
  - Spark原生支持

#### 3.3.4 索引和统计信息
- 创建索引
  - `CREATE INDEX idx_movie_id ON TABLE cleaned_movies(movie_id)`
- 收集统计信息
  - `ANALYZE TABLE cleaned_movies COMPUTE STATISTICS`

---

## 4. 第三阶段：Spark读取Hive数据

### 4.1 Spark连接Hive配置

#### 4.1.1 启用Hive支持
- enableHiveSupport()
  - 必须在创建SparkSession时调用
  - 加载Hive Metastore配置
- 配置Metastore URI
  - `spark.sql.warehouse.dir`
  - `hive.metastore.uris=thrift://localhost:9083`

#### 4.1.2 读取Hive表
- SQL方式
  - `spark.sql("SELECT * FROM movielens_db.cleaned_movies")`
  - 支持复杂SQL查询
- Table方式
  - `spark.table("cleaned_movies")`
  - 直接返回DataFrame

#### 4.1.3 分区剪裁优化
- 自动分区过滤
  - `WHERE year = 2020`
  - 只读取相关分区
- 减少数据扫描量
  - 提高查询速度

### 4.2 Spark进行高级分析

#### 4.2.1 统计聚合（复用现有代码）
- movielens_processor.py
  - calculate_movie_statistics()
  - 计算平均评分
  - 统计评分数量

#### 4.2.2 推荐算法计算
- generate_top_rated_movies()
  - 贝叶斯平均评分
  - 加权排序
- generate_genre_recommendations()
  - 按类型推荐

#### 4.2.3 机器学习特征工程
- 特征提取
  - TF-IDF向量化标题
  - One-hot编码genres
- 协同过滤
  - ALS算法
  - 基于用户-物品矩阵

### 4.3 性能优化

#### 4.3.1 缓存策略
- DataFrame缓存
  - `df.cache()`
  - 多次使用的中间结果
- Hive表缓存
  - `CACHE TABLE cleaned_movies`

#### 4.3.2 并行度调整
- 分区数设置
  - `spark.sql.shuffle.partitions=200`
- Executor配置
  - executor-memory
  - executor-cores

---

## 5. 第四阶段：结果写入Django

### 5.1 复用现有流程
- spark_to_django.py
  - toPandas()转换
  - bulk_create批量插入
  - 外键关联处理

### 5.2 新增功能

#### 5.2.1 数据质量报告展示
- HiveCleaningJob模型
  - job_id
  - status（pending/running/completed/failed）
  - quality_report（JSONField）
  - created_at
- 前端展示
  - 清洗前后对比图表
  - 数据质量分数
  - 异常数据明细

#### 5.2.2 任务调度
- Celery集成
  - 异步执行Hive清洗任务
  - 任务进度追踪
- 状态通知
  - WebSocket实时推送
  - 邮件通知完成状态

---

## 6. 项目文件结构

### 6.1 新增文件

#### spark_jobs/hive_data_cleaner.py
- 类：HiveDataCleaner
  - upload_to_hdfs()
  - create_external_tables()
  - data_quality_check()
  - clean_movies_data()
  - clean_ratings_data()
  - create_cleaned_tables()
  - export_quality_report()

#### spark_jobs/spark_hive_processor.py
- 类：SparkHiveProcessor
  - connect_to_hive()
  - read_cleaned_data()
  - process_recommendations()
  - write_to_django()

#### hive_scripts/目录
- create_tables.hql（创建表DDL）
- data_quality_check.hql（质量检查SQL）
- clean_movies.hql（电影清洗DML）
- clean_ratings.hql（评分清洗DML）
- create_partitions.hql（分区管理）
- optimize_tables.hql（优化脚本）

#### config/hive_config.py
- Hive连接配置
  - HIVE_METASTORE_URI
  - HDFS_NAMENODE_URI
  - WAREHOUSE_DIR
- 数据库配置
  - HIVE_DB_NAME
  - TABLE_NAMES

### 6.2 修改文件

#### app/views.py
- 新增视图函数
  - process_with_hive_view()
  - hive_quality_report_view()
  - hive_job_status_view()

#### app/models.py
- 新增模型
  - HiveCleaningJob
  - DataQualityReport

#### app/templates/data_management.html
- UI增强
  - 添加"使用Hive清洗"按钮
  - 显示清洗进度条
  - 质量报告弹窗

---

## 7. Hive SQL脚本示例

### 7.1 创建表脚本（create_tables.hql）

#### 创建外部表
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS raw_movies (
    movieId INT,
    title STRING,
    genres STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/raw/movies'
TBLPROPERTIES ("skip.header.line.count"="1");
```

#### 创建清洗表
```sql
CREATE TABLE IF NOT EXISTS cleaned_movies (
    movie_id INT,
    title STRING,
    year INT,
    genres ARRAY<STRING>,
    title_clean STRING
)
PARTITIONED BY (decade INT)
STORED AS ORC;
```

### 7.2 数据质量检查（data_quality_check.hql）

#### 空值统计
```sql
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END) as null_titles,
    SUM(CASE WHEN genres = '(no genres listed)' THEN 1 ELSE 0 END) as no_genre
FROM raw_movies;
```

#### 重复检查
```sql
SELECT movieId, COUNT(*) as cnt
FROM raw_movies
GROUP BY movieId
HAVING COUNT(*) > 1;
```

### 7.3 数据清洗（clean_movies.hql）

#### INSERT清洗数据
```sql
INSERT OVERWRITE TABLE cleaned_movies PARTITION (decade)
SELECT
    movieId AS movie_id,
    title,
    CAST(regexp_extract(title, '\\((\\d{4})\\)', 1) AS INT) AS year,
    split(genres, '\\|') AS genres,
    trim(regexp_replace(title, '[^a-zA-Z0-9\\s]', '')) AS title_clean,
    FLOOR(CAST(regexp_extract(title, '\\((\\d{4})\\)', 1) AS INT) / 10) * 10 AS decade
FROM raw_movies
WHERE movieId IS NOT NULL
  AND title IS NOT NULL;
```

---

## 8. Python核心代码框架

### 8.1 HiveDataCleaner类

#### 初始化
```python
def __init__(self):
    self.hdfs_client = HDFSClient()
    self.hive_cursor = connect_to_hive()
```

#### 上传HDFS
```python
def upload_to_hdfs(self, local_path, hdfs_path):
    # 使用hdfs3或subprocess调用hdfs命令
    # 错误处理和日志记录
```

#### 执行Hive脚本
```python
def execute_hql_file(self, script_path):
    with open(script_path) as f:
        sql = f.read()
    self.hive_cursor.execute(sql)
```

#### 数据质量检查
```python
def data_quality_check(self):
    # 执行quality check脚本
    # 解析结果
    # 生成JSON报告
    return quality_report
```

### 8.2 SparkHiveProcessor类

#### 连接Hive
```python
def __init__(self):
    self.spark = SparkSession.builder \
        .enableHiveSupport() \
        .config("hive.metastore.uris", "thrift://localhost:9083") \
        .getOrCreate()
```

#### 读取清洗数据
```python
def read_cleaned_data(self):
    movies_df = self.spark.table("cleaned_movies")
    ratings_df = self.spark.table("cleaned_ratings")
    return movies_df, ratings_df
```

---

## 9. 数据流对比分析

### 9.1 现有Spark直接处理流程
```
CSV文件 → Spark读取 → 内存清洗 → 计算分析 → Django数据库
         ↑________________________|（每次都重复清洗）
```
- 优点
  - 实现简单
  - 依赖少
- 缺点
  - 重复工作
  - 难以复用
  - 缺乏数据血缘

### 9.2 新Hive+Spark流程
```
CSV → HDFS → Hive清洗 → ORC存储 → Spark读取 → 计算 → Django
                 ↓
          质量报告生成
          清洗结果可重用
          数据血缘追踪
```
- 优点
  - 一次清洗，多次使用
  - SQL易维护
  - 数据质量可控
  - 支持超大数据集
- 缺点
  - 初始配置复杂
  - 依赖Hive环境

---

## 10. 优势对比表

### 10.1 数据质量
- 现有方案：每次处理时临时清洗，不一致
- Hive方案：统一清洗标准，结果一致

### 10.2 性能
- 现有方案：重复读取CSV，I/O密集
- Hive方案：读取ORC列式存储，性能提升3-10倍

### 10.3 可维护性
- 现有方案：清洗逻辑在Python代码中
- Hive方案：SQL脚本独立，易于维护和版本控制

### 10.4 数据血缘
- 现有方案：难以追踪数据变换历史
- Hive方案：Metastore记录完整血缘

### 10.5 团队协作
- 现有方案：需要PySpark技能
- Hive方案：SQL开发者可参与，降低门槛

### 10.6 扩展性
- 现有方案：受Spark内存限制
- Hive方案：支持PB级数据处理

---

## 11. 实施路线图

### Phase 1: 环境搭建（1周）
- 安装Hadoop HDFS
- 安装Hive Metastore
- 配置Spark连接Hive
- 测试连通性

### Phase 2: 基础功能（2周）
- 实现HDFS上传模块
- 创建Hive外部表脚本
- 基础数据清洗SQL
- Spark读取Hive表测试

### Phase 3: 质量检查（1周）
- 数据质量检查脚本
- 质量报告生成
- Django展示界面

### Phase 4: 优化集成（1周）
- 分区表优化
- ORC格式存储
- 性能调优
- 完整流程测试

### Phase 5: 上线部署（1周）
- 文档编写
- 用户培训
- 监控告警
- 生产环境部署

---

## 12. 适用场景判断

### 适合使用Hive清洗的场景
- 数据集大小 > 10GB
- 需要多次重复分析
- 团队有SQL背景
- 需要严格数据质量管控
- 数据需要长期存档

### 继续使用Spark直接处理的场景
- 小数据集 < 1GB
- 一次性分析任务
- 快速原型开发
- 团队熟悉PySpark

---

## 13. 风险与挑战

### 技术风险
- Hive环境配置复杂
  - 缓解：详细文档+自动化脚本
- Metastore单点故障
  - 缓解：高可用配置

### 运维风险
- HDFS磁盘空间管理
  - 缓解：定期清理+配额限制
- 任务失败处理
  - 缓解：完善错误处理+重试机制

### 学习曲线
- 团队需要学习HiveQL
  - 缓解：培训+示例库

---

## 14. 监控指标

### 数据质量指标
- 空值率
- 重复率
- 异常值比例
- 清洗成功率

### 性能指标
- 清洗任务执行时间
- HDFS读写速度
- Spark任务耗时
- 数据库写入速度

### 资源指标
- HDFS存储空间使用率
- Hive任务CPU使用率
- Metastore连接数

---

## 15. 未来扩展

### 增量更新
- 仅处理新增数据
- 合并到已有分区

### 实时清洗
- Spark Streaming读取Kafka
- 实时写入Hive

### 数据版本管理
- Delta Lake集成
- 时间旅行查询

### 自动化调度
- Airflow DAG定义
- 定时清洗任务

### 机器学习集成
- 特征工程存储在Hive
- MLlib模型训练
