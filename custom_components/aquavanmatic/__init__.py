"""AquaVanMatic: REST buttons for MQTT-discovered devices plus a ready-made dashboard."""
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PREFIX, STRATEGY_URL, VERSION
from .decision import DecisionState
from .discovery import find_devices

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BUTTON, Platform.SELECT]


async def _async_register_frontend(hass):
    """Serve the dashboard strategy and load it in every browser session."""
    if hass.data.get(f"{DOMAIN}_frontend"):
        return
    path = Path(__file__).parent / "frontend" / "aquavanmatic-strategy.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STRATEGY_URL, str(path), False)]
    )
    url = f"{STRATEGY_URL}?v={VERSION}"
    add_extra_js_url(hass, url)             # moderne Oberfläche (Browser)
    add_extra_js_url(hass, url, es5=True)   # Kompatibilitäts-Oberfläche (ältere App-Webviews)
    hass.data[f"{DOMAIN}_frontend"] = True


async def async_setup(hass, config):
    """Runs once the integration is loaded (UI entry or legacy YAML).

    Registers the dashboard strategy and watches the device registry so that
    further AquaVanMatic devices are added automatically.
    """
    await _async_register_frontend(hass)
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
