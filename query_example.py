#!/usr/bin/env python3
"""
Example queries for the aircraft DuckDB database.
"""

import duckdb

def main():
    con = duckdb.connect('aircraft.duckdb')

    print("=== Aircraft with Positions ===")
    result = con.execute("""
        SELECT
            hex,
            flight,
            lat,
            lon,
            alt_baro,
            gs,
            track,
            observation_time
        FROM aircraft_observations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY observation_time DESC
        LIMIT 10
    """).fetchdf()
    print(result.to_string(index=False))

    print("\n=== Unique Aircraft Count ===")
    result = con.execute("""
        SELECT COUNT(DISTINCT hex) as unique_aircraft
        FROM aircraft_observations
    """).fetchone()
    print(f"Total unique aircraft: {result[0]}")

    print("\n=== Aircraft by Category ===")
    result = con.execute("""
        SELECT
            category,
            COUNT(*) as count
        FROM aircraft_observations
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    """).fetchdf()
    print(result.to_string(index=False))

    print("\n=== Flight Callsigns (cleaned) ===")
    result = con.execute("""
        SELECT DISTINCT
            flight,
            hex
        FROM aircraft_observations
        WHERE flight IS NOT NULL
        ORDER BY flight
        LIMIT 20
    """).fetchdf()
    print(result.to_string(index=False))

    print("\n=== Signal Quality Statistics ===")
    result = con.execute("""
        SELECT
            AVG(rssi) as avg_rssi,
            MIN(rssi) as min_rssi,
            MAX(rssi) as max_rssi,
            AVG(messages) as avg_messages
        FROM aircraft_observations
        WHERE rssi IS NOT NULL
    """).fetchone()
    print(f"Average RSSI: {result[0]:.2f} dB")
    print(f"Min RSSI: {result[1]:.2f} dB")
    print(f"Max RSSI: {result[2]:.2f} dB")
    print(f"Average Messages: {result[3]:.2f}")

    con.close()


if __name__ == '__main__':
    main()
