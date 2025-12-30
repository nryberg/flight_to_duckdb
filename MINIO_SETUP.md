# MinIO Upload Setup

This guide walks through setting up automated upload of Parquet files (hourly/daily/weekly) to MinIO object storage.

## Overview

The `upload_to_minio.py` script uploads Parquet files to a MinIO server for:
- Off-site backup
- Long-term storage
- Cloud access to flight data
- Integration with analytics tools

**Supports three levels**:
- **Hourly**: Uploads yesterday's hourly files (runs daily at 2:30 AM)
- **Daily**: Uploads yesterday's daily file (runs daily at 1:30 AM)
- **Weekly**: Uploads last week's weekly file (runs Monday at 2:30 AM)

## Prerequisites

### 1. MinIO Server Access

You need access to a MinIO server with:
- **Endpoint**: MinIO server URL (e.g., `http://100.107.134.23:9000`)
- **Access Key**: Your MinIO access key
- **Secret Key**: Your MinIO secret key

### 2. Python Dependencies

The script requires additional packages (`minio` and `python-dotenv`):

```bash
# On littlebox
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# If venv already exists, activate and install
source venv/bin/activate
pip install minio python-dotenv

# Or re-run setup script (will install all packages including new ones)
./setup_venv.sh
```

## Setup Steps

### Step 1: Create MinIO Bucket

Create the bucket in MinIO before running the upload script:

**Option A: Using MinIO Web Console**
1. Open MinIO console: `http://100.107.134.23:9000` (or your MinIO URL)
2. Log in with your credentials
3. Click "Buckets" → "Create Bucket"
4. Enter bucket name: `flight-parquet`
5. Click "Create"

**Option B: Using mc (MinIO Client)**
```bash
# Install mc if not already installed
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure mc
mc alias set myminio http://100.107.134.23:9000 YOUR_ACCESS_KEY YOUR_SECRET_KEY

# Create bucket
mc mb myminio/flight-parquet
```

**Option C: Script creates it automatically**
The Python script will create the bucket if it doesn't exist (requires appropriate permissions).

### Step 2: Configure Credentials

Create a `.env` file in the `flight_to_duckdb` directory:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env
```

Update the `.env` file with your MinIO credentials:

```bash
# MinIO server endpoint (without http://)
# Format: host:port
MINIO_ENDPOINT=100.107.134.23:9000

# MinIO access credentials
MINIO_ACCESS_KEY=your_actual_access_key
MINIO_SECRET_KEY=your_actual_secret_key
```

**Security Note**: The `.env` file contains secrets and should never be committed to git. It's already in `.gitignore`.

### Step 3: Test Manual Upload

Before setting up automation, test the upload manually:

```bash
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Upload yesterday's hourly files (default)
venv/bin/python3 upload_to_minio.py --level hourly

# Upload yesterday's daily file
venv/bin/python3 upload_to_minio.py --level daily

# Upload last week's weekly file
venv/bin/python3 upload_to_minio.py --level weekly

# Upload multiple days back
venv/bin/python3 upload_to_minio.py --level hourly --days-back 7

# Custom options
venv/bin/python3 upload_to_minio.py \
    --level daily \
    --parquet-dir /mnt/usb3/tinkerboard/flights/daily \
    --bucket flight-parquet \
    --days-back 1
```

**Expected output (hourly):**
```
Auto-detected parquet directory: /mnt/usb3/tinkerboard/flights/hourly
==================================================
MinIO Hourly Parquet Upload
==================================================
MinIO endpoint: localhost:9199
Bucket: flight-parquet
Level: hourly
Parquet directory: /mnt/usb3/tinkerboard/flights/hourly
Days/weeks back: 1
Delete after upload: False
==================================================

Connecting to MinIO at localhost:9199 (secure=False)...
✓ Bucket 'flight-parquet' exists

Looking for hourly files from 2025-11-24 to 2025-11-24...
Found 24 files to upload
↑ Uploading flights_hourly_2025-11-24_0000.parquet (8.32 MB)... ✓
↑ Uploading flights_hourly_2025-11-24_0100.parquet (7.89 MB)... ✓
...
↑ Uploading flights_hourly_2025-11-24_2300.parquet (9.14 MB)... ✓

