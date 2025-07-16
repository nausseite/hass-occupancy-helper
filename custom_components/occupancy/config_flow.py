import voluptuous as vol
from typing import Any, cast
from collections.abc import Mapping
from typing import Any, cast

from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)


from .const import (
    CONF_ADVERSARIAL_OCCUPANCIES,
    CONF_MASTER_OCCUPANCY,
    CONF_NAME,
    DOMAIN,
    CONF_MOTION_SENSORS,
    CONF_DOOR_SENSORS,
    CONF_OCCUPANCY_SENSORS,
    CONF_TIMEOUT,
)


async def get_base_options_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Get base options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_MOTION_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor", device_class="motion", multiple=True
                )
            ),
            vol.Required(CONF_DOOR_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor", device_class="door", multiple=True
                )
            ),
            vol.Required(CONF_OCCUPANCY_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",device_class="occupancy",multiple=True
                )
            ),
            vol.Required(CONF_ADVERSARIAL_OCCUPANCIES): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor", device_class="occupancy", multiple=True
                )
            ),
            vol.Optional(CONF_MASTER_OCCUPANCY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor", device_class="occupancy", multiple=False
                )
            ),
            vol.Optional(CONF_TIMEOUT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=1800, step=1, unit_of_measurement="seconds"
                )
            ),
        }
    )


async def get_extended_options_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Get extended options schema."""
    return (await get_base_options_schema(handler)).extend({})


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
    }
)


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Trend."""

    config_flow = {
        "user": SchemaFlowFormStep(schema=CONFIG_SCHEMA, next_step="settings"),
        "settings": SchemaFlowFormStep(get_base_options_schema),
    }
    options_flow = {
        "init": SchemaFlowFormStep(get_extended_options_schema),
    }

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
