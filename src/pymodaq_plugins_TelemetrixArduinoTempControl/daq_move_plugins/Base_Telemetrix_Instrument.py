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
        logger.debug(f'Entering context with Base_Telemetrix_Instrument for pin {self.pin}.')
        return self  # Return the instance itself for use within the context

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug(f'Exiting context with Base_Telemetrix_Instrument for pin {self.pin}.')
        self.connection_manager.disconnect()  # Disconnect when exiting the context


if __name__ == '__main__':
    
    from thermistor_model import ThermistorModel 
    from Digital_Output_Controller import Digital_PinController  
    from Thermistor_Reader import ThermistorReader  
    
    # Setup logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    
    # Define pins and constants
    THERMISTOR_PIN = 4  # Analog pin where thermistor is connected
    DIGITAL_PIN_1 = 8     # Digital pin for relay 1
    DIGITAL_PIN_2 = 2     # Digital pin for relay 2
    THERMISTOR_25C = 10000  # Resistance at 25°C
    SERIES_RESISTOR = 10000  # Known resistor in ohms

    # Load thermistor model from CSV file
    file_path = "../../../Thermistor_R_vs_T.csv"
    resistance_column = 'Type 8016'
    thR_model = ThermistorModel(file_path, ref_R=THERMISTOR_25C, resistance_col_label=resistance_column)

    # Instantiate the thermistor reader and relay controllers
    with ThermistorReader(THERMISTOR_PIN, thR_model, series_resistor=SERIES_RESISTOR) as thermistor_reader, \
         Digital_PinController(DIGITAL_PIN_1) as relay_controller1, \
         Digital_PinController(DIGITAL_PIN_2) as relay_controller2:
        
        try:
            while True:
                # Display the temperature from the thermistor
                temperature = thermistor_reader.get_temperature()
                if temperature is not None:
                    print(f"Temperature: {temperature:.2f}°C")

                # Blink relay 1 at 0.5 Hz (2 seconds ON, 2 seconds OFF)
                relay_controller1.turn_on()
                time.sleep(.2)  # ON for 2 seconds
                relay_controller1.turn_off()
                time.sleep(.2)  # OFF for 2 seconds

                # Blink relay 2 at 1/3 Hz (3 seconds ON, 3 seconds OFF)
                relay_controller2.turn_on()
                time.sleep(.3)  # ON for 3 seconds
                relay_controller2.turn_off()
                time.sleep(.3)  # OFF for 3 seconds

                # Wait 0.5 seconds before the next temperature reading
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Session ended.")
        except Exception as e:
            logger.error(f"Error: {e}")
