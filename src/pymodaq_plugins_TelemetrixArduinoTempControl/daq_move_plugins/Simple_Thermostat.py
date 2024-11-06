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
THERMISTOR_PIN = 4       # Analog pin where thermistor is connected
DIGITAL_PIN = 2          # Digital pin to control
TEMP_THRESHOLD = 26.0    # Temperature threshold in °C
SERIES_RESISTOR = 10000  # Known resistor in ohms
THERMISTOR_25C = 10000   # Resistance of the thermistor at 25°C
MIN_TIME = 5.0           # Minimum time interval between pin state changes in seconds

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

# Initialize thermistor model and reader
file_path = "../../../Thermistor_R_vs_T.csv"
resistance_column = 'Type 8016'  # Adjust based on your thermistor data
thR_model = ThermistorModel(file_path, ref_R=THERMISTOR_25C, resistance_col_label=resistance_column)

logger.info(f'Using a thermistor of type {resistance_column}, of ref resistance {THERMISTOR_25C} ohm, a series resistor of {SERIES_RESISTOR} ohm')

with ThermistorReader(THERMISTOR_PIN, thR_model, series_resistor=SERIES_RESISTOR) as thermistor_reader, \
     Digital_PinController(DIGITAL_PIN) as relay_controller:
    
    last_toggle_time = 0  # Track the last time the pin was toggled
    
    try:
        while True:
            # Read temperature from the thermistor
            temperature = thermistor_reader.get_temperature()
            
            if temperature is not None:
                # Log the temperature
                logger.info(f"Temperature: {temperature:.2f}°C")
                print(f"Temperature: {temperature:.2f}°C")
                
                current_time = time.time()
                if current_time - last_toggle_time >= MIN_TIME:
                    print("Change available")
                else:
                    print("Change blocked")
                
                # Check if enough time has passed since the last toggle
                if (temperature < TEMP_THRESHOLD and current_time - last_toggle_time >= MIN_TIME):
                    if not relay_controller.is_on():
                        relay_controller.turn_on()
                        print("Pin ON")
                        logger.info('Turn on heater')
                        last_toggle_time = current_time
                elif (temperature >= TEMP_THRESHOLD and current_time - last_toggle_time >= MIN_TIME):
                    if relay_controller.is_on():
                        relay_controller.turn_off()
                        print("Pin OFF")
                        logger.info('Turn off heater')
                        last_toggle_time = current_time
            
            # Wait for a short time before the next reading
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("Script terminated by user.")
        logger.info("Script terminated by user.")
    finally:
        relay_controller.turn_off()  # Ensure pin is off on exit
        logger.info("Script exited and pin turned off.")
