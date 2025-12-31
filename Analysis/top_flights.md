# Top Flights Analysis

**Analysis Date**: December 31, 2025
**Data Period**: November 25 - December 30, 2025
**Total Observations**: 199,786
**Unique Aircraft**: 3,501

## Top Flights by Unique Days Observed
*Aircraft with valid flight callsigns seen on the most different days*

| ICAO Hex | Callsign | Unique Days | Total Observations | Date Range | Aircraft Type |
|----------|----------|-------------|-------------------|------------|---------------|
| a43887 | **N371LL** | 7 | 353 | Dec 22-30 | Pilatus PC-12/47E (Life Link III) |
| a06e4a | **N127GA** | 7 | 274 | Dec 21-30 | Beech 200 |
| a28bc9 | **SKW3984** | 7 | 129 | Dec 21-29 | Embraer ERJ 170-200 LL |
| a28bc9 | **SKW3799** | 7 | 72 | Dec 21-29 | Embraer ERJ 170-200 LL |
| a199f4 | **N202FF** | 6 | 164 | Dec 22-29 | Raytheon B200 |

**Notable**: Aircraft **a28bc9** (N263SY) is a SkyWest Airlines Embraer E175 operating multiple different flight numbers, indicating it's a regional airline aircraft flying regular routes through the area.

## Top Flights by Total Observations
*Most frequently observed aircraft with callsigns*

| ICAO | Callsign | Observations | Days | Avg Alt (ft) | Avg Speed (kts) | Manufacturer | Model | Year |
|------|----------|--------------|------|--------------|-----------------|--------------|-------|------|
| aa3509 | **N757LE** | 859 | 4 | 2,155 | 74 | CESSNA | 172M | 1975 |
| a80fe5 | **N61879** | 646 | 3 | 2,336 | 79 | CESSNA | 172M | 1975 |
| a9e745 | **N737YU** | 594 | 3 | 2,350 | 75 | CESSNA | 172N | 1977 |
| a0642c | **N124SP** | 525 | 5 | 3,067 | 123 | CIRRUS | SR22 | 2023 |
| a9e624 | **N737ME** | 511 | 4 | 1,749 | 75 | CESSNA | 172N | 1977 |
| a5ea3b | **N480ST** | 483 | 5 | 2,383 | 88 | VANS | RV-12IS | 2021 |
| a10f4a | **N1679H** | 480 | 4 | 2,113 | 91 | PIPER | PA-28-181 | N/A |
| a0d18d | **N1519V** | 452 | 3 | 2,731 | 86 | CESSNA | 172M | 1974 |
| acaaf9 | **N915TT** | 426 | 3 | 2,309 | 86 | PIPER | PA-28-181 | N/A |
| a04f40 | **N119SP** | 367 | 5 | 2,266 | 73 | BELL HELICOPTER | 407 | N/A |
| a66442 | **N5103T** | 362 | 3 | 1,737 | 68 | CHAMPION | 7ECA | N/A |
| a43887 | **N371LL** | 353 | 7 | 6,995 | 201 | PILATUS | PC-12/47E | 2010 |

### Flight Category Breakdown

#### Training Aircraft (Cessna 172s)
The most-observed aircraft are 1970s Cessna 172s used for flight training:

| Callsign | Observations | Operator | Age | Pattern |
|----------|--------------|----------|-----|---------|
| **N757LE** | 859 | Lake Elmo Aero LLC | 50 years | Low & slow (2,155 ft, 74 kts) |
| **N61879** | 646 | Unknown | 50 years | Training patterns |
| **N737YU** | 594 | Unknown | 48 years | Training patterns |
| **N737ME** | 511 | Unknown | 48 years | Training patterns |
| **N1519V** | 452 | Unknown | 51 years | Training patterns |

**Pattern**: These aircraft fly repetitive patterns at low altitudes (1,700-2,700 ft) and slow speeds (74-79 kts), consistent with flight training operations.

#### Medical Aircraft
Life Link III operates the most-observed medical aircraft:

| Callsign | Observations | Aircraft Type | Operator | Avg Altitude | Avg Speed |
|----------|--------------|---------------|----------|--------------|-----------|
| **N371LL** | 353 | Pilatus PC-12/47E | Critical Care Services (Life Link III) | 6,995 ft | 201 kts |
| **N119SP** | 367 | Bell 407 Helicopter | Unknown Medical | 2,266 ft | 73 kts |

**Pattern**: N371LL flies higher and much faster than training aircraft, consistent with inter-hospital medical transport missions.

#### Modern General Aviation

| Callsign | Observations | Aircraft Type | Year | Notes |
|----------|--------------|---------------|------|-------|
| **N124SP** | 525 | Cirrus SR22 | 2023 | Brand new high-performance aircraft |
| **N480ST** | 483 | Van's RV-12IS | 2021 | Experimental light sport aircraft |

**Pattern**: These represent the modern general aviation fleet - advanced avionics, better performance than legacy trainers.

## Aircraft Without Callsigns
*Top 10 aircraft observed without transmitting flight callsigns*

