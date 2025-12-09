"""
Core ADS-B parsing and state tracking utilities.

This module contains reusable pieces for reading SBS-1/BaseStation lines,
merging partial messages into a per-aircraft state, and producing position
records ready for storage or exposure via APIs.

It is intentionally light on I/O so callers can reuse the logic in
different contexts (CSV logger, DB writer, API server, tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass
class ParsedMessage:
    """Structured representation of a single SBS-1 line."""

    icao: str
    flight: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_ft: Optional[int] = None
    speed_kts: Optional[float] = None
    heading_deg: Optional[float] = None
    squawk: Optional[str] = None
    has_position: bool = False


def parse_sbs_line(line: str) -> Optional[ParsedMessage]:
    """
    Parse a single SBS-1/BaseStation CSV line.

    Returns ParsedMessage or None if the line is not usable.
    """
    line = line.strip()
    if not line:
        return None

    fields = line.split(",")

    # Must be a MSG line with an ICAO code
    if len(fields) < 5 or fields[0] != "MSG":
        return None

    icao = fields[4].strip()
    if not icao:
        return None

    parsed = ParsedMessage(icao=icao)

    # Callsign / flight
    if len(fields) > 10 and fields[10].strip():
        parsed.flight = fields[10].strip()

    # Altitude (ft)
    if len(fields) > 11 and fields[11].strip():
        try:
            parsed.altitude_ft = int(float(fields[11]))
        except ValueError:
            pass

    # Speed (kts)
    if len(fields) > 12 and fields[12].strip():
        try:
            parsed.speed_kts = float(fields[12])
        except ValueError:
            pass

    # Heading (deg)
    if len(fields) > 13 and fields[13].strip():
        try:
            parsed.heading_deg = float(fields[13])
        except ValueError:
            pass

    # Position
    if len(fields) > 15:
        lat_str = fields[14].strip()
        lon_str = fields[15].strip()
        try:
            if lat_str and lon_str:
                lat = float(lat_str)
                lon = float(lon_str)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    parsed.lat = lat
                    parsed.lon = lon
                    parsed.has_position = True
        except ValueError:
            pass

    # Squawk
    if len(fields) > 17 and fields[17].strip():
        parsed.squawk = fields[17].strip()

    return parsed


@dataclass
class AircraftState:
    """Tracks the latest known data for a single aircraft."""

    icao: str
    flight: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_ft: Optional[int] = None
    speed_kts: Optional[float] = None
    heading_deg: Optional[float] = None
    squawk: Optional[str] = None
    last_update: Optional[str] = None

    def as_position(self) -> Optional[Dict[str, Any]]:
        """Return a position dict if we have at least a valid lat/lon."""
        if self.lat is None or self.lon is None:
            return None
        return {
            "icao": self.icao,
            "flight": self.flight,
            "lat": self.lat,
            "lon": self.lon,
            "altitude_ft": self.altitude_ft,
            "speed_kts": self.speed_kts,
            "heading_deg": self.heading_deg,
            "squawk": self.squawk,
        }


@dataclass
class AircraftStateTracker:
    """
    Maintains per-aircraft state across multiple messages.

    update() merges the latest ParsedMessage and returns:
      - position dict (if we have lat/lon), otherwise None
      - boolean indicating whether the record has full position+velocity data
    """

    _state: Dict[str, AircraftState] = field(default_factory=dict)

    def update(self, msg: ParsedMessage) -> Tuple[Optional[Dict[str, Any]], bool]:
        state = self._state.get(msg.icao)
        if state is None:
            state = AircraftState(icao=msg.icao)
            self._state[msg.icao] = state

        if msg.flight:
            state.flight = msg.flight
        if msg.lat is not None:
            state.lat = msg.lat
        if msg.lon is not None:
            state.lon = msg.lon
        if msg.altitude_ft is not None:
            state.altitude_ft = msg.altitude_ft
        if msg.speed_kts is not None:
            state.speed_kts = msg.speed_kts
        if msg.heading_deg is not None:
            state.heading_deg = msg.heading_deg
        if msg.squawk:
            state.squawk = msg.squawk

        state.last_update = datetime.now(timezone.utc).isoformat()

        position = state.as_position()
        has_full_velocity = position is not None and state.speed_kts is not None and state.heading_deg is not None
        return position, has_full_velocity

    def latest_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Return a snapshot of latest positions (including timestamps) keyed by ICAO.
        Only includes aircraft with a valid position.
        """
        snapshot: Dict[str, Dict[str, Any]] = {}
        for icao, state in self._state.items():
            position = state.as_position()
            if position:
                snapshot[icao] = {
                    **position,
                    "timestamp_utc": state.last_update or datetime.now(timezone.utc).isoformat(),
                }
        return snapshot
