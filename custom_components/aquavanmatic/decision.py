"""Tracks open decision and open messages from aquamatic/state/status."""
import json
import logging
import time
from datetime import timedelta

from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval

from .const import SELECTS, STATUS_TOPIC

SETTING_FIELDS = [spec["field"] for spec in SELECTS]

_LOGGER = logging.getLogger(__name__)

# Firmware publishes aquamatic/state/status on every change, otherwise every 30 s.
STALE_AFTER = 90  # seconds without a live message -> unit regarded as unreachable


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
        self._unsub_timer = None
        self._last_seen = 0.0

    async def async_start(self):
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            _LOGGER.warning("AquaVanMatic: MQTT nicht verfügbar, Entscheidungen/Meldungen werden nicht angezeigt")
            return
        self._unsub = await mqtt.async_subscribe(self.hass, STATUS_TOPIC, self._message)
        self._unsub_timer = async_track_time_interval(
            self.hass, self._check_stale, timedelta(seconds=30))

    @callback
    def async_stop(self):
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @property
    def online(self):
        return bool(self._last_seen) and time.monotonic() - self._last_seen < STALE_AFTER

    @callback
    def _check_stale(self, _now=None):
        """No live status for STALE_AFTER s -> forget decision, messages, settings."""
        if self._last_seen and not self.online:
            _LOGGER.info("AquaVanMatic %s: seit %s s keine Statusnachricht, gilt als nicht erreichbar",
                         self.serial, STALE_AFTER)
            self._last_seen = 0.0
            self.pending, self.code, self.text = False, 0, ""
            self.open_messages, self.messages = 0, []
            self.settings = {}
            self._notify()

    @callback
    def _notify(self):
        for cb in list(self._listeners):
            cb()

    @callback
    def add_listener(self, cb):
        self._listeners.add(cb)
        return lambda: self._listeners.discard(cb)

    @callback
    def _message(self, msg):
        # A retained message may be old (unit switched off, other board ...).
        # Only live messages count; the next live one arrives within 30 s.
        if getattr(msg, "retain", False):
            return
        try:
            data = json.loads(msg.payload)
        except (ValueError, TypeError):
            return
        if not isinstance(data, dict):
            return
        # Topic has no serial: only accept messages carrying our own serial.
        if str(data.get("serial", "")) != self.serial:
            return
        self._last_seen = time.monotonic()

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

        self._notify()


def _int(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0
