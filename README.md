# Flight Data to DuckDB

Convert dump1090-fa ADS-B aircraft tracking JSON data into a DuckDB database for analysis.

## Overview

This project processes JSON files from a dump1090-fa ADS-B receiver (tracking aircraft via radio signals) and loads them into a DuckDB database for efficient querying and analysis.

## Data Source

Data is synced from a dump1090-fa receiver at `tinkerboard:/run/dump1090-fa/` into the `raw/` directory.

### Automated Sync (Recommended)

A cron job runs every 20 minutes to automatically sync data and update the database:

```bash
# The cron job runs: sync_flight_data.sh
# Check sync logs:
tail -f sync_flight_data.log
```

To manage the cron job:

```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Remove the cron job
crontab -r
```

### Manual Sync

```bash
# Sync data manually
rsync -avh --progress tinkerboard:/run/dump1090-fa/ ./raw/

# Load into database
python3 load_to_duckdb.py
```

## Database Schema

### `aircraft_observations` table
Stores aircraft position, altitude, speed, and other telemetry data with timestamps. Each observation is unique by aircraft (`hex`) and time (`observation_epoch`).

**Primary Key**: `(hex, observation_epoch)` - Prevents duplicate observations

Key fields:
- `hex`: ICAO 24-bit aircraft address (unique identifier)
- `flight`: Flight callsign
- `lat`, `lon`: Position coordinates
- `alt_baro`, `alt_geom`: Barometric and geometric altitude
- `gs`: Ground speed
- `track`: Direction of travel
- `observation_time`: When the observation was recorded
- `observation_epoch`: Unix timestamp for the observation
- `rssi`: Signal strength

### `receiver_stats` table
Receiver performance statistics for different time periods (latest, last1min, last5min, last15min, total).

**Primary Key**: `(end_epoch, period)` - Prevents duplicate stats

### Duplicate Handling

The database uses composite primary keys to prevent duplicates:
- Multiple runs of `load_to_duckdb.py` will not create duplicate records
- Existing observations are skipped using `INSERT OR IGNORE`
- Safe to run the sync script repeatedly without data duplication

## Usage

### Load data into DuckDB

```bash
python3 load_to_duckdb.py
```

This will:
1. Create `aircraft.duckdb` database
2. Load `aircraft.json` (current observations)
3. Load all `history_*.json` files (120 historical snapshots)
4. Load `stats.json` (receiver statistics)

### Visualize flight paths

#### Static Map

Generate an interactive map showing aircraft flight paths:

```bash
python3 visualize_flights.py
```

This creates `flight_map.html` - an interactive map with:
- Flight paths as colored lines
- Green markers for start positions
- Red markers for end positions
- Popups showing flight details (altitude, speed, track)
- Layer controls and fullscreen mode

Options:
```bash
# Show only flights with 10+ observations
python3 visualize_flights.py --min-observations 10

# Custom output file
python3 visualize_flights.py --output my_map.html
```

#### Animated Map

Generate an animated map showing aircraft moving along their paths over time:

```bash
python3 visualize_flights_animated.py
```

This creates `flight_map_animated.html` - an animated map with:
- Aircraft appearing and moving in real-time sequence
- Time slider to scrub through the recording
- Play/Pause controls
- Speed controls to adjust playback speed
- Moving markers showing aircraft positions over time

Options:
```bash
# Faster playback (500x real-time instead of default 100x)
python3 visualize_flights_animated.py --speed 500

# Show only flights with 10+ observations
python3 visualize_flights_animated.py --min-observations 10

# Custom output file
python3 visualize_flights_animated.py --output my_animated_map.html
```

### Query the database

```bash
python3 query_example.py
```

Or use DuckDB CLI:

```bash
duckdb aircraft.duckdb
```

Example queries:

```sql
-- Find all aircraft currently with positions
SELECT hex, flight, lat, lon, alt_baro, gs
FROM aircraft_observations
WHERE lat IS NOT NULL
ORDER BY observation_time DESC;

-- Track a specific aircraft over time
SELECT observation_time, lat, lon, alt_baro, gs
FROM aircraft_observations
WHERE hex = 'a094a3'
ORDER BY observation_time;

-- Aircraft categories seen
SELECT category, COUNT(*) as count
FROM aircraft_observations
GROUP BY category
ORDER BY count DESC;
```

## Files

- `load_to_duckdb.py` - Main script to load JSON data into DuckDB
- `query_example.py` - Example queries demonstrating database usage
- `visualize_flights.py` - Generate static interactive map visualization of flight paths
- `visualize_flights_animated.py` - Generate animated map with time-based playback
- `sync_flight_data.sh` - Automated sync script (run by cron every 20 minutes)
- `sync_flight_data.log` - Log file for automated sync operations
- `raw/` - Directory containing JSON files from dump1090-fa
- `aircraft.duckdb` - DuckDB database file (created by load script)
- `flight_map.html` - Static interactive map (created by visualize_flights.py)
- `flight_map_animated.html` - Animated map with playback controls (created by visualize_flights_animated.py)

## Data Format

The dump1090-fa receiver produces:
- `aircraft.json` - Current aircraft being tracked
- `history_0.json` to `history_119.json` - Historical snapshots (2 hours at 1-minute intervals)
- `receiver.json` - Receiver metadata
- `stats.json` - Receiver performance statistics

## Requirements

```bash
pip install duckdb folium
```

- `duckdb` - For database operations
- `folium` - For map visualization
