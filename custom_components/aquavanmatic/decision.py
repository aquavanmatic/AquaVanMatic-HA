"""Tracks open decision and open messages from aquamatic/state/status."""
import json
import logging

from homeassistant.components import mqtt
from homeassistant.core import callback

from .const import SELECTS, STATUS_TOPIC

SETTING_FIELDS = [spec["field"] for spec in SELECTS]

_LOGGER = logging.getLogger(__name__)


class DecisionState:
    """decisionPending/-Code/-Text and openMessages/messages of one unit."""

    def __init__(self, hass, serial):
        self.hass = hass
        self.serial = serial
        self.pending = False
        self.code = 0
        self.text = ""
        self.open_messages = 0
        self.messages = []  # [{"code": int, "text": str}], max. 8 (firmware)
        self.settings = {}  # waterMode, waterSource, drain* (raw firmware values)
        self._listeners = set()
        self._unsub = None

    async def async_start(self):
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            _LOGGER.warning("AquaVanMatic: MQTT nicht verfügbar, Entscheidungen/Meldungen werden nicht angezeigt")
            return
        self._unsub = await mqtt.async_subscribe(self.hass, STATUS_TOPIC, self._message)

    @callback
    def async_stop(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def add_listener(self, cb):
        self._listeners.add(cb)
        return lambda: self._listeners.discard(cb)

    @callback
    def _message(self, msg):
        try:
            data = json.loads(msg.payload)
        except (ValueError, TypeError):
            return
        if not isinstance(data, dict):
            return
        # Topic has no serial: only accept messages carrying our own serial.
        if str(data.get("serial", "")) != self.serial:
            return

        if "decisionPending" in data:
            self.pending = bool(data.get("decisionPending"))
            self.code = _int(data.get("decisionCode"))
            self.text = str(data.get("decisionText") or "")

        if "openMessages" in data:
            self.open_messages = _int(data.get("openMessages"))
            msgs = []
            for item in data.get("messages") or []:
                if isinstance(item, dict) and _int(item.get("code")):
                    msgs.append({"code": _int(item.get("code")), "text": str(item.get("text") or "")})
            self.messages = msgs

        for field in SETTING_FIELDS:
            if field in data:
                self.settings[field] = str(data[field])

        for cb in list(self._listeners):
            cb()


def _int(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0
