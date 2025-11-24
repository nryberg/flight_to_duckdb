# MinIO Object Storage Integration

This document describes the MinIO upload integration for backing up hourly Parquet files to object storage.

## Overview

The `upload_to_minio.py` script provides automated upload of hourly Parquet files to MinIO object storage for:
- **Off-site backup**: Redundant storage separate from littlebox
- **Long-term retention**: Centralized archive of all flight data
- **Cloud access**: Access data from anywhere
- **Analytics integration**: Connect BI tools and notebooks directly to MinIO

**Default Schedule**: Daily at 2:30 AM (after daily aggregation completes)

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Littlebox                                      │
│                                                 │
│  Hourly Parquet Files                          │
│  /mnt/usb3/tinkerboard/flights/hourly/         │
│  └── flights_hourly_YYYY-MM-DD_HH00.parquet    │
│                                                 │
│  upload_to_minio.py (runs daily at 2:30 AM)    │
│  └── Reads credentials from .env               │
│      Uploads to MinIO via S3 API               │
│                                                 │
└──────────────────┬──────────────────────────────┘
                   │
                   │ S3 API over HTTP
                   │ (minio Python SDK)
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  MinIO Server (100.107.134.23:9000)            │
│                                                 │
│  Bucket: flight_parquet                        │
│  └── hourly/                                   │
│      ├── flights_hourly_2025-11-23_0000.parquet│
│      ├── flights_hourly_2025-11-23_0100.parquet│
│      └── ...                                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Configuration

### MinIO Server Details

- **Endpoint**: `100.107.134.23:9000`
- **Protocol**: HTTP (not HTTPS)
- **API**: S3-compatible
- **Bucket**: `flight_parquet`
- **Object Prefix**: `hourly/` (all files stored under this prefix)

### Credentials (.env file)

Credentials are stored in `/mnt/usb3/tinkerboard/flight_to_duckdb/.env`:

```bash
# MinIO Configuration
MINIO_ENDPOINT=100.107.134.23:9000
MINIO_ACCESS_KEY=LahuutUtG4KRHtdfCZL3PVALdhhaL7QD
MINIO_SECRET_KEY=XnLiKHhvMnX4rMPQAyQvcqN23hiqqci2
```

**Security Notes**:
- ✅ `.env` is in `.gitignore` (never committed to git)
- ✅ File permissions should be `600` (only owner can read/write)
- ⚠️ Contains secrets - keep secure

### Python Dependencies

Required packages (installed via `setup_venv.sh`):
- `minio` - MinIO Python SDK (S3-compatible client)
- `python-dotenv` - Load environment variables from .env file

## Usage

### Manual Upload

```bash
# On littlebox
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# Upload yesterday's files (default)
venv/bin/python3 upload_to_minio.py

# Upload last 7 days
venv/bin/python3 upload_to_minio.py --days-back 7

# Delete local files after successful upload
venv/bin/python3 upload_to_minio.py --delete-after-upload

# Custom bucket or directory
venv/bin/python3 upload_to_minio.py \
    --bucket my-bucket \
    --hourly-dir /path/to/hourly/files
```

### Automated Daily Upload

Add to crontab on littlebox:

```cron
# Upload hourly Parquet files to MinIO - runs daily at 2:30 AM
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py >> minio_upload.log 2>&1
```

**Recommended Pipeline Schedule**:
```
1:00 AM - Daily aggregation (aggregate_daily.py)
2:00 AM - Weekly aggregation (aggregate_weekly.py, Mondays only)
2:30 AM - MinIO upload (upload_to_minio.py)
```

## Script Behavior

### Upload Process

1. **Connect to MinIO**: Authenticate using credentials from `.env`
2. **Check/Create Bucket**: Ensure `flight_parquet` bucket exists
3. **Find Files**: Locate hourly Parquet files in date range
4. **Filter by Date**: Default uploads yesterday's files (configurable)
5. **Skip Existing**: Check if file already exists in MinIO (idempotent)
6. **Upload**: Transfer files using multipart upload if needed
7. **Optional Cleanup**: Delete local files if `--delete-after-upload` flag used
8. **Summary**: Report uploaded/skipped/failed counts

