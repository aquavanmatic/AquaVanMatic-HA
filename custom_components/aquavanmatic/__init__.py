"""AquaVanMatic: REST buttons for MQTT-discovered devices plus a ready-made dashboard."""
import logging

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PREFIX
from .decision import DecisionState
from .discovery import find_devices
from .services import async_register_services
from .frontend_resource import (
    async_ensure_resource,
    async_register_static,
    async_remove_resource,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BUTTON, Platform.SELECT]


async def async_setup(hass, config):
    """Runs once the integration is loaded (UI entry or legacy YAML).

    Serves the dashboard strategy, keeps it registered as Lovelace resource
    and watches the device registry so that
    further AquaVanMatic devices are added automatically.
    """
    await async_register_static(hass)
    await async_ensure_resource(hass)
    await async_register_services(hass)
    in_progress = set()

    @callback
    def schedule_scan(event=None):
        hass.async_create_task(scan())

    async def scan():
        for identifier, url in find_devices(hass):
            if identifier in in_progress:
                continue
            existing = next((entry for entry in hass.config_entries.async_entries(DOMAIN)
                             if entry.unique_id == identifier), None)
            if existing:
                if existing.data.get("url") != url:
                    hass.config_entries.async_update_entry(existing, data={"url": url})
                continue
            in_progress.add(identifier)
            try:
                await hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data={"identifier": identifier, "url": url},
                )
            except Exception:
                _LOGGER.exception("AquaVanMatic discovery failed for %s", identifier)
            finally:
                in_progress.discard(identifier)

    hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, schedule_scan)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, schedule_scan)
    schedule_scan()
    return True


async def async_setup_entry(hass, entry):
    state = DecisionState(hass, entry.unique_id.removeprefix(PREFIX))
    await state.async_start()
    entry.async_on_unload(state.async_stop)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass, entry):
    """Last AquaVanMatic entry deleted -> remove the Lovelace resource too."""
    if not [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]:
        await async_remove_resource(hass)
