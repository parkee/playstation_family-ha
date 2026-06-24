"""Constants for the PlayStation Family integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "playstation_family"
LOGGER = logging.getLogger(__package__)

CONF_NPSSO: Final = "npsso"
CONF_TOKENS: Final = "tokens"

# Service for setting a per-weekday play-time schedule.
SERVICE_SET_WEEKLY_SCHEDULE: Final = "set_weekly_schedule"

# Mon..Sun keys for the weekly-schedule service. Index 0 == Monday matches the
# order PSN's ohanaUpdatePlaytimeSchedule applies the 7-entry list (see the
# service handler for the documented assumption).
WEEKDAYS: Final[tuple[str, ...]] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

ATTR_DEVICE_ID: Final = "device_id"
ATTR_ENTITY_ID: Final = "entity_id"
ATTR_WINDOW_START: Final = "window_start"
ATTR_WINDOW_END: Final = "window_end"

DEFAULT_WINDOW_START: Final = 0
DEFAULT_WINDOW_END: Final = 1440

# PSN self-throttles to 1 request / 3s and play-time data changes slowly, so a
# 2-minute poll keeps us well within rate limits while staying fresh.
UPDATE_INTERVAL: Final = timedelta(seconds=120)

PLATFORMS: Final[list[Platform]] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]
