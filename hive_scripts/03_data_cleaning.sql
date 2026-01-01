-- ====================================================
-- 数据清洗脚本
-- 清洗原始数据并写入清洗后的表
-- ====================================================

-- 设置本地执行模式
SET hive.exec.mode.local.auto=true;
SET mapreduce.framework.name=local;

USE movielens_db;

-- ====================================================
-- 1. 清洗电影数据
-- ====================================================

-- 清空目标表
TRUNCATE TABLE cleaned_movies;

-- 插入清洗后的数据
INSERT INTO TABLE cleaned_movies
SELECT
    movieId,
    -- 清理标题（去除首尾空格）
    TRIM(title) as title,

    -- 提取年份（从标题中提取括号内的年份）
    CAST(
        CASE
            WHEN title RLIKE '\\([0-9]{4}\\)$'
            THEN REGEXP_EXTRACT(title, '\\(([0-9]{4})\\)$', 1)
            ELSE NULL
        END
    AS INT) as year,

    -- 将 genres 字符串拆分为数组
    SPLIT(genres, '\\|') as genres_array,

    -- 保留原始 genres 字符串
    genres,

    -- 数据有效性标记
    CASE
        WHEN movieId IS NOT NULL
            AND title IS NOT NULL
            AND title != ''
            AND genres IS NOT NULL
            AND genres != ''
            AND genres != '(no genres listed)'
        THEN TRUE
        ELSE FALSE
    END as is_valid

FROM raw_movies
WHERE movieId IS NOT NULL;  -- 过滤掉 movieId 为空的记录

-- ====================================================
-- 2. 清洗评分数据
-- ====================================================

-- 设置动态分区模式
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.exec.max.dynamic.partitions=2000;
SET hive.exec.max.dynamic.partitions.pernode=1000;

-- 清空目标表（如果需要）
-- TRUNCATE TABLE cleaned_ratings;

-- 插入清洗后的数据（带分区）
INSERT INTO TABLE cleaned_ratings PARTITION(rating_year, rating_month)
SELECT
    userId,
    movieId,
    rating,

    -- 将 timestamp 转换为日期字符串
    FROM_UNIXTIME(`timestamp`, 'yyyy-MM-dd HH:mm:ss') as rating_date,

    `timestamp`,

    -- 数据有效性标记
    CASE
        WHEN userId IS NOT NULL
            AND movieId IS NOT NULL
            AND rating IS NOT NULL
            AND rating >= 0.5
            AND rating <= 5.0
            AND `timestamp` IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END as is_valid,

    -- 分区字段：年份
    YEAR(FROM_UNIXTIME(`timestamp`)) as rating_year,

    -- 分区字段：月份
    MONTH(FROM_UNIXTIME(`timestamp`)) as rating_month

FROM (
    -- 使用子查询进行去重（保留最新的评分）
    SELECT
        userId,
        movieId,
        rating,
        `timestamp`,
        ROW_NUMBER() OVER (PARTITION BY userId, movieId ORDER BY `timestamp` DESC) as rn
    FROM raw_ratings
    WHERE userId IS NOT NULL
        AND movieId IS NOT NULL
        AND rating IS NOT NULL
        AND `timestamp` IS NOT NULL
        AND rating >= 0.5
        AND rating <= 5.0
) t
WHERE rn = 1;  -- 只保留每个用户-电影对的最新评分

-- ====================================================
-- 3. 验证清洗结果
-- ====================================================

-- 3.1 检查清洗后的电影数据
SELECT
    'cleaned_movies' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_valid = TRUE THEN 1 ELSE 0 END) as valid_records,
    SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) as invalid_records,
    COUNT(DISTINCT movieId) as unique_movies,
    SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as records_with_year,
    SUM(CASE WHEN SIZE(genres_array) > 0 THEN 1 ELSE 0 END) as records_with_genres
FROM cleaned_movies;

-- 3.2 检查清洗后的评分数据
SELECT
    'cleaned_ratings' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_valid = TRUE THEN 1 ELSE 0 END) as valid_records,
    SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) as invalid_records,
    COUNT(DISTINCT userId) as unique_users,
    COUNT(DISTINCT movieId) as unique_movies,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating,
    AVG(rating) as avg_rating
FROM cleaned_ratings;

-- 3.3 按分区查看评分数据分布
SELECT
    rating_year,
    rating_month,
    COUNT(*) as rating_count,
    COUNT(DISTINCT userId) as unique_users,
    AVG(rating) as avg_rating
FROM cleaned_ratings
GROUP BY rating_year, rating_month
ORDER BY rating_year DESC, rating_month DESC
LIMIT 20;

-- 3.4 数据清洗前后对比
SELECT
    'Movies - Before Cleaning' as description,
    COUNT(*) as record_count,
    COUNT(DISTINCT movieId) as unique_count
FROM raw_movies
UNION ALL
SELECT
    'Movies - After Cleaning' as description,
    COUNT(*) as record_count,
    COUNT(DISTINCT movieId) as unique_count
FROM cleaned_movies
UNION ALL
SELECT
    'Ratings - Before Cleaning' as description,
    COUNT(*) as record_count,
    COUNT(DISTINCT userId, movieId) as unique_count
FROM raw_ratings
UNION ALL
SELECT
    'Ratings - After Cleaning' as description,
    COUNT(*) as record_count,
    COUNT(DISTINCT userId, movieId) as unique_count
FROM cleaned_ratings;

-- ====================================================
-- 完成
-- ====================================================
SELECT 'Data cleaning completed successfully!' as status;
