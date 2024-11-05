# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 17:18:43 2024

@author: gaignebet
"""
import time
import logging

from Base_Telemetrix_Instrument import Base_Telemetrix_Instrument
# Setup logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG level for detailed output
logger = logging.getLogger(__name__)


class RelayController(Base_Telemetrix_Instrument):
    """Controls a relay connected to an Arduino through telemetrix."""
    
    def __init__(self, pin, com_port=None, ip_port=31335):
        super().__init__(com_port, ip_port)  # Call the parent constructor
        self.pin = pin
        
        logger.debug(f'Setting pin {self.pin} as digital output.')
        self.board.set_pin_mode_digital_output(self.pin)  # Set the pin as digital output
        self.state = False  # Track the state of the relay (True for ON, False for OFF)
        
    def turn_on(self):
        if self.board is not None:
            logger.debug(f'Turning on relay connected to pin {self.pin}.')
            self.board.digital_write(self.pin, 1)  # Set pin high
            self.state = True
        else:
            logger.warning('Cannot turn on: board is not connected.')

    def turn_off(self):
        if self.board is not None:
            logger.debug(f'Turning off relay connected to pin {self.pin}.')
            self.board.digital_write(self.pin, 0)  # Set pin low
            self.state = False
        else:
            logger.warning('Cannot turn off: board is not connected.')

    def is_on(self):
        logger.debug(f'Checking if relay on pin {self.pin} is ON: {self.state}')
        return self.state

if __name__ == '__main__':
    RELAY_PIN_1 = 8  # Digital pin where relay 1 is connected
    RELAY_PIN_2 = 2  # Digital pin where relay 2 is connected
    
    # Frequencies for blinking (in seconds)
    frequency_relay_1 = 1.0  # 1 Hz
    frequency_relay_2 = 0.5  # 2 Hz

    with RelayController(RELAY_PIN_1) as relay_controller1:
        with RelayController(RELAY_PIN_2) as relay_controller2:
            try:
                while True:
                    relay_controller1.turn_on()
                    time.sleep(frequency_relay_1 / 2)  # Half period for ON state
                    relay_controller1.turn_off()
                    time.sleep(frequency_relay_1 / 2)  # Half period for OFF state
                    
                    # Blink relay 2
                    relay_controller2.turn_on()
                    time.sleep(frequency_relay_2 / 2)  # Half period for ON state
                    relay_controller2.turn_off()
                    time.sleep(frequency_relay_2 / 2)  # Half period for OFF state
            except KeyboardInterrupt:
                logger.info("Session ended.")
            except Exception as e:
                logger.error(f"Error: {e}")
