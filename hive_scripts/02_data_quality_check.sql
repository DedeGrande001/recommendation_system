-- ====================================================
-- 数据质量检查脚本
-- 检查原始数据中的问题：缺失值、重复、异常值等
-- ====================================================

USE movielens_db;

-- ====================================================
-- 1. 电影数据质量检查
-- ====================================================

-- 1.1 检查空值和缺失数据
SELECT
    'raw_movies' as table_name,
    'null_check' as check_type,
    COUNT(*) as total_records,
    SUM(CASE WHEN movieId IS NULL THEN 1 ELSE 0 END) as null_movieId,
    SUM(CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END) as null_title,
    SUM(CASE WHEN genres IS NULL OR genres = '' OR genres = '(no genres listed)' THEN 1 ELSE 0 END) as null_or_missing_genres
FROM raw_movies;

-- 1.2 检查重复的 movieId
SELECT
    'raw_movies' as table_name,
    'duplicate_check' as check_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT movieId) as unique_movies,
    COUNT(*) - COUNT(DISTINCT movieId) as duplicate_count
FROM raw_movies;

-- 1.3 检查标题格式问题（没有年份）
SELECT
    'raw_movies' as table_name,
    'title_format_check' as check_type,
    COUNT(*) as total_records,
    SUM(CASE WHEN title NOT RLIKE '\\([0-9]{4}\\)$' THEN 1 ELSE 0 END) as missing_year_count
FROM raw_movies;

-- ====================================================
-- 2. 评分数据质量检查
-- ====================================================

-- 2.1 检查空值
SELECT
    'raw_ratings' as table_name,
    'null_check' as check_type,
    COUNT(*) as total_records,
    SUM(CASE WHEN userId IS NULL THEN 1 ELSE 0 END) as null_userId,
    SUM(CASE WHEN movieId IS NULL THEN 1 ELSE 0 END) as null_movieId,
    SUM(CASE WHEN rating IS NULL THEN 1 ELSE 0 END) as null_rating,
    SUM(CASE WHEN `timestamp` IS NULL THEN 1 ELSE 0 END) as null_timestamp
FROM raw_ratings;

-- 2.2 检查评分范围异常（MovieLens 评分应该在 0.5-5.0 之间）
SELECT
    'raw_ratings' as table_name,
    'rating_range_check' as check_type,
    COUNT(*) as total_records,
    SUM(CASE WHEN rating < 0.5 OR rating > 5.0 THEN 1 ELSE 0 END) as out_of_range_count,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating
FROM raw_ratings;

-- 2.3 检查重复评分（同一用户对同一电影的多次评分）
SELECT
    'raw_ratings' as table_name,
    'duplicate_ratings_check' as check_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT userId, movieId) as unique_user_movie_pairs,
    COUNT(*) - COUNT(DISTINCT userId, movieId) as duplicate_ratings_count
FROM raw_ratings;

-- 2.4 检查孤立评分（评分的电影不在电影表中）
SELECT
    'raw_ratings' as table_name,
    'orphan_ratings_check' as check_type,
    COUNT(DISTINCT r.movieId) as total_rated_movies,
    COUNT(DISTINCT CASE WHEN m.movieId IS NULL THEN r.movieId ELSE NULL END) as orphan_movie_count
FROM raw_ratings r
LEFT JOIN raw_movies m ON r.movieId = m.movieId;

-- ====================================================
-- 3. 生成数据质量摘要报告
-- ====================================================

-- 清空旧报告
TRUNCATE TABLE data_quality_report;

-- 插入电影数据质量报告
INSERT INTO TABLE data_quality_report
SELECT
    'raw_movies' as table_name,
    'overall_quality' as check_type,
    COUNT(*) as total_records,
    SUM(CASE
        WHEN movieId IS NULL
            OR title IS NULL
            OR title = ''
            OR genres IS NULL
            OR genres = ''
            OR genres = '(no genres listed)'
        THEN 1
        ELSE 0
    END) as invalid_records,
    SUM(CASE
        WHEN movieId IS NOT NULL
            AND title IS NOT NULL
            AND title != ''
            AND genres IS NOT NULL
            AND genres != ''
            AND genres != '(no genres listed)'
        THEN 1
        ELSE 0
    END) as valid_records,
    ROUND(SUM(CASE
        WHEN movieId IS NULL
            OR title IS NULL
            OR title = ''
            OR genres IS NULL
            OR genres = ''
            OR genres = '(no genres listed)'
        THEN 1
        ELSE 0
    END) * 100.0 / COUNT(*), 2) as invalid_percentage,
    FROM_UNIXTIME(UNIX_TIMESTAMP()) as check_timestamp
FROM raw_movies;

-- 插入评分数据质量报告
INSERT INTO TABLE data_quality_report
SELECT
    'raw_ratings' as table_name,
    'overall_quality' as check_type,
    COUNT(*) as total_records,
    SUM(CASE
        WHEN userId IS NULL
            OR movieId IS NULL
            OR rating IS NULL
            OR `timestamp` IS NULL
            OR rating < 0.5
            OR rating > 5.0
        THEN 1
        ELSE 0
    END) as invalid_records,
    SUM(CASE
        WHEN userId IS NOT NULL
            AND movieId IS NOT NULL
            AND rating IS NOT NULL
            AND `timestamp` IS NOT NULL
            AND rating >= 0.5
            AND rating <= 5.0
        THEN 1
        ELSE 0
    END) as valid_records,
    ROUND(SUM(CASE
        WHEN userId IS NULL
            OR movieId IS NULL
            OR rating IS NULL
            OR `timestamp` IS NULL
            OR rating < 0.5
            OR rating > 5.0
        THEN 1
        ELSE 0
    END) * 100.0 / COUNT(*), 2) as invalid_percentage,
    FROM_UNIXTIME(UNIX_TIMESTAMP()) as check_timestamp
FROM raw_ratings;

-- 查看质量报告
SELECT * FROM data_quality_report;
