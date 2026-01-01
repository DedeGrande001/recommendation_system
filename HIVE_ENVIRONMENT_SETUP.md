# Hive 环境搭建指南

## 📋 环境需求清单

### 1️⃣ 基础环境要求

#### 操作系统
- **推荐系统:**
  - Linux: Ubuntu 20.04/22.04 或 CentOS 7/8
  - macOS: 10.14+ (Mojave及以上)
  - Windows: Windows 10/11 (需要WSL2)

- **当前你的系统:** Windows (从项目路径判断)
  - ✅ 可行方案1: 使用 **WSL2 (Windows Subsystem for Linux)**
  - ✅ 可行方案2: 使用 **Docker** (最简单)
  - ✅ 可行方案3: 使用虚拟机 (VirtualBox/VMware)

#### 硬件要求
```
最低配置（开发/演示）:
- CPU: 4核心
- 内存: 8GB RAM
- 磁盘: 50GB 可用空间

推荐配置（性能测试）:
- CPU: 8核心
- 内存: 16GB RAM
- 磁盘: 100GB SSD
```

---

## 2️⃣ 核心软件依赖

### A. Java Development Kit (JDK)

**版本要求:** JDK 8 或 JDK 11

**检查现有Java版本:**
```bash
java -version
```

**你的系统已有JDK 21** (从 `movielens_processor.py` 看到):
```python
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-21'
```

**重要提示:**
- ✅ Hive 3.1+ 支持 JDK 11
- ⚠️ JDK 21 可能有兼容性问题
- 建议: 安装 JDK 11 LTS 版本并行使用

**安装JDK 11 (Windows):**
1. 下载: https://adoptium.net/temurin/releases/?version=11
2. 选择 Windows x64 MSI 安装包
3. 安装到: `C:\Program Files\Java\jdk-11`
4. 配置环境变量 (可切换):
   ```bash
   JAVA_HOME=C:\Program Files\Java\jdk-11
   PATH=%JAVA_HOME%\bin;%PATH%
   ```

---

### B. Apache Hadoop (HDFS + YARN)

**版本要求:** Hadoop 3.3.x

**核心组件:**
1. **HDFS** (Hadoop Distributed File System) - 分布式文件存储
2. **YARN** (Yet Another Resource Negotiator) - 资源管理器 (可选，Hive可以不依赖YARN)

**安装方式选择:**

#### 方式1: 使用 Docker (强烈推荐 ⭐⭐⭐⭐⭐)
```bash
# 拉取Hadoop镜像
docker pull apache/hadoop:3.3.6

# 运行Hadoop容器
docker run -d \
  --name hadoop \
  -p 9870:9870 \
  -p 8088:8088 \
  -p 9000:9000 \
  apache/hadoop:3.3.6
```

**优点:**
- 无需复杂配置
- 5分钟即可启动
- 隔离环境，不影响现有系统

#### 方式2: 本地安装 (Windows WSL2)
```bash
# 在WSL2 Ubuntu中执行
wget https://dlcdn.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
tar -xzf hadoop-3.3.6.tar.gz
sudo mv hadoop-3.3.6 /opt/hadoop

# 配置环境变量
echo 'export HADOOP_HOME=/opt/hadoop' >> ~/.bashrc
echo 'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' >> ~/.bashrc
source ~/.bashrc
```

**最小配置文件:**

`$HADOOP_HOME/etc/hadoop/core-site.xml`:
```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
</configuration>
```

`$HADOOP_HOME/etc/hadoop/hdfs-site.xml`:
```xml
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file:///opt/hadoop/data/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file:///opt/hadoop/data/datanode</value>
    </property>
</configuration>
```

**格式化HDFS并启动:**
```bash
# 格式化NameNode (只需执行一次)
hdfs namenode -format

# 启动HDFS
start-dfs.sh

# 验证HDFS运行
hdfs dfs -ls /
```

---

### C. Apache Hive

**版本要求:** Hive 3.1.3

**依赖检查:**
- ✅ Java 8/11 已安装
- ✅ Hadoop HDFS 已运行
- ⚠️ 需要关系型数据库 (存储Metastore)

**安装步骤:**

