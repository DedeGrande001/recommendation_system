# Distributed Architecture Design Documentation
## MovieLens Recommendation System

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Why Distributed/Parallel Computing is Needed](#why-distributedparallel-computing-is-needed)
3. [Proposed Distributed System Architecture](#proposed-distributed-system-architecture)
4. [Architecture Diagram](#architecture-diagram)
5. [Component Overview and Technical Workflow](#component-overview-and-technical-workflow)
6. [Future AWS Services for Production Deployment](#future-aws-services-for-production-deployment)

---

## 1. Problem Statement

This project addresses the challenge of **real-time movie recommendation generation from large-scale user rating datasets**.

The MovieLens dataset contains millions of user ratings across thousands of movies, requiring:
- Processing of large CSV files (100MB+)
- Statistical aggregation across multiple dimensions
- Real-time recommendation score calculations
- Concurrent user access to recommendation results

Traditional single-machine processing would face bottlenecks in:
- Memory constraints when loading large datasets
- CPU limitations for complex statistical calculations
- Slow I/O operations for file processing
- Poor scalability as dataset size grows

---

## 2. Why Distributed/Parallel Computing is Needed

### 2.1 Data Volume Challenges
The MovieLens dataset includes:
- 27,000+ movies
- 100,000+ ratings
- Multiple CSV files requiring joins and aggregations

Processing this data on a single machine would require:
- High memory consumption (loading entire dataset into RAM)
- Sequential processing leading to long computation times
- Risk of out-of-memory errors

### 2.2 Computational Complexity
The recommendation algorithm requires:
- Calculating average ratings per movie
- Computing rating counts and statistical metrics
- Joining multiple datasets (movies, ratings, tags)
- Sorting and filtering operations across millions of records

These operations benefit from **parallel processing** where data can be partitioned and processed simultaneously across multiple cores or nodes.

### 2.3 Scalability Requirements
As the system scales:
- User base grows (more concurrent requests)
- Dataset size increases (new movies and ratings)
- Real-time processing demands increase

A distributed architecture enables:
- **Horizontal scaling**: Add more processing nodes as needed
- **Fault tolerance**: System continues operating if individual nodes fail
- **Load balancing**: Distribute work evenly across resources

### 2.4 Apache Spark as the Solution
Apache Spark provides:
- **In-memory computing**: 100x faster than traditional MapReduce
- **Lazy evaluation**: Optimizes execution plans before processing
- **DataFrame API**: Efficient distributed data structures
- **Built-in fault tolerance**: Automatically recovers from node failures

---

## 3. Proposed Distributed System Architecture

### 3.1 Architecture Type: **Three-Tier Client-Server with Distributed Data Processing**

The system follows a hybrid architecture combining:
- **Client-Server Model**: Web frontend communicates with Django backend
- **Distributed Computing Layer**: Apache Spark cluster for data processing
- **Microservices Pattern**: Separated concerns (web serving, data processing, database)

### 3.2 System Layers

#### Layer 1: Presentation Layer (Client)
- **Technology**: HTML5, Bootstrap 5, JavaScript
- **Purpose**: User interface for data upload, viewing recommendations
- **Communication**: HTTP/HTTPS requests to application server

#### Layer 2: Application Layer (Server)
- **Technology**: Django 4.2 (Python web framework)
- **Purpose**:
  - User authentication and session management
  - Request routing and business logic
  - API endpoints for frontend communication
  - Trigger Spark job execution
- **Components**:
  - Views (request handlers)
  - Models (database ORM)
  - Forms (data validation)
  - URL routing

#### Layer 3: Distributed Processing Layer
- **Technology**: Apache Spark 3.x with PySpark
- **Purpose**: Parallel data processing and transformation
- **Operations**:
  - Distributed file reading (CSV parsing)
  - Parallel aggregations (groupBy, agg)
  - Distributed joins (movies + ratings)
  - Statistical computations (mean, count, variance)
- **Execution Mode**: Standalone mode (can scale to YARN/Mesos in production)

#### Layer 4: Data Persistence Layer
- **Technology**: SQLite (development) / MySQL (production-ready)
- **Purpose**:
  - Store processed movie metadata
  - Store recommendation results
  - Persist user accounts and sessions
- **Access Pattern**: ORM-based queries through Django

### 3.3 Data Flow Architecture

```
User Upload → Django File Handler → Spark Cluster
                                        ↓
                                   [Partition 1] [Partition 2] [Partition 3]
                                        ↓
                                   Parallel Processing
                                        ↓
                                   Aggregate Results
                                        ↓
Django ORM ← Database Write ← Spark Output
    ↓
Web Response → User Dashboard
```

---

## 4. Architecture Diagram

### 4.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Browser  │  │ Browser  │  │ Browser  │  │ Browser  │       │
│  │  User 1  │  │  User 2  │  │  User 3  │  │  User N  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                          │                                       │
│                    HTTP/HTTPS                                    │
└──────────────────────────┼──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Application Server Layer                       │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Django Web Framework                         │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │ │
│  │  │  Views  │  │  Models │  │  Forms  │  │   URLs  │     │ │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘     │ │
│  │       └────────────┴────────────┴────────────┘           │ │
│  └───────────────────────┬───────────────────────────────────┘ │
│                          │                                      │
│  ┌───────────────────────┼───────────────────────────────────┐ │
│  │  Background Task Manager (Threading)                      │ │
│  │  • Subprocess spawner for Spark jobs                      │ │
│  │  • Asynchronous execution                                 │ │
│  └───────────────────────┬───────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│             Distributed Processing Layer (Apache Spark)          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Spark Driver                           │ │
│  │  • Task scheduler                                         │ │
│  │  • DAG optimizer                                          │ │
│  │  • Resource manager                                       │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                          │
│       ┌──────────────┼──────────────┐                          │
│       ↓              ↓              ↓                          │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                     │
│  │Executor │   │Executor │   │Executor │                     │
│  │  Core 1 │   │  Core 2 │   │  Core 3 │                     │
│  │         │   │         │   │         │                     │
│  │ Task 1  │   │ Task 2  │   │ Task 3  │                     │
│  │ Task 4  │   │ Task 5  │   │ Task 6  │                     │
│  └────┬────┘   └────┬────┘   └────┬────┘                     │
│       │             │             │                            │
│       └─────────────┴─────────────┘                            │
│                     │                                          │
│            Parallel Processing                                 │
│                     ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Processing Operations:                                   │ │
│  │  • Read CSV files (distributed)                           │ │
│  │  • Parse and clean data                                   │ │
│  │  • Group by movie_id (parallel grouping)                  │ │
│  │  • Calculate aggregates (avg rating, count)               │ │
│  │  • Join datasets (broadcast join)                         │ │
│  │  • Sort by recommendation score                           │ │
│  └───────────────────────┬───────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Data Persistence Layer                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Relational Database (MySQL/SQLite)           │ │
│  │                                                           │ │
│  │  Tables:                                                  │ │
│  │  • app_movie (movie metadata + statistics)               │ │
│  │  • app_recommendationdata (recommendation scores)        │ │
│  │  • app_rawdataset (uploaded files tracking)              │ │
│  │  • auth_user (user accounts)                             │ │
│  │                                                           │ │
│  │  Indexes: movie_id, recommendation_score, user_id        │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Processing Workflow Diagram

```
┌──────────────┐
│ User Uploads │
│  CSV File    │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ Django receives file                     │
│ • Saves to /data directory               │
│ • Creates RawDataset record              │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ User clicks "Process MovieLens Data"     │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ Django spawns background Spark job       │
│ • subprocess.Popen()                     │
│ • No blocking, returns immediately       │
└──────┬───────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────────────────┐
│              Spark Job Execution (spark_to_django.py)      │
│                                                            │
│  Step 1: Initialize Spark Session                         │
│  ┌──────────────────────────────────────┐                │
│  │ spark = SparkSession.builder         │                │
│  │   .appName("MovieLensProcessor")     │                │
│  │   .config("spark.driver.memory","2g")│                │
│  │   .getOrCreate()                     │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 2: Distributed File Reading                         │
│  ┌──────────────────────────────────────┐                │
│  │ ratings_df = spark.read.csv(         │                │
│  │   "data/ratings.csv",                │                │
│  │   header=True,                       │                │
│  │   inferSchema=True                   │                │
│  │ )                                    │                │
│  │ • Data partitioned across executors  │                │
│  │ • Parallel parsing                   │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 3: Data Cleaning (Distributed)                      │
│  ┌──────────────────────────────────────┐                │
│  │ ratings_df = ratings_df.filter(      │                │
│  │   col("rating").isNotNull()          │                │
│  │ )                                    │                │
│  │ • Filter applied in parallel         │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 4: Parallel Aggregation                             │
│  ┌──────────────────────────────────────┐                │
│  │ movie_stats = ratings_df.groupBy(    │                │
│  │   "movieId"                          │                │
│  │ ).agg(                               │                │
│  │   avg("rating").alias("avg_rating"), │                │
│  │   count("rating").alias("count")     │                │
│  │ )                                    │                │
│  │                                      │                │
│  │ Partition 1: Movies 1-1000           │                │
│  │ Partition 2: Movies 1001-2000        │                │
│  │ Partition 3: Movies 2001-3000        │                │
│  │         ↓                            │                │
│  │   Parallel compute avg & count       │                │
│  │         ↓                            │                │
│  │   Shuffle & combine results          │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 5: Distributed Join                                 │
│  ┌──────────────────────────────────────┐                │
│  │ result = movies_df.join(             │                │
│  │   movie_stats,                       │                │
│  │   movies_df.movieId ==               │                │
│  │   movie_stats.movieId,               │                │
│  │   "left"                             │                │
│  │ )                                    │                │
│  │ • Broadcast join for small table     │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 6: Calculate Recommendation Score                   │
│  ┌──────────────────────────────────────┐                │
│  │ result = result.withColumn(          │                │
│  │   "rec_score",                       │                │
│  │   col("avg_rating") * 0.7 +          │                │
│  │   log(col("count") + 1) * 0.3        │                │
│  │ )                                    │                │
│  │ • Applied in parallel to all rows    │                │
│  └──────────────────┬───────────────────┘                │
│                     ↓                                      │
│  Step 7: Sort and Collect                                 │
│  ┌──────────────────────────────────────┐                │
│  │ final_df = result.orderBy(           │                │
│  │   col("rec_score").desc()            │                │
│  │ ).limit(1000)                        │                │
│  │                                      │                │
│  │ • Distributed sort                   │                │
│  │ • Top-K optimization                 │                │
│  └──────────────────┬───────────────────┘                │
└────────────────────┼────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────┐
│ Write Results to Database                │
│ • Django ORM: Movie.objects.create()     │
│ • Batch insert for performance           │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ User views results on Dashboard          │
│ • Top recommendations displayed           │
│ • Statistics shown (count, avg rating)   │
└──────────────────────────────────────────┘
```

### 4.3 Parallel Processing Visualization

```
CSV File (100MB)
       ↓
┌──────────────────────────────────────────┐
│     Spark partitions data into chunks    │
└──────────────────────────────────────────┘
       ↓
┌─────────────┬─────────────┬─────────────┐
│ Partition 1 │ Partition 2 │ Partition 3 │
│  (33MB)     │  (33MB)     │  (34MB)     │
└─────┬───────┴─────┬───────┴─────┬───────┘
      │             │             │
      ↓             ↓             ↓
┌─────────────┬─────────────┬─────────────┐
│ Executor 1  │ Executor 2  │ Executor 3  │
│ CPU Core 1  │ CPU Core 2  │ CPU Core 3  │
│             │             │             │
│ • Parse CSV │ • Parse CSV │ • Parse CSV │
│ • Filter    │ • Filter    │ • Filter    │
│ • Aggregate │ • Aggregate │ • Aggregate │
└─────┬───────┴─────┬───────┴─────┬───────┘
      │             │             │
      └─────────────┴─────────────┘
                    ↓
        ┌───────────────────────┐
        │  Shuffle & Combine    │
        │  (Distributed merge)  │
        └───────────┬───────────┘
                    ↓
            ┌───────────────┐
            │ Final Result  │
            └───────────────┘
```

**For full architecture diagram, please refer to the accompanying Draw.io file: `architecture_diagram.drawio`**

---

## 5. Component Overview and Technical Workflow

### 5.1 Frontend Components

#### User Interface (HTML/Bootstrap)
- **Dashboard Page** (`dashboard.html`): Displays system statistics and overview
- **Recommendations Page** (`recommendations.html`): Shows paginated movie recommendations
- **Data Management Page** (`data_management.html`): File upload interface and dataset management
- **Authentication Pages**: Login and registration forms

#### JavaScript Components
- **Progress Bar**: Real-time feedback during Spark processing
- **AJAX Calls**: Asynchronous communication with backend
- **Form Validation**: Client-side input checking

### 5.2 Backend Components (Django)

#### Views (Request Handlers)
```python
# Main view functions
- login_view()          # User authentication
- dashboard_view()      # Homepage with statistics
- data_management_view() # File upload handling
- process_movielens_view() # Trigger Spark job
- recommendations_view() # Display results
- delete_dataset_view() # Remove datasets
```

#### Models (Database Schema)
```python
# Django ORM models
class Movie:
    movie_id         # Primary key
    title           # Movie name
    year            # Release year
    genres          # Genre list
    avg_rating      # Average rating (from Spark)
    rating_count    # Number of ratings

class RecommendationData:
    movie           # Foreign key to Movie
    recommendation_score  # Calculated score

class RawDataset:
    data_file       # Uploaded file path
    upload_date     # Timestamp
    processed       # Boolean flag
```

#### Background Task Execution
```python
# Threading for non-blocking Spark execution
thread = threading.Thread(
    target=run_spark,
    daemon=True
)
thread.start()
# Returns immediately, user doesn't wait
```

### 5.3 Distributed Processing Components (Spark)

#### Data Cleaning Module (`data_cleaner.py`)
```python
class DataCleaner:
    def clean_ratings(df):
        # Remove null values
        # Filter invalid ratings
        # Standardize formats

    def clean_movies(df):
        # Parse year from title
        # Normalize genres
        # Remove duplicates
```

#### Processing Pipeline (`spark_to_django.py`)

**Phase 1: Initialization**
```python
spark = SparkSession.builder \
    .appName("MovieLensProcessor") \
    .config("spark.driver.memory", "2g") \
    .config("spark.executor.memory", "1g") \
    .getOrCreate()
```

**Phase 2: Distributed Reading**
```python
# Spark automatically partitions the file
ratings_df = spark.read.csv(
    "data/ratings.csv",
    header=True,
    inferSchema=True
)
# Data is now distributed across cluster
```

**Phase 3: Parallel Transformations**
```python
# Each executor processes its partition independently
movie_stats = ratings_df.groupBy("movieId").agg(
    avg("rating").alias("avg_rating"),
    count("rating").alias("rating_count"),
    stddev("rating").alias("rating_stddev")
)
# groupBy triggers shuffle operation
# Aggregations run in parallel
```

**Phase 4: Distributed Join**
```python
# Broadcast join for small datasets
result = movies_df.join(
    broadcast(movie_stats),
    "movieId",
    "left"
)
# Small table replicated to all executors
```

**Phase 5: Complex Calculations**
```python
# Recommendation score formula (parallel execution)
result = result.withColumn(
    "recommendation_score",
    (col("avg_rating") * 0.7 +
     log(col("rating_count") + 1) * 0.3)
)
# Applied to each row in parallel
```

**Phase 6: Database Write**
```python
# Collect results and write to Django database
for row in final_df.collect():
    Movie.objects.create(
        movie_id=row.movieId,
        title=row.title,
        avg_rating=row.avg_rating,
        rating_count=row.rating_count
    )
```

### 5.4 Database Components

#### Schema Design
```sql
-- Movies table (processed data)
CREATE TABLE app_movie (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER UNIQUE,
    title VARCHAR(500),
    year INTEGER,
    genres VARCHAR(200),
    avg_rating DECIMAL(3,2),
    rating_count INTEGER,
    INDEX idx_movie_id (movie_id)
);

-- Recommendations table
CREATE TABLE app_recommendationdata (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER,
    recommendation_score DECIMAL(5,3),
    FOREIGN KEY (movie_id) REFERENCES app_movie(id),
    INDEX idx_score (recommendation_score)
);
```

### 5.5 Technical Workflow Summary

1. **User uploads CSV** → Django saves file to `/data` directory
2. **User triggers processing** → Django spawns background Spark job
3. **Spark initializes** → Creates distributed execution environment
4. **Data ingestion** → CSV loaded and partitioned across executors
5. **Parallel processing** → Each partition processed independently
6. **Shuffle & aggregate** → Results combined across partitions
7. **Join operations** → Multiple datasets merged efficiently
8. **Score calculation** → Recommendation algorithm applied in parallel
9. **Result collection** → Top recommendations gathered
10. **Database write** → Django ORM stores results in MySQL
11. **User views results** → Dashboard displays recommendations with pagination

---

## 6. Future AWS Services for Production Deployment

### 6.1 Compute Services

#### Amazon EMR (Elastic MapReduce)
**Purpose**: Managed Spark cluster for production workloads

**Benefits**:
- Auto-scaling: Add/remove nodes based on workload
- Managed service: AWS handles cluster setup, monitoring, patching
- Integration with S3, DynamoDB, Redshift
- Cost optimization: Spot instances for non-critical tasks

**Implementation**:
```python
# EMR cluster configuration
{
    "Name": "MovieLens-Processor",
    "ReleaseLabel": "emr-6.10.0",
    "Applications": [{"Name": "Spark"}],
    "Instances": {
        "MasterInstanceType": "m5.xlarge",
        "SlaveInstanceType": "m5.2xlarge",
        "InstanceCount": 5,
        "Ec2KeyName": "key-pair",
        "KeepJobFlowAliveWhenNoSteps": True
    }
}
```

#### AWS Lambda
**Purpose**: Serverless function for triggering Spark jobs

**Use Case**: User uploads file → Lambda triggers EMR step → Returns immediately

**Benefits**:
- No server management
- Pay per execution
- Automatic scaling

#### EC2 Auto Scaling Group
**Purpose**: Host Django application servers

**Configuration**:
- Min instances: 2 (high availability)
- Max instances: 10 (handle traffic spikes)
- Scaling policy: CPU > 70% → add instance

### 6.2 Storage Services

#### Amazon S3 (Simple Storage Service)
**Purpose**: Distributed file storage for datasets

**Use Case**:
- Store uploaded CSV files
- Store processed results
- Archive historical data

**Benefits**:
- 99.999999999% durability
- Unlimited storage
- Lifecycle policies (auto-archive old data)
- Integration with Spark (read directly from S3)

**Implementation**:
```python
# Spark reads from S3
ratings_df = spark.read.csv(
    "s3://movielens-bucket/data/ratings.csv",
    header=True,
    inferSchema=True
)
```

#### Amazon EFS (Elastic File System)
**Purpose**: Shared filesystem for multiple EC2 instances

**Use Case**: Django application servers share static files, media uploads

### 6.3 Database Services

#### Amazon RDS (Relational Database Service)
**Purpose**: Managed MySQL/PostgreSQL for production

**Benefits**:
- Automated backups
- Multi-AZ deployment (high availability)
- Read replicas (scale read operations)
- Automatic failover

**Configuration**:
```yaml
DB Instance: db.r5.large
Storage: 500 GB SSD
Multi-AZ: Enabled
Backup Retention: 7 days
Read Replicas: 2
```

#### Amazon DynamoDB
**Purpose**: NoSQL database for high-velocity writes

**Use Case**: Store real-time user interactions, session data

**Benefits**:
- Single-digit millisecond latency
- Automatic scaling
- Pay per request

#### Amazon ElastiCache (Redis)
**Purpose**: In-memory caching for recommendation results

**Benefits**:
- Sub-millisecond response times
- Reduce database load
- Session storage for Django

**Implementation**:
```python
# Cache recommendations in Redis
import redis
cache = redis.Redis(host='elasticache-endpoint')
cache.set('top_movies', json.dumps(recommendations))
# Expire after 1 hour
cache.expire('top_movies', 3600)
```

### 6.4 Networking & Load Balancing

#### Elastic Load Balancer (ELB)
**Purpose**: Distribute traffic across Django servers

**Type**: Application Load Balancer (ALB) for HTTP/HTTPS

**Features**:
- Health checks
- SSL/TLS termination
- Path-based routing

#### Amazon CloudFront
**Purpose**: CDN for static assets (CSS, JS, images)

**Benefits**:
- Global edge locations
- Reduce latency
- DDoS protection

#### Amazon VPC (Virtual Private Cloud)
**Purpose**: Isolated network for security

**Architecture**:
```
Public Subnet: Load Balancer, NAT Gateway
Private Subnet: Django servers, Spark cluster
Database Subnet: RDS instances (no internet access)
```

### 6.5 Analytics & Monitoring

#### Amazon CloudWatch
**Purpose**: Monitoring and logging

**Metrics**:
- EC2 CPU, memory, disk usage
- EMR job success/failure rates
- RDS connections, queries per second
- Custom metrics: recommendation generation time

**Alarms**:
- Email notification if error rate > 5%
- Auto-scaling trigger if CPU > 70%

#### AWS Glue
**Purpose**: ETL service for data cataloging

**Use Case**: Automatically discover and catalog uploaded datasets

#### Amazon Athena
**Purpose**: SQL queries on S3 data

**Use Case**: Ad-hoc analysis of historical recommendations without loading into database

### 6.6 Security Services

#### AWS IAM (Identity and Access Management)
**Purpose**: Fine-grained access control

**Policies**:
```json
{
    "Effect": "Allow",
    "Action": [
        "s3:GetObject",
        "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::movielens-bucket/*"
}
```

#### AWS Secrets Manager
**Purpose**: Store database credentials, API keys

**Benefits**:
- Automatic rotation
- Encrypted storage
- Audit logging

#### AWS WAF (Web Application Firewall)
**Purpose**: Protect against SQL injection, XSS attacks

### 6.7 Deployment & CI/CD

#### AWS CodePipeline
**Purpose**: Automated deployment pipeline

**Workflow**:
```
GitHub Push → CodeBuild → Run Tests →
CodeDeploy → Update EC2 instances →
Healthcheck → Success/Rollback
```

#### AWS Elastic Beanstalk
**Purpose**: Platform-as-a-Service for Django

**Benefits**:
- Auto-scaling
- Load balancing
- Monitoring
- Zero-downtime deployments

### 6.8 Machine Learning Enhancement

#### Amazon SageMaker
**Purpose**: Train advanced recommendation models

**Use Case**: Replace simple score calculation with collaborative filtering or neural networks

**Workflow**:
```
EMR processes data → S3 stores features →
SageMaker trains model → Deploy as endpoint →
Django calls endpoint for predictions
```

### 6.9 Cost Optimization Services

#### AWS Cost Explorer
**Purpose**: Analyze spending patterns

#### EC2 Spot Instances
**Purpose**: 70-90% cost reduction for Spark workers

**Implementation**: Use spot instances for EMR task nodes (not master/core nodes)

#### S3 Intelligent-Tiering
**Purpose**: Auto-move infrequently accessed data to cheaper storage

### 6.10 Complete AWS Architecture Diagram

```
                          Internet
                             ↓
                    ┌────────────────┐
                    │  Route 53 DNS  │
                    └────────┬───────┘
                             ↓
                    ┌────────────────┐
                    │  CloudFront    │
                    │  (CDN)         │
                    └────────┬───────┘
                             ↓
┌────────────────────────────────────────────────────────┐
│                        AWS VPC                         │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │           Public Subnet (AZ-1)                  │  │
│  │  ┌─────────────────┐                            │  │
│  │  │ Application     │                            │  │
│  │  │ Load Balancer   │                            │  │
│  │  └────────┬────────┘                            │  │
│  └───────────┼──────────────────────────────────────┘  │
│              ↓                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │         Private Subnet (Django Servers)         │  │
│  │                                                 │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  │  │
│  │  │ EC2       │  │ EC2       │  │ EC2       │  │  │
│  │  │ Django 1  │  │ Django 2  │  │ Django N  │  │  │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │  │
│  └────────┼──────────────┼──────────────┼─────────┘  │
│           │              │              │            │
│           └──────────────┴──────────────┘            │
│                          ↓                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │        Private Subnet (Database)                │  │
│  │                                                 │  │
│  │  ┌─────────────────────────────────────┐       │  │
│  │  │  RDS MySQL (Multi-AZ)               │       │  │
│  │  │  Master: us-east-1a                 │       │  │
│  │  │  Standby: us-east-1b                │       │  │
│  │  └─────────────────────────────────────┘       │  │
│  │                                                 │  │
│  │  ┌─────────────────────────────────────┐       │  │
│  │  │  ElastiCache Redis Cluster          │       │  │
│  │  └─────────────────────────────────────┘       │  │
│  └─────────────────────────────────────────────────┘  │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │        Private Subnet (EMR Spark Cluster)       │  │
│  │                                                 │  │
│  │  ┌──────────┐                                   │  │
│  │  │ Master   │                                   │  │
│  │  │ m5.xlarge│                                   │  │
│  │  └────┬─────┘                                   │  │
│  │       │                                         │  │
│  │  ┌────┴──────────────────┐                     │  │
│  │  ↓         ↓         ↓         ↓               │  │
│  │ ┌────┐  ┌────┐  ┌────┐  ┌────┐                │  │
│  │ │Core│  │Core│  │Task│  │Task│                │  │
│  │ │ m5 │  │ m5 │  │ m5 │  │ m5 │                │  │
│  │ │.2xl│  │.2xl│  │.2xl│  │.2xl│                │  │
│  │ └────┘  └────┘  └────┘  └────┘                │  │
│  │              (Spot Instances)                   │  │
│  └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                             ↓
                  ┌──────────────────────┐
                  │      Amazon S3       │
                  │  movielens-bucket    │
                  │  • /data/uploads     │
                  │  • /data/processed   │
                  │  • /static-assets    │
                  └──────────────────────┘
                             ↓
                  ┌──────────────────────┐
                  │    AWS Glue          │
                  │  Data Catalog        │
                  └──────────────────────┘
```

### 6.11 Estimated AWS Cost (Monthly)

**Small Scale (Development)**:
- EC2 (t3.medium × 2): $60
- RDS (db.t3.small): $50
- S3 (100GB): $3
- Total: ~$113/month

**Medium Scale (Production)**:
- EC2 Auto Scaling (m5.large × 5): $450
- EMR Cluster (on-demand 10hrs/day): $300
- RDS (db.r5.large Multi-AZ): $400
- ElastiCache (cache.m5.large): $150
- S3 (1TB): $23
- CloudFront: $50
- Load Balancer: $20
- Total: ~$1,393/month

**Large Scale (High Traffic)**:
- EC2 Auto Scaling (c5.2xlarge × 20): $3,600
- EMR Cluster (24/7): $2,500
- RDS (db.r5.4xlarge Multi-AZ): $2,800
- ElastiCache Cluster (3 nodes): $800
- S3 (10TB): $230
- CloudFront: $500
- Total: ~$10,430/month

---

## Conclusion

This distributed architecture provides:
- **Scalability**: Handle datasets from MB to TB scale
- **Performance**: Process millions of records in minutes
- **Reliability**: Fault tolerance through Spark's resilience
- **Maintainability**: Clear separation of concerns
- **Cost Efficiency**: AWS services enable pay-as-you-grow model

The system demonstrates real-world application of distributed computing principles for solving data-intensive recommendation problems.
