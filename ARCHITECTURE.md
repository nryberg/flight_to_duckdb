# Architecture: Flight Data Pipeline

## Overview

The flight data pipeline collects ADS-B aircraft tracking data and processes it into Parquet files for analysis. The system is distributed across two machines to optimize resource usage.

## System Components

### Tinkerboard (Data Collector)
- **Hardware**: Armbian-based ARM SBC with limited resources
- **Role**: Data collection only
- **Services**:
  - Runs `dump1090-fa` to receive ADS-B signals
  - Generates JSON snapshots in `/run/dump1090-fa/`
  - Syncs raw JSON data to littlebox every 20 minutes

**Why not process here?**
- Limited RAM and CPU resources
- Compiling Python packages (DuckDB, numpy) is extremely slow on ARM
- Better to focus resources on signal reception

### Littlebox (Data Processor)
- **Hardware**: More powerful server with adequate resources
- **Role**: Data processing and storage
- **Services**:
  - Receives raw JSON data from tinkerboard
  - Runs Parquet pipeline (hourly capture, daily/weekly aggregation)
  - Stores processed Parquet files on USB3 drive (`/mnt/usb3/tinkerboard/flights/`)
  - Hosts Python virtual environment with DuckDB, numpy, etc.

**Why process here?**
- More CPU and RAM for compilation and processing
- USB3 storage for long-term data retention
- Can run visualization and analysis tasks

## Data Flow

```
┌─────────────────┐
│  Tinkerboard    │
│                 │
│  dump1090-fa    │ ──► Generates JSON snapshots
│  /run/dump1090  │     (aircraft.json, history_*.json)
│     -fa/        │
└────────┬────────┘
         │
         │ rsync every 20 min
         │ (sync_raw_to_littlebox.sh)
         │
         ▼
┌─────────────────────────────────────┐
│  Littlebox                          │
│                                     │
│  /mnt/usb3/tinkerboard/raw/         │ ◄─ Raw JSON files
│                                     │
│  Parquet Pipeline:                  │
│  ┌─────────────────────────────┐   │
│  │ capture_hourly.py           │   │
│  │ (runs every hour)           │   │
│  │ Reads: raw/*.json           │   │
│  │ Writes: parquet/hourly/     │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌─────────────────────────────┐   │
│  │ aggregate_daily.py          │   │
│  │ (runs daily at 1 AM)        │   │
│  │ Reads: parquet/hourly/      │   │
│  │ Writes: parquet/daily/      │   │
│  │ Deduplicates data           │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌─────────────────────────────┐   │
│  │ aggregate_weekly.py         │   │
│  │ (runs Mon at 2 AM)          │   │
│  │ Reads: parquet/daily/       │   │
│  │ Writes: parquet/weekly/     │   │
│  └─────────────────────────────┘   │
│                                     │
│  /mnt/usb3/tinkerboard/flights/    │ ◄─ Parquet files
│    ├── hourly/                     │
│    ├── daily/                      │
│    └── weekly/                     │
└─────────────────────────────────────┘
```

## Cron Schedules

### Tinkerboard
```bash
# Sync raw data to littlebox every 20 minutes
*/20 * * * * /path/to/sync_raw_to_littlebox.sh >> sync_raw.log 2>&1
```

### Littlebox
```bash
# Hourly capture - process all raw JSON into Parquet
0 * * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 capture_hourly.py >> parquet_hourly.log 2>&1

# Daily aggregation - combine hourly files, remove duplicates
0 1 * * * cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_daily.py >> parquet_daily.log 2>&1

# Weekly aggregation - combine daily files
0 2 * * 1 cd /mnt/usb3/tinkerboard/flight_to_duckdb && venv/bin/python3 aggregate_weekly.py >> parquet_weekly.log 2>&1
```

## File Locations

### Tinkerboard
```
/run/dump1090-fa/          # Live data from dump1090-fa (tmpfs, volatile)
  ├── aircraft.json        # Current aircraft
  └── history_*.json       # Historical snapshots (120 files, 2 hours)
```

