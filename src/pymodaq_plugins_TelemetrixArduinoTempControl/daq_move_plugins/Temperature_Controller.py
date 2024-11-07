# -*- coding: utf-8 -*-
"""
Created on Thu Nov  7 15:48:08 2024

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
THERMISTOR_PIN_HEATER = 4        # Analog pin for the heater thermistor
THERMISTOR_PIN_COOLER = 5        # Analog pin for the cooler thermistor (e.g., A0)
DIGITAL_PIN_HEATER = 2           # Digital pin to control the heater
DIGITAL_PIN_COOLER = 3           # Digital pin to control the cooler
TEMP_THRESHOLD_HEATER = 25.0     # Heater activation threshold in °C
TEMP_THRESHOLD_COOLER = 26.0     # Cooler activation threshold in °C
SERIES_RESISTOR_HEATER = 10000   # Series resistor for the heater thermistor in ohms
SERIES_RESISTOR_COOLER = 10000   # Series resistor for the cooler thermistor in ohms
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

# Base class for temperature control (Heater and Cooler)
class TemperatureController:
    heater_counter = 1  # Class variable to track heater instance count
    cooler_counter = 1  # Class variable to track cooler instance count

    def __init__(self, thermistor_pin, digital_pin, threshold, series_resistor, thR_model, pin_mode, name=None):
        # Assign a default name if none is provided
        if not name:
            if pin_mode == "heater":
                name = f"heater{TemperatureController.heater_counter}"
                TemperatureController.heater_counter += 1
            elif pin_mode == "cooler":
                name = f"cooler{TemperatureController.cooler_counter}"
                TemperatureController.cooler_counter += 1
        
        self.name = name  # Assign the unique name to the controller
        self.thermistor_reader = ThermistorReader(thermistor_pin, thR_model, series_resistor=series_resistor, series_mode='VCC_R_Rth_GND')
        self.controller = Digital_PinController(digital_pin)
        self.threshold = threshold
        self.pin_mode = pin_mode
        self.last_toggle_time = 0

    def __enter__(self):
        # Initialize any necessary resources when the context is entered
        logger.info(f"Initializing {self.name} ({self.pin_mode} controller)")
        self.controller.turn_off()  # Ensure the controller is off when entering the context
        return self  # Return the instance itself

    def __exit__(self, exc_type, exc_value, traceback):
        # Handle any cleanup when exiting the context
        logger.info(f"Exiting {self.name} ({self.pin_mode} controller)")
        self.controller.turn_off()  # Ensure the controller is turned off when exiting the context
        if exc_type:
            logger.error(f"An error occurred in {self.name}: {exc_value}")
        return True  # Suppress exceptions (optional)

    def control(self, current_time, min_time):
        temperature = self.thermistor_reader.get_temperature()
        if temperature is not None:
            logger.info(f"{self.name} - Temperature: {temperature:.2f}°C")
            
            if current_time - self.last_toggle_time >= min_time:
                if self.pin_mode == "heater" and temperature < self.threshold and not self.controller.is_on():
                    self.controller.turn_on()
                    logger.info(f"{self.name} - Heater ON")
                    self.last_toggle_time = current_time
                elif self.pin_mode == "heater" and temperature >= self.threshold and self.controller.is_on():
                    self.controller.turn_off()
                    logger.info(f"{self.name} - Heater OFF")
                    self.last_toggle_time = current_time

                if self.pin_mode == "cooler" and temperature > self.threshold and not self.controller.is_on():
                    self.controller.turn_on()
                    logger.info(f"{self.name} - Cooler ON")
                    self.last_toggle_time = current_time
                elif self.pin_mode == "cooler" and temperature <= self.threshold and self.controller.is_on():
                    self.controller.turn_off()
                    logger.info(f"{self.name} - Cooler OFF")
                    self.last_toggle_time = current_time

# Specialized class for Heater control
class HeaterController(TemperatureController):
    def __init__(self, thermistor_pin, digital_pin, threshold, series_resistor, thR_model, name=None):
        super().__init__(thermistor_pin, digital_pin, threshold, series_resistor, thR_model, pin_mode="heater", name=name)

# Specialized class for Cooler control
class CoolerController(TemperatureController):
    def __init__(self, thermistor_pin, digital_pin, threshold, series_resistor, thR_model, name=None):
        super().__init__(thermistor_pin, digital_pin, threshold, series_resistor, thR_model, pin_mode="cooler", name=name)


# Instantiate the heater and cooler controllers
with HeaterController(THERMISTOR_PIN_HEATER, DIGITAL_PIN_HEATER, TEMP_THRESHOLD_HEATER, SERIES_RESISTOR_HEATER, thR_model) as heater_controller, \
     CoolerController(THERMISTOR_PIN_COOLER, DIGITAL_PIN_COOLER, TEMP_THRESHOLD_COOLER, SERIES_RESISTOR_COOLER, thR_model) as cooler_controller:
    
    try:
        while True:
            current_time = time.time()
            heater_controller.control(current_time, MIN_TIME)
            cooler_controller.control(current_time, MIN_TIME)
            
            # Wait for a short time before the next reading
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
    finally:
        heater_controller.controller.turn_off()  # Ensure heater pin is off on exit
        cooler_controller.controller.turn_off()  # Ensure cooler pin is off on exit
        logger.info("Script exited, and both heater and cooler pins turned off.")
