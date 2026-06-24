"""Config flow for the PlayStation Family integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from psnfamily import (
    FamilyMember,
    OhanaClient,
    PsnFamilyAuthError,
    PsnFamilyConnectionError,
    PsnFamilyScopeError,
)

from .const import CONF_NPSSO, CONF_TOKENS, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NPSSO): str,
    }
)

# Family roles that identify the family manager / owner account. The roster
# data uses "FAMILY_MANAGER"; "OWNER" is accepted defensively.
_MANAGER_ROLES = {"OWNER", "FAMILY_MANAGER"}


class PlaystationFamilyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PlayStation Family."""

    VERSION = 1

    async def _validate_npsso(
        self, npsso: str
    ) -> tuple[OhanaClient, list[FamilyMember]]:
        """Authenticate with an npsso and return the client and roster.

        Raises the psnfamily exceptions for the caller to map to errors.
        """
        session = async_get_clientsession(self.hass)
        client = OhanaClient(session=session)
        await client.authenticate(npsso)
        members = await client.get_family_members()
        return client, members

    @staticmethod
    def _owner_account_id(members: list[FamilyMember]) -> str | None:
        """Return the account id of the family manager / owner, if present."""
        for member in members:
            if member.identity.family_role in _MANAGER_ROLES:
                return member.identity.account_id
        # Fall back to the first non-child member (the managing adult).
        for member in members:
            if not member.identity.is_child:
                return member.identity.account_id
        return None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            npsso = user_input[CONF_NPSSO]
            try:
                client, members = await self._validate_npsso(npsso)
            except PsnFamilyAuthError:
                errors["base"] = "invalid_auth"
            except PsnFamilyScopeError:
                errors["base"] = "scope_unavailable"
            except PsnFamilyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            else:
                owner_id = self._owner_account_id(members)
                if owner_id:
                    await self.async_set_unique_id(owner_id)
                    self._abort_if_unique_id_configured()

                tokens = client.tokens
                return self.async_create_entry(
                    title="PlayStation Family",
                    data={
                        CONF_NPSSO: npsso,
                        CONF_TOKENS: tokens.to_dict() if tokens else {},
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the npsso/token has died."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication by re-entering the npsso."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            npsso = user_input[CONF_NPSSO]
            try:
                client, members = await self._validate_npsso(npsso)
            except PsnFamilyAuthError:
                errors["base"] = "invalid_auth"
            except PsnFamilyScopeError:
                errors["base"] = "scope_unavailable"
            except PsnFamilyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                owner_id = self._owner_account_id(members)
                if owner_id:
                    await self.async_set_unique_id(owner_id)
                    self._abort_if_unique_id_mismatch(reason="wrong_account")

                tokens = client.tokens
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_NPSSO: npsso,
                        CONF_TOKENS: tokens.to_dict() if tokens else {},
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
