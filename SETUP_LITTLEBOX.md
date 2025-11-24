# Littlebox Setup Guide

This guide walks you through setting up the Parquet data pipeline on **littlebox**, which will process raw flight data received from tinkerboard.

## Architecture Overview

- **Tinkerboard**: Collects ADS-B data, syncs raw JSON to littlebox every 20 minutes
- **Littlebox**: Processes JSON into Parquet files, stores on USB3 drive

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete details.

## Prerequisites

### 1. Verify Python 3 and Dependencies

On littlebox:

```bash
python3 --version
# Should show Python 3.7+

# Check for required system packages
sudo apt update
sudo apt install -y \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    git \
    rsync
```

### 2. Verify USB Drive is Mounted

```bash
ls -la /mnt/usb3/tinkerboard/
```

If the directory doesn't exist:

```bash
sudo mkdir -p /mnt/usb3/tinkerboard
# Mount your USB drive here (your specific mount command may vary)
```

### 3. Verify SSH Access from Tinkerboard

From **tinkerboard**, test SSH to littlebox:

```bash
ssh littlebox "echo 'Connection successful'"
```

Should connect without password. If not, set up SSH keys (see SCHEDULED.md).

## Setup Steps

### Step 1: Create Directory Structure

On littlebox:

```bash
# Create base directory on USB drive
sudo mkdir -p /mnt/usb3/tinkerboard/{raw,flight_to_duckdb,flights/{hourly,daily,weekly}}

# Set ownership (replace 'nick' with your username)
sudo chown -R nick:nick /mnt/usb3/tinkerboard/

# Verify
ls -la /mnt/usb3/tinkerboard/
```

### Step 2: Deploy Scripts to Littlebox

From your **local development machine**:

```bash
# In your local flight_to_duckdb directory
cd /path/to/flight_to_duckdb

# Copy scripts to littlebox
scp capture_hourly.py aggregate_daily.py aggregate_weekly.py \
    setup_venv.sh validate_parquet.py query_parquet_example.py \
    visualize_parquet.py \
    littlebox:/mnt/usb3/tinkerboard/flight_to_duckdb/

# Make scripts executable
ssh littlebox "chmod +x /mnt/usb3/tinkerboard/flight_to_duckdb/*.py /mnt/usb3/tinkerboard/flight_to_duckdb/*.sh"
```

### Step 3: Set Up Python Virtual Environment

On littlebox:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Run the setup script
./setup_venv.sh
```

This will:
- Create `venv/` directory
- Install pip, DuckDB, and Folium
- Verify installations

**Expected output:**
```
=========================================
Python Virtual Environment Setup
=========================================

Found: Python 3.x.x
Python version: 3.x

Checking for python3-venv package...
✓ python3-venv is available

Creating virtual environment...
✓ Virtual environment created

Upgrading pip...
✓ pip upgraded

Installing required packages...
[1/2] Installing duckdb (this may take 5-10 minutes to compile)...
✓ DuckDB installed

[2/2] Installing folium (for visualization - optional)...
✓ Folium installed

✓ All packages installed successfully

Verifying installations...
✓ DuckDB version: 0.9.2
✓ Folium version: 0.15.0
```

**Note**: DuckDB may take several minutes to compile on first install.

### Step 4: Test Manual Capture

Before setting up automation, test the hourly capture:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Run manually (make sure raw/ directory has some JSON files first)
venv/bin/python3 capture_hourly.py \
    --raw-dir /mnt/usb3/tinkerboard/raw \
    --output-dir /mnt/usb3/tinkerboard/flights/hourly
```

**Expected output:**
```
Capturing hourly snapshot: flights_hourly_2025-11-23_1900.parquet
Timestamp: 2025-11-23 19:00:00
Processing aircraft.json...
Processing 120 history files...
Total observations collected: 15432

✓ Hourly snapshot saved: /mnt/usb3/tinkerboard/flights/hourly/flights_hourly_2025-11-23_1900.parquet
  - Total records: 15432
  - Unique aircraft: 127
  - Time range: 2025-11-23 17:00:32 to 2025-11-23 19:00:15
```

### Step 5: Set Up Cron Jobs

