"""Sensor platform for the PlayStation Family integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import (
    ChildData,
    PlaystationFamilyConfigEntry,
    PlaystationFamilyCoordinator,
)
from .entity import PlaystationFamilyChildEntity


@dataclass(frozen=True, kw_only=True)
class PlaystationFamilySensorDescription(SensorEntityDescription):
    """Describe a PS Family child sensor."""

    value_fn: Callable[[ChildData], int | str | datetime | None]


def _used_today_minutes(data: ChildData) -> int:
    """Minutes of play-time used today."""
    return data.playtime.used_today_seconds // 60


def _remaining_minutes(data: ChildData) -> int | None:
    """Minutes of play-time remaining today (None if unlimited)."""
    remaining = data.playtime.remaining_seconds
    if remaining is None:
        return None
    return remaining // 60


def _online_status(data: ChildData) -> str | None:
    """Current online status string."""
    if data.presence is None:
        return None
    return data.presence.online_status or None


def _now_playing(data: ChildData) -> str:
    """Title currently being played, or 'Not playing'."""
    if data.presence is None or not data.presence.now_playing_title:
        return "Not playing"
    return data.presence.now_playing_title


def _last_online(data: ChildData) -> datetime | None:
    """Parse the last-online timestamp into a tz-aware datetime."""
    if data.presence is None or not data.presence.last_online_date:
        return None
    return dt_util.parse_datetime(data.presence.last_online_date)


SENSOR_DESCRIPTIONS: tuple[PlaystationFamilySensorDescription, ...] = (
    PlaystationFamilySensorDescription(
        key="playtime_used_today",
        translation_key="playtime_used_today",
        icon="mdi:timer-play",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_used_today_minutes,
    ),
    PlaystationFamilySensorDescription(
        key="playtime_remaining",
        translation_key="playtime_remaining",
        icon="mdi:timer-sand",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_remaining_minutes,
    ),
    PlaystationFamilySensorDescription(
        key="online_status",
        translation_key="online_status",
        icon="mdi:account-circle",
        value_fn=_online_status,
    ),
    PlaystationFamilySensorDescription(
        key="now_playing",
        translation_key="now_playing",
        icon="mdi:gamepad-variant",
        value_fn=_now_playing,
    ),
    PlaystationFamilySensorDescription(
        key="last_online",
        translation_key="last_online",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_online,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PS Family sensors for each child."""
    coordinator = entry.runtime_data
    async_add_entities(
        PlaystationFamilySensor(coordinator, member, description)
        for member in coordinator.children
        for description in SENSOR_DESCRIPTIONS
    )


class PlaystationFamilySensor(PlaystationFamilyChildEntity, SensorEntity):
    """A sensor describing one aspect of a child's PS Family status."""

    entity_description: PlaystationFamilySensorDescription

    def __init__(
        self,
        coordinator: PlaystationFamilyCoordinator,
        member,
        description: PlaystationFamilySensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, member)
        self.entity_description = description
        self._attr_unique_id = f"{self._account_id}_{description.key}"

    @property
    def native_value(self) -> int | str | datetime | None:
        """Return the sensor value from the coordinator data."""
        data = self.child_data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
