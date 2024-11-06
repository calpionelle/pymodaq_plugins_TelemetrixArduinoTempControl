# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:09:35 2024

@author: gaignebet
"""

import time
from thermistor_model import ThermistorModel
from Thermistor_Reader import ThermistorReader
from Digital_Output_Controller import Digital_PinController

# Define constants
THERMISTOR_PIN = 4       # Analog pin where thermistor is connected
DIGITAL_PIN = 2          # Digital pin to control
TEMP_THRESHOLD = 28.0    # Temperature threshold in °C
SERIES_RESISTOR = 10000  # Known resistor in ohms
THERMISTOR_25C = 10000   # Resistance of the thermistor at 25°C
MIN_TIME = 5.0           # Minimum time interval between pin state changes in seconds

# Initialize thermistor model and reader
file_path = "../../../Thermistor_R_vs_T.csv"
resistance_column = 'Type 8016'  # Adjust based on your thermistor data
thR_model = ThermistorModel(file_path, ref_R=THERMISTOR_25C, resistance_col_label=resistance_column)

with ThermistorReader(THERMISTOR_PIN, thR_model, series_resistor=SERIES_RESISTOR) as thermistor_reader, \
     Digital_PinController(DIGITAL_PIN) as relay_controller:
    
    last_toggle_time = 0  # Track the last time the pin was toggled
    
    try:
        while True:
            # Read temperature from the thermistor
            temperature = thermistor_reader.get_temperature()
            
            if temperature is not None:
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
                        last_toggle_time = current_time
                elif (temperature >= TEMP_THRESHOLD and current_time - last_toggle_time >= MIN_TIME):
                    if relay_controller.is_on():
                        relay_controller.turn_off()
                        print("Pin OFF")
                        last_toggle_time = current_time
            
            # Wait for a short time before the next reading
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("Script terminated by user.")
    finally:
        relay_controller.turn_off()  # Ensure pin is off on exit
