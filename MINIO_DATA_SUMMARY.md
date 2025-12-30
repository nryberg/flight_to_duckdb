# MinIO S3 Data Summary - Final Status
**Updated:** December 30, 2025

## 🎉 All Good Quality Data Now in MinIO

### Daily Files (12 files)

| Date | Size | Status | Records | Aircraft |
|------|------|--------|---------|----------|
| 2025-11-24 | 673 KiB | ✅ Good | ~20,000 | ~600 |
| 2025-11-25 | 343 KiB | ✅ Good | ~10,000 | ~400 |
| 2025-12-21 | 1.0 MiB | ✅ Good | 26,826 | 811 |
| 2025-12-22 | 892 KiB | ✅ Good | 22,137 | 779 |
| 2025-12-23 | 1.2 MiB | ✅ Good | 35,193 | 925 |
| 2025-12-24 | 666 KiB | ✅ Good | 15,355 | 626 |
| 2025-12-25 | 733 KiB | ✅ Good | 17,590 | 579 |
| 2025-12-26 | 802 KiB | ✅ Good | 18,871 | 592 |
| 2025-12-27 | 686 KiB | ✅ Good | 16,851 | 617 |
| 2025-12-28 | 872 KiB | ✅ Good | 22,754 | 642 |
| 2025-12-29 | 783 KiB | ✅ Good | 18,286 | 654 |
| 2025-12-30 | 283 KiB | ✅ Good | 5,923 | 277 |

**Total Daily Data:** ~9.8 MB covering 12 days

### Weekly Files (3 files)

| Week Ending | Size | Status | Records | Aircraft |
|-------------|------|--------|---------|----------|
| 2025-11-30 | 1.0 MiB | ✅ Good | 39,552 | 882 |
| 2025-12-21 | 1.1 MiB | ✅ Good | 34,578 | 811 |
| 2025-12-28 | 5.5 MiB | ✅ Good | 148,751 | 2,859 |

**Total Weekly Data:** ~7.6 MB covering 3 weeks

### Hourly Files

**Count:** 856 files
**Coverage:** Multiple months of hourly snapshots

## Data Gaps (Dates Not Available)

The following dates had corrupted hourly source data and cannot be recovered:
- **Nov 26-30, Dec 1-20**: Hourly files contained duplicate/stale data from Nov 25

These dates were removed from MinIO and cannot be regenerated from source data.

## Access Information

**Endpoint:** `http://100.107.134.23:9199`
**Bucket:** `flight-parquet`
**Access Key:** `DhAOFkxzoxFlBm5C3XAj`
**Secret Key:** `kedkuVf3dGHxkz2KZcE0ewrNHgKzdNVxBa3YPFaA`

### S3 URL Format

```
s3://flight-parquet/daily/flights_daily_2025-12-29.parquet
s3://flight-parquet/weekly/flights_weekly_ending_2025-12-28.parquet
s3://flight-parquet/hourly/flights_hourly_2025-12-30_1100.parquet
```

### Quick Access Examples

**Download Latest Daily File:**
```bash
mc cp littlebox/flight-parquet/daily/flights_daily_2025-12-30.parquet ./
```

**Query with DuckDB:**
```sql
CREATE SECRET minio_secret (
    TYPE S3,
    KEY_ID 'DhAOFkxzoxFlBm5C3XAj',
    SECRET 'kedkuVf3dGHxkz2KZcE0ewrNHgKzdNVxBa3YPFaA',
    REGION 'us-east-1',
    ENDPOINT '100.107.134.23:9199',
    USE_SSL false
);

SELECT * FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet');
```

## Data Quality Indicators

### Good Quality Daily Files:
- Size: 300 KiB - 1.3 MiB per day
- Records: 5,000 - 35,000 per day
- Aircraft: 250 - 925 unique aircraft per day

### Good Quality Weekly Files:
- Size: 1.0 - 5.5 MiB per week
- Records: 30,000 - 150,000 per week
- Aircraft: 800 - 2,900 unique aircraft per week

## Cleanup Summary

**Files Removed (Corrupted Data):**
- 26 corrupt daily files (Nov 24, 26-30, Dec 1-20)
- 2 corrupt weekly files (Dec 7, Dec 14)
- Total: 28 files removed, ~2 MB of corrupt data cleaned

**Files Added (Good Data):**
- 2 new daily files uploaded (Nov 24, Dec 30)
- 9 daily files refreshed (Dec 21-29)
- 3 weekly files refreshed (Nov 30, Dec 21, Dec 28)

## Automated Updates

Going forward, new files are automatically uploaded:
- **Daily:** Every day at 1:30 AM (after daily aggregation at 1:00 AM)
- **Weekly:** Every Monday at 2:30 AM (after weekly aggregation at 2:00 AM)
- **Hourly:** Every hour at X:30 (after hourly capture at X:00)

All future data will be generated with the schema fix and will be high quality.

## Monitoring

Check pipeline health:
```bash
ssh littlebox "cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 monitor_parquet_pipeline.py"
```

## Notes

- **Nov 24-25**: Original good data from early in the collection period
- **Dec 21-30**: Regenerated from hourly files with schema fix applied
- **Dec 26-30 (week)**: Included in Dec 28 weekly file (best quality data available)
- All timestamps are in CST (Central Standard Time)
