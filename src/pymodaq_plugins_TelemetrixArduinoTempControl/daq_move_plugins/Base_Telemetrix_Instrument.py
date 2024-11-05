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

class Base_Telemetrix_Instrument:
    """Base class to manage the connection to the telemetrix board as a singleton."""
    
    _connection_manager = None  # Singleton instance of ConnectionManager

    class ConnectionManager:
        """Manages the connection to the telemetrix board."""
        
        def __init__(self, com_port, ip_port):
            self.board = None
            self.reference_count = 0
            self.com_port = com_port
            self.ip_port = ip_port

        def connect(self):
            if self.reference_count == 0:
                logger.debug('Establishing connection with Arduino...')
                self.board = telemetrix.Telemetrix(com_port=self.com_port, ip_port=self.ip_port)
            self.reference_count += 1
            logger.debug(f'Current connection reference count: {self.reference_count}')

        def disconnect(self):
            if self.reference_count > 0:
                self.reference_count -= 1
                logger.debug(f'Decreasing reference count: {self.reference_count}')
                if self.reference_count == 0 and self.board is not None:
                    logger.debug('Closing Arduino connection...')
                    self.board.shutdown()
                    self.board = None

    def __init__(self, com_port, ip_port):
        # Initialize the connection manager if it doesn't exist
        if Base_Telemetrix_Instrument._connection_manager is None:
            Base_Telemetrix_Instrument._connection_manager = Base_Telemetrix_Instrument.ConnectionManager(com_port, ip_port)
        self.connection_manager = Base_Telemetrix_Instrument._connection_manager
        self.connection_manager.connect()  # Automatically connect upon base class initialization
        self.board = self.connection_manager.board

    def __del__(self):
        self.connection_manager.disconnect()
    
    def __enter__(self):
        logger.debug(f'Entering context with RelayController for pin {self.pin}.')
        return self  # Return the instance itself for use within the context

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug(f'Exiting context with RelayController for pin {self.pin}.')
        self.connection_manager.disconnect()  # Disconnect when exiting the context


if __name__ == '__main__':
    
    from Digital_Output_Controller import Digital_PinController
    RELAY_PIN_1 = 8  # Digital pin where relay 1 is connected
    RELAY_PIN_2 = 2  # Digital pin where relay 2 is connected
    
    # Frequencies for blinking (in seconds)
    frequency_relay_1 = 1.0  # 1 Hz
    frequency_relay_2 = 0.5  # 2 Hz

    logger.debug('Starting multiple digital pins control test.')

    with Digital_PinController(RELAY_PIN_1) as relay_controller1:
        with Digital_PinController(RELAY_PIN_2) as relay_controller2:
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