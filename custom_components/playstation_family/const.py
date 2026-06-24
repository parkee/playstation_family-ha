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

# PSN self-throttles to 1 request / 3s and play-time data changes slowly, so a
# 2-minute poll keeps us well within rate limits while staying fresh.
UPDATE_INTERVAL: Final = timedelta(seconds=120)

PLATFORMS: Final[list[Platform]] = [
    Platform.NUMBER,
    Platform.SENSOR,
]
