# Group Project Proposal - MovieLens Recommendation System with Hive Data Cleaning

## 📧 Email to Lecturer (Week 9 - 21 Dec 2025)

---

**Subject:** Group Project Proposal - MovieLens Recommendation System with Hive Integration

**Dear Lecturer,**

Please find below our group project proposal for the Big Data Analytics course:

---

## 1️⃣ Group Members

- **Group Leader:** [Your Name] - [Student ID]
- **Member 2:** [Name] - [Student ID]
- **Member 3:** [Name] - [Student ID]
- **Member 4:** [Name] - [Student ID]

*(Please fill in your actual names and student IDs)*

---

## 2️⃣ Project Title

**"Intelligent MovieLens Recommendation System with Distributed Data Cleaning Pipeline Using Apache Hive and Spark"**

**Alternative Title:**
"Building a Scalable Movie Recommendation Engine: Integrating Hive for Data Quality Management and Spark for Real-Time Analytics"

---

## 3️⃣ Problem Statement Identified

### Core Problem: Generating Accurate Movie Recommendations from Large-Scale, Dirty Data

**Problem Context:**

Building an effective movie recommendation system faces a fundamental challenge: **the quality of recommendations is directly dependent on the quality of input data**. The MovieLens-25M dataset, while rich with 25 million user ratings across 62,000+ movies, contains significant data quality issues that corrupt recommendation accuracy.

**The Recommendation Quality Paradox:**

Traditional recommendation systems focus on algorithm sophistication (collaborative filtering, matrix factorization, deep learning) but overlook a critical bottleneck: **garbage in, garbage out**. Specifically:

1. **Dirty Data Corrupts Rating Calculations**
   - **Missing genre information** (~15% of movies): A movie labeled "(no genres listed)" cannot be recommended to users who prefer specific genres
   - **Duplicate ratings**: Same user rates the same movie multiple times → artificially inflates rating counts → biases "popularity score"
   - **Inconsistent title formats**: "Toy Story (1995)" vs "Toy Story" → fails to extract release year → unable to recommend "recent movies"
   - **Orphaned ratings**: Ratings exist for deleted/invalid movieIds → crashes join operations

2. **Computational Scalability Bottleneck**
   - **Single-machine processing fails at scale**: Loading 25M ratings into Pandas/R causes memory overflow (requires >16GB RAM)
   - **Sequential processing is too slow**: Calculating average ratings + applying Bayesian smoothing across 62K movies takes **3-4 hours** on a single core
   - **No incremental updates**: Every new user rating requires **full recomputation** of all recommendations

3. **Data Cleaning Overhead Dominates Workflow**
   - Data scientists spend **60-70% of time** on repetitive cleaning tasks:
     - Manually filtering null values
     - Deduplicating records
     - Parsing irregular text fields
   - **No reusable cleaned dataset**: Every analysis (e.g., genre-based recommendations, trending movies, user segmentation) re-cleans the same raw data
   - **Inconsistent cleaning logic**: Different analysts apply different rules → unreproducible results

**Business Impact:**

| Impact Area | Without Proper Data Management | With Hive + Spark Solution |
|-------------|-------------------------------|---------------------------|
| **Recommendation Accuracy** | 15% of movies excluded due to missing genres → Poor user experience | 98% data completeness → Comprehensive recommendations |
| **Processing Time** | 3-4 hours for full recommendation refresh | 8-10 minutes with distributed processing |
| **System Scalability** | Cannot handle >10M ratings (memory limits) | Scales to 100M+ ratings (horizontal scaling) |
| **Developer Productivity** | 70% time on data cleaning, 30% on algorithm tuning | 20% time on cleaning (one-time), 80% on innovation |

**Why Traditional Solutions Fail:**

- **Excel/CSV processing**: Maximum 1M rows, no parallelism
- **Single-machine Python (Pandas)**: Memory bound, single-threaded aggregations
- **Relational databases (MySQL)**: Not designed for analytical queries across 25M records (slow JOINs)
- **Manual data cleaning**: Error-prone, not reproducible, no version control

**Why Big Data Tools Are Essential:**

This problem **requires distributed computing** because:

1. **Data Volume Exceeds Single-Machine Capacity**
   - 25M ratings + 62K movies = ~2GB raw CSV
   - Intermediate computations (user-item matrix) = 15GB+ in memory
   - **HDFS** enables storage across multiple nodes with fault tolerance

2. **Parallel Processing is Mandatory for Performance**
   - **Hive** executes data cleaning SQL across distributed partitions (10x faster than sequential)
   - **Spark** performs in-memory aggregations across multiple cores (100x faster than Hadoop MapReduce)

