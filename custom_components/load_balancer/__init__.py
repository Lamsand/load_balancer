"""Load balancer integration."""

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    config = {**entry.data, **entry.options}

    smart_meter_sensor = config.get("smart_meter_sensor")
    active_charging_load_sensor = config.get("active_charging_load_sensor")
    current_limit_entity = config.get(
        "current_limit_entity", config.get("current_limit_entity")
    )

    if not smart_meter_sensor or not current_limit_entity or not active_charging_load_sensor:
        _LOGGER.error("Required entities missing in configuration")
        return False

    if not current_limit_entity.startswith("number."):
        _LOGGER.error(
            "Current limit entity must be a number entity: %s",
            current_limit_entity,
        )
        return False

    runtime_data = {
        "calculated_surplus": 0.0,
        "calculated_current": 0.0,
        "sensor_entities": [],
        "definitively_off": True,
        "timer_disable_time": None,
        "timer_enable_time": None,
        "unsub_disable_timer": None,
        "unsub_enable_timer": None,
    }

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    mode_entity = f"select.{DOMAIN}_mode"
    max_current_entity = f"number.{DOMAIN}_max_current"
    min_current_entity = f"number.{DOMAIN}_min_current"
    custom_current_entity = f"number.{DOMAIN}_custom_current"
    enable_threshold_entity = f"number.{DOMAIN}_enable_threshold"
    disable_threshold_entity = f"number.{DOMAIN}_disable_threshold"

    def cancel_disable_timer():
        """Annuleer uitschakeltimer en wis eindtijd."""
        if runtime_data["unsub_disable_timer"]:
            runtime_data["unsub_disable_timer"]()
            runtime_data["unsub_disable_timer"] = None
        runtime_data["timer_disable_time"] = None

    def cancel_enable_timer():
        """Annuleer inschakeltimer en wis starttijd."""
        if runtime_data["unsub_enable_timer"]:
            runtime_data["unsub_enable_timer"]()
            runtime_data["unsub_enable_timer"] = None
        runtime_data["timer_enable_time"] = None

    def cancel_all_timers():
        """Annuleer alle actieve timers."""
        cancel_disable_timer()
        cancel_enable_timer()

    async def async_recalculate_and_update_current_limit():
        """Recalculate the target current limit and update its number entity."""
        meter_state = hass.states.get(smart_meter_sensor)
        if not meter_state or meter_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            power_w = float(meter_state.state)
        except ValueError:
            return

        surplus_w = max(0.0, -(power_w))
        now = datetime.now(timezone.utc)

        active_charging_load_state = hass.states.get(active_charging_load_sensor)
        if not active_charging_load_state or active_charging_load_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        try:
            active_charging_load = float(active_charging_load_state.state)
        except ValueError:
            return

        # 1. Haal UI entiteiten op
        mode_state = hass.states.get(mode_entity)
        mode = mode_state.state if mode_state and mode_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else config.get("mode", "PV")

        max_current_state = hass.states.get(max_current_entity)
        try:
            max_current = float(max_current_state.state) if max_current_state and max_current_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else float(config.get("max_current", 3000))
        except ValueError:
            max_current = float(config.get("max_current", 3000))

        min_current_state = hass.states.get(min_current_entity)
        try:
            min_current = float(min_current_state.state) if min_current_state and min_current_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else float(config.get("min_current", 3000))
        except ValueError:
            min_current = float(config.get("min_current", 3000))

        custom_current_state = hass.states.get(custom_current_entity)
        try:
            custom_current = float(custom_current_state.state) if custom_current_state and custom_current_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else float(config.get("custom_current", 20))
        except ValueError:
            custom_current = float(config.get("custom_current", 20))

        # Drempelwaardes voor inschakelen en uitschakelen (klaar voor uitbreiding)
        enable_threshold_state = hass.states.get(enable_threshold_entity)   # bijv. float(config.get("enable_threshold", 100))
        try:
            enable_threshold_w = float(enable_threshold_state.state) if enable_threshold_state and enable_threshold_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else 0
        except ValueError:
            enable_threshold_w = 0

        disable_threshold_state = hass.states.get(disable_threshold_entity)  # bijv. float(config.get("disable_threshold", 0))
        try:
            disable_threshold_w = float(disable_threshold_state.state) if disable_threshold_state and disable_threshold_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else 0
        except ValueError:
            disable_threshold_w = 0
            
        # 2. Bepaal gewenste helderheid op basis van modus
        if mode == "Off":
            cancel_all_timers()
            runtime_data["definitively_off"] = True
            current = 0.0

        elif mode == "PV":
            # VOORWAARDE 1: Aangaan!
            if power_w <= enable_threshold_w:
                cancel_disable_timer()  # Uitschakeltimer opruimen

                if runtime_data["definitively_off"]:
                    # Lamp staat uit -> controleer/start inschakelvertraging
                    timer_enable = runtime_data.get("timer_enable_time")

                    if timer_enable is None:
                        # Start een nieuwe inschakeltimer van 1 minuut
                        target_enable = now + timedelta(minutes=1)
                        runtime_data["timer_enable_time"] = target_enable
                        current = 0.0

                        @callback
                        def _enable_timer_expired(_):
                            hass.async_create_task(async_recalculate_and_update_current_limit())

                        runtime_data["unsub_enable_timer"] = async_track_point_in_time(
                            hass, _enable_timer_expired, target_enable
                        )
                    else:
                        if now < timer_enable:
                            current = 0.0
                        else:
                            # Inschakeltimer voorbij -> Lamp gaat AAN
                            cancel_enable_timer()
                            runtime_data["definitively_off"] = False
                            current = max(min_current, min(max_current, float((power_w - active_charging_load) / (-230))))
                else:
                    # Lamp is al aan -> direct helderheid schalen
                    cancel_enable_timer()
                    current = max(min_current, min(max_current, float((power_w - active_charging_load) / (-230))))

            # VOORWAARDE 2: Uitgaan
            elif power_w > disable_threshold_w:
                cancel_enable_timer()  # Inschakeltimer afbreken indien actief

                if runtime_data["definitively_off"]:
                    current = 0.0
                else:
                    # Lamp is aan -> controleer/start uitschakeltimer
                    timer_disable = runtime_data.get("timer_disable_time")

                    if timer_disable is None:
                        # Start een nieuwe uitschakeltimer van 3 minuten
                        target_disable = now + timedelta(minutes=3)
                        runtime_data["timer_disable_time"] = target_disable
                        current = min_current

                        @callback
                        def _disable_timer_expired(_):
                            hass.async_create_task(async_recalculate_and_update_current_limit())

                        runtime_data["unsub_disable_timer"] = async_track_point_in_time(
                            hass, _disable_timer_expired, target_disable
                        )
                    else:
                        if now < timer_disable:
                            current = min_current
                        else:
                            # Uitschakeltimer voorbij -> Lamp gaat UIT
                            cancel_disable_timer()
                            runtime_data["definitively_off"] = True
                            current = 0.0

            # VOORWAARDE 3: Aan of uit houden
            else:
                cancel_all_timers()
                if runtime_data["definitively_off"]:
                    current = 0.0
                else:
                    current = max(min_current, min(max_current, float((power_w - active_charging_load) / (-230))))

        elif mode == "Min+PV":
            cancel_all_timers()
            runtime_data["definitively_off"] = False
            current = max(min_current, min(max_current, float((power_w - active_charging_load) / (-230))))

        elif mode == "Fast":
            cancel_all_timers()
            runtime_data["definitively_off"] = False
            current = max_current

        elif mode == "Custom":
            cancel_all_timers()
            runtime_data["definitively_off"] = False
            if custom_current != 0.0:
                current = max(custom_current, min_current)
            else: 
                current = 0.0

        else:
            cancel_all_timers()
            current = 0.0

        # 3. Update de sensoren van de integratie
        runtime_data["calculated_surplus"] = round(surplus_w, 1)
        runtime_data["calculated_current"] = current

        for sensor in runtime_data["sensor_entities"]:
            sensor.async_write_ha_state()

        # 4. Stuur de lamp aan
        await hass.services.async_call(
            "number", "set_value", {"entity_id": current_limit_entity, "value": current},
                blocking=False,
        )

    @callback
    def state_change_listener(event):
        """Handle state change triggers safely."""
        hass.async_create_task(async_recalculate_and_update_current_limit())

    tracked_entities = [
        smart_meter_sensor,
        active_charging_load_sensor,
        mode_entity,
        max_current_entity,
        min_current_entity,
        custom_current_entity,
        enable_threshold_entity,
        disable_threshold_entity,
    ]

    unsub_track = async_track_state_change_event(hass, tracked_entities, state_change_listener)
    unsub_options = entry.add_update_listener(async_reload_entry)

    runtime_data["unsub_listeners"] = [unsub_track, unsub_options]

    hass.async_create_task(async_recalculate_and_update_current_limit())

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry and remove active state listeners."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})

    if entry_data.get("unsub_disable_timer"):
        entry_data["unsub_disable_timer"]()

    if entry_data.get("unsub_enable_timer"):
        entry_data["unsub_enable_timer"]()

    for unsub in entry_data.get("unsub_listeners", []):
        unsub()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok