"""
Hive 数据查询工具
通过 Beeline 查询 Hive 中的数据统计
"""
import subprocess
import re


def run_hive_query(query):
    """执行 Hive 查询并返回结果"""
    try:
        # 转义引号
        escaped_query = query.replace('"', '\\"')

        # 执行 beeline 命令
        command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 --outputformat=csv2 --showHeader=false -e "{escaped_query}"'

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, f"查询失败: {result.stderr}"

        # 解析输出
        output_lines = result.stdout.strip().split('\n')

        # 过滤掉日志行
        data_lines = []
        for line in output_lines:
            # 跳过 Beeline 日志
            if any(keyword in line for keyword in [
                'SLF4J', 'Connecting', 'Connected', 'Driver',
                'Transaction', 'WARNING', 'Beeline', 'Closing',
                'row selected', 'row affected', 'jdbc:hive2'
            ]):
                continue

            # 有效数据行
            if line.strip():
                data_lines.append(line)

        return data_lines, None

    except subprocess.TimeoutExpired:
        return None, "查询超时"
    except Exception as e:
        return None, f"执行错误: {str(e)}"


def get_hive_statistics():
    """获取 Hive 中的数据统计"""
    stats = {
        'movies_count': 0,
        'ratings_count': 0,
        'users_count': 0,
        'avg_rating': 0.0,
        'available': False,
        'error': None
    }

    # 检查 Hive 是否可用
    query = """
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT COUNT(*) FROM cleaned_movies WHERE is_valid = TRUE;
    """

    result, error = run_hive_query(query)

    if error:
        stats['error'] = error
        return stats

    if result and len(result) > 0:
        try:
            stats['movies_count'] = int(result[0].strip())
            stats['available'] = True
        except:
            pass

    # 获取评分数
    query = """
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT COUNT(*) FROM cleaned_ratings WHERE is_valid = TRUE;
    """

    result, error = run_hive_query(query)
    if result and len(result) > 0:
        try:
            stats['ratings_count'] = int(result[0].strip())
        except:
            pass

    # 获取用户数
    query = """
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT COUNT(DISTINCT userId) FROM cleaned_ratings WHERE is_valid = TRUE;
    """

    result, error = run_hive_query(query)
    if result and len(result) > 0:
        try:
            stats['users_count'] = int(result[0].strip())
        except:
            pass

    # 获取平均评分
    query = """
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT AVG(rating) FROM cleaned_ratings WHERE is_valid = TRUE;
    """

    result, error = run_hive_query(query)
    if result and len(result) > 0:
        try:
            stats['avg_rating'] = float(result[0].strip())
        except:
            pass

    return stats


def get_top_rated_movies_from_hive(limit=10):
    """从 Hive 获取评分最高的电影"""
    query = f"""
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT
        m.movieId,
        m.title,
        m.year,
        m.genres,
        COUNT(r.rating) as rating_count,
        AVG(r.rating) as avg_rating
    FROM cleaned_movies m
    JOIN cleaned_ratings r ON m.movieId = r.movieId
    WHERE m.is_valid = TRUE AND r.is_valid = TRUE
    GROUP BY m.movieId, m.title, m.year, m.genres
    HAVING rating_count >= 100
    ORDER BY avg_rating DESC
    LIMIT {limit};
    """

    result, error = run_hive_query(query)

    if error:
        return [], error

    movies = []
    for line in result:
        if not line.strip():
            continue

        try:
            parts = line.split(',')
            if len(parts) >= 6:
                movies.append({
                    'movie_id': parts[0],
                    'title': parts[1],
                    'year': parts[2] if parts[2] else 'N/A',
                    'genres': parts[3],
                    'rating_count': int(float(parts[4])),
                    'avg_rating': round(float(parts[5]), 2)
                })
        except:
            continue

    return movies, None


def check_hive_connection():
    """检查 Hive 连接是否正常"""
    query = "SHOW DATABASES;"
    result, error = run_hive_query(query)

    if error:
        return False, error

    return True, "连接正常"
