"""CRT Notices integration for Home Assistant.

Known limitations:
1. Distance calculation uses the nearest Point in the GeometryCollection. A
   notice may have multiple points representing the extent of the affected
   area; the reported distance is to the closest one.
2. Some notices have no geometry data. These are included in results but
   cannot be distance-filtered or sorted.
3. CRT waterway names in the API may include branch or section suffixes in
   parentheses. Manual mode uses substring matching to handle this.
4. The API is unauthenticated and rate limits are undocumented. The default
   1-hour interval is conservative by design.
5. The state field from the API is used to filter active notices. Only
   "Published" notices are treated as active. "Completed" and "Cancelled"
   notices are excluded.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    API_FIELDS,
    CONF_DEVICE_TRACKER_ENTITY_ID,
    CONF_LOOKAHEAD_DAYS,
    CONF_MODE,
    CONF_RADIUS_MILES,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WATERWAYS,
    CRT_API_URL,
    CRT_BROWSE_URL,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_RADIUS_MILES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_NAME,
    MODE_GPS,
    MODE_MANUAL,
    NAVIGATION_BLOCKING_TYPE_IDS,
    NOTICE_TYPE_LOOKUP,
    REASON_LOOKUP,
    build_notice_url,
    extract_geometry_points,
    haversine_miles,
    matches_selected_waterways,
    resolve_selected_waterway_names,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


@dataclass(slots=True)
class CRTNotice:
    """Parsed CRT notice model used by the entities."""

    notice_id: str
    title: str
    waterway: str
    type_id: int | None
    reason_id: int | None
    programme_id: int | None
    start: str | None
    end: str | None
    state: str
    path: str | None
    image: str | None
    region: str | None
    points: tuple[tuple[float, float], ...]
    distance_miles: float | None = None

    @property
    def type_name(self) -> str | None:
        """Return the human-readable notice type."""
        if self.type_id is None:
            return None
        return NOTICE_TYPE_LOOKUP.get(self.type_id, str(self.type_id))

    @property
    def reason_name(self) -> str | None:
        """Return the human-readable notice reason."""
        if self.reason_id is None:
            return None
        return REASON_LOOKUP.get(self.reason_id, str(self.reason_id))

    @property
    def url(self) -> str:
        """Return the full public notice URL."""
        return build_notice_url(self.path)

    @property
    def first_latitude(self) -> float | None:
        """Return the first geometry latitude when available."""
        return self.points[0][0] if self.points else None

    @property
    def first_longitude(self) -> float | None:
        """Return the first geometry longitude when available."""
        return self.points[0][1] if self.points else None

    def summary_attributes(self) -> dict[str, Any]:
        """Return a compact summary for the count sensor."""
        return {
            "title": self.title,
            "waterway": self.waterway,
            "type_name": self.type_name,
            "distance_miles": self.distance_miles,
            "url": self.url,
        }

    def closure_attributes(self, include_distance: bool) -> dict[str, Any]:
        """Return the binary sensor's active closure payload."""
        return {
            "title": self.title,
            "waterway": self.waterway,
            "type_name": self.type_name,
            "reason_name": self.reason_name,
            "start_date": self.start,
            "end_date": self.end,
            "distance_miles": self.distance_miles if include_distance else None,
            "url": self.url,
        }

    def nearest_attributes(self, include_distance: bool) -> dict[str, Any]:
        """Return the nearest sensor attribute payload."""
        return {
            "title": self.title,
            "waterway": self.waterway,
            "type_name": self.type_name,
            "reason_name": self.reason_name,
            "distance_miles": self.distance_miles if include_distance else None,
            "start_date": self.start,
            "end_date": self.end,
            "latitude": self.first_latitude,
            "longitude": self.first_longitude,
            "url": self.url,
            "notice_state": self.state,
        }


@dataclass(slots=True)
class CRTCoordinatorData:
    """Coordinator payload shared across all entities."""

    notices: list[CRTNotice]
    mode: str
    tracker_latitude: float | None
    tracker_longitude: float | None
    using_home_fallback: bool

    @property
    def nearest_notice(self) -> CRTNotice | None:
        """Return the first matched notice, if any."""
        return self.notices[0] if self.notices else None

    @property
    def blocking_notices(self) -> list[CRTNotice]:
        """Return notices that block or restrict navigation."""
        return [
            notice
            for notice in self.notices
            if notice.type_id in NAVIGATION_BLOCKING_TYPE_IDS
        ]

    def notice_by_id(self, notice_id: str) -> CRTNotice | None:
        """Return one matched notice by ID."""
        return next((notice for notice in self.notices if notice.notice_id == notice_id), None)


