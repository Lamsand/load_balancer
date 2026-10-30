"""Select entity for the load_balancer integration."""

import logging
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MODES = ["Off", "PV", "Min+PV", "Fast", "Custom"]

ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="mode",
        name="Mode",
        options=MODES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""
    async_add_entities(
        ModeSelect(hass, entry, description)
        for description in ENTITY_DESCRIPTIONS
    )


class ModeSelect(SelectEntity):
    """Select entity for mode."""

    entity_description: SelectEntityDescription

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        description: SelectEntityDescription
    ):
        """Initialize the select entity."""
        self.hass = hass
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Load Balancer",
            manufacturer="Custom",
        )
        
        config = {**entry.data, **entry.options}
        default_mode = config.get("mode", "PV")
        self._attr_current_option = default_mode
        
        _LOGGER.debug(f"ModeSelect initialized with mode {default_mode}")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.async_write_ha_state()
        _LOGGER.debug(f"Mode changed to {option}")
        
        # Schrijf de gekozen modus direct live weg naar het gedeelde geheugen
        self.hass.data[DOMAIN]["current_mode"] = option
