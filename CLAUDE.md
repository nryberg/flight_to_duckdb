# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADS-B aircraft tracking data pipeline that converts dump1090-fa JSON snapshots into Parquet files for analysis and visualization.

### Architecture (Distributed)

- **Tinkerboard**: Runs dump1090-fa, syncs raw JSON to littlebox every 20 minutes
- **Littlebox**: Processes JSON into Parquet files, stores on USB3 drive

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete system design.

### Setup Guides

- **Littlebox Setup**: [SETUP_LITTLEBOX.md](SETUP_LITTLEBOX.md) - Primary processing server
- **Tinkerboard Setup**: [SCHEDULED.md](SCHEDULED.md) - Data collector (deprecated for processing)
- **Architecture Details**: [ARCHITECTURE.md](ARCHITECTURE.md) - System overview

## Prerequisites

### Python Virtual Environment (Littlebox Only)

**Processing is done on littlebox**, not tinkerboard. Set up a virtual environment on littlebox:

```bash
# On littlebox
cd /mnt/usb3/tinkerboard/flight_to_duckdb
./setup_venv.sh
```

All commands below assume you're on **littlebox** and either:
- In the activated venv: `source venv/bin/activate`
- Or using venv python directly: `venv/bin/python3 script.py`

**Tinkerboard** only needs rsync and SSH - no Python packages required.

## Core Commands

### Data Pipeline
```bash
# Manual sync from receiver
rsync -avh --progress tinkerboard:/run/dump1090-fa/ ./raw/

# Load/update DuckDB database
python3 load_to_duckdb.py

# Run example queries
python3 query_example.py

# Query database directly
duckdb aircraft.duckdb
```

### Visualization
```bash
# Generate static flight path map
python3 visualize_flights.py [--min-observations N] [--output FILE]

# Generate animated flight path map with time controls
python3 visualize_flights_animated.py [--speed N] [--min-observations N] [--output FILE]
```

### Automated Sync (Tinkerboard → Littlebox)
```bash
# On tinkerboard: View sync logs
tail -f ~/sync_raw.log

# On tinkerboard: Manage cron job
crontab -l  # View current jobs
crontab -e  # Edit jobs

# On tinkerboard: Manual sync test
./sync_raw_to_littlebox.sh
```

### Parquet Pipeline (Littlebox)
```bash
# On littlebox: Setup Python environment (first time only)
cd /mnt/usb3/tinkerboard/flight_to_duckdb
./setup_venv.sh

# On littlebox: Manual hourly capture
venv/bin/python3 capture_hourly.py \
    --raw-dir /mnt/usb3/tinkerboard/raw \
    --output-dir /mnt/usb3/tinkerboard/flights/hourly

# On littlebox: Manual daily aggregation (yesterday by default)
venv/bin/python3 aggregate_daily.py \
    --hourly-dir /mnt/usb3/tinkerboard/flights/hourly \
    --daily-dir /mnt/usb3/tinkerboard/flights/daily \
    [--date YYYY-MM-DD] [--delete-hourly]

# On littlebox: Manual weekly aggregation (last week by default)
venv/bin/python3 aggregate_weekly.py \
    --daily-dir /mnt/usb3/tinkerboard/flights/daily \
    --weekly-dir /mnt/usb3/tinkerboard/flights/weekly \
    [--end-date YYYY-MM-DD] [--delete-daily]

# On littlebox: Setup automated cron jobs
./setup_cron_littlebox.sh

# On littlebox: View parquet pipeline logs
tail -f parquet_hourly.log
tail -f parquet_daily.log
tail -f parquet_weekly.log
```

## Architecture

### Data Flow (Distributed Processing)

**New Architecture** (recommended):
1. **Tinkerboard** runs dump1090-fa, produces JSON snapshots in `/run/dump1090-fa/`
2. **Tinkerboard** syncs JSON to littlebox every 20 minutes via `sync_raw_to_littlebox.sh`
3. **Littlebox** receives data in `/mnt/usb3/tinkerboard/raw/`
4. **Littlebox** runs Parquet pipeline:
   - **Hourly**: `capture_hourly.py` (every hour) → `/mnt/usb3/tinkerboard/flights/hourly/`
   - **Daily**: `aggregate_daily.py` (1 AM) → `/mnt/usb3/tinkerboard/flights/daily/`
   - **Weekly**: `aggregate_weekly.py` (Mon 2 AM) → `/mnt/usb3/tinkerboard/flights/weekly/`

