# MovieLens 推荐系统 - Django 集成指南

## 概述

本系统使用 Apache Spark ALS (Alternating Least Squares) 协同过滤算法训练推荐模型，并将结果集成到 Django Web 应用中。

## 系统架构

```
数据流程:
CSV 数据 → Spark ALS 训练 → 推荐结果 → Django 数据库 → Web API/界面
```

### 组件说明

1. **数据处理层** - Apache Spark
   - `movielens_csv_processor.py` - 处理 CSV 数据并训练 ALS 模型
   - `movielens_hdfs_processor.py` - 从 HDFS 读取 Hive 清洗后的数据（可选）

2. **数据存储层** - Django ORM
   - `Movie` - 电影信息（标题、类型、年份、统计信息）
   - `RecommendationData` - 推荐结果（用户ID、电影、预测评分）
   - `Rating` - 用户评分（可选，用于存储原始评分数据）

3. **应用层** - Django Web 应用
   - REST API 端点
   - Web 界面

## 快速开始

### 1. 训练推荐模型

```bash
# 使用 CSV 数据训练（推荐）
cd d:\myproject\project\recommendation_system
python spark_jobs\movielens_csv_processor.py
```

训练完成后，结果将保存在 `output/` 目录：
- `movie_statistics.csv` - 59,047 部电影的统计信息
- `user_recommendations.csv` - 用户推荐结果（前 1000 个用户）

### 2. 导入到 Django 数据库

```bash
# 导入训练好的推荐结果
python import_recommendations.py
```

导入结果：
- ✓ 电影: 59,047 部
- ✓ 推荐: 10,000 条（1000 个用户 × 10 条推荐）
- ✓ 平均每用户推荐数: 10.0

### 3. 启动 Django 服务器

```bash
python manage.py runserver 0.0.0.0:8000
```

## API 端点

### 获取用户推荐（公开访问）

**端点**: `GET /api/user/<user_id>/recommendations/`

**参数**:
- `user_id` (路径参数) - 用户ID（1-1000）
- `limit` (查询参数，可选) - 返回推荐数量，默认 10

**示例请求**:
```bash
curl http://127.0.0.1:8000/api/user/1/recommendations/?limit=5
```

**响应示例**:
```json
{
  "user_id": 1,
  "recommendations": [
    {
      "movie_id": 183947,
      "title": "NOFX Backstage Passport 2",
      "genres": "(no genres listed)",
      "year": null,
      "predicted_rating": 5.46,
      "avg_rating": 5.0,
      "rating_count": 1
    },
    {
      "movie_id": 192089,
      "title": "National Theatre Live: One Man, Two Guvnors (2011)",
      "genres": "Comedy",
      "year": 2011,
      "predicted_rating": 5.24,
      "avg_rating": 5.0,
      "rating_count": 1
    }
  ],
  "count": 5
}
```

### 字段说明

- `movie_id` - 电影唯一标识符
- `title` - 电影标题（包含年份）
- `genres` - 电影类型（用 | 分隔）
- `year` - 上映年份
- `predicted_rating` - **ALS 模型预测评分**（1.0-5.0，核心推荐指标）
- `avg_rating` - 所有用户的平均评分
- `rating_count` - 评分总数

## Web 界面路由

需要登录的页面：

1. **主仪表板** - `http://127.0.0.1:8000/`
   - 显示系统统计信息
   - 最新推荐列表

2. **所有推荐** - `http://127.0.0.1:8000/recommendations/`
   - 分页显示所有推荐
   - 按类型筛选

3. **个性化推荐** - `http://127.0.0.1:8000/personalized/?user_id=1`
   - 查看特定用户的推荐
   - 支持分页

4. **数据管理** - `http://127.0.0.1:8000/data-management/`
   - 上传数据集
   - 触发 Spark 处理
   - 清空数据

## 数据库模型

### Movie (电影)

```python
class Movie(models.Model):
    movie_id = models.IntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=500)
    genres = models.CharField(max_length=200)
    year = models.IntegerField(null=True, blank=True)
    avg_rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
```

### RecommendationData (推荐)

```python
class RecommendationData(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    user_id = models.IntegerField(db_index=True)
    recommendation_score = models.FloatField()  # ALS 预测评分
    popularity_score = models.FloatField()      # 平均评分
```

## 推荐算法说明

### ALS (Alternating Least Squares) 协同过滤

