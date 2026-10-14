"""Usage and water path as select entities.

State comes from aquamatic/state/status, setting goes via REST (POST).
After setting, the state is NOT assumed: the unit sends a new status
message immediately, which updates the entity.
"""
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, SELECTS
from .rest import fail, post


async def async_setup_entry(hass, entry, async_add_entities):
    state = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AquaVanMaticSelect(entry, state, spec) for spec in SELECTS)


class AquaVanMaticSelect(SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, state, spec):
        self._entry = entry
        self._state = state
        self._spec = spec
        self._attr_name = spec["name"]
        self._attr_icon = spec["icon"]
        self._attr_unique_id = f"{entry.unique_id}_{spec['key']}"
        self._attr_device_info = {"identifiers": {("mqtt", entry.unique_id)}}
        self._attr_options = list(spec["options"].values())
        self._to_value = {label: value for value, label in spec["options"].items()}

    @property
    def available(self):
        return self._state.settings.get(self._spec["field"]) in self._spec["options"]

    @property
    def current_option(self):
        return self._spec["options"].get(self._state.settings.get(self._spec["field"]))

    @property
    def extra_state_attributes(self):
        return {"hint": self._spec["hint"]} if self._spec.get("hint") else None

    async def async_added_to_hass(self):
        self.async_on_remove(self._state.add_listener(self.async_write_ha_state))

    async def async_select_option(self, option):
        value = self._to_value.get(option)
        if value is None:
            raise HomeAssistantError(f"Unbekannte Auswahl: {option}")
        if self._spec["options"].get(self._state.settings.get(self._spec["field"])) == option:
            return
        try:
            status, payload = await post(self.hass, self._entry, self._spec["path"],
                                         self._spec["data"](value))
            if status == 200 and payload.get("ok") is True:
                return  # new state arrives via MQTT status message
            fail(f"{self._spec['name']} = {value}", status, payload)
        finally:
            # On rejection the UI falls back to the real state of the unit.
            self.async_write_ha_state()
