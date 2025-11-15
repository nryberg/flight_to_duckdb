#!/usr/bin/env python3
"""
Create an interactive map visualization of aircraft flight paths.
Generates an HTML map showing flight paths from the DuckDB database.
"""

import duckdb
import folium
from folium import plugins
import random


def generate_color():
    """Generate a random color for flight paths."""
    colors = [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
        '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
        '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
        '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
    ]
    return random.choice(colors)


def create_flight_map(db_path='aircraft.duckdb', output_file='flight_map.html', min_observations=5):
    """
    Create an interactive map with flight paths.

    Args:
        db_path: Path to DuckDB database
        output_file: Output HTML file path
        min_observations: Minimum number of observations to show a flight path
    """

    con = duckdb.connect(db_path)

    # Get center point for map
    center_result = con.execute("""
        SELECT AVG(lat) as center_lat, AVG(lon) as center_lon
        FROM aircraft_observations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """).fetchone()

    center_lat, center_lon = center_result[0], center_result[1]

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles='OpenStreetMap'
    )

    # Add additional tile layers
    folium.TileLayer('cartodbpositron').add_to(m)

    # Get all aircraft with multiple observations
    aircraft_query = """
        SELECT DISTINCT hex, flight
        FROM aircraft_observations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        GROUP BY hex, flight
        HAVING COUNT(*) >= ?
        ORDER BY hex
    """

    aircraft_list = con.execute(aircraft_query, [min_observations]).fetchall()

    print(f"Creating map centered at ({center_lat:.4f}, {center_lon:.4f})")
    print(f"Processing {len(aircraft_list)} aircraft with {min_observations}+ observations...")

    # Track statistics
    total_paths = 0
    total_points = 0

    # Create a feature group for flight paths
    flight_paths_group = folium.FeatureGroup(name='Flight Paths')

    # Process each aircraft
    for hex_code, flight_name in aircraft_list:
        # Get flight path for this aircraft
        path_query = """
            SELECT
                observation_time,
                lat,
                lon,
                alt_baro,
                gs,
                track,
                rssi
            FROM aircraft_observations
            WHERE hex = ? AND flight = ? AND lat IS NOT NULL AND lon IS NOT NULL
            ORDER BY observation_time
        """

        path_data = con.execute(path_query, [hex_code, flight_name]).fetchall()

        if len(path_data) < 2:
            continue

        # Extract coordinates for the path
        coordinates = [(row[1], row[2]) for row in path_data]

        # Generate a color for this flight
        color = generate_color()

        # Create flight label
        flight_label = flight_name.strip() if flight_name else hex_code

        # Calculate altitude range for tooltip
        altitudes = [row[3] for row in path_data if row[3] is not None and row[3] != 'ground']
        if altitudes:
            try:
                # Try to convert to int if they're strings
                altitudes = [int(a) if isinstance(a, str) else a for a in altitudes]
                min_alt = min(altitudes)
                max_alt = max(altitudes)
                alt_info = f"{min_alt}-{max_alt} ft"
            except (ValueError, TypeError):
                alt_info = "varies"
        else:
            alt_info = "ground"

        # Create enhanced tooltip
        tooltip_text = f"<b>{flight_label}</b><br>Altitude: {alt_info}<br>Points: {len(coordinates)}"

        # Add the flight path as a polyline
        folium.PolyLine(
            coordinates,
            color=color,
            weight=2,
            opacity=0.8,
            popup=f"<b>{flight_label}</b><br>Aircraft: {hex_code}<br>Points: {len(coordinates)}",
            tooltip=tooltip_text
        ).add_to(flight_paths_group)

        # Add markers for start and end points
        start_point = path_data[0]
        end_point = path_data[-1]

        # Helper to format values safely
        def fmt_val(val, suffix='', fmt=None):
            if val is None:
                return 'N/A'
            if fmt:
                return f"{val:{fmt}}{suffix}"
            return f"{val}{suffix}"

        # Start marker (green)
        folium.CircleMarker(
            location=[start_point[1], start_point[2]],
            radius=4,
            color='green',
            fill=True,
            fillColor='green',
            fillOpacity=0.7,
            popup=f"""
                <b>START: {flight_label}</b><br>
                Time: {start_point[0]}<br>
                Altitude: {fmt_val(start_point[3])}<br>
                Speed: {fmt_val(start_point[4], ' kt', '.1f')}<br>
                Track: {fmt_val(start_point[5], '°')}
            """
        ).add_to(flight_paths_group)

        # End marker (red)
        folium.CircleMarker(
            location=[end_point[1], end_point[2]],
            radius=4,
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=0.7,
            popup=f"""
                <b>END: {flight_label}</b><br>
                Time: {end_point[0]}<br>
                Altitude: {fmt_val(end_point[3])}<br>
                Speed: {fmt_val(end_point[4], ' kt', '.1f')}<br>
                Track: {fmt_val(end_point[5], '°')}
            """
        ).add_to(flight_paths_group)

        total_paths += 1
        total_points += len(coordinates)

    # Add the flight paths group to the map
    flight_paths_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Add title
    title_html = f'''
        <div style="position: fixed;
                    top: 10px; left: 50px; width: 400px; height: 90px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
            <h4 style="margin:0">Flight Tracker Visualization</h4>
            <p style="margin:5px 0"><b>{total_paths}</b> flight paths<br>
            <b>{total_points}</b> position observations<br>
            <span style="color:green">●</span> Start
            <span style="color:red">●</span> End</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save the map
    m.save(output_file)

    con.close()

    print(f"\n✓ Map created successfully!")
    print(f"  - {total_paths} flight paths")
    print(f"  - {total_points} total position points")
    print(f"  - Saved to: {output_file}")
    print(f"\nOpen the map in your browser:")
    print(f"  open {output_file}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Visualize aircraft flight paths')
    parser.add_argument('--db', default='aircraft.duckdb', help='Path to DuckDB database')
    parser.add_argument('--output', default='flight_map.html', help='Output HTML file')
    parser.add_argument('--min-observations', type=int, default=5,
                       help='Minimum observations to show flight path (default: 5)')

    args = parser.parse_args()

    create_flight_map(args.db, args.output, args.min_observations)


if __name__ == '__main__':
    main()
