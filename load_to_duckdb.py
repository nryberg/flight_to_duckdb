#!/usr/bin/env python3
"""
Load dump1090-fa JSON data into DuckDB database.
Processes aircraft.json and history_*.json files from the raw directory.
"""

import json
import duckdb
from pathlib import Path
from datetime import datetime


def create_database(db_path: str = "aircraft.duckdb"):
    """Create DuckDB database with schema for aircraft tracking data."""

    con = duckdb.connect(db_path)

    # Create aircraft observations table
    con.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_observations (
            -- Timestamp info
            observation_time TIMESTAMP,
            observation_epoch DOUBLE,

            -- Aircraft identification
            hex VARCHAR,
            flight VARCHAR,
            type VARCHAR,

            -- Position
            lat DOUBLE,
            lon DOUBLE,

            -- Altitude (can be integer or "ground")
            alt_baro VARCHAR,
            alt_geom VARCHAR,
            baro_rate INTEGER,
            geom_rate INTEGER,

            -- Speed and direction
            gs DOUBLE,
            track DOUBLE,

            -- Squawk and emergency
            squawk VARCHAR,
            emergency VARCHAR,
            category VARCHAR,

            -- Navigation
            nav_qnh DOUBLE,
            nav_altitude_mcp INTEGER,
            nav_altitude_fms INTEGER,
            nav_heading DOUBLE,
            nav_modes VARCHAR,

            -- Signal quality
            rssi DOUBLE,
            messages INTEGER,
            seen DOUBLE,
            seen_pos DOUBLE,

            -- Accuracy metrics
            nic INTEGER,
            rc INTEGER,
            nic_baro INTEGER,
            nac_p INTEGER,
            nac_v INTEGER,
            sil INTEGER,
            sil_type VARCHAR,
            gva INTEGER,
            sda INTEGER,

            -- Version info
            version INTEGER,

            -- Source file
            source_file VARCHAR,

            -- Composite primary key to allow multiple observations per aircraft
            PRIMARY KEY (hex, observation_epoch)
        )
    """)

    # Create stats table for receiver statistics
    con.execute("""
        CREATE TABLE IF NOT EXISTS receiver_stats (
            observation_time TIMESTAMP,
            period VARCHAR,
            start_epoch DOUBLE,
            end_epoch DOUBLE,

            -- Local stats
            samples_processed BIGINT,
            samples_dropped BIGINT,
            modes BIGINT,
            bad BIGINT,
            unknown_icao BIGINT,
            accepted_0 BIGINT,
            accepted_1 BIGINT,
            signal DOUBLE,
            noise DOUBLE,
            peak_signal DOUBLE,
            strong_signals INTEGER,
            gain_db DOUBLE,

            -- Messages
            messages BIGINT,

            -- Tracks
            tracks_all BIGINT,
            tracks_single_message BIGINT,
            tracks_unreliable BIGINT,

            source_file VARCHAR,

            -- Composite primary key to prevent duplicate stats
            PRIMARY KEY (end_epoch, period)
        )
    """)

    return con


def load_aircraft_file(con: duckdb.DuckDBPyConnection, file_path: Path):
    """Load a single aircraft JSON file into the database."""

    with open(file_path, 'r') as f:
        data = json.load(f)

    observation_time = datetime.fromtimestamp(data['now'])
    observation_epoch = data['now']

    # Process each aircraft in the file
    for aircraft in data['aircraft']:
        # Convert nav_modes list to string if present
        nav_modes = None
        if 'nav_modes' in aircraft:
            nav_modes = ','.join(aircraft['nav_modes'])

        # Extract accepted array values if present
        accepted_0 = aircraft.get('accepted', [None, None])[0] if 'accepted' in aircraft else None
        accepted_1 = aircraft.get('accepted', [None, None])[1] if 'accepted' in aircraft else None

        # Insert aircraft observation (skip if duplicate)
        con.execute("""
            INSERT OR IGNORE INTO aircraft_observations (
                observation_time, observation_epoch, hex, flight, type,
                lat, lon, alt_baro, alt_geom, baro_rate, geom_rate,
                gs, track, squawk, emergency, category,
                nav_qnh, nav_altitude_mcp, nav_altitude_fms, nav_heading, nav_modes,
                rssi, messages, seen, seen_pos,
                nic, rc, nic_baro, nac_p, nac_v, sil, sil_type, gva, sda,
                version, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            observation_time, observation_epoch,
            aircraft.get('hex'),
            aircraft.get('flight', '').strip() if aircraft.get('flight') else None,
            aircraft.get('type'),
            aircraft.get('lat'),
            aircraft.get('lon'),
            aircraft.get('alt_baro'),
            aircraft.get('alt_geom'),
            aircraft.get('baro_rate'),
            aircraft.get('geom_rate'),
            aircraft.get('gs'),
            aircraft.get('track'),
            aircraft.get('squawk'),
            aircraft.get('emergency'),
            aircraft.get('category'),
            aircraft.get('nav_qnh'),
            aircraft.get('nav_altitude_mcp'),
            aircraft.get('nav_altitude_fms'),
            aircraft.get('nav_heading'),
            nav_modes,
            aircraft.get('rssi'),
            aircraft.get('messages'),
            aircraft.get('seen'),
            aircraft.get('seen_pos'),
            aircraft.get('nic'),
            aircraft.get('rc'),
            aircraft.get('nic_baro'),
            aircraft.get('nac_p'),
            aircraft.get('nac_v'),
            aircraft.get('sil'),
            aircraft.get('sil_type'),
            aircraft.get('gva'),
            aircraft.get('sda'),
            aircraft.get('version'),
            file_path.name
        ])


