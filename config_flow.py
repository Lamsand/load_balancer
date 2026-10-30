"""Config flow for load_balancer integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN


def get_data_schema() -> vol.Schema:
    """Generate the schema without any default values."""
    return vol.Schema(
        {
            vol.Required("smart_meter_sensor"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required("active_charging_load_sensor"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required("current_limit_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")
            ),
            vol.Optional("max_current"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=32.0, step=0.1, mode=selector.NumberSelectorMode.BOX)
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
            vol.Optional("custom_current"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=32.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER)
            ),
        }
    )


class LoadBalancerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for load_balancer."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Load balancer",
                data=user_input,
            )

        schema = get_data_schema()
        return self.async_show_form(step_id="user", data_schema=schema)