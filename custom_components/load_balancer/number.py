"""Number entity for the load_balancer integration."""

import logging
from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="max_current",
        name="Max Current",
        native_unit_of_measurement="A",
        native_min_value=0.0,
        native_max_value=32.0,
        native_step=0.1,
        icon="mdi:flash",
    ),
    NumberEntityDescription(
        key="min_current",
        name="Min Current",
        native_unit_of_measurement="A",
        native_min_value=0.0,
        native_max_value=32.0,
        native_step=0.1,
        icon="mdi:flash",
    ),
    NumberEntityDescription(
        key="custom_current",
        name="Custom Current",
        native_unit_of_measurement="A",
        native_min_value=0.0,
        native_max_value=32.0,
        native_step=0.1,
        icon="mdi:flash-outline",
    ),
    NumberEntityDescription(
        key="absolute_upper_bound",
        name="Absolute upper bound",
        native_unit_of_measurement="W",
        native_min_value=0,
        native_max_value=12000,
        native_step=10,
        icon="mdi:flash",
    ),
    NumberEntityDescription(
        key="enable_threshold",
        name="Enable threshold",
        native_unit_of_measurement="W",
        native_min_value=-2000,
        native_max_value=0,
        native_step=1,
        icon="mdi:scale-balance",
    ),
    NumberEntityDescription(
        key="disable_threshold",
        name="Disable threshold",
        native_unit_of_measurement="W",
        native_min_value=-500,
        native_max_value=1000,
        native_step=1,
        icon="mdi:scale-balance",
    ),
)

DEFAULT_VALUES = {
    "max_current": 0.0,
    "min_current": 6.0,
    "custom_current": 0.0,
    "absolute_upper_bound": 12000.0,
    "enable_threshold": 0.0,
    "disable_threshold": 0.0,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    _LOGGER.debug("Setting up number platform")

    async_add_entities(
        LoadBalancerNumberEntity(hass, entry, description)
        for description in ENTITY_DESCRIPTIONS
    )


class LoadBalancerNumberEntity(RestoreNumber):
    """Generic number entity for the load_balancer integration."""

    entity_description: NumberEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: NumberEntityDescription,
    ):
        """Initialize the number entity."""
        self.hass = hass
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Load Balancer",
            manufacturer="Custom",
        )

        # Look into entry data AND options seamlessly
        config = {**entry.data, **entry.options}

        default = config.get(description.key, DEFAULT_VALUES[description.key])
        self._attr_native_value = float(default)

        # Seed the shared runtime dictionary right away so __init__.py has it on boot
        if DOMAIN in self.hass.data:
            self.hass.data[DOMAIN][f"current_{description.key}"] = float(default)

    async def async_added_to_hass(self) -> None:
        """Restore the last value when one was saved by Home Assistant."""
        await super().async_added_to_hass()

        if (last_number_data := await self.async_get_last_number_data()) is not None:
            if last_number_data.native_value is not None:
                self._attr_native_value = last_number_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
        _LOGGER.info(f"{self.entity_description.name} changed to {value}")

        # Safely store into shared runtime state
        if DOMAIN in self.hass.data:
            self.hass.data[DOMAIN][f"current_{self.entity_description.key}"] = value