@dataclass(slots=True)
class CRTNoticesRuntimeData:
    """Runtime state stored for a config entry."""

    coordinator: "CRTNoticesCoordinator"


class CRTNoticesCoordinator(DataUpdateCoordinator[CRTCoordinatorData]):
    """Fetch and filter CRT notices for one config entry."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self._hass = hass
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(
                minutes=int(
                    self._config_value(
                        CONF_UPDATE_INTERVAL_MINUTES,
                        DEFAULT_UPDATE_INTERVAL_MINUTES,
                    )
                )
            ),
        )

    def _config_value(self, key: str, default: Any = None) -> Any:
        """Return the active config value, preferring options over entry data."""
        return self.config_entry.options.get(key, self.config_entry.data.get(key, default))

    async def _async_update_data(self) -> CRTCoordinatorData:
        """Fetch, validate, and filter CRT notice data."""
        params = self._build_request_params()
        _LOGGER.debug("Fetching CRT notices with params: %s", params)

        try:
            async with asyncio.timeout(30):
                response = await self._session.get(CRT_API_URL, params=params)
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("CRT notice fetch failed: %s", err)
            raise UpdateFailed(f"Error communicating with CRT API: {err}") from err
        except ValueError as err:
            _LOGGER.error("CRT notice response was not valid JSON: %s", err)
            raise UpdateFailed("CRT API returned invalid JSON") from err

        if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
            raise UpdateFailed("CRT API returned an invalid GeoJSON payload")

        notices = [
            notice
            for feature in payload["features"]
            if (notice := self._parse_feature(feature)) is not None
        ]
        _LOGGER.debug("Parsed %s published CRT notices", len(notices))

        mode = self._config_value(CONF_MODE, MODE_GPS)
        if mode == MODE_MANUAL:
            filtered_notices = self._filter_manual_notices(notices)
            return CRTCoordinatorData(
                notices=filtered_notices,
                mode=MODE_MANUAL,
                tracker_latitude=None,
                tracker_longitude=None,
                using_home_fallback=False,
            )

        tracker_latitude, tracker_longitude, using_home_fallback = (
            self._resolve_reference_coordinates()
        )
        filtered_notices = self._filter_gps_notices(
            notices,
            tracker_latitude,
            tracker_longitude,
        )
        return CRTCoordinatorData(
            notices=filtered_notices,
            mode=MODE_GPS,
            tracker_latitude=tracker_latitude,
            tracker_longitude=tracker_longitude,
            using_home_fallback=using_home_fallback,
        )

    def _build_request_params(self) -> dict[str, str]:
        """Build the CRT API query parameters for the current entry."""
        start_date = dt_util.now().date()
        lookahead_days = int(self._config_value(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS))
        end_date = start_date + timedelta(days=lookahead_days)

        return {
            "consult": "false",
            "geometry": "point",
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "fields": API_FIELDS,
        }

    def _parse_feature(self, feature: dict[str, Any]) -> CRTNotice | None:
        """Parse one GeoJSON feature into a notice model."""
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            return None

        state = str(properties.get("state") or "")
        if state != "Published":
            return None

        points = tuple(extract_geometry_points(feature.get("geometry")))
        return CRTNotice(
            notice_id=str(properties.get("id") or properties.get("path") or properties.get("title") or "unknown"),
            title=str(properties.get("title") or "Untitled notice"),
            waterway=str(properties.get("waterways") or ""),
            type_id=_safe_int(properties.get("typeId")),
            reason_id=_safe_int(properties.get("reasonId")),
            programme_id=_safe_int(properties.get("programmeId")),
            start=_safe_optional_str(properties.get("start")),
            end=_safe_optional_str(properties.get("end")),
            state=state,
            path=_safe_optional_str(properties.get("path")),
            image=_safe_optional_str(properties.get("image")),
            region=_safe_optional_str(properties.get("region")),
            points=points,
        )

    def _filter_manual_notices(self, notices: list[CRTNotice]) -> list[CRTNotice]:
        """Filter published notices by selected waterways."""
        selected_codes = self._config_value(CONF_WATERWAYS, [])
        selected_names = resolve_selected_waterway_names(selected_codes)
        filtered = [
            notice
            for notice in notices
            if matches_selected_waterways(notice.waterway, selected_names)
        ]
        filtered.sort(key=lambda item: (item.start or "", item.title.casefold()))
        _LOGGER.debug(
            "Manual mode matched %s notices across %s waterways",
            len(filtered),
            len(selected_names),
        )
        return filtered

    def _filter_gps_notices(
        self,
        notices: list[CRTNotice],
        tracker_latitude: float,
        tracker_longitude: float,
    ) -> list[CRTNotice]:
        """Filter published notices by radius, preserving no-geometry notices."""
        radius_miles = int(self._config_value(CONF_RADIUS_MILES, DEFAULT_RADIUS_MILES))
        in_range: list[CRTNotice] = []
        without_geometry: list[CRTNotice] = []

        for notice in notices:
            if not notice.points:
                without_geometry.append(notice)
                continue

            nearest_distance = min(
                haversine_miles(
                    tracker_latitude,
                    tracker_longitude,
                    point_latitude,
                    point_longitude,
                )
                for point_latitude, point_longitude in notice.points
            )
            if nearest_distance <= radius_miles:
                notice.distance_miles = round(nearest_distance, 2)
                in_range.append(notice)

        in_range.sort(
            key=lambda item: (item.distance_miles or 0.0, item.start or "", item.title.casefold())
        )
        without_geometry.sort(key=lambda item: (item.start or "", item.title.casefold()))
        _LOGGER.debug(
            "GPS mode matched %s notices within %s miles and %s notices without geometry",
            len(in_range),
            radius_miles,
            len(without_geometry),
        )
        return [*in_range, *without_geometry]

    def _resolve_reference_coordinates(self) -> tuple[float, float, bool]:
        """Resolve GPS coordinates from the tracker, falling back to the HA home zone."""
        tracker_entity_id = self._config_value(CONF_DEVICE_TRACKER_ENTITY_ID)
        if tracker_entity_id:
            tracker_state = self.hass.states.get(tracker_entity_id)
            if tracker_state is not None:
                latitude = tracker_state.attributes.get(ATTR_LATITUDE)
                longitude = tracker_state.attributes.get(ATTR_LONGITUDE)
                if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
                    return float(latitude), float(longitude), False

                _LOGGER.warning(
                    "Device tracker %s had no usable coordinates; falling back to Home Assistant home coordinates",
                    tracker_entity_id,
                )
            else:
                _LOGGER.warning(
                    "Device tracker %s was unavailable; falling back to Home Assistant home coordinates",
                    tracker_entity_id,
                )

        if self.hass.config.latitude is not None and self.hass.config.longitude is not None:
            return float(self.hass.config.latitude), float(self.hass.config.longitude), True

        raise UpdateFailed("No usable coordinates were available for CRT GPS filtering")


class CRTNoticesEntity(CoordinatorEntity[CRTNoticesCoordinator], Entity):
    """Base entity for CRT notice entities."""

    _attr_attribution = "Data provided by Canal & River Trust"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: CRTNoticesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the base CRT entity."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared integration device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Canal & River Trust",
            model=INTEGRATION_NAME,
            configuration_url=CRT_BROWSE_URL,
        )

    async def async_update(self) -> None:
        """Support homeassistant.update_entity refreshes."""
        await self.coordinator.async_request_refresh()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CRT notices from a config entry."""
    coordinator = CRTNoticesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = CRTNoticesRuntimeData(
        coordinator=coordinator
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a CRT notices config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Future-proof config entry migrations."""
    _LOGGER.debug("No migration required for config entry version %s", entry.version)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def get_runtime_data(hass: HomeAssistant, entry: ConfigEntry) -> CRTNoticesRuntimeData:
    """Return runtime data for a CRT notices config entry."""
    return hass.data[DOMAIN][entry.entry_id]


def _safe_int(value: Any) -> int | None:
    """Safely coerce an optional integer-like value."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_optional_str(value: Any) -> str | None:
    """Safely coerce a value to an optional string."""
    if value is None:
        return None
    return str(value)
