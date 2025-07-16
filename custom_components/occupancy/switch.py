from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .device import OccupancyDevice


async def async_setup_entry(hass, entry, async_add_entities):
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities([OverrideSwitch(entry, device), StateSwitch(entry, device)])

class OverrideSwitch(RestoreEntity, SwitchEntity):
    def __init__(self, entry, device: OccupancyDevice):
        self.device = device

        self._attr_name = f"Override"
        self._attr_unique_id = f"{entry.entry_id}_override"

        self.device.override = False

    @property
    def suggested_object_id(self):
        return f"occupancy_{slugify(self.device.device_name)}_override"

    @property
    def device_info(self):
        return self.device.device_info

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state:
            self.device.override = last_state.state == "on"
        else:
            self.device.override = False
        self.async_schedule_update_ha_state()

    @property
    def is_on(self):
        return self.device.override

    async def async_turn_on(self, **kwargs):
        self.device.override = True
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        self.device.override = False
        self.async_schedule_update_ha_state()

class StateSwitch(RestoreEntity, SwitchEntity):
    def __init__(self, entry, device: OccupancyDevice):
        self.device = device

        self._attr_name = f"Occupancy"
        self._attr_unique_id = f"{entry.entry_id}_state"

        self.device.is_occupied = False
        self.device.add_state_change_listener(self._on_device_state_change)

    @property
    def suggested_object_id(self):
        return f"occupancy_{slugify(self.device.device_name)}"


    @property
    def device_info(self):
        return self.device.device_info

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state:
            self.device.is_occupied = last_state.state == "on"
        else:
            self.device.is_occupied = False
        self.async_schedule_update_ha_state()

    @property
    def is_on(self):
        return self.device.is_occupied

    async def async_turn_on(self, **kwargs):
        self.device.is_occupied = True
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        self.device.is_occupied = False
        self.async_schedule_update_ha_state()

    def _on_device_state_change(self):
        """Callback for when the device state changes."""
        self.async_schedule_update_ha_state()

