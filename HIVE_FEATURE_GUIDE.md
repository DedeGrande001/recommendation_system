# Hive 数据仓库功能说明

## 功能概述

本项目新增了 **Hive 数据查看页面**，可以直接在 Web 界面查看 Hive 数据仓库中的清洗数据统计。

---

## 访问地址

登录后访问: **http://127.0.0.1:8000/hive-data/**

---

## 页面功能

### 1. 连接状态检查
- ✅ 自动检测 Hive 容器是否运行
- ✅ 显示连接状态提示

### 2. 数据统计卡片
显示 Hive 中清洗后的数据统计：
- **电影数量** - 清洗后有效的电影记录数
- **评分数量** - 清洗后有效的评分记录数
- **用户数量** - 独立用户总数
- **平均评分** - 所有评分的平均值

### 3. Top 评分电影
查询并显示评分最高的电影（至少 100 个评分）：
- 电影 ID
- 标题（含年份）
- 类型
- 评分数
- 平均评分

---

## 使用前提

### 1. 启动 Hive 容器

```bash
docker-compose up -d
```

确保以下容器运行中：
- `namenode` - Hadoop NameNode
- `datanode` - Hadoop DataNode
- `hive-server` - HiveServer2
- `hive-metastore-postgresql` - Hive Metastore 数据库

### 2. 运行 Hive 数据清洗

```bash
python hive_data_pipeline.py
```

这会执行完整的数据清洗流程：
1. 创建数据库和表
2. 加载 CSV 数据到 HDFS
3. 数据质量检查
4. 数据清洗和转换
5. 存储到 Hive 表

**预期结果**:
- ✓ 清洗电影: 62,423 部
- ✓ 清洗评分: 25,000,095 条

---

## 技术实现

### 后端实现 - [app/hive_utils.py](app/hive_utils.py)

提供了三个主要函数：

#### 1. `check_hive_connection()`
检查 Hive 连接是否正常
```python
connected, message = check_hive_connection()
```

#### 2. `get_hive_statistics()`
获取 Hive 数据统计
```python
stats = get_hive_statistics()
# 返回: {
#   'movies_count': 62423,
#   'ratings_count': 25000095,
#   'users_count': 162541,
#   'avg_rating': 3.533,
#   'available': True,
#   'error': None
# }
```

#### 3. `get_top_rated_movies_from_hive(limit=10)`
从 Hive 查询 Top 电影
```python
movies, error = get_top_rated_movies_from_hive(limit=10)
```

### 查询机制

使用 **Beeline 命令行工具** 通过 JDBC 查询 Hive：

```python
command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 --outputformat=csv2 -e "{query}"'
```

**查询示例**:
```sql
SET hive.exec.mode.local.auto=true;
SET mapreduce.framework.name=local;
USE movielens_db;
SELECT COUNT(*) FROM cleaned_movies WHERE is_valid = TRUE;
```

---

## 视图路由

### URL 配置 - [app/urls.py](app/urls.py:15)

```python
path('hive-data/', views.hive_data_view, name='hive_data')
```

### 视图函数 - [app/views.py](app/views.py:370-403)

```python
@login_required
def hive_data_view(request):
    """查看 Hive 中的清洗数据"""
    connected, connection_msg = check_hive_connection()

    if connected:
        hive_stats = get_hive_statistics()
        top_movies, error = get_top_rated_movies_from_hive(limit=10)

    return render(request, 'hive_data.html', context)
```

---

## 数据来源

### Hive 表结构

#### cleaned_movies (电影表)
```sql
CREATE TABLE cleaned_movies (
    movieId INT,
    title STRING,
    year INT,
    genres STRING,
    genres_array ARRAY<STRING>,
    is_valid BOOLEAN
)
STORED AS PARQUET
LOCATION '/user/hive/warehouse/cleaned/movies';
```

#### cleaned_ratings (评分表)
```sql
CREATE TABLE cleaned_ratings (
    userId INT,
    movieId INT,
    rating DOUBLE,
    rating_date STRING,
    `timestamp` BIGINT,
    is_valid BOOLEAN
)
PARTITIONED BY (rating_year INT, rating_month INT)
STORED AS ORC
LOCATION '/user/hive/warehouse/cleaned/ratings';
```

