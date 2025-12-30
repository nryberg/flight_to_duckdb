#!/usr/bin/env python3
"""
Monitor parquet pipeline health and data quality.
Checks for recent hourly/daily/weekly files, validates file sizes, and reports any issues.
"""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta
import sys
import argparse


def check_hourly_files(hourly_dir: str, hours_back: int = 48):
    """Check hourly files for recent data."""
    print("="*60)
    print("HOURLY FILES CHECK")
    print("="*60)

    hourly_path = Path(hourly_dir)
    if not hourly_path.exists():
        print(f"❌ ERROR: Hourly directory not found: {hourly_dir}")
        return False

    # Check for files in the last N hours
    now = datetime.now()
    expected_files = []
    missing_files = []

    for i in range(hours_back):
        check_time = now - timedelta(hours=i)
        hour_timestamp = check_time.replace(minute=0, second=0, microsecond=0)
        filename = f"flights_hourly_{hour_timestamp.strftime('%Y-%m-%d_%H00')}.parquet"
        file_path = hourly_path / filename

        expected_files.append((hour_timestamp, file_path))
        if not file_path.exists():
            missing_files.append((hour_timestamp, filename))

    # Report summary
    found_count = len(expected_files) - len(missing_files)
    print(f"✓ Found {found_count}/{len(expected_files)} hourly files in last {hours_back} hours")

    if missing_files:
        print(f"\n⚠ Missing {len(missing_files)} hourly files:")
        for timestamp, filename in missing_files[-10:]:  # Show last 10 missing
            print(f"  - {filename} ({timestamp})")
        if len(missing_files) > 10:
            print(f"  ... and {len(missing_files) - 10} more")

    # Check most recent file
    if found_count > 0:
        recent_file = expected_files[0][1]
        if recent_file.exists():
            file_size = recent_file.stat().st_size / (1024 * 1024)
            print(f"\nMost recent file: {recent_file.name}")
            print(f"  Size: {file_size:.2f} MB")

            # Check file contents
            try:
                con = duckdb.connect(':memory:')
                stats = con.execute(f"""
                    SELECT
                        COUNT(*) as records,
                        COUNT(DISTINCT hex) as aircraft
                    FROM read_parquet('{recent_file}')
                """).fetchone()
                con.close()

                print(f"  Records: {stats[0]}")
                print(f"  Aircraft: {stats[1]}")

                if stats[0] == 0:
                    print("  ⚠ WARNING: File is empty!")
                    return False

            except Exception as e:
                print(f"  ❌ ERROR reading file: {e}")
                return False

    return found_count > 0


def check_daily_files(daily_dir: str, days_back: int = 7):
    """Check daily files for recent data."""
    print("\n" + "="*60)
    print("DAILY FILES CHECK")
    print("="*60)

    daily_path = Path(daily_dir)
    if not daily_path.exists():
        print(f"❌ ERROR: Daily directory not found: {daily_dir}")
        return False

    # Check for files in the last N days
    now = datetime.now()
    expected_files = []
    missing_files = []

    for i in range(1, days_back + 1):  # Start from yesterday
        check_date = (now - timedelta(days=i)).date()
        filename = f"flights_daily_{check_date}.parquet"
        file_path = daily_path / filename

        expected_files.append((check_date, file_path))
        if not file_path.exists():
            missing_files.append((check_date, filename))

    # Report summary
    found_count = len(expected_files) - len(missing_files)
    print(f"✓ Found {found_count}/{len(expected_files)} daily files in last {days_back} days")

    if missing_files:
        print(f"\n⚠ Missing {len(missing_files)} daily files:")
        for date, filename in missing_files:
            print(f"  - {filename}")

    # Check most recent valid file and identify problematic small files
    print("\nRecent daily files:")
    recent_files = sorted(daily_path.glob("flights_daily_*.parquet"), reverse=True)[:days_back]

    problematic_files = []
    valid_files = []

    for file_path in recent_files:
        file_size = file_path.stat().st_size / (1024 * 1024)

        # Check file contents
        try:
            con = duckdb.connect(':memory:')
            stats = con.execute(f"""
                SELECT
                    COUNT(*) as records,
                    COUNT(DISTINCT hex) as aircraft
                FROM read_parquet('{file_path}')
            """).fetchone()
            con.close()

            # Flag files with suspiciously small sizes or low record counts
            is_problematic = file_size < 0.5 or stats[0] < 1000

            status = "⚠" if is_problematic else "✓"
            print(f"  {status} {file_path.name}: {file_size:.2f} MB, {stats[0]} records, {stats[1]} aircraft")

            if is_problematic:
                problematic_files.append(file_path.name)
            else:
                valid_files.append((file_path, stats))

        except Exception as e:
            print(f"  ❌ {file_path.name}: ERROR - {e}")
            problematic_files.append(file_path.name)

    if problematic_files:
        print(f"\n⚠ Found {len(problematic_files)} problematic daily files (may be corrupted or incomplete)")

    return found_count > 0


