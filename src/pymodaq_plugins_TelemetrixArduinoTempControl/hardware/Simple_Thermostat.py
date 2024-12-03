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
from colorama import init, Fore

# Initialize colorama
init(autoreset=True)

# Define constants
THERMISTOR_PIN_HEATER = 0        # Analog pin for the heater thermistor
THERMISTOR_PIN_COOLER = 1        # Analog pin for the cooler thermistor (e.g., A0)
DIGITAL_PIN_HEATER = 2           # Digital pin to control the heater
DIGITAL_PIN_COOLER = 4           # Digital pin to control the cooler
TEMP_THRESHOLD_HEATER = 60.0     # Heater activation threshold in °C
TEMP_THRESHOLD_COOLER = 26.0     # Cooler activation threshold in °C
SERIES_RESISTOR_HEATER = 13000   # Series resistor for the heater thermistor in ohms
SERIES_RESISTOR_COOLER = 13000   # Series resistor for the cooler thermistor in ohms
THERMISTOR_25C = 10000           # Resistance of the thermistor at 25°C
MIN_TIME = 5.0                   # Minimum time interval between pin state changes in seconds
SLIDE_WINDOW_TIME = 300          # Sliding window time in seconds (5 minutes)

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

# Initialize data lists for plotting (full dataset)
full_times = {}
full_temps = {}

# Initialize data lists for real-time sliding window
sensor_times = {}
sensor_temps = {}

# Define the sensor configurations (dynamically populated)
sensors = {
    "heater": {
        "pin": THERMISTOR_PIN_HEATER,
        "digital_pin": DIGITAL_PIN_HEATER,
        "temp_threshold": TEMP_THRESHOLD_HEATER,
        "series_resistor": SERIES_RESISTOR_HEATER,
        "name": "Heater",
        "line_color": '#FF5733',  # Hex color code for heater
    },
    "cooler": {
        "pin": THERMISTOR_PIN_COOLER,
        "digital_pin": DIGITAL_PIN_COOLER,
        "temp_threshold": TEMP_THRESHOLD_COOLER,
        "series_resistor": SERIES_RESISTOR_COOLER,
        "name": "Cooler",
        "line_color": '#33CFFF',  # Hex color code for cooler
    },
}

# Manually initialize the thermistor readers and digital controllers
sensor_readers_controllers = {}
for sensor_name, config in sensors.items():
    sensor_reader = ThermistorReader(config['pin'], thR_model, series_resistor=config['series_resistor'], series_mode='VCC_R_Rth_GND')
    controller = Digital_PinController(config['digital_pin'])
    sensor_readers_controllers[sensor_name] = (sensor_reader, controller)

last_toggle_times = {sensor_name: 0 for sensor_name in sensors}
start_time = time.time()

# Generalized method to update the graph for any sensor
def update_graph(sensor_name, times, temps, line):
    line.set_data(times, temps)
    ax.relim()
    ax.autoscale_view()

# Helper function to convert hex color to colorama-compatible format
def hex_to_foreground_color(hex_color):
    """Convert hex color code to colorama foreground color."""
    if hex_color == '#FF5733':
        return Fore.RED
    elif hex_color == '#33CFFF':
        return Fore.CYAN
    else:
        return Fore.WHITE

try:
    # Set up live plotting
    plt.ion()
    fig, ax = plt.subplots()
    sensor_lines = {sensor_name: ax.plot([], [], color=config['line_color'], label=f"{config['name']} Temp (°C)")[0] for sensor_name, config in sensors.items()}
    
    ax.set_title("Temperature Monitoring")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True)  # Add grid to the real-time plot

    # Add horizontal lines for the thresholds with matching colors
    for sensor_name, config in sensors.items():
        ax.axhline(config['temp_threshold'], linestyle='--', color=config['line_color'], label=f"{config['name']} Threshold ({config['temp_threshold']}°C)")

    while True:
        for sensor_name, config in sensors.items():
            reader, controller = sensor_readers_controllers[sensor_name]
            temp = reader.get_temperature()
            if temp is not None:
                current_time = time.time()
                elapsed_time = current_time - start_time

                # Update full data
                full_times.setdefault(sensor_name, []).append(elapsed_time)
                full_temps.setdefault(sensor_name, []).append(temp)

                # Real-time sliding window data update
                sensor_times.setdefault(sensor_name, []).append(elapsed_time)
                sensor_temps.setdefault(sensor_name, []).append(temp)

                if elapsed_time > SLIDE_WINDOW_TIME:
                    # Remove old data (older than SLIDE_WINDOW_TIME)
                    sensor_times[sensor_name].pop(0)
                    sensor_temps[sensor_name].pop(0)

                # Log color formatting using colorama
                color_code = config['line_color']
                log_color = hex_to_foreground_color(color_code)
                logger.info(f"{log_color}{config['name']} Temperature: {temp:.2f}°C")

                # Update control logic for each sensor
                if current_time - last_toggle_times[sensor_name] >= MIN_TIME:
                    if temp < config['temp_threshold'] and controller.is_on():
                        controller.turn_off()
                        logger.info(f"{config['name']} OFF")
                        last_toggle_times[sensor_name] = current_time
                    elif temp >= config['temp_threshold'] and not controller.is_on():
                        controller.turn_on()
                        logger.info(f"{config['name']} ON")
                        last_toggle_times[sensor_name] = current_time

                # Update the graph for the sensor
                update_graph(sensor_name, sensor_times[sensor_name], sensor_temps[sensor_name], sensor_lines[sensor_name])

        plt.pause(0.1)

        time.sleep(0.5)

except KeyboardInterrupt:
    logger.info("Script terminated by user.")
finally:
    for sensor_name, config in sensors.items():
        sensor_readers_controllers[sensor_name][1].turn_off()  # Ensure all controllers are turned off
        sensor_readers_controllers[sensor_name][0].disconnect() # Disconnect thermistor reader
        sensor_readers_controllers[sensor_name][1].disconnect() # Disconnect digital pin controller

    logger.info("Script exited. All devices are turned off.")

    # Save the plot with the full dataset
    full_fig, full_ax = plt.subplots()
    full_sensor_lines = {
        sensor_name: full_ax.plot(full_times[sensor_name], full_temps[sensor_name], color=config['line_color'], label=f"{config['name']} Temp (°C)")[0]
        for sensor_name, config in sensors.items()
    }
    full_ax.set_title("Full Temperature Data")
    full_ax.set_xlabel("Time (s)")
    full_ax.set_ylabel("Temperature (°C)")
    full_ax.legend()
    full_ax.grid(True)

    for sensor_name, config in sensors.items():
        full_ax.axhline(config['temp_threshold'], linestyle='--', color=config['line_color'], label=f"{config['name']} Threshold ({config['temp_threshold']}°C)")

    full_fig.tight_layout()
    # Save the plot
    # full_fig.savefig(f"full_temperature_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    graph_file_path = log_file_path.replace(".log", ".png")
    full_fig.savefig(graph_file_path)
    logger.info(f"Graph saved at {graph_file_path}.")
    plt.ioff()
    plt.show()
    
