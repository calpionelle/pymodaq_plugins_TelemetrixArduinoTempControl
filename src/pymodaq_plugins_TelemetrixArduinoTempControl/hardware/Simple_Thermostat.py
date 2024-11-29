# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:09:35 2024

@author: gaignebet
"""

import time
import logging
from datetime import datetime
from thermistor_model import ThermistorModel
from Thermistor_Reader import ThermistorReader
from Digital_Output_Controller import Digital_PinController
import os

# Define constants
THERMISTOR_PIN_HEATER = 0        # Analog pin for the heater thermistor
THERMISTOR_PIN_COOLER = 1        # Analog pin for the cooler thermistor (e.g., A0)
DIGITAL_PIN_HEATER = 2           # Digital pin to control the heater
DIGITAL_PIN_COOLER = 4           # Digital pin to control the cooler
TEMP_THRESHOLD_HEATER = 25.0     # Heater activation threshold in °C
TEMP_THRESHOLD_COOLER = 26.0     # Cooler activation threshold in °C
SERIES_RESISTOR_HEATER = 13000   # Series resistor for the heater thermistor in ohms
SERIES_RESISTOR_COOLER = 13000   # Series resistor for the cooler thermistor in ohms
THERMISTOR_25C = 10000           # Resistance of the thermistor at 25°C
MIN_TIME = 5.0                   # Minimum time interval between pin state changes in seconds

# Define a logger setup function
def setup_logger(logger_name, log_file, level=logging.DEBUG):
    # Configure logger
    l = logging.getLogger(logger_name)
    
    # Remove any existing handlers
    for handler in l.handlers[:]:
        l.removeHandler(handler)
    
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt="%Y.%m.%d-%H:%M:%S")
    
    # File handler for all messages, including DEBUG
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setLevel(logging.DEBUG)  # Log all levels to the file
    fileHandler.setFormatter(formatter)
    
    # Stream handler (console output) for WARNING and above
    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)  # Only WARNING and above to console
    streamHandler.setFormatter(formatter)
    
    # Set logger level to DEBUG so that file captures all levels
    l.setLevel(logging.DEBUG)
    
    # Add handlers to the logger
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)
    
    return l


# Define log directory and file path
log_directory = os.path.join(os.getcwd(), "logs")  
os.makedirs(log_directory, exist_ok=True)  # Create directory if it doesn't exist

# Log file path with timestamp
log_file_path = os.path.join(log_directory, f"temperature_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Initialize logger
logger = setup_logger('TemperatureLogger', log_file_path, level=logging.DEBUG)
logger.info("Logger initialized. Temperature monitoring started.")

# Initialize thermistor models and readers
file_path = "../../../Thermistor_R_vs_T.csv"
resistance_column = 'Type 8016'  # Adjust based on your thermistor data
thR_model = ThermistorModel(file_path, ref_R=THERMISTOR_25C, resistance_col_label=resistance_column)

logger.info(f"Using a heater thermistor of type {resistance_column}, with ref resistance {THERMISTOR_25C} ohm, and series resistor {SERIES_RESISTOR_HEATER} ohm.")
logger.info(f"Using a cooler thermistor of type {resistance_column}, with ref resistance {THERMISTOR_25C} ohm, and series resistor {SERIES_RESISTOR_COOLER} ohm.")

# Set up thermistor readers and controllers for the heater and cooler
with ThermistorReader(THERMISTOR_PIN_HEATER, thR_model, series_resistor=SERIES_RESISTOR_HEATER, series_mode='VCC_R_Rth_GND') as heater_thermistor_reader, \
     Digital_PinController(DIGITAL_PIN_HEATER) as heater_controller, \
     ThermistorReader(THERMISTOR_PIN_COOLER, thR_model, series_resistor=SERIES_RESISTOR_COOLER, series_mode='VCC_R_Rth_GND') as cooler_thermistor_reader, \
     Digital_PinController(DIGITAL_PIN_COOLER) as cooler_controller:
    
    last_toggle_time_heater = 0  # Track the last toggle time for the heater
    last_toggle_time_cooler = 0  # Track the last toggle time for the cooler
    
    try:
        while True:
            # Read temperature from the heater thermistor
            heater_temperature = heater_thermistor_reader.get_temperature()
            if heater_temperature is not None:
                # Log the temperature for the heater
                logger.info(f"Heater Temperature: {heater_temperature:.2f}°C")
                
                current_time = time.time()
                if current_time - last_toggle_time_heater >= MIN_TIME:
                    # Control the heater based on the temperature threshold
                    if heater_temperature < TEMP_THRESHOLD_HEATER and heater_controller.is_on():
                        heater_controller.turn_off() # Turn off pin will turn on the relay power to heat
                        logger.info("Heater ON")
                        last_toggle_time_heater = current_time
                    elif heater_temperature >= TEMP_THRESHOLD_HEATER and not heater_controller.is_on():
                        heater_controller.turn_on() # Turn on pin will turn off the relay power to stop heating
                        logger.info("Heater OFF")
                        last_toggle_time_heater = current_time

            # Read temperature from the cooler thermistor
            cooler_temperature = cooler_thermistor_reader.get_temperature()
            if cooler_temperature is not None:
                # Log the temperature for the cooler
                logger.info(f"Cooler Temperature: {cooler_temperature:.2f}°C")
                
                current_time = time.time()
                if current_time - last_toggle_time_cooler >= MIN_TIME:
                    # Control the cooler based on the temperature threshold
                    if cooler_temperature > TEMP_THRESHOLD_COOLER and cooler_controller.is_on():
                        cooler_controller.turn_off() # Turn off pin will turn on the relay power to cool
                        logger.info("Cooler ON")
                        last_toggle_time_cooler = current_time
                    elif cooler_temperature <= TEMP_THRESHOLD_COOLER and not cooler_controller.is_on():
                        cooler_controller.turn_on() # Turn on pin will turn off the relay power to stop cooling
                        logger.info("Cooler OFF")
                        last_toggle_time_cooler = current_time
            
            # Wait for a short time before the next reading
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
    finally:
        heater_controller.turn_off()  # Ensure heater pin is off on exit
        cooler_controller.turn_off()  # Ensure cooler pin is off on exit
        logger.info("Script exited, and both heater and cooler pins turned off.")