---

## 与 Spark 训练的关系

### 数据流程图

```
原始 CSV 数据
    ↓
Hive 数据清洗 ← 可选：通过 Web 页面查看清洗结果
    ↓
方案 1: 从 HDFS 读取 (movielens_hdfs_processor.py)
方案 2: 直接使用 CSV (movielens_csv_processor.py) ← 当前使用
    ↓
Spark ALS 训练
    ↓
Django 数据库
    ↓
Web 展示
```

### 说明

1. **Hive 是数据清洗的中间层**
   - 用于数据验证和质量检查
   - 提供 SQL 接口方便数据分析
   - 存储格式优化（Parquet/ORC）

2. **当前训练方式**
   - 我们使用 **方案 2**（直接 CSV 训练）
   - 因为 HDFS DataNode 存在 IP 变化问题
   - Hive 清洗的数据主要用于演示和验证

3. **未来改进方向**
   - 修复 HDFS 网络问题
   - 使用 Spark 从 Hive/HDFS 读取数据训练
   - 实现完整的大数据处理流程

---

## 常见问题

### Q1: 页面显示"Hive 连接失败"

**原因**: Hive 容器未运行

**解决方案**:
```bash
# 启动容器
docker-compose up -d

# 检查容器状态
docker-compose ps

# 查看 hive-server 日志
docker logs hive-server
```

### Q2: 数据统计显示全为 0

**原因**: Hive 表为空，未运行数据清洗

**解决方案**:
```bash
python hive_data_pipeline.py
```

### Q3: 查询超时

**原因**: Hive 查询执行时间过长

**解决方案**:
- 检查 MapReduce 是否设置为本地模式
- 增加超时时间（`hive_utils.py` 中的 `timeout=30`）
- 减少查询数据量

---

## 页面截图示例

### 正常显示状态

```
============================================
Hive 数据仓库
查看 Hive 中清洗后的 MovieLens 数据
============================================

✓ Hive 连接正常

┌─────────────────────────────────────────┐
│  62,423      25,000,095    162,541      │
│  清洗后的电影   用户评分      独立用户     │
│                                          │
│          平均评分: 3.53                  │
└─────────────────────────────────────────┘

🏆 评分最高的电影（至少 100 个评分）

#  | 标题                          | 年份 | 平均评分
---|-------------------------------|------|----------
1  | The Shawshank Redemption     | 1994 | 4.49
2  | The Godfather                | 1972 | 4.42
3  | Schindler's List             | 1993 | 4.41
...
```

---

## 性能指标

- **连接检查**: < 1 秒
- **统计查询**: 5-10 秒（取决于数据量）
- **Top 电影查询**: 10-15 秒

---

## 文件清单

| 文件 | 说明 |
|------|------|
| [app/hive_utils.py](app/hive_utils.py) | Hive 查询工具函数 |
| [app/views.py](app/views.py:370-403) | Hive 数据视图 |
| [app/urls.py](app/urls.py:15) | URL 路由配置 |
| [app/templates/hive_data.html](app/templates/hive_data.html) | 页面模板 |
| [hive_data_pipeline.py](hive_data_pipeline.py) | 数据清洗脚本 |

---

## 总结

### ✅ 已实现的功能

1. **Hive 连接检查** - 自动检测容器状态
2. **数据统计展示** - 电影、评分、用户数量
3. **Top 电影查询** - 评分最高的电影列表
4. **错误处理** - 友好的错误提示

### 📋 使用步骤

```bash
# 1. 启动 Hive
docker-compose up -d

# 2. 运行数据清洗
python hive_data_pipeline.py

# 3. 启动 Django
python manage.py runserver

# 4. 访问页面
http://127.0.0.1:8000/hive-data/
```

### 🎯 价值

- ✅ **数据验证** - 可视化查看清洗结果
- ✅ **质量监控** - 实时查看数据统计
- ✅ **演示功能** - 展示大数据技术栈
- ✅ **调试工具** - 快速检查 Hive 数据状态

---

**创建时间**: 2026-01-01
**最后更新**: 2026-01-01
