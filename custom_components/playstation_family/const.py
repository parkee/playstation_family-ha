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

# Service for a one-off, today-only play-time adjustment (signed delta). Unlike
# the recurring "Daily playtime limit" number, today's limit is a *delta*
# operation (PSN's updateTodaysPlaytimeLimit), so it is exposed as add/remove
# rather than an absolute set -- mirroring the app's "+15 / -15 min" buttons.
SERVICE_ADJUST_TODAY_PLAYTIME: Final = "adjust_today_playtime"

# Service for writing a single parental-control field (web browsing, comms, VR,
# age/content level, spending limit). Write-only: PSN exposes no clean read of
# the current values, so this is an action rather than a stateful entity.
SERVICE_SET_PARENTAL_CONTROL: Final = "set_parental_control"

# Step used by the today-only +/- buttons and the default service step, matching
# the app's 15-minute increments (the API quantizes to 15 min regardless).
TODAY_STEP_MINUTES: Final = 15

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
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]