### Idempotent Uploads

The script is **idempotent** - running it multiple times is safe:
- Already-uploaded files are detected via `stat_object()` check
- Only missing files are uploaded
- No duplicates are created
- Safe to re-run after failures

### Object Naming

Files are stored with the prefix `hourly/`:
```
flight_parquet/
└── hourly/
    ├── flights_hourly_2025-11-23_0000.parquet
    ├── flights_hourly_2025-11-23_0100.parquet
    ├── flights_hourly_2025-11-23_0200.parquet
    └── ...
```

This allows for future expansion:
- `daily/` - Daily aggregated files
- `weekly/` - Weekly aggregated files
- `backups/` - Manual backups

## Monitoring

### Check Upload Logs

```bash
# On littlebox
cd /mnt/usb3/tinkerboard/flight_to_duckdb

# View recent uploads
tail -50 minio_upload.log

# Follow log in real-time
tail -f minio_upload.log

# Search for errors
grep -i error minio_upload.log

# Count successful uploads
grep "✓" minio_upload.log | wc -l
```

### Verify Files in MinIO

**Using MinIO Web Console**:
1. Open `http://100.107.134.23:9000` in browser
2. Log in with access key and secret key
3. Navigate to `flight_parquet` bucket
4. Browse `hourly/` prefix
5. Check file counts, sizes, and upload timestamps

**Using mc (MinIO Client)**:
```bash
# Configure mc
mc alias set myminio http://100.107.134.23:9000 \
    LahuutUtG4KRHtdfCZL3PVALdhhaL7QD \
    XnLiKHhvMnX4rMPQAyQvcqN23hiqqci2

# List files
mc ls myminio/flight_parquet/hourly/

# List files from specific date
mc ls myminio/flight_parquet/hourly/ | grep 2025-11-23

# Get bucket statistics
mc du myminio/flight_parquet

# Count files
mc ls myminio/flight_parquet/hourly/ | wc -l

# Download a file for verification
mc cp myminio/flight_parquet/hourly/flights_hourly_2025-11-23_1400.parquet /tmp/
```

### Expected Output

**Successful upload**:
```
==================================================
MinIO Hourly Parquet Upload
==================================================
MinIO endpoint: 100.107.134.23:9000
Bucket: flight_parquet
Hourly directory: /mnt/usb3/tinkerboard/flights/hourly
Days back: 1
Delete after upload: False
==================================================

Connecting to MinIO at 100.107.134.23:9000 (secure=False)...
✓ Bucket 'flight_parquet' exists

Looking for files from 2025-11-23 to 2025-11-23...
Found 24 files to upload
↑ Uploading flights_hourly_2025-11-23_0000.parquet (8.32 MB)... ✓
↑ Uploading flights_hourly_2025-11-23_0100.parquet (7.89 MB)... ✓
...
⊘ flights_hourly_2025-11-23_2300.parquet - already exists, skipping

==================================================
Upload Summary:
  Uploaded: 23 files
  Skipped:  1 files (already exist)
  Failed:   0 files
==================================================
```

## Storage Estimates

### File Sizes

Typical hourly Parquet file sizes:
- **Minimum**: ~5 MB (low traffic hours)
- **Average**: ~8 MB per file
- **Maximum**: ~15 MB (high traffic hours)

### Storage Requirements

| Period | Files | Size (avg 8 MB/file) |
|--------|-------|---------------------|
| 1 Day | 24 | ~190 MB |
| 1 Week | 168 | ~1.3 GB |
| 1 Month | 720 | ~5.6 GB |
| 1 Year | 8,760 | ~68 GB |

