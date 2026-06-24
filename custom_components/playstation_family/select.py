"""Select platform for the PlayStation Family integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from psnfamily import PsnFamilyError

from .const import LOGGER
from .coordinator import PlaystationFamilyConfigEntry, PlaystationFamilyCoordinator
from .entity import PlaystationFamilyChildEntity

# Map the human-readable option labels to the PSN action values, both ways.
# The set of valid actions mirrors psnfamily.const.ON_LIMIT_ACTIONS.
_LABEL_TO_ACTION: dict[str, str] = {
    "Notify only": "NOTIFY_ONLY",
    "Log out": "FORCE_LOGOUT",
}
_ACTION_TO_LABEL: dict[str, str] = {v: k for k, v in _LABEL_TO_ACTION.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlaystationFamilyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the on-limit action select for each child."""
    coordinator = entry.runtime_data
    async_add_entities(
        PlaystationFamilyOnLimitSelect(coordinator, member)
        for member in coordinator.children
    )


class PlaystationFamilyOnLimitSelect(PlaystationFamilyChildEntity, SelectEntity):
    """Action taken when a child reaches their daily play-time limit."""

    _attr_translation_key = "on_limit_action"
    _attr_icon = "mdi:bell-alert"
    _attr_options = list(_LABEL_TO_ACTION)

    def __init__(self, coordinator: PlaystationFamilyCoordinator, member) -> None:
        """Initialize the on-limit action select."""
        super().__init__(coordinator, member)
        self._attr_unique_id = f"{self._account_id}_on_limit_action"

    @property
    def current_option(self) -> str | None:
        """Return the current on-limit action as a display label."""
        data = self.child_data
        if data is None:
            return None
        return _ACTION_TO_LABEL.get(data.playtime.on_limit_reached)

    async def async_select_option(self, option: str) -> None:
        """Set the on-limit action."""
        action = _LABEL_TO_ACTION.get(option)
        if action is None:
            raise HomeAssistantError(f"Unknown on-limit action: {option}")
        try:
            await self.coordinator.client.set_on_limit_action(
                self._member.member_id, action
            )
        except PsnFamilyError as err:
            LOGGER.error(
                "Failed to set on-limit action for %s: %s",
                self._member.identity.display_name,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set on-limit action: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