3. **Separation of Data Cleaning and Analytics Layers**
   - **Hive** creates a **curated, reusable data layer** (cleaned once, used many times)
   - **Spark** reads pre-cleaned data → focuses on advanced analytics (ML models)
   - Enables **data governance** (centralized quality checks, metadata tracking)

**Proposed Solution Architecture:**

```
Raw Data (25M ratings, quality issues)
    ↓
HDFS (distributed storage)
    ↓
Hive (SQL-based cleaning: dedup, validation, standardization)
    ↓
Cleaned Data Layer (ORC format, partitioned by year/genre)
    ↓
Spark (parallel aggregation + recommendation algorithm)
    ↓
Django Web App (Top-N movie recommendations)
```

**Success Criteria:**

- ✅ **Data Quality**: Reduce missing/invalid records from 15% to <2%
- ✅ **Performance**: Generate top-1000 recommendations in <10 minutes (vs 3 hours baseline)
- ✅ **Accuracy**: Recommendation precision increases by 25% (measured via A/B testing)
- ✅ **Scalability**: Successfully process 100M synthetic ratings (4x current size)
- ✅ **Reusability**: Cleaned dataset used for 3+ different analyses (genre trends, user segmentation, temporal analysis)

---

## 4️⃣ Tool(s) to be Used

### Primary Hadoop Ecosystem Tools

#### 1. Apache Hadoop HDFS (v3.3+)
**Purpose:** Distributed file storage for raw and processed datasets

**Usage in Project:**
- Store raw CSV files (movies.csv, ratings.csv) in `/user/hive/warehouse/raw/`
- Store cleaned ORC-formatted data in `/user/hive/warehouse/cleaned/`
- Enable fault tolerance through replication factor 3

**Why HDFS?**
- Handles large files (1GB+ MovieLens datasets) efficiently
- High throughput for sequential reads (required for batch processing)
- Integrates seamlessly with Hive and Spark

#### 2. Apache Hive (v3.1+)
**Purpose:** Data warehousing and SQL-based data cleaning

**Usage in Project:**

**Phase 1: External Table Creation**
```sql
-- Map raw CSV files to Hive tables
CREATE EXTERNAL TABLE raw_movies (
    movieId INT,
    title STRING,
    genres STRING
)
LOCATION '/user/hive/warehouse/raw/movies/';
```

**Phase 2: Data Quality Checks**
```sql
-- Identify data quality issues
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END) as missing_titles,
    COUNT(DISTINCT movieId) as unique_movies,
    SUM(CASE WHEN genres = '(no genres listed)' THEN 1 ELSE 0 END) as no_genre_count
FROM raw_movies;
```

**Phase 3: Data Cleaning & Transformation**
```sql
-- Create cleaned, optimized table
INSERT OVERWRITE TABLE cleaned_movies PARTITION (decade)
SELECT
    movieId,
    TRIM(title) as title,
    CAST(regexp_extract(title, '\\((\\d{4})\\)', 1) AS INT) as year,
    SPLIT(genres, '\\|') as genres_array,
    FLOOR(CAST(regexp_extract(title, '\\((\\d{4})\\)', 1) AS INT) / 10) * 10 as decade
FROM raw_movies
WHERE movieId IS NOT NULL;
```

**Why Hive?**
- SQL interface lowers barrier for data analysts
- Automatically manages metadata via Metastore
- Supports partitioning for query optimization (10x faster queries)
- ORC/Parquet storage formats reduce storage costs by 75%

#### 3. Apache Spark (v3.4+) with PySpark
**Purpose:** In-memory distributed computing for advanced analytics

**Usage in Project:**

**Connect to Hive Tables:**
```python
spark = SparkSession.builder \
    .appName("MovieLensRecommendation") \
    .enableHiveSupport() \
    .config("hive.metastore.uris", "thrift://localhost:9083") \
    .getOrCreate()

# Read cleaned data from Hive
movies_df = spark.table("cleaned_movies")
ratings_df = spark.table("cleaned_ratings")
```

**Parallel Aggregation:**
```python
# Calculate movie statistics in parallel
movie_stats = ratings_df.groupBy("movieId").agg(
    avg("rating").alias("avg_rating"),
    count("rating").alias("rating_count")
)
```

**Recommendation Algorithm:**
```python
# Bayesian weighted rating
mean_rating = movie_stats.agg(avg("avg_rating")).collect()[0][0]
recommendations = movies_with_stats.withColumn(
    "weighted_score",
    (col("rating_count") / (col("rating_count") + 100)) * col("avg_rating") +
    (100 / (col("rating_count") + 100)) * lit(mean_rating)
).orderBy(desc("weighted_score"))
```

**Why Spark?**
- 100x faster than Hadoop MapReduce for iterative algorithms
- Unified API for batch and streaming processing
- Rich ML library (MLlib) for collaborative filtering

