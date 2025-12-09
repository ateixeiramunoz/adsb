#!/usr/bin/env python3
"""
ADS-B Map Plotter

Plots aircraft positions from CSV files onto an interactive map.
Supports both current positions and historical trajectories.

Usage:
    python3 plot_map.py                    # Plot current positions
    python3 plot_map.py --historical       # Plot all historical positions
    python3 plot_map.py --icao 3C5EF2     # Plot trajectory for specific aircraft
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


def read_csv_positions(csv_path: str) -> List[Dict[str, Any]]:
    """Read positions from a CSV file."""
    positions = []
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        return positions
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
            try:
                # Skip empty rows
                if not row.get("icao") or not row.get("lat") or not row.get("lon"):
                    continue
                
                lat = float(row["lat"])
                lon = float(row["lon"])
                
                position = {
                    "timestamp_utc": row.get("timestamp_utc", ""),
                    "icao": row.get("icao", "").strip(),
                    "flight": row.get("flight", "").strip(),
                    "lat": lat,
                    "lon": lon,
                    "altitude_ft": int(float(row["altitude_ft"])) if row.get("altitude_ft") and row["altitude_ft"].strip() else None,
                    "speed_kts": float(row["speed_kts"]) if row.get("speed_kts") and row["speed_kts"].strip() else None,
                    "heading_deg": float(row["heading_deg"]) if row.get("heading_deg") and row["heading_deg"].strip() else None,
                    "squawk": row.get("squawk", "").strip(),
                }
                positions.append(position)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row {row_num} in {csv_path}: {e}", file=sys.stderr)
                continue
    
    return positions


def get_altitude_color(altitude_ft: Optional[int]) -> str:
    """
    Get color based on altitude with progressive interpolation.
    Returns folium-compatible colors: orange, lightred, green, lightblue, blue, purple
    """
    if altitude_ft is None:
        return "gray"
    
    # Color stops: (altitude_ft, folium_color)
    # Mapped to valid folium colors: orange -> lightred -> green -> lightblue -> blue -> purple
    color_stops = [
        (0, "orange"),        # 0ft - orange
        (4000, "lightred"),   # 4000ft - yellow-ish (using lightred as closest)
        (8000, "green"),      # 8000ft - green
        (20000, "lightblue"), # 20000ft - cyan-ish (using lightblue)
        (30000, "blue"),      # 30000ft - blue
        (40000, "purple"),    # 40000ft - magenta-ish (using purple)
    ]
    
    # Find the two stops to interpolate between
    if altitude_ft <= color_stops[0][0]:
        return color_stops[0][1]
    if altitude_ft >= color_stops[-1][0]:
        return color_stops[-1][1]
    
    # Find the segment
    for i in range(len(color_stops) - 1):
        if color_stops[i][0] <= altitude_ft <= color_stops[i + 1][0]:
            # Interpolate between these two colors
            alt1, color1 = color_stops[i]
            alt2, color2 = color_stops[i + 1]
            
            # Simple interpolation - use the lower color if close, higher if far
            ratio = (altitude_ft - alt1) / (alt2 - alt1)
            if ratio < 0.5:
                return color1
            else:
                return color2
    
    return "gray"


def create_map(positions: List[Dict[str, Any]], output_path: str = "adsb_map.html", 
                title: str = "ADS-B Aircraft Positions", refresh_interval: int = 1,
                current_icaos: Optional[set] = None) -> None:
    """Create an interactive map with aircraft positions using folium."""
    try:
        import folium
        from folium import plugins
    except ImportError:
        print("Error: folium is not installed.", file=sys.stderr)
        print("Install it with: pip install folium", file=sys.stderr)
        sys.exit(1)
    
    if not positions:
        print("No positions to plot.", file=sys.stderr)
        return
    
    # Calculate center of map from positions
    # If we have current ICAOs, prioritize centering on those
    if current_icaos:
        current_positions = [p for p in positions if p["icao"] in current_icaos]
        if current_positions:
            lats = [p["lat"] for p in current_positions]
            lons = [p["lon"] for p in current_positions]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            print(f"Centering map on current aircraft: {len(current_positions)} positions")
        else:
            lats = [p["lat"] for p in positions]
            lons = [p["lon"] for p in positions]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
    else:
        lats = [p["lat"] for p in positions]
        lons = [p["lon"] for p in positions]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,  # Slightly zoomed in to better see aircraft
        tiles="OpenStreetMap"
    )
    
    # Add different tile layers
    folium.TileLayer("CartoDB positron").add_to(m)
    folium.TileLayer("CartoDB dark_matter").add_to(m)
    
    # Add home position marker if specified (default to Via Pezzolo 6, Cannobio, Ticino)
    # Note: This is likely Canobbio in Ticino, Switzerland (not Cannobio, Italy)
    # Using approximate coordinates for Canobbio, Ticino - user should provide exact coordinates
    home_lat = os.getenv("ADSB_HOME_LAT", "46.0359")
    home_lon = os.getenv("ADSB_HOME_LON", "8.9661")
    home_lat_str = ""
    home_lon_str = ""
    if home_lat and home_lon:
        try:
            home_lat_float = float(home_lat)
            home_lon_float = float(home_lon)
            home_lat_str = str(home_lat_float)
            home_lon_str = str(home_lon_float)
            # Use DivIcon for custom "H" icon
            from folium import DivIcon
            home_icon_html = '''
            <div style="
                background-color: red;
                border: 2px solid white;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 18px;
                color: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            ">H</div>
            '''
            home_icon = DivIcon(
                html=home_icon_html,
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                className='home-marker'  # Important: allows JavaScript to identify and preserve this marker
            )
            folium.Marker(
                location=[home_lat_float, home_lon_float],
                popup=folium.Popup("<b>Home Position</b>", max_width=200),
                tooltip="Home",
                icon=home_icon,
            ).add_to(m)
        except (ValueError, TypeError):
            pass  # Skip if coordinates are invalid
    
    # Determine which aircraft are currently visible (have recent positions)
    # If current_icaos is provided, use it; otherwise determine from timestamps
    if current_icaos is None:
        current_icaos = set()
        from datetime import datetime, timezone
        try:
            current_time = datetime.now(timezone.utc)
            for pos in positions:
                if pos.get("timestamp_utc"):
                    try:
                        pos_time = datetime.fromisoformat(pos["timestamp_utc"].replace('Z', '+00:00'))
                        # If position is within last 2 minutes, consider it current
                        if (current_time - pos_time).total_seconds() < 120:
                            current_icaos.add(pos["icao"])
                    except:
                        pass
        except:
            # Fallback: if we can't determine, show markers for all
            current_icaos = set(p["icao"] for p in positions)
    
    # Group positions by ICAO for trajectories
    
    if len(positions) > 0:
        # Group all positions by ICAO
        icao_groups = {}
        for pos in positions:
            icao = pos["icao"]
            if icao not in icao_groups:
                icao_groups[icao] = []
            icao_groups[icao].append(pos)
        
        for idx, (icao, pos_list) in enumerate(icao_groups.items()):
            # Sort by timestamp if available
            try:
                pos_list_sorted = sorted(
                    pos_list,
                    key=lambda p: p.get("timestamp_utc", ""),
                    reverse=True
                )
            except:
                pos_list_sorted = pos_list
            
            # Latest position
            latest = pos_list_sorted[0]
            
            # Get color based on latest altitude
            marker_color = get_altitude_color(latest.get("altitude_ft"))
            
            # Only show marker for currently visible aircraft
            # But always draw trajectory lines for all aircraft with multiple positions
            is_current = icao in current_icaos if current_icaos else True
            
            # NOTE: Markers for current aircraft are created dynamically by JavaScript
            # to avoid duplicates and allow real-time updates. Only trajectory lines
            # are created here in Python.
            
            # Always draw trajectory if we have multiple positions (for both current and historical aircraft)
            # Sort by timestamp for proper trajectory order
            try:
                pos_list_sorted_by_time = sorted(
                    pos_list,
                    key=lambda p: p.get("timestamp_utc", ""),
                    reverse=False  # Oldest first for trajectory
                )
            except:
                pos_list_sorted_by_time = pos_list
            
            # Draw trajectory line connecting all historical positions
            if len(pos_list_sorted_by_time) > 1:
                trajectory_coords = [[p["lat"], p["lon"]] for p in pos_list_sorted_by_time]
                # Use altitude-based color for all lines, but different opacity
                # Current aircraft: full opacity (0.6), historical: semi-transparent (0.3)
                line_opacity = 0.6 if is_current else 0.3
                folium.PolyLine(
                    trajectory_coords,
                    color=marker_color,  # Always use altitude-based color
                    weight=2,
                    opacity=line_opacity,
                    popup=f"Trajectory: {icao} ({len(pos_list_sorted_by_time)} points)",
                    tooltip=f"{icao} path",
                ).add_to(m)
    else:
        # Single position or single aircraft
        # NOTE: Markers are created dynamically by JavaScript to avoid duplicates
        # Only trajectory lines are created here in Python (if multiple positions exist)
        pass
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Prepare positions data for JavaScript (will be embedded in HTML)
    positions_data = [
        {
            "icao": p["icao"],
            "flight": p.get("flight", ""),
            "lat": p["lat"],
            "lon": p["lon"],
            "altitude_ft": p.get("altitude_ft"),
            "speed_kts": p.get("speed_kts"),
            "heading_deg": p.get("heading_deg"),
            "squawk": p.get("squawk", ""),
            "timestamp_utc": p.get("timestamp_utc", "")
        }
        for p in positions
    ]
    positions_json = json.dumps(positions_data)
    
    # Prepare current ICAOs list for JavaScript (aircraft that should show markers)
    current_icaos_list = list(current_icaos) if current_icaos else []
    current_icaos_json = json.dumps(current_icaos_list)
    
    # Also save to JSON file for HTTP fetching
    json_path = os.path.splitext(output_path)[0] + "_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(positions_json)
    
    # Add title
    title_html = f'''
    <h3 id="map-title" style="position:fixed;
               top:10px;left:50px;width:320px;z-index:1000;
               background-color:white;padding:10px;
               border:2px solid grey;border-radius:5px;
               font-size:14px">
    {title}<br>
    <span id="map-stats" style="font-size:12px">Aircraft: {len(set(p["icao"] for p in positions))} | Positions: {len(positions)}</span><br>
    <span style="font-size:10px;color:#666;">Auto-updating every 1s</span>
    </h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add JavaScript for dynamic marker updates
    # Embed positions data directly in HTML to avoid CORS issues with file:// protocol
    update_js = f'''
    <script>
    // Embedded positions data (updated when HTML is regenerated or via HTTP fetch)
    let embeddedPositionsData = {positions_json};
    
    // Current ICAOs (aircraft that should show markers, not just lines)
    let currentICAOs = new Set({current_icaos_json});
    
    let markerLayer = null;
    let lineLayer = null;
    let currentMarkers = {{}};
    let currentLines = {{}};
    let homeMarker = null;  // Global reference to home marker - NEVER remove this
    
    // Initialize layers after map loads - run immediately to prevent static markers from showing
    (function initializeMap() {{
        function findMap() {{
            // Find the map object - folium creates a variable with the map div ID
            let mapObj = null;
            
            // Method 1: Find the folium map div and get its variable
            const mapDiv = document.querySelector('.folium-map, [id^="map_"]');
            if (mapDiv && mapDiv.id) {{
                // Folium creates a variable with the same name as the div ID
                const mapVarName = mapDiv.id;
                if (typeof window[mapVarName] !== 'undefined' && window[mapVarName] instanceof L.Map) {{
                    mapObj = window[mapVarName];
                }}
            }}
            
            // Method 2: Check window.map (fallback)
            if (!mapObj && typeof window.map !== 'undefined' && window.map instanceof L.Map) {{
                mapObj = window.map;
            }}
            
            // Method 3: Try to find via Leaflet instances (if available)
            if (!mapObj && typeof L !== 'undefined' && L.Map && L.Map._instances) {{
                const instanceIds = Object.keys(L.Map._instances);
                if (instanceIds.length > 0) {{
                    mapObj = L.Map._instances[instanceIds[0]];
                }}
            }}
            
            // Method 4: Find map div and get from _leaflet_id (if available)
            if (!mapObj && mapDiv) {{
                const leafletId = mapDiv._leaflet_id;
                if (leafletId && L.Map && L.Map._instances && L.Map._instances[leafletId]) {{
                    mapObj = L.Map._instances[leafletId];
                }}
            }}
            
            if (mapObj && mapObj instanceof L.Map) {{
                // AGGRESSIVELY remove ALL existing aircraft markers (but preserve home marker)
                // This ensures we start with a clean slate - only JavaScript will create aircraft markers
                const layersToRemove = [];
                mapObj.eachLayer(function(layer) {{
                    // Remove ALL markers EXCEPT home marker
                    if (layer instanceof L.Marker) {{
                        // Check if this is the home marker by checking icon className
                        const isHomeMarker = layer.options && 
                                           layer.options.icon && 
                                           (layer.options.icon.options || layer.options.icon) &&
                                           (layer.options.icon.options ? layer.options.icon.options.className : layer.options.icon.className) === 'home-marker';
                        if (!isHomeMarker) {{
                            layersToRemove.push(layer);
                        }}
                    }}
                }});
                // Also check for markers in any feature groups before removing (preserve home marker)
                mapObj.eachLayer(function(layer) {{
                    if (layer instanceof L.FeatureGroup || layer instanceof L.LayerGroup) {{
                        layer.eachLayer(function(sublayer) {{
                            if (sublayer instanceof L.Marker) {{
                                const isHomeMarker = sublayer.options && 
                                                   sublayer.options.icon && 
                                                   (sublayer.options.icon.options || sublayer.options.icon) &&
                                                   (sublayer.options.icon.options ? sublayer.options.icon.options.className : sublayer.options.icon.className) === 'home-marker';
                                if (!isHomeMarker) {{
                                    layersToRemove.push(sublayer);
                                }}
                            }}
                        }});
                    }}
                }});
                
                // Remove all collected markers (home marker is excluded)
                // CRITICAL: Never remove homeMarker - it's stored globally and must always be visible
                layersToRemove.forEach(function(layer) {{
                    try {{
                        // Double-check: never remove the home marker
                        if (layer === homeMarker) {{
                            console.log('WARNING: Attempted to remove home marker - skipping!');
                            return;
                        }}
                        if (layer._map) {{
                            layer._map.removeLayer(layer);
                        }} else {{
                            mapObj.removeLayer(layer);
                        }}
                    }} catch(e) {{
                        // Ignore errors if layer already removed
                    }}
                }});
                
                // Create feature groups for markers and lines
                markerLayer = L.featureGroup();
                lineLayer = L.featureGroup();
                mapObj.addLayer(markerLayer);
                mapObj.addLayer(lineLayer);
                
                // ALWAYS add home position marker - this is CRITICAL and must NEVER be removed
                const homeLat = '{home_lat_str}';
                const homeLon = '{home_lon_str}';
                console.log('Home position:', homeLat, homeLon);
                if (homeLat && homeLon && homeLat !== '' && homeLon !== '') {{
                    try {{
                        const lat = parseFloat(homeLat);
                        const lon = parseFloat(homeLon);
                        console.log('Parsed home coordinates:', lat, lon);
                        if (!isNaN(lat) && !isNaN(lon)) {{
                            // Remove existing home marker if it exists
                            if (homeMarker && mapObj.hasLayer(homeMarker)) {{
                                mapObj.removeLayer(homeMarker);
                            }}
                            
                            const homeIcon = L.divIcon({{
                                className: 'home-marker',
                                html: '<div style="background-color: red; border: 2px solid white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">H</div>',
                                iconSize: [30, 30],
                                iconAnchor: [15, 15]
                            }});
                            homeMarker = L.marker([lat, lon], {{
                                icon: homeIcon
                            }}).bindPopup('<b>Home Position<br>Cannobio, Ticino</b>');
                            mapObj.addLayer(homeMarker);
                            console.log('HOME MARKER ADDED at:', lat, lon);
                        }} else {{
                            console.log('Invalid home coordinates:', lat, lon);
                        }}
                    }} catch(e) {{
                        console.log('Could not add home marker:', e);
                    }}
                }} else {{
                    console.log('Home coordinates not provided');
                }}
                
                // Initial render
                updateMarkers(embeddedPositionsData);
                
                // Start checking for updates
                startAutoUpdate();
            }} else {{
                console.log('Map not found, retrying...');
                setTimeout(findMap, 100);
            }}
        }}
        
        // Try immediately, then retry if needed
        findMap();
        
        // Also try after DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', findMap);
        }}
    }})();
    
    function getAltitudeColor(altitude_ft) {{
        if (altitude_ft === null || altitude_ft === undefined) return 'gray';
        
        // Mapped to valid folium/AwesomeMarkers colors
        const colorStops = [
            [0, 'orange'],        // 0ft - orange
            [4000, 'lightred'],    // 4000ft - yellow-ish (using lightred)
            [8000, 'green'],      // 8000ft - green
            [20000, 'lightblue'], // 20000ft - cyan-ish (using lightblue)
            [30000, 'blue'],      // 30000ft - blue
            [40000, 'purple']     // 40000ft - magenta-ish (using purple)
        ];
        
        if (altitude_ft <= colorStops[0][0]) return colorStops[0][1];
        if (altitude_ft >= colorStops[colorStops.length - 1][0]) return colorStops[colorStops.length - 1][1];
        
        for (let i = 0; i < colorStops.length - 1; i++) {{
            if (altitude_ft >= colorStops[i][0] && altitude_ft <= colorStops[i + 1][0]) {{
                const ratio = (altitude_ft - colorStops[i][0]) / (colorStops[i + 1][0] - colorStops[i][0]);
                return ratio < 0.5 ? colorStops[i][1] : colorStops[i + 1][1];
            }}
        }}
        return 'gray';
    }}
    
    function startAutoUpdate() {{
        // Check if we're being served via HTTP (not file://)
        const isHttp = window.location.protocol === 'http:' || window.location.protocol === 'https:';
        
        if (isHttp) {{
            // HTTP mode: fetch JSON data file
            updateMapData();
            setInterval(updateMapData, 1000);
        }} else {{
            // file:// mode: use embedded data (will update when HTML is regenerated)
            // Update markers with embedded data every second
            setInterval(function() {{
                updateMarkers(embeddedPositionsData);
            }}, 1000);
        }}
    }}
    
    function updateMapData() {{
        // Fetch JSON data file (works when served via HTTP)
        fetch('adsb_map_data.json?t=' + new Date().getTime())
            .then(response => response.json())
            .then(data => {{
                embeddedPositionsData = data; // Update embedded data
                
                // IMPORTANT: currentICAOs should ONLY come from adsb_current.csv (embedded set)
                // Do NOT recalculate from timestamps - this ensures aircraft in adsb_current.csv
                // always show markers, regardless of timestamp age
                // The embedded currentICAOs set is the source of truth
                
                updateMarkers(data);
            }})
            .catch(error => {{
                console.log('Update failed:', error);
            }});
    }}
    
    function updateMarkers(positions) {{
        if (!markerLayer || !lineLayer) return;
        
        // CRITICAL: ENSURE HOME MARKER IS ALWAYS PRESENT - CHECK FIRST, BEFORE ANYTHING ELSE
        const mapObj = markerLayer._map;
        if (mapObj) {{
            if (!homeMarker) {{
                // Home marker doesn't exist, create it
                const homeLat = '{home_lat_str}';
                const homeLon = '{home_lon_str}';
                if (homeLat && homeLon && homeLat !== '' && homeLon !== '') {{
                    try {{
                        const lat = parseFloat(homeLat);
                        const lon = parseFloat(homeLon);
                        if (!isNaN(lat) && !isNaN(lon)) {{
                            const homeIcon = L.divIcon({{
                                className: 'home-marker',
                                html: '<div style="background-color: red; border: 2px solid white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">H</div>',
                                iconSize: [30, 30],
                                iconAnchor: [15, 15]
                            }});
                            homeMarker = L.marker([lat, lon], {{
                                icon: homeIcon
                            }}).bindPopup('<b>Home Position<br>Cannobio, Ticino</b>');
                            mapObj.addLayer(homeMarker);
                            console.log('HOME MARKER RE-CREATED at:', lat, lon);
                        }}
                    }} catch(e) {{
                        console.log('Could not create home marker:', e);
                    }}
                }}
            }} else if (!mapObj.hasLayer(homeMarker)) {{
                // Home marker exists but not on map, re-add it
                console.log('Home marker missing from map, re-adding it!');
                mapObj.addLayer(homeMarker);
            }}
        }}
        
        console.log('=== updateMarkers called with', positions.length, 'positions ===');
        console.log('currentICAOs (from adsb_current.csv):', Array.from(currentICAOs));
        console.log('currentICAOs size:', currentICAOs.size);
        console.log('currentICAOs.has(4405EA):', currentICAOs.has('4405EA'));
        console.log('currentICAOs.has(4CA88C):', currentICAOs.has('4CA88C'));
        
        // Group by ICAO
        const icaoGroups = {{}};
        positions.forEach(pos => {{
            if (!icaoGroups[pos.icao]) {{
                icaoGroups[pos.icao] = [];
            }}
            icaoGroups[pos.icao].push(pos);
        }});
        
        console.log('ICAO groups in data:', Object.keys(icaoGroups));
        console.log('ICAOs that should have markers:', Array.from(currentICAOs).filter(icao => icaoGroups[icao]));
        
        // Update stats
        const statsEl = document.getElementById('map-stats');
        if (statsEl) {{
            statsEl.textContent = `Aircraft: ${{Object.keys(icaoGroups).length}} | Positions: ${{positions.length}} | Current: ${{currentICAOs.size}}`;
        }}
        
        // CRITICAL: Remove markers for aircraft that are NOT in currentICAOs (adsb_current.csv)
        // This ensures only aircraft in adsb_current.csv have markers
        // BUT: Never touch the home marker!
        Object.keys(currentMarkers).forEach(icao => {{
            if (!currentICAOs.has(icao)) {{
                console.log('Removing marker for ICAO not in adsb_current.csv:', icao);
                const marker = currentMarkers[icao];
                // Double-check: never remove home marker
                if (marker !== homeMarker) {{
                    markerLayer.removeLayer(marker);
                    delete currentMarkers[icao];
                }} else {{
                    console.log('WARNING: Attempted to remove home marker - preserving it!');
                }}
            }}
        }});
        
        // Remove all lines and recreate them
        lineLayer.clearLayers();
        currentLines = {{}};
        
        // Process each aircraft
        Object.keys(icaoGroups).forEach(icao => {{
            const posList = icaoGroups[icao];
            // Sort by timestamp
            posList.sort((a, b) => {{
                return (a.timestamp_utc || '').localeCompare(b.timestamp_utc || '');
            }});
            
            const latest = posList[posList.length - 1];
            const color = getAltitudeColor(latest.altitude_ft);
            
            // Only show marker for aircraft in adsb_current.csv (currentICAOs set)
            const isCurrent = currentICAOs.has(icao);
            
            console.log('ICAO:', icao, 'isCurrent (in adsb_current.csv):', isCurrent, 'currentICAOs.has:', currentICAOs.has(icao));
            
            if (isCurrent) {{
                // This aircraft is in adsb_current.csv, so it should have a marker
                console.log('*** PROCESSING CURRENT AIRCRAFT:', icao, 'at', latest.lat, latest.lon, 'altitude:', latest.altitude_ft);
                
                // Update existing marker or create new one
                if (currentMarkers[icao]) {{
                    console.log('Updating existing marker for:', icao);
                    // Update existing marker position and popup
                    currentMarkers[icao].setLatLng([latest.lat, latest.lon]);
                    
                    // Update popup
                    let popupText = `<b>ICAO:</b> ${{latest.icao}}<br>`;
                    if (latest.flight) popupText += `<b>Flight:</b> ${{latest.flight}}<br>`;
                    if (latest.altitude_ft) popupText += `<b>Altitude:</b> ${{latest.altitude_ft.toLocaleString()}} ft<br>`;
                    if (latest.speed_kts) popupText += `<b>Speed:</b> ${{Math.round(latest.speed_kts)}} kts<br>`;
                    if (latest.heading_deg) popupText += `<b>Heading:</b> ${{Math.round(latest.heading_deg)}}°<br>`;
                    if (latest.squawk) popupText += `<b>Squawk:</b> ${{latest.squawk}}<br>`;
                    if (latest.timestamp_utc) popupText += `<b>Time:</b> ${{latest.timestamp_utc}}`;
                    currentMarkers[icao].setPopupContent(popupText);
                    
                    // Update icon color if altitude changed
                    const newIcon = L.AwesomeMarkers.icon({{
                        icon: 'plane',
                        prefix: 'fa',
                        markerColor: color
                    }});
                    currentMarkers[icao].setIcon(newIcon);
                    console.log('Marker updated for:', icao);
                }} else {{
                    // Create new marker for aircraft in adsb_current.csv
                    console.log('*** CREATING NEW MARKER for ICAO:', icao, 'at', latest.lat, latest.lon);
                    let popupText = `<b>ICAO:</b> ${{latest.icao}}<br>`;
                    if (latest.flight) popupText += `<b>Flight:</b> ${{latest.flight}}<br>`;
                    if (latest.altitude_ft) popupText += `<b>Altitude:</b> ${{latest.altitude_ft.toLocaleString()}} ft<br>`;
                    if (latest.speed_kts) popupText += `<b>Speed:</b> ${{Math.round(latest.speed_kts)}} kts<br>`;
                    if (latest.heading_deg) popupText += `<b>Heading:</b> ${{Math.round(latest.heading_deg)}}°<br>`;
                    if (latest.squawk) popupText += `<b>Squawk:</b> ${{latest.squawk}}<br>`;
                    if (latest.timestamp_utc) popupText += `<b>Time:</b> ${{latest.timestamp_utc}}`;
                    
                    try {{
                        const marker = L.marker([latest.lat, latest.lon], {{
                            icon: L.AwesomeMarkers.icon({{
                                icon: 'plane',
                                prefix: 'fa',
                                markerColor: color
                            }})
                        }}).bindPopup(popupText);
                        markerLayer.addLayer(marker);
                        currentMarkers[icao] = marker;
                        console.log('*** AIRCRAFT MARKER SUCCESSFULLY CREATED for ICAO:', icao, 'at', latest.lat, latest.lon, 'color:', color);
                        console.log('Marker added to markerLayer, total markers now:', Object.keys(currentMarkers).length);
                    }} catch(e) {{
                        console.error('ERROR creating marker for', icao, ':', e);
                    }}
                }}
            }}
            
            // Draw trajectory line if multiple positions (for ALL aircraft, current and historical)
            if (posList.length > 1) {{
                const coords = posList.map(p => [p.lat, p.lon]);
                // Use altitude-based color for all lines, but different opacity
                // Current aircraft: full opacity (0.6), historical: semi-transparent (0.3)
                const lineOpacity = isCurrent ? 0.6 : 0.3;
                const line = L.polyline(coords, {{
                    color: color,  // Always use altitude-based color
                    weight: 2,
                    opacity: lineOpacity
                }}).bindPopup(`Trajectory: ${{icao}} (${{posList.length}} points)`);
                lineLayer.addLayer(line);
                currentLines[icao] = line;
            }}
        }});
        
        // FINAL CHECK: Ensure home marker is still on map after all updates
        if (homeMarker && mapObj && !mapObj.hasLayer(homeMarker)) {{
            console.log('Home marker lost during update, re-adding it!');
            mapObj.addLayer(homeMarker);
        }}
        
        console.log('updateMarkers complete. Total markers on map:', Object.keys(currentMarkers).length, 'ICAOs:', Object.keys(currentMarkers));
    }}
    </script>
    '''
    m.get_root().html.add_child(folium.Element(update_js))
    
    # Save map
    m.save(output_path)
    print(f"Map saved to: {output_path}")
    print(f"Open it in your browser. The map file updates automatically without page reload.")


def main():
    parser = argparse.ArgumentParser(
        description="Plot ADS-B aircraft positions on an interactive map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plot current positions with historical trajectories
  python3 plot_map.py

  # Plot all historical positions
  python3 plot_map.py --historical

  # Plot trajectory for specific aircraft
  python3 plot_map.py --icao 3C5EF2

  # Current positions only (no historical trajectories)
  python3 plot_map.py --no-history

  # Custom CSV file
  python3 plot_map.py --csv custom_positions.csv
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
        help="Use historical CSV file (adsb_history.csv) instead of current"
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Don't load historical data for trajectories (current positions only)"
    )
    parser.add_argument(
        "--icao",
        default=None,
        help="Filter to specific ICAO hex code"
    )
    parser.add_argument(
        "--output",
        default="adsb_map.html",
        help="Output HTML file path (default: adsb_map.html)"
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Map title (default: auto-generated)"
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=0,
        help="Auto-refresh interval in seconds (default: 0 = disabled, map updates via file regeneration)"
    )
    parser.add_argument(
        "--home-lat",
        type=float,
        default=None,
        help="Home position latitude (or set ADSB_HOME_LAT env var)"
    )
    parser.add_argument(
        "--home-lon",
        type=float,
        default=None,
        help="Home position longitude (or set ADSB_HOME_LON env var)"
    )
    
    args = parser.parse_args()
    
    # Determine CSV file
    if args.csv:
        csv_path = args.csv
        historical_csv_path = None
    elif args.historical:
        csv_path = os.getenv("ADSB_CSV_PATH", "adsb_history.csv")
        historical_csv_path = None
    else:
        csv_path = os.getenv("ADSB_CURRENT_CSV_PATH", "adsb_current.csv")
        # Load historical data for trajectories unless --no-history is set
        if not args.no_history:
            historical_csv_path = os.getenv("ADSB_CSV_PATH", "adsb_history.csv")
        else:
            historical_csv_path = None
    
    # Read positions
    print(f"Reading positions from: {csv_path}")
    positions = read_csv_positions(csv_path)
    
    # If we have current positions and historical file exists, merge trajectories
    if historical_csv_path and os.path.exists(historical_csv_path) and not args.historical:
        print(f"Loading historical trajectories from: {historical_csv_path}")
        historical_positions = read_csv_positions(historical_csv_path)
        
        if historical_positions:
            # Get ICAOs from current positions
            current_icaos = set(p["icao"] for p in positions)
            
            # Group historical positions by ICAO to find aircraft with trajectories
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
            
            print(f"Loaded {len(historical_positions)} historical positions for {len(historical_by_icao)} aircraft")
    
    if not positions:
        print("No positions found.", file=sys.stderr)
        sys.exit(1)
    
    # Filter by ICAO if specified
    if args.icao:
        positions = [p for p in positions if p["icao"].upper() == args.icao.upper()]
        if not positions:
            print(f"No positions found for ICAO: {args.icao}", file=sys.stderr)
            sys.exit(1)
    
    # Generate title
    if args.title:
        title = args.title
    elif args.icao:
        title = f"ADS-B Aircraft {args.icao.upper()}"
    elif args.historical:
        title = "ADS-B Historical Positions"
    else:
        title = "ADS-B Current Positions with Trajectories"
    
    # Determine current ICAOs (aircraft with recent positions) for marker display
    current_icaos_for_map = set()
    if not args.historical:
        # Read current CSV to get current ICAOs
        current_csv_path = os.getenv("ADSB_CURRENT_CSV_PATH", "adsb_current.csv")
        if os.path.exists(current_csv_path):
            current_only = read_csv_positions(current_csv_path)
            current_icaos_for_map = set(p["icao"] for p in current_only)
            print(f"Current ICAOs from {current_csv_path}: {current_icaos_for_map}")
            
            # CRITICAL: Ensure positions from adsb_current.csv are in the positions list
            # Add current positions if they're not already there (by ICAO and coordinates)
            # This ensures markers can be created for aircraft in adsb_current.csv
            current_positions_by_icao = {p["icao"]: p for p in current_only}
            for icao, current_pos in current_positions_by_icao.items():
                # Check if this position is already in the positions list
                is_duplicate = any(
                    p["icao"] == icao and 
                    abs(p["lat"] - current_pos["lat"]) < 0.0001 and
                    abs(p["lon"] - current_pos["lon"]) < 0.0001
                    for p in positions
                )
                if not is_duplicate:
                    # Add the current position to ensure it's in the embedded data
                    positions.insert(0, current_pos)  # Insert at beginning to prioritize current positions
                    print(f"Added current position for ICAO {icao} to embedded data: lat={current_pos['lat']}, lon={current_pos['lon']}")
                else:
                    print(f"Current position for ICAO {icao} already in positions list")
    
    # Set home position from args or environment variables
    if args.home_lat and args.home_lon:
        os.environ["ADSB_HOME_LAT"] = str(args.home_lat)
        os.environ["ADSB_HOME_LON"] = str(args.home_lon)
    
    print(f"Total positions for map: {len(positions)}, ICAOs: {len(set(p['icao'] for p in positions))}")
    print(f"Current ICAOs for markers: {current_icaos_for_map}")
    
    # Create map (will show markers for current aircraft, lines for all)
    create_map(positions, args.output, title, args.refresh, current_icaos_for_map)


if __name__ == "__main__":
    main()

