# MinIO S3 Access Guide

This document explains how to access flight parquet data from the MinIO S3 server.

## Connection Details

- **Endpoint**: `http://100.107.134.23:9199` (or `http://localhost:9199` from littlebox)
- **Bucket**: `flight-parquet`
- **Region**: `us-east-1` (default)
- **Access Key**: See `.env` file on littlebox
- **Secret Key**: See `.env` file on littlebox

## File Structure

```
s3://flight-parquet/
├── hourly/
│   ├── flights_hourly_2025-11-24_0600.parquet
│   ├── flights_hourly_2025-11-24_0700.parquet
│   └── ... (hourly snapshots)
├── daily/
│   ├── flights_daily_2025-12-21.parquet
│   ├── flights_daily_2025-12-22.parquet
│   └── ... (daily aggregated files)
└── weekly/
    ├── flights_weekly_ending_2025-11-30.parquet
    ├── flights_weekly_ending_2025-12-07.parquet
    └── ... (weekly aggregated files)
```

## Access Methods

### 1. MinIO Client (mc) - Command Line

**Setup alias (one-time):**
```bash
mc alias set myminio http://100.107.134.23:9199 ACCESS_KEY SECRET_KEY
```

**List files:**
```bash
# List all daily files
mc ls myminio/flight-parquet/daily/

# List all weekly files
mc ls myminio/flight-parquet/weekly/

# List specific date range
mc ls myminio/flight-parquet/daily/ | grep "2025-12"
```

**Download files:**
```bash
# Download single file
mc cp myminio/flight-parquet/daily/flights_daily_2025-12-29.parquet ./

# Download all daily files
mc cp --recursive myminio/flight-parquet/daily/ ./local_daily/

# Download all weekly files
mc cp --recursive myminio/flight-parquet/weekly/ ./local_weekly/

# Download specific date range (using mirror with --newer-than)
mc mirror --newer-than 7d myminio/flight-parquet/daily/ ./local_daily/
```

### 2. Web Console

Access the MinIO web interface:
```
http://100.107.134.23:9000
```

Login with the access key and secret key from `.env` file.
Navigate to the `flight-parquet` bucket to browse and download files.

### 3. Python with boto3 (AWS S3 Compatible)

```python
import boto3
from botocore.client import Config

# Configure S3 client for MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://100.107.134.23:9199',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# List files
response = s3_client.list_objects_v2(
    Bucket='flight-parquet',
    Prefix='daily/'
)
for obj in response.get('Contents', []):
    print(f"{obj['Key']}: {obj['Size']/1024/1024:.2f} MB")

# Download a file
s3_client.download_file(
    'flight-parquet',
    'daily/flights_daily_2025-12-29.parquet',
    'local_file.parquet'
)

# Get file as bytes
response = s3_client.get_object(
    Bucket='flight-parquet',
    Key='daily/flights_daily_2025-12-29.parquet'
)
data = response['Body'].read()
```

### 4. Python with MinIO Library

```python
from minio import Minio
from minio.error import S3Error

# Initialize MinIO client
client = Minio(
    "100.107.134.23:9199",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    secure=False  # Set to True if using HTTPS
)

# List files
objects = client.list_objects('flight-parquet', prefix='daily/', recursive=True)
for obj in objects:
    print(f"{obj.object_name}: {obj.size/1024/1024:.2f} MB")

# Download a file
client.fget_object(
    'flight-parquet',
    'daily/flights_daily_2025-12-29.parquet',
    'local_file.parquet'
)

# Get file as stream
response = client.get_object('flight-parquet', 'daily/flights_daily_2025-12-29.parquet')
try:
    data = response.read()
finally:
    response.close()
    response.release_conn()
```

### 5. DuckDB Direct S3 Query (RECOMMENDED for Analysis)

**Query parquet files directly from S3 without downloading:**

