# MovieLens Recommendation System - Setup Guide

## Project Overview

This is a distributed movie recommendation system built with **Django 4.2** and **Apache Spark 3.x** that processes the **MovieLens 25M dataset** (25 million ratings, 62,000+ movies).

### Key Features

- User authentication (login/register)
- Apache Spark distributed data processing
- Movie recommendation algorithm (rating-based with popularity weighting)
- Web-based data management interface
- Real-time progress tracking for Spark jobs
- Responsive Bootstrap 5 UI with glass-morphism design
- SQLite database (development) / MySQL-ready (production)

---

## System Requirements

### Software Requirements

**Required:**
- Python 3.8 or higher
- Java 8 or 11 (required for Apache Spark)
- pip (Python package manager)

**Optional (for production):**
- MySQL 8.0+ (currently uses SQLite for development)

### Hardware Requirements (Minimum)

- CPU: 4 cores recommended
- RAM: 8GB minimum (16GB recommended for large datasets)
- Disk: 10GB free space
- OS: Windows, macOS, or Linux

### Check Java Installation

Spark requires Java. Verify installation:

```bash
java -version
```

Expected output:
```
java version "1.8.0" or higher
```

If Java is not installed, download from:
- [OpenJDK](https://adoptium.net/)
- [Oracle JDK](https://www.oracle.com/java/technologies/downloads/)

---

## Installation Steps

### Step 1: Install Python Dependencies

Navigate to the project directory and install required packages:

```bash
cd recommendation_system
pip install -r requirements.txt
```

**Key dependencies:**
- Django 4.2 - Web framework
- PySpark 3.5 - Distributed computing
- pandas, numpy - Data manipulation
- SQLite (included with Python)

### Step 2: Initialize Database

Run Django migrations to create database tables:

```bash
python manage.py migrate
```

This creates a SQLite database file: `db.sqlite3`

### Step 3: Create Admin User

Create a superuser account for accessing the system:

```bash
python manage.py createsuperuser
```

Enter the following when prompted:
- Username: `admin` (or your choice)
- Email: (can be left blank or use test@example.com)
- Password: `admin123` (or your choice)

**Important:** Remember these credentials for logging in.

### Step 4: Download MovieLens Dataset

The system requires the MovieLens 25M dataset.

**Option A: Download Manually**

1. Visit: https://grouplens.org/datasets/movielens/25m/
2. Download the `ml-25m.zip` file (~265 MB)
3. Extract to: `recommendation_system/data/archive/ml-25m/`

**Option B: Use Direct Link (if available)**

```bash
# Navigate to data directory
cd data/archive

# Download and extract
curl -O https://files.grouplens.org/datasets/movielens/ml-25m.zip
unzip ml-25m.zip
```

**Expected file structure:**
```
data/
└── archive/
    └── ml-25m/
        ├── movies.csv       (62,423 movies)
        ├── ratings.csv      (25,000,095 ratings)
        ├── tags.csv
        ├── genome-scores.csv
        └── links.csv
```

---

## Running the System

### Start Django Development Server

```bash
python manage.py runserver
```

Expected output:
```
System check identified no issues (0 silenced).
Django version 4.2, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
```

### Access the Application

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

You will be redirected to the login page.

---

## Using the System

### 1. Login

- Navigate to http://127.0.0.1:8000/login
- Enter the admin credentials you created earlier
- Click "Login"

### 2. Dashboard Overview

After login, you'll see the main dashboard with:
- **Total Movies** - Number of movies in database
- **Total Recommendations** - Number of generated recommendations
- **Latest Recommendations** - Top 10 recommended movies

### 3. Process MovieLens Data with Spark

**Important:** You must process the data before you can view recommendations.

#### Step-by-Step:

1. **Navigate to Data Management**
   - Click "Data Management" in the navigation bar
   - URL: http://127.0.0.1:8000/data-management/

2. **Initiate Spark Processing**
   - Click the "Process MovieLens Data" button
   - Confirm the action in the popup dialog

3. **Monitor Progress**
   - A progress bar will appear showing processing status
   - Status messages include:
     - "Initializing Spark environment..."
     - "Reading MovieLens dataset..."
     - "Calculating movie statistics..."
     - "Generating recommendations..."
     - "Saving to database..."

4. **Wait for Completion**
   - Processing typically takes 2-5 minutes depending on system performance
   - For the full 25M dataset, it may take up to 10 minutes
   - The page will automatically refresh when complete

5. **View Results**
   - After processing, navigate to "Recommendations" page
   - You'll see a paginated list of recommended movies

### 4. View Recommendations

Navigate to http://127.0.0.1:8000/recommendations/

**Information displayed:**
- Movie ID
- Title (with year extracted)
- Genres
- Average Rating (1.0 - 5.0)
- Rating Count (number of users who rated)
- Recommendation Score (calculated value)

**Features:**
- Pagination (shows 50 movies per page)
- Sortable columns
- Responsive design

### 5. Upload Custom Datasets (Optional)

You can also upload your own CSV files:

1. Go to "Data Management"
2. Use the file upload form
3. Select a CSV file (must contain movie/rating data)
4. Click "Upload Dataset"
5. Process the uploaded file using the "Process with Spark" button

### 6. Clear All Data

**Warning:** This permanently deletes all processed data!

To clear all movies and recommendations:
1. Go to "Data Management"
2. Scroll to "Dangerous Operation" section
3. Click "Clear All Data"
4. Confirm the action

This is useful when you want to reprocess the dataset with different parameters.

---

## Understanding the Recommendation Algorithm

### Algorithm: Weighted Rating Score

The system uses a hybrid approach combining:
1. Average rating quality
2. Rating count (popularity)

**Formula:**
```
recommendation_score = (avg_rating * 0.7) + (log(rating_count + 1) * 0.3)
```

**Components:**
- `avg_rating`: Mean of all user ratings (0.5 - 5.0)
- `rating_count`: Number of ratings received
- `log(rating_count + 1)`: Logarithmic scaling to prevent popularity bias

**Why this works:**
- Movies with high ratings but few reviews get balanced scores
- Very popular movies get a boost from rating count
- Logarithm prevents blockbusters from dominating entirely
- 70/30 weighting favors quality over quantity

### Data Processing Pipeline

1. **Data Ingestion (Spark)**
   - Read `movies.csv` and `ratings.csv` from disk
   - Partition data across available CPU cores

2. **Data Cleaning**
   - Remove null values
   - Filter invalid ratings
   - Parse year from movie title (e.g., "Toy Story (1995)")

3. **Parallel Aggregation**
   - Group ratings by movie_id
   - Calculate average rating per movie
   - Count number of ratings per movie
   - Compute standard deviation

4. **Join Operations**
   - Merge movie metadata with statistics
   - Broadcast join for efficient processing

5. **Score Calculation**
   - Apply recommendation formula
   - Sort by recommendation score descending
   - Select top 1000 movies

6. **Database Write**
   - Insert results into SQLite/MySQL
   - Create Movie and RecommendationData records

---

## Project Structure

```
recommendation_system/
├── ARCHITECTURE_DOCUMENTATION.md  # Detailed architecture guide
├── SUBMISSION_README.md          # Submission package guide
├── MOVIELENS_SETUP.md           # This file
├── README.md                     # Project overview
├── requirements.txt              # Python dependencies
├── manage.py                     # Django CLI
│
├── app/                          # Django application
│   ├── models.py                # Database models
│   │   ├── Movie                # Movie metadata
│   │   ├── RecommendationData   # Recommendation scores
│   │   └── RawDataset           # Uploaded datasets
│   ├── views.py                 # Request handlers
│   ├── forms.py                 # Form definitions
│   ├── urls.py                  # URL routing
│   ├── admin.py                 # Admin interface
│   ├── templates/               # HTML templates
│   │   ├── base.html           # Base template with UI
│   │   ├── dashboard.html       # Dashboard page
│   │   ├── recommendations.html # Recommendations list
│   │   ├── data_management.html # Data management
│   │   └── registration/        # Auth pages
│   └── static/                  # Static files
│       └── images/              # UM background image
│
├── config/                      # Django configuration
│   ├── settings.py             # Main settings
│   ├── urls.py                 # Root URL config
│   └── wsgi.py                 # WSGI entry point
│
├── spark_jobs/                  # Spark processing scripts
│   ├── spark_to_django.py      # Main Spark script
│   ├── movielens_processor.py  # MovieLens processor
│   └── data_cleaner.py         # Data cleaning utilities
│
├── data/                        # Data storage
│   └── archive/                 # MovieLens datasets
│       └── ml-25m/             # 25M dataset
│
└── db.sqlite3                   # SQLite database (created after migrate)
```

---

## Database Schema

### Movie Table

```sql
CREATE TABLE app_movie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER UNIQUE NOT NULL,
    title VARCHAR(500),
    year INTEGER,
    genres VARCHAR(200),
    avg_rating REAL,
    rating_count INTEGER
);
```

**Fields:**
- `id`: Auto-increment primary key
- `movie_id`: Original MovieLens ID
- `title`: Movie title (year removed)
- `year`: Release year (extracted from title)
- `genres`: Pipe-separated genres (e.g., "Action|Thriller")
- `avg_rating`: Average rating (0.5 - 5.0)
- `rating_count`: Number of ratings

### RecommendationData Table

```sql
CREATE TABLE app_recommendationdata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER,
    recommendation_score REAL,
    FOREIGN KEY (movie_id) REFERENCES app_movie (id)
);
```

### RawDataset Table

```sql
CREATE TABLE app_rawdataset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_file VARCHAR(500),
    upload_date DATETIME,
    processed BOOLEAN DEFAULT 0,
    processed_date DATETIME NULL,
    record_count INTEGER DEFAULT 0
);
```

---

## Troubleshooting

### Issue 1: Django Server Won't Start

**Error:** `Port 8000 is already in use`

**Solution:**
```bash
# Option A: Use a different port
python manage.py runserver 8080

# Option B: Kill the process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Issue 2: Spark Processing Fails

**Error:** `Java not found` or `JAVA_HOME not set`

**Solution:**
1. Install Java 8 or 11
2. Set JAVA_HOME environment variable:

```bash
# Windows
setx JAVA_HOME "C:\Program Files\Java\jdk-11"

# Linux/Mac
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
```

### Issue 3: Database Migration Errors

**Error:** `No changes detected in app 'app'`

**Solution:**
```bash
# Delete existing migrations
rm app/migrations/0*.py

# Recreate migrations
python manage.py makemigrations app
python manage.py migrate
```

### Issue 4: Spark Out of Memory

**Error:** `OutOfMemoryError: Java heap space`

**Solution:**
Edit `spark_jobs/spark_to_django.py`:

```python
spark = SparkSession.builder \
    .appName("MovieLensProcessor") \
    .config("spark.driver.memory", "4g")  # Increase from 2g
    .config("spark.executor.memory", "2g") \
    .getOrCreate()
```

### Issue 5: Background Image Not Loading

**Error:** 404 error for um-background.jpg

**Solution:**
1. Ensure image exists at `app/static/images/um-background.jpg`
2. Run `python manage.py collectstatic` (for production)
3. Check browser console for errors

### Issue 6: Processing Never Completes

**Symptoms:** Progress bar stuck at 90%

**Causes:**
- Dataset too large
- Insufficient memory
- Disk space full

**Solution:**
1. Check Spark process is running:
   ```bash
   # Windows
   tasklist | findstr python

   # Linux
   ps aux | grep spark
   ```

2. Check available memory:
   ```bash
   # Windows
   wmic OS get FreePhysicalMemory
   ```

3. Monitor disk space:
   ```bash
   # Windows
   dir

   # Linux
   df -h
   ```

---

## Advanced Configuration

### Switch from SQLite to MySQL (Production)

**Step 1: Install MySQL**
```bash
pip install mysqlclient
```

**Step 2: Create Database**
```sql
CREATE DATABASE recommendation_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

**Step 3: Update settings.py**

Edit `config/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'recommendation_db',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}
```

**Step 4: Run Migrations**
```bash
python manage.py migrate
```

### Customize Spark Processing

Edit `spark_jobs/spark_to_django.py` to adjust:

**Memory allocation:**
```python
.config("spark.driver.memory", "8g")  # Default: 2g
.config("spark.executor.memory", "4g")
```

**Partition count:**
```python
df = df.repartition(16)  # Default: auto-detect
```

**Minimum rating threshold:**
```python
# Filter movies with at least N ratings
movie_stats = movie_stats.filter(col("rating_count") >= 100)
```

### Enable Debug Mode

For development, ensure debug mode is on:

Edit `config/settings.py`:
```python
DEBUG = True
```

For production, always set:
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
```

---

## Performance Optimization

### For Large Datasets

**1. Increase Spark Memory**
```python
.config("spark.driver.memory", "16g")
.config("spark.executor.memory", "8g")
```

**2. Enable Spark UI for Monitoring**
```python
.config("spark.ui.enabled", "true")
.config("spark.ui.port", "4040")
```

Access at: http://localhost:4040

**3. Database Indexing**

Add indexes for faster queries:
```sql
CREATE INDEX idx_movie_id ON app_movie(movie_id);
CREATE INDEX idx_rec_score ON app_recommendationdata(recommendation_score DESC);
```

**4. Django Query Optimization**

Use `select_related` to reduce database queries:
```python
recommendations = RecommendationData.objects \
    .select_related('movie') \
    .order_by('-recommendation_score')[:100]
```

---

## Next Steps

### Feature Enhancements

1. **User-based Recommendations**
   - Track user rating history
   - Implement collaborative filtering
   - Use ALS (Alternating Least Squares)

2. **Content-based Filtering**
   - Analyze movie tags
   - Use TF-IDF for text similarity
   - Genre-based recommendations

3. **Real-time Processing**
   - Implement Spark Streaming
   - Use Kafka for event processing
   - Redis for caching

4. **Data Visualization**
   - Add Chart.js graphs
   - Rating distribution charts
   - Genre statistics

5. **REST API**
   - Django REST Framework
   - API endpoints for mobile apps
   - Authentication tokens

---

## Additional Resources

### Documentation
- [MovieLens Dataset](https://grouplens.org/datasets/movielens/)
- [Django Documentation](https://docs.djangoproject.com/en/4.2/)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)

### Tutorials
- [Django Tutorial](https://docs.djangoproject.com/en/4.2/intro/tutorial01/)
- [Spark with Python](https://spark.apache.org/docs/latest/api/python/getting_started/index.html)
- [Building Recommendation Systems](https://realpython.com/build-recommendation-engine-collaborative-filtering/)

### Related Projects
- [Surprise Library](http://surpriselib.com/) - Python recommender systems
- [LightFM](https://github.com/lyst/lightfm) - Hybrid recommendation algorithms
- [MovieLens Analysis Examples](https://github.com/topics/movielens)

---

## License and Credits

### Dataset License
The MovieLens dataset is provided by GroupLens Research at the University of Minnesota. Usage must comply with their license terms. See: https://grouplens.org/datasets/movielens/

### Project Code
This project code is for educational purposes. All code comments are in professional English without decorative elements.

### Technologies Used
- **Django 4.2** - Web framework
- **Apache Spark 3.x** - Distributed processing
- **Bootstrap 5.3** - UI framework
- **SQLite/MySQL** - Database
- **Python 3.8+** - Programming language

---

## Support

For questions or issues:
1. Check the `ARCHITECTURE_DOCUMENTATION.md` for detailed technical information
2. Review the code comments in `spark_jobs/spark_to_django.py`
3. Check Django admin panel for database inspection
4. Review browser console for frontend errors

---

## Summary

You now have a fully functional distributed movie recommendation system!

**Key Capabilities:**
- Process millions of ratings efficiently using Apache Spark
- Generate high-quality movie recommendations
- Web-based interface for data management
- Scalable architecture ready for cloud deployment
- Professional UI with modern design

**Typical Workflow:**
1. Start Django server
2. Login to the system
3. Process MovieLens data via web interface
4. View generated recommendations
5. Analyze results on dashboard

Enjoy exploring the world of recommendation systems!