#### 1. 下载Hive
```bash
wget https://dlcdn.apache.org/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
tar -xzf apache-hive-3.1.3-bin.tar.gz
sudo mv apache-hive-3.1.3-bin /opt/hive
```

#### 2. 配置环境变量
```bash
echo 'export HIVE_HOME=/opt/hive' >> ~/.bashrc
echo 'export PATH=$PATH:$HIVE_HOME/bin' >> ~/.bashrc
source ~/.bashrc
```

#### 3. 配置Hive
创建 `$HIVE_HOME/conf/hive-site.xml`:
```xml
<configuration>
    <!-- HDFS路径配置 -->
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>/user/hive/warehouse</value>
    </property>

    <!-- Metastore数据库配置 (使用Derby内嵌数据库 - 开发环境) -->
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:derby:;databaseName=/opt/hive/metastore_db;create=true</value>
    </property>

    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>org.apache.derby.jdbc.EmbeddedDriver</value>
    </property>

    <!-- Metastore服务配置 -->
    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://localhost:9083</value>
    </property>
</configuration>
```

#### 4. 初始化Metastore数据库
```bash
# 初始化schema (只需执行一次)
schematool -dbType derby -initSchema
```

#### 5. 启动Hive Metastore服务
```bash
# 后台启动Metastore
nohup hive --service metastore &

# 检查服务是否运行
netstat -an | grep 9083
```

---

### D. Metastore 数据库 (重要!)

Hive需要一个关系型数据库存储元数据(表结构、分区信息等)。

#### 选项1: Derby (嵌入式数据库) - 开发环境
**优点:**
- 无需额外安装
- Hive自带
- 配置简单

**缺点:**
- ⚠️ **只支持单用户** (同时只能有一个Hive连接)
- 不适合生产环境

**适用场景:** 个人开发、课程演示 ✅

#### 选项2: MySQL (推荐用于小组项目) ⭐⭐⭐⭐
**优点:**
- 支持多用户并发
- 稳定可靠
- 易于备份

**安装MySQL:**
```bash
# Ubuntu/WSL2
sudo apt update
sudo apt install mysql-server

# 启动MySQL
sudo service mysql start

# 创建Hive专用数据库
mysql -u root -p
CREATE DATABASE hive_metastore;
CREATE USER 'hive'@'localhost' IDENTIFIED BY 'hive_password';
GRANT ALL PRIVILEGES ON hive_metastore.* TO 'hive'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**下载MySQL JDBC驱动:**
```bash
cd /opt/hive/lib
wget https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar
```

**修改 `hive-site.xml`:**
```xml
<property>
    <name>javax.jdo.option.ConnectionURL</name>
    <value>jdbc:mysql://localhost:3306/hive_metastore?useSSL=false</value>
</property>

<property>
    <name>javax.jdo.option.ConnectionDriverName</name>
    <value>com.mysql.cj.jdbc.Driver</value>
</property>

<property>
    <name>javax.jdo.option.ConnectionUserName</name>
    <value>hive</value>
</property>

<property>
    <name>javax.jdo.option.ConnectionPassword</name>
    <value>hive_password</value>
</property>
```

**初始化MySQL Metastore:**
```bash
schematool -dbType mysql -initSchema
```

---

## 3️⃣ Spark 集成 Hive

### 配置 Spark 连接 Hive

#### 1. 复制 Hive 配置到 Spark
```bash
cp $HIVE_HOME/conf/hive-site.xml $SPARK_HOME/conf/
```

#### 2. 在 PySpark 代码中启用 Hive 支持
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("SparkHiveIntegration") \
    .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
    .config("hive.metastore.uris", "thrift://localhost:9083") \
    .enableHiveSupport() \
    .getOrCreate()

# 测试连接
spark.sql("SHOW DATABASES").show()
```

---

## 4️⃣ 快速验证环境

### 完整验证脚本

