"""Number platform for the PlayStation Family integration.

Play-time limit numbers per child (all in minutes, 15-minute steps):

* **Today's playtime limit** — a *one-day* override that absolutely sets today's
  limit (PSN's ``updateTodaysPlaytimeLimit``). ``0`` clears the override, so
  today reverts to the recurring schedule.
* **Daily playtime limit** — sets the *recurring* limit uniformly on every
  weekday at once (the per-day playable windows are preserved). ``0`` blocks
  play every day; it is not an "unlimited" sentinel.
* **<Weekday> playtime limit** — the recurring limit for one weekday only
  (Monday…Sunday). Editing one day leaves the other six untouched.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from psnfamily import PsnFamilyError

from .const import LOGGER, WEEKDAY_NAMES, WEEKDAYS
from .coordinator import PlaystationFamilyConfigEntry, PlaystationFamilyCoordinator
from .entity import PlaystationFamilyChildEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the today, uniform-daily, and per-weekday limit numbers."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    for member in coordinator.children:
        entities.append(PlaystationFamilyTodayLimitNumber(coordinator, member))
        entities.append(PlaystationFamilyDailyLimitNumber(coordinator, member))
        entities.extend(
            PlaystationFamilyWeekdayLimitNumber(coordinator, member, weekday)
            for weekday in range(7)
        )
    async_add_entities(entities)


class _PlaytimeLimitNumber(PlaystationFamilyChildEntity, NumberEntity):
    """Shared config for the play-time limit numbers (minutes, 15-min steps)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 15
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    async def _apply(self, coro) -> None:
        """Await a client write, mapping errors to HA and refreshing after."""
        try:
            await coro
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set play-time limit for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set play-time limit: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


class PlaystationFamilyTodayLimitNumber(_PlaytimeLimitNumber):
    """Today's play-time limit (minutes) for a child — a one-day override.

    Absolutely sets today's limit. ``0`` clears the override, so today reverts
    to the recurring schedule.
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
        return None if seconds is None else seconds / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set today's play-time limit (0 = clear override / revert to schedule)."""
        await self._apply(
            self.coordinator.client.set_today_limit(self._member, int(value) * 60)
        )


class PlaystationFamilyDailyLimitNumber(_PlaytimeLimitNumber):
    """Uniform recurring daily limit (minutes) — applied to every weekday.

    ``0`` blocks play every day. Per-day playable windows are preserved.
    """

    _attr_translation_key = "daily_playtime_limit"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: PlaystationFamilyCoordinator, member) -> None:
        """Initialize the uniform daily limit number."""
        super().__init__(coordinator, member)
        self._attr_unique_id = f"{self._account_id}_daily_playtime_limit"

    @property
    def native_value(self) -> float | None:
        """Return the recurring per-day limit in minutes (0 = blocked).

        When the weekdays differ, returns ``None`` (mixed) so the value isn't
        misleading; use the per-weekday numbers to see each day.
        """
        data = self.child_data
        if data is None:
            return None
        schedule = data.playtime.weekly_schedule
        durations = {day.duration_seconds for day in schedule}
        if len(durations) != 1:
            return None
        return durations.pop() / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set the same recurring limit on every weekday (0 = block every day)."""
        await self._apply(
            self.coordinator.client.set_all_days_limit(self._member, int(value) * 60)
        )


class PlaystationFamilyWeekdayLimitNumber(_PlaytimeLimitNumber):
    """Recurring play-time limit (minutes) for a single weekday."""

    _attr_translation_key = "weekday_playtime_limit"
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: PlaystationFamilyCoordinator, member, weekday: int
    ) -> None:
        """Initialize the per-weekday limit number (``weekday`` 0=Mon..6=Sun)."""
        super().__init__(coordinator, member)
        self._weekday = weekday
        self._attr_translation_placeholders = {"day": WEEKDAY_NAMES[weekday]}
        self._attr_unique_id = f"{self._account_id}_limit_{WEEKDAYS[weekday]}"

    @property
    def native_value(self) -> float | None:
        """Return this weekday's recurring limit in minutes (0 = blocked)."""
        data = self.child_data
        if data is None:
            return None
        return data.playtime.weekly_schedule[self._weekday].duration_seconds / 60

    async def async_set_native_value(self, value: float) -> None:
        """Set this weekday's recurring limit, leaving the other days untouched."""
        await self._apply(
            self.coordinator.client.set_schedule_day(
                self._member, self._weekday, duration_seconds=int(value) * 60
            )
        )
