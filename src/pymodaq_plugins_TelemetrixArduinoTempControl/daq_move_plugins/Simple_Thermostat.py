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
THERMISTOR_PIN_1 = 4       # First thermistor's analog pin
THERMISTOR_PIN_2 = 5       # Second thermistor's analog pin (e.g., A0)
DIGITAL_PIN_1 = 2          # First digital pin to control
DIGITAL_PIN_2 = 3          # Second digital pin to control
TEMP_THRESHOLD_1 = 26.0    # Temperature threshold for first thermistor in °C
TEMP_THRESHOLD_2 = 27.0    # Temperature threshold for second thermistor in °C
SERIES_RESISTOR_1 = 10000    # Known resistor in ohms
SERIES_RESISTOR_2 = 10000    # Known resistor in ohms
THERMISTOR_25C = 10000     # Resistance of the thermistor at 25°C
MIN_TIME = 5.0             # Minimum time interval between pin state changes in seconds

# Define a logger setup function
def setup_logger(logger_name, log_file, level=logging.WARNING):
    # Configure logger
    l = logging.getLogger(logger_name)
    
    # Remove any existing handlers
    for handler in l.handlers[:]:
        l.removeHandler(handler)
    
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt="%Y.%m.%d-%H:%M:%S")
    
    # File handler
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    
    # Stream handler (console output)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    
    l.setLevel(level)
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

logger.info(f'Using a thermistor of type {resistance_column}, with ref resistance {THERMISTOR_25C} ohm, and a series resistor of {SERIES_RESISTOR_1} ohm as heater thermistor')
logger.info(f'Using a thermistor of type {resistance_column}, with ref resistance {THERMISTOR_25C} ohm, and a series resistor of {SERIES_RESISTOR_2} ohm as coolor thermistor')

with ThermistorReader(THERMISTOR_PIN_1, thR_model, series_resistor=SERIES_RESISTOR_1) as thermistor_reader_1, \
     Digital_PinController(DIGITAL_PIN_1) as relay_controller_1, \
     ThermistorReader(THERMISTOR_PIN_2, thR_model, series_resistor=SERIES_RESISTOR_2, series_mode='VCC_R_Rth_GND') as thermistor_reader_2, \
     Digital_PinController(DIGITAL_PIN_2) as relay_controller_2:
    
    last_toggle_time_1 = 0  # Track the last time the first pin was toggled
    last_toggle_time_2 = 0  # Track the last time the second pin was toggled
    
    try:
        while True:
            # Read temperature from the first thermistor
            temperature_1 = thermistor_reader_1.get_temperature()
            if temperature_1 is not None:
                # Log the temperature
                logger.info(f"Temperature 1: {temperature_1:.2f}°C")
                print(f"Temperature 1: {temperature_1:.2f}°C")
                
                current_time = time.time()
                if current_time - last_toggle_time_1 >= MIN_TIME:
                    # Control the first digital pin based on the first temperature threshold
                    if temperature_1 < TEMP_THRESHOLD_1 and not relay_controller_1.is_on():
                        relay_controller_1.turn_on()
                        logger.info("Pin 1 ON")
                        last_toggle_time_1 = current_time
                    elif temperature_1 >= TEMP_THRESHOLD_1 and relay_controller_1.is_on():
                        relay_controller_1.turn_off()
                        logger.info("Pin 1 OFF")
                        last_toggle_time_1 = current_time

            # Read temperature from the second thermistor
            temperature_2 = thermistor_reader_2.get_temperature()
            if temperature_2 is not None:
                # Log the temperature
                logger.info(f"Temperature 2: {temperature_2:.2f}°C")
                print(f"Temperature 2: {temperature_2:.2f}°C")
                
                current_time = time.time()
                if current_time - last_toggle_time_2 >= MIN_TIME:
                    # Control the second digital pin based on the second temperature threshold
                    if temperature_2 > TEMP_THRESHOLD_2 and not relay_controller_2.is_on():
                        relay_controller_2.turn_on()
                        logger.info("Pin 2 ON")
                        last_toggle_time_2 = current_time
                    elif temperature_2 <= TEMP_THRESHOLD_2 and relay_controller_2.is_on():
                        relay_controller_2.turn_off()
                        logger.info("Pin 2 OFF")
                        last_toggle_time_2 = current_time
            
            # Wait for a short time before the next reading
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("Script terminated by user.")
        logger.info("Script terminated by user.")
    finally:
        relay_controller_1.turn_off()  # Ensure first pin is off on exit
        relay_controller_2.turn_off()  # Ensure second pin is off on exit
        logger.info("Script exited, and both pins turned off.")
