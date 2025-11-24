#!/usr/bin/env python3
"""
Create an interactive map visualization of aircraft flight paths from Parquet files.
Generates an HTML map showing flight paths directly from Parquet data.
"""

import duckdb
import folium
from folium import plugins
import random
from pathlib import Path
import argparse
import sys


def generate_color():
    """Generate a random color for flight paths."""
    colors = [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
        '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
        '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
        '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
    ]
    return random.choice(colors)


def create_flight_map_from_parquet(parquet_files, output_file='flight_map_parquet.html',
                                   min_observations=5, title=None):
    """
    Create an interactive map with flight paths from Parquet files.

    Args:
        parquet_files: List of paths to Parquet files
        output_file: Output HTML file path
        min_observations: Minimum number of observations to show a flight path
        title: Optional title for the map
    """
    if not parquet_files:
        print("ERROR: No Parquet files provided", file=sys.stderr)
        return False

    # Convert to list of strings for DuckDB query
    file_list = [str(f) for f in parquet_files]
    file_list_str = ', '.join([f"'{f}'" for f in file_list])

    print(f"Processing {len(file_list)} Parquet file(s)...")
    for f in parquet_files:
        print(f"  - {f.name}")
    print()

    # Create in-memory DuckDB connection
    con = duckdb.connect(':memory:')

    # Get center point for map
    center_result = con.execute(f"""
        SELECT AVG(lat) as center_lat, AVG(lon) as center_lon
        FROM read_parquet([{file_list_str}])
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """).fetchone()

    if not center_result[0] or not center_result[1]:
        print("ERROR: No valid position data found in Parquet files", file=sys.stderr)
        con.close()
        return False

    center_lat, center_lon = center_result[0], center_result[1]

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles='OpenStreetMap'
    )

    # Add additional tile layers
    folium.TileLayer('cartodbpositron', name='Light Mode').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='Dark Mode').add_to(m)

    # Add title if provided
    if title:
        title_html = f'''
            <div style="position: fixed;
                        top: 10px; left: 50px; width: 400px; height: 50px;
                        background-color: white; border:2px solid grey;
                        z-index:9999; font-size:16px; padding: 10px;
                        ">
                <b>{title}</b>
            </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

    # Get all aircraft with multiple observations
    aircraft_query = f"""
        SELECT DISTINCT hex, flight
        FROM read_parquet([{file_list_str}])
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        GROUP BY hex, flight
        HAVING COUNT(*) >= {min_observations}
        ORDER BY hex
    """

    aircraft_list = con.execute(aircraft_query).fetchall()

    print(f"Creating map centered at ({center_lat:.4f}, {center_lon:.4f})")
    print(f"Processing {len(aircraft_list)} aircraft with {min_observations}+ observations...")

    # Track statistics
    total_paths = 0
    total_points = 0

    # Create a feature group for flight paths
    flight_paths_group = folium.FeatureGroup(name='Flight Paths', show=True)

    # Process each aircraft
    for i, (hex_code, flight_name) in enumerate(aircraft_list, 1):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(aircraft_list)} aircraft...")

        # Get flight path for this aircraft
        path_query = f"""
            SELECT
                observation_time,
                lat,
                lon,
                alt_baro,
                gs,
                track,
                rssi
            FROM read_parquet([{file_list_str}])
            WHERE hex = '{hex_code}'
              AND flight = '{flight_name}'
              AND lat IS NOT NULL
              AND lon IS NOT NULL
            ORDER BY observation_time
        """

        path_data = con.execute(path_query).fetchall()

        if len(path_data) < 2:
            continue

        # Extract coordinates for the path
        coordinates = [(row[1], row[2]) for row in path_data]
        total_points += len(coordinates)

        # Generate a color for this flight path
        color = generate_color()

        # Create the polyline for the flight path
        flight_label = flight_name if flight_name else hex_code
        popup_text = f"""
            <b>Flight:</b> {flight_label}<br>
            <b>Hex:</b> {hex_code}<br>
            <b>Observations:</b> {len(path_data)}
        """

        folium.PolyLine(
            coordinates,
            color=color,
            weight=2,
            opacity=0.7,
            popup=folium.Popup(popup_text, max_width=250)
        ).add_to(flight_paths_group)

        # Add start marker (green)
        start_point = path_data[0]
        start_popup = f"""
            <b>START</b><br>
            <b>Flight:</b> {flight_label}<br>
            <b>Hex:</b> {hex_code}<br>
            <b>Time:</b> {start_point[0]}<br>
            <b>Altitude:</b> {start_point[3]}<br>
            <b>Speed:</b> {start_point[4]} kts
        """
        folium.CircleMarker(
            location=(start_point[1], start_point[2]),
            radius=5,
            color='green',
            fill=True,
            fillColor='green',
            fillOpacity=0.8,
            popup=folium.Popup(start_popup, max_width=250)
        ).add_to(flight_paths_group)

        # Add end marker (red)
        end_point = path_data[-1]
        end_popup = f"""
            <b>END</b><br>
            <b>Flight:</b> {flight_label}<br>
            <b>Hex:</b> {hex_code}<br>
            <b>Time:</b> {end_point[0]}<br>
            <b>Altitude:</b> {end_point[3]}<br>
            <b>Speed:</b> {end_point[4]} kts
        """
        folium.CircleMarker(
            location=(end_point[1], end_point[2]),
            radius=5,
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=0.8,
            popup=folium.Popup(end_popup, max_width=250)
        ).add_to(flight_paths_group)

        total_paths += 1

    # Add the flight paths group to the map
    flight_paths_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Save the map
    m.save(output_file)

    con.close()

    print(f"\n✓ Map created successfully!")
    print(f"  Output file: {output_file}")
    print(f"  Flight paths: {total_paths}")
    print(f"  Total points: {total_points}")
    print(f"  Center: ({center_lat:.4f}, {center_lon:.4f})")

    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Create interactive flight path map from Parquet files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize latest daily file
  python3 visualize_parquet.py --level daily

  # Visualize latest weekly file
  python3 visualize_parquet.py --level weekly

  # Visualize specific file
  python3 visualize_parquet.py --file parquet/daily/flights_daily_2025-11-23.parquet

  # Visualize last 7 daily files combined
  python3 visualize_parquet.py --level daily --count 7

  # Visualize with custom settings
  python3 visualize_parquet.py --level daily --min-observations 10 --output custom_map.html
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', type=str,
                      help='Specific Parquet file to visualize')
    group.add_argument('--level', choices=['hourly', 'daily', 'weekly'],
                      help='Visualize recent file(s) at this level')

    parser.add_argument('--count', type=int, default=1,
                       help='Number of recent files to combine (default: 1, only with --level)')
    parser.add_argument('--parquet-dir', default='parquet',
                       help='Base directory containing parquet files (default: parquet)')
    parser.add_argument('--min-observations', type=int, default=5,
                       help='Minimum observations to show a flight path (default: 5)')
    parser.add_argument('--output', type=str, default='flight_map_parquet.html',
                       help='Output HTML file (default: flight_map_parquet.html)')
    parser.add_argument('--title', type=str,
                       help='Optional title for the map')

    args = parser.parse_args()

    try:
        parquet_files = []

        if args.file:
            # Single file mode
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"ERROR: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)
            parquet_files = [file_path]

        else:
            # Directory mode - find recent files
            directory = Path(args.parquet_dir) / args.level

            if not directory.exists():
                print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
                sys.exit(1)

            # Get most recent files
            all_files = sorted(directory.glob('*.parquet'), reverse=True)

            if not all_files:
                print(f"ERROR: No Parquet files found in {directory}", file=sys.stderr)
                sys.exit(1)

            parquet_files = all_files[:args.count]

        # Generate title if not provided
        title = args.title
        if not title:
            if len(parquet_files) == 1:
                title = f"Flight Paths - {parquet_files[0].name}"
            else:
                title = f"Flight Paths - {len(parquet_files)} {args.level} file(s)"

        # Create the map
        success = create_flight_map_from_parquet(
            parquet_files,
            args.output,
            args.min_observations,
            title
        )

        if success:
            print(f"\nOpen the map in your browser:")
            print(f"  file://{Path(args.output).absolute()}")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
