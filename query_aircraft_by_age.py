#!/usr/bin/env python3
"""
Query and display aircraft observations bucketed by airframe age (by decade).
"""

import duckdb
from datetime import datetime


def query_by_age(db_path='./duckdb/flights.db'):
    """Query and display aircraft by manufacturing decade."""

    print("="*90)
    print("AIRCRAFT DISTRIBUTION BY MANUFACTURING DECADE")
    print("="*90)
    print(f"Query time: {datetime.now()}")
    print()

    con = duckdb.connect(db_path)

    # Overall distribution by decade
    print("="*90)
    print("OBSERVATION DISTRIBUTION BY DECADE")
    print("="*90)
    print()

    result = con.execute("""
        WITH aircraft_ages AS (
            SELECT
                a.hex,
                af.manufacture_year,
                TRY_CAST(af.manufacture_year AS INTEGER) as year_int,
                2025 - TRY_CAST(af.manufacture_year AS INTEGER) as age,
                FLOOR((TRY_CAST(af.manufacture_year AS INTEGER) - 1900) / 10) * 10 + 1900 as decade,
                COUNT(*) as observations
            FROM aircraft_observations a
            LEFT JOIN airframes af ON a.hex = af.icao
            WHERE af.manufacture_year IS NOT NULL
                AND TRY_CAST(af.manufacture_year AS INTEGER) IS NOT NULL
                AND TRY_CAST(af.manufacture_year AS INTEGER) >= 1900
                AND TRY_CAST(af.manufacture_year AS INTEGER) <= 2025
            GROUP BY a.hex, af.manufacture_year, year_int
        )
        SELECT
            CAST(decade AS VARCHAR) || 's' as decade_label,
            COUNT(DISTINCT hex) as unique_aircraft,
            SUM(observations) as total_observations,
            ROUND(100.0 * SUM(observations) / SUM(SUM(observations)) OVER (), 2) as percentage,
            MIN(year_int) as earliest_year,
            MAX(year_int) as latest_year,
            ROUND(AVG(age), 1) as avg_age
        FROM aircraft_ages
        GROUP BY decade
        ORDER BY decade
    """).fetchall()

    print(f"{'Decade':<12} {'Aircraft':>10} {'Observations':>15} {'%':>8} {'Year Range':<12} {'Avg Age':>8}")
    print("-"*90)

    total_obs = sum(row[2] for row in result)
    total_aircraft = sum(row[1] for row in result)

    for row in result:
        decade = row[0]
        aircraft = row[1]
        obs = row[2]
        pct = row[3]
        year_range = f"{row[4]}-{row[5]}"
        avg_age = row[6]
        print(f"{decade:<12} {aircraft:>10,} {obs:>15,} {pct:>7.2f}% {year_range:<12} {avg_age:>7.1f}y")

    print("-"*90)
    print(f"{'TOTAL':<12} {total_aircraft:>10,} {total_obs:>15,}")
    print()

    # Examples from select decades
    decades_to_show = [
        (1940, 1950, '1940s - Vintage Aircraft'),
        (1970, 1980, '1970s - Classic Aircraft'),
        (2000, 2010, '2000s - Modern Aircraft'),
        (2020, 2026, '2020s - Latest Aircraft'),
    ]

    for start_year, end_year, title in decades_to_show:
        result = con.execute(f"""
            WITH aircraft_ages AS (
                SELECT
                    a.hex,
                    a.flight,
                    af.registration,
                    af.manufacturer,
                    af.model,
                    af.manufacture_year,
                    TRY_CAST(af.manufacture_year AS INTEGER) as year_int,
                    2025 - TRY_CAST(af.manufacture_year AS INTEGER) as age,
                    COUNT(*) as observations
                FROM aircraft_observations a
                LEFT JOIN airframes af ON a.hex = af.icao
                WHERE af.manufacture_year IS NOT NULL
                    AND TRY_CAST(af.manufacture_year AS INTEGER) >= {start_year}
                    AND TRY_CAST(af.manufacture_year AS INTEGER) < {end_year}
                    AND a.flight IS NOT NULL
                    AND LENGTH(a.flight) > 0
                GROUP BY a.hex, a.flight, af.registration, af.manufacturer, af.model, af.manufacture_year, year_int
            )
            SELECT
                flight,
                registration,
                year_int as year,
                2025 - year_int as age,
                manufacturer,
                model,
                observations
            FROM aircraft_ages
            ORDER BY observations DESC
            LIMIT 10
        """).fetchall()

        if result:
            print("="*90)
            print(f"{title.upper()}")
            print("="*90)
            print()
            print(f"{'Flight':<10} {'Registration':<12} {'Year':>6} {'Age':>5} {'Manufacturer':<20} {'Model':<15} {'Obs':>8}")
            print("-"*90)
            for row in result:
                flight = row[0] if row[0] else 'N/A'
                reg = row[1] if row[1] else 'N/A'
                year = row[2]
                age = row[3]
                mfr = (row[4][:18] + '..') if row[4] and len(row[4]) > 20 else (row[4] or 'N/A')
                model = (row[5][:13] + '..') if row[5] and len(row[5]) > 15 else (row[5] or 'N/A')
                obs = row[6]
                print(f"{flight:<10} {reg:<12} {year:>6} {age:>4}y {mfr:<20} {model:<15} {obs:>8,}")
            print()

    # Age statistics by aircraft type
    print("="*90)
    print("AVERAGE AGE BY AIRCRAFT TYPE (Top Types)")
    print("="*90)
    print()

    result = con.execute("""
        WITH aircraft_ages AS (
            SELECT
                a.hex,
                af.icao_type,
                af.manufacturer,
                af.model,
                TRY_CAST(af.manufacture_year AS INTEGER) as year_int,
                2025 - TRY_CAST(af.manufacture_year AS INTEGER) as age,
                COUNT(*) as observations
            FROM aircraft_observations a
            LEFT JOIN airframes af ON a.hex = af.icao
            WHERE af.manufacture_year IS NOT NULL
                AND af.icao_type IS NOT NULL
                AND TRY_CAST(af.manufacture_year AS INTEGER) IS NOT NULL
                AND TRY_CAST(af.manufacture_year AS INTEGER) >= 1900
                AND TRY_CAST(af.manufacture_year AS INTEGER) <= 2025
            GROUP BY a.hex, af.icao_type, af.manufacturer, af.model, year_int
        )
        SELECT
            icao_type,
            manufacturer,
            model,
            COUNT(DISTINCT hex) as aircraft_count,
            SUM(observations) as total_observations,
            ROUND(AVG(age), 1) as avg_age,
            MIN(age) as youngest,
            MAX(age) as oldest
        FROM aircraft_ages
        GROUP BY icao_type, manufacturer, model
        HAVING SUM(observations) > 100
        ORDER BY total_observations DESC
        LIMIT 15
    """).fetchall()

    print(f"{'Type':<8} {'Manufacturer':<20} {'Model':<15} {'Aircraft':>8} {'Obs':>10} {'Avg Age':>8} {'Range':<12}")
    print("-"*90)
    for row in result:
        icao_type = row[0]
        mfr = (row[1][:18] + '..') if row[1] and len(row[1]) > 20 else (row[1] or 'N/A')
        model = (row[2][:13] + '..') if row[2] and len(row[2]) > 15 else (row[2] or 'N/A')
        count = row[3]
        obs = row[4]
        avg_age = row[5]
        age_range = f"{row[7]}-{row[6]}y"
        print(f"{icao_type:<8} {mfr:<20} {model:<15} {count:>8,} {obs:>10,} {avg_age:>7.1f}y {age_range:<12}")
    print()

    con.close()

    print("="*90)
    print(f"Completed: {datetime.now()}")
    print("="*90)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Query aircraft by manufacturing age')
    parser.add_argument('--db', default='./duckdb/flights.db', help='Path to DuckDB database')

    args = parser.parse_args()

    try:
        query_by_age(args.db)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
