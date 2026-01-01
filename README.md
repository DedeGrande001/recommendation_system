# Recommendation System

A Django-based recommendation system with Apache Spark for distributed data processing.

## Features

- ✅ User Authentication (Login/Register)
- ✅ Data Management Dashboard
- ✅ Upload CSV Datasets
- ✅ Apache Spark Data Cleaning & Processing
- ✅ MySQL Database Integration
- ✅ Recommendation Results Display
- ✅ Responsive Bootstrap UI

## Tech Stack

- **Backend:** Django 4.2
- **Database:** MySQL
- **Big Data:** Apache Spark (PySpark)
- **Frontend:** Bootstrap 5
- **Language:** Python 3.8+

## Project Structure

```
recommendation_system/
├── app/                        # Django app
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── recommendations.html
│   │   ├── data_management.html
│   │   └── registration/
│   │       ├── login.html
│   │       └── register.html
│   ├── models.py              # Database models
│   ├── views.py               # View logic
│   ├── forms.py               # Django forms
│   ├── urls.py                # URL routing
│   └── admin.py               # Admin configuration
├── config/                    # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── spark_jobs/                # Spark data processing
│   └── data_cleaner.py        # Data cleaning script
├── data/                      # Dataset storage
├── manage.py                  # Django management
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- Java 8+ (for Spark)
- pip

### Step 1: Clone and Setup

```bash
cd recommendation_system
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Database

1. Create MySQL database:
```sql
CREATE DATABASE recommendation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

3. Edit `.env` file with your database credentials:
```env
DB_NAME=recommendation_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### Step 5: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

### Step 7: Run Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000

## Usage

### 1. Register/Login
- Navigate to http://localhost:8000/register
- Create an account
- Login to access the dashboard

### 2. Upload Dataset
- Go to "Data Management" page
- Upload a CSV file
- The system will store it in the `data/` directory

### 3. Process with Spark
- Click "Process with Spark" button next to your dataset
- Spark will clean and transform the data
- Processed data will be written to MySQL

### 4. View Recommendations
- Go to "Recommendations" page
- Browse all processed recommendations
- Results are paginated for easy navigation

## Spark Data Processing

The Spark job (`spark_jobs/data_cleaner.py`) performs:

1. **Data Loading:** Read CSV files
2. **Data Cleaning:**
   - Remove duplicates
   - Handle missing values
   - Clean string columns
3. **Transformation:** Convert to recommendation format
4. **MySQL Write:** Store processed data

### Customize Spark Processing

Edit `spark_jobs/data_cleaner.py` to match your dataset structure:

```python
def transform_for_recommendation(self, df):
    # Add your custom transformation logic
    # Map your columns to: item_id, item_name, category, score, description
    pass
```

## Database Models

### RecommendationData
- `item_id`: Item identifier
- `item_name`: Item name
- `category`: Item category
- `score`: Recommendation score
- `description`: Item description

### RawDataset
- `data_file`: Uploaded filename
- `upload_date`: Upload timestamp
- `processed`: Processing status
- `record_count`: Number of records

### UserPreference
- `user`: Associated user
- `favorite_categories`: User preferences

## Admin Panel

Access Django admin at: http://localhost:8000/admin

Login with your superuser credentials to:
- Manage users
- View/edit recommendations
- Monitor datasets
- Configure user preferences

## API Integration (Future)

You can extend this system with Django REST Framework to create APIs for:
- Mobile apps
- External integrations
- Real-time recommendations

## Troubleshooting

### MySQL Connection Error
```bash
# Install MySQL client
pip install mysqlclient
# Or on Windows, download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

### Spark Java Error
Ensure Java 8+ is installed:
```bash
java -version
```

### Port Already in Use
```bash
python manage.py runserver 8080  # Use different port
```

## Next Steps

1. **Customize Dataset Processing:**
   - Modify `spark_jobs/data_cleaner.py` based on your data
   - Implement recommendation algorithms

2. **Add More Features:**
   - User-specific recommendations
   - Filtering and search
   - Data visualization
   - Export functionality

3. **Deploy to Production:**
   - Use PostgreSQL or production MySQL
   - Configure NGINX/Apache
   - Set DEBUG=False
   - Use environment variables

## Contributing

Feel free to fork and customize this system for your needs!

## License

MIT License

## Support

For issues and questions, please create an issue in the repository.