**Note**: Using `--delete-after-upload` eliminates local hourly storage after upload (saves ~190 MB/day locally).

## Disk Space Management

### Strategy 1: Keep Local Copies (Default)

```cron
# Upload but keep local copies
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py >> minio_upload.log 2>&1
```

**Pros**:
- Local files available for quick access
- Redundant storage (local + MinIO)

**Cons**:
- Uses ~190 MB/day local disk space
- Requires periodic cleanup

### Strategy 2: Delete After Upload

```cron
# Upload and delete local files
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py --delete-after-upload >> minio_upload.log 2>&1
```

**Pros**:
- Minimal local disk usage
- MinIO becomes primary storage for hourly files

**Cons**:
- Must download from MinIO to query hourly data
- Slightly slower access to historical hourly data

### Strategy 3: Hybrid (Recommended)

```cron
# Upload daily, delete hourly files older than 7 days
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py >> minio_upload.log 2>&1
0 3 * * * find /mnt/usb3/tinkerboard/flights/hourly/ -name "*.parquet" -mtime +7 -delete
```

**Pros**:
- Keep recent data (7 days) locally for quick access
- Archive older data in MinIO
- Balanced disk usage (~1.3 GB local)

## Troubleshooting

### Connection Refused

**Symptoms**: `Cannot connect to MinIO at 100.107.134.23:9000`

**Checks**:
```bash
# Test network connectivity
ping 100.107.134.23

# Test MinIO port
telnet 100.107.134.23 9000
# Or
curl http://100.107.134.23:9000

# Check from littlebox
ssh littlebox "curl http://100.107.134.23:9000"
```

**Solutions**:
- Verify MinIO server is running
- Check firewall rules on MinIO server
- Ensure littlebox can reach MinIO server

### Authentication Failed

**Symptoms**: `Access Denied` or `Invalid credentials`

**Checks**:
```bash
# Verify .env file exists
cat /mnt/usb3/tinkerboard/flight_to_duckdb/.env

# Test credentials with mc
mc alias set test http://100.107.134.23:9000 \
    LahuutUtG4KRHtdfCZL3PVALdhhaL7QD \
    XnLiKHhvMnX4rMPQAyQvcqN23hiqqci2
mc ls test/
```

**Solutions**:
- Verify credentials in MinIO admin console
- Check for typos in `.env` file
- Ensure access key has appropriate permissions

### Bucket Not Found

**Symptoms**: `Bucket 'flight_parquet' does not exist`

**Solutions**:
```bash
# Create bucket manually with mc
mc mb myminio/flight_parquet

# Or create via web console
# Navigate to http://100.107.134.23:9000
# Buckets → Create Bucket → "flight_parquet"
```

**Note**: The script will attempt to create the bucket automatically if it has `s3:CreateBucket` permission.

### No Files to Upload

**Symptoms**: `No files found in date range`

**Checks**:
```bash
# Verify hourly files exist
ls -lh /mnt/usb3/tinkerboard/flights/hourly/*.parquet | tail -10

# Check file naming
ls /mnt/usb3/tinkerboard/flights/hourly/ | head -5

# Verify date calculation
python3 -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(days=1)).date())"
```

**Solutions**:
- Ensure hourly capture cron is running
- Check `parquet_hourly.log` for errors
- Verify date range with `--days-back` parameter

### Upload Fails Partway

**Symptoms**: Some files upload, then script errors

**Recovery**:
Simply re-run the script - it will skip already-uploaded files:
```bash
venv/bin/python3 upload_to_minio.py
```

**Common Causes**:
- Network interruption
- MinIO server restart
- Disk space issues on MinIO server

### Permission Denied on .env

**Symptoms**: `ERROR: Environment file not found: .env`

**Solution**:
```bash
# Ensure .env exists
ls -l /mnt/usb3/tinkerboard/flight_to_duckdb/.env

# Set proper permissions
chmod 600 /mnt/usb3/tinkerboard/flight_to_duckdb/.env
```

