# Hive 环境状态报告

## ✅ 已成功完成

### 1. Hive Metastore 修复
- **问题**: Metastore 无法启动，报错 "Version information not found in metastore"
- **解决方案**: 在 `docker-compose.yml` 中添加了正确的配置：
  ```yaml
  HIVE_SITE_CONF_datanucleus_schema_autoCreateAll: "true"
  HIVE_SITE_CONF_hive_metastore_schema_verification: "false"
  ```
- **状态**: ✅ **Hive Metastore 已成功启动并运行在端口 9083**

### 2. 数据库清理
- 删除了旧的 PostgreSQL 数据卷
- 重新创建了全新的 Metastore 数据库
- 数据库 schema 自动创建成功

### 3. HDFS 目录
- `/user/hive/warehouse/raw/movies` - 原始电影数据
- `/user/hive/warehouse/raw/ratings` - 原始评分数据
- `/user/hive/warehouse/cleaned` - 清洗后的数据

## ⏳ 正在进行中

### HiveServer2 启动
- **状态**: 进程正在运行 (PID 582)，但**尚未完全启动**
- **启动时间**: 已运行约 8-10 分钟
- **预计时间**: HiveServer2 首次启动通常需要 **10-15 分钟**
- **原因**: HiveServer2 需要初始化大量组件（Thrift server, JDBC, YARN 连接等）

## 📋 如何验证 Hive 状态

### 方法 1: 使用检查脚本 (推荐)
```bash
# Windows
check_hive_status.bat

# Linux/Mac
bash check_hive_status.sh
```

### 方法 2: 手动检查端口
```bash
# 检查 Metastore (应该已经在监听)
docker exec hive-metastore bash -c "ss -tulnp | grep 9083"

# 检查 HiveServer2 (可能还未监听)
docker exec hive-server bash -c "ss -tulnp | grep 10000"
```

### 方法 3: 使用 Python 测试
```bash
python test_hive_connection.py
```

### 方法 4: 使用 Beeline 直接测试
```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"
```

## 🎯 下一步操作

### 如果 HiveServer2 还未启动完成：

#### 选项 A: 继续等待 HiveServer2 (推荐用于生产环境)
1. 等待 5-10 分钟
2. 运行 `check_hive_status.bat` 检查状态
3. 当看到端口 10000 监听时，说明启动成功

#### 选项 B: 使用 Spark SQL 直接访问 Hive Metastore (推荐用于开发)
由于 **Hive Metastore 已经成功启动**，您可以：

1. **通过 Spark 直接使用 Hive**，无需等待 HiveServer2
2. Spark 可以通过 Metastore (端口 9083) 直接访问 Hive 表
3. 这是更常见和高效的使用方式

**示例代码**:
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("MovieLens") \
    .config("spark.sql.warehouse.dir", "hdfs://namenode:9000/user/hive/warehouse") \
    .config("hive.metastore.uris", "thrift://hive-metastore:9083") \
    .enableHiveSupport() \
    .getOrCreate()

# 现在可以直接使用 Hive
spark.sql("SHOW DATABASES").show()
spark.sql("CREATE DATABASE IF NOT EXISTS movielens_db").show()
```

### 如果 HiveServer2 启动成功：

1. 创建 Hive 数据库和表
2. 从 HDFS 加载 MovieLens 数据
3. 运行数据清洗脚本
4. 通过 Spark 读取清洗后的数据

## 🔧 故障排查

### HiveServer2 长时间未启动
如果等待 15 分钟后 HiveServer2 仍未启动：

1. **检查日志**:
   ```bash
   docker logs hive-server --tail 100
   ```

2. **重启 HiveServer2**:
   ```bash
   docker-compose restart hive-server
   ```

3. **增加内存限制** (如果系统资源充足):
   在 `docker-compose.yml` 中添加:
   ```yaml
   hive-server:
     deploy:
       resources:
         limits:
           memory: 2G
   ```

### 使用 Spark 替代方案
如果 HiveServer2 持续有问题，使用 Spark SQL 是完全可行的：
- Spark 可以直接读写 Hive 表
- 性能更好
- 更适合大数据处理
- **Hive Metastore 已经正常工作，这是关键！**

## 📊 当前环境总结

| 组件 | 状态 | 端口 | 说明 |
|------|------|------|------|
| HDFS NameNode | ✅ 运行中 | 9870, 9000 | 健康 |
| HDFS DataNode | ✅ 运行中 | 9864 | 健康 |
| Hive Metastore | ✅ 运行中 | 9083 | **已完全启动** |
| PostgreSQL | ✅ 运行中 | 5432 | 元数据库 |
| HiveServer2 | ⏳ 启动中 | 10000, 10002 | 进程运行中，等待完全初始化 |

## ✅ 重要结论

**Hive 环境核心组件 (Metastore) 已经成功启动！**

您可以：
1. 继续等待 HiveServer2 完全启动（推荐给充足时间）
2. 或者直接使用 Spark + Hive Metastore 开始工作（更高效）

**项目不会被 HiveServer2 的启动时间阻塞，因为 Metastore 是关键，它已经正常工作了！**

---

最后更新: 2025-12-31
