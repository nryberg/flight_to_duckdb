#!/usr/bin/env python3
"""
Validate and inspect Parquet flight data files.
Provides detailed information about file structure, data quality, and potential issues.
"""

import duckdb
from pathlib import Path
import argparse
import sys
from datetime import datetime, timedelta


def format_bytes(bytes_size):
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def validate_file(file_path: Path):
    """
    Validate a single Parquet file and report statistics and issues.

    Args:
        file_path: Path to Parquet file
    """
    print(f"{'=' * 80}")
    print(f"Validating: {file_path.name}")
    print(f"Location: {file_path}")
    print(f"{'=' * 80}")
    print()

    # Check if file exists
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        return False

    # Get file size
    file_size = file_path.stat().st_size
    print(f"File size: {format_bytes(file_size)}")
    print()

    # Create in-memory DuckDB connection
    con = duckdb.connect(':memory:')

    try:
        # Basic file information
        print("=== Basic Information ===")
        basic_info = con.execute(f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT hex) as unique_aircraft,
                COUNT(DISTINCT flight) as unique_flights,
                COUNT(DISTINCT observation_epoch) as unique_timestamps,
                MIN(observation_time) as earliest,
                MAX(observation_time) as latest
            FROM read_parquet('{file_path}')
        """).fetchone()

        total_records = basic_info[0]
        unique_aircraft = basic_info[1]
        unique_flights = basic_info[2]
        unique_timestamps = basic_info[3]
        earliest = basic_info[4]
        latest = basic_info[5]

        print(f"Total records: {total_records:,}")
        print(f"Unique aircraft (hex): {unique_aircraft:,}")
        print(f"Unique flight callsigns: {unique_flights:,}")
        print(f"Unique timestamps: {unique_timestamps:,}")
        print(f"Time range: {earliest} to {latest}")

        if earliest and latest:
            time_span = latest - earliest
            print(f"Time span: {time_span}")
        print()

        # Schema information
        print("=== Schema Information ===")
        schema = con.execute(f"""
            DESCRIBE SELECT * FROM read_parquet('{file_path}')
        """).fetchdf()
        print(f"Number of columns: {len(schema)}")
        print()

        # Data quality checks
        print("=== Data Quality Checks ===")
        issues_found = False

        # Check for duplicate (hex, observation_epoch) pairs
        duplicates = con.execute(f"""
            SELECT COUNT(*) as duplicate_count
            FROM (
                SELECT hex, observation_epoch, COUNT(*) as cnt
                FROM read_parquet('{file_path}')
                GROUP BY hex, observation_epoch
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        if duplicates > 0:
            print(f"⚠️  WARNING: Found {duplicates} duplicate (hex, observation_epoch) pairs")
            issues_found = True

            # Show examples
            examples = con.execute(f"""
                SELECT hex, observation_epoch, COUNT(*) as count
                FROM read_parquet('{file_path}')
                GROUP BY hex, observation_epoch
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 5
            """).fetchdf()
            print("\nExample duplicates:")
            print(examples.to_string(index=False))
            print()
        else:
            print("✓ No duplicate (hex, observation_epoch) pairs found")

        # Check for records with missing critical fields
        missing_hex = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{file_path}')
            WHERE hex IS NULL
        """).fetchone()[0]

        if missing_hex > 0:
            print(f"⚠️  WARNING: {missing_hex} records have missing 'hex' field")
            issues_found = True
        else:
            print("✓ All records have 'hex' field")

        # Check position data coverage
        position_stats = con.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 ELSE 0 END) as with_position,
                SUM(CASE WHEN lat IS NULL OR lon IS NULL THEN 1 ELSE 0 END) as without_position
            FROM read_parquet('{file_path}')
        """).fetchone()

        position_coverage = (position_stats[1] / position_stats[0] * 100) if position_stats[0] > 0 else 0
        print(f"Position coverage: {position_coverage:.1f}% ({position_stats[1]:,}/{position_stats[0]:,} records)")

        if position_coverage < 50:
            print("⚠️  WARNING: Low position data coverage")
            issues_found = True

        # Check altitude data
        altitude_stats = con.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN alt_baro IS NOT NULL THEN 1 ELSE 0 END) as with_alt_baro,
                SUM(CASE WHEN alt_baro = 'ground' THEN 1 ELSE 0 END) as on_ground
            FROM read_parquet('{file_path}')
        """).fetchone()

        alt_coverage = (altitude_stats[1] / altitude_stats[0] * 100) if altitude_stats[0] > 0 else 0
        ground_pct = (altitude_stats[2] / altitude_stats[0] * 100) if altitude_stats[0] > 0 else 0

        print(f"Altitude coverage: {alt_coverage:.1f}%")
        print(f"Ground observations: {ground_pct:.1f}%")
        print()

        # Check for future timestamps
        now = datetime.now()
        future_records = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{file_path}')
            WHERE observation_time > TIMESTAMP '{now.isoformat()}'
        """).fetchone()[0]

        if future_records > 0:
            print(f"⚠️  WARNING: Found {future_records} records with future timestamps")
            issues_found = True

        # Check for very old timestamps (more than 1 year old)
        one_year_ago = now - timedelta(days=365)
        old_records = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{file_path}')
            WHERE observation_time < TIMESTAMP '{one_year_ago.isoformat()}'
        """).fetchone()[0]

        if old_records > 0:
            print(f"ℹ️  INFO: Found {old_records} records older than 1 year")

        print()

        # Statistics by category
        print("=== Observations by Category ===")
        category_stats = con.execute(f"""
            SELECT
                COALESCE(category, '(unknown)') as category,
                COUNT(*) as count,
                COUNT(DISTINCT hex) as unique_aircraft,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM read_parquet('{file_path}')
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """).fetchdf()
        print(category_stats.to_string(index=False))
        print()

        # Signal quality statistics
        print("=== Signal Quality Statistics ===")
        signal_stats = con.execute(f"""
            SELECT
                COUNT(*) as records_with_rssi,
                AVG(rssi) as avg_rssi,
                MIN(rssi) as min_rssi,
                MAX(rssi) as max_rssi,
                AVG(messages) as avg_messages,
                MAX(messages) as max_messages
            FROM read_parquet('{file_path}')
            WHERE rssi IS NOT NULL
        """).fetchone()

        if signal_stats[0] > 0:
            print(f"Records with RSSI: {signal_stats[0]:,}")
            print(f"Average RSSI: {signal_stats[1]:.2f} dB")
            print(f"RSSI range: {signal_stats[2]:.2f} to {signal_stats[3]:.2f} dB")
            print(f"Average messages: {signal_stats[4]:.2f}")
            print(f"Max messages: {signal_stats[5]:,}")
        else:
            print("No RSSI data available")
        print()

        # Top aircraft by observation count
        print("=== Top 10 Aircraft by Observation Count ===")
        top_aircraft = con.execute(f"""
            SELECT
                hex,
                flight,
                COUNT(*) as observations,
                MIN(observation_time) as first_seen,
                MAX(observation_time) as last_seen
            FROM read_parquet('{file_path}')
            GROUP BY hex, flight
            ORDER BY observations DESC
            LIMIT 10
        """).fetchdf()
        print(top_aircraft.to_string(index=False))
        print()

        # Summary
        print("=== Validation Summary ===")
        if issues_found:
            print("⚠️  Some issues were found (see warnings above)")
            return False
        else:
            print("✓ File passed all validation checks")
            return True

    except Exception as e:
        print(f"ERROR during validation: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        con.close()


def validate_directory(directory: Path, level: str):
    """
    Validate all Parquet files in a directory.

    Args:
        directory: Directory containing Parquet files
        level: Level name ('hourly', 'daily', or 'weekly')
    """
    print(f"\n{'=' * 80}")
    print(f"Validating all {level} Parquet files in: {directory}")
    print(f"{'=' * 80}\n")

    parquet_files = sorted(directory.glob('*.parquet'))

    if not parquet_files:
        print(f"No Parquet files found in {directory}")
        return False

    print(f"Found {len(parquet_files)} Parquet file(s)\n")

    all_valid = True
    for i, file_path in enumerate(parquet_files, 1):
        print(f"\n[{i}/{len(parquet_files)}] ", end='')
        is_valid = validate_file(file_path)
        if not is_valid:
            all_valid = False
        print()

    print(f"\n{'=' * 80}")
    print(f"Validation complete for {len(parquet_files)} file(s)")
    if all_valid:
        print("✓ All files passed validation")
    else:
        print("⚠️  Some files have issues")
    print(f"{'=' * 80}\n")

    return all_valid


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Validate and inspect Parquet flight data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a specific file
  python3 validate_parquet.py --file parquet/daily/flights_daily_2025-11-23.parquet

  # Validate all daily files
  python3 validate_parquet.py --level daily

  # Validate all hourly files
  python3 validate_parquet.py --level hourly

  # Validate all weekly files
  python3 validate_parquet.py --level weekly
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', type=str,
                      help='Path to specific Parquet file to validate')
    group.add_argument('--level', choices=['hourly', 'daily', 'weekly'],
                      help='Validate all files at this level')

    parser.add_argument('--parquet-dir', default='parquet',
                       help='Base directory containing parquet files (default: parquet)')

    args = parser.parse_args()

    try:
        if args.file:
            file_path = Path(args.file)
            success = validate_file(file_path)
        else:
            directory = Path(args.parquet_dir) / args.level
            success = validate_directory(directory, args.level)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
