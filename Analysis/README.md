# Flight Data Analysis Reports

This directory contains comprehensive analysis reports generated from ADS-B aircraft tracking data collected between November 25 - December 30, 2025.

## Analysis Reports

### [Aircraft by Category](aircraft_by_category.md)
Analysis of aircraft bucketed by size and engine configuration using ICAO type codes.

**Key Findings**:
- **84%** of observations are twin-jet aircraft (commercial airlines and business jets)
- **10%** are single-engine piston aircraft (primarily flight training)
- **2%** are quad-jet cargo aircraft (Boeing 747s)
- UH-60 Black Hawks from Minnesota Army National Guard regularly observed

**Top Categories**:
- Twin-Jet (L2J): 165,276 observations
- Single-Engine Piston (L1P): 19,636 observations
- Quad-Jet (L4J): 2,967 observations

---

### [Aircraft by Age](aircraft_by_age.md)
Distribution of aircraft observations by manufacturing decade.

**Key Findings**:
- **83%** of observations are aircraft manufactured since 2000
- **34%** are from the 2010s decade (largest group)
- **Oldest**: 1948 Cessna 170 (77 years old) still flying
- **Newest**: 2025 Cessna 172S (brand new)

**Fleet Age Trends**:
- Commercial jets: Average 7-14 years old
- Training aircraft (Cessna 172): Average 48-51 years old
- Business jets: Average 2-6 years old

---

### [Top Flights](top_flights.md)
Most frequently observed aircraft with flight callsigns.

**Top Aircraft by Observations**:
1. **N757LE**: Cessna 172M (859 obs) - Lake Elmo Aero flight school
2. **N61879**: Cessna 172M (646 obs) - Flight training
3. **N737YU**: Cessna 172N (594 obs) - Flight training
4. **N124SP**: Cirrus SR22 (525 obs) - Modern general aviation
5. **N371LL**: Pilatus PC-12 (353 obs) - Life Link III air ambulance

**Operator Highlights**:
- SkyWest Airlines: Multiple regional jet flights daily
- Delta Air Lines: Boeing 717 operations
- Atlas Air / UPS: Boeing 747 cargo operations
- Life Link III: Medical evacuation services

---

### [Medical Helicopters](medical_helicopters.md)
Analysis of air ambulance operations in the region.

**Medical Aircraft Fleet**:
- **Life Link III**: 6+ aircraft (5 helicopters + 1 fixed-wing)
- **Sanford Medical**: 2 Beechcraft King Airs
- **Total**: 564 medical aircraft observations

**Primary Operators**:
- **N371LL** (Pilatus PC-12): 353 observations - fixed-wing air ambulance
- **N716LF** (AgustaWestland AW119): 56 observations - helicopter
- **N119SP** (Bell 407): 367 observations - helicopter (operator unknown)

**Operations**: 24/7 emergency medical services, inter-hospital transfers, trauma response

---

## Dataset Summary

| Metric | Value |
|--------|-------|
| **Total Observations** | 199,786 |
| **Unique Aircraft** | 3,501 |
| **Date Range** | Nov 25 - Dec 30, 2025 |
| **Airframes Database** | 615,656 aircraft records |
| **Match Rate** | 99% |
| **Observation Location** | Minneapolis-St. Paul metro area |

## Data Collection

**Receiver Setup**:
- **Hardware**: dump1090-fa ADS-B receiver
- **Architecture**: Distributed processing (Tinkerboard → Littlebox)
- **Storage**: DuckDB database + Parquet files
- **MinIO**: S3-compatible object storage for long-term archival

**Processing Pipeline**:
1. **Raw Data**: JSON snapshots from dump1090-fa
2. **Hourly**: Parquet files with position/velocity filtering
3. **Daily**: Aggregated and deduplicated
4. **DuckDB**: Loaded with airframes database for analysis

## Key Insights

### Geographic Context
Based on flight patterns and frequencies:
- **Location**: Minneapolis-St. Paul metropolitan area
- **Primary Airport**: MSP International Airport (major hub)
- **Training**: Lake Elmo Airport (21D) - active flight school
- **Medical**: Life Link III bases throughout Minnesota

### Traffic Patterns

1. **Commercial Aviation** (84%):
   - Regional airlines dominate (SkyWest, Delta Connection)
   - Business jets frequent (Gulfstream, Bombardier, Pilatus)
   - Cargo operations (Boeing 747s - Atlas Air, UPS)

2. **General Aviation** (10%):
   - Heavy flight training activity (Cessna 172s)
   - Modern aircraft (Cirrus SR22, Van's RV-12IS)
   - 50-year-old trainers still in active service

3. **Military/Emergency** (6%):
   - UH-60 Black Hawks (Minnesota Army National Guard)
   - Multiple medical helicopters and fixed-wing aircraft
   - 24/7 emergency response capability

### Fleet Modernization

- **Regional Jets**: Transitioning from CRJ-700s/717s to newer Embraer E175s and Airbus A220s
- **Training Fleet**: Mix of 1970s Cessna 172s and modern Cirrus SR22s
- **Business Aviation**: Very modern fleet (2-6 years average)
- **Vintage Aircraft**: Small but active community (56 aircraft from 1940s-1960s)

## Analysis Scripts

All analyses can be regenerated using Python scripts:

| Analysis | Script | Output |
|----------|--------|--------|
| Aircraft Categories | `query_aircraft_by_category.py` | Terminal output |
| Aircraft Age | `query_aircraft_by_age.py` | Terminal output |
| Medical Helicopters | `visualize_medical_helicopters.py` | HTML map |
| Flight Paths | `visualize_flights.py` | HTML map |

**Database**:
- **Location**: `./duckdb/flights.db`
- **Tables**: `aircraft_observations`, `airframes`
- **Size**: 34 MB (199,786 observations + 615,656 aircraft records)

## Visualizations

Interactive HTML maps are available:

1. **flight_map.html**: All flight paths (6,909 flights, 163,611 points)
2. **medical_helicopters_map.html**: Medical helicopter routes (6 flights, 93 points)

Features:
- Color-coded flight paths
- Start/end markers (green/red)
- Interactive popups with aircraft details
- Layer controls and fullscreen mode

## Data Quality

- **Position Data**: 100% of observations have valid lat/lon
- **Airframe Match**: 99% of observed aircraft identified in database
- **Age Data**: 94% of aircraft have manufacturing year
- **Deduplication**: Composite key (hex, observation_epoch) prevents duplicates

## Future Analysis Opportunities

Potential areas for deeper analysis:

- **Seasonal Patterns**: Compare data across different months/seasons
- **Weather Impact**: Correlate flight patterns with weather conditions
- **Route Analysis**: Identify common flight paths and airways
- **Noise Analysis**: Track low-altitude overflights in residential areas
- **Economic Indicators**: Business jet activity as economic indicator
- **Training Efficiency**: Flight school activity patterns and duration
- **Emergency Response**: Medical helicopter response times and coverage areas

## How to Use These Reports

1. **Browse Reports**: Click on any markdown file above to view detailed analysis
2. **Regenerate Data**: Run Python scripts to update with latest data
3. **Interactive Maps**: Open HTML files in web browser for flight path visualization
4. **Query Database**: Use DuckDB to run custom queries on the dataset

## Contact & Attribution

- **Data Source**: dump1090-fa ADS-B receiver
- **Airframes Database**: Basic Aircraft Database (615K+ records)
- **Generated**: December 31, 2025
- **Analysis Period**: November 25 - December 30, 2025 (35 days)

---

*All analysis generated from real ADS-B data collected in the Minneapolis-St. Paul metropolitan area.*