```bash
#!/bin/bash

echo "=== 环境验证开始 ==="

# 1. 检查Java
echo "1. 检查Java版本..."
java -version

# 2. 检查Hadoop HDFS
echo "2. 检查HDFS..."
hdfs dfs -ls /
if [ $? -eq 0 ]; then
    echo "✅ HDFS运行正常"
else
    echo "❌ HDFS未运行，请执行: start-dfs.sh"
fi

# 3. 检查Hive Metastore
echo "3. 检查Hive Metastore..."
netstat -an | grep 9083
if [ $? -eq 0 ]; then
    echo "✅ Metastore运行正常"
else
    echo "❌ Metastore未运行，请执行: hive --service metastore &"
fi

# 4. 测试Hive CLI
echo "4. 测试Hive..."
hive -e "SHOW DATABASES;"
if [ $? -eq 0 ]; then
    echo "✅ Hive可用"
else
    echo "❌ Hive配置有误"
fi

echo "=== 验证完成 ==="
```

---

## 5️⃣ 推荐方案：Docker Compose 一键部署 (最简单!)

### 为什么推荐Docker?
- ✅ 无需复杂配置
- ✅ 所有组员环境一致
- ✅ 5分钟启动完整环境
- ✅ 不影响现有系统

### 创建 `docker-compose.yml`

```yaml
version: '3'

services:
  # Hadoop NameNode
  namenode:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    container_name: namenode
    ports:
      - "9870:9870"
      - "9000:9000"
    environment:
      - CLUSTER_NAME=hive
    env_file:
      - ./hadoop.env

  # Hadoop DataNode
  datanode:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    container_name: datanode
    depends_on:
      - namenode
    environment:
      - SERVICE_PRECONDITION=namenode:9870
    env_file:
      - ./hadoop.env

  # Hive Metastore 数据库 (PostgreSQL)
  hive-metastore-postgresql:
    image: bde2020/hive-metastore-postgresql:2.3.0
    container_name: hive-metastore-postgresql

  # Hive Metastore 服务
  hive-metastore:
    image: bde2020/hive:2.3.2-postgresql-metastore
    container_name: hive-metastore
    env_file:
      - ./hadoop.env
    environment:
      - SERVICE_PRECONDITION=namenode:9870 datanode:9864 hive-metastore-postgresql:5432
    ports:
      - "9083:9083"
    depends_on:
      - namenode
      - datanode
      - hive-metastore-postgresql

  # Hive Server (可选，提供JDBC/ODBC接口)
  hive-server:
    image: bde2020/hive:2.3.2-postgresql-metastore
    container_name: hive-server
    env_file:
      - ./hadoop.env
    environment:
      - HIVE_CORE_CONF_javax_jdo_option_ConnectionURL=jdbc:postgresql://hive-metastore/metastore
      - SERVICE_PRECONDITION=hive-metastore:9083
    ports:
      - "10000:10000"
    depends_on:
      - hive-metastore
```

### 创建 `hadoop.env`

```bash
CORE_CONF_fs_defaultFS=hdfs://namenode:9000
CORE_CONF_hadoop_http_staticuser_user=root
CORE_CONF_hadoop_proxyuser_hue_hosts=*
CORE_CONF_hadoop_proxyuser_hue_groups=*

HDFS_CONF_dfs_webhdfs_enabled=true
HDFS_CONF_dfs_permissions_enabled=false
HDFS_CONF_dfs_replication=1

YARN_CONF_yarn_log___aggregation___enable=true
YARN_CONF_yarn_resourcemanager_recovery_enabled=true
YARN_CONF_yarn_resourcemanager_store_class=org.apache.hadoop.yarn.server.resourcemanager.recovery.FileSystemRMStateStore
YARN_CONF_yarn_resourcemanager_fs_state___store_uri=/rmstate
YARN_CONF_yarn_nodemanager_remote___app___log___dir=/app-logs
YARN_CONF_yarn_log_server_url=http://historyserver:8188/applicationhistory/logs/
YARN_CONF_yarn_timeline___service_enabled=true
YARN_CONF_yarn_timeline___service_generic___application___history_enabled=true
YARN_CONF_yarn_resourcemanager_system___metrics___publisher_enabled=true
YARN_CONF_yarn_resourcemanager_hostname=resourcemanager
YARN_CONF_yarn_timeline___service_hostname=historyserver
YARN_CONF_yarn_resourcemanager_address=resourcemanager:8032
YARN_CONF_yarn_resourcemanager_scheduler_address=resourcemanager:8030
YARN_CONF_yarn_resourcemanager_resource___tracker_address=resourcemanager:8031
```

