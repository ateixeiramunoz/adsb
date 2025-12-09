#!/usr/bin/env python3
"""
Watch and auto-update map from ADS-B CSV files.

Continuously regenerates the map HTML file as new positions are captured.
"""

import argparse
import os
import sys
import time
from plot_map import read_csv_positions, create_map


def watch_and_update(csv_path: str, output_path: str = "adsb_map.html", 
                     interval: int = 1, historical: bool = False):
    """Watch CSV file and regenerate map periodically."""
    print(f"Watching {csv_path} and updating {output_path} every {interval} second{'s' if interval != 1 else ''}...")
    print("Press Ctrl+C to stop.")
    print()
    
    # Determine historical CSV path for merging trajectories
    historical_csv_path = None
    if not historical:
        historical_csv_path = os.getenv("ADSB_CSV_PATH", "adsb_history.csv")
    
    last_size = 0
    update_count = 0
    
    try:
        while True:
            # Check if file exists and has changed
            if os.path.exists(csv_path):
                current_size = os.path.getsize(csv_path)
                
                if current_size != last_size or update_count == 0:
                    # File changed or first run
                    positions = read_csv_positions(csv_path)
                    
                    # Merge historical data for trajectories if watching current positions
                    if positions and historical_csv_path and os.path.exists(historical_csv_path) and not historical:
                        historical_positions = read_csv_positions(historical_csv_path)
                        
                        if historical_positions:
                            # Get ICAOs from current positions
                            current_icaos = set(p["icao"] for p in positions)
                            
                            # Group historical positions by ICAO
                            historical_by_icao = {}
                            for hist_pos in historical_positions:
                                icao = hist_pos["icao"]
                                if icao not in historical_by_icao:
                                    historical_by_icao[icao] = []
                                historical_by_icao[icao].append(hist_pos)
                            
                            # Add ALL historical positions (for both current and past aircraft)
                            # This shows trajectories for all aircraft that have historical data
                            for hist_pos in historical_positions:
                                # For currently visible aircraft, avoid duplicates with current positions
                                if hist_pos["icao"] in current_icaos:
                                    is_duplicate = any(
                                        p["icao"] == hist_pos["icao"] and 
                                        abs(p["lat"] - hist_pos["lat"]) < 0.0001 and
                                        abs(p["lon"] - hist_pos["lon"]) < 0.0001
                                        for p in positions
                                    )
                                    if not is_duplicate:
                                        positions.append(hist_pos)
                                else:
                                    # For aircraft not currently visible, add all their historical positions
                                    # This will show their trajectory lines even if they're not currently visible
                                    positions.append(hist_pos)
                    
                    if positions:
                        title = "ADS-B Current Positions with Trajectories" if not historical else "ADS-B Historical Positions"
                        # Determine current ICAOs for marker display
                        current_icaos_for_map = set()
                        if not historical:
                            current_csv_path = os.getenv("ADSB_CURRENT_CSV_PATH", "adsb_current.csv")
                            if os.path.exists(current_csv_path):
                                current_only = read_csv_positions(current_csv_path)
                                current_icaos_for_map = set(p["icao"] for p in current_only)
                        # Pass refresh_interval=0 (no page reload, but dynamic updates via JS)
                        create_map(positions, output_path, title, refresh_interval=0, current_icaos=current_icaos_for_map)
                        update_count += 1
                        print(f"[{update_count}] Map updated: {len(positions)} positions, {len(set(p['icao'] for p in positions))} aircraft")
                    else:
                        print("No positions found, skipping update...")
                    
                    last_size = current_size
                else:
                    print(f"Waiting... (no changes detected)")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n\nStopped. Total updates: {update_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Watch ADS-B CSV and auto-update map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch current positions (default)
  python3 watch_map.py

  # Watch historical positions
  python3 watch_map.py --historical

  # Update every 5 seconds
  python3 watch_map.py --interval 5
        """
    )
    
    parser.add_argument(
        "--csv",
        default=None,
        help="Path to CSV file (default: adsb_current.csv or adsb_history.csv)"
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Watch historical CSV file (adsb_history.csv) instead of current"
    )
    parser.add_argument(
        "--output",
        default="adsb_map.html",
        help="Output HTML file path (default: adsb_map.html)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Update interval in seconds (default: 1)"
    )
    
    args = parser.parse_args()
    
    # Determine CSV file
    if args.csv:
        csv_path = args.csv
    elif args.historical:
        csv_path = os.getenv("ADSB_CSV_PATH", "adsb_history.csv")
    else:
        csv_path = os.getenv("ADSB_CURRENT_CSV_PATH", "adsb_current.csv")
    
    watch_and_update(csv_path, args.output, args.interval, args.historical)


if __name__ == "__main__":
    main()

