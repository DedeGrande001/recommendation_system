-- ====================================================
-- Hive 表结构创建脚本
-- 用于 MovieLens 推荐系统数据清洗
-- ====================================================

-- 使用 movielens_db 数据库
USE movielens_db;

-- ====================================================
-- 1. 创建原始数据表（Raw Tables）
-- ====================================================

-- 1.1 原始电影数据表
DROP TABLE IF EXISTS raw_movies;
CREATE EXTERNAL TABLE IF NOT EXISTS raw_movies (
    movieId INT,
    title STRING,
    genres STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/raw/movies'
TBLPROPERTIES ('skip.header.line.count'='1');

-- 1.2 原始评分数据表
DROP TABLE IF EXISTS raw_ratings;
CREATE EXTERNAL TABLE IF NOT EXISTS raw_ratings (
    userId INT,
    movieId INT,
    rating DOUBLE,
    `timestamp` BIGINT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/raw/ratings'
TBLPROPERTIES ('skip.header.line.count'='1');

-- ====================================================
-- 2. 创建清洗后数据表（Cleaned Tables）
-- ====================================================

-- 2.1 清洗后电影数据表
DROP TABLE IF EXISTS cleaned_movies;
CREATE TABLE IF NOT EXISTS cleaned_movies (
    movieId INT,
    title STRING,
    year INT,
    genres_array ARRAY<STRING>,
    genres STRING,
    is_valid BOOLEAN
)
STORED AS PARQUET
LOCATION '/user/hive/warehouse/cleaned/movies';

-- 2.2 清洗后评分数据表
DROP TABLE IF EXISTS cleaned_ratings;
CREATE TABLE IF NOT EXISTS cleaned_ratings (
    userId INT,
    movieId INT,
    rating DOUBLE,
    rating_date STRING,
    `timestamp` BIGINT,
    is_valid BOOLEAN
)
PARTITIONED BY (rating_year INT, rating_month INT)
STORED AS PARQUET
LOCATION '/user/hive/warehouse/cleaned/ratings';

-- ====================================================
-- 3. 创建数据质量统计表
-- ====================================================

-- 3.1 数据质量报告表
DROP TABLE IF EXISTS data_quality_report;
CREATE TABLE IF NOT EXISTS data_quality_report (
    table_name STRING,
    check_type STRING,
    total_records BIGINT,
    invalid_records BIGINT,
    valid_records BIGINT,
    invalid_percentage DOUBLE,
    check_timestamp STRING
)
STORED AS PARQUET;

-- ====================================================
-- 验证表创建
-- ====================================================
SHOW TABLES;