### 启动环境

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f hive-metastore

# 进入Hive容器测试
docker exec -it hive-server bash
hive

# 停止所有服务
docker-compose down
```

### 验证部署成功

```bash
# 1. 访问Hadoop Web UI
浏览器打开: http://localhost:9870

# 2. 测试Hive连接
docker exec -it hive-server hive -e "SHOW DATABASES;"

# 3. 从Python连接 (在你的Windows主机上)
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("TestHive") \
    .config("hive.metastore.uris", "thrift://localhost:9083") \
    .enableHiveSupport() \
    .getOrCreate()

spark.sql("SHOW DATABASES").show()
```

---

## 6️⃣ 网络端口清单

确保以下端口未被占用:

| 服务 | 端口 | 用途 |
|-----|------|------|
| HDFS NameNode Web UI | 9870 | 查看HDFS状态 |
| HDFS NameNode IPC | 9000 | HDFS文件操作 |
| Hive Metastore | 9083 | Spark连接Hive |
| Hive Server2 | 10000 | JDBC/ODBC连接 |
| YARN ResourceManager | 8088 | YARN任务监控 |

**检查端口占用 (Windows):**
```cmd
netstat -ano | findstr "9083"
```

---

## 7️⃣ 常见问题解决

### Q1: "Connection refused to Metastore"
**原因:** Metastore服务未启动

**解决:**
```bash
# 检查Metastore进程
ps aux | grep metastore

# 重启Metastore
hive --service metastore &
```

### Q2: "Permission denied" 访问HDFS
**原因:** HDFS权限问题

**解决:**
```bash
# 关闭HDFS权限检查 (仅开发环境)
hdfs dfs -chmod -R 777 /user/hive/warehouse
```

### Q3: Derby "already booted by another instance"
**原因:** Derby只支持单连接

**解决:** 切换到MySQL Metastore (见上面配置)

### Q4: Java版本不兼容
**原因:** JDK版本过高

**解决:**
```bash
# 切换到JDK 11
update-alternatives --config java  # Linux
# 或修改JAVA_HOME环境变量
```

---

## 8️⃣ 推荐学习路径

### Week 9-10: 环境搭建
1. **Day 1-2:** 安装Docker，运行 docker-compose
2. **Day 3-4:** 测试Hive CLI，创建第一个表
3. **Day 5-6:** 配置Spark连接Hive
4. **Day 7:** 完整验证数据流: CSV → HDFS → Hive → Spark

### Week 11: 数据清洗实践
1. 上传MovieLens数据到HDFS
2. 编写Hive SQL清洗脚本
3. 测试数据质量检查查询

---

## 9️⃣ 环境配置总结

### 最简方案 (推荐小组使用) ⭐
```
Docker Compose (所有服务容器化)
    ↓
5分钟启动
    ↓
所有组员环境一致
```

**优点:**
- 最快速(5分钟)
- 最可靠(官方镜像)
- 最易协作(配置文件共享)

### 完整本地安装方案
```
JDK 11
    ↓
Hadoop HDFS
    ↓
MySQL (Metastore)
    ↓
Hive 3.1.3
    ↓
Spark 3.4+
```

**优点:**
- 更深入理解架构
- 更灵活的配置

**缺点:**
- 配置复杂(2-3天)
- 环境差异大

---

## 🔟 下一步行动

### 立即执行 (今天):
1. ✅ 安装 Docker Desktop for Windows
2. ✅ 下载我提供的 `docker-compose.yml`
3. ✅ 运行 `docker-compose up -d`
4. ✅ 验证 Hive 可用: `docker exec -it hive-server hive`

### 本周完成:
1. 测试从Python连接Hive
2. 上传测试数据到HDFS
3. 创建第一个Hive表

---

## 📚 参考资料

- Hive官方文档: https://hive.apache.org/
- Hadoop文档: https://hadoop.apache.org/docs/stable/
- Docker Hive镜像: https://github.com/big-data-europe/docker-hive
- Spark + Hive集成: https://spark.apache.org/docs/latest/sql-data-sources-hive-tables.html

---

**需要帮助?**
如果遇到任何环境配置问题，请告诉我具体的错误信息，我会帮你解决！
