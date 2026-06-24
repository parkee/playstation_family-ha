"""DataUpdateCoordinator for the PlayStation Family integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from psnfamily import (
    FamilyMember,
    OhanaClient,
    Playtime,
    Presence,
    PsnFamilyAuthError,
    PsnFamilyConnectionError,
    PsnFamilyError,
    TokenSet,
)

from .const import CONF_TOKENS, DOMAIN, LOGGER, UPDATE_INTERVAL

type PlaystationFamilyConfigEntry = ConfigEntry[PlaystationFamilyCoordinator]


@dataclass
class ChildData:
    """Per-child data assembled on each coordinator refresh."""

    member: FamilyMember
    playtime: Playtime
    presence: Presence | None


class PlaystationFamilyCoordinator(
    DataUpdateCoordinator[dict[str, ChildData]]
):
    """Coordinator that polls the PS Family API for each child.

    Fetches the child roster once in :meth:`_async_setup`, then on every
    update gathers each child's play-time and a single batched presence
    response. The underlying client self-throttles (1 req / 3s), so calls
    naturally serialize. Refreshed OAuth tokens are persisted back to the
    config entry whenever they change.
    """

    config_entry: PlaystationFamilyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: PlaystationFamilyConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
        )
        session = async_get_clientsession(hass)
        tokens = TokenSet.from_dict(config_entry.data[CONF_TOKENS])
        self.client = OhanaClient(session=session, tokens=tokens)
        self.children: list[FamilyMember] = []

    async def _async_setup(self) -> None:
        """Fetch the child roster once before the first refresh."""
        try:
            self.children = await self.client.get_children()
        except PsnFamilyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PsnFamilyConnectionError as err:
            raise UpdateFailed(f"Error connecting to PSN: {err}") from err
        except PsnFamilyError as err:
            raise UpdateFailed(f"Error fetching family members: {err}") from err
        LOGGER.debug("Loaded %d child member(s) from PS Family", len(self.children))
        self._persist_tokens()

    async def _async_update_data(self) -> dict[str, ChildData]:
        """Fetch play-time and presence for every child."""
        if not self.children:
            return {}

        account_ids = [c.identity.account_id for c in self.children]
        try:
            presences = await self.client.get_presences(
                account_ids, now_playing=True
            )
            presence_by_id = {p.account_id: p for p in presences}

            data: dict[str, ChildData] = {}
            for child in self.children:
                account_id = child.identity.account_id
                playtime = await self.client.get_playtime(account_id)
                data[account_id] = ChildData(
                    member=child,
                    playtime=playtime,
                    presence=presence_by_id.get(account_id),
                )
        except PsnFamilyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PsnFamilyConnectionError as err:
            # Keep prior data on transient connection errors.
            raise UpdateFailed(f"Error connecting to PSN: {err}") from err
        except PsnFamilyError as err:
            raise UpdateFailed(f"Error fetching PS Family data: {err}") from err

        self._persist_tokens()
        return data

    def _persist_tokens(self) -> None:
        """Write refreshed OAuth tokens back to the config entry if changed."""
        tokens = self.client.tokens
        if tokens is None:
            return
        new_tokens = tokens.to_dict()
        if new_tokens == self.config_entry.data.get(CONF_TOKENS):
            return
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_TOKENS: new_tokens},
        )
        LOGGER.debug("Persisted refreshed PSN tokens to config entry")

    def get_child_data(self, account_id: str) -> ChildData | None:
        """Return the assembled data for a child by account id."""
        if self.data is None:
            return None
        return self.data.get(account_id)
