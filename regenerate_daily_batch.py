#!/usr/bin/env python3
"""
Batch regenerate daily parquet files from hourly data.
Useful for fixing corrupted daily files or backfilling missing data.
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess


def regenerate_date_range(start_date: datetime, end_date: datetime,
                          hourly_dir: str, daily_dir: str,
                          script_path: str = 'aggregate_daily.py',
                          venv_python: str = None,
                          force: bool = False):
    """
    Regenerate daily files for a date range.

    Args:
        start_date: First date to regenerate
        end_date: Last date to regenerate (inclusive)
        hourly_dir: Directory containing hourly files
        daily_dir: Directory for daily files
        script_path: Path to aggregate_daily.py script
        venv_python: Path to venv python (if None, uses system python3)
        force: If True, regenerate even if daily file exists
    """
    hourly_path = Path(hourly_dir)
    daily_path = Path(daily_dir)

    if not hourly_path.exists():
        print(f"ERROR: Hourly directory not found: {hourly_dir}", file=sys.stderr)
        sys.exit(1)

    # Determine python command
    python_cmd = venv_python if venv_python else 'python3'

    print("="*70)
    print("BATCH DAILY FILE REGENERATION")
    print("="*70)
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Hourly directory: {hourly_dir}")
    print(f"Daily directory: {daily_dir}")
    print(f"Python: {python_cmd}")
    print(f"Force regenerate: {force}")
    print("="*70)
    print()

    # Count total days
    total_days = (end_date - start_date).days + 1

    # Track results
    success_count = 0
    skip_count = 0
    fail_count = 0
    failed_dates = []

    current_date = start_date
    day_num = 1

    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"\n[{day_num}/{total_days}] Processing {date_str}...")

        # Check if daily file already exists
        daily_file = daily_path / f"flights_daily_{date_str}.parquet"

        if daily_file.exists() and not force:
            file_size = daily_file.stat().st_size / (1024 * 1024)
            print(f"  ⊘ Daily file already exists ({file_size:.2f} MB) - skipping")
            print(f"     Use --force to regenerate")
            skip_count += 1
            current_date += timedelta(days=1)
            day_num += 1
            continue

        # Check if hourly files exist for this date
        pattern = f"flights_hourly_{date_str}_*.parquet"
        hourly_files = list(hourly_path.glob(pattern))

        if not hourly_files:
            print(f"  ⊘ No hourly files found for {date_str} - skipping")
            skip_count += 1
            current_date += timedelta(days=1)
            day_num += 1
            continue

        print(f"  → Found {len(hourly_files)} hourly files")

        # Run aggregate_daily.py for this date
        cmd = [
            python_cmd,
            script_path,
            '--date', date_str,
            '--hourly-dir', hourly_dir,
            '--daily-dir', daily_dir
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Check if output indicates success
            if 'Daily aggregation completed' in result.stdout:
                print(f"  ✓ Successfully regenerated daily file")
                success_count += 1
            else:
                print(f"  ⚠ Completed but with warnings")
                print(f"     Check output: {result.stdout[-200:]}")
                success_count += 1

        except subprocess.CalledProcessError as e:
            print(f"  ✗ FAILED to regenerate")
            print(f"     Error: {e.stderr[-200:] if e.stderr else 'Unknown error'}")
            fail_count += 1
            failed_dates.append(date_str)

        except Exception as e:
            print(f"  ✗ FAILED with exception: {e}")
            fail_count += 1
            failed_dates.append(date_str)

        current_date += timedelta(days=1)
        day_num += 1

    # Summary
    print("\n" + "="*70)
    print("REGENERATION SUMMARY")
    print("="*70)
    print(f"Total dates processed: {total_days}")
    print(f"  ✓ Successfully regenerated: {success_count}")
    print(f"  ⊘ Skipped (already exists): {skip_count}")
    print(f"  ✗ Failed: {fail_count}")

    if failed_dates:
        print(f"\nFailed dates:")
        for date in failed_dates:
            print(f"  - {date}")

    print("="*70)

    # Return exit code
    if fail_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Batch regenerate daily parquet files from hourly data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate all of December 2025
  python3 regenerate_daily_batch.py --start 2025-12-01 --end 2025-12-29

  # Regenerate specific problem period
  python3 regenerate_daily_batch.py --start 2025-12-12 --end 2025-12-28

  # Force regenerate even if files exist
  python3 regenerate_daily_batch.py --start 2025-12-01 --end 2025-12-29 --force

  # On littlebox with venv
  venv/bin/python3 regenerate_daily_batch.py \\
      --start 2025-12-01 --end 2025-12-29 \\
      --hourly-dir /mnt/usb3/tinkerboard/flights/hourly \\
      --daily-dir /mnt/usb3/tinkerboard/flights/daily \\
      --venv-python /mnt/usb3/tinkerboard/flight_to_duckdb/venv/bin/python3
        """
    )

    parser.add_argument('--start', required=True,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True,
                       help='End date (YYYY-MM-DD), inclusive')
    parser.add_argument('--hourly-dir', default='parquet/hourly',
                       help='Directory containing hourly files (default: parquet/hourly)')
    parser.add_argument('--daily-dir', default='parquet/daily',
                       help='Directory for daily files (default: parquet/daily)')
    parser.add_argument('--script-path', default='aggregate_daily.py',
                       help='Path to aggregate_daily.py script (default: aggregate_daily.py)')
    parser.add_argument('--venv-python', default=None,
                       help='Path to venv python interpreter (default: system python3)')
    parser.add_argument('--force', action='store_true',
                       help='Force regeneration even if daily file exists')

    args = parser.parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError as e:
        print(f"ERROR: Invalid date format: {e}", file=sys.stderr)
        print("Use format: YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    if start_date > end_date:
        print("ERROR: Start date must be before or equal to end date", file=sys.stderr)
        sys.exit(1)

    # Validate script exists
    script_path = Path(args.script_path)
    if not script_path.exists():
        print(f"ERROR: Script not found: {args.script_path}", file=sys.stderr)
        sys.exit(1)

    # Run regeneration
    regenerate_date_range(
        start_date,
        end_date,
        args.hourly_dir,
        args.daily_dir,
        str(script_path),
        args.venv_python,
        args.force
    )


if __name__ == '__main__':
    main()
