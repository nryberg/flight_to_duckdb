# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADS-B aircraft tracking data pipeline that converts dump1090-fa JSON snapshots into a DuckDB database for analysis and visualization. Data is synced from a remote receiver (`tinkerboard:/run/dump1090-fa/`) and processed into a queryable format with interactive map visualizations.

## Prerequisites

### Python Virtual Environment (Tinkerboard)

If deploying to tinkerboard (which may not have system-wide pip), use a virtual environment:

```bash
# Quick setup (recommended)
./setup_venv.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install duckdb folium
```

All commands below assume you're either:
- In the activated venv: `source venv/bin/activate`
- Or using venv python directly: `venv/bin/python3 script.py`

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

### Automated Sync
```bash
# View sync logs
tail -f sync_flight_data.log

# Manage cron job
crontab -l  # View current jobs
crontab -e  # Edit jobs
```

### Parquet Pipeline
```bash
# Setup Python environment (first time only)
./setup_venv.sh

# Manual hourly capture (with backup to littlebox)
venv/bin/python3 capture_hourly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/hourly

# Manual daily aggregation (yesterday by default)
venv/bin/python3 aggregate_daily.py [--date YYYY-MM-DD] [--delete-hourly] [--backup-dir littlebox:...]

# Manual weekly aggregation (last week by default)
venv/bin/python3 aggregate_weekly.py [--end-date YYYY-MM-DD] [--delete-daily] [--backup-dir littlebox:...]

# Setup automated cron jobs for hourly/daily/weekly processing
./setup_parquet_cron.sh

# View parquet pipeline logs
tail -f parquet_hourly.log
tail -f parquet_daily.log
tail -f parquet_weekly.log
```

## Architecture

### Data Flow

**DuckDB Pipeline** (existing):
1. **dump1090-fa receiver** produces JSON snapshots every ~1 minute
2. **rsync** copies data from remote receiver to `raw/` directory
3. **load_to_duckdb.py** processes JSON files into structured database
4. **Visualization scripts** query database and generate interactive maps

**Parquet Pipeline** (new):
1. **Hourly**: `capture_hourly.py` runs every hour, reads all JSON files from `raw/`, creates timestamped Parquet file
2. **Daily**: `aggregate_daily.py` runs at 1 AM, concatenates previous day's hourly files, removes duplicates, creates daily Parquet
3. **Weekly**: `aggregate_weekly.py` runs Monday at 2 AM, concatenates previous week's daily files, creates weekly Parquet
4. Files organized in `parquet/hourly/`, `parquet/daily/`, `parquet/weekly/` directories

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

**Parquet Pipeline**:
- `parquet/hourly/` - Hourly snapshot files (one per hour)
- `parquet/daily/` - Daily aggregated files (one per day, deduplicated)
- `parquet/weekly/` - Weekly aggregated files (one per week ending Sunday)
- `capture_hourly.py` - Hourly capture script
- `aggregate_daily.py` - Daily aggregation script (with deduplication)
- `aggregate_weekly.py` - Weekly aggregation script
- `setup_parquet_cron.sh` - Automated cron setup script
- `parquet_hourly.log` - Hourly capture logs
- `parquet_daily.log` - Daily aggregation logs
- `parquet_weekly.log` - Weekly aggregation logs
