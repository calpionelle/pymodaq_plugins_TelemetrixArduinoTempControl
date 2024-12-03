# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:09:35 2024

@author: gaignebet
"""

import time
import logging
import matplotlib.pyplot as plt
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

# Initialize data lists for plotting
heater_times, heater_temps = [], []
cooler_times, cooler_temps = [], []

# Set up thermistor readers and controllers
with ThermistorReader(THERMISTOR_PIN_HEATER, thR_model, series_resistor=SERIES_RESISTOR_HEATER, series_mode='VCC_R_Rth_GND') as heater_reader, \
     Digital_PinController(DIGITAL_PIN_HEATER) as heater_ctrl, \
     ThermistorReader(THERMISTOR_PIN_COOLER, thR_model, series_resistor=SERIES_RESISTOR_COOLER, series_mode='VCC_R_Rth_GND') as cooler_reader, \
     Digital_PinController(DIGITAL_PIN_COOLER) as cooler_ctrl:

    last_toggle_time_heater = 0
    last_toggle_time_cooler = 0
    start_time = time.time()

    try:
        # Set up live plotting
        plt.ion()
        fig, ax = plt.subplots()
        heater_line, = ax.plot([], [], 'r+-', label="Heater Temp (°C)")
        cooler_line, = ax.plot([], [], 'b+-', label="Cooler Temp (°C)")
        ax.set_title("Temperature Monitoring")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Temperature (°C)")
        ax.legend()

        while True:
            # Read temperatures
            heater_temp = heater_reader.get_temperature()
            cooler_temp = cooler_reader.get_temperature()
            current_time = time.time()

            # Update and log heater
            if heater_temp is not None:
                elapsed_time = current_time - start_time
                heater_times.append(elapsed_time)
                heater_temps.append(heater_temp)
                logger.info(f"\033[1;31mHeater Temperature: {heater_temp:.2f}°C\033[0m")

                if current_time - last_toggle_time_heater >= MIN_TIME:
                    if heater_temp < TEMP_THRESHOLD_HEATER and heater_ctrl.is_on():
                        heater_ctrl.turn_off()
                        logger.info("Heater ON")
                        last_toggle_time_heater = current_time
                    elif heater_temp >= TEMP_THRESHOLD_HEATER and not heater_ctrl.is_on():
                        heater_ctrl.turn_on()
                        logger.info("Heater OFF")
                        last_toggle_time_heater = current_time

            # Update and log cooler
            if cooler_temp is not None:
                elapsed_time = current_time - start_time
                cooler_times.append(elapsed_time)
                cooler_temps.append(cooler_temp)
                logger.info(f"\033[1;34mCooler Temperature: {cooler_temp:.2f}°C\033[0m")

                if current_time - last_toggle_time_cooler >= MIN_TIME:
                    if cooler_temp > TEMP_THRESHOLD_COOLER and cooler_ctrl.is_on():
                        cooler_ctrl.turn_off()
                        logger.info("Cooler ON")
                        last_toggle_time_cooler = current_time
                    elif cooler_temp <= TEMP_THRESHOLD_COOLER and not cooler_ctrl.is_on():
                        cooler_ctrl.turn_on()
                        logger.info("Cooler OFF")
                        last_toggle_time_cooler = current_time

            # Update the plot
            heater_line.set_data(heater_times, heater_temps)
            cooler_line.set_data(cooler_times, cooler_temps)
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.1)

            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
    finally:
        heater_ctrl.turn_on()
        cooler_ctrl.turn_on()
        logger.info("Script exited. Both heater and cooler pins turned on (i.e. no current through the relays).")

        # Save the plot
        graph_file_path = log_file_path.replace(".log", ".png")
        plt.savefig(graph_file_path)
        logger.info(f"Graph saved at {graph_file_path}.")
        plt.ioff()
        plt.show()