==================================================
Upload Summary:
  Uploaded: 24 files
  Skipped:  0 files (already exist)
  Failed:   0 files
==================================================
```

### Step 4: Set Up Automated Cron Jobs

Add cron jobs to upload all three levels automatically:

```bash
# Edit crontab
crontab -e
```

Add these lines:

```cron
# MinIO Uploads - upload Parquet files to object storage

# Upload hourly files daily at 2:30 AM (after all hourly captures)
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --level hourly >> minio_upload_hourly.log 2>&1

# Upload daily file at 1:30 AM (after daily aggregation at 1 AM)
30 1 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --level daily >> minio_upload_daily.log 2>&1

# Upload weekly file on Mondays at 2:30 AM (after weekly aggregation at 2 AM)
30 2 * * 1 cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --level weekly >> minio_upload_weekly.log 2>&1
```

**Optional**: Add `--delete-after-upload` flag to save disk space by removing local files after successful upload:

```cron
# Example: Delete hourly files after upload
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --level hourly --delete-after-upload >> minio_upload_hourly.log 2>&1
```

**Complete Schedule**:
- **Hourly capture**: Every hour (top of the hour)
- **Daily aggregation**: 1:00 AM
- **Daily MinIO upload**: 1:30 AM (30 min after daily aggregation)
- **Weekly aggregation**: Monday 2:00 AM
- **Hourly MinIO upload**: 2:30 AM (after all hourly files collected)
- **Weekly MinIO upload**: Monday 2:30 AM (30 min after weekly aggregation)

### Step 5: Verify Cron Installation

```bash
# View cron jobs
crontab -l | grep minio

# Check log after first run (next day after 2:30 AM)
tail -50 /mnt/usb3/tinkerboard/flight_to_duckdb/minio_upload.log
```

## Usage Options

### Command Line Arguments

```bash
# Basic usage (default: yesterday's files)
venv/bin/python3 upload_to_minio.py

# Upload last 7 days of hourly files
venv/bin/python3 upload_to_minio.py --days-back 7

# Custom bucket name
venv/bin/python3 upload_to_minio.py --bucket my-custom-bucket

# Delete local files after successful upload (save disk space)
venv/bin/python3 upload_to_minio.py --delete-after-upload

# Custom hourly directory
venv/bin/python3 upload_to_minio.py --hourly-dir /path/to/hourly/files

# Custom .env file location
venv/bin/python3 upload_to_minio.py --env-file /path/to/.env

# Combine options
venv/bin/python3 upload_to_minio.py \
    --days-back 3 \
    --bucket flight-parquet \
    --delete-after-upload
```

### Script Behavior

- **Duplicate Detection**: Files already uploaded are skipped (no re-upload)
- **Date Filtering**: Only uploads files within specified date range
- **Error Handling**: Failed uploads are logged and reported
- **Atomic Operations**: Each file upload is independent
- **Object Storage Path**: Files stored as `hourly/flights_hourly_YYYY-MM-DD_HH00.parquet`

## Monitoring

### Check Upload Logs

```bash
# View recent uploads
tail -50 /mnt/usb3/tinkerboard/flight_to_duckdb/minio_upload.log

# Follow log in real-time
tail -f /mnt/usb3/tinkerboard/flight_to_duckdb/minio_upload.log

# Search for errors
grep -i error /mnt/usb3/tinkerboard/flight_to_duckdb/minio_upload.log
```

### Verify Files in MinIO

**Using MinIO Web Console**:
1. Open `http://100.107.134.23:9000`
2. Navigate to `flight-parquet` bucket
3. Browse `hourly/` prefix
4. Check file sizes and timestamps

**Using mc (MinIO Client)**:
```bash
# List files in bucket
mc ls myminio/flight-parquet/hourly/

# List files from specific date
mc ls myminio/flight-parquet/hourly/ | grep 2025-11-23

# Check bucket size
mc du myminio/flight-parquet
```

### Disk Space Management

If using `--delete-after-upload` flag:

```bash
# Check local disk space before/after
df -h /mnt/usb3/

# Check hourly directory size
du -sh /mnt/usb3/tinkerboard/flights/hourly/

# Count remaining local hourly files
ls -1 /mnt/usb3/tinkerboard/flights/hourly/*.parquet | wc -l
```

## Troubleshooting

### Connection Refused / Network Issues

