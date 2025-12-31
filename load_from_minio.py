#!/usr/bin/env python3
"""
Load flight data from MinIO S3 into local DuckDB database.
"""

import duckdb
from datetime import datetime
import os
from dotenv import load_dotenv

def load_from_minio():
    """Load data from MinIO into local DuckDB database."""

    # Load environment variables
    load_dotenv()

    # Get MinIO credentials from environment
    endpoint = os.getenv('MINIO_ENDPOINT')
    access_key = os.getenv('MINIO_ACCESS_KEY')
    secret_key = os.getenv('MINIO_SECRET_KEY')

    if not all([endpoint, access_key, secret_key]):
        raise ValueError("Missing MinIO credentials in .env file")

    print("="*70)
    print("LOADING FLIGHT DATA FROM MINIO TO DUCKDB")
    print("="*70)
    print(f"Started: {datetime.now()}")
    print(f"MinIO endpoint: {endpoint}")
    print()

    # Connect to local database
    db_path = './duckdb/flights.db'
    print(f"Connecting to database: {db_path}")
    con = duckdb.connect(db_path)
    print("✓ Connected")
    print()

    # Configure S3 credentials for MinIO
    print("Configuring MinIO S3 credentials...")
    con.execute(f"""
        CREATE SECRET IF NOT EXISTS minio_secret (
            TYPE S3,
            KEY_ID '{access_key}',
            SECRET '{secret_key}',
            REGION 'us-east-1',
            ENDPOINT '{endpoint}',
            USE_SSL false,
            URL_STYLE 'path'
        );
    """)
    print("✓ S3 credentials configured")
    print()

    # Drop existing table and create fresh from daily files
    print("Dropping existing table if it exists...")
    con.execute("DROP TABLE IF EXISTS aircraft_observations")
    print("✓ Table dropped")
    print()

    print("Loading data from MinIO daily files...")
    print("This may take a few minutes...")

    con.execute("""
        CREATE TABLE aircraft_observations AS
        SELECT * FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
    """)

    # Get statistics
    result = con.execute("""
        SELECT
            COUNT(*) as total_observations,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest
        FROM aircraft_observations
    """).fetchone()

    print()
    print("="*70)
    print("DATA LOADED SUCCESSFULLY")
    print("="*70)
    print(f"Total observations:    {result[0]:,}")
    print(f"Unique aircraft:       {result[1]:,}")
    print(f"Earliest observation:  {result[2]}")
    print(f"Latest observation:    {result[3]}")
    print()

    # Show table schema
    print("Table schema:")
    schema = con.execute("DESCRIBE aircraft_observations").fetchall()
    for col in schema:
        print(f"  {col[0]:<25} {col[1]}")
    print()

    con.close()
    print(f"Finished: {datetime.now()}")
    print("="*70)

if __name__ == '__main__':
    try:
        load_from_minio()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
