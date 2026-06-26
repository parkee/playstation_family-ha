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

# Service for a one-off, today-only play-time adjustment (signed minutes). PSN's
# updateTodaysPlaytimeLimit absolutely sets today's one-day override, so the
# library reads the current value and writes back current +/- the amount --
# mirroring the app's "+15 / -15 min" buttons. The recurring "Daily playtime
# limit" number is a separate, absolute control.
SERVICE_ADJUST_TODAY_PLAYTIME: Final = "adjust_today_playtime"

# Service for writing a single parental-control field (web browsing, comms, VR,
# age/content level, spending limit). Write-only: PSN exposes no clean read of
# the current values, so this is an action rather than a stateful entity.
SERVICE_SET_PARENTAL_CONTROL: Final = "set_parental_control"

ATTR_MINUTES: Final = "minutes"
ATTR_FIELD: Final = "field"
ATTR_VALUE: Final = "value"

# Parental-control fields writable via psnfamily.OhanaClient.set_parental_control.
# The full updateParentalControls content family (all individually allow-listed).
PARENTAL_CONTROL_FIELDS: Final[tuple[str, ...]] = (
    "internetBrowser",
    "vrApp",
    "freeCommunication",
    "contentControl",
    "ageLevel",
    "gameContent",
    "spendingLimit",
    "bluerayAgeContent",
    "discContentCountry",
    "dvdContent",
)

# Mon..Sun keys for the weekly schedule. Index 0 == Monday matches the order
# PSN's ohanaUpdatePlaytimeSchedule applies the 7-entry list (confirmed live by
# writing 7 distinct durations and reading back which weekday each landed on).
WEEKDAYS: Final[tuple[str, ...]] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# Display names for the per-weekday schedule entities (translation placeholder).
WEEKDAY_NAMES: Final[tuple[str, ...]] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
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
    Platform.TIME,
]
