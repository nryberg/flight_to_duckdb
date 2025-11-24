#!/usr/bin/env python3
"""
Example queries for Parquet flight data files.
Demonstrates how to query hourly, daily, and weekly Parquet files using DuckDB.
"""

import duckdb
from pathlib import Path
import argparse
import sys


def query_latest_parquet(parquet_dir: str = 'parquet', level: str = 'daily'):
    """
    Query the most recent Parquet file at the specified level.

    Args:
        parquet_dir: Base directory containing parquet files
        level: 'hourly', 'daily', or 'weekly'
    """
    parquet_path = Path(parquet_dir) / level

    if not parquet_path.exists():
        print(f"ERROR: Directory not found: {parquet_path}", file=sys.stderr)
        return False

    # Find the most recent parquet file
    parquet_files = sorted(parquet_path.glob('*.parquet'), reverse=True)

    if not parquet_files:
        print(f"No Parquet files found in {parquet_path}", file=sys.stderr)
        return False

    latest_file = parquet_files[0]
    print(f"Querying: {latest_file.name}")
    print(f"Location: {latest_file}")
    print("=" * 70)
    print()

    # Create in-memory DuckDB connection
    con = duckdb.connect(':memory:')

    # File information
    print("=== File Information ===")
    file_info = con.execute(f"""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT hex) as unique_aircraft,
            COUNT(DISTINCT flight) as unique_flights,
            MIN(observation_time) as earliest_observation,
            MAX(observation_time) as latest_observation
        FROM read_parquet('{latest_file}')
    """).fetchone()

    print(f"Total records: {file_info[0]:,}")
    print(f"Unique aircraft: {file_info[1]:,}")
    print(f"Unique flights: {file_info[2]:,}")
    print(f"Time range: {file_info[3]} to {file_info[4]}")
    print()

    # Recent aircraft with positions
    print("=== Recent Aircraft with Positions ===")
    result = con.execute(f"""
        SELECT
            hex,
            flight,
            lat,
            lon,
            alt_baro,
            gs,
            track,
            observation_time
        FROM read_parquet('{latest_file}')
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY observation_time DESC
        LIMIT 10
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    # Aircraft by category
    print("=== Aircraft by Category ===")
    result = con.execute(f"""
        SELECT
            category,
            COUNT(DISTINCT hex) as unique_aircraft,
            COUNT(*) as observations
        FROM read_parquet('{latest_file}')
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY observations DESC
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    # Top flights by observation count
    print("=== Top Flights by Observation Count ===")
    result = con.execute(f"""
        SELECT
            flight,
            hex,
            COUNT(*) as observations,
            MIN(observation_time) as first_seen,
            MAX(observation_time) as last_seen
        FROM read_parquet('{latest_file}')
        WHERE flight IS NOT NULL
        GROUP BY flight, hex
        ORDER BY observations DESC
        LIMIT 10
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    # Altitude distribution (excluding ground)
    print("=== Altitude Distribution (excluding ground) ===")
    result = con.execute(f"""
        SELECT
            CASE
                WHEN CAST(alt_baro AS INTEGER) < 5000 THEN '< 5,000 ft'
                WHEN CAST(alt_baro AS INTEGER) < 10000 THEN '5,000-10,000 ft'
                WHEN CAST(alt_baro AS INTEGER) < 20000 THEN '10,000-20,000 ft'
                WHEN CAST(alt_baro AS INTEGER) < 30000 THEN '20,000-30,000 ft'
                WHEN CAST(alt_baro AS INTEGER) < 40000 THEN '30,000-40,000 ft'
                ELSE '> 40,000 ft'
            END as altitude_range,
            COUNT(*) as count
        FROM read_parquet('{latest_file}')
        WHERE alt_baro IS NOT NULL
          AND alt_baro != 'ground'
          AND TRY_CAST(alt_baro AS INTEGER) IS NOT NULL
        GROUP BY altitude_range
        ORDER BY MIN(TRY_CAST(alt_baro AS INTEGER))
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    # Signal quality statistics
    print("=== Signal Quality Statistics ===")
    result = con.execute(f"""
        SELECT
            AVG(rssi) as avg_rssi,
            MIN(rssi) as min_rssi,
            MAX(rssi) as max_rssi,
            AVG(messages) as avg_messages,
            MAX(messages) as max_messages
        FROM read_parquet('{latest_file}')
        WHERE rssi IS NOT NULL
    """).fetchone()
    print(f"Average RSSI: {result[0]:.2f} dB")
    print(f"Min RSSI: {result[1]:.2f} dB")
    print(f"Max RSSI: {result[2]:.2f} dB")
    print(f"Average Messages: {result[3]:.2f}")
    print(f"Max Messages: {result[4]:,}")
    print()

    con.close()
    return True


def query_multiple_files(parquet_dir: str = 'parquet', level: str = 'daily', count: int = 7):
    """
    Query multiple Parquet files for trend analysis.

    Args:
        parquet_dir: Base directory containing parquet files
        level: 'hourly', 'daily', or 'weekly'
        count: Number of recent files to analyze
    """
    parquet_path = Path(parquet_dir) / level

    if not parquet_path.exists():
        print(f"ERROR: Directory not found: {parquet_path}", file=sys.stderr)
        return False

    # Find recent parquet files
    parquet_files = sorted(parquet_path.glob('*.parquet'), reverse=True)[:count]

    if not parquet_files:
        print(f"No Parquet files found in {parquet_path}", file=sys.stderr)
        return False

    print(f"Analyzing {len(parquet_files)} most recent {level} files")
    print("=" * 70)
    print()

    # Create in-memory DuckDB connection
    con = duckdb.connect(':memory:')

    # Build file list for query
    file_list = ', '.join([f"'{f}'" for f in parquet_files])

    # Per-file statistics
    print(f"=== Per-File Statistics ===")
    result = con.execute(f"""
        SELECT
            source_file,
            COUNT(*) as records,
            COUNT(DISTINCT hex) as aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest
        FROM read_parquet([{file_list}])
        GROUP BY source_file
        ORDER BY earliest DESC
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    # Overall statistics
    print(f"=== Overall Statistics Across {len(parquet_files)} Files ===")
    overall = con.execute(f"""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT hex) as unique_aircraft,
            COUNT(DISTINCT flight) as unique_flights,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest
        FROM read_parquet([{file_list}])
    """).fetchone()

    print(f"Total records: {overall[0]:,}")
    print(f"Unique aircraft: {overall[1]:,}")
    print(f"Unique flights: {overall[2]:,}")
    print(f"Time range: {overall[3]} to {overall[4]}")
    print()

    # Most frequently observed aircraft across all files
    print(f"=== Most Frequently Observed Aircraft ===")
    result = con.execute(f"""
        SELECT
            hex,
            flight,
            COUNT(*) as total_observations,
            COUNT(DISTINCT DATE(observation_time)) as days_observed,
            MIN(observation_time) as first_seen,
            MAX(observation_time) as last_seen
        FROM read_parquet([{file_list}])
        WHERE flight IS NOT NULL
        GROUP BY hex, flight
        ORDER BY total_observations DESC
        LIMIT 15
    """).fetchdf()
    print(result.to_string(index=False))
    print()

    con.close()
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Query Parquet flight data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query latest daily file
  python3 query_parquet_example.py

  # Query latest hourly file
  python3 query_parquet_example.py --level hourly

  # Query latest weekly file
  python3 query_parquet_example.py --level weekly

  # Analyze trends across multiple daily files
  python3 query_parquet_example.py --multi --count 7

  # Analyze last 24 hourly files
  python3 query_parquet_example.py --level hourly --multi --count 24
        """
    )

    parser.add_argument('--level', choices=['hourly', 'daily', 'weekly'],
                       default='daily',
                       help='Level of aggregation to query (default: daily)')
    parser.add_argument('--parquet-dir', default='parquet',
                       help='Base directory containing parquet files (default: parquet)')
    parser.add_argument('--multi', action='store_true',
                       help='Query multiple files for trend analysis')
    parser.add_argument('--count', type=int, default=7,
                       help='Number of recent files to analyze in multi mode (default: 7)')

    args = parser.parse_args()

    try:
        if args.multi:
            success = query_multiple_files(args.parquet_dir, args.level, args.count)
        else:
            success = query_latest_parquet(args.parquet_dir, args.level)

        if not success:
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
