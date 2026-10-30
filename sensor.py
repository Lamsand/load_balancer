"""Sensor platform for brightness_from_surplus integration."""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="calculated_surplus",
        name="Calculated Solar Surplus",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
    ),
    SensorEntityDescription(
        key="calculated_brightness_percent",
        name="Calculated Lamp Percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:file-percent",
    ),
    SensorEntityDescription(
        key="timer_disable_time",
        name="Surplus Timer Disable",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:weather-sunset-down",
    ),
    SensorEntityDescription(
        key="timer_enable_time",
        name="Surplus Timer Enable",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:weather-sunset-up",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    _LOGGER.debug("Setting up sensor platform")
    
    async_add_entities(
        BrightnessSensorEntity(hass, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BrightnessSensorEntity(SensorEntity):
    """Representation of a calculation sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        description: SensorEntityDescription
    ):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"
        
        # Koppel aan hetzelfde apparaat als de rest
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Brightness from Surplus",
            manufacturer="Custom",
        )
        
        # Voeg deze entiteit toe aan de live-update lijst in __init__.py
        if DOMAIN in self.hass.data and entry.entry_id in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][entry.entry_id]["sensor_entities"].append(self)

    @property
    def native_value(self) -> float:
        """Haal de live berekende waarde op uit de centrale data map."""
        try:
            return self.hass.data[DOMAIN][self.entry.entry_id].get(self.entity_description.key, 0.0)
        except KeyError:
            return 0.0
