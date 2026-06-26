"""Time platform for the PlayStation Family integration.

Per-weekday **playable-hours window** (the app's "allowed hours / bedtime"
window): for each weekday a start and an end time entity. PSN stores the window
as minutes from local midnight; these entities convert to/from clock times and
write through the library's per-day schedule read-modify-write, so editing one
edge of one day leaves the rest of the schedule untouched.

Full day is ``00:00``–``24:00``. ``24:00`` can't be a ``time``, so an end of
``23:59`` is treated as end-of-day (1440 min) — a 1-minute granularity that is
irrelevant for a playable-hours window.
"""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from psnfamily import PsnFamilyError

from .const import LOGGER, WEEKDAY_NAMES, WEEKDAYS
from .coordinator import PlaystationFamilyConfigEntry, PlaystationFamilyCoordinator
from .entity import PlaystationFamilyChildEntity

_FULL_DAY_MINUTES = 1440


def _minutes_to_time(minutes: int) -> time:
    """Minutes from midnight (0..1440) -> clock time (1440 -> 23:59)."""
    if minutes >= _FULL_DAY_MINUTES:
        return time(23, 59)
    return time(minutes // 60, minutes % 60)


def _time_to_minutes(value: time) -> int:
    """Clock time -> minutes from midnight (23:59 -> end-of-day 1440)."""
    if value.hour == 23 and value.minute == 59:
        return _FULL_DAY_MINUTES
    return value.hour * 60 + value.minute


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the per-weekday playable-window start/end times for each child."""
    coordinator = entry.runtime_data
    async_add_entities(
        PlaystationFamilyWindowTime(coordinator, member, weekday, edge)
        for member in coordinator.children
        for weekday in range(7)
        for edge in ("start", "end")
    )


class PlaystationFamilyWindowTime(PlaystationFamilyChildEntity, TimeEntity):
    """One edge (start or end) of one weekday's playable-hours window."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: PlaystationFamilyCoordinator,
        member,
        weekday: int,
        edge: str,
    ) -> None:
        """Initialize a window time (``weekday`` 0=Mon..6=Sun, ``edge`` start/end)."""
        super().__init__(coordinator, member)
        self._weekday = weekday
        self._edge = edge
        self._attr_translation_key = f"weekday_window_{edge}"
        self._attr_translation_placeholders = {"day": WEEKDAY_NAMES[weekday]}
        self._attr_unique_id = (
            f"{self._account_id}_window_{edge}_{WEEKDAYS[weekday]}"
        )

    @property
    def native_value(self) -> time | None:
        """Return this edge of the weekday's playable window as a clock time."""
        data = self.child_data
        if data is None:
            return None
        day = data.playtime.weekly_schedule[self._weekday]
        minutes = (
            day.window_start_minutes
            if self._edge == "start"
            else day.window_end_minutes
        )
        return _minutes_to_time(minutes)

    async def async_set_value(self, value: time) -> None:
        """Set this edge of the weekday's window, leaving the rest untouched."""
        minutes = _time_to_minutes(value)
        kwargs = (
            {"window_start_minutes": minutes}
            if self._edge == "start"
            else {"window_end_minutes": minutes}
        )
        try:
            await self.coordinator.client.set_schedule_day(
                self._member, self._weekday, **kwargs
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set playable window for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set playable-hours window: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