Create a cron setup script for littlebox:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Create cron setup script
cat > setup_cron_littlebox.sh << 'EOF'
#!/bin/bash

WORK_DIR="/mnt/usb3/tinkerboard/flight_to_duckdb"
PYTHON="${WORK_DIR}/venv/bin/python3"

# Generate cron entries
CRON_ENTRIES=$(cat <<CRON
# Flight Data Parquet Pipeline (Littlebox)
# Process data from tinkerboard

# Hourly capture - process all raw JSON into Parquet
0 * * * * cd ${WORK_DIR} && ${PYTHON} capture_hourly.py --raw-dir /mnt/usb3/tinkerboard/raw --output-dir /mnt/usb3/tinkerboard/flights/hourly >> parquet_hourly.log 2>&1

# Daily aggregation - combine hourly files, remove duplicates
0 1 * * * cd ${WORK_DIR} && ${PYTHON} aggregate_daily.py --hourly-dir /mnt/usb3/tinkerboard/flights/hourly --daily-dir /mnt/usb3/tinkerboard/flights/daily >> parquet_daily.log 2>&1

# Weekly aggregation - combine daily files
0 2 * * 1 cd ${WORK_DIR} && ${PYTHON} aggregate_weekly.py --daily-dir /mnt/usb3/tinkerboard/flights/daily --weekly-dir /mnt/usb3/tinkerboard/flights/weekly >> parquet_weekly.log 2>&1
CRON
)

echo "Adding cron jobs..."
echo "$CRON_ENTRIES"
echo ""

read -p "Add these cron jobs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    (crontab -l 2>/dev/null; echo ""; echo "$CRON_ENTRIES") | crontab -
    echo "✓ Cron jobs added"
    echo ""
    echo "View with: crontab -l"
else
    echo "Cancelled"
fi
EOF

chmod +x setup_cron_littlebox.sh

# Run it
./setup_cron_littlebox.sh
```

Type `y` when prompted to add the cron jobs.

### Step 6: Verify Cron Installation

```bash
crontab -l
```

You should see three cron entries for hourly, daily, and weekly processing.

## Tinkerboard Configuration

Now configure tinkerboard to sync data to littlebox.

### On Your Local Machine

Deploy the sync script to tinkerboard:

```bash
cd /path/to/flight_to_duckdb

scp sync_raw_to_littlebox.sh tinkerboard:~/
ssh tinkerboard "chmod +x ~/sync_raw_to_littlebox.sh"
```

### On Tinkerboard

Set up the cron job:

```bash
# Add to crontab
crontab -e
```

Add this line:

```cron
# Sync raw flight data to littlebox every 20 minutes
*/20 * * * * /home/nick/sync_raw_to_littlebox.sh >> /home/nick/sync_raw.log 2>&1
```

Save and exit.

### Test the Sync

On tinkerboard:

```bash
# Run manually to test
./sync_raw_to_littlebox.sh
```

**Expected output:**
```
=========================================
Sync started: 2025-11-23 19:00:00
=========================================
Found 121 JSON files in /run/dump1090-fa

Syncing to littlebox:/mnt/usb3/tinkerboard/raw...
sending incremental file list
aircraft.json
history_0.json
history_1.json
...

✓ Sync completed successfully
  Files synced: 121
  Destination: littlebox:/mnt/usb3/tinkerboard/raw

