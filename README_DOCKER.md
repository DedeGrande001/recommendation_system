# Docker环境快速启动指南

## 📦 包含的服务

这个Docker Compose配置包含以下服务：

1. **Hadoop HDFS**
   - NameNode (端口 9870, 9000)
   - DataNode

2. **Apache Hive**
   - Metastore (端口 9083)
   - HiveServer2 (端口 10000, 10002)
   - PostgreSQL Metastore数据库

---

## 🚀 快速启动步骤

### 第1步：确保Docker已安装

```bash
# 检查Docker是否安装
docker --version
docker-compose --version
```

如果没有安装：
- 下载 Docker Desktop: https://www.docker.com/products/docker-desktop/
- 安装后重启电脑

---

### 第2步：启动所有服务

在项目根目录 `d:\myproject\project\recommendation_system\` 下执行：

```bash
# 启动所有服务（后台运行）
docker-compose up -d
```

**预期输出：**
```
Creating network "recommendation_system_default" with the default driver
Creating volume "recommendation_system_hadoop_namenode" with default driver
Creating volume "recommendation_system_hadoop_datanode" with default driver
Creating volume "recommendation_system_hive_postgresql_data" with default driver
Creating namenode ... done
Creating hive-metastore-postgresql ... done
Creating datanode ... done
Creating hive-metastore ... done
Creating hive-server ... done
```

**等待时间：** 第一次启动需要下载镜像，大约3-5分钟

---

### 第3步：查看服务状态

```bash
# 查看所有容器运行状态
docker-compose ps
```

**预期输出（所有服务都应该是 "Up"）：**
```
         Name                       Command               State                    Ports
----------------------------------------------------------------------------------------------------------------
datanode                    /entrypoint.sh /run.sh           Up      9864/tcp
hive-metastore              entrypoint.sh /opt/hive/b ...   Up      0.0.0.0:9083->9083/tcp
hive-metastore-postgresql   /docker-entrypoint.sh postgres   Up      5432/tcp
hive-server                 entrypoint.sh /opt/hive/b ...   Up      0.0.0.0:10000->10000/tcp, 0.0.0.0:10002->10002/tcp
namenode                    /entrypoint.sh /run.sh           Up      0.0.0.0:9000->9000/tcp, 0.0.0.0:9870->9870/tcp
```

---

### 第4步：验证环境

#### 4.1 验证HDFS

```bash
# 进入NameNode容器
docker exec -it namenode bash

# 在容器内执行HDFS命令
hdfs dfs -ls /

# 创建测试目录
hdfs dfs -mkdir -p /user/hive/warehouse

# 查看目录
hdfs dfs -ls /user/hive/

# 退出容器
exit
```

**✅ 成功标志：** 能够执行命令且没有报错

#### 4.2 验证Hive

```bash
# 进入Hive Server容器
docker exec -it hive-server bash

# 启动Hive CLI
hive

# 在Hive CLI中执行
hive> SHOW DATABASES;
hive> CREATE DATABASE IF NOT EXISTS movielens_db;
hive> USE movielens_db;
hive> SHOW TABLES;
hive> exit;

# 退出容器
exit
```

**✅ 成功标志：** 能看到 `default` 数据库，能创建新数据库

#### 4.3 访问Web界面

在浏览器中打开：

1. **HDFS NameNode Web UI**
   - URL: http://localhost:9870
   - 可以看到HDFS的存储状态、数据节点信息

2. **HiveServer2 Web UI**
   - URL: http://localhost:10002
   - 可以看到Hive的运行状态

**✅ 成功标志：** 能够打开页面，看到服务运行正常

---

## 📂 HDFS目录结构

建议创建以下目录结构：

```bash
# 执行脚本创建目录
docker exec -it namenode bash -c "
hdfs dfs -mkdir -p /user/hive/warehouse/raw/movies
hdfs dfs -mkdir -p /user/hive/warehouse/raw/ratings
hdfs dfs -mkdir -p /user/hive/warehouse/cleaned
hdfs dfs -chmod -R 777 /user/hive/warehouse
"
```

目录说明：
- `/user/hive/warehouse/raw/movies/` - 存放原始电影CSV文件
- `/user/hive/warehouse/raw/ratings/` - 存放原始评分CSV文件
- `/user/hive/warehouse/cleaned/` - 存放清洗后的数据

---

## 🧪 测试上传数据到HDFS

```bash
# 假设你有一个测试CSV文件 test.csv
# 从Windows主机上传到HDFS