**Problem**: Cannot connect to MinIO server

**Check**:
```bash
# Test network connectivity
ping 100.107.134.23

# Test MinIO port
telnet 100.107.134.23 9000

# Or using curl
curl http://100.107.134.23:9000
```

### Authentication Failed

**Problem**: Access denied or invalid credentials

**Solutions**:
1. Verify credentials in `.env` file
2. Check MinIO console to ensure user has appropriate permissions
3. Test credentials using mc:
   ```bash
   mc alias set test http://100.107.134.23:9000 YOUR_KEY YOUR_SECRET
   mc ls test/
   ```

### Bucket Not Found

**Problem**: Bucket doesn't exist

**Solutions**:
- Create bucket manually in MinIO console
- Or let the script create it (requires `s3:CreateBucket` permission)
- Verify bucket name matches (case-sensitive)

### No Files to Upload

**Problem**: Script reports no files found

**Check**:
```bash
# Verify hourly files exist
ls -lh /mnt/usb3/tinkerboard/flights/hourly/*.parquet

# Check file naming pattern
ls -1 /mnt/usb3/tinkerboard/flights/hourly/ | head -5

# Verify date range
python3 -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(days=1)).date())"
```

### Upload Fails Partway Through

**Problem**: Some files upload, then script fails

**Cause**: Network interruption, disk space, or permission issues

**Recovery**:
- Script automatically skips already-uploaded files
- Simply re-run the script:
  ```bash
  venv/bin/python3 upload_to_minio.py
  ```
- Already uploaded files will be skipped
- Only failed files will be re-attempted

## Storage Estimates

Typical file sizes and storage requirements:

- **Hourly files**: ~5-10 MB each
- **24 hours**: ~120-240 MB/day
- **30 days**: ~3.6-7.2 GB/month
- **1 year**: ~43-86 GB/year

**Retention Strategies**:

1. **Keep all hourly files**: Simple but uses most space
2. **Delete hourly after upload**: Use MinIO as primary storage
3. **Delete hourly after daily aggregation**: Keep daily locally, hourly in MinIO
4. **Lifecycle policies**: Use MinIO's object lifecycle management to auto-delete old files

## Advanced Usage

### Upload Only Specific Hours

```bash
# Upload only morning hours (0-11)
venv/bin/python3 upload_to_minio.py --days-back 1
# Then manually remove unwanted files from bucket
```

### Bulk Historical Upload

Upload many days of historical data:

```bash
# Upload last 30 days
venv/bin/python3 upload_to_minio.py --days-back 30

# Monitor progress
tail -f minio_upload.log
```

### Multiple Buckets

To upload to different buckets:

```bash
# Production bucket
venv/bin/python3 upload_to_minio.py --bucket flight-parquet-prod

# Archive bucket
venv/bin/python3 upload_to_minio.py --bucket flight-parquet-archive
```

## Integration with Daily/Weekly Aggregation

Recommended cron schedule for complete pipeline:

```cron
# Hourly capture - runs at the top of every hour
0 * * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 capture_hourly.py --raw-dir /mnt/usb3/tinkerboard/raw --output-dir /mnt/usb3/tinkerboard/flights/hourly >> parquet_hourly.log 2>&1

# Daily aggregation - runs at 1:00 AM every day
0 1 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_daily.py --hourly-dir /mnt/usb3/tinkerboard/flights/hourly --daily-dir /mnt/usb3/tinkerboard/flights/daily >> parquet_daily.log 2>&1

# MinIO upload - runs at 2:30 AM (after daily aggregation)
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --delete-after-upload >> minio_upload.log 2>&1

# Weekly aggregation - runs at 2:00 AM every Monday
0 2 * * 1 cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_weekly.py --daily-dir /mnt/usb3/tinkerboard/flights/daily --weekly-dir /mnt/usb3/tinkerboard/flights/weekly >> parquet_weekly.log 2>&1
```

## Summary

After completing this setup:

✅ **Hourly Parquet files** automatically uploaded to MinIO daily
✅ **Credentials** stored securely in `.env` file
✅ **Duplicate detection** prevents re-uploading existing files
✅ **Error logging** for troubleshooting
✅ **Optional cleanup** to save local disk space

Your flight data is now safely backed up to object storage! 🎉
