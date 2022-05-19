import asyncio
import socket
import logging
import os.path
import time
import voluptuous as vol

from homeassistant.components.water_heater import WaterHeaterEntity, PLATFORM_SCHEMA, STATE_ELECTRIC, SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE,ATTR_OPERATION_MODE

from homeassistant.const import (
    CONF_NAME, STATE_ON, STATE_UNKNOWN, ATTR_TEMPERATURE, PRECISION_WHOLE, STATE_OFF)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity


COMPONENT_ABS_DIR = os.path.dirname(
  os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)

CONF_UNIQUE_ID = 'unique_id'
CONF_NAME = 'name'
CONF_HOST = 'host'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_UNIQUE_ID): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    host=config.get(CONF_HOST)
    async_add_entities([ZanussiWH(
        hass, config, {}
    )])    


class ZanussiWH(WaterHeaterEntity, RestoreEntity):
    def __init__(self, hass, config, device_data):
        self._host=config.get(CONF_HOST)
        self.hass = hass
        self._attr_unique_id
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._manufacturer = 'Zanussi'
        self._supported_models = ['Centurio 2.0']
        self._min_temp = 35
        self._max_temp = 75
        self._attr_precision = PRECISION_WHOLE

        self._target_temperature = self._min_temp
        self._operation_list = [
            'OFF',
            '700W',
            '1200W',
            '2000W'
        ]
        self._current_operation = 'OFF'

        self._last_on_operation = None
        self._current_temperature = None

        self._unit = hass.config.units.temperature_unit

        self._temp_lock = asyncio.Lock()

        _LOGGER.warning('zanussi_wh_init_ok!')

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
    
        last_state = await self.async_get_last_state()
        
        if last_state is not None:
            self._target_temperature = last_state.attributes['temperature']

            if 'last_on_operation' in last_state.attributes:
                self._last_on_operation = last_state.attributes['last_on_operation']

    @property
    def max_temp(self):
        """Return the polling state."""
        return self._max_temp

    @property
    def min_temp(self):
        """Return the polling state."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the polling state."""
        return self._max_temp

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def current_operation(self):
        """ return current operation mode"""
        return self._current_operation

    @property
    def operation_list(self):
        return self._operation_list

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_OPERATION_MODE | SUPPORT_TARGET_TEMPERATURE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self._current_operation==self.operation_list[0]:
            return STATE_OFF
        return STATE_ELECTRIC

    @property
    def last_on_operation(self):
        """Return the last non-idle operation ie. heat, cool."""
        return self._last_on_operation

    @property
    def device_state_attributes(self) -> dict:
        """Platform specific attributes."""
        return {
            'last_on_operation': self._last_on_operation,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
        }

    def set_operation_mode(self, **kwargs):
        _LOGGER.warning(**kwargs)

    async def async_set_operation_mode(self, **kwargs):
        operation_mode = kwargs.get(ATTR_OPERATION_MODE)
        _LOGGER.warning(operation_mode)
        if operation_mode not in self._operation_list:
            return
        self._current_operation = operation_mode
        await self.send_command()
        return
        pass

    def set_temperature(self, **kwargs):
        _LOGGER.warning(**kwargs)
        pass

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = round(kwargs.get(ATTR_TEMPERATURE))
        self._target_temperature = temperature
        _LOGGER.warning(temperature)
        if not self._current_operation==self.operation_list[0]:
            await self.send_command()

    async def make_packet(self,data):
        crc = (await self.checksum(data)).decode("utf-8")
        return (f'{data}{crc}')

    async def checksum(self, the_bytes):
        the_bytes = bytes.fromhex(the_bytes)
        return b'%02X' % (sum(the_bytes) & 0xFF)

    async def send_command(self):
        async with self._temp_lock:
            target_temperature = round(self._target_temperature)
            if  self._current_operation == self.operation_list[0]:
                mode = '00'
            else:
                mode = '{:02}'.format(self.operation_list.index(self._current_operation))
            # aa 04 0a 00 01 4b 04 (turn on and set temp to 75)
            packet = await self.make_packet(f'aa040a00{mode}{format(target_temperature, "x")}')
            try:
                await self.send(packet)
            except Exception as e:
                _LOGGER.exception(e)

    async def send(self, packet):
        for i in range(2):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self._host, 8899))
                s.send(bytes.fromhex(packet))
            s.close()
            time.sleep(1)

    async def async_turn_on(self):
        if not self._current_operation==self.operation_list[0]:
            await self.send_command()



