"""Services for the PlayStation Family integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from psnfamily import FamilyMember, PsnFamilyError, format_pt

from .const import (
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_WINDOW_END,
    ATTR_WINDOW_START,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
    LOGGER,
    SERVICE_SET_WEEKLY_SCHEDULE,
    WEEKDAYS,
)
from .coordinator import PlaystationFamilyCoordinator

_MINUTES = vol.All(vol.Coerce(int), vol.Range(min=0, max=1440))

# Each weekday field is optional; omitted or 0 == no limit for that day.
SET_WEEKLY_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_DEVICE_ID, "target"): cv.string,
        vol.Exclusive(ATTR_ENTITY_ID, "target"): cv.entity_id,
        **{vol.Optional(day): _MINUTES for day in WEEKDAYS},
        vol.Optional(ATTR_WINDOW_START, default=DEFAULT_WINDOW_START): _MINUTES,
        vol.Optional(ATTR_WINDOW_END, default=DEFAULT_WINDOW_END): _MINUTES,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the PlayStation Family services (once per HA start)."""

    async def _handle_set_weekly_schedule(call: ServiceCall) -> None:
        """Build a 7-day schedule and push it to PSN for the target child."""
        coordinator, member = _resolve_target(hass, call)

        window_start = call.data[ATTR_WINDOW_START]
        window_end = call.data[ATTR_WINDOW_END]
        if window_start > window_end:
            raise ServiceValidationError(
                "window_start must be less than or equal to window_end"
            )

        # WEEKDAYS is Monday..Sunday (index 0..6). PSN's
        # ohanaUpdatePlaytimeSchedule applies the 7-entry list in this order,
        # so entry 0 == Monday. (Documented assumption — see services.yaml.)
        schedule: list[dict[str, object]] = []
        for day in WEEKDAYS:
            minutes = call.data.get(day, 0) or 0
            duration = format_pt(minutes * 60) if minutes else "P0D"
            schedule.append(
                {
                    "maxPlaytimeDuration": duration,
                    "windowStart": window_start,
                    "windowEnd": window_end,
                }
            )

        try:
            await coordinator.client.set_playtime_schedule(
                member.member_id, schedule
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set weekly schedule for %s: %s",
                member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set weekly schedule: {err}"
            ) from err
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_WEEKLY_SCHEDULE,
        _handle_set_weekly_schedule,
        schema=SET_WEEKLY_SCHEDULE_SCHEMA,
    )


def _resolve_target(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[PlaystationFamilyCoordinator, FamilyMember]:
    """Resolve the service target to (coordinator, child member).

    Accepts ``device_id`` (preferred) or ``entity_id``; both are mapped to a
    child PSN account id, then to the owning config entry's coordinator.
    """
    account_id = _account_id_from_call(hass, call)
    if account_id is None:
        raise ServiceValidationError(
            "Provide a device_id or entity_id for a PlayStation Family child"
        )

    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator: PlaystationFamilyCoordinator | None = getattr(
            entry, "runtime_data", None
        )
        if coordinator is None:
            continue
        for member in coordinator.children:
            if member.identity.account_id == account_id:
                return coordinator, member

    raise ServiceValidationError(
        f"No configured PlayStation Family child found for {account_id}"
    )


def _account_id_from_call(
    hass: HomeAssistant, call: ServiceCall
) -> str | None:
    """Extract the child PSN account id from device_id or entity_id."""
    device_id = call.data.get(ATTR_DEVICE_ID)
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device_id: {device_id}")
        return _account_id_from_identifiers(device.identifiers)

    entity_id = call.data.get(ATTR_ENTITY_ID)
    if entity_id:
        entity_registry = er.async_get(hass)
        entity = entity_registry.async_get(entity_id)
        if entity is None or entity.device_id is None:
            raise ServiceValidationError(f"Unknown entity_id: {entity_id}")
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(entity.device_id)
        if device is None:
            raise ServiceValidationError(
                f"No device for entity_id: {entity_id}"
            )
        return _account_id_from_identifiers(device.identifiers)

    return None


def _account_id_from_identifiers(
    identifiers: set[tuple[str, str]],
) -> str | None:
    """Return the PSN account id from a device's ``{(DOMAIN, account_id)}``."""
    for domain, account_id in identifiers:
        if domain == DOMAIN:
            return account_id
    return None
