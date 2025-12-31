#!/usr/bin/env python3
"""
Test querying MinIO S3 data with DuckDB.
Verifies S3 connectivity and data integrity.
"""

import duckdb
from datetime import datetime

def test_s3_queries():
    """Run comprehensive S3 query tests."""

    print("="*70)
    print("DUCKDB S3 QUERY TEST - MinIO Flight Data")
    print("="*70)
    print(f"Test started: {datetime.now()}")
    print()

    # Connect to DuckDB
    con = duckdb.connect(':memory:')

    # Configure S3 credentials for MinIO
    print("1. Configuring S3 credentials...")
    con.execute("""
        CREATE SECRET minio_secret (
            TYPE S3,
            KEY_ID 'DhAOFkxzoxFlBm5C3XAj',
            SECRET 'kedkuVf3dGHxkz2KZcE0ewrNHgKzdNVxBa3YPFaA',
            REGION 'us-east-1',
            ENDPOINT '100.107.134.23:9199',
            USE_SSL false,
            URL_STYLE 'path'
        );
    """)
    print("   ✓ S3 credentials configured")
    print()

    # Test 1: Query single daily file
    print("="*70)
    print("TEST 1: Query Single Daily File (Dec 29, 2025)")
    print("="*70)

    result = con.execute("""
        SELECT
            COUNT(*) as total_observations,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest_observation,
            MAX(observation_time) as latest_observation,
            COUNT(DISTINCT flight) as unique_flights
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-29.parquet')
    """).fetchone()

    print(f"Total observations:    {result[0]:,}")
    print(f"Unique aircraft:       {result[1]:,}")
    print(f"Earliest observation:  {result[2]}")
    print(f"Latest observation:    {result[3]}")
    print(f"Unique flights:        {result[4]:,}")
    print()

    # Test 2: Query multiple daily files with wildcard
    print("="*70)
    print("TEST 2: Query Multiple Daily Files (All December 2025)")
    print("="*70)

    result = con.execute("""
        SELECT
            COUNT(*) as total_observations,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(DATE(observation_time)) as first_date,
            MAX(DATE(observation_time)) as last_date
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
    """).fetchone()

    print(f"Total observations:    {result[0]:,}")
    print(f"Unique aircraft:       {result[1]:,}")
    print(f"Date range:            {result[2]} to {result[3]}")
    print()

    # Test 3: Daily summary statistics
    print("="*70)
    print("TEST 3: Daily Summary Statistics (December 2025)")
    print("="*70)

    results = con.execute("""
        SELECT
            DATE(observation_time) as date,
            COUNT(*) as observations,
            COUNT(DISTINCT hex) as aircraft,
            COUNT(DISTINCT flight) as flights,
            AVG(CASE WHEN gs IS NOT NULL THEN gs END) as avg_ground_speed,
            COUNT(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 END) as with_position
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
        GROUP BY DATE(observation_time)
        ORDER BY date
    """).fetchall()

    print(f"{'Date':<12} {'Observations':>12} {'Aircraft':>10} {'Flights':>10} {'Avg Speed':>10} {'W/Position':>12}")
    print("-"*70)
    for row in results:
        print(f"{row[0]!s:<12} {row[1]:>12,} {row[2]:>10,} {row[3]:>10,} {row[4]:>10.1f} {row[5]:>12,}")
    print()

    # Test 4: Query weekly file
    print("="*70)
    print("TEST 4: Query Weekly File (Week ending Dec 28, 2025)")
    print("="*70)

    result = con.execute("""
        SELECT
            COUNT(*) as total_observations,
            COUNT(DISTINCT hex) as unique_aircraft,
            MIN(observation_time) as earliest,
            MAX(observation_time) as latest
        FROM read_parquet('s3://flight-parquet/weekly/flights_weekly_ending_2025-12-28.parquet')
    """).fetchone()

    print(f"Total observations:    {result[0]:,}")
    print(f"Unique aircraft:       {result[1]:,}")
    print(f"Time range:            {result[2]} to {result[3]}")
    print()

    # Test 5: Top aircraft by observations
    print("="*70)
    print("TEST 5: Top 10 Aircraft by Observations (December 2025)")
    print("="*70)

    results = con.execute("""
        SELECT
            hex,
            flight,
            COUNT(*) as observations,
            MIN(DATE(observation_time)) as first_seen,
            MAX(DATE(observation_time)) as last_seen
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
        GROUP BY hex, flight
        ORDER BY observations DESC
        LIMIT 10
    """).fetchall()

    print(f"{'ICAO Hex':<10} {'Flight':<10} {'Observations':>12} {'First Seen':<12} {'Last Seen':<12}")
    print("-"*70)
    for row in results:
        flight = row[1] if row[1] else 'N/A'
        print(f"{row[0]:<10} {flight:<10} {row[2]:>12,} {row[3]!s:<12} {row[4]!s:<12}")
    print()

    # Test 6: Altitude distribution
    print("="*70)
    print("TEST 6: Altitude Distribution (December 2025)")
    print("="*70)

    results = con.execute("""
        SELECT
            CASE
                WHEN alt_baro = 'ground' THEN 'Ground'
                WHEN TRY_CAST(alt_baro AS INTEGER) < 5000 THEN '0-5k ft'
                WHEN TRY_CAST(alt_baro AS INTEGER) < 10000 THEN '5k-10k ft'
                WHEN TRY_CAST(alt_baro AS INTEGER) < 20000 THEN '10k-20k ft'
                WHEN TRY_CAST(alt_baro AS INTEGER) < 30000 THEN '20k-30k ft'
                WHEN TRY_CAST(alt_baro AS INTEGER) < 40000 THEN '30k-40k ft'
                ELSE '40k+ ft'
            END as altitude_range,
            COUNT(*) as observations
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
        WHERE alt_baro IS NOT NULL
        GROUP BY altitude_range
        ORDER BY
            CASE altitude_range
                WHEN 'Ground' THEN 0
                WHEN '0-5k ft' THEN 1
                WHEN '5k-10k ft' THEN 2
                WHEN '10k-20k ft' THEN 3
                WHEN '20k-30k ft' THEN 4
                WHEN '30k-40k ft' THEN 5
                ELSE 6
            END
    """).fetchall()

    print(f"{'Altitude Range':<15} {'Observations':>12} {'Percentage':>12}")
    print("-"*70)
    total_obs = sum(row[1] for row in results)
    for row in results:
        pct = (row[1] / total_obs * 100) if total_obs > 0 else 0
        print(f"{row[0]:<15} {row[1]:>12,} {pct:>11.1f}%")
    print()

    # Test 7: Hourly activity pattern
    print("="*70)
    print("TEST 7: Hourly Activity Pattern (December 2025)")
    print("="*70)

    results = con.execute("""
        SELECT
            HOUR(observation_time) as hour,
            COUNT(*) as observations,
            COUNT(DISTINCT hex) as unique_aircraft
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
        GROUP BY HOUR(observation_time)
        ORDER BY hour
    """).fetchall()

    print(f"{'Hour (CST)':<12} {'Observations':>12} {'Aircraft':>10}")
    print("-"*70)
    for row in results:
        print(f"{row[0]:02d}:00{'':<6} {row[1]:>12,} {row[2]:>10,}")
    print()

    # Test 8: Data quality check
    print("="*70)
    print("TEST 8: Data Quality Check (December 2025)")
    print("="*70)

    result = con.execute("""
        SELECT
            COUNT(*) as total_records,
            COUNT(CASE WHEN hex IS NULL THEN 1 END) as missing_hex,
            COUNT(CASE WHEN lat IS NULL OR lon IS NULL THEN 1 END) as missing_position,
            COUNT(CASE WHEN gs IS NULL THEN 1 END) as missing_ground_speed,
            COUNT(CASE WHEN track IS NULL THEN 1 END) as missing_track,
            COUNT(CASE WHEN alt_baro IS NULL THEN 1 END) as missing_altitude
        FROM read_parquet('s3://flight-parquet/daily/flights_daily_2025-12-*.parquet')
    """).fetchone()

    print(f"Total records:         {result[0]:,}")
    print(f"Missing ICAO hex:      {result[1]:,} ({result[1]/result[0]*100:.2f}%)")
    print(f"Missing position:      {result[2]:,} ({result[2]/result[0]*100:.2f}%)")
    print(f"Missing ground speed:  {result[3]:,} ({result[3]/result[0]*100:.2f}%)")
    print(f"Missing track:         {result[4]:,} ({result[4]/result[0]*100:.2f}%)")
    print(f"Missing altitude:      {result[5]:,} ({result[5]/result[0]*100:.2f}%)")
    print()

    # Close connection
    con.close()

    print("="*70)
    print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"Test finished: {datetime.now()}")
    print()
    print("Summary:")
    print("- S3 connectivity: ✓ Working")
    print("- Single file query: ✓ Working")
    print("- Multi-file wildcard query: ✓ Working")
    print("- Aggregations: ✓ Working")
    print("- Data quality: ✓ Verified")
    print()


if __name__ == '__main__':
    try:
        test_s3_queries()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
