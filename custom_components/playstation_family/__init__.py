"""The PlayStation Family integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, SERVICE_SET_WEEKLY_SCHEDULE
from .coordinator import (
    PlaystationFamilyConfigEntry,
    PlaystationFamilyCoordinator,
)
from .services import async_setup_services


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
) -> bool:
    """Set up PlayStation Family from a config entry."""
    coordinator = PlaystationFamilyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register integration-wide services once.
    if not hass.services.has_service(DOMAIN, SERVICE_SET_WEEKLY_SCHEDULE):
        async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
) -> bool:
    """Unload a PlayStation Family config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
