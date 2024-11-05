# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 17:18:43 2024

@author: gaignebet
"""
import time
from telemetrix import telemetrix
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG level for detailed output
logger = logging.getLogger(__name__)

class RelayController:
    
    def __init__(self, pin, board=None, com_port=None, ip_port=31335):
        self.pin = pin
        self.board = board
        self.com_port = com_port
        self.ip_port = ip_port
        self.state = False  # Track the state of the relay (True for ON, False for OFF)

    def open_connection(self):
        if self.board is None:
            logger.debug('Establishing connection with Arduino...')
            self.board = telemetrix.Telemetrix(com_port=self.com_port, ip_port=self.ip_port)
        elif not isinstance(self.board, telemetrix.Telemetrix):
            raise ConnectionError("Invalid board instance provided.")
        
        logger.debug(f'Setting pin {self.pin} as digital output.')
        self.board.set_pin_mode_digital_output(self.pin)  # Set the pin as digital output

    def close_connection(self):
        logger.debug('Closing Arduino connection...')
        if self.board:
            self.board.shutdown()

    def __enter__(self):
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()
        
    def turn_on(self):
        logger.debug(f'Turning on relay connected to pin {self.pin}.')
        self.board.digital_write(self.pin, 1)  # Set pin high
        self.state = True

    def turn_off(self):
        logger.debug(f'Turning off relay connected to pin {self.pin}.')
        self.board.digital_write(self.pin, 0)  # Set pin low
        self.state = False

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
        with RelayController(RELAY_PIN_2, board = relay_controller1.board) as relay_controller2:
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