| ICAO Hex | Total Obs | Unique Days | First Seen | Last Seen | Aircraft Type |
|----------|-----------|-------------|------------|-----------|---------------|
| a34c2f | 151 | 10 | Dec 21 | Dec 30 | Unknown |
| a37ed3 | 145 | 10 | Dec 21 | Dec 30 | Unknown |
| a305fd | 102 | 10 | Dec 21 | Dec 30 | Unknown |
| a28bc9 | 101 | 10 | Dec 21 | Dec 30 | Embraer ERJ 170 |
| a7e18a | 100 | 10 | Dec 21 | Dec 30 | Unknown |
| a97c85 | 91 | 10 | Dec 21 | Dec 30 | Unknown |
| aba2ef | 84 | 10 | Dec 21 | Dec 30 | Unknown |
| a35254 | 79 | 10 | Dec 21 | Dec 30 | Unknown |
| ab5a01 | 75 | 11 | Nov 25 | Dec 30 | Unknown |
| ab7402 | 56 | 10 | Dec 21 | Dec 30 | Unknown |

**Note**: Aircraft without callsigns are typically:
- General aviation aircraft not required to file flight plans
- Drones or UAVs
- Military aircraft operating in stealth mode
- Aircraft with faulty or disabled ADS-B transponders

## Commercial Airline Activity

### Regional Airlines (SkyWest)
SkyWest Airlines operates multiple regional jets through the area:

| Flight Number | ICAO Hex | Registration | Aircraft | Observations | Operating For |
|---------------|----------|--------------|----------|--------------|---------------|
| SKW3984 | a28bc9 | N263SY | Embraer E175 | 129 | United/Delta/Alaska |
| SKW3799 | a28bc9 | N263SY | Embraer E175 | 72 | United/Delta/Alaska |
| SKW3795 | - | N607CZ | Embraer E175 | 133 | United/Delta/Alaska |
| SKW3638 | - | N311SY | Embraer E175 | 128 | United/Delta/Alaska |
| SKW4236 | - | N710EV | Bombardier CRJ7 | 123 | United/Delta/Alaska |

**Note**: SkyWest operates as a regional carrier for major airlines (United, Delta, Alaska).

### Major Airlines
Delta Air Lines operates Boeing 717s:

| Flight Number | Registration | Aircraft | Observations | Route Pattern |
|---------------|--------------|----------|--------------|---------------|
| DAL2884 | N717JL | Boeing 717-200 | 148 | Regular service |
| DAL1641 | N717JL | Boeing 717-200 | 107 | Regular service |

### Cargo Operations
Multiple cargo carriers operate heavy jets over the area:

| Operator | Callsign Pattern | Aircraft Type | Observations | Notes |
|----------|------------------|---------------|--------------|-------|
| Atlas Air | GTI#### | Boeing 747-400F | 300+ | Multiple daily flights |
| UPS | UPS#### | Boeing 747-8F | 150+ | Package delivery |
| Cathay Pacific Cargo | CPA#### | Boeing 747-8F | 31 | International cargo |

## Business Aviation

### Top Business Jets

| Callsign | Registration | Aircraft Type | Observations | Owner/Operator |
|----------|--------------|---------------|--------------|----------------|
| EJM19 | N1CC | Gulfstream G550 | 279 | Executive Jet Management |
| N963U | N963U | Gulfstream G500 | 166 | Private |
| N412RK | N412RK | Pilatus PC-24 | 128 | Private |
| N524BB | N524BB | Cessna Citation XLS | 113 | Private |

**Pattern**: High-speed, high-altitude flights (typically 35,000-45,000 ft), point-to-point travel.

## Key Insights

1. **Training Dominance**: Cessna 172s from the 1970s generate the most observations, indicating heavy flight training activity near the receiver

2. **Medical Services**: Life Link III operates both fixed-wing (Pilatus PC-12) and rotary-wing aircraft for medical evacuations

3. **Regional Airline Hub**: Significant SkyWest Airlines presence suggests proximity to a regional airport hub (likely Minneapolis-St. Paul)

4. **Cargo Corridor**: Multiple daily Boeing 747 cargo flights indicate the area is under a major cargo route

5. **Modern GA Fleet**: Growing presence of newer aircraft (Cirrus SR22, Van's RV-12IS) alongside legacy trainers

6. **Business Aviation**: Regular business jet activity (Gulfstream, Pilatus PC-24) indicates corporate aviation presence

## Geographic Context

Based on flight patterns and operator locations:
- **Primary Area**: Minneapolis-St. Paul metropolitan area
- **Nearest Major Airport**: Likely near MSP International Airport
- **Training Activity**: Lake Elmo Airport (21D) - home of Lake Elmo Aero flight school
- **Medical Base**: Life Link III operates from multiple bases in Minnesota

## Data Source

- **Database**: ./duckdb/flights.db
- **Total Observations**: 199,786
- **Date Range**: November 25 - December 30, 2025
- **Unique Aircraft**: 3,501
- **Script**: Various custom queries