Sync finished: 2025-11-23 19:00:05
```

Verify on littlebox:

```bash
ls -lh /mnt/usb3/tinkerboard/raw/*.json | wc -l
# Should show 121 files
```

## Monitoring

### On Littlebox

Check parquet pipeline logs:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# View recent hourly captures
tail -50 parquet_hourly.log

# View daily aggregations
tail -50 parquet_daily.log

# View weekly aggregations
tail -50 parquet_weekly.log

# Check generated files
ls -lh /mnt/usb3/tinkerboard/flights/hourly/ | tail -10
ls -lh /mnt/usb3/tinkerboard/flights/daily/
ls -lh /mnt/usb3/tinkerboard/flights/weekly/
```

### On Tinkerboard

Check sync logs:

```bash
tail -50 ~/sync_raw.log
```

### Disk Usage

Monitor disk space on littlebox:

```bash
df -h /mnt/usb3/
du -sh /mnt/usb3/tinkerboard/flights/*
```

**Expected sizes:**
- Hourly files: ~10 MB each (24/day)
- Daily files: ~200 MB each (after deduplication)
- Weekly files: ~1 GB each

## Validation & Queries

### Validate Parquet Files

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Validate latest hourly file
venv/bin/python3 validate_parquet.py --level hourly --parquet-dir /mnt/usb3/tinkerboard/flights

# Validate latest daily file
venv/bin/python3 validate_parquet.py --level daily --parquet-dir /mnt/usb3/tinkerboard/flights
```

### Query Examples

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Query latest daily file
venv/bin/python3 query_parquet_example.py \
    --level daily \
    --parquet-dir /mnt/usb3/tinkerboard/flights

# Analyze trends across last 7 days
venv/bin/python3 query_parquet_example.py \
    --level daily \
    --multi --count 7 \
    --parquet-dir /mnt/usb3/tinkerboard/flights
```

### Generate Visualizations

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Create map from latest daily file
venv/bin/python3 visualize_parquet.py \
    --level daily \
    --parquet-dir /mnt/usb3/tinkerboard/flights \
    --output /tmp/flight_map.html

# View the map (copy to local machine or open in browser)
```

## Troubleshooting

### No Data in raw/ Directory

**Problem**: `/mnt/usb3/tinkerboard/raw/` is empty

**Check**:
1. Is tinkerboard sync cron running?
   ```bash
   # On tinkerboard
   tail -f ~/sync_raw.log
   ```

2. Is dump1090-fa running on tinkerboard?
   ```bash
   # On tinkerboard
   systemctl status dump1090-fa
   ls -l /run/dump1090-fa/*.json
   ```

3. Can tinkerboard reach littlebox?
   ```bash
   # On tinkerboard
   ping littlebox
   ssh littlebox "echo 'test'"
   ```

### Parquet Pipeline Not Running

**Problem**: No new hourly files being created

**Check**:
1. Are cron jobs set up?
   ```bash
   # On littlebox
   crontab -l | grep parquet
   ```

2. Check logs for errors:
   ```bash
   # On littlebox
   cd /mnt/usb3/tinkerboard/flight_to_duckdb
   tail -100 parquet_hourly.log
   ```

3. Test manually:
   ```bash
   cd /mnt/usb3/tinkerboard/flight_to_duckdb
   venv/bin/python3 capture_hourly.py \
       --raw-dir /mnt/usb3/tinkerboard/raw \
       --output-dir /mnt/usb3/tinkerboard/flights/hourly
   ```

### Disk Space Issues

**Problem**: USB drive full

**Solutions**:
1. Clean up old hourly files:
   ```bash
   # Keep only last 7 days of hourly files
   find /mnt/usb3/tinkerboard/flights/hourly/ -name "*.parquet" -mtime +7 -delete
   ```

2. Clean up old daily files:
   ```bash
   # Keep only last 30 days of daily files
   find /mnt/usb3/tinkerboard/flights/daily/ -name "*.parquet" -mtime +30 -delete
   ```

3. Use aggregation cleanup flags:
   ```bash
   # Edit cron to delete hourly after daily aggregation
   venv/bin/python3 aggregate_daily.py --delete-hourly ...

   # Delete daily after weekly aggregation
   venv/bin/python3 aggregate_weekly.py --delete-daily ...
   ```

## Summary

After completing this setup:

✅ **Tinkerboard**: Syncs raw JSON data to littlebox every 20 minutes
✅ **Littlebox**: Processes data into Parquet files every hour
✅ **Littlebox**: Aggregates data daily (1 AM) and weekly (Monday 2 AM)
✅ **Storage**: All data stored on littlebox USB drive
✅ **Monitoring**: Logs available on both machines

The system runs automatically with no manual intervention required! 🎉

## Next Steps

- **MinIO Upload** (Recommended): Set up automated upload of hourly files to MinIO object storage for off-site backup. See [MINIO_SETUP.md](MINIO_SETUP.md)
- Set up disk space monitoring/alerts
- Configure log rotation
- Create data analysis notebooks using the Parquet data
