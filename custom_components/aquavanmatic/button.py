"""Process commands, operator decision and acknowledge as buttons (REST, POST only)."""
from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .const import ACKNOWLEDGE, COMMANDS, DECISIONS, DOMAIN
from .rest import REASONS, fail, post


async def async_setup_entry(hass, entry, async_add_entities):
    state = hass.data[DOMAIN][entry.entry_id]
    entities = [AquaVanMaticButton(entry, key, label, icon)
                for key, (label, icon) in COMMANDS.items()]
    entities += [AquaVanMaticDecisionButton(entry, state, key, label, icon)
                 for key, (label, icon) in DECISIONS.items()]
    entities.append(AquaVanMaticAcknowledgeButton(entry, state, *ACKNOWLEDGE))
    async_add_entities(entities)


class _Base(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, unique_suffix, label, icon):
        self._entry = entry
        self._attr_name = label
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.unique_id}_{unique_suffix}"
        # Same identifier as MQTT Discovery -> same HA device.
        self._attr_device_info = {"identifiers": {("mqtt", entry.unique_id)}}


class _StateBound(_Base):
    """Button whose availability follows aquamatic/state/status."""

    def __init__(self, entry, state, unique_suffix, label, icon):
        super().__init__(entry, unique_suffix, label, icon)
        self._state = state

    async def async_added_to_hass(self):
        self.async_on_remove(self._state.add_listener(self.async_write_ha_state))


class AquaVanMaticButton(_Base):
    """POST /api/process/<key> -> 202 accepted / 409 reason."""

    def __init__(self, entry, key, label, icon):
        super().__init__(entry, key, label, icon)
        self._key = key

    async def async_press(self):
        status, payload = await post(self.hass, self._entry, f"/api/process/{self._key}")
        if status < 300 and payload.get("accepted") is True:
            return
        fail(f"Befehl {self._key}", status, payload)


class AquaVanMaticDecisionButton(_StateBound):
    """POST /api/decision  result=continue|abort&code=<decisionCode>."""

    def __init__(self, entry, state, key, label, icon):
        super().__init__(entry, state, f"decision_{key}", label, icon)
        self._key = key

    @property
    def available(self):
        return self._state.pending and self._state.code != 0

    @property
    def extra_state_attributes(self):
        return {"question": self._state.text, "code": self._state.code}

    async def async_press(self):
        code = self._state.code
        if not self._state.pending or not code:
            raise HomeAssistantError(REASONS["no_pending_decision"])
        status, payload = await post(self.hass, self._entry, "/api/decision",
                                     {"result": self._key, "code": str(code)})
        if status == 200 and payload.get("ok") is True:
            return
        if status == 400 and not payload.get("reason"):
            payload["reason"] = "invalid_result"
        fail(f"Entscheidung {self._key} (Code {code})", status, payload)


class AquaVanMaticAcknowledgeButton(_StateBound):
    """POST /api/acknowledge  codes=<exactly the codes shown in 'messages'>."""

    @property
    def available(self):
        return self._state.open_messages > 0 and bool(self._state.messages)

    @property
    def extra_state_attributes(self):
        return {"open_messages": self._state.open_messages, "messages": self._state.messages}

    async def async_press(self):
        codes = [m["code"] for m in self._state.messages]
        if not codes:
            raise HomeAssistantError(REASONS["nothing_acknowledged"])
        status, payload = await post(self.hass, self._entry, "/api/acknowledge",
                                     {"codes": ",".join(str(c) for c in codes)})
        if status == 200 and payload.get("ok") is True:
            return
        fail(f"Quittieren {codes}", status, payload)
