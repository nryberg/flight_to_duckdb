# Scheduled Parquet Pipeline Setup for Tinkerboard

This guide provides step-by-step instructions for configuring the automated Parquet data pipeline on Tinkerboard.

## Overview

The Parquet pipeline automatically captures and aggregates flight data on the following schedule:

- **Hourly Capture**: Every hour at :00 (captures all current flight data from `raw/` directory)
- **Daily Aggregation**: Every day at 1:00 AM (aggregates previous day's hourly files, removes duplicates)
- **Weekly Aggregation**: Every Monday at 2:00 AM (aggregates previous week's daily files)

### Backup Architecture

All files are automatically backed up from **tinkerboard** to **littlebox** using rsync over SSH:
- Files are created locally on tinkerboard in `~/flight_to_duckdb/parquet/`
- After each operation, files are synced to `littlebox:/mnt/usb3/tinkerboard/flights/`
- Rsync provides efficient, compressed transfers with automatic retry capability

## Prerequisites

### 1. Verify Tinkerboard Access

From your local machine, ensure you can SSH into Tinkerboard:

```bash
ssh tinkerboard
```

If this fails, you may need to configure SSH keys or update your SSH config.

### 2. Verify SSH Access to littlebox

From **tinkerboard**, verify SSH access to littlebox:

```bash
ssh littlebox
```

You should be able to connect without entering a password (SSH keys should be configured).

If SSH keys aren't set up yet:

```bash
# On tinkerboard, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "tinkerboard-to-littlebox"

# Copy your public key to littlebox
ssh-copy-id littlebox

# Test passwordless login
ssh littlebox "echo 'Connection successful'"
```

### 3. Verify Backup Directory on littlebox

From **tinkerboard**, check that the backup directory exists on littlebox:

```bash
ssh littlebox "ls -la /mnt/usb3/tinkerboard/"
```

If the directory doesn't exist, create it:

```bash
ssh littlebox "mkdir -p /mnt/usb3/tinkerboard/flights/{hourly,daily,weekly}"
```

### 4. Verify Python and Dependencies

On Tinkerboard, verify Python 3 and DuckDB are installed:

```bash
python3 --version
python3 -c "import duckdb; print(f'DuckDB version: {duckdb.__version__}')"
```

Expected output should show Python 3.7+ and DuckDB installation.

Also verify rsync is installed:

```bash
rsync --version
```

## Deployment Steps

### Step 1: Deploy Scripts to Tinkerboard

From your **local machine** (in the flight_to_duckdb directory):

```bash
# Make the deployment script executable (if not already)
chmod +x deploy_to_tinkerboard.sh

# Run the deployment script
./deploy_to_tinkerboard.sh
```

This script will:
- Test SSH connection to Tinkerboard
- Create directory structure on Tinkerboard
- Copy all Python scripts (capture_hourly.py, aggregate_daily.py, aggregate_weekly.py)
- Copy the Tinkerboard-specific cron setup script
- Make all scripts executable

**Expected output:**
```
=========================================
Deploy Parquet Pipeline to Tinkerboard
=========================================

Configuration:
  Remote host: tinkerboard
  Remote user: <your-username>
  Remote directory: /home/<your-username>/flight_to_duckdb

Testing connection to tinkerboard...
✓ Connection successful

Creating remote directory structure...
✓ Directory structure created

Copying Python scripts...
✓ Python scripts copied

Copying cron setup script...
✓ Cron setup script copied

Making scripts executable...
✓ Scripts are now executable

=========================================
Deployment Complete!
=========================================
```

### Step 2: SSH into Tinkerboard

```bash
ssh tinkerboard
```

### Step 3: Navigate to Deployment Directory

```bash
cd ~/flight_to_duckdb  # Or wherever you deployed to
```

Verify the scripts are present:

```bash
ls -la *.py *.sh
```

You should see:
- `capture_hourly.py`
- `aggregate_daily.py`
- `aggregate_weekly.py`
- `setup_parquet_cron.sh`

### Step 4: Verify Backup Directory Access on littlebox

From **tinkerboard**, create and verify the backup directory structure on littlebox:

```bash
ssh littlebox "mkdir -p /mnt/usb3/tinkerboard/flights/{hourly,daily,weekly}"
ssh littlebox "ls -la /mnt/usb3/tinkerboard/flights/"
```

You should see three subdirectories: `hourly/`, `daily/`, and `weekly/`.

### Step 5: Test Manual Capture (RECOMMENDED)

Before setting up automation, test the hourly capture manually with rsync backup to littlebox:

```bash
python3 capture_hourly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/hourly
```

**Expected output:**
```
Capturing hourly snapshot: flights_hourly_2025-11-23_1900.parquet
Timestamp: 2025-11-23 19:00:00
Processing aircraft.json...
Processing 120 history files...
Total observations collected: 15432

✓ Hourly snapshot saved: parquet/hourly/flights_hourly_2025-11-23_1900.parquet
  - Total records: 15432
  - Unique aircraft: 127
  - Time range: 2025-11-23 17:00:32 to 2025-11-23 19:00:15

Rsyncing to remote backup: littlebox:/mnt/usb3/tinkerboard/flights/hourly/flights_hourly_2025-11-23_1900.parquet
sending incremental file list
flights_hourly_2025-11-23_1900.parquet
          5,234,567 100%  512.34MB/s    0:00:00 (xfr#1, to-chk=0/1)
✓ Remote backup completed via rsync
```

If this succeeds, you're ready to set up automation!

### Step 6: Set Up Cron Jobs

Run the cron setup script:

```bash
./setup_parquet_cron.sh
```

The script will:
1. Show you the cron jobs that will be added
2. Ask for confirmation
3. Backup your existing crontab (if any)
4. Add the new cron jobs

**Expected interaction:**
```
=========================================
Parquet Pipeline Cron Setup (Tinkerboard)
=========================================

This script will set up automated cron jobs for:
  1. Hourly capture  - Run every hour (with rsync backup to littlebox:/mnt/usb3/tinkerboard/flights/hourly)
  2. Daily aggregation - Run daily at 1:00 AM (with rsync backup to littlebox:/mnt/usb3/tinkerboard/flights/daily)
  3. Weekly aggregation - Run weekly on Monday at 2:00 AM (with rsync backup to littlebox:/mnt/usb3/tinkerboard/flights/weekly)

Testing SSH connection to littlebox...
✓ SSH connection to littlebox successful
Checking backup directory on littlebox...
✓ Backup directory ready: littlebox:/mnt/usb3/tinkerboard/flights

Using Python: /usr/bin/python3

The following cron entries will be added:

# Flight Data Parquet Pipeline (Tinkerboard)
# Managed by setup_parquet_cron.sh
# Backup location: littlebox:/mnt/usb3/tinkerboard/flights

# Hourly capture - runs at the top of every hour
# Captures current flight data and backs up to littlebox via rsync
0 * * * * cd /home/<user>/flight_to_duckdb && /usr/bin/python3 capture_hourly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/hourly >> parquet_hourly.log 2>&1

# Daily aggregation - runs at 1:00 AM every day
# Aggregates previous day's hourly files and backs up to littlebox via rsync
0 1 * * * cd /home/<user>/flight_to_duckdb && /usr/bin/python3 aggregate_daily.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/daily >> parquet_daily.log 2>&1

# Weekly aggregation - runs at 2:00 AM every Monday
# Aggregates previous week's daily files and backs up to littlebox via rsync
0 2 * * 1 cd /home/<user>/flight_to_duckdb && /usr/bin/python3 aggregate_weekly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/weekly >> parquet_weekly.log 2>&1

WARNING: This will modify your crontab!

Do you want to add these cron jobs? (y/N):
```

**Type `y` and press Enter to confirm.**

**Expected output:**
```
✓ Current crontab backed up to: crontab_backup_20251123_190000.txt
✓ Cron jobs added successfully!

Schedule:
  - Hourly capture:     Every hour at :00
  - Daily aggregation:  Every day at 1:00 AM
  - Weekly aggregation: Every Monday at 2:00 AM

Backup locations (on littlebox):
  - Hourly:  littlebox:/mnt/usb3/tinkerboard/flights/hourly/
  - Daily:   littlebox:/mnt/usb3/tinkerboard/flights/daily/
  - Weekly:  littlebox:/mnt/usb3/tinkerboard/flights/weekly/

Logs will be written to:
  - parquet_hourly.log
  - parquet_daily.log
  - parquet_weekly.log

To view current cron jobs:
  crontab -l

To edit cron jobs manually:
  crontab -e

To remove all cron jobs:
  crontab -r

Test the setup by running:
  python3 capture_hourly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/hourly

Note: Files are backed up to littlebox via rsync over SSH
```

### Step 7: Verify Cron Installation

Check that the cron jobs were added correctly:

```bash
crontab -l
```

You should see the three cron entries for hourly, daily, and weekly jobs.

## Monitoring and Verification

### Check Log Files

The scripts write to log files in the deployment directory. Monitor them to ensure everything is working:

```bash
# View hourly capture log (shows last 20 lines)
tail -20 parquet_hourly.log

# Follow hourly capture log in real-time
tail -f parquet_hourly.log

# View daily aggregation log
tail -20 parquet_daily.log

# View weekly aggregation log
tail -20 parquet_weekly.log
```

### Check Generated Files

**Hourly files** (generated every hour):
```bash
# Local files on tinkerboard
ls -lh parquet/hourly/ | tail -10

# Backup files on littlebox
ssh littlebox "ls -lh /mnt/usb3/tinkerboard/flights/hourly/ | tail -10"
```

**Daily files** (generated at 1 AM):
```bash
# Local files on tinkerboard
ls -lh parquet/daily/

# Backup files on littlebox
ssh littlebox "ls -lh /mnt/usb3/tinkerboard/flights/daily/"
```

**Weekly files** (generated Monday at 2 AM):
```bash
# Local files on tinkerboard
ls -lh parquet/weekly/

# Backup files on littlebox
ssh littlebox "ls -lh /mnt/usb3/tinkerboard/flights/weekly/"
```

### Verify File Contents

Use the validation script to check file integrity:

```bash
# Validate the latest hourly file
python3 validate_parquet.py --level hourly --parquet-dir parquet | head -50

# Validate a specific file
python3 validate_parquet.py --file parquet/hourly/flights_hourly_2025-11-23_1900.parquet
```

### Query Parquet Files

Run example queries on the Parquet data:

```bash
# Query latest daily file
python3 query_parquet_example.py --level daily

# Query latest hourly file
python3 query_parquet_example.py --level hourly

# Analyze trends across last 7 daily files
python3 query_parquet_example.py --level daily --multi --count 7
```

## Troubleshooting

### Cron Jobs Not Running

1. **Check cron service is running:**
   ```bash
   sudo service cron status
   ```

2. **Check cron logs:**
   ```bash
   sudo grep CRON /var/log/syslog | tail -20
   ```

3. **Verify Python path in crontab:**
   ```bash
   which python3
   crontab -l | grep python3
   ```
   Make sure the paths match.

### Backup Directory Issues

If backup operations fail:

1. **Check directory permissions:**
   ```bash
   ls -ld /mnt/usb3/tinkerboard/flights/
   ```

2. **Check disk space:**
   ```bash
   df -h /mnt/usb3/
   ```

3. **Test write access:**
   ```bash
   touch /mnt/usb3/tinkerboard/flights/test.txt && rm /mnt/usb3/tinkerboard/flights/test.txt
   ```

### No Data Being Captured

1. **Check raw data directory:**
   ```bash
   ls -la raw/*.json
   ```
   Make sure `aircraft.json` and `history_*.json` files exist and are recent.

2. **Run manual capture with verbose output:**
   ```bash
   python3 capture_hourly.py --backup-dir /mnt/usb3/tinkerboard/flights/hourly 2>&1 | tee test_capture.log
   ```

### Disk Space Issues

Monitor disk space usage:

```bash
# Check local disk space
df -h .

# Check USB drive space
df -h /mnt/usb3/

# Check size of parquet directories
du -sh parquet/*
du -sh /mnt/usb3/tinkerboard/flights/*
```

**Parquet file size estimates:**
- Hourly files: ~5-10 MB each (24 files/day = ~120-240 MB/day)
- Daily files: ~100-200 MB each (after deduplication)
- Weekly files: ~500 MB - 1 GB each

## Maintenance Tasks

### Clean Up Old Hourly Files

The hourly files accumulate quickly. You may want to clean them up after successful daily aggregation:

```bash
# Manually aggregate daily with cleanup
python3 aggregate_daily.py --delete-hourly

# Or schedule daily aggregation to clean up hourly files (edit crontab)
crontab -e
# Change the daily aggregation line to include --delete-hourly flag
```

### Clean Up Old Daily Files

Similarly, clean up daily files after weekly aggregation:

```bash
# Manually aggregate weekly with cleanup
python3 aggregate_weekly.py --delete-daily

# Or modify weekly cron job to include --delete-daily flag
crontab -e
```

### Verify Backup Integrity

Periodically verify that backup files are valid:

```bash
# Validate all daily backup files
python3 validate_parquet.py --level daily --parquet-dir /mnt/usb3/tinkerboard/flights
```

### Monitor Log File Growth

Log files grow over time. Rotate them periodically:

```bash
# Archive current logs
gzip parquet_hourly.log parquet_daily.log parquet_weekly.log

# Or delete old logs after archiving
rm parquet_*.log.gz
```

## Testing After Setup

### Wait for Next Hour

The easiest way to verify the setup is to wait for the next hour and check:

```bash
# Wait for the top of the hour, then check:
ls -lth parquet/hourly/ | head -5
tail -30 parquet_hourly.log
```

### Force a Test Run

Or manually trigger a capture to verify everything works:

```bash
python3 capture_hourly.py --backup-dir /mnt/usb3/tinkerboard/flights/hourly
```

### Check Tomorrow for Daily Aggregation

At 1:05 AM the next day, check for daily aggregation:

```bash
ls -lth parquet/daily/ | head -5
tail -50 parquet_daily.log
```

## Uninstalling

If you need to remove the cron jobs:

```bash
# View current crontab
crontab -l

# Edit to remove parquet pipeline entries
crontab -e

# Or remove all cron jobs (be careful!)
crontab -r
```

The cron setup script creates a backup of your crontab before making changes. Restore from backup if needed:

```bash
# List backups
ls -lh crontab_backup_*.txt

# Restore from backup
crontab crontab_backup_YYYYMMDD_HHMMSS.txt
```

## Summary

After completing this setup, your Tinkerboard will automatically:

1. ✅ Capture flight data every hour to Parquet files
2. ✅ Aggregate hourly data into daily files at 1 AM (with deduplication)
3. ✅ Aggregate daily data into weekly files every Monday at 2 AM
4. ✅ Back up all files to the USB drive at `/mnt/usb3/tinkerboard/flights/`
5. ✅ Log all operations for monitoring and troubleshooting

No manual intervention required! 🎉

## Additional Resources

- Main README: `README.md`
- Project documentation: `CLAUDE.md`
- Query examples: `python3 query_parquet_example.py --help`
- Validation tool: `python3 validate_parquet.py --help`
- Visualization tool: `python3 visualize_parquet.py --help`
