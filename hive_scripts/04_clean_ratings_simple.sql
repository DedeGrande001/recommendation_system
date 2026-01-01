-- ====================================================
-- 清洗评分数据 (简化版 - 不去重)
-- ====================================================

-- 设置本地执行模式
SET hive.exec.mode.local.auto=true;
SET mapreduce.framework.name=local;

USE movielens_db;

-- 设置动态分区模式
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.exec.max.dynamic.partitions=2000;
SET hive.exec.max.dynamic.partitions.pernode=1000;

-- 设置 Parquet 内存参数
SET parquet.block.size=134217728;
SET parquet.page.size=1048576;
SET parquet.writer.max-padding=8388608;

-- 插入清洗后的数据（带分区，不去重）
INSERT INTO TABLE cleaned_ratings PARTITION(rating_year, rating_month)
SELECT
    userId,
    movieId,
    rating,
    FROM_UNIXTIME(`timestamp`, 'yyyy-MM-dd HH:mm:ss') as rating_date,
    `timestamp`,
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
    YEAR(FROM_UNIXTIME(`timestamp`)) as rating_year,
    MONTH(FROM_UNIXTIME(`timestamp`)) as rating_month
FROM raw_ratings
WHERE userId IS NOT NULL
    AND movieId IS NOT NULL
    AND rating IS NOT NULL
    AND `timestamp` IS NOT NULL
    AND rating >= 0.5
    AND rating <= 5.0;

SELECT 'Ratings cleaning completed successfully!' as status;