### Secondary Tools (Web Interface & Visualization)

#### 4. Django Web Framework (Python)
**Purpose:** User interface for uploading data and viewing recommendations

**Features:**
- User authentication system
- File upload interface for MovieLens CSV files
- Trigger Hive cleaning jobs via web interface
- Display data quality reports and recommendations

#### 5. SQLite/MySQL Database
**Purpose:** Store final recommendation results for web serving

**Integration:**
- Spark writes aggregated recommendations to Django ORM
- Web queries fetch from relational DB (sub-second response)

---

## 5️⃣ Planned Additional Tools

### Tool 1: Apache Airflow (Workflow Orchestration)
**Purpose:** Automate the entire data pipeline

**Planned DAG Workflow:**
```python
# Daily recommendation update pipeline
upload_to_hdfs >> create_hive_tables >> run_quality_checks >>
clean_data >> run_spark_analysis >> update_django_db >> send_email_report
```

**Benefits:**
- Schedule daily recommendation updates
- Monitor task failures with retry logic
- Visualize pipeline execution via Airflow UI

**Usage Timeline:** Week 13 (integration phase)

---

### Tool 2: Tableau / Power BI (Interactive Visualization)
**Purpose:** Create interactive dashboards for data quality insights

**Planned Visualizations:**

1. **Data Quality Dashboard:**
   - Missing value heatmap by year
   - Duplicate record trends over time
   - Data completeness score (gauge chart)

2. **Recommendation Analytics Dashboard:**
   - Top 10 movies by weighted rating (bar chart)
   - Genre distribution (treemap)
   - Rating trends over decades (line chart)
   - User engagement metrics (KPIs)

3. **Performance Metrics Dashboard:**
   - Spark job execution time trends
   - HDFS storage utilization
   - Hive query performance statistics

**Data Connection:**
- Connect Tableau to Hive via ODBC driver
- Connect to Django MySQL database for real-time metrics

**Benefits:**
- Non-technical stakeholders can explore data
- Drill-down capabilities (e.g., from decade → year → individual movies)
- Exportable reports for presentations

**Usage Timeline:** Week 14 (final report preparation)

---

### Tool 3: Apache Kafka + Spark Streaming (Real-Time Processing)
**Purpose:** Handle real-time user rating submissions

**Architecture:**
```
User submits rating → Django sends to Kafka topic →
Spark Streaming consumes → Update Hive tables →
Recalculate recommendations incrementally
```

**Benefits:**
- Near real-time recommendation updates (< 5 seconds)
- Decouples web layer from processing layer
- Scalable to 10,000+ concurrent users

**Challenges to Address:**
- Exactly-once semantics for rating deduplication
- State management for incremental aggregation

**Usage Timeline:** Week 14 (if time permits, as advanced feature)

---

### Tool 4: Python Libraries for Enhanced Analytics

#### 4.1 Pandas (Data Conversion Layer)
**Purpose:** Bridge between Spark DataFrames and Django ORM
```python
# Convert Spark results to Pandas for Django insertion
recommendations_pandas = recommendations_df.toPandas()
```

#### 4.2 Matplotlib / Seaborn (Static Visualization)
**Purpose:** Generate quality report charts
- Distribution plots for ratings
- Correlation heatmaps
- Before/after cleaning comparison charts

**Output:** PNG files embedded in Django admin dashboard

#### 4.3 Scikit-learn (Machine Learning)
**Purpose:** Content-based filtering complement
- TF-IDF vectorization of movie titles
- Cosine similarity for "similar movies" feature

