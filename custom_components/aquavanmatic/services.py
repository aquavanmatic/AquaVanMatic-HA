"""Actions (services) of the AquaVanMatic integration.

aquavanmatic.report_leakage – report an external leakage to one unit
(POST /api/leakage, sensor=1|2|3). Acts like the unit's own leakage input:
the running process is aborted and the message stays until acknowledged.
"""
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, LEAKAGE_SENSORS
from .rest import fail, post

SERVICE_REPORT_LEAKAGE = "report_leakage"

SCHEMA_REPORT_LEAKAGE = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("sensor"): vol.All(vol.Coerce(int), vol.In(LEAKAGE_SENSORS)),
})


def _entry_for_device(hass, device_id):
    """Config entry of the AquaVanMatic unit behind a HA device id."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise HomeAssistantError("Gerät nicht gefunden")
    identifiers = {value for domain, value in device.identifiers if domain == "mqtt"}
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.unique_id in identifiers:
            return entry
    raise HomeAssistantError("Das gewählte Gerät ist keine eingerichtete AquaVanMatic-Anlage")


async def async_register_services(hass):
    if hass.services.has_service(DOMAIN, SERVICE_REPORT_LEAKAGE):
        return

    async def report_leakage(call):
        entry = _entry_for_device(hass, call.data["device_id"])
        sensor = call.data["sensor"]
        status, payload = await post(hass, entry, "/api/leakage", {"sensor": str(sensor)})
        if status == 200 and payload.get("ok") is True:
            return
        fail(f"Leckage {sensor}", status, payload)

    hass.services.async_register(DOMAIN, SERVICE_REPORT_LEAKAGE, report_leakage,
                                 schema=SCHEMA_REPORT_LEAKAGE)