def check_weekly_files(weekly_dir: str, weeks_back: int = 4):
    """Check weekly files for recent data."""
    print("\n" + "="*60)
    print("WEEKLY FILES CHECK")
    print("="*60)

    weekly_path = Path(weekly_dir)
    if not weekly_path.exists():
        print(f"❌ ERROR: Weekly directory not found: {weekly_dir}")
        return False

    # List all weekly files
    weekly_files = sorted(weekly_path.glob("flights_weekly_ending_*.parquet"), reverse=True)

    if not weekly_files:
        print("⚠ No weekly files found")
        return False

    print(f"✓ Found {len(weekly_files)} weekly files")
    print(f"\nShowing last {min(weeks_back, len(weekly_files))} weekly files:")

    for file_path in weekly_files[:weeks_back]:
        file_size = file_path.stat().st_size / (1024 * 1024)

        # Check file contents
        try:
            con = duckdb.connect(':memory:')
            stats = con.execute(f"""
                SELECT
                    COUNT(*) as records,
                    COUNT(DISTINCT hex) as aircraft
                FROM read_parquet('{file_path}')
            """).fetchone()
            con.close()

            print(f"  ✓ {file_path.name}: {file_size:.2f} MB, {stats[0]} records, {stats[1]} aircraft")

        except Exception as e:
            print(f"  ❌ {file_path.name}: ERROR - {e}")

    return True


def check_logs(log_dir: str):
    """Check recent log files for errors."""
    print("\n" + "="*60)
    print("RECENT LOG ACTIVITY")
    print("="*60)

    log_path = Path(log_dir)

    log_files = {
        'parquet_hourly.log': 'Hourly Capture',
        'parquet_daily.log': 'Daily Aggregation',
        'parquet_weekly.log': 'Weekly Aggregation',
        'minio_upload_hourly.log': 'MinIO Upload (Hourly)',
        'minio_upload_daily.log': 'MinIO Upload (Daily)',
        'minio_upload_weekly.log': 'MinIO Upload (Weekly)'
    }

    for log_file, description in log_files.items():
        file_path = log_path / log_file

        if not file_path.exists():
            print(f"⊘ {description}: No log file found")
            continue

        # Get last modified time
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime

        # Read last few lines
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-5:] if len(lines) >= 5 else lines

            # Check for errors
            has_error = any('ERROR' in line or 'Error' in line or 'Traceback' in line
                          for line in last_lines)

            status = "❌" if has_error else "✓"
            print(f"{status} {description}: Last updated {age.total_seconds()/3600:.1f}h ago")

            if has_error:
                print(f"   ⚠ Recent errors detected - check {log_file}")

        except Exception as e:
            print(f"❌ {description}: Could not read log - {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Monitor parquet pipeline health and data quality'
    )
    parser.add_argument('--hourly-dir', default='/mnt/usb3/tinkerboard/flights/hourly',
                       help='Directory containing hourly files')
    parser.add_argument('--daily-dir', default='/mnt/usb3/tinkerboard/flights/daily',
                       help='Directory containing daily files')
    parser.add_argument('--weekly-dir', default='/mnt/usb3/tinkerboard/flights/weekly',
                       help='Directory containing weekly files')
    parser.add_argument('--log-dir', default='/mnt/usb3/tinkerboard/flight_to_duckdb',
                       help='Directory containing log files')
    parser.add_argument('--hours-back', type=int, default=48,
                       help='Hours back to check for hourly files (default: 48)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Days back to check for daily files (default: 7)')
    parser.add_argument('--weeks-back', type=int, default=4,
                       help='Weeks back to show for weekly files (default: 4)')

    args = parser.parse_args()

    print("PARQUET PIPELINE MONITORING REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        hourly_ok = check_hourly_files(args.hourly_dir, args.hours_back)
        daily_ok = check_daily_files(args.daily_dir, args.days_back)
        weekly_ok = check_weekly_files(args.weekly_dir, args.weeks_back)
        check_logs(args.log_dir)

        # Overall status
        print("\n" + "="*60)
        print("OVERALL STATUS")
        print("="*60)

        if hourly_ok and daily_ok and weekly_ok:
            print("✓ All pipeline stages appear healthy")
            sys.exit(0)
        else:
            print("⚠ Some pipeline stages have issues - review details above")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR during monitoring: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
