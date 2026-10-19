"""Find AquaVanMatic devices that MQTT Discovery has already registered."""
import logging
from urllib.parse import urlsplit

from homeassistant.helpers import device_registry as dr

from .const import PREFIX

_LOGGER = logging.getLogger(__name__)


def find_devices(hass):
    """Yield (identifier, url) for every MQTT device with an aquamatic_ identifier."""
    registry = dr.async_get(hass)
    # Neuere HA-Versionen liefern beim Iterieren die Geräte selbst, ältere nur die IDs.
    for item in registry.devices:
        device = registry.async_get(item) if isinstance(item, str) else item
        if device is None:
            continue
        ids = [value for domain, value in device.identifiers
               if domain == "mqtt" and value.startswith(PREFIX)]
        if not ids:
            continue
        url = device.configuration_url
        if not url:
            _LOGGER.debug("AquaVanMatic %s: noch keine configuration_url", ids[0])
            continue
        parsed = urlsplit(url)
        if parsed.scheme != "http" or not parsed.hostname:
            continue
        _LOGGER.debug("AquaVanMatic gefunden: %s, REST-Adresse: %s", ids[0], url)
        yield ids[0], url
