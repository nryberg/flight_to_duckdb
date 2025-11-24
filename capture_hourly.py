#!/usr/bin/env python3
"""
Capture hourly flight data snapshots to Parquet files.
Processes all aircraft observations from raw/ directory and saves to timestamped Parquet file.
"""

import json
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
import shutil
import subprocess


def process_aircraft_file(file_path: Path) -> list:
    """
    Process a single aircraft JSON file and return list of observation records.

    Args:
        file_path: Path to JSON file

    Returns:
        List of dictionaries containing aircraft observations
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    observation_time = datetime.fromtimestamp(data['now'])
    observation_epoch = data['now']

    observations = []

    for aircraft in data['aircraft']:
        # Convert nav_modes list to string if present
        nav_modes = None
        if 'nav_modes' in aircraft:
            nav_modes = ','.join(aircraft['nav_modes'])

        # Create observation record
        record = {
            'observation_time': observation_time,
            'observation_epoch': observation_epoch,
            'hex': aircraft.get('hex'),
            'flight': aircraft.get('flight', '').strip() if aircraft.get('flight') else None,
            'type': aircraft.get('type'),
            'lat': aircraft.get('lat'),
            'lon': aircraft.get('lon'),
            'alt_baro': aircraft.get('alt_baro'),
            'alt_geom': aircraft.get('alt_geom'),
            'baro_rate': aircraft.get('baro_rate'),
            'geom_rate': aircraft.get('geom_rate'),
            'gs': aircraft.get('gs'),
            'track': aircraft.get('track'),
            'squawk': aircraft.get('squawk'),
            'emergency': aircraft.get('emergency'),
            'category': aircraft.get('category'),
            'nav_qnh': aircraft.get('nav_qnh'),
            'nav_altitude_mcp': aircraft.get('nav_altitude_mcp'),
            'nav_altitude_fms': aircraft.get('nav_altitude_fms'),
            'nav_heading': aircraft.get('nav_heading'),
            'nav_modes': nav_modes,
            'rssi': aircraft.get('rssi'),
            'messages': aircraft.get('messages'),
            'seen': aircraft.get('seen'),
            'seen_pos': aircraft.get('seen_pos'),
            'nic': aircraft.get('nic'),
            'rc': aircraft.get('rc'),
            'nic_baro': aircraft.get('nic_baro'),
            'nac_p': aircraft.get('nac_p'),
            'nac_v': aircraft.get('nac_v'),
            'sil': aircraft.get('sil'),
            'sil_type': aircraft.get('sil_type'),
            'gva': aircraft.get('gva'),
            'sda': aircraft.get('sda'),
            'version': aircraft.get('version'),
            'source_file': file_path.name
        }

        observations.append(record)

    return observations


def capture_hourly_snapshot(raw_dir: str = 'raw', output_dir: str = 'parquet/hourly',
                           backup_dir: str = None):
    """
    Capture current flight data and save to hourly Parquet file.

    Args:
        raw_dir: Directory containing raw JSON files
        output_dir: Directory to save hourly Parquet files
        backup_dir: Optional backup directory to copy files to (e.g., /mnt/usb3/tinkerboard/flights/hourly)
    """
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename with current timestamp
    now = datetime.now()
    # Round to current hour
    hour_timestamp = now.replace(minute=0, second=0, microsecond=0)
    filename = f"flights_hourly_{hour_timestamp.strftime('%Y-%m-%d_%H00')}.parquet"
    output_file = output_path / filename

    print(f"Capturing hourly snapshot: {filename}")
    print(f"Timestamp: {hour_timestamp}")

    # Collect all observations
    all_observations = []

    # Process aircraft.json
    aircraft_file = raw_path / 'aircraft.json'
    if aircraft_file.exists():
        print(f"Processing {aircraft_file.name}...")
        all_observations.extend(process_aircraft_file(aircraft_file))

    # Process all history files
    history_files = sorted(raw_path.glob('history_*.json'))
    print(f"Processing {len(history_files)} history files...")

    for history_file in history_files:
        all_observations.extend(process_aircraft_file(history_file))

    print(f"Total observations collected: {len(all_observations)}")

    if not all_observations:
        print("WARNING: No observations found!")
        return

    # Convert list of dicts to pandas DataFrame
    df = pd.DataFrame(all_observations)

    # Use DuckDB to write Parquet file
    con = duckdb.connect(':memory:')

    # Register the DataFrame as a view that DuckDB can query
    con.register('observations_df', df)

    # Create table from the registered DataFrame
    con.execute("CREATE TABLE observations AS SELECT * FROM observations_df")

    # Write to Parquet
    con.execute(f"COPY observations TO '{output_file}' (FORMAT PARQUET)")

    # Get statistics
    stats = con.execute("""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest
        FROM observations
    """).fetchone()

    con.close()

    print(f"\n✓ Hourly snapshot saved: {output_file}")
    print(f"  - Total records: {stats[0]}")
    print(f"  - Unique aircraft: {stats[1]}")
    print(f"  - Time range: {stats[2]} to {stats[3]}")

    # Copy to backup directory if specified
    if backup_dir:
        # Check if backup_dir is a remote path (contains ':')
        if ':' in backup_dir:
            # Remote backup using rsync
            remote_file = f"{backup_dir}/{filename}"
            print(f"\nRsyncing to remote backup: {remote_file}")

            try:
                # Use rsync with compression and progress
                result = subprocess.run(
                    ['rsync', '-avz', '--progress', str(output_file), remote_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"✓ Remote backup completed via rsync")
            except subprocess.CalledProcessError as e:
                print(f"WARNING: Backup failed: {e.stderr}", file=sys.stderr)
            except FileNotFoundError:
                print(f"WARNING: rsync not found. Skipping remote backup.", file=sys.stderr)
        else:
            # Local backup using shutil
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            backup_file = backup_path / filename

            print(f"\nCopying to backup location: {backup_file}")
            shutil.copy2(output_file, backup_file)
            print(f"✓ Backup copy completed")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Capture hourly flight data snapshots to Parquet files'
    )
    parser.add_argument('--backup-dir', type=str,
                       help='Backup directory - local path or remote (e.g., littlebox:/mnt/usb3/tinkerboard/flights/hourly)')
    parser.add_argument('--raw-dir', default='raw',
                       help='Directory containing raw JSON files (default: raw)')
    parser.add_argument('--output-dir', default='parquet/hourly',
                       help='Directory to save hourly Parquet files (default: parquet/hourly)')

    args = parser.parse_args()

    try:
        capture_hourly_snapshot(args.raw_dir, args.output_dir, args.backup_dir)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
