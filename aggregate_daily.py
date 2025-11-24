#!/usr/bin/env python3
"""
Aggregate hourly Parquet files into daily files.
Concatenates all hourly files from a given day, removes duplicates, and creates a daily file.
"""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta
import sys
import argparse
import shutil


def aggregate_daily(date: datetime, hourly_dir: str = 'parquet/hourly',
                   daily_dir: str = 'parquet/daily', keep_hourly: bool = True,
                   backup_dir: str = None):
    """
    Aggregate hourly parquet files into a single daily file.

    Args:
        date: Date to aggregate (datetime object)
        hourly_dir: Directory containing hourly Parquet files
        daily_dir: Directory to save daily Parquet files
        keep_hourly: If True, keep hourly files after aggregation
        backup_dir: Optional backup directory to copy files to (e.g., /mnt/usb3/tinkerboard/flights/daily)
    """
    hourly_path = Path(hourly_dir)
    daily_path = Path(daily_dir)
    daily_path.mkdir(parents=True, exist_ok=True)

    # Format date string
    date_str = date.strftime('%Y-%m-%d')

    # Find all hourly files for this date
    pattern = f"flights_hourly_{date_str}_*.parquet"
    hourly_files = sorted(hourly_path.glob(pattern))

    if not hourly_files:
        print(f"No hourly files found for date: {date_str}")
        print(f"  Searched for: {pattern}")
        return False

    print(f"Aggregating daily file for: {date_str}")
    print(f"Found {len(hourly_files)} hourly files:")
    for f in hourly_files:
        print(f"  - {f.name}")

    # Output filename
    output_file = daily_path / f"flights_daily_{date_str}.parquet"

    # Use DuckDB to aggregate and deduplicate
    con = duckdb.connect(':memory:')

    # Read all hourly files into a single table
    hourly_files_str = ', '.join([f"'{f}'" for f in hourly_files])

    print(f"\nLoading {len(hourly_files)} hourly files...")
    con.execute(f"""
        CREATE TABLE hourly_data AS
        SELECT * FROM read_parquet([{hourly_files_str}])
    """)

    # Get stats before deduplication
    before_count = con.execute("SELECT COUNT(*) FROM hourly_data").fetchone()[0]
    print(f"Total records before deduplication: {before_count}")

    # Remove duplicates based on (hex, observation_epoch)
    print("Removing duplicates...")
    con.execute("""
        CREATE TABLE daily_data AS
        SELECT DISTINCT ON (hex, observation_epoch) *
        FROM hourly_data
        ORDER BY hex, observation_epoch, observation_time
    """)

    # Get stats after deduplication
    after_count = con.execute("SELECT COUNT(*) FROM daily_data").fetchone()[0]
    duplicates_removed = before_count - after_count
    print(f"Total records after deduplication: {after_count}")
    print(f"Duplicates removed: {duplicates_removed}")

    # Get additional statistics
    stats = con.execute("""
        SELECT
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest,
            COUNT(DISTINCT source_file) as source_files
        FROM daily_data
    """).fetchone()

    # Write to Parquet
    print(f"\nWriting daily file: {output_file}")
    con.execute(f"COPY daily_data TO '{output_file}' (FORMAT PARQUET)")

    con.close()

    print(f"\n✓ Daily aggregation completed: {output_file}")
    print(f"  - Total records: {after_count}")
    print(f"  - Unique aircraft: {stats[0]}")
    print(f"  - Time range: {stats[1]} to {stats[2]}")
    print(f"  - Source files: {stats[3]}")

    # Copy to backup directory if specified
    if backup_dir:
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = backup_path / output_file.name

        print(f"\nCopying to backup location: {backup_file}")
        shutil.copy2(output_file, backup_file)
        print(f"✓ Backup copy completed")

    # Clean up hourly files if requested
    if not keep_hourly:
        print(f"\nRemoving {len(hourly_files)} hourly files...")
        for f in hourly_files:
            f.unlink()
            print(f"  Deleted: {f.name}")

    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Aggregate hourly Parquet files into daily files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate yesterday's data (default)
  python3 aggregate_daily.py

  # Aggregate specific date
  python3 aggregate_daily.py --date 2025-11-23

  # Aggregate and delete hourly files
  python3 aggregate_daily.py --date 2025-11-23 --delete-hourly
        """
    )

    parser.add_argument('--date', type=str,
                       help='Date to aggregate (YYYY-MM-DD). Default: yesterday')
    parser.add_argument('--delete-hourly', action='store_true',
                       help='Delete hourly files after successful aggregation')
    parser.add_argument('--hourly-dir', default='parquet/hourly',
                       help='Directory containing hourly files (default: parquet/hourly)')
    parser.add_argument('--daily-dir', default='parquet/daily',
                       help='Directory for daily files (default: parquet/daily)')
    parser.add_argument('--backup-dir', type=str,
                       help='Backup directory to copy files to (e.g., /mnt/usb3/tinkerboard/flights/daily)')

    args = parser.parse_args()

    # Determine date to process
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"ERROR: Invalid date format: {args.date}", file=sys.stderr)
            print("Use format: YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        # Default to yesterday
        target_date = datetime.now() - timedelta(days=1)
        print(f"No date specified, using yesterday: {target_date.strftime('%Y-%m-%d')}")

    try:
        success = aggregate_daily(
            target_date,
            args.hourly_dir,
            args.daily_dir,
            keep_hourly=not args.delete_hourly,
            backup_dir=args.backup_dir
        )
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