**Example:**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(movies_df['title'])
similarity_matrix = cosine_similarity(tfidf_matrix)
```

---

### Tool 5: Git + GitHub (Version Control)
**Purpose:** Collaborate on code and Hive scripts

**Repository Structure:**
```
recommendation_system/
├── hive_scripts/        # SQL scripts versioned
├── spark_jobs/          # PySpark applications
├── app/                 # Django web app
├── docs/                # Project documentation
└── tests/               # Unit tests
```

**Benefits:**
- Track changes in data cleaning logic
- Code review process for quality assurance
- Rollback capability if bugs are introduced

---

## 6️⃣ Why These Tools Enhance the Report

### Enhanced Outcome 1: Reproducible Data Lineage
**Without Additional Tools:**
- Manual data cleaning with unclear transformations
- Unable to reproduce results 6 months later

**With Hive + Git:**
- Every SQL script versioned in Git
- Hive Metastore tracks table creation history
- **Report Outcome:** "Data Governance" section demonstrating enterprise-grade practices

---

### Enhanced Outcome 2: Executive-Friendly Insights
**Without Tableau:**
- Static screenshots of terminal outputs
- Non-technical readers confused by technical jargon

**With Tableau/Power BI:**
- Interactive dashboard embedded in final report
- Stakeholders can filter by genre/year themselves
- **Report Outcome:** "Interactive Appendix" with live dashboard link

---

### Enhanced Outcome 3: Real-World Production Readiness
**Without Airflow:**
- Manual execution of scripts (error-prone)
- No monitoring of pipeline health

**With Airflow:**
- Automated daily updates
- Email alerts on failures
- **Report Outcome:** "Production Deployment" section showing industry best practices

---

### Enhanced Outcome 4: Advanced Analytics Showcase
**Without ML Tools:**
- Basic sorting by average rating
- Limited to popularity-based recommendations

**With Scikit-learn + MLlib:**
- Hybrid recommendation system (collaborative + content-based)
- Personalized recommendations using ALS algorithm
- **Report Outcome:** "Machine Learning" section demonstrating technical depth

---

## 7️⃣ Presentation Time Slot

**Preferred Time:** Week 13 to Week 14

**Reason for Preference:**
- Week 13: Allows time to integrate Tableau dashboard
- Week 14: Ensures all advanced features (Airflow, Kafka) are tested

**Presentation Outline (10 minutes):**

1. **Problem Introduction (1 min)**
   - Show real MovieLens data quality issues (screenshots)

2. **Architecture Overview (2 min)**
   - Live demo of data flow diagram
   - Highlight Hadoop ecosystem integration

3. **Live Demo (4 min)**
   - Upload CSV via Django interface
   - Show Hive cleaning execution (terminal output)
   - Display Tableau dashboard with results
   - Show top 10 movie recommendations

4. **Technical Deep Dive (2 min)**
   - Code walkthrough: Hive SQL + PySpark snippet
   - Performance comparison: Before/After optimization

5. **Q&A (1 min)**

---

## 8️⃣ Expected Deliverables

### Week 13-14 Presentation Deliverables:
1. **Live System Demo**
   - Fully functional web interface
   - Executable Hive + Spark pipeline

2. **Slide Deck (PDF)**
   - Architecture diagrams
   - Code snippets with explanations
   - Performance benchmarks

3. **Tableau Dashboard (Published Online)**
   - Shareable link for classmates to explore

### Final Report Sections:
1. **Introduction** (Problem statement expansion)
2. **Literature Review** (Related work on recommendation systems)
3. **System Architecture** (Detailed design with diagrams)
4. **Implementation** (Code explanations, Hive scripts)
5. **Data Quality Analysis** (Before/after cleaning statistics)
6. **Results & Evaluation** (Recommendation accuracy metrics)
7. **Scalability Analysis** (Performance benchmarks with different data sizes)
8. **Production Considerations** (Airflow deployment, monitoring)
9. **Conclusion & Future Work**
10. **Appendices** (Full code, SQL scripts, screenshots)

---

## 9️⃣ Success Metrics

### Technical Metrics:
- **Data Quality Improvement:** Reduce missing values from 15% to <2%
- **Processing Speed:** Clean 25M records in <10 minutes (vs 3 hours baseline)
- **Query Performance:** Generate top-1000 recommendations in <30 seconds
- **Storage Efficiency:** Achieve 75% compression with ORC format

### Demonstration Metrics:
- **System Uptime:** 99% availability during demo week
- **Response Time:** Web interface loads recommendations in <2 seconds
- **Scalability:** Successfully process 100M synthetic ratings (4x original size)

---

## 🔟 Risk Mitigation

### Risk 1: Hive Metastore Configuration Issues
**Mitigation:**
- Set up environment by Week 11 (2-week buffer)
- Use Docker containers for reproducible setup

### Risk 2: Large Dataset Upload Timeouts
**Mitigation:**
- Pre-load MovieLens data into HDFS before presentation
- Prepare backup demo video

### Risk 3: Tableau Dashboard Connectivity
**Mitigation:**
- Export static dashboard as PDF backup
- Test ODBC connection 1 day before presentation

---

## Contact Information

**Group Leader:** [Your Name]
**Email:** [your.email@university.edu]
**Phone:** [Your Phone Number]

We are excited to present this project and demonstrate the power of Hadoop ecosystem tools for real-world data challenges!

**Best regards,**
**[Group Leader Name]**
**[Date]**

---

## Appendix: Quick Reference Links

- **Project GitHub Repository:** [To be created]
- **MovieLens Dataset:** https://grouplens.org/datasets/movielens/25m/
- **Hive Documentation:** https://hive.apache.org/
- **Spark Documentation:** https://spark.apache.org/docs/latest/
- **Airflow Documentation:** https://airflow.apache.org/docs/