**DuckDB Pipeline** (legacy):
1. **rsync** copies data from tinkerboard to local `raw/` directory
2. **load_to_duckdb.py** processes JSON files into `aircraft.duckdb`
3. **Visualization scripts** query database and generate maps

See [ARCHITECTURE.md](ARCHITECTURE.md) for diagrams and details.

### Database Schema

**aircraft_observations table** - Composite primary key: `(hex, observation_epoch)`
- Each row represents one aircraft observation at a specific timestamp
- Primary key prevents duplicate observations when re-running loader
- `hex`: ICAO 24-bit aircraft address (unique identifier per aircraft)
- Temporal: `observation_time`, `observation_epoch`
- Position: `lat`, `lon`, `alt_baro`, `alt_geom`
- Velocity: `gs` (ground speed), `track` (direction)
- Signal: `rssi`, `messages`, `seen`, `seen_pos`
- Navigation: `nav_qnh`, `nav_altitude_mcp`, `nav_heading`, `nav_modes`
- Note: `alt_baro` and `alt_geom` are VARCHAR (can be integer or "ground")

**receiver_stats table** - Composite primary key: `(end_epoch, period)`
- Statistics for different time periods: latest, last1min, last5min, last15min, total
- Local receiver metrics: samples processed/dropped, signal quality, gain
- Track counts: all, single_message, unreliable

### Key Design Patterns

**Idempotent Loading**: Database uses `INSERT OR IGNORE` with composite primary keys, so re-running `load_to_duckdb.py` on the same data will not create duplicates. Safe to run repeatedly.

**JSON Processing**: Each dump1090-fa JSON file contains:
- `now`: Unix timestamp for observation time
- `aircraft[]`: Array of aircraft with various telemetry fields
- Special handling for `nav_modes` (array → comma-delimited string) and `accepted` (array → separate columns)

**Flight Path Visualization**:
- Groups observations by `(hex, flight)` to track individual flights
- Filters by minimum observation count to show only complete paths
- Static version uses Folium polylines with start/end markers
- Animated version uses timestamped markers with playback controls

**Parquet File Naming Conventions**:
- Hourly: `flights_hourly_YYYY-MM-DD_HH00.parquet` (e.g., `flights_hourly_2025-11-23_1400.parquet`)
- Daily: `flights_daily_YYYY-MM-DD.parquet` (e.g., `flights_daily_2025-11-23.parquet`)
- Weekly: `flights_weekly_ending_YYYY-MM-DD.parquet` (e.g., `flights_weekly_ending_2025-11-24.parquet` for week ending Sunday)

**Parquet Deduplication**:
- Daily aggregation uses `DISTINCT ON (hex, observation_epoch)` to remove duplicates
- Weekly aggregation should have no duplicates if daily aggregation worked correctly
- Same composite key as DuckDB ensures consistency across pipelines

## Important Implementation Details

### DuckDB and Pandas Integration
- **Pandas Dependency**: `capture_hourly.py` requires pandas to convert observation lists to DataFrames
- **DuckDB Requirement**: DuckDB's `register()` method requires pandas DataFrame, not plain Python lists
- **Conversion Pattern**:
  ```python
  df = pd.DataFrame(all_observations)  # Convert list of dicts to DataFrame
  con.register('observations_df', df)  # Register DataFrame with DuckDB
  con.execute("CREATE TABLE observations AS SELECT * FROM observations_df")
  ```
- **Why Pandas**: DuckDB uses pandas DataFrames for efficient data interchange and type inference

### Data Type Handling
- Altitude fields (`alt_baro`, `alt_geom`) stored as VARCHAR because they can be integer values OR the string "ground"
- When querying altitudes for visualization, filter out "ground" and convert to int
- `nav_modes` is an array in JSON but stored as comma-delimited VARCHAR

### Flight Path Queries
When querying for flight paths, always:
- Filter `WHERE lat IS NOT NULL AND lon IS NOT NULL` to exclude incomplete observations
- Group by both `hex` AND `flight` (same aircraft can have different flight numbers over time)
- Order by `observation_time` to get chronological path

### Visualization Performance
- Use `min_observations` parameter to filter out incomplete flights (default: 5)
- Static map (`visualize_flights.py`) better for overview of all paths
- Animated map (`visualize_flights_animated.py`) better for temporal analysis but slower to generate

