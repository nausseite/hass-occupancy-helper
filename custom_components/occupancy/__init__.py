from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .device import OccupancyDevice


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.entry_id in hass.data[DOMAIN]:
        raise ValueError(
            f"Config entry {entry.title} ({entry.entry_id}) for {DOMAIN} has already been setup!"
        )

    hass.data.setdefault(DOMAIN, {})

    device = OccupancyDevice(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = {"device": device}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    await device.async_start()

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.entry_id not in hass.data[DOMAIN]:
        return False

    # Stop the device and clean up
    entry_data = hass.data[DOMAIN].pop(entry.entry_id)
    entry_data["device"].stop()

    # Unload platforms
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return True