**训练参数**:
- `rank=10` - 隐因子维度
- `maxIter=10` - 最大迭代次数
- `regParam=0.1` - 正则化参数

**模型性能**:
- 训练集: 19,999,838 条评分
- 测试集: 5,000,257 条评分
- **RMSE: 0.8019** （均方根误差）

**推荐逻辑**:
1. 模型学习用户和电影的隐向量表示
2. 对于每个用户，计算其对所有未评分电影的预测评分
3. 返回预测评分最高的 Top-N 电影

## 使用 Python 调用 API

```python
import requests

# 获取用户 1 的前 10 条推荐
response = requests.get('http://127.0.0.1:8000/api/user/1/recommendations/', params={'limit': 10})
data = response.json()

print(f"用户 {data['user_id']} 的推荐:")
for i, rec in enumerate(data['recommendations'], 1):
    print(f"{i}. {rec['title']} - 预测评分: {rec['predicted_rating']}")
```

## 测试用户范围

当前系统包含 **1000 个用户**的推荐数据（User ID: 1-1000）

每个用户有 **10 条推荐**

## 扩展推荐数据

如果需要为更多用户生成推荐：

1. 修改 `movielens_csv_processor.py` 的 `save_results()` 方法：
   ```python
   # 修改采样条件，例如前 5000 个用户
   rec_sample = recommendations.filter(col("userId") <= 5000)
   ```

2. 重新运行训练和导入：
   ```bash
   python spark_jobs\movielens_csv_processor.py
   python import_recommendations.py
   ```

## 常见问题

### Q: 如何添加新用户的推荐？

A: 需要重新训练 ALS 模型，包含新用户的评分数据。单个用户的增量更新需要实现在线学习。

### Q: 推荐结果多久更新一次？

A: 当前为离线批处理模式，需要手动重新训练。可以设置定时任务（cron/celery）自动更新。

### Q: 如何提高推荐准确度？

A: 可以尝试：
1. 调整 ALS 参数（rank, maxIter, regParam）
2. 使用更多训练数据
3. 结合内容过滤（基于类型、年份等）
4. 实现混合推荐系统

### Q: API 为什么不需要认证？

A: `user_recommendations_api` 端点已移除 `@login_required` 装饰器，便于测试和外部调用。生产环境建议添加 API Token 认证。

## 性能优化建议

1. **数据库索引**
   - `user_id` 已建立索引
   - `recommendation_score` 建议添加索引以加速排序

2. **缓存**
   - 使用 Redis 缓存热门推荐
   - 缓存用户推荐结果（减少数据库查询）

3. **分页**
   - API 已支持 `limit` 参数
   - 建议添加 `offset` 参数支持更灵活的分页

## 项目文件结构

```
recommendation_system/
├── spark_jobs/
│   ├── movielens_csv_processor.py     # CSV 数据训练（主要）
│   ├── movielens_hdfs_processor.py    # HDFS 数据训练
│   └── test_*.py                      # 测试脚本
├── app/
│   ├── models.py                      # Django 模型
│   ├── views.py                       # 视图和 API
│   └── urls.py                        # URL 路由
├── output/
│   ├── movie_statistics.csv           # 电影统计
│   └── user_recommendations.csv       # 推荐结果
├── import_recommendations.py          # 导入脚本
└── manage.py                          # Django 管理脚本
```

## 下一步开发

- [ ] 实现实时推荐 API
- [ ] 添加用户评分提交功能
- [ ] 实现混合推荐（协同 + 内容）
- [ ] 添加推荐解释功能
- [ ] 实现 A/B 测试框架
- [ ] 添加推荐效果监控

## 技术栈

- **大数据处理**: Apache Spark 4.0.1 + PySpark
- **机器学习**: MLlib ALS 算法
- **Web 框架**: Django 4.2
- **数据库**: SQLite (开发) / PostgreSQL (生产推荐)
- **数据存储**: Hadoop HDFS, Apache Hive 2.3.2
- **编程语言**: Python 3.11

## 参考文档

- [MovieLens 数据集](https://grouplens.org/datasets/movielens/)
- [Spark MLlib ALS](https://spark.apache.org/docs/latest/ml-collaborative-filtering.html)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

**完成时间**: 2026-01-01
**模型 RMSE**: 0.8019
**推荐数据**: 1000 用户 × 10 条 = 10,000 条