### Parquet File Management
- **Reading Parquet files**: Use DuckDB `read_parquet()` function for efficient querying
- **Deduplication strategy**: Daily aggregation removes duplicates based on `(hex, observation_epoch)` composite key
- **Week boundaries**: Weeks defined as Sunday to Saturday (7 days ending on Sunday)
- **File retention**: Scripts support `--delete-hourly` and `--delete-daily` flags to clean up intermediate files after successful aggregation
- **Cron schedule**: Hourly (top of each hour), Daily (1 AM), Weekly (Monday 2 AM) to avoid conflicts and allow time for aggregation
- **Schema consistency**: Parquet files use same schema as DuckDB `aircraft_observations` table for interoperability

## Data Files

**Raw Data** (from dump1090-fa receiver):
- `raw/aircraft.json` - Current aircraft being tracked
- `raw/history_0.json` through `raw/history_119.json` - 120 historical snapshots (2 hours at 1-minute intervals)
- `raw/stats.json` - Receiver performance statistics

**DuckDB Pipeline**:
- `aircraft.duckdb` - Output database
- `sync_flight_data.sh` - Automated sync script (run by cron every 20 minutes)
- `sync_flight_data.log` - Sync operation logs

**Parquet Pipeline** (on littlebox):
- **Raw data**: `/mnt/usb3/tinkerboard/raw/` - Synced from tinkerboard
- **Parquet files**:
  - `/mnt/usb3/tinkerboard/flights/hourly/` - Hourly snapshots (~10 MB each)
  - `/mnt/usb3/tinkerboard/flights/daily/` - Daily aggregated (~200 MB each, deduplicated)
  - `/mnt/usb3/tinkerboard/flights/weekly/` - Weekly aggregated (~1 GB each)
- **Scripts** (in `/mnt/usb3/tinkerboard/flight_to_duckdb/`):
  - `capture_hourly.py` - Hourly capture script
  - `aggregate_daily.py` - Daily aggregation script (with deduplication)
  - `aggregate_weekly.py` - Weekly aggregation script
  - `setup_venv.sh` - Python virtual environment setup
  - `setup_cron_littlebox.sh` - Automated cron setup
  - `validate_parquet.py` - Data validation tool
  - `query_parquet_example.py` - Query examples
  - `visualize_parquet.py` - Map visualization from Parquet
- **Logs**:
  - `parquet_hourly.log` - Hourly capture logs
  - `parquet_daily.log` - Daily aggregation logs
  - `parquet_weekly.log` - Weekly aggregation logs

**Sync Scripts** (on tinkerboard):
- `sync_raw_to_littlebox.sh` - Syncs raw JSON to littlebox every 20 minutes
  - Uses IP address `100.107.134.23` instead of hostname for reliability
  - Syncs via rsync over SSH (passwordless authentication required)
- `sync_raw.log` - Sync operation logs

## Common Issues and Solutions

### DuckDB Parameter Mismatch Error
**Error**: `Invalid Input Error: Parameter argument/count mismatch`

**Cause**: Attempting to use parameter binding with lists when DuckDB expects DataFrames.

**Solution**: Use pandas DataFrame with `con.register()`:
```python
import pandas as pd
df = pd.DataFrame(all_observations)
con.register('observations_df', df)
con.execute("CREATE TABLE observations AS SELECT * FROM observations_df")
```

### Python Object Not Suitable for Replacement Scans
**Error**: `Python Object "all_observations_view" of type "list" not suitable for replacement scans`

**Cause**: DuckDB's `register()` method requires pandas DataFrame, not plain Python lists.

**Solution**: Install pandas (`pip install pandas`) and convert list to DataFrame before registering.

### ARM Compilation Issues (Tinkerboard)
**Problem**: DuckDB or numpy fail to compile on Armbian/ARM devices due to resource constraints.

**Solution**: Use distributed architecture - process data on littlebox (x86/x64) instead of tinkerboard (ARM). See [ARCHITECTURE.md](ARCHITECTURE.md).

### Cannot Reach "littlebox" Hostname
**Problem**: SSH/rsync can't resolve "littlebox" hostname.

**Solution**: Use IP address `100.107.134.23` in `sync_raw_to_littlebox.sh` instead of hostname.

### Missing python3-venv Package
**Problem**: `python3 -m venv` fails with "ensurepip is not available".

**Solution**: Install version-specific venv package:
```bash
# On Debian/Ubuntu/Armbian
python3 --version  # Check version (e.g., 3.10)
sudo apt install python3.10-venv python3.10-dev
```

The `setup_venv.sh` script handles this automatically.
