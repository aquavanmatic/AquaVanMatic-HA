"""Shared REST helpers: POST (form-urlencoded) to the unit, readable rejections."""
import asyncio
import logging
from urllib.parse import urlsplit

import aiohttp

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

REASONS = {
    "no_pending_decision": "Es ist keine Entscheidung mehr offen.",
    "decision_mismatch": "Inzwischen ist eine andere Entscheidung offen. Bitte die neue Frage prüfen.",
    "rejected": "Die Anlage hat die Entscheidung abgelehnt.",
    "invalid_result": "Ungültige Entscheidung.",
    "nothing_acknowledged": "Es wurde nichts quittiert – die Meldungen sind nicht mehr offen.",
    "codes_missing": "Keine Meldungsnummern übergeben.",
    "not_idle": "Nur im Leerlauf möglich. Bitte erst den laufenden Vorgang beenden.",
    "invalid_mode": "Ungültige Auswahl.",
    "invalid_process": "Ungültiger Vorgang.",
    "invalid_target": "Ungültiges Ablaufziel.",
    "invalid_sensor": "Ungültige Leckage-Nummer (erlaubt: 1, 2 oder 3).",
}


def base_url(hass, entry):
    """REST address from configuration_url of the MQTT device."""
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={("mqtt", entry.unique_id)})
    url = (device.configuration_url if device else None) or entry.data.get("url")
    if not url:
        raise HomeAssistantError("Keine REST-Adresse über MQTT Discovery verfügbar")
    parsed = urlsplit(url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise HomeAssistantError("Ungültige REST-Adresse in configuration_url")
    return f"{parsed.scheme}://{parsed.netloc}"


async def post(hass, entry, path, data=None):
    """POST and return (status, json-dict)."""
    url = f"{base_url(hass, entry)}{path}"
    try:
        async with asyncio.timeout(10):
            async with async_get_clientsession(hass).post(url, data=data, allow_redirects=False) as resp:
                status = resp.status
                try:
                    payload = await resp.json(content_type=None)
                except ValueError:
                    payload = None
    except (asyncio.TimeoutError, aiohttp.ClientError) as err:
        raise HomeAssistantError(f"AquaVanMatic nicht erreichbar: {err}") from err
    if status == 405:
        raise HomeAssistantError("AquaVanMatic-Firmware unterstützt noch kein POST – bitte Firmware aktualisieren")
    return status, payload if isinstance(payload, dict) else {}


def fail(what, status, payload):
    reason = payload.get("reason")
    _LOGGER.warning("AquaVanMatic %s abgelehnt: HTTP %s %s", what, status, reason)
    raise HomeAssistantError(REASONS.get(reason, f"AquaVanMatic hat abgelehnt: {reason or f'HTTP {status}'}"))
