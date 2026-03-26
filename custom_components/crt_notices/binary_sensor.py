"""Binary sensor platform for CRT Notices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CRTNoticesEntity, get_runtime_data
from .const import DOMAIN, MODE_GPS, format_notice_brief


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CRT notice binary sensors."""
    runtime_data = get_runtime_data(hass, entry)
    async_add_entities([CRTBlockedBinarySensor(runtime_data.coordinator, entry)])


class CRTBlockedBinarySensor(CRTNoticesEntity, BinarySensorEntity):
    """Show whether a blocking or restrictive navigation notice is active."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "blocked"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the blocking binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_blocked"

    @property
    def is_on(self) -> bool:
        """Return whether any matching notice blocks or restricts navigation."""
        return bool(self.coordinator.data.blocking_notices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return active closure details."""
        include_distance = self.coordinator.data.mode == MODE_GPS
        blocking_notices = self.coordinator.data.blocking_notices
        attributes: dict[str, Any] = {
            "active_closures": [
                notice.closure_attributes(include_distance=include_distance)
                for notice in blocking_notices
            ],
            "closure_titles": [notice.title for notice in blocking_notices],
        }

        for index, notice in enumerate(blocking_notices, start=1):
            attributes[f"closure_{index:02d}"] = format_notice_brief(
                title=notice.title,
                waterway=notice.waterway,
                type_name=notice.type_name,
                start_date=notice.start,
                end_date=notice.end,
            )

        return attributes
