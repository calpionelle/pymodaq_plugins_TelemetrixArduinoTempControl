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


class Digital_PinController(Base_Telemetrix_Instrument):
    """Controls a digital_pin connected to an Arduino through telemetrix."""
    
    def __init__(self, pin, com_port=None, ip_port=31335):
        super().__init__(com_port, ip_port)  # Call the parent constructor
        self.pin = pin
        
        logger.debug(f'Setting pin {self.pin} as digital output.')
        self.board.set_pin_mode_digital_output(self.pin)  # Set the pin as digital output
        self.state = False  # Track the state of the digital_pin (True for ON, False for OFF)
        
    def turn_on(self):
        if self.board is not None:
            logger.debug(f'Turning on digital pin {self.pin}.')
            self.board.digital_write(self.pin, 1)  # Set pin high
            self.state = True
        else:
            logger.warning('Cannot turn on: board is not connected.')

    def turn_off(self):
        if self.board is not None:
            logger.debug(f'Turning off digital pin {self.pin}.')
            self.board.digital_write(self.pin, 0)  # Set pin low
            self.state = False
        else:
            logger.warning('Cannot turn off: board is not connected.')

    def is_on(self):
        logger.debug(f'Checking if digital pin {self.pin} is ON: {self.state}')
        return self.state
    
    def __exit__(self, exc_type, exc_value, traceback):
        # logger.debug(f'Setting RelayController pin {self.pin} to low before exiting.')
        # self.turn_off()
        super().__exit__(exc_type, exc_value, traceback)  # Call the parent method

if __name__ == '__main__':
    RELAY_PIN_1 = 8  # Digital pin where digital_pin 1 is connected
    RELAY_PIN_2 = 2  # Digital pin where digital_pin 2 is connected
    
    # Frequencies for blinking (in seconds)
    frequency_digital_pin_1 = 1.0  # 1 Hz
    frequency_digital_pin_2 = 0.5  # 2 Hz

    with Digital_PinController(RELAY_PIN_1) as digital_pin_controller1:
        with Digital_PinController(RELAY_PIN_2) as digital_pin_controller2:
            try:
                while True:
                    digital_pin_controller1.turn_on()
                    time.sleep(frequency_digital_pin_1 / 2)  # Half period for ON state
                    digital_pin_controller1.turn_off()
                    time.sleep(frequency_digital_pin_1 / 2)  # Half period for OFF state
                    
                    # Blink digital_pin 2
                    digital_pin_controller2.turn_on()
                    time.sleep(frequency_digital_pin_2 / 2)  # Half period for ON state
                    digital_pin_controller2.turn_off()
                    time.sleep(frequency_digital_pin_2 / 2)  # Half period for OFF state
            except KeyboardInterrupt:
                logger.info("Session ended.")
            except Exception as e:
                logger.error(f"Error: {e}")
