"""Button platform for the PlayStation Family integration.

Exposes today-only play-time adjustments. PSN's ``updateTodaysPlaytimeLimit``
*absolutely sets* today's one-day override, so the library's ``add_time`` /
``remove_time`` helpers read today's current limit and write back
``current ± 15 min`` -- mirroring the PS Family app's "+15 / -15 min" buttons on
the "Change Playtime for Today" screen. Removing past 0 clears the override, so
today reverts to the recurring schedule (it never goes negative). The recurring
per-day limit is the separate "Daily playtime limit" number entity.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from psnfamily import FamilyMember, OhanaClient, PsnFamilyError

from .const import LOGGER, TODAY_STEP_MINUTES
from .coordinator import PlaystationFamilyConfigEntry, PlaystationFamilyCoordinator
from .entity import PlaystationFamilyChildEntity

_STEP_SECONDS = TODAY_STEP_MINUTES * 60


@dataclass(frozen=True, kw_only=True)
class PlaystationFamilyButtonDescription(ButtonEntityDescription):
    """Describe a PS Family child button and the client call it performs."""

    press_fn: Callable[[OhanaClient, FamilyMember], Coroutine[Any, Any, bool]]


BUTTON_DESCRIPTIONS: tuple[PlaystationFamilyButtonDescription, ...] = (
    PlaystationFamilyButtonDescription(
        key="add_today_playtime",
        translation_key="add_today_playtime",
        icon="mdi:timer-plus",
        press_fn=lambda client, member: client.add_time(member, _STEP_SECONDS),
    ),
    PlaystationFamilyButtonDescription(
        key="remove_today_playtime",
        translation_key="remove_today_playtime",
        icon="mdi:timer-minus",
        press_fn=lambda client, member: client.remove_time(member, _STEP_SECONDS),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the today-only play-time adjustment buttons for each child."""
    coordinator = entry.runtime_data
    async_add_entities(
        PlaystationFamilyButton(coordinator, member, description)
        for member in coordinator.children
        for description in BUTTON_DESCRIPTIONS
    )


class PlaystationFamilyButton(PlaystationFamilyChildEntity, ButtonEntity):
    """A one-press today-only play-time adjustment for a child."""

    entity_description: PlaystationFamilyButtonDescription

    def __init__(
        self,
        coordinator: PlaystationFamilyCoordinator,
        member,
        description: PlaystationFamilyButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, member)
        self.entity_description = description
        self._attr_unique_id = f"{self._account_id}_{description.key}"

    async def async_press(self) -> None:
        """Apply the today-only adjustment and refresh."""
        try:
            await self.entity_description.press_fn(
                self.coordinator.client, self._member
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed today's play-time adjustment for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to adjust today's play-time: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
