"""Binary sensor platform for the load_balancer integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="above_absolute_upper_bound",
        name="Above Absolute Upper Bound",
        icon="mdi:alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    async_add_entities(
        LoadBalancerBinarySensorEntity(hass, entry, description)
        for description in ENTITY_DESCRIPTIONS
    )


class LoadBalancerBinarySensorEntity(BinarySensorEntity):
    """Representation of a load balancer binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Load Balancer",
            manufacturer="Custom",
        )

        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id]["entities_to_update"].append(self)

    @property
    def is_on(self) -> bool:
        """Return whether the absolute upper bound has been exceeded."""
        return self.hass.data[DOMAIN][self.entry.entry_id].get(
            self.entity_description.key, False
        )
