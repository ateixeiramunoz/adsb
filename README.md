# ADS-B Data Collection Toolchain

A portable Python toolchain for collecting, storing, and serving ADS-B aircraft position data from dump1090. Designed to run identically on macOS, Linux, and Raspberry Pi.

## Overview

This project provides:

1. **CSV Logger** (Step 1 - MVP): Collects aircraft positions from dump1090 and logs to CSV
2. **Database Logger** (Step 2): Stores positions in PostgreSQL for long-term storage
3. **HTTP API** (Step 3): Serves current positions and historical trajectories for Unreal Engine integration

## Prerequisites

- Python 3.9 or higher
- `dump1090` installed and available in PATH
- RTL-SDR dongle and antenna (for receiving ADS-B signals)

## Quick Start - Step 1 (CSV Logger)

### One Command to Run Everything

Simply run:

```bash
./adsb.sh csv
```

That's it! The script will:
- Check if dump1090 is available
- Start dump1090 in the background (if not already running)
- Wait for it to be ready
- Start the CSV logger
- Automatically clean up dump1090 when you press Ctrl+C

### Verify Output

The script creates two CSV files:

1. **Historical positions** (`adsb_history.csv`): All position records (append-only)
2. **Current positions** (`adsb_current.csv`): Latest position per aircraft seen in the last 60 seconds (snapshot, updated continuously)

Check the historical file:

```bash
head -20 adsb_history.csv
```

Or watch it in real-time:

```bash
tail -f adsb_history.csv
```

Check the current positions snapshot:

```bash
cat adsb_current.csv
```

You should see rows like:

```csv
timestamp_utc,icao,flight,lat,lon,altitude_ft,speed_kts,heading_deg,squawk
2025-12-07T17:01:58.400000+00:00,3C5EF2,EWG4TV,45.630,8.936,11100,376,158,2531
...
```

The current CSV contains one row per aircraft seen in the last 60 seconds (latest position), while the historical CSV contains all positions over time. Aircraft that haven't been seen recently are automatically filtered out of the current CSV.

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DUMP1090_CMD` | `dump1090` | dump1090 command name or path |
| `ADSB_HOST` | `127.0.0.1` | dump1090 host address |
| `ADSB_PORT` | `30003` | dump1090 SBS-1 port |
| `ADSB_CSV_PATH` | `adsb_history.csv` | Historical positions CSV file path |
| `ADSB_CURRENT_CSV_PATH` | `adsb_current.csv` | Current positions snapshot CSV file path |
| `ADSB_CURRENT_MAX_AGE_SECONDS` | `60` | Maximum age (seconds) for aircraft to appear in current CSV |

### Example with custom settings:

```bash
export ADSB_HOST=192.168.1.100
export ADSB_PORT=30003
export ADSB_CSV_PATH=/data/adsb/history.csv
export ADSB_CURRENT_CSV_PATH=/data/adsb/current.csv
./adsb.sh csv
```

## Project Structure

```
adsb/
├── SPEC.md              # Full project specification
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── adsb.sh              # One script to rule them all (starts dump1090 + Python)
├── adsb_to_csv.py      # Step 1: CSV logger (MVP)
├── plot_map.py          # Map visualization tool
├── adsb_to_db.py       # Step 2: Database logger (TODO)
└── api/                 # Step 3: HTTP API (TODO)
    ├── main.py
    ├── models.py
    └── db.py
```

## Usage

The `adsb.sh` script is the unified entry point for all operations:

```bash
# 🚀 ONE COMMAND TO RULE THEM ALL: Start capture + live map updates
./adsb.sh live

# Or use individual modes:
./adsb.sh csv          # CSV logger only (Step 1)
./adsb.sh db           # Database logger (Step 2 - when implemented)
./adsb.sh api          # HTTP API server (Step 3 - when implemented)

# Show help
./adsb.sh
```

**The `live` mode:**
- Starts dump1090 automatically
- Captures ADS-B data to CSV files
- Auto-updates the map every 10 seconds
- Opens `adsb_map.html` in your browser and refresh to see updates!

## Map Visualization

### Static Map

Plot aircraft positions on an interactive map:

```bash
# Plot current positions
python3 plot_map.py

# Plot all historical positions (from adsb_history.csv)
python3 plot_map.py --historical

# Plot trajectory for specific aircraft
python3 plot_map.py --icao 3C5EF2

# Custom output file
python3 plot_map.py --output my_map.html
```

### Real-Time Map Updates

For real-time map updates while capturing data:

**Terminal 1:** Start data capture
```bash
./adsb.sh csv
```

**Terminal 2:** Auto-update map
```bash
# Watch current positions and update map every 10 seconds
python3 watch_map.py

# Or watch historical positions
python3 watch_map.py --historical

# Custom update interval (e.g., every 5 seconds)
python3 watch_map.py --interval 5
```

**Browser:** Open `adsb_map.html` and refresh periodically, or use a browser extension that auto-refreshes.

**Requirements:** Install folium first:
```bash
pip install folium
```

The scripts generate an interactive HTML map that you can open in any web browser. Features:
- Interactive markers for each aircraft
- Trajectory lines showing flight paths
- Popups with aircraft details (ICAO, flight, altitude, speed, heading)
- Multiple map tile layers (OpenStreetMap, CartoDB)
- Color-coded aircraft for easy identification
- Auto-updates when using `watch_map.py`

## Implementation Status

- ✅ **Step 1**: CSV logger (`adsb_to_csv.py`) - Complete
- ✅ **Map Visualization**: Interactive map plotting (`plot_map.py`) - Complete
- ⏳ **Step 2**: Database logger (`adsb_to_db.py`) - Planned
- ⏳ **Step 3**: HTTP API (`api/`) - Planned

## Troubleshooting

### dump1090 not found

If you see "dump1090 not found in PATH":
- Install dump1090 or ensure it's in your PATH
- Or set `DUMP1090_CMD` to the full path: `export DUMP1090_CMD=/path/to/dump1090`

### Port already in use

If port 30003 is already in use, the script will detect it and assume dump1090 is already running. This is fine - the logger will connect to the existing instance.

### No data in CSV

- Verify dump1090 is receiving aircraft (check the interactive table in dump1090 output)
- Ensure you're in an area with ADS-B traffic
- Check that the CSV file is writable

### Permission errors

Make sure the script is executable:

```bash
chmod +x adsb.sh
```

And that the CSV file location is writable:

```bash
export ADSB_CSV_PATH=/path/with/write/permissions/adsb_positions.csv
```

## Portability

The code uses only Python standard library for Step 1, ensuring it runs identically on:
- macOS (tested)
- Linux (generic)
- Raspberry Pi OS

The shell script uses standard POSIX commands (`lsof`, `kill`, etc.) that are available on all Unix-like systems.

## Next Steps

See `SPEC.md` for detailed specifications of:
- Step 2: Database storage with PostgreSQL
- Step 3: HTTP API for Unreal Engine integration

## License

[Add your license here]
