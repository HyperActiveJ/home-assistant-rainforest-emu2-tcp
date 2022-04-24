import logging
from typing import Optional, Dict, Any
from .const import (
    DOMAIN,
    ATTR_STATUS_DESCRIPTION,
    ATTR_MANUFACTURER,
)
from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_IP_ADDRESS,
    DEVICE_CLASS_POWER,
    ENERGY_KILO_WATT_HOUR,
    POWER_KILO_WATT,
    DEVICE_CLASS_ENERGY, 
)
from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
    StateType,
)
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity import DeviceInfo

import homeassistant.helpers.config_validation as cv

import voluptuous as vol
from threading import Thread


_LOGGER = logging.getLogger(__name__)

SENSORS = (
    SensorEntityDescription(
        key="EMU2:InstantaneousDemand",
        # We can drop the "EMU2-200" part of the name in HA 2021.12
        name="EMU2 Meter Power Demand",
        native_unit_of_measurement=POWER_KILO_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="EMU2:CurrentSummationDelivered",
        name="EMU2 Total Meter Energy Delivered",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="EMU2:CurrentSummationReceived",
        name="EMU2 Total Meter Energy Received",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
)


async def async_setup_entry(hass, config, async_add_entities, discovery_info=None):
    #_LOGGER.debug("Loading")
    hub_name = config.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    entities = [EMU2TCPSensor(hub_name, hub, description) for description in SENSORS]
    async_add_entities(entities)



class EMU2TCPSensor(SensorEntity):
    """Representation of an Rainforest EMU2 Eagle sensor."""

   
    def __init__(self, platform_name, hub, entity_description):
        """Initialize the sensor."""
        super().__init__()
        #_LOGGER.debug("3 EMU2TCPSensor platform_name %s name %s ", platform_name, entity_description.name) 
        self._platform_name = platform_name
        self._hub = hub
        self.entity_description = entity_description
        

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_emu2_sensor(self)


    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_emu2_sensor(self)

    @callback
    def _data_updated(self):
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """Return unique ID of entity."""
        #_LOGGER.debug("5 EMU2TCPSensor key %s ",  self.entity_description.key) 
        return f"{self.entity_description.key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        #_LOGGER.debug("5 EMU2TCPSensor available %s ",  self._hub.available()) 
        return self._hub.available()

    @property
    def native_value(self) -> StateType:
        """Return native value of the sensor."""
        #_LOGGER.debug("5 EMU2TCPSensor native_value %d ",  self._hub.test(self.entity_description.key)) 
        return self._hub.test(self.entity_description.key)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "name": self._platform_name,
            "identifiers": {(DOMAIN, self._platform_name)},
            "manufacturer": "P Jorgensen / Rainforest Automation",
            "model": "EMU2 TCP",
        }