"""Constants and pure helpers for the CRT Notices integration."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Mapping, Sequence, TypedDict

DOMAIN = "crt_notices"
INTEGRATION_NAME = "Canal and River Trust Notices"

CRT_API_URL = "https://canalrivertrust.org.uk/api/stoppage/notices"
CRT_NOTICE_BASE_URL = "https://canalrivertrust.org.uk"
CRT_BROWSE_URL = "https://canalrivertrust.org.uk/notices"

MODE_GPS = "gps"
MODE_MANUAL = "manual"

CONF_DEVICE_TRACKER_ENTITY_ID = "device_tracker_entity_id"
CONF_LOOKAHEAD_DAYS = "lookahead_days"
CONF_MODE = "mode"
CONF_RADIUS_MILES = "radius_miles"
CONF_SHOW_ALL_WATERWAYS = "show_all_waterways"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_WATERWAYS = "waterways"

DEFAULT_LOOKAHEAD_DAYS = 14
DEFAULT_RADIUS_MILES = 25
DEFAULT_SHOW_ALL_WATERWAYS = False
DEFAULT_UPDATE_INTERVAL_MINUTES = 60

MIN_LOOKAHEAD_DAYS = 1
MAX_LOOKAHEAD_DAYS = 90
MIN_RADIUS_MILES = 1
MAX_RADIUS_MILES = 100
MIN_UPDATE_INTERVAL_MINUTES = 15
MAX_UPDATE_INTERVAL_MINUTES = 1440

GPS_HOME_IDENTIFIER = "home"

API_FIELDS = (
    "title,region,waterways,path,typeId,reasonId,programmeId,start,end,state,image"
)

NAVIGATION_BLOCKING_TYPE_IDS = {1, 2, 9, 11}

NOTICE_TYPE_LOOKUP: dict[int, str] = {
    1: "Navigation Closure",
    2: "Navigation Restriction",
    3: "Towpath Closure",
    4: "Advice",
    8: "Towpath Restriction",
    9: "Navigation and Towpath Closure",
    10: "Customer Service Facility",
    11: "Navigation Restriction and Towpath Closure",
}

REASON_LOOKUP: dict[int, str] = {
    2: "3rd Party Works",
    5: "Inspections",
    6: "Maintenance",
    8: "Repair",
    9: "Suspected Vandalism",
    10: "Vegetation",
    12: "Information",
    13: "Event",
    14: "Boating Incident",
    15: "Emergency Services Incident",
    16: "Underwater Obstruction",
    17: "Vehicle Incident",
    18: "Low Water Levels",
    19: "High Water Levels",
    20: "Pollution Incident",
}


class WaterwayDefinition(TypedDict):
    """A CRT waterway definition from the public page source."""

    value: str
    name: str
    level: int


WATERWAYS: list[WaterwayDefinition] = json.loads(
    """
    [
      {"value": "AB", "name": "Albert Dock", "level": 1},
      {"value": "AI", "name": "River Aire", "level": 1},
      {"value": "AL", "name": "Aire & Calder Navigation Main Line", "level": 1},
      {"value": "AL-AD", "name": "Bank Dole Cut", "level": 2},
      {"value": "AL-AW", "name": "Wakefield Branch", "level": 2},
      {"value": "AL-CE", "name": "Clarence Dock", "level": 2},
      {"value": "AL-FH", "name": "Fairies Hill Cut", "level": 2},
      {"value": "AN", "name": "Ashton Canal", "level": 1},
      {"value": "AS", "name": "Ashby Canal", "level": 1},
      {"value": "BBN", "name": "Bow Back Rivers", "level": 1},
      {"value": "BBN-AC", "name": "Abbey Creek", "level": 2},
      {"value": "BBN-BQ", "name": "Bow Creek", "level": 2},
      {"value": "BBN-CI", "name": "City Mill River", "level": 2},
      {"value": "BBN-CV", "name": "Channelsea River", "level": 2},
      {"value": "BBN-LI", "name": "Limehouse Cut", "level": 2},
      {"value": "BBN-LI-LB", "name": "Limehouse Basin", "level": 3},
      {"value": "BBN-LO", "name": "Old River Lea", "level": 2},
      {"value": "BBN-PC", "name": "Prescott Channel", "level": 2},
      {"value": "BBN-TH", "name": "Three Mills River", "level": 2},
      {"value": "BBN-TK", "name": "St Thomas Creek", "level": 2},
      {"value": "BBN-WK", "name": "Waterworks River", "level": 2},
      {"value": "BCN", "name": "Birmingham Canal Navigations", "level": 1},
      {"value": "BCN-BC", "name": "New Mainline", "level": 2},
      {"value": "BCN-BC-BE", "name": "Netherton Tunnel Branch", "level": 3},
      {"value": "BCN-BC-BG", "name": "Gower Branch", "level": 3},
      {"value": "BCN-BC-BI", "name": "Icknield Port Loop", "level": 3},
      {"value": "BCN-BC-BN", "name": "Spon Lane Locks", "level": 3},
      {"value": "BCN-BC-BO", "name": "Oozells Street Loop", "level": 3},
      {"value": "BCN-BC-BS", "name": "Soho Loop", "level": 3},
      {"value": "BCN-BC-BX", "name": "Hockley Port Branch", "level": 3},
      {"value": "BCN-BC-CP", "name": "Cape Arm", "level": 3},
      {"value": "BCN-BC-LW", "name": "Ladywood Arm", "level": 3},
      {"value": "BCN-BF", "name": "Birmingham & Fazeley Canal", "level": 2},
      {"value": "BCN-BF-WZ", "name": "Digbeth Branch", "level": 3},
      {"value": "BCN-BK", "name": "Dudley No 2 Canal", "level": 2},
      {"value": "BCN-BK-BL", "name": "Boshboil Arm", "level": 3},
      {"value": "BCN-BK-BZ", "name": "Bumble Hole Arm", "level": 3},
      {"value": "BCN-BP", "name": "Dudley No 1 Canal", "level": 2},
      {"value": "BCN-BP-GZ", "name": "Grazebrook Arm", "level": 3},
      {"value": "BCN-BP-WR", "name": "Dudley Tunnel Branch", "level": 3},
      {"value": "BCN-RC", "name": "Rushall Canal", "level": 2},
      {"value": "BCN-ST", "name": "Stourbridge Canal", "level": 2},
      {"value": "BCN-ST-FB", "name": "Fens Branch", "level": 3},
      {
        "value": "BCN-ST-SB",
        "name": "Stourbridge Extension Canal",
        "level": 3
      },
      {"value": "BCN-ST-SG", "name": "Stourbridge Town Arm", "level": 3},
      {"value": "BCN-TC", "name": "Titford Canal", "level": 2},
      {"value": "BCN-TC-TD", "name": "Tat Bank Branch", "level": 3},
      {"value": "BCN-TC-TG", "name": "Causeway Green Branch", "level": 3},
      {"value": "BCN-TC-TL", "name": "Jim Crow Arm", "level": 3},
      {"value": "BCN-TC-TP", "name": "Portway Branch", "level": 3},
      {"value": "BCN-TC-TQ", "name": "Titford Pools", "level": 3},
      {"value": "BCN-TV", "name": "Tame Valley Canal", "level": 2},
      {"value": "BCN-WE", "name": "Wyrley & Essington Canal", "level": 2},
      {"value": "BCN-WE-BA", "name": "Anglesey Branch", "level": 3},
      {"value": "BCN-WE-DE", "name": "Daw End Canal", "level": 3},
      {
        "value": "BCN-WE-WX",
        "name": "Cannock Extension Canal",
        "level": 3
      },
      {
        "value": "BCN-WF",
        "name": "Wyrley & Essington Canal (Coventry)",
        "level": 2
      },
      {"value": "BCN-WS", "name": "Walsall Canal", "level": 2},
      {"value": "BCN-WS-BD", "name": "Bradley Branch", "level": 3},
      {"value": "BCN-WS-BJ", "name": "Ridgacre Branch", "level": 3},
      {"value": "BCN-WS-BR", "name": "Wednesbury Old Canal", "level": 3},
      {"value": "BCN-WS-GO", "name": "Gospel Oak Branch", "level": 3},
      {"value": "BCN-WS-HA", "name": "Haines Branch Canal", "level": 3},
      {"value": "BCN-WS-WA", "name": "Anson Branch", "level": 3},
      {"value": "BCN-WS-WJ", "name": "Walsall Town Arm", "level": 3},
      {"value": "BCN-WS-WL", "name": "Willenhall Branch", "level": 3},
      {
        "value": "BCN-WS-WO",
        "name": "Ocker Hill Tunnel Branch",
        "level": 3
      },
      {"value": "BCN-WV", "name": "Old Main Line", "level": 2},
      {"value": "BCN-WV-WG", "name": "Engine Arm", "level": 3},
      {"value": "BCN-WV-WW", "name": "Bradley Arm", "level": 3},
      {"value": "BCN-WV-XX", "name": "Chemical Arm", "level": 3},
      {"value": "BT", "name": "Bridgwater & Taunton Canal", "level": 1},
      {"value": "CA", "name": "Calder & Hebble Navigation", "level": 1},
      {"value": "CA-CB", "name": "Dewsbury Arm", "level": 2},
      {"value": "CA-CX", "name": "Halifax Branch", "level": 2},
      {"value": "CC", "name": "Coventry Canal", "level": 1},
      {"value": "CH", "name": "Chesterfield Canal", "level": 1},
      {"value": "CL", "name": "Caldon Canal", "level": 1},
      {"value": "CL-CK", "name": "Leek Branch", "level": 2},
      {"value": "CY", "name": "Canning Dock", "level": 1},
      {"value": "CZ", "name": "Canning Half Tide Dock", "level": 1},
      {"value": "DC", "name": "Droitwich Canals", "level": 1},
      {"value": "DC-DB", "name": "Droitwich Barge Canal", "level": 2},
      {
        "value": "DC-DJ",
        "name": "Droitwich Junction Canal",
        "level": 2
      },
      {"value": "DU", "name": "Dukes Dock", "level": 1},
      {"value": "EL", "name": "Egerton Dock", "level": 1},
      {"value": "EM", "name": "Morpeth Dock", "level": 1},
      {"value": "ER", "name": "Erewash Canal", "level": 1},
      {"value": "ER-CM", "name": "Cromford Canal", "level": 2},
      {"value": "ER-TT", "name": "Nottingham Canal", "level": 2},
      {"value": "FK", "name": "Stainforth & Keadby Canal", "level": 1},
      {"value": "FO", "name": "Fossdyke Canal", "level": 1},
      {"value": "GC", "name": "Coburg Dock", "level": 1},
      {"value": "GR", "name": "Grantham Canal", "level": 1},
      {"value": "GS", "name": "Gloucester & Sharpness Canal", "level": 1},
      {"value": "GS-OA", "name": "Sharpness", "level": 2},
      {"value": "GS-SJ", "name": "Stroudwater Canal", "level": 2},
      {"value": "GU", "name": "Grand Union Canal", "level": 1},
      {"value": "GU-GA", "name": "Aylesbury Arm", "level": 2},
      {
        "value": "GU-GB",
        "name": "Birmingham & Warwick Junction Canal",
        "level": 2
      },
      {"value": "GU-GD", "name": "Stratford Arm", "level": 2},
      {"value": "GU-GF", "name": "Saltisford Arm", "level": 2},
      {"value": "GU-GG", "name": "Slough Arm", "level": 2},
      {"value": "GU-GK", "name": "Buckingham Arm", "level": 2},
      {"value": "GU-GL", "name": "Leicester Line", "level": 2},
      {"value": "GU-GL-FI", "name": "Foxton Incline Arm", "level": 3},
      {"value": "GU-GL-GE", "name": "Welford Arm", "level": 3},
      {
        "value": "GU-GL-GH",
        "name": "Market Harborough Arm",
        "level": 3
      },
      {"value": "GU-GN", "name": "Northampton Arm", "level": 2},
      {"value": "GU-GP", "name": "Paddington Arm", "level": 2},
      {"value": "GU-GV", "name": "Wendover Arm", "level": 2},
      {"value": "GU-GX", "name": "River Chess", "level": 2},
      {"value": "HB", "name": "Huddersfield Broad Canal", "level": 1},
      {"value": "HN", "name": "Huddersfield Narrow Canal", "level": 1},
      {"value": "HU", "name": "Hertford Union Canal", "level": 1},
      {"value": "KA", "name": "Kennet & Avon Canal", "level": 1},
      {"value": "LA", "name": "Llangollen Canal", "level": 1},
      {"value": "LA-LP", "name": "Prees Branch", "level": 2},
      {"value": "LC", "name": "Lancaster Canal", "level": 1},
      {"value": "LC-LG", "name": "Glasson Branch", "level": 2},
      {"value": "LDN", "name": "London Docklands", "level": 1},
      {"value": "LDN-BB", "name": "Blackwall Basin", "level": 2},
      {"value": "LDN-BW", "name": "Docklands London Waterway", "level": 2},
      {"value": "LDN-MD", "name": "Middle Branch Dock", "level": 2},
      {"value": "LDN-MI", "name": "Millwall Inner Dock", "level": 2},
      {"value": "LDN-ND", "name": "Northern Branch Dock", "level": 2},
      {"value": "LDN-NW", "name": "Millwall Outer Dock", "level": 2},
      {"value": "LDN-PD", "name": "Poplar Dock", "level": 2},
      {"value": "LDN-SD", "name": "South Dock", "level": 2},
      {"value": "LL", "name": "Leeds & Liverpool Canal", "level": 1},
      {"value": "LL-LE", "name": "Leigh Branch", "level": 2},
      {"value": "LL-LM", "name": "Walton Summit Arm", "level": 2},
      {"value": "LL-LR", "name": "Rufford Branch", "level": 2},
      {"value": "LL-LS", "name": "Springs Branch", "level": 2},
      {"value": "LN", "name": "Lee Navigation", "level": 1},
      {"value": "LT", "name": "St Helens Canal", "level": 1},
      {"value": "MA", "name": "Macclesfield Canal", "level": 1},
      {"value": "MB", "name": "Monmouthshire & Brecon Canal", "level": 1},
      {
        "value": "MC",
        "name": "Manchester Bolton & Bury Canal",
        "level": 1
      },
      {"value": "MC-ME", "name": "Bolton Arm", "level": 2},
      {"value": "MO", "name": "Montgomery Canal", "level": 1},
      {"value": "MO-MG", "name": "Guilsfield Arm", "level": 2},
      {"value": "NJ", "name": "New Junction Canal", "level": 1},
      {"value": "OX", "name": "Oxford Canal", "level": 1},
      {"value": "OX-OB", "name": "Brownsover Arm", "level": 2},
      {"value": "OX-OD", "name": "Dukes Cut", "level": 2},
      {"value": "OX-OE", "name": "Engine Arm", "level": 2},
      {"value": "OX-OF", "name": "Clifton Arm", "level": 2},
      {"value": "OX-OH", "name": "Hythe Bridge Street Arm", "level": 2},
      {"value": "OX-OK", "name": "Brinklow Arm", "level": 2},
      {"value": "OX-OR", "name": "Rugby Arm", "level": 2},
      {"value": "OX-OS", "name": "Stretton Arm", "level": 2},
      {"value": "OX-OW", "name": "Newbold Arm", "level": 2},
      {"value": "PF", "name": "Peak Forest Canal", "level": 1},
      {"value": "PF-PB", "name": "Bugsworth Arm", "level": 2},
      {"value": "PL", "name": "Liverpool Link", "level": 1},
      {"value": "PO", "name": "Pocklington Canal", "level": 1},
      {"value": "QG", "name": "Brunswick Dock", "level": 1},
      {"value": "QN", "name": "Queen's Dock", "level": 1},
      {"value": "RD", "name": "Rochdale Canal", "level": 1},
      {"value": "RE", "name": "Regent's Canal", "level": 1},
      {"value": "RI", "name": "Ripon Canal", "level": 1},
      {"value": "RL", "name": "Ribble Link", "level": 1},
      {"value": "RO", "name": "River Ouse", "level": 1},
      {"value": "RS", "name": "River Severn Navigation", "level": 1},
      {"value": "RT", "name": "River Trent", "level": 1},
      {"value": "RU", "name": "Ure Navigation", "level": 1},
      {"value": "SA", "name": "Swansea Canal", "level": 1},
      {"value": "SE", "name": "Selby Canal", "level": 1},
      {"value": "SH", "name": "Sheffield & South Yorkshire Nav", "level": 1},
      {"value": "SH-DD", "name": "Dearne & Dove Canal", "level": 2},
      {"value": "SH-FT", "name": "Sheffield & Tinsley Canal", "level": 2},
      {"value": "SO", "name": "River Soar", "level": 1},
      {"value": "SP", "name": "Shrewsbury & Newport Canal", "level": 1},
      {"value": "SR", "name": "River Stort", "level": 1},
      {"value": "SU", "name": "Shropshire Union Canal", "level": 1},
      {"value": "SU-SM", "name": "Middlewich Branch", "level": 2},
      {"value": "SU-UD", "name": "Shropshire Union", "level": 2},
      {"value": "SUA", "name": "Stratford-Upon-Avon Canal", "level": 1},
      {"value": "SUA-SK", "name": "Kingswood Arm", "level": 2},
      {"value": "SUA-SN", "name": "North Stratford Canal", "level": 2},
      {"value": "SUA-SS", "name": "South Stratford Canal", "level": 2},
      {
        "value": "SW",
        "name": "Staffordshire & Worcestershire Canal",
        "level": 1
      },
      {"value": "SW-HT", "name": "Hatherton Canal", "level": 2},
      {"value": "SZ", "name": "Salthouse Dock", "level": 1},
      {"value": "TE", "name": "Nottingham & Beeston Canal", "level": 1},
      {"value": "TM", "name": "Trent & Mersey Canal", "level": 1},
      {"value": "TN", "name": "Tees Navigation", "level": 1},
      {"value": "TN-TB", "name": "River Leven", "level": 2},
      {
        "value": "TN-TX",
        "name": "Tees White Water Canoe Course",
        "level": 2
      },
      {"value": "UT", "name": "Upper Trent", "level": 1},
      {"value": "VT", "name": "Wapping Basin", "level": 1},
      {"value": "VZ", "name": "Wapping Dock", "level": 1},
      {"value": "WB", "name": "Worcester & Birmingham Canal.", "level": 1},
      {"value": "WB-SI", "name": "New Wharf Arm", "level": 2},
      {"value": "WI", "name": "River Witham", "level": 1},
      {"value": "WN", "name": "Weaver Navigation", "level": 1},
      {"value": "WN-WC", "name": "Weston Canal", "level": 2},
      {"value": "WN-WM", "name": "Frodsham Cut", "level": 2},
      {"value": "WN-WT", "name": "Witton Brook", "level": 2}
    ]
    """
)

WATERWAY_NAME_LOOKUP = {item["value"]: item["name"] for item in WATERWAYS}
LEVEL_ONE_WATERWAYS = [item for item in WATERWAYS if item["level"] == 1]


def build_entry_title(
    mode: str,
    radius_miles: int | float | None = None,
    selected_waterways: Sequence[str] | None = None,
) -> str:
    """Build a friendly config entry title from the active mode."""
    if mode == MODE_GPS:
        radius = int(radius_miles or DEFAULT_RADIUS_MILES)
        return f"Canal and River Trust Notices (GPS - {radius}mi)"

    selected_names = resolve_selected_waterway_names(selected_waterways or [])
    if not selected_names:
        return "Canal and River Trust Notices (Manual)"
    if len(selected_names) == 1:
        return f"Canal and River Trust Notices ({selected_names[0]})"
    return f"Canal and River Trust Notices ({selected_names[0]} +{len(selected_names) - 1})"


def gps_identifier(entity_id: str | None) -> str:
    """Normalize the GPS unique identifier."""
    if not entity_id:
        return GPS_HOME_IDENTIFIER
    return entity_id.replace(".", "_")


def slug_identifier_from_waterways(selected_waterways: Sequence[str]) -> str:
    """Build the manual-mode unique id suffix from the first selection."""
    selected_names = resolve_selected_waterway_names(selected_waterways)
    if not selected_names:
        return "manual"

    slug = re.sub(r"[^a-z0-9]+", "_", selected_names[0].lower()).strip("_")
    return slug or "manual"


def resolve_selected_waterway_names(selected_waterways: Sequence[str]) -> list[str]:
    """Resolve selected CRT waterway codes to display names."""
    return [
        WATERWAY_NAME_LOOKUP[code]
        for code in selected_waterways
        if code in WATERWAY_NAME_LOOKUP
    ]


def matches_selected_waterways(
    notice_waterways: str | None,
    selected_names: Sequence[str],
) -> bool:
    """Return True when any selected waterway name appears in the notice text."""
    if not notice_waterways:
        return False

    haystack = notice_waterways.casefold()
    return any(name.casefold() in haystack for name in selected_names)


def extract_geometry_points(
    geometry: Mapping[str, Any] | None,
) -> list[tuple[float, float]]:
    """Extract latitude/longitude pairs from a CRT GeometryCollection."""
    if not geometry or geometry.get("type") != "GeometryCollection":
        return []

    points: list[tuple[float, float]] = []
    for item in geometry.get("geometries", []):
        if not isinstance(item, Mapping) or item.get("type") != "Point":
            continue
        coordinates = item.get("coordinates")
        if (
            not isinstance(coordinates, Sequence)
            or len(coordinates) < 2
            or not isinstance(coordinates[0], (int, float))
            or not isinstance(coordinates[1], (int, float))
        ):
            continue

        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        points.append((latitude, longitude))

    return points


def haversine_miles(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the Haversine distance between two points in miles."""
    earth_radius_miles = 3958.7613

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_miles * c


def build_notice_url(path: str | None) -> str:
    """Build a full CRT notice URL from a relative path."""
    if not path:
        return CRT_BROWSE_URL
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{CRT_NOTICE_BASE_URL}{path}"


def format_notice_brief(
    title: str,
    waterway: str | None = None,
    type_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Format a notice into a short readable summary for HA attributes."""
    parts = [title]
    if waterway:
        parts.append(waterway)
    if type_name:
        parts.append(type_name)
    if start_date or end_date:
        parts.append(f"{start_date or '?'} to {end_date or 'Ongoing'}")
    return " | ".join(parts)
