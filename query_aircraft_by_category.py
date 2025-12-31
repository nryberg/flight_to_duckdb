#!/usr/bin/env python3
"""
Query aircraft observations bucketed by size (platform type) and number/type of engines.
Uses the airframes database short_type field to categorize aircraft.
"""

import duckdb
from datetime import datetime


def query_by_category(db_path='./duckdb/flights.db'):
    """Query and display aircraft bucketed by size and engine configuration."""

    print("="*80)
    print("AIRCRAFT CATEGORIZED BY SIZE AND ENGINE CONFIGURATION")
    print("="*80)
    print(f"Query time: {datetime.now()}")
    print()

    con = duckdb.connect(db_path)

    # Overall category summary
    print("="*80)
    print("SUMMARY BY PLATFORM, ENGINE COUNT, AND ENGINE TYPE")
    print("="*80)
    print()

    result = con.execute("""
        WITH aircraft_categories AS (
            SELECT
                a.hex,
                af.short_type,
                SUBSTRING(af.short_type, 1, 1) as platform_type,
                SUBSTRING(af.short_type, 2, 1) as engine_count,
                SUBSTRING(af.short_type, 3, 1) as engine_type,
                COUNT(*) as observations
            FROM aircraft_observations a
            LEFT JOIN airframes af ON a.hex = af.icao
            WHERE af.short_type IS NOT NULL
            GROUP BY a.hex, af.short_type
        )
        SELECT
            CASE platform_type
                WHEN 'L' THEN 'Land Airplane'
                WHEN 'H' THEN 'Helicopter'
                WHEN 'A' THEN 'Amphibian'
                WHEN 'G' THEN 'Gyrocopter'
                ELSE platform_type
            END as platform,
            CASE engine_count
                WHEN '0' THEN '0 (glider)'
                WHEN '1' THEN '1'
                WHEN '2' THEN '2'
                WHEN '3' THEN '3'
                WHEN '4' THEN '4'
                WHEN '8' THEN '8'
                ELSE engine_count
            END as engines,
            CASE engine_type
                WHEN 'P' THEN 'Piston'
                WHEN 'J' THEN 'Jet'
                WHEN 'T' THEN 'Turboprop'
                WHEN 'E' THEN 'Electric'
                WHEN '-' THEN 'None'
                ELSE engine_type
            END as power,
            COUNT(DISTINCT hex) as aircraft,
            SUM(observations) as observations
        FROM aircraft_categories
        GROUP BY platform, engines, power, platform_type, engine_count, engine_type
        ORDER BY observations DESC
    """).fetchall()

    print(f"{'Platform':<15} {'Engines':<10} {'Power':<12} {'Aircraft':>10} {'Observations':>15}")
    print("-"*80)
    for row in result:
        print(f"{row[0]:<15} {row[1]:<10} {row[2]:<12} {row[3]:>10,} {row[4]:>15,}")
    print()

    # Top aircraft in each major category
    categories = [
        ('L', '1', 'P', 'Single-Engine Piston'),
        ('L', '2', 'J', 'Twin-Jet'),
        ('L', '4', 'J', 'Quad-Jet'),
        ('L', '2', 'T', 'Twin Turboprop'),
        ('L', '1', 'T', 'Single-Engine Turboprop'),
        ('H', '2', 'T', 'Twin-Engine Helicopter'),
        ('H', '1', 'T', 'Single-Engine Helicopter'),
    ]

    for platform_code, engines, power_code, desc in categories:

        result = con.execute(f"""
            WITH aircraft_categories AS (
                SELECT
                    a.hex,
                    a.flight,
                    af.registration,
                    af.manufacturer,
                    af.model,
                    af.icao_type,
                    af.short_type,
                    COUNT(*) as observations
                FROM aircraft_observations a
                LEFT JOIN airframes af ON a.hex = af.icao
                WHERE af.short_type = '{platform_code}{engines}{power_code}'
                    AND a.flight IS NOT NULL
                    AND LENGTH(a.flight) > 0
                GROUP BY a.hex, a.flight, af.registration, af.manufacturer, af.model, af.icao_type, af.short_type
            )
            SELECT
                flight,
                registration,
                manufacturer,
                model,
                icao_type,
                observations
            FROM aircraft_categories
            ORDER BY observations DESC
            LIMIT 10
        """).fetchall()

        if result:
            print("="*80)
            print(f"{desc.upper()} (Category: {platform_code}{engines}{power_code})")
            print("="*80)
            print()
            print(f"{'Flight':<10} {'Registration':<12} {'Manufacturer':<20} {'Model':<15} {'Type':<8} {'Obs':>8}")
            print("-"*80)
            for row in result:
                flight = row[0] if row[0] else 'N/A'
                reg = row[1] if row[1] else 'N/A'
                mfr = (row[2][:18] + '..') if row[2] and len(row[2]) > 20 else (row[2] or 'N/A')
                model = (row[3][:13] + '..') if row[3] and len(row[3]) > 15 else (row[3] or 'N/A')
                icao = row[4] if row[4] else 'N/A'
                print(f"{flight:<10} {reg:<12} {mfr:<20} {model:<15} {icao:<8} {row[5]:>8,}")
            print()

    # Size distribution summary
    print("="*80)
    print("AIRCRAFT SIZE DISTRIBUTION")
    print("="*80)
    print()

    result = con.execute("""
        WITH aircraft_categories AS (
            SELECT
                a.hex,
                af.short_type,
                SUBSTRING(af.short_type, 2, 1) as engine_count,
                COUNT(*) as observations
            FROM aircraft_observations a
            LEFT JOIN airframes af ON a.hex = af.icao
            WHERE af.short_type IS NOT NULL
                AND SUBSTRING(af.short_type, 1, 1) = 'L'
            GROUP BY a.hex, af.short_type
        )
        SELECT
            CASE engine_count
                WHEN '1' THEN 'Small (1 engine)'
                WHEN '2' THEN 'Medium (2 engines)'
                WHEN '3' THEN 'Large (3 engines)'
                WHEN '4' THEN 'Large (4 engines)'
                ELSE 'Other'
            END as size_category,
            COUNT(DISTINCT hex) as aircraft,
            SUM(observations) as observations,
            ROUND(100.0 * SUM(observations) / SUM(SUM(observations)) OVER (), 2) as pct
        FROM aircraft_categories
        GROUP BY size_category, engine_count
        ORDER BY observations DESC
    """).fetchall()

    print(f"{'Size Category':<25} {'Aircraft':>10} {'Observations':>15} {'Percentage':>12}")
    print("-"*80)
    for row in result:
        print(f"{row[0]:<25} {row[1]:>10,} {row[2]:>15,} {row[3]:>11.2f}%")
    print()

    con.close()

    print("="*80)
    print(f"Completed: {datetime.now()}")
    print("="*80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Query aircraft by size and engine configuration')
    parser.add_argument('--db', default='./duckdb/flights.db', help='Path to DuckDB database')

    args = parser.parse_args()

    try:
        query_by_category(args.db)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