# 方法1: 先复制到容器，再上传到HDFS
docker cp test.csv namenode:/tmp/test.csv
docker exec -it namenode hdfs dfs -put /tmp/test.csv /user/hive/warehouse/raw/

# 方法2: 直接从管道上传（推荐）
cat test.csv | docker exec -i namenode hdfs dfs -put - /user/hive/warehouse/raw/test.csv
```

验证上传：
```bash
docker exec -it namenode hdfs dfs -ls /user/hive/warehouse/raw/
docker exec -it namenode hdfs dfs -cat /user/hive/warehouse/raw/test.csv | head -5
```

---

## 🛠️ 常用管理命令

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs hive-server
docker-compose logs namenode

# 实时跟踪日志
docker-compose logs -f hive-metastore
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart hive-server
```

### 停止服务
```bash
# 停止所有服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除所有（包括数据卷）⚠️ 慎用
docker-compose down -v
```

### 重新启动
```bash
# 如果之前已经启动过，再次启动
docker-compose start

# 或者完全重建
docker-compose up -d --force-recreate
```

---

## 🔧 Python连接配置

### 从本地Python连接Hive

```python
from pyspark.sql import SparkSession

# 创建Spark会话，连接到Docker中的Hive
spark = SparkSession.builder \
    .appName("MovieLensHiveIntegration") \
    .config("spark.sql.warehouse.dir", "hdfs://localhost:9000/user/hive/warehouse") \
    .config("hive.metastore.uris", "thrift://localhost:9083") \
    .enableHiveSupport() \
    .getOrCreate()

# 测试连接
spark.sql("SHOW DATABASES").show()

# 使用数据库
spark.sql("USE movielens_db")

# 查看表
spark.sql("SHOW TABLES").show()
```

### 从Python上传文件到HDFS

```python
import subprocess

def upload_to_hdfs(local_path, hdfs_path):
    """上传本地文件到Docker中的HDFS"""
    cmd = f'docker exec -i namenode hdfs dfs -put - {hdfs_path}'

    with open(local_path, 'rb') as f:
        process = subprocess.Popen(
            cmd.split(),
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

    if process.returncode == 0:
        print(f"✓ 上传成功: {local_path} -> {hdfs_path}")
        return True
    else:
        print(f"✗ 上传失败: {stderr.decode()}")
        return False

# 使用示例
upload_to_hdfs(
    local_path="data/movies.csv",
    hdfs_path="/user/hive/warehouse/raw/movies/movies.csv"
)
```

---

## ❓ 故障排查

### 问题1: 容器启动失败

```bash
# 查看详细日志
docker-compose logs namenode

# 常见原因：端口被占用
# 检查端口占用情况（Windows）
netstat -ano | findstr "9870"
netstat -ano | findstr "9000"
netstat -ano | findstr "9083"

# 解决方法：修改docker-compose.yml中的端口映射
# 例如：将9870改为9871
```

### 问题2: Hive Metastore连接失败

```bash
# 检查Metastore服务是否运行
docker-compose ps hive-metastore

# 查看Metastore日志
docker-compose logs hive-metastore

# 重启Metastore
docker-compose restart hive-metastore
docker-compose restart hive-server
```

### 问题3: HDFS权限拒绝

```bash
# 关闭HDFS权限检查（仅开发环境）
docker exec -it namenode bash -c "
hdfs dfs -chmod -R 777 /user/hive/warehouse
"
```

### 问题4: 磁盘空间不足

```bash
# 查看Docker磁盘使用情况
docker system df

# 清理未使用的镜像和容器
docker system prune -a
```

---

## 📊 性能监控

### 查看HDFS存储状态
```bash
docker exec -it namenode hdfs dfsadmin -report
```

### 查看容器资源使用
```bash
docker stats
```

---

## 🎓 下一步

环境启动成功后，继续以下步骤：

1. ✅ 创建Hive表（见 `hive_scripts/create_tables.hql`）
2. ✅ 上传MovieLens数据到HDFS
3. ✅ 运行数据清洗脚本
4. ✅ 从Spark读取Hive表
5. ✅ 生成推荐结果

---

## 📞 需要帮助？

如果遇到问题：
1. 检查上面的"故障排查"部分
2. 查看日志：`docker-compose logs -f`
3. 确保Docker Desktop正在运行
4. 确保有足够的磁盘空间（至少10GB）

---

**环境配置完成！接下来可以开始开发Hive数据清洗脚本了。** 🎉
