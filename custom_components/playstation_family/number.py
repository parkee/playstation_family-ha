"""Number platform for the PlayStation Family integration.

Two play-time numbers per child:

* **Daily playtime limit** — the *recurring* per-day limit (PSN's weekly
  schedule, set uniformly). ``0`` blocks play every day (``P0D``); it is not an
  "unlimited" sentinel.
* **Today's playtime limit** — a *one-day* override that absolutely sets today's
  limit (PSN's ``updateTodaysPlaytimeLimit``). ``0`` clears the override, so
  today reverts to the recurring schedule. Setting any value (e.g. 13, 45) is
  accepted; PSN quantizes to 15-minute steps.
"""

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
    """Set up the recurring and today-only play-time limit numbers per child."""
    coordinator = entry.runtime_data
    async_add_entities(
        number(coordinator, member)
        for member in coordinator.children
        for number in (
            PlaystationFamilyDailyLimitNumber,
            PlaystationFamilyTodayLimitNumber,
        )
    )


class _PlaytimeLimitNumber(PlaystationFamilyChildEntity, NumberEntity):
    """Shared config for the play-time limit numbers (minutes, 15-min steps)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 15
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX


class PlaystationFamilyDailyLimitNumber(_PlaytimeLimitNumber):
    """Recurring daily play-time limit (minutes) for a child.

    ``0`` blocks play every day. Quantized to 15 minutes by PSN.
    """

    _attr_translation_key = "daily_playtime_limit"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: PlaystationFamilyCoordinator, member) -> None:
        """Initialize the recurring daily limit number."""
        super().__init__(coordinator, member)
        self._attr_unique_id = f"{self._account_id}_daily_playtime_limit"

    @property
    def native_value(self) -> float | None:
        """Return the recurring per-day limit in minutes (0 = blocked)."""
        data = self.child_data
        if data is None:
            return None
        seconds = data.playtime.recurring_limit_seconds
        if seconds is None:
            return None
        return seconds / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set the recurring daily play-time limit (0 = block every day)."""
        try:
            await self.coordinator.client.set_daily_limit(
                self._member.member_id, int(value) * 60
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


class PlaystationFamilyTodayLimitNumber(_PlaytimeLimitNumber):
    """Today's play-time limit (minutes) for a child — a one-day override.

    Absolutely sets today's limit. ``0`` clears the override, so today reverts
    to the recurring schedule. Quantized to 15 minutes by PSN.
    """

    _attr_translation_key = "today_playtime_limit"
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator: PlaystationFamilyCoordinator, member) -> None:
        """Initialize the today-only limit number."""
        super().__init__(coordinator, member)
        self._attr_unique_id = f"{self._account_id}_today_playtime_limit"

    @property
    def native_value(self) -> float | None:
        """Return today's effective limit in minutes (0 = blocked)."""
        data = self.child_data
        if data is None:
            return None
        seconds = data.playtime.today_limit_seconds
        if seconds is None:
            return None
        return seconds / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set today's play-time limit (0 = clear override / revert to schedule)."""
        try:
            await self.coordinator.client.set_today_limit(
                self._member, int(value) * 60
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set today's limit for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set today's play-time limit: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
