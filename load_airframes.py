#!/usr/bin/env python3
"""
Load airframes database from JSON into DuckDB.
This enriches the flight data with aircraft registration, type, manufacturer, and owner info.
"""

import duckdb
from datetime import datetime


def load_airframes(db_path='./duckdb/flights.db', json_path='./airframes/basic-ac-db.json'):
    """
    Load airframes data from JSON into DuckDB.

    Args:
        db_path: Path to DuckDB database
        json_path: Path to airframes JSON file (NDJSON format)
    """

    print("="*70)
    print("LOADING AIRFRAMES DATABASE TO DUCKDB")
    print("="*70)
    print(f"Started: {datetime.now()}")
    print(f"Database: {db_path}")
    print(f"JSON file: {json_path}")
    print()

    # Connect to database
    print("Connecting to database...")
    con = duckdb.connect(db_path)
    print("✓ Connected")
    print()

    # Drop existing table if it exists
    print("Dropping existing airframes table if it exists...")
    con.execute("DROP TABLE IF EXISTS airframes")
    print("✓ Table dropped")
    print()

    # Load JSON data directly into table
    # DuckDB can read NDJSON (newline-delimited JSON) natively
    print(f"Loading airframes from {json_path}...")
    print("This may take a minute...")

    con.execute(f"""
        CREATE TABLE airframes AS
        SELECT
            icao,
            reg AS registration,
            icaotype AS icao_type,
            year AS manufacture_year,
            manufacturer,
            model,
            ownop AS owner_operator,
            faa_pia,
            faa_ladd,
            short_type,
            mil AS military
        FROM read_json_auto('{json_path}', format='newline_delimited')
    """)

    print("✓ Data loaded")
    print()

    # Get statistics
    result = con.execute("""
        SELECT
            COUNT(*) as total_aircraft,
            COUNT(DISTINCT icao) as unique_icao,
            COUNT(CASE WHEN registration IS NOT NULL THEN 1 END) as with_registration,
            COUNT(CASE WHEN manufacturer IS NOT NULL THEN 1 END) as with_manufacturer,
            COUNT(CASE WHEN military = true THEN 1 END) as military_aircraft
        FROM airframes
    """).fetchone()

    print("="*70)
    print("AIRFRAMES DATA LOADED SUCCESSFULLY")
    print("="*70)
    print(f"Total aircraft:        {result[0]:,}")
    print(f"Unique ICAO codes:     {result[1]:,}")
    print(f"With registration:     {result[2]:,}")
    print(f"With manufacturer:     {result[3]:,}")
    print(f"Military aircraft:     {result[4]:,}")
    print()

    # Create index on ICAO for fast lookups
    print("Creating index on ICAO field for fast joins...")
    con.execute("CREATE INDEX IF NOT EXISTS idx_airframes_icao ON airframes(icao)")
    print("✓ Index created")
    print()

    # Show table schema
    print("Table schema:")
    schema = con.execute("DESCRIBE airframes").fetchall()
    for col in schema:
        print(f"  {col[0]:<20} {col[1]}")
    print()

    # Test join with observed aircraft
    print("="*70)
    print("SAMPLE JOIN WITH OBSERVED AIRCRAFT")
    print("="*70)
    print()

    result = con.execute("""
        SELECT
            a.hex,
            a.flight,
            COUNT(*) as observations,
            af.registration,
            af.manufacturer,
            af.model,
            af.icao_type,
            af.owner_operator
        FROM aircraft_observations a
        LEFT JOIN airframes af ON a.hex = af.icao
        WHERE a.flight IS NOT NULL AND a.flight != ''
        GROUP BY a.hex, a.flight, af.registration, af.manufacturer, af.model, af.icao_type, af.owner_operator
        ORDER BY observations DESC
        LIMIT 10
    """).fetchall()

    print(f"{'ICAO':<8} {'Flight':<10} {'Obs':>6} {'Registration':<10} {'Manufacturer':<20} {'Model':<15}")
    print("-"*70)
    for row in result:
        flight = row[1] if row[1] else 'N/A'
        reg = row[3] if row[3] else 'Unknown'
        mfr = row[4] if row[4] else 'Unknown'
        model = row[5] if row[5] else 'Unknown'
        print(f"{row[0]:<8} {flight:<10} {row[2]:>6,} {reg:<10} {mfr:<20} {model:<15}")
    print()

    # Show match rate
    match_result = con.execute("""
        SELECT
            COUNT(DISTINCT a.hex) as total_observed,
            COUNT(DISTINCT CASE WHEN af.icao IS NOT NULL THEN a.hex END) as matched,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN af.icao IS NOT NULL THEN a.hex END) / COUNT(DISTINCT a.hex), 2) as match_pct
        FROM aircraft_observations a
        LEFT JOIN airframes af ON a.hex = af.icao
    """).fetchone()

    print("Match statistics:")
    print(f"  Aircraft observed:     {match_result[0]:,}")
    print(f"  Matched in database:   {match_result[1]:,}")
    print(f"  Match rate:            {match_result[2]}%")
    print()

    con.close()

    print(f"Finished: {datetime.now()}")
    print("="*70)
    print()
    print("You can now join aircraft_observations with airframes on hex = icao:")
    print()
    print("  SELECT a.*, af.registration, af.manufacturer, af.model")
    print("  FROM aircraft_observations a")
    print("  LEFT JOIN airframes af ON a.hex = af.icao")
    print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load airframes database into DuckDB')
    parser.add_argument('--db', default='./duckdb/flights.db', help='Path to DuckDB database')
    parser.add_argument('--json', default='./airframes/basic-ac-db.json', help='Path to airframes JSON file')

    args = parser.parse_args()

    try:
        load_airframes(args.db, args.json)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
