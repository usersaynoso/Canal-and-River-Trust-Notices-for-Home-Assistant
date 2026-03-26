"""Config flow for CRT Notices."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError

from .const import (
    API_FIELDS,
    CONF_DEVICE_TRACKER_ENTITY_ID,
    CONF_LOOKAHEAD_DAYS,
    CONF_MODE,
    CONF_RADIUS_MILES,
    CONF_SHOW_ALL_WATERWAYS,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WATERWAYS,
    CRT_API_URL,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_RADIUS_MILES,
    DEFAULT_SHOW_ALL_WATERWAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    LEVEL_ONE_WATERWAYS,
    MAX_LOOKAHEAD_DAYS,
    MAX_RADIUS_MILES,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_LOOKAHEAD_DAYS,
    MIN_RADIUS_MILES,
    MIN_UPDATE_INTERVAL_MINUTES,
    MODE_GPS,
    MODE_MANUAL,
    WATERWAYS,
    build_entry_title,
    gps_identifier,
    slug_identifier_from_waterways,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate CRT connectivity issues."""


class CRTNoticesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CRT Notices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._selected_mode = MODE_GPS
        self._show_all_waterways = DEFAULT_SHOW_ALL_WATERWAYS

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Select the integration mode."""
        if user_input is not None:
            self._selected_mode = user_input[CONF_MODE]
            if self._selected_mode == MODE_GPS:
                return await self.async_step_gps()
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODE, default=self._selected_mode): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            options=[
                                {
                                    "value": MODE_GPS,
                                    "label": "GPS Proximity (Dynamic) or Home Assistant home coordinates",
                                },
                                {
                                    "value": MODE_MANUAL,
                                    "label": "Manual Canal Selection (Static)",
                                },
                            ],
                        )
                    )
                }
            ),
        )

    async def async_step_gps(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Configure GPS mode."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_MODE: MODE_GPS,
                CONF_DEVICE_TRACKER_ENTITY_ID: user_input.get(CONF_DEVICE_TRACKER_ENTITY_ID),
                CONF_RADIUS_MILES: int(user_input[CONF_RADIUS_MILES]),
                CONF_LOOKAHEAD_DAYS: DEFAULT_LOOKAHEAD_DAYS,
                CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            }

            try:
                await _async_validate_crt_api(self.hass, DEFAULT_LOOKAHEAD_DAYS)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                unique_id = f"crt_{MODE_GPS}_{gps_identifier(data[CONF_DEVICE_TRACKER_ENTITY_ID])}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=build_entry_title(
                        MODE_GPS,
                        radius_miles=data[CONF_RADIUS_MILES],
                    ),
                    data=data,
                )

        return self.async_show_form(
            step_id="gps",
            data_schema=_build_gps_schema(
                tracker_entity_id=user_input.get(CONF_DEVICE_TRACKER_ENTITY_ID)
                if user_input
                else None,
                radius_miles=user_input.get(CONF_RADIUS_MILES, DEFAULT_RADIUS_MILES)
                if user_input
                else DEFAULT_RADIUS_MILES,
            ),
            errors=errors,
        )

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Configure manual waterway mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            show_all_waterways = bool(user_input.get(CONF_SHOW_ALL_WATERWAYS, False))
            selected_waterways = list(user_input.get(CONF_WATERWAYS, []))

            if show_all_waterways != self._show_all_waterways and not selected_waterways:
                self._show_all_waterways = show_all_waterways
                return await self.async_step_manual()

            if not selected_waterways:
                errors["base"] = "no_waterways"
            else:
                data = {
                    CONF_MODE: MODE_MANUAL,
                    CONF_WATERWAYS: selected_waterways,
                    CONF_SHOW_ALL_WATERWAYS: show_all_waterways,
                    CONF_LOOKAHEAD_DAYS: DEFAULT_LOOKAHEAD_DAYS,
                    CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
                }

                try:
                    await _async_validate_crt_api(self.hass, DEFAULT_LOOKAHEAD_DAYS)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                else:
                    unique_id = f"crt_{MODE_MANUAL}_{slug_identifier_from_waterways(selected_waterways)}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=build_entry_title(
                            MODE_MANUAL,
                            selected_waterways=selected_waterways,
                        ),
                        data=data,
                    )

        options = WATERWAYS if self._show_all_waterways else LEVEL_ONE_WATERWAYS

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SHOW_ALL_WATERWAYS,
                        default=user_input.get(
                            CONF_SHOW_ALL_WATERWAYS,
                            self._show_all_waterways,
                        )
                        if user_input
                        else self._show_all_waterways,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_WATERWAYS,
                        default=user_input.get(CONF_WATERWAYS, []) if user_input else [],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            multiple=True,
                            options=[
                                {
                                    "value": item["value"],
                                    "label": item["name"],
                                }
                                for item in options
                            ],
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return CRTNoticesOptionsFlow(config_entry)


class CRTNoticesOptionsFlow(OptionsFlow):
    """Handle CRT notice options updates."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry
        self._show_all_waterways = self._value(
            CONF_SHOW_ALL_WATERWAYS,
            DEFAULT_SHOW_ALL_WATERWAYS,
        )

    def _value(self, key: str, default: Any = None) -> Any:
        """Return the current value for an option-aware key."""
        return self._config_entry.options.get(
            key,
            self._config_entry.data.get(key, default),
        )

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Edit entry options."""
        mode = self._value(CONF_MODE, MODE_GPS)
        errors: dict[str, str] = {}

        if user_input is not None:
            if mode == MODE_MANUAL:
                show_all_waterways = bool(user_input.get(CONF_SHOW_ALL_WATERWAYS, False))
                selected_waterways = list(user_input.get(CONF_WATERWAYS, []))
                if show_all_waterways != self._show_all_waterways and not selected_waterways:
                    self._show_all_waterways = show_all_waterways
                    return await self.async_step_init()
                if not selected_waterways:
                    errors["base"] = "no_waterways"
                else:
                    title = build_entry_title(
                        MODE_MANUAL,
                        selected_waterways=selected_waterways,
                    )
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        title=title,
                    )
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_WATERWAYS: selected_waterways,
                            CONF_SHOW_ALL_WATERWAYS: show_all_waterways,
                            CONF_LOOKAHEAD_DAYS: int(user_input[CONF_LOOKAHEAD_DAYS]),
                            CONF_UPDATE_INTERVAL_MINUTES: int(
                                user_input[CONF_UPDATE_INTERVAL_MINUTES]
                            ),
                        },
                    )
            else:
                title = build_entry_title(
                    MODE_GPS,
                    radius_miles=int(user_input[CONF_RADIUS_MILES]),
                )
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    title=title,
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_DEVICE_TRACKER_ENTITY_ID: user_input.get(
                            CONF_DEVICE_TRACKER_ENTITY_ID
                        ),
                        CONF_RADIUS_MILES: int(user_input[CONF_RADIUS_MILES]),
                        CONF_LOOKAHEAD_DAYS: int(user_input[CONF_LOOKAHEAD_DAYS]),
                        CONF_UPDATE_INTERVAL_MINUTES: int(
                            user_input[CONF_UPDATE_INTERVAL_MINUTES]
                        ),
                    },
                )

        if mode == MODE_MANUAL:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_SHOW_ALL_WATERWAYS,
                            default=user_input.get(
                                CONF_SHOW_ALL_WATERWAYS,
                                self._show_all_waterways,
                            )
                            if user_input
                            else self._show_all_waterways,
                        ): BooleanSelector(),
                        vol.Required(
                            CONF_WATERWAYS,
                            default=user_input.get(
                                CONF_WATERWAYS,
                                self._value(CONF_WATERWAYS, []),
                            )
                            if user_input
                            else self._value(CONF_WATERWAYS, []),
                        ): SelectSelector(
                            SelectSelectorConfig(
                                mode=SelectSelectorMode.LIST,
                                multiple=True,
                                options=[
                                    {
                                        "value": item["value"],
                                        "label": item["name"],
                                    }
                                    for item in (
                                        WATERWAYS
                                        if self._show_all_waterways
                                        else LEVEL_ONE_WATERWAYS
                                    )
                                ],
                            )
                        ),
                        vol.Required(
                            CONF_LOOKAHEAD_DAYS,
                            default=user_input.get(
                                CONF_LOOKAHEAD_DAYS,
                                self._value(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
                            )
                            if user_input
                            else self._value(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_LOOKAHEAD_DAYS,
                                max=MAX_LOOKAHEAD_DAYS,
                                step=1,
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_UPDATE_INTERVAL_MINUTES,
                            default=user_input.get(
                                CONF_UPDATE_INTERVAL_MINUTES,
                                self._value(
                                    CONF_UPDATE_INTERVAL_MINUTES,
                                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                                ),
                            )
                            if user_input
                            else self._value(
                                CONF_UPDATE_INTERVAL_MINUTES,
                                DEFAULT_UPDATE_INTERVAL_MINUTES,
                            ),
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_UPDATE_INTERVAL_MINUTES,
                                max=MAX_UPDATE_INTERVAL_MINUTES,
                                step=1,
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
                errors=errors,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_gps_options_schema(
                tracker_entity_id=user_input.get(
                    CONF_DEVICE_TRACKER_ENTITY_ID,
                    self._value(CONF_DEVICE_TRACKER_ENTITY_ID),
                )
                if user_input
                else self._value(CONF_DEVICE_TRACKER_ENTITY_ID),
                radius_miles=user_input.get(
                    CONF_RADIUS_MILES,
                    self._value(CONF_RADIUS_MILES, DEFAULT_RADIUS_MILES),
                )
                if user_input
                else self._value(CONF_RADIUS_MILES, DEFAULT_RADIUS_MILES),
                lookahead_days=user_input.get(
                    CONF_LOOKAHEAD_DAYS,
                    self._value(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
                )
                if user_input
                else self._value(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
                update_interval_minutes=user_input.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    self._value(
                        CONF_UPDATE_INTERVAL_MINUTES,
                        DEFAULT_UPDATE_INTERVAL_MINUTES,
                    ),
                )
                if user_input
                else self._value(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            ),
            errors=errors,
        )


def _build_entity_selector_key(
    tracker_entity_id: str | None,
) -> vol.Marker:
    """Build an optional tracker selector key without defaulting to None."""
    if tracker_entity_id:
        return vol.Optional(
            CONF_DEVICE_TRACKER_ENTITY_ID,
            default=tracker_entity_id,
        )
    return vol.Optional(CONF_DEVICE_TRACKER_ENTITY_ID)


def _build_gps_schema(
    tracker_entity_id: str | None,
    radius_miles: int,
) -> vol.Schema:
    """Build the GPS setup schema."""
    return vol.Schema(
        {
            _build_entity_selector_key(tracker_entity_id): EntitySelector(
                EntitySelectorConfig(
                    domain="device_tracker",
                    multiple=False,
                )
            ),
            vol.Required(
                CONF_RADIUS_MILES,
                default=radius_miles,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_RADIUS_MILES,
                    max=MAX_RADIUS_MILES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _build_gps_options_schema(
    tracker_entity_id: str | None,
    radius_miles: int,
    lookahead_days: int,
    update_interval_minutes: int,
) -> vol.Schema:
    """Build the GPS options schema."""
    return vol.Schema(
        {
            _build_entity_selector_key(tracker_entity_id): EntitySelector(
                EntitySelectorConfig(
                    domain="device_tracker",
                    multiple=False,
                )
            ),
            vol.Required(
                CONF_RADIUS_MILES,
                default=radius_miles,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_RADIUS_MILES,
                    max=MAX_RADIUS_MILES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_LOOKAHEAD_DAYS,
                default=lookahead_days,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_LOOKAHEAD_DAYS,
                    max=MAX_LOOKAHEAD_DAYS,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=update_interval_minutes,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL_MINUTES,
                    max=MAX_UPDATE_INTERVAL_MINUTES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


async def _async_validate_crt_api(hass, lookahead_days: int) -> None:
    """Validate CRT API connectivity before saving the config entry."""
    session = async_get_clientsession(hass)
    start_date = dt_util.now().date()
    end_date = start_date + timedelta(days=lookahead_days)

    try:
        async with asyncio.timeout(30):
            response = await session.get(
                CRT_API_URL,
                params={
                    "consult": "false",
                    "geometry": "point",
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "fields": API_FIELDS,
                },
            )
            response.raise_for_status()
            payload = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
        _LOGGER.warning("CRT API connectivity check failed: %s", err)
        raise CannotConnect from err

    if not isinstance(payload, dict) or "features" not in payload:
        raise CannotConnect
