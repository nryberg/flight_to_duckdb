#!/usr/bin/env python3
"""
Aggregate weekly average temperatures from weather METAR files stored in MinIO.
Reads .txt files (raw METAR) and GeoJSON .json files and outputs a weekly
summary parquet to MinIO at s3://weather-summary/weekly_temps.parquet.
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess
import sys

try:
    import duckdb
except ImportError:
    print("Installing duckdb...")
    subprocess.run([sys.executable, "-m", "pip", "install", "duckdb"], check=True)
    import duckdb

try:
    from minio import Minio
except ImportError:
    print("Installing minio...")
    subprocess.run([sys.executable, "-m", "pip", "install", "minio"], check=True)
    from minio import Minio

try:
    from dotenv import load_dotenv
    import os
    load_dotenv("/mnt/usb3/tinkerboard/flight_to_duckdb/.env")
    ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9199")
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
except Exception:
    ENDPOINT = "localhost:9199"
    ACCESS_KEY = None
    SECRET_KEY = None

BUCKET = "weather"
OUTPUT_BUCKET = "flight-parquet"
OUTPUT_KEY = "weather/weekly_temps.parquet"
OUTPUT_FILE = "/tmp/weekly_temps.parquet"

# Regex for METAR T-group: T + sign(0=pos,1=neg) + 3 digits temp + sign + 3 digits dewp
T_GROUP_RE = re.compile(r'T([01])(\d{3})([01])(\d{3})')
API_MOVED = "API endpoint has moved"


def parse_metar_temp(line: str):
    """Extract temperature in Celsius from a METAR line using T-group."""
    m = T_GROUP_RE.search(line)
    if m:
        sign = -1 if m.group(1) == '1' else 1
        return sign * int(m.group(2)) / 10.0
    return None


def week_ending_sunday(date: datetime) -> str:
    """Return the Sunday ending the week containing date (YYYY-MM-DD)."""
    days_until_sunday = (6 - date.weekday()) % 7
    sunday = date + timedelta(days=days_until_sunday)
    return sunday.strftime('%Y-%m-%d')


def process_txt_file(content: str, obs_date: str) -> list:
    """Parse METAR temps from a .txt file's content."""
    if API_MOVED in content:
        return []
    temps = []
    for line in content.splitlines():
        t = parse_metar_temp(line)
        if t is not None:
            temps.append((obs_date, t))
    return temps


def process_geojson_file(content: str, obs_date: str) -> list:
    """Parse temps from old GeoJSON FeatureCollection format."""
    try:
        data = json.loads(content)
        features = data.get('features', [])
        temps = []
        for f in features:
            props = f.get('properties', {})
            temp = props.get('temp')
            if temp is not None:
                temps.append((obs_date, float(temp)))
        return temps
    except Exception:
        return []


def process_new_json_file(content: str, obs_date: str) -> list:
    """Parse temps from new JSON format (Mar 2026+) with temp_c field."""
    try:
        rows = json.loads(content)
        if not isinstance(rows, list):
            rows = [rows]
        temps = []
        for row in rows:
            temp = row.get('temp_c')
            if temp is not None:
                temps.append((obs_date, float(temp)))
        return temps
    except Exception:
        return []


def main():
    client = Minio(ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)

    print("Listing weather files from MinIO...")
    objects = list(client.list_objects(BUCKET, recursive=True))
    print(f"Found {len(objects)} files")

    # Collect (obs_date, temp_c) pairs
    weekly = defaultdict(list)
    processed = 0
    errors = 0

    for obj in objects:
        name = obj.object_name
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', name)
        if not date_match:
            continue
        obs_date = date_match.group(1)

        # Skip files after the txt API break and before new JSON
        # Good ranges: Aug-Nov 2023 (json), Dec 2023 - Sep 16 2025 (txt), Mar 13 2026+ (json :15)
        if obs_date > '2025-09-16' and obs_date < '2026-03-13':
            continue

        try:
            response = client.get_object(BUCKET, name)
            content = response.read().decode('utf-8', errors='replace')
            response.close()

            obs_dt = datetime.strptime(obs_date, '%Y-%m-%d')
            week = week_ending_sunday(obs_dt)

            if name.endswith('.txt'):
                pairs = process_txt_file(content, obs_date)
            elif ':15' in name and name.endswith('.json') and obs_date >= '2026-03-13':
                pairs = process_new_json_file(content, obs_date)
            elif name.endswith('.json') and obs_date <= '2023-11-30':
                pairs = process_geojson_file(content, obs_date)
            else:
                continue

            for _, temp in pairs:
                weekly[week].append(temp)

            processed += 1
            if processed % 500 == 0:
                print(f"  Processed {processed}/{len(objects)} files...")

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error reading {name}: {e}")

    print(f"\nDone. Processed {processed} files, {errors} errors.")
    print(f"Weekly buckets: {len(weekly)}")

    # Build summary
    rows = []
    for week_ending in sorted(weekly.keys()):
    	temps = weekly[week_ending]
    	avg = round(sum(temps) / len(temps), 2)
    	avg_f = round(avg * 9/5 + 32, 1)
    	rows.append({
            'week_ending': week_ending,
            'avg_temp_c': avg,
            'avg_temp_f': avg_f,
            'obs_count': len(temps)
        })
    	print(f"  {week_ending}: {avg:.1f}°C / {avg_f:.1f}°F ({len(temps)} obs)")

    # Write parquet via DuckDB
    print(f"\nWriting {OUTPUT_FILE}...")
    con = duckdb.connect(':memory:')
    con.execute("CREATE TABLE temps AS SELECT * FROM ?", [rows])
    con.execute(f"COPY temps TO '{OUTPUT_FILE}' (FORMAT PARQUET)")
    con.close()

    # Upload to MinIO
    print(f"Uploading to s3://{OUTPUT_BUCKET}/{OUTPUT_KEY}...")
    client.fput_object(OUTPUT_BUCKET, OUTPUT_KEY, OUTPUT_FILE)
    print("Done! Weekly temperature summary uploaded.")


if __name__ == '__main__':
    main()
