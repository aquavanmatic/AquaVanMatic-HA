"""Serve the dashboard strategy and keep it registered as a Lovelace resource.

Since HA 2026.10 the extra-module mechanism (add_extra_js_url) is no longer
reliable for loading custom dashboard strategies, so the integration manages a
regular Lovelace resource (type "module") itself:

* creates it if missing,
* updates the ?v= cache-busting parameter on every new version,
* removes duplicates (e.g. an entry a user added by hand),
* removes it again when the last AquaVanMatic entry is deleted.
"""
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, STRATEGY_URL, VERSION

_LOGGER = logging.getLogger(__name__)

RESOURCE_URL = f"{STRATEGY_URL}?v={VERSION}"


async def async_register_static(hass):
    """Serve frontend/aquavanmatic-strategy.js under STRATEGY_URL (once)."""
    if hass.data.get(f"{DOMAIN}_static"):
        return
    path = Path(__file__).parent / "frontend" / "aquavanmatic-strategy.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STRATEGY_URL, str(path), False)]
    )
    hass.data[f"{DOMAIN}_static"] = True


def _resources(hass):
    """Lovelace resource collection, or None (e.g. resources in YAML mode)."""
    data = None
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # HA >= 2025.2
        data = hass.data.get(LOVELACE_DATA)
    except ImportError:
        pass
    if data is None:
        data = hass.data.get("lovelace")
    if data is None:
        return None
    resources = data.get("resources") if isinstance(data, dict) else getattr(data, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        return None  # YAML mode: resources are read-only
    return resources


async def _loaded(resources):
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True


def _ours(resources):
    return [item for item in resources.async_items()
            if str(item.get("url", "")).split("?")[0] == STRATEGY_URL]


async def async_ensure_resource(hass):
    """Create/update the Lovelace resource; never raises."""
    try:
        resources = _resources(hass)
        if resources is None:
            _LOGGER.warning(
                "AquaVanMatic: Lovelace-Ressourcen nicht verwaltbar (YAML-Modus?). "
                "Bitte '%s' als JavaScript-Modul unter Einstellungen → Dashboards → "
                "Ressourcen eintragen.", RESOURCE_URL)
            return
        await _loaded(resources)
        ours = _ours(resources)
        if not ours:
            await resources.async_create_item({"res_type": "module", "url": RESOURCE_URL})
            _LOGGER.info("AquaVanMatic: Lovelace-Ressource angelegt: %s", RESOURCE_URL)
            return
        keep, *duplicates = ours
        if keep.get("url") != RESOURCE_URL or keep.get("type") != "module":
            await resources.async_update_item(keep["id"], {"res_type": "module", "url": RESOURCE_URL})
            _LOGGER.info("AquaVanMatic: Lovelace-Ressource aktualisiert: %s", RESOURCE_URL)
        for item in duplicates:
            await resources.async_delete_item(item["id"])
            _LOGGER.info("AquaVanMatic: doppelte Lovelace-Ressource entfernt: %s", item.get("url"))
    except Exception:  # pragma: no cover - must never block the integration
        _LOGGER.exception("AquaVanMatic: Lovelace-Ressource konnte nicht eingerichtet werden")


async def async_remove_resource(hass):
    """Remove our resource(s), e.g. after the last entry was deleted."""
    try:
        resources = _resources(hass)
        if resources is None:
            return
        await _loaded(resources)
        for item in _ours(resources):
            await resources.async_delete_item(item["id"])
        _LOGGER.info("AquaVanMatic: Lovelace-Ressource entfernt")
    except Exception:  # pragma: no cover
        _LOGGER.exception("AquaVanMatic: Lovelace-Ressource konnte nicht entfernt werden")