```python
import duckdb

# Create connection
con = duckdb.connect(':memory:')

# Configure S3 access
con.execute(f"""
    CREATE SECRET minio_secret (
        TYPE S3,
        KEY_ID 'YOUR_ACCESS_KEY',
        SECRET 'YOUR_SECRET_KEY',
        REGION 'us-east-1',
        ENDPOINT '100.107.134.23:9199',
        USE_SSL false,
        URL_STYLE 'path'
    );
""")

# Query single daily file
result = con.execute("""
    SELECT
        COUNT(*) as total_observations,
        COUNT(DISTINCT hex) as unique_aircraft,
        MIN(observation_time) as earliest,
        MAX(observation_time) as latest
    FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-29.parquet')
""").fetchall()

print(result)

# Query all daily files for December
result = con.execute("""
    SELECT
        DATE(observation_time) as date,
        COUNT(*) as observations,
        COUNT(DISTINCT hex) as aircraft
    FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
    GROUP BY DATE(observation_time)
    ORDER BY date
""").fetchall()

print(result)

# Query weekly files
result = con.execute("""
    SELECT
        source_file,
        COUNT(*) as observations,
        COUNT(DISTINCT hex) as aircraft
    FROM read_parquet('s3://flight-parquet/weekly/flights_weekly_*.parquet')
    GROUP BY source_file
    ORDER BY source_file
""").fetchall()

print(result)

con.close()
```

### 6. Pandas with S3

```python
import pandas as pd
import s3fs

# Create S3 filesystem
s3 = s3fs.S3FileSystem(
    key='YOUR_ACCESS_KEY',
    secret='YOUR_SECRET_KEY',
    client_kwargs={
        'endpoint_url': 'http://100.107.134.23:9199',
        'region_name': 'us-east-1'
    }
)

# Read parquet file directly from S3
df = pd.read_parquet(
    's3://flight-parquet/daily/flights_daily_2025-12-29.parquet',
    filesystem=s3
)

print(df.head())
print(f"Total records: {len(df)}")
print(f"Unique aircraft: {df['hex'].nunique()}")

# Read multiple files
df = pd.read_parquet(
    's3://flight-parquet/daily/flights_daily_2025-12-2*.parquet',
    filesystem=s3
)
```

## S3 URL Formats

Depending on the tool, use one of these formats:

**Path-style (recommended for MinIO):**
```
http://100.107.134.23:9199/flight-parquet/daily/flights_daily_2025-12-29.parquet
```

**S3 protocol (for DuckDB, Pandas, etc.):**
```
s3://flight-parquet/daily/flights_daily_2025-12-29.parquet
s3://flight-parquet/daily/flights_daily_2025-12-*.parquet  # Wildcard
s3://flight-parquet/weekly/flights_weekly_ending_*.parquet
```

## File Quality Reference

### Good Data (Dec 21+):
- **Daily files**: 666 KiB - 1.3 MiB per day
- **Records**: 15,000 - 35,000 per day
- **Aircraft**: 500 - 900 unique aircraft per day

### Corrupted Data (Dec 10-20):
- **Daily files**: 73 KiB (corrupted - do not use)
- Contains stale/duplicate data from Nov 25

### Weekly Files:
- **Week ending Dec 28**: 5.5 MiB, 148,751 records (excellent)
- **Week ending Dec 21**: 1.1 MiB, 34,578 records (partial good data)
- **Earlier weeks**: ~130 KiB (corrupted)

## Credentials Location

On littlebox:
```bash
cat /mnt/usb3/tinkerboard/flight_to_duckdb/.env
```

## Quick Examples

**Get latest daily file:**
```bash
mc cp myminio/flight-parquet/daily/flights_daily_$(date -d yesterday +%Y-%m-%d).parquet ./
```

**Query today's data with DuckDB:**
```bash
duckdb -c "
SET s3_endpoint='100.107.134.23:9199';
SET s3_access_key_id='YOUR_KEY';
SET s3_secret_access_key='YOUR_SECRET';
SET s3_use_ssl=false;
SELECT COUNT(*), COUNT(DISTINCT hex)
FROM read_parquet('s3://flight-parquet/daily/flights_daily_$(date -d yesterday +%Y-%m-%d).parquet');
"
```

## Troubleshooting

**Connection refused:**
- Verify MinIO is running: `ssh littlebox "systemctl status minio"`
- Check firewall: Port 9199 should be accessible

**Access denied:**
- Verify credentials in `.env` file are correct
- Check bucket permissions in MinIO console

**SSL certificate errors:**
- Use `secure=False` (Python) or `USE_SSL false` (DuckDB)
- MinIO is configured for HTTP, not HTTPS
