"""
Test reading Hive data using Beeline commands from Python
Simpler approach without JDBC complications
"""
import subprocess
import re

def run_beeline_query(query):
    """Execute query via Beeline in Docker container"""
    # Escape quotes in the query
    escaped_query = query.replace('"', '\\"')

    command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "{escaped_query}"'

    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        raise Exception(f"Beeline query failed: {result.stderr}")

    # Parse output from combined stdout and stderr
    output = result.stdout + result.stderr

    # Extract meaningful lines (data rows and headers)
    lines = output.split('\n')
    data_section = []
    in_result = False

    for line in lines:
        # Start capturing when we see the result table
        if '|' in line or '+--' in line:
            in_result = True

        if in_result:
            data_section.append(line)

        # Stop when we see "rows selected" or "rows affected"
        if 'row' in line.lower() and ('selected' in line.lower() or 'affected' in line.lower()):
            break

    return '\n'.join(data_section) if data_section else "No results"


def test_hive_data():
    """Test reading data from Hive using Beeline"""
    print("\n" + "="*60)
    print("Testing Hive Data Access via Beeline")
    print("="*60 + "\n")

    try:
        # Test 1: Count movies
        print("Test 1: Count movies in cleaned_movies")
        print("-" * 60)

        query1 = """
        SET hive.exec.mode.local.auto=true;
        SET mapreduce.framework.name=local;
        USE movielens_db;
        SELECT COUNT(*) as movie_count FROM cleaned_movies WHERE is_valid = TRUE
        """
        output1 = run_beeline_query(query1)
        print(output1)

        # Test 2: Sample movies
        print("\nTest 2: Sample movies from cleaned_movies")
        print("-" * 60)

        query2 = """
        SET hive.exec.mode.local.auto=true;
        SET mapreduce.framework.name=local;
        USE movielens_db;
        SELECT movieId, title, year, genres
        FROM cleaned_movies
        WHERE is_valid = TRUE
        LIMIT 5
        """
        output2 = run_beeline_query(query2)
        print(output2)

        # Test 3: Count ratings
        print("\nTest 3: Count ratings in cleaned_ratings")
        print("-" * 60)

        query3 = """
        SET hive.exec.mode.local.auto=true;
        SET mapreduce.framework.name=local;
        USE movielens_db;
        SELECT COUNT(*) as rating_count FROM cleaned_ratings WHERE is_valid = TRUE
        """
        output3 = run_beeline_query(query3)
        print(output3)

        # Test 4: Sample ratings
        print("\nTest 4: Sample ratings from cleaned_ratings")
        print("-" * 60)

        query4 = """
        SET hive.exec.mode.local.auto=true;
        SET mapreduce.framework.name=local;
        USE movielens_db;
        SELECT userId, movieId, rating, rating_date
        FROM cleaned_ratings
        WHERE is_valid = TRUE
        LIMIT 5
        """
        output4 = run_beeline_query(query4)
        print(output4)

        # Test 5: Top rated movies
        print("\nTest 5: Top 10 movies by average rating (min 100 ratings)")
        print("-" * 60)

        query5 = """
        SET hive.exec.mode.local.auto=true;
        SET mapreduce.framework.name=local;
        USE movielens_db;
        SELECT
            m.movieId,
            m.title,
            m.year,
            COUNT(r.rating) as rating_count,
            AVG(r.rating) as avg_rating
        FROM cleaned_movies m
        JOIN cleaned_ratings r ON m.movieId = r.movieId
        WHERE m.is_valid = TRUE AND r.is_valid = TRUE
        GROUP BY m.movieId, m.title, m.year
        HAVING rating_count >= 100
        ORDER BY avg_rating DESC
        LIMIT 10
        """
        output5 = run_beeline_query(query5)
        print(output5)

        # Success!
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("✅ Successfully verified Hive data is ready for Spark")
        print("="*60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_hive_data()
    exit(0 if success else 1)