### Littlebox
```
/mnt/usb3/tinkerboard/
├── raw/                           # Synced from tinkerboard
│   ├── aircraft.json
│   └── history_*.json
│
├── flight_to_duckdb/             # Processing scripts
│   ├── venv/                     # Python virtual environment
│   ├── capture_hourly.py
│   ├── aggregate_daily.py
│   ├── aggregate_weekly.py
│   ├── parquet/                  # Local working directory
│   │   ├── hourly/
│   │   ├── daily/
│   │   └── weekly/
│   └── *.log                     # Processing logs
│
└── flights/                      # Final storage (USB3 drive)
    ├── hourly/                   # ~10 MB/file, 24/day
    ├── daily/                    # ~200 MB/file, deduplicated
    └── weekly/                   # ~1 GB/file
```

## Network Requirements

### Tinkerboard → Littlebox
- **Protocol**: rsync over SSH
- **Frequency**: Every 20 minutes
- **Data size**: ~2-5 MB per sync (121 JSON files)
- **Bandwidth**: Minimal (<1 Mbps average)
- **Authentication**: SSH keys (passwordless)

## Resource Requirements

### Tinkerboard (Minimal)
- **CPU**: Dedicated to dump1090-fa signal processing
- **RAM**: 512 MB minimum for dump1090-fa
- **Storage**: Minimal (tmpfs for live data)
- **Network**: Stable connection for rsync

### Littlebox (Moderate)
- **CPU**: Multi-core for DuckDB processing
- **RAM**: 2+ GB recommended (for DuckDB compilation and processing)
- **Storage**:
  - ~5 GB for hourly files (7 days retention)
  - ~5 GB for daily files (30 days retention)
  - ~10 GB for weekly files (1 year retention)
  - Total: ~20 GB for 1 year of data
- **Swap**: 2 GB recommended if RAM < 4 GB

## Benefits of This Architecture

✅ **Separation of Concerns**: tinkerboard focuses on signal reception, littlebox on processing
✅ **Resource Optimization**: Heavy processing on capable hardware
✅ **Data Reliability**: Multiple copies (tinkerboard tmpfs → littlebox raw → littlebox parquet)
✅ **Scalability**: Can add more receivers without overloading processing
✅ **Maintainability**: Python environment only on one machine
✅ **Storage**: Centralized storage on littlebox USB drive

## Failure Modes & Recovery

### Tinkerboard Offline
- **Impact**: No new data collection
- **Recovery**: When back online, rsync will catch up with latest data
- **Note**: Older data (>2 hours) will be lost from tmpfs

### Littlebox Offline
- **Impact**: Data continues collecting on tinkerboard tmpfs (2 hours max)
- **Recovery**: When back online, rsync syncs available data
- **Note**: Data older than 2 hours on tinkerboard will be lost

### Network Interruption
- **Impact**: rsync fails, data stays on tinkerboard tmpfs (2 hours max)
- **Recovery**: Automatic retry on next cron run (20 min intervals)

### USB Drive Full
- **Impact**: Parquet pipeline fails
- **Recovery**:
  - Clean up old hourly files (oldest first)
  - Increase retention cleanup frequency
  - Monitor with disk space alerts

## Monitoring

### Tinkerboard
```bash
# Check rsync status
tail -f /path/to/sync_raw.log

# Check dump1090-fa status
systemctl status dump1090-fa
```

### Littlebox
```bash
# Check parquet pipeline logs
tail -f /mnt/usb3/tinkerboard/flight_to_duckdb/parquet_hourly.log
tail -f /mnt/usb3/tinkerboard/flight_to_duckdb/parquet_daily.log
tail -f /mnt/usb3/tinkerboard/flight_to_duckdb/parquet_weekly.log

# Check disk usage
df -h /mnt/usb3/
du -sh /mnt/usb3/tinkerboard/flights/*

# Check recent parquet files
ls -lh /mnt/usb3/tinkerboard/flights/hourly/ | tail -10
```

## Migration from Old Architecture

If you were previously running the parquet pipeline on tinkerboard:

1. **Stop tinkerboard cron jobs**: `crontab -e` on tinkerboard, remove parquet pipeline entries
2. **Copy scripts to littlebox**: Use deployment script for littlebox
3. **Set up littlebox environment**: Run `setup_venv.sh` on littlebox
4. **Configure tinkerboard rsync**: Set up `sync_raw_to_littlebox.sh` cron
5. **Start littlebox processing**: Run `setup_parquet_cron.sh` on littlebox
6. **Monitor transition**: Watch logs on both machines for 24 hours
