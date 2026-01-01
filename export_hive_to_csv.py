"""
Export cleaned data from Hive to CSV files for Spark processing
"""
import subprocess
import os
from pathlib import Path


def export_table_to_csv(table_name, output_file, columns):
    """Export Hive table to CSV file"""
    print(f"\n{'='*60}")
    print(f"Exporting {table_name} to {output_file}")
    print('='*60)

    # Construct query
    query = f"""
    SET hive.exec.mode.local.auto=true;
    SET mapreduce.framework.name=local;
    USE movielens_db;
    SELECT {columns}
    FROM {table_name}
    WHERE is_valid = TRUE
    """

    # Escape quotes
    escaped_query = query.replace('"', '\\"')

    # Execute query
    command = f'docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "{escaped_query}" --outputformat=csv2 --showHeader=true'

    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"❌ Export failed: {result.stderr}")
        return False

    # Parse output from stdout
    output_lines = result.stdout.split('\n')

    # Find where the actual CSV data starts
    csv_lines = []
    for line in output_lines:
        # Skip log and connection lines
        if any(keyword in line for keyword in ['SLF4J', 'Connecting', 'Connected', 'Driver', 'Transaction', 'WARNING', 'Beeline', 'Closing', 'row selected', 'row affected']):
            continue

        # If line contains commas or starts with a quote, it's likely CSV data or header
        if (',' in line or line.startswith('"') or line.startswith(columns.split(',')[0].strip())):
            csv_lines.append(line)

    if not csv_lines:
        print("❌ No CSV data found in output")
        return False

    # Write CSV file
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        for line in csv_lines:
            f.write(line + '\n')

    # Get row count
    row_count = len(csv_lines) - 1  # Subtract header

    print(f"✅ Exported {row_count:,} rows to {output_file}")
    return True


def main():
    print("\n" + "="*60)
    print("Exporting Hive Data to CSV Files")
    print("="*60)

    # Create output directory
    output_dir = Path(__file__).parent / "hive_export"
    output_dir.mkdir(exist_ok=True)

    # Export movies (excluding genres_array which has complex type)
    movies_file = output_dir / "cleaned_movies.csv"
    movies_columns = "movieId, title, year, genres"

    if not export_table_to_csv("cleaned_movies", movies_file, movies_columns):
        return False

    # Export ratings
    ratings_file = output_dir / "cleaned_ratings.csv"
    ratings_columns = "userId, movieId, rating, rating_date, `timestamp`"

    if not export_table_to_csv("cleaned_ratings", ratings_file, ratings_columns):
        return False

    print("\n" + "="*60)
    print("✅ ALL EXPORTS COMPLETED!")
    print(f"✅ Files saved to: {output_dir.absolute()}")
    print("="*60 + "\n")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
