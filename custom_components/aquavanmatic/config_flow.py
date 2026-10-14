"""Config flow: devices come from MQTT, the user only picks/confirms."""
import json
import re

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN, PREFIX
from .discovery import find_devices

SERIAL_RE = re.compile(r"^\d{10}$")


def _title(identifier):
    return f"AquaVanMatic {identifier.removeprefix(PREFIX)}"


class AquaVanMaticConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_import(self, discovery_info):
        """Created automatically by the registry scan in __init__.py."""
        identifier = discovery_info["identifier"]
        if not identifier.startswith(PREFIX):
            return self.async_abort(reason="invalid_device")
        await self.async_set_unique_id(identifier)
        self._abort_if_unique_id_configured(updates={"url": discovery_info["url"]})
        return self.async_create_entry(title=_title(identifier),
                                       data={"url": discovery_info["url"]})

    async def async_step_mqtt(self, discovery_info):
        """Started by HA when a retained discovery config arrives on
        homeassistant/sensor/<node_id>/stateText/config (one topic per unit).

        Only units with manufacturer "AquaVanMatic", an entity unique_id
        starting with "aquamatic_" and a 10-digit serial are accepted.
        """
        try:
            payload = json.loads(discovery_info.payload or "")
        except (ValueError, TypeError):
            return self.async_abort(reason="invalid_device")  # empty = removal
        if not isinstance(payload, dict):
            return self.async_abort(reason="invalid_device")

        # MQTT Discovery allows abbreviated keys (dev/mf/sn, uniq_id).
        device = payload.get("device") or payload.get("dev") or {}
        manufacturer = device.get("manufacturer") or device.get("mf")
        serial = str(device.get("serial_number") or device.get("sn") or "")
        unique_id = str(payload.get("unique_id") or payload.get("uniq_id") or "")
        if (manufacturer != "AquaVanMatic"
                or not unique_id.startswith(PREFIX)
                or not SERIAL_RE.match(serial)):
            return self.async_abort(reason="invalid_device")

        identifier = f"{PREFIX}{serial}"
        await self.async_set_unique_id(identifier)
        self._abort_if_unique_id_configured()
        self._identifier = identifier
        self.context["title_placeholders"] = {"name": _title(identifier)}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        """Customer clicks 'Hinzufügen' on the 'Neues Gerät gefunden' card."""
        if user_input is not None:
            # REST address comes from configuration_url of the MQTT device;
            # button.py reads it from the device registry at every press.
            url = dict(find_devices(self.hass)).get(self._identifier)
            return self.async_create_entry(title=_title(self._identifier),
                                           data={"url": url})
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": _title(self._identifier)},
        )

    async def async_step_user(self, user_input=None):
        """Customer clicks 'Integration hinzufügen → AquaVanMatic'."""
        configured = {entry.unique_id for entry in self._async_current_entries()}
        found = {ident: url for ident, url in find_devices(self.hass)
                 if ident not in configured}
        if not found:
            if configured:
                return self.async_abort(reason="already_configured")
            return self.async_abort(reason="no_devices_found")

        if user_input is not None:
            identifier = user_input["device"]
            await self.async_set_unique_id(identifier)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=_title(identifier),
                                           data={"url": found[identifier]})

        choices = {ident: _title(ident) for ident in found}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("device", default=next(iter(choices))): vol.In(choices)}
            ),
        )
