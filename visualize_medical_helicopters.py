#!/usr/bin/env python3
"""
Create an interactive map visualization of medical helicopter flight paths.
"""

import duckdb
import folium
from folium import plugins


def create_medical_helicopter_map(db_path='./duckdb/flights.db', output_file='medical_helicopters_map.html'):
    """
    Create an interactive map with medical helicopter flight paths.

    Args:
        db_path: Path to DuckDB database
        output_file: Output HTML file path
    """

    con = duckdb.connect(db_path)

    # Get all medical helicopter flights
    medical_aircraft = con.execute("""
        SELECT DISTINCT
            a.hex,
            a.flight,
            af.registration,
            af.manufacturer,
            af.model,
            af.owner_operator
        FROM aircraft_observations a
        LEFT JOIN airframes af ON a.hex = af.icao
        WHERE (
            LOWER(af.owner_operator) LIKE '%life%link%'
            OR LOWER(af.owner_operator) LIKE '%medical%'
            OR LOWER(af.owner_operator) LIKE '%critical care%'
            OR LOWER(af.owner_operator) LIKE '%air ambulance%'
        )
        AND af.short_type LIKE 'H%'  -- Helicopters only
        AND a.flight IS NOT NULL
        AND LENGTH(a.flight) > 0
        GROUP BY a.hex, a.flight, af.registration, af.manufacturer, af.model, af.owner_operator
    """).fetchall()

    if not medical_aircraft:
        print("No medical helicopters found in database")
        con.close()
        return

    print(f"Found {len(medical_aircraft)} medical helicopter flights")
    print()

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

    # Color scheme for medical helicopters
    colors = ['#FF0000', '#FF4500', '#FF6347', '#DC143C', '#C71585', '#8B0000']
    color_idx = 0

    total_paths = 0
    total_points = 0

    # Create a feature group for each operator
    life_link_group = folium.FeatureGroup(name='Life Link III')
    other_medical_group = folium.FeatureGroup(name='Other Medical')

    # Process each medical helicopter flight
    for hex_code, flight_name, registration, manufacturer, model, owner in medical_aircraft:
        # Get flight path
        path_data = con.execute("""
            SELECT
                observation_time,
                lat,
                lon,
                alt_baro,
                gs,
                track
            FROM aircraft_observations
            WHERE hex = ? AND flight = ? AND lat IS NOT NULL AND lon IS NOT NULL
            ORDER BY observation_time
        """, [hex_code, flight_name]).fetchall()

        if len(path_data) < 2:
            continue

        # Extract coordinates
        coordinates = [(row[1], row[2]) for row in path_data]

        # Assign color
        color = colors[color_idx % len(colors)]
        color_idx += 1

        # Create label
        flight_label = flight_name.strip() if flight_name else registration
        operator = owner if owner else "Unknown"

        # Tooltip
        tooltip_text = f"<b>{flight_label}</b><br>{manufacturer} {model}<br>{operator}<br>Points: {len(coordinates)}"

        # Add the flight path
        folium.PolyLine(
            coordinates,
            color=color,
            weight=3,
            opacity=0.8,
            popup=f"<b>{flight_label}</b><br>Registration: {registration}<br>Aircraft: {manufacturer} {model}<br>Operator: {operator}<br>Points: {len(coordinates)}",
            tooltip=tooltip_text
        ).add_to(life_link_group if 'LIFE LINK' in operator.upper() else other_medical_group)

        # Start marker (green)
        start_point = path_data[0]
        folium.CircleMarker(
            location=[start_point[1], start_point[2]],
            radius=6,
            color='green',
            fill=True,
            fillColor='green',
            fillOpacity=0.8,
            popup=f"""
                <b>START: {flight_label}</b><br>
                Time: {start_point[0]}<br>
                Altitude: {start_point[3] if start_point[3] else 'N/A'}<br>
                Speed: {start_point[4] if start_point[4] else 'N/A'} kt
            """
        ).add_to(life_link_group if 'LIFE LINK' in operator.upper() else other_medical_group)

        # End marker (red)
        end_point = path_data[-1]
        folium.CircleMarker(
            location=[end_point[1], end_point[2]],
            radius=6,
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=0.8,
            popup=f"""
                <b>END: {flight_label}</b><br>
                Time: {end_point[0]}<br>
                Altitude: {end_point[3] if end_point[3] else 'N/A'}<br>
                Speed: {end_point[4] if end_point[4] else 'N/A'} kt
            """
        ).add_to(life_link_group if 'LIFE LINK' in operator.upper() else other_medical_group)

        total_paths += 1
        total_points += len(coordinates)

        print(f"  {flight_label:<10} {manufacturer} {model:<15} {len(coordinates):>4} points")

    # Add feature groups to map
    life_link_group.add_to(m)
    other_medical_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Add title
    title_html = f'''
        <div style="position: fixed;
                    top: 10px; left: 50px; width: 450px; height: 110px;
                    background-color: white; border:2px solid red; z-index:9999;
                    font-size:14px; padding: 10px">
            <h4 style="margin:0; color:red">Medical Helicopter Flight Paths</h4>
            <p style="margin:5px 0"><b>{total_paths}</b> medical helicopter flights<br>
            <b>{total_points}</b> position observations<br>
            <span style="color:green">●</span> Start
            <span style="color:red">●</span> End<br>
            <small>Life Link III Air Ambulance Services</small></p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save the map
    m.save(output_file)

    con.close()

    print()
    print(f"✓ Medical helicopter map created successfully!")
    print(f"  - {total_paths} flight paths")
    print(f"  - {total_points} total position points")
    print(f"  - Saved to: {output_file}")
    print()
    print(f"Open the map in your browser:")
    print(f"  open {output_file}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Visualize medical helicopter flight paths')
    parser.add_argument('--db', default='./duckdb/flights.db', help='Path to DuckDB database')
    parser.add_argument('--output', default='medical_helicopters_map.html', help='Output HTML file')

    args = parser.parse_args()

    try:
        create_medical_helicopter_map(args.db, args.output)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
