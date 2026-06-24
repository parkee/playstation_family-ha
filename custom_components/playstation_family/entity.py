"""Base entity for the PlayStation Family integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from psnfamily import FamilyMember

from .const import DOMAIN
from .coordinator import ChildData, PlaystationFamilyCoordinator


class PlaystationFamilyChildEntity(
    CoordinatorEntity[PlaystationFamilyCoordinator]
):
    """Base entity for a PS Family child.

    Each child is exposed as one HA device, identified by the child's PSN
    account id. Concrete platform entities attach to this device.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlaystationFamilyCoordinator,
        member: FamilyMember,
    ) -> None:
        """Initialize the child entity."""
        super().__init__(coordinator)
        self._member = member
        self._account_id = member.identity.account_id

        display_name = member.identity.display_name or member.identity.online_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._account_id)},
            name=display_name or self._account_id,
            manufacturer="Sony",
            model="PlayStation Family",
        )

    @property
    def child_data(self) -> ChildData | None:
        """Return the coordinator data for this child."""
        return self.coordinator.get_child_data(self._account_id)

    @property
    def available(self) -> bool:
        """Return True if the coordinator has data for this child."""
        return super().available and self.child_data is not None
