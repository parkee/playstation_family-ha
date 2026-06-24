"""Number platform for the PlayStation Family integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from psnfamily import PsnFamilyError

from .const import LOGGER
from .coordinator import PlaystationFamilyConfigEntry, PlaystationFamilyCoordinator
from .entity import PlaystationFamilyChildEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the daily play-time limit number for each child."""
    coordinator = entry.runtime_data
    async_add_entities(
        PlaystationFamilyDailyLimitNumber(coordinator, member)
        for member in coordinator.children
    )


class PlaystationFamilyDailyLimitNumber(
    PlaystationFamilyChildEntity, NumberEntity
):
    """Daily play-time limit (in minutes) for a child.

    A value of 0 means unlimited. Values are quantized to 15 minutes by the
    PS Family API.
    """

    _attr_translation_key = "daily_playtime_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 15
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: PlaystationFamilyCoordinator, member) -> None:
        """Initialize the daily limit number."""
        super().__init__(coordinator, member)
        self._attr_unique_id = f"{self._account_id}_daily_playtime_limit"

    @property
    def native_value(self) -> float | None:
        """Return today's limit in minutes (0 if unlimited)."""
        data = self.child_data
        if data is None:
            return None
        seconds = data.playtime.today_limit_seconds
        if not seconds:
            return 0
        return seconds / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set the daily play-time limit."""
        seconds = int(value) * 60 if value > 0 else None
        try:
            await self.coordinator.client.set_daily_limit(
                self._member.member_id, seconds
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set daily limit for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set daily play-time limit: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
