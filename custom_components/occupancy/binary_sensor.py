import asyncio

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.util import slugify

from .const import DOMAIN
from .device import OccupancyDevice


async def async_setup_entry(hass, entry, async_add_entities):
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities([Occupancy(entry, device), Lockout(entry, device)])


class Occupancy(BinarySensorEntity):
    def __init__(self, entry, device: OccupancyDevice):
        self.device = device

        self._attr_name = f"Occupancy"
        self._attr_unique_id = f"{entry.entry_id}_sensor"
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY

        self.device.add_state_change_listener(self._on_device_state_change)

    @property
    def suggested_object_id(self):
        return f"occupancy_{slugify(self.device.device_name)}"

    @property
    def device_info(self):
        return self.device.device_info

    @property
    def is_on(self):
        return self.device.is_occupied

    def _on_device_state_change(self):
        """Callback for when the device state changes."""
        self.async_schedule_update_ha_state()


class Lockout(BinarySensorEntity):
    def __init__(self, entry, device: OccupancyDevice):
        self.device = device

        self._attr_name = f"Lockout"
        self._attr_unique_id = f"{entry.entry_id}_lockout"

        self.device.add_state_change_listener(self._on_device_state_change)

    @property
    def suggested_object_id(self):
        return f"occupancy_{slugify(self.device.device_name)}_lockout"

    @property
    def device_info(self):
        return self.device.device_info

    @property
    def is_on(self):
        return self.device.lockout

    def _on_device_state_change(self):
        """Callback for when the device state changes."""
        self.async_schedule_update_ha_state()
