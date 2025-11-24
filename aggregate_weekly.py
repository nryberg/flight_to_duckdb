#!/usr/bin/env python3
"""
Aggregate daily Parquet files into weekly files.
Concatenates all daily files from a given week into a single weekly file.
"""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta
import sys
import argparse
import shutil
import subprocess


def get_week_boundaries(end_date: datetime):
    """
    Get the start and end dates for a week ending on the given date.
    Week is defined as 7 days ending on Sunday.

    Args:
        end_date: The last day of the week (should be a Sunday)

    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    # If end_date is not a Sunday, find the next Sunday
    days_until_sunday = (6 - end_date.weekday()) % 7
    if days_until_sunday > 0:
        end_date = end_date + timedelta(days=days_until_sunday)

    # Start is 6 days before end (7 days total including end)
    start_date = end_date - timedelta(days=6)

    return start_date, end_date


def aggregate_weekly(end_date: datetime, daily_dir: str = 'parquet/daily',
                    weekly_dir: str = 'parquet/weekly', keep_daily: bool = True,
                    backup_dir: str = None):
    """
    Aggregate daily parquet files into a single weekly file.

    Args:
        end_date: Last day of the week to aggregate (will be adjusted to Sunday)
        daily_dir: Directory containing daily Parquet files
        weekly_dir: Directory to save weekly Parquet files
        keep_daily: If True, keep daily files after aggregation
        backup_dir: Optional backup directory to copy files to (e.g., /mnt/usb3/tinkerboard/flights/weekly)
    """
    daily_path = Path(daily_dir)
    weekly_path = Path(weekly_dir)
    weekly_path.mkdir(parents=True, exist_ok=True)

    # Get week boundaries
    start_date, actual_end_date = get_week_boundaries(end_date)

    print(f"Aggregating weekly file")
    print(f"  Week: {start_date.strftime('%Y-%m-%d')} to {actual_end_date.strftime('%Y-%m-%d')}")
    print(f"  ({start_date.strftime('%A')} to {actual_end_date.strftime('%A')})")

    # Find all daily files for this week
    daily_files = []
    current_date = start_date
    while current_date <= actual_end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        daily_file = daily_path / f"flights_daily_{date_str}.parquet"
        if daily_file.exists():
            daily_files.append(daily_file)
        current_date += timedelta(days=1)

    if not daily_files:
        print(f"No daily files found for week ending {actual_end_date.strftime('%Y-%m-%d')}")
        return False

    print(f"\nFound {len(daily_files)} daily files:")
    for f in daily_files:
        print(f"  - {f.name}")

    # Output filename with week ending date
    output_file = weekly_path / f"flights_weekly_ending_{actual_end_date.strftime('%Y-%m-%d')}.parquet"

    # Use DuckDB to aggregate
    con = duckdb.connect(':memory:')

    # Read all daily files
    daily_files_str = ', '.join([f"'{f}'" for f in daily_files])

    print(f"\nLoading {len(daily_files)} daily files...")
    con.execute(f"""
        CREATE TABLE weekly_data AS
        SELECT * FROM read_parquet([{daily_files_str}])
    """)

    # Get statistics
    stats = con.execute("""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest,
            COUNT(DISTINCT source_file) as source_files
        FROM weekly_data
    """).fetchone()

    # Check for any duplicates (shouldn't be any if daily aggregation worked correctly)
    duplicate_check = con.execute("""
        SELECT COUNT(*) as duplicates
        FROM (
            SELECT hex, observation_epoch, COUNT(*) as cnt
            FROM weekly_data
            GROUP BY hex, observation_epoch
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    if duplicate_check > 0:
        print(f"WARNING: Found {duplicate_check} duplicate (hex, observation_epoch) pairs")
        print("This suggests the daily aggregation may have issues.")

    # Write to Parquet
    print(f"\nWriting weekly file: {output_file}")
    con.execute(f"COPY weekly_data TO '{output_file}' (FORMAT PARQUET)")

    con.close()

    print(f"\n✓ Weekly aggregation completed: {output_file}")
    print(f"  - Week ending: {actual_end_date.strftime('%Y-%m-%d (%A)')}")
    print(f"  - Total records: {stats[0]}")
    print(f"  - Unique aircraft: {stats[1]}")
    print(f"  - Time range: {stats[2]} to {stats[3]}")
    print(f"  - Source files: {stats[4]}")
    print(f"  - Daily files used: {len(daily_files)}")

    # Copy to backup directory if specified
    if backup_dir:
        # Check if backup_dir is a remote path (contains ':')
        if ':' in backup_dir:
            # Remote backup using rsync
            remote_file = f"{backup_dir}/{output_file.name}"
            print(f"\nRsyncing to remote backup: {remote_file}")

            try:
                # Use rsync with compression and progress
                result = subprocess.run(
                    ['rsync', '-avz', '--progress', str(output_file), remote_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"✓ Remote backup completed via rsync")
            except subprocess.CalledProcessError as e:
                print(f"WARNING: Backup failed: {e.stderr}", file=sys.stderr)
            except FileNotFoundError:
                print(f"WARNING: rsync not found. Skipping remote backup.", file=sys.stderr)
        else:
            # Local backup using shutil
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            backup_file = backup_path / output_file.name

            print(f"\nCopying to backup location: {backup_file}")
            shutil.copy2(output_file, backup_file)
            print(f"✓ Backup copy completed")

    # Clean up daily files if requested
    if not keep_daily:
        print(f"\nRemoving {len(daily_files)} daily files...")
        for f in daily_files:
            f.unlink()
            print(f"  Deleted: {f.name}")

    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Aggregate daily Parquet files into weekly files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate last week (ending on most recent Sunday)
  python3 aggregate_weekly.py

  # Aggregate week ending on specific date (will adjust to Sunday if needed)
  python3 aggregate_weekly.py --end-date 2025-11-24

  # Aggregate and delete daily files
  python3 aggregate_weekly.py --end-date 2025-11-24 --delete-daily

Note: Weeks are defined as 7 days ending on Sunday.
      If you specify a date that's not Sunday, it will be adjusted to the next Sunday.
        """
    )

    parser.add_argument('--end-date', type=str,
                       help='Last day of week to aggregate (YYYY-MM-DD). Will adjust to Sunday. Default: last Sunday')
    parser.add_argument('--delete-daily', action='store_true',
                       help='Delete daily files after successful aggregation')
    parser.add_argument('--daily-dir', default='parquet/daily',
                       help='Directory containing daily files (default: parquet/daily)')
    parser.add_argument('--weekly-dir', default='parquet/weekly',
                       help='Directory for weekly files (default: parquet/weekly)')
    parser.add_argument('--backup-dir', type=str,
                       help='Backup directory - local path or remote (e.g., littlebox:/mnt/usb3/tinkerboard/flights/weekly)')

    args = parser.parse_args()

    # Determine end date to process
    if args.end_date:
        try:
            target_end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"ERROR: Invalid date format: {args.end_date}", file=sys.stderr)
            print("Use format: YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        # Default to last Sunday
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7  # Monday=0, Sunday=6
        if days_since_sunday == 0:
            # Today is Sunday, use last Sunday
            target_end_date = today - timedelta(days=7)
        else:
            target_end_date = today - timedelta(days=days_since_sunday)

        print(f"No end date specified, using last Sunday: {target_end_date.strftime('%Y-%m-%d')}")

    try:
        success = aggregate_weekly(
            target_end_date,
            args.daily_dir,
            args.weekly_dir,
            keep_daily=not args.delete_daily,
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
