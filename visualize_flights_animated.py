#!/usr/bin/env python3
"""
Create an animated map visualization of aircraft flight paths.
Shows aircraft moving along their paths with time-based animation.
"""

import duckdb
import folium
from folium import plugins
import json
from datetime import datetime
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


def create_animated_map(db_path='aircraft.duckdb', output_file='flight_map_animated.html',
                        min_observations=5, speed_multiplier=100):
    """
    Create an animated map with flight paths that play over time.

    Args:
        db_path: Path to DuckDB database
        output_file: Output HTML file path
        min_observations: Minimum number of observations to show a flight path
        speed_multiplier: How fast to play animation (higher = faster, e.g., 100 = 100x real-time)
    """

    con = duckdb.connect(db_path)

    # Get center point for map
    center_result = con.execute("""
        SELECT AVG(lat) as center_lat, AVG(lon) as center_lon
        FROM aircraft_observations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """).fetchone()

    center_lat, center_lon = center_result[0], center_result[1]

    # Get time range
    time_range = con.execute("""
        SELECT
            MIN(observation_epoch) as min_time,
            MAX(observation_epoch) as max_time
        FROM aircraft_observations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """).fetchone()

    min_time, max_time = time_range[0], time_range[1]

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

    print(f"Creating animated map centered at ({center_lat:.4f}, {center_lon:.4f})")
    print(f"Processing {len(aircraft_list)} aircraft with {min_observations}+ observations...")
    print(f"Time range: {datetime.fromtimestamp(min_time)} to {datetime.fromtimestamp(max_time)}")
    print(f"Animation speed: {speed_multiplier}x real-time")

    # Prepare features for TimestampedGeoJson
    features = []

    # Track statistics
    total_paths = 0
    total_points = 0

    # Process each aircraft
    for hex_code, flight_name in aircraft_list:
        # Get flight path for this aircraft
        path_query = """
            SELECT
                observation_time,
                observation_epoch,
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

        # Create flight label
        flight_label = flight_name.strip() if flight_name else hex_code

        # Generate a color for this flight
        color = generate_color()

        # Create features for each point in the path with timestamps
        for i in range(len(path_data) - 1):
            point1 = path_data[i]
            point2 = path_data[i + 1]

            # Extract data
            time1 = point1[0]  # datetime
            epoch1 = point1[1]  # epoch
            lat1, lon1 = point1[2], point1[3]
            alt1, speed1, track1 = point1[4], point1[5], point1[6]

            lat2, lon2 = point2[2], point2[3]
            alt2, speed2 = point2[4], point2[5]

            # Create a line segment between consecutive points
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[lon1, lat1], [lon2, lat2]]
                },
                'properties': {
                    'time': time1.isoformat(),
                    'times': [time1.isoformat(), point2[0].isoformat()],
                    'style': {
                        'color': color,
                        'weight': 3,
                        'opacity': 0.8
                    },
                    'icon': 'circle',
                    'iconstyle': {
                        'fillColor': color,
                        'fillOpacity': 0.8,
                        'stroke': 'true',
                        'radius': 5
                    },
                    'popup': f"""
                        <b>{flight_label}</b><br>
                        Hex: {hex_code}<br>
                        Time: {time1.strftime('%H:%M:%S')}<br>
                        Alt: {alt1 if alt1 else 'N/A'}<br>
                        Speed: {f'{speed1:.1f}' if speed1 else 'N/A'} kt<br>
                        Track: {track1 if track1 else 'N/A'}°
                    """
                }
            }

            features.append(feature)

        # Also create a moving marker for the aircraft
        for i, point in enumerate(path_data):
            time_point = point[0]
            epoch_point = point[1]
            lat, lon = point[2], point[3]
            alt, speed, track = point[4], point[5], point[6]

            # Create marker feature
            marker_feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                },
                'properties': {
                    'time': time_point.isoformat(),
                    'icon': 'marker',
                    'iconstyle': {
                        'fillColor': color,
                        'fillOpacity': 0.8,
                        'stroke': 'true',
                        'radius': 6,
                        'color': 'white',
                        'weight': 2
                    },
                    'style': {
                        'color': color,
                        'fillColor': color,
                        'fillOpacity': 0.8
                    },
                    'popup': f"""
                        <b>{flight_label}</b><br>
                        Hex: {hex_code}<br>
                        Time: {time_point.strftime('%H:%M:%S')}<br>
                        Alt: {alt if alt else 'N/A'}<br>
                        Speed: {f'{speed:.1f}' if speed else 'N/A'} kt<br>
                        Track: {track if track else 'N/A'}°
                    """
                }
            }
            features.append(marker_feature)

        total_paths += 1
        total_points += len(path_data)

    # Create TimestampedGeoJson
    timestamped_geojson = plugins.TimestampedGeoJson(
        {
            'type': 'FeatureCollection',
            'features': features
        },
        period='PT1S',  # Update period (1 second)
        add_last_point=True,
        auto_play=False,
        loop=False,
        max_speed=speed_multiplier,
        loop_button=True,
        date_options='YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True,
        duration='PT1M'  # How long each feature is displayed
    )

    timestamped_geojson.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Add title
    title_html = f'''
        <div style="position: fixed;
                    top: 10px; left: 50px; width: 450px; height: 110px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
            <h4 style="margin:0">Animated Flight Tracker</h4>
            <p style="margin:5px 0"><b>{total_paths}</b> flight paths<br>
            <b>{total_points}</b> position observations<br>
            <b>{speed_multiplier}x</b> real-time speed<br>
            Use the time slider at the bottom to control playback</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save the map
    m.save(output_file)

    con.close()

    print(f"\n✓ Animated map created successfully!")
    print(f"  - {total_paths} flight paths")
    print(f"  - {total_points} total position points")
    print(f"  - Saved to: {output_file}")
    print(f"\nOpen the map in your browser:")
    print(f"  open {output_file}")
    print(f"\nControls:")
    print(f"  - Play/Pause button to start/stop animation")
    print(f"  - Time slider to scrub through time")
    print(f"  - Speed slider to adjust playback speed")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Create animated flight path visualization')
    parser.add_argument('--db', default='aircraft.duckdb', help='Path to DuckDB database')
    parser.add_argument('--output', default='flight_map_animated.html', help='Output HTML file')
    parser.add_argument('--min-observations', type=int, default=5,
                       help='Minimum observations to show flight path (default: 5)')
    parser.add_argument('--speed', type=int, default=100,
                       help='Animation speed multiplier (default: 100x real-time)')

    args = parser.parse_args()

    create_animated_map(args.db, args.output, args.min_observations, args.speed)


if __name__ == '__main__':
    main()