def load_stats_file(con: duckdb.DuckDBPyConnection, file_path: Path):
    """Load receiver stats JSON file into the database."""

    with open(file_path, 'r') as f:
        data = json.load(f)

    # Process each time period in stats
    for period_name in ['latest', 'last1min', 'last5min', 'last15min', 'total']:
        if period_name not in data:
            continue

        period_data = data[period_name]
        local_data = period_data.get('local', {})

        observation_time = datetime.fromtimestamp(period_data['end'])

        # Extract accepted array values
        accepted = local_data.get('accepted', [None, None])

        con.execute("""
            INSERT OR IGNORE INTO receiver_stats (
                observation_time, period, start_epoch, end_epoch,
                samples_processed, samples_dropped, modes, bad, unknown_icao,
                accepted_0, accepted_1, signal, noise, peak_signal, strong_signals, gain_db,
                messages, tracks_all, tracks_single_message, tracks_unreliable,
                source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            observation_time, period_name,
            period_data.get('start'),
            period_data.get('end'),
            local_data.get('samples_processed'),
            local_data.get('samples_dropped'),
            local_data.get('modes'),
            local_data.get('bad'),
            local_data.get('unknown_icao'),
            accepted[0],
            accepted[1],
            local_data.get('signal'),
            local_data.get('noise'),
            local_data.get('peak_signal'),
            local_data.get('strong_signals'),
            local_data.get('gain_db'),
            period_data.get('messages'),
            period_data.get('tracks', {}).get('all'),
            period_data.get('tracks', {}).get('single_message'),
            period_data.get('tracks', {}).get('unreliable'),
            file_path.name
        ])


def main():
    """Main function to load all JSON files into DuckDB."""

    raw_dir = Path('raw')
    db_path = 'aircraft.duckdb'

    print(f"Creating DuckDB database: {db_path}")
    con = create_database(db_path)

    # Load aircraft.json
    aircraft_file = raw_dir / 'aircraft.json'
    if aircraft_file.exists():
        print(f"Loading {aircraft_file}...")
        load_aircraft_file(con, aircraft_file)

    # Load all history files
    history_files = sorted(raw_dir.glob('history_*.json'))
    print(f"Found {len(history_files)} history files")

    for idx, history_file in enumerate(history_files, 1):
        if idx % 10 == 0:
            print(f"  Processed {idx}/{len(history_files)} history files...")
        load_aircraft_file(con, history_file)

    print(f"Loaded all {len(history_files)} history files")

    # Load stats.json
    stats_file = raw_dir / 'stats.json'
    if stats_file.exists():
        print(f"Loading {stats_file}...")
        load_stats_file(con, stats_file)

    # Print summary statistics
    print("\n=== Database Summary ===")

    result = con.execute("SELECT COUNT(*) as count FROM aircraft_observations").fetchone()
    print(f"Total aircraft observations: {result[0]}")

    result = con.execute("SELECT COUNT(DISTINCT hex) as count FROM aircraft_observations").fetchone()
    print(f"Unique aircraft: {result[0]}")

    result = con.execute("SELECT COUNT(*) as count FROM receiver_stats").fetchone()
    print(f"Receiver stats records: {result[0]}")

    result = con.execute("""
        SELECT MIN(observation_time) as earliest, MAX(observation_time) as latest
        FROM aircraft_observations
    """).fetchone()
    print(f"Time range: {result[0]} to {result[1]}")

    con.close()
    print(f"\n✓ Database created successfully: {db_path}")


if __name__ == '__main__':
    main()
