"""Config flow for brightness_from_surplus integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN


def get_data_schema(defaults: dict) -> vol.Schema:
    """Generate the schema without any default values."""
    if not isinstance(defaults, dict):
        defaults = {}

    return vol.Schema(
        {
            vol.Required("smart_meter_sensor"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required("lamp_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light")
            ),
            vol.Optional("max_surplus"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=5000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("min_current"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=32.0, step=0.1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("mode"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["Off", "PV", "Min+PV", "Fast", "Custom"],
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Optional("custom_minimum"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
        }
    )


class BrightnessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for brightness_from_surplus."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Brightness from Surplus",
                data=user_input,
            )

        schema = get_data_schema({})
        return self.async_show_form(step_id="user", data_schema=schema)