"""Sensor platform for CRT Notices."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CRTNotice, CRTNoticesEntity, get_runtime_data
from .const import DOMAIN, MODE_GPS, format_notice_brief


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CRT notice sensors."""
    runtime_data = get_runtime_data(hass, entry)
    coordinator = runtime_data.coordinator
    entity_registry = er.async_get(hass)
    seen_notice_ids: set[str] = set()
    current_notice_ids = {notice.notice_id for notice in coordinator.data.notices}

    entities: list[SensorEntity] = [
        CRTNearestStoppageSensor(coordinator, entry),
        CRTNoticeCountSensor(coordinator, entry),
        CRTLastUpdatedSensor(coordinator, entry),
    ]

    for notice in coordinator.data.notices:
        if notice.notice_id in seen_notice_ids:
            continue
        seen_notice_ids.add(notice.notice_id)
        entities.append(CRTActiveNoticeSensor(coordinator, entry, notice.notice_id))

    _remove_stale_notice_registry_entries(
        entity_registry=entity_registry,
        entry=entry,
        active_notice_ids=current_notice_ids,
    )
    async_add_entities(entities)

    @callback
    def _async_sync_notice_entities() -> None:
        active_notice_ids = {notice.notice_id for notice in coordinator.data.notices}
        stale_notice_ids = seen_notice_ids - active_notice_ids
        if stale_notice_ids:
            _remove_notice_entities(
                entity_registry=entity_registry,
                entry=entry,
                notice_ids=stale_notice_ids,
            )
            seen_notice_ids.difference_update(stale_notice_ids)

        new_entities: list[SensorEntity] = []
        for notice in coordinator.data.notices:
            if notice.notice_id in seen_notice_ids:
                continue
            seen_notice_ids.add(notice.notice_id)
            new_entities.append(CRTActiveNoticeSensor(coordinator, entry, notice.notice_id))

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_notice_entities))


class CRTNearestStoppageSensor(CRTNoticesEntity, SensorEntity):
    """Show the nearest or first matched CRT notice."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "nearest_stoppage"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the nearest stoppage sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_nearest_stoppage"

    @property
    def native_value(self) -> str:
        """Return the nearest notice title."""
        notice = self.coordinator.data.nearest_notice
        if notice is None:
            return "No active notices"
        return notice.title[:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return nearest notice details."""
        notice = self.coordinator.data.nearest_notice
        if notice is None:
            return {
                "matched_notice_count": 0,
                "title": None,
                "waterway": None,
                "type_name": None,
                "reason_name": None,
                "distance_miles": None,
                "start_date": None,
                "end_date": None,
                "latitude": None,
                "longitude": None,
                "url": None,
                "notice_state": None,
                "notice_titles": [],
            }

        attributes = notice.nearest_attributes(
            include_distance=self.coordinator.data.mode == MODE_GPS
        )
        attributes["matched_notice_count"] = len(self.coordinator.data.notices)
        attributes.update(_all_notice_attributes(self.coordinator.data.notices))
        return attributes


class CRTNoticeCountSensor(CRTNoticesEntity, SensorEntity):
    """Show the number of matched published notices."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "notice_count"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the count sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_notice_count"

    @property
    def native_value(self) -> int:
        """Return the number of matched notices."""
        return len(self.coordinator.data.notices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a summary list for matched notices."""
        return _all_notice_attributes(self.coordinator.data.notices)


class CRTLastUpdatedSensor(CRTNoticesEntity, SensorEntity):
    """Show the last successful coordinator refresh time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_updated"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the last updated sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_updated"

    @property
    def native_value(self) -> datetime | None:
        """Return the last successful refresh timestamp."""
        return self.coordinator.data.last_updated


class CRTActiveNoticeSensor(CRTNoticesEntity, SensorEntity):
    """Expose each matched CRT notice as its own sensor entity."""

    def __init__(self, coordinator, entry: ConfigEntry, notice_id: str) -> None:
        """Initialize an individual notice sensor."""
        super().__init__(coordinator, entry)
        self._notice_id = notice_id
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_notice_{notice_id}"

    @property
    def available(self) -> bool:
        """Return whether this notice is still part of the current result set."""
        return super().available and self._notice is not None

    @property
    def name(self) -> str | None:
        """Return the current notice title as the entity name."""
        notice = self._notice
        if notice is None:
            return self._notice_id
        return notice.title[:255]

    @property
    def native_value(self) -> str | None:
        """Return a compact state for the notice."""
        notice = self._notice
        if notice is None:
            return None
        return notice.type_name or notice.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full notice details."""
        notice = self._notice
        if notice is None:
            return {}

        include_distance = self.coordinator.data.mode == MODE_GPS
        return {
            "notice_id": notice.notice_id,
            "title": notice.title,
            "waterway": notice.waterway,
            "type_name": notice.type_name,
            "reason_name": notice.reason_name,
            "distance_miles": notice.distance_miles if include_distance else None,
            "start_date": notice.start,
            "end_date": notice.end,
            "latitude": notice.first_latitude,
            "longitude": notice.first_longitude,
            "url": notice.url,
            "notice_state": notice.state,
            "region": notice.region,
            "image": notice.image,
        }

    @property
    def _notice(self) -> CRTNotice | None:
        """Return the backing notice model for this entity."""
        return self.coordinator.data.notice_by_id(self._notice_id)


def _all_notice_attributes(notices: list[Any]) -> dict[str, Any]:
    """Return HA-friendly attributes for all matched notices."""
    attributes: dict[str, Any] = {
        "notice_titles": [notice.title for notice in notices],
        "notices": [notice.summary_attributes() for notice in notices],
    }

    for index, notice in enumerate(notices, start=1):
        attributes[f"notice_{index:02d}"] = format_notice_brief(
            title=notice.title,
            waterway=notice.waterway,
            type_name=notice.type_name,
            start_date=notice.start,
            end_date=notice.end,
        )

    return attributes


def _remove_stale_notice_registry_entries(
    entity_registry: er.EntityRegistry,
    entry: ConfigEntry,
    active_notice_ids: set[str],
) -> None:
    """Remove old dynamic notice entities that are no longer active."""
    active_unique_ids = {
        f"{DOMAIN}_{entry.entry_id}_notice_{notice_id}" for notice_id in active_notice_ids
    }
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        unique_id = entity_entry.unique_id or ""
        if not unique_id.startswith(f"{DOMAIN}_{entry.entry_id}_notice_"):
            continue
        if unique_id in active_unique_ids:
            continue
        entity_registry.async_remove(entity_entry.entity_id)


def _remove_notice_entities(
    entity_registry: er.EntityRegistry,
    entry: ConfigEntry,
    notice_ids: set[str],
) -> None:
    """Remove specific dynamic notice entities by notice ID."""
    for notice_id in notice_ids:
        unique_id = f"{DOMAIN}_{entry.entry_id}_notice_{notice_id}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is not None:
            entity_registry.async_remove(entity_id)