## Integration with Data Pipeline

### Complete Cron Schedule

```cron
# ============================================
# Flight Data Pipeline (Littlebox)
# ============================================

# Hourly capture - runs at the top of every hour
0 * * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 capture_hourly.py --raw-dir /mnt/usb3/tinkerboard/raw --output-dir /mnt/usb3/tinkerboard/flights/hourly >> parquet_hourly.log 2>&1

# Daily aggregation - runs at 1:00 AM
0 1 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_daily.py --hourly-dir /mnt/usb3/tinkerboard/flights/hourly --daily-dir /mnt/usb3/tinkerboard/flights/daily >> parquet_daily.log 2>&1

# Weekly aggregation - runs Monday at 2:00 AM
0 2 * * 1 cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_weekly.py --daily-dir /mnt/usb3/tinkerboard/flights/daily --weekly-dir /mnt/usb3/tinkerboard/flights/weekly >> parquet_weekly.log 2>&1

# MinIO upload - runs daily at 2:30 AM
30 2 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 upload_to_minio.py >> minio_upload.log 2>&1

# Optional: Cleanup old hourly files (runs at 3:00 AM)
# Uncomment to delete hourly files older than 7 days after MinIO upload
# 0 3 * * * find /mnt/usb3/tinkerboard/flights/hourly/ -name "*.parquet" -mtime +7 -delete
```

### Data Flow Timeline

```
00:00 - Hourly capture runs (captures previous hour's data)
...
01:00 - Daily aggregation begins (aggregates all of yesterday's hourly files)
01:15 - Daily aggregation completes
02:00 - Weekly aggregation (Mondays only)
02:30 - MinIO upload begins (uploads yesterday's hourly files)
02:45 - MinIO upload completes
03:00 - Optional: Cleanup old local hourly files
```

## Accessing Data from MinIO

### Download Files

```bash
# Using mc
mc cp myminio/flight_parquet/hourly/flights_hourly_2025-11-23_1400.parquet ./

# Using Python (boto3/minio SDK)
from minio import Minio
client = Minio('100.107.134.23:9000',
               access_key='LahuutUtG4KRHtdfCZL3PVALdhhaL7QD',
               secret_key='XnLiKHhvMnX4rMPQAyQvcqN23hiqqci2',
               secure=False)
client.fget_object('flight_parquet',
                   'hourly/flights_hourly_2025-11-23_1400.parquet',
                   '/tmp/data.parquet')
```

### Query Directly from MinIO

DuckDB can query Parquet files directly from S3-compatible storage:

```python
import duckdb

# Set S3 credentials
con = duckdb.connect(':memory:')
con.execute("""
    SET s3_endpoint='100.107.134.23:9000';
    SET s3_use_ssl=false;
    SET s3_access_key_id='LahuutUtG4KRHtdfCZL3PVALdhhaL7QD';
    SET s3_secret_access_key='XnLiKHhvMnX4rMPQAyQvcqN23hiqqci2';
""")

# Query Parquet files in MinIO
result = con.execute("""
    SELECT COUNT(*) as total_observations,
           COUNT(DISTINCT hex) as unique_aircraft
    FROM read_parquet('s3://flight_parquet/hourly/flights_hourly_2025-11-23_*.parquet')
""").fetchall()

print(result)
```

## Summary

The MinIO integration provides:

✅ **Automated Backup**: Daily upload of hourly Parquet files
✅ **Redundant Storage**: Off-site backup separate from littlebox
✅ **Cloud Access**: Query data directly from S3-compatible storage
✅ **Idempotent**: Safe to re-run, skips existing files
✅ **Secure**: Credentials stored in `.env` file (not in git)
✅ **Monitored**: Comprehensive logging for troubleshooting
✅ **Flexible**: Configurable retention and cleanup strategies

Your flight data is now safely backed up to object storage! 🎉
