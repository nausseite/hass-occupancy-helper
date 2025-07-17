import asyncio
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change

from .const import (
    CONF_ADVERSARIAL_OCCUPANCIES,
    CONF_DOOR_SENSORS,
    CONF_MASTER_OCCUPANCY,
    CONF_MOTION_SENSORS,
    CONF_NAME,
    CONF_OCCUPANCY_SENSORS,
    CONF_TIMEOUT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)


class OccupancyDevice:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass

        self.motion_sensors = entry.options.get(CONF_MOTION_SENSORS, [])
        self.door_sensors = entry.options.get(CONF_DOOR_SENSORS, [])
        self.occupancy_sensors = entry.options.get(CONF_OCCUPANCY_SENSORS, [])
        self.adversarial_occupancies = entry.options.get(
            CONF_ADVERSARIAL_OCCUPANCIES, []
        )
        self.master_occupancy = entry.options.get(CONF_MASTER_OCCUPANCY, None)
        self.timeout = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        self.device_name = entry.options.get(CONF_NAME)
        self.device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self.device_name,
        }

        self._state_change_listeners: list[Callable] = []
        self._is_occupied = False
        self.override = False
        self._off_handle = None
        self._lockout_handle = None

        # region Subscriptions
        self._motion_sensor_unsub = None
        self._door_sensor_unsub = None
        self._occupancy_sensor_unsub = None
        self._adversarial_occupancy_unsub = None
        self._master_occupancy_unsub = None
        # endregion

        self.lockout = False

    _desired_state = None

    def _set_desired_state(self, state: bool, check_lockout: bool = True):
        if self.override or (check_lockout and self.lockout):
            return
        self._desired_state = state

        master = self.hass.states.get(self.master_occupancy)
        if master and master.state != "on":
            self.is_occupied = False
            return

        if self._adversarial_occupancy_detected() or self._desired_state is True:
            self.is_occupied = self._desired_state

    def _adversarial_occupancy_detected(self):
        """Check if any adversarial occupancy sensors are triggered."""
        if not self.adversarial_occupancies or len(self.adversarial_occupancies) == 0:
            return True  # No adversarial sensors configured, assume safe
        return any(
            self.hass.states.get(sensor).state == "on"
            for sensor in self.adversarial_occupancies
        )

    def _doors_closed(self):
        if not self.door_sensors or len(self.door_sensors) == 0:
            return False
        return all(
            self.hass.states.get(sensor).state == "off" for sensor in self.door_sensors
        )

    async def _motion_sensor_callback(self, entity_id, old_state, new_state):
        if new_state is None or new_state.state != "on":
            return

        self.motion_detected = True
        self._set_desired_state(True)
        self._start_off_timer()

    async def _door_sensor_callback(self, entity_id, old_state, new_state):
        if new_state is None:
            return
        if new_state.state == "on":
            # if any door is opened, reset the lockout
            self.lockout = False
            self._notify_state_change_listeners()
            self._set_desired_state(True)
            self._start_off_timer()
        self._cancel_lockout_timer()
        if self._doors_closed():
            # If all doors are closed, start the lockout timer
            self._start_lockout_timer()

    async def _occupancy_sensor_callback(self, entity_id, old_state, new_state):
        pass

    async def _adversarial_occupancy_callback(self, entity_id, old_state, new_state):
        if new_state is None or new_state.state != "on":
            return

        # If any adversarial occupancy sensor is on and our desired state is Off we can safely set the occupancy now
        self._set_desired_state(self._desired_state)

    async def _master_occupancy_callback(self, entity_id, old_state, new_state):
        if self.override:
            return

        if new_state.state == "on":
            # set occupancy to desired state if master occupancy is on
            self._set_desired_state(self._desired_state)
        else:
            # always turn off occupancy if master occupancy is off
            self.is_occupied = False

    # region pir timer
    async def _delayed_off(self):
        await asyncio.sleep(self.timeout)
        self._set_desired_state(False)

    def _start_off_timer(self):
        if self._off_handle:
            self._off_handle.cancel()
        self._off_handle = asyncio.create_task(self._delayed_off())

    def _cancel_off_timer(self):
        if self._off_handle:
            self._off_handle.cancel()
            self._off_handle = None

    # endregion

    # region lockout timer
    async def _delayed_lockout(self):
        # Reset the motion_detected flag and wait for the timeout
        self.motion_detected = False
        await asyncio.sleep(self.timeout)
        # Activate lockout mode
        self.lockout = True
        self._notify_state_change_listeners()
        # set occupancy based on if we saw any motion during the lockout period
        if self.motion_detected:
            self._set_desired_state(True, check_lockout=False)
        else:
            self._set_desired_state(False, check_lockout=False)

    def _start_lockout_timer(self):
        if self._lockout_handle:
            self._lockout_handle.cancel()
        self._lockout_handle = asyncio.create_task(self._delayed_lockout())

    def _cancel_lockout_timer(self):
        if self._lockout_handle:
            self._lockout_handle.cancel()
            self._lockout_handle = None

    # endregion

    @property
    def is_occupied(self):
        return self._is_occupied

    @is_occupied.setter
    def is_occupied(self, value):
        self._desired_state = value
        self._is_occupied = value
        self._notify_state_change_listeners()

    def add_state_change_listener(self, listener):
        """Add a listener to be notified when the state changes."""
        self._state_change_listeners.append(listener)

    def _notify_state_change_listeners(self):
        """Notify all registered listeners of a state change."""
        for listener in self._state_change_listeners:
            listener()

    # region Start and Stop
    async def async_start(self):
        self._motion_sensor_unsub = async_track_state_change(
            self.hass, self.motion_sensors, self._motion_sensor_callback
        )
        self._door_sensor_unsub = async_track_state_change(
            self.hass, self.door_sensors, self._door_sensor_callback
        )
        self._occupancy_sensor_unsub = async_track_state_change(
            self.hass, self.occupancy_sensors, self._occupancy_sensor_callback
        )
        self._adversarial_occupancy_unsub = async_track_state_change(
            self.hass,
            self.adversarial_occupancies,
            self._adversarial_occupancy_callback,
        )
        if self.master_occupancy:
            self._master_occupancy_unsub = async_track_state_change(
                self.hass, self.master_occupancy, self._master_occupancy_callback
            )

    def stop(self):
        if self._motion_sensor_unsub:
            self._motion_sensor_unsub()
            self._motion_sensor_unsub = None
        if self._door_sensor_unsub:
            self._door_sensor_unsub()
            self._door_sensor_unsub = None
        if self._occupancy_sensor_unsub:
            self._occupancy_sensor_unsub()
            self._occupancy_sensor_unsub = None
        if self._adversarial_occupancy_unsub:
            self._adversarial_occupancy_unsub()
            self._adversarial_occupancy_unsub = None
        if self._master_occupancy_unsub:
            self._master_occupancy_unsub()
            self._master_occupancy_unsub = None
        self._cancel_off_timer()
        self._cancel_lockout_timer()
        self._state_change_listeners.clear()

    # endregion
