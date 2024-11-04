# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 16:14:05 2024

@author: gaignebet
"""

import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import logging

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Constants for column names
TEMP_COLUMN = 'T (C)'
RESISTANCE_COLUMN = 'Type 8016'

class ThermistorModel:
    def __init__(self, file_path, resistance_column):
        """
        Initialize the ThermistorModel with data from the specified file.

        :param file_path: Path to the CSV file containing thermistor data.
        :param resistance_column: Name of the column containing the resistance ratio data (R/R(25°C)).
        """
        try:
            # Load the CSV file
            data = pd.read_csv(file_path, sep='\t')

            # Extract temperature and resistance ratio columns
            self.temperatures = data[TEMP_COLUMN].values
            self.resistance_ratios = data[resistance_column].values

            # Ensure the data is not empty
            if len(self.temperatures) == 0 or len(self.resistance_ratios) == 0:
                raise ValueError("Loaded data columns are empty.")

            # Create interpolation models for temperature and resistance ratio
            self.temp_from_resistance = interp1d(
                self.resistance_ratios, self.temperatures, kind='linear', fill_value="extrapolate"
            )
            self.resistance_from_temp = interp1d(
                self.temperatures, self.resistance_ratios, kind='linear', fill_value="extrapolate"
            )

            logger.info("Interpolation model initialized successfully.")

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            self.temp_from_resistance = None
            self.resistance_from_temp = None
        except ValueError as ve:
            logger.error(f"Value error: {ve}")
            self.temp_from_resistance = None
            self.resistance_from_temp = None
        except Exception as e:
            logger.error(f"Error loading thermistor data: {e}")
            self.temp_from_resistance = None
            self.resistance_from_temp = None

    def get_temperature(self, resistance_ratio):
        """
        Get the temperature corresponding to a given resistance ratio.

        :param resistance_ratio: The resistance ratio (R/R(25°C)).
        :return: Estimated temperature or raises an error if out of bounds.
        """
        if self.temp_from_resistance is None:
            raise ValueError("Model not initialized.")

        # Check bounds and raise a clear error message if out of range
        if np.any(resistance_ratio < np.min(self.resistance_ratios)) or np.any(resistance_ratio > np.max(self.resistance_ratios)):
            min_ratio = np.min(self.resistance_ratios)
            max_ratio = np.max(self.resistance_ratios)
            
            # Generate an appropriate error message depending on array or single value
            if resistance_ratio.size == 1:
                raise ValueError(f"Input resistance ratio ({resistance_ratio.item():.2e}) is out of bounds. "
                                 f"Valid domain: [{min_ratio:.2e}:{max_ratio:.2e}].")
            else:
                raise ValueError(f"One or more input resistance ratios are out of bounds. "
                             f"Valid domain: [{min_ratio:.2e}:{max_ratio:.2e}].")

        return self.temp_from_resistance(resistance_ratio)

    def get_resistance_ratio(self, temperature):
        """
        Get the resistance ratio corresponding to a given temperature.

        :param temperature: The temperature in °C.
        :return: Estimated resistance ratio or raises an error if out of bounds.
        """
        if self.resistance_from_temp is None:
            raise ValueError("Model not initialized.")

        # Check bounds and raise a clear error message if out of range
        if np.any(temperature < np.min(self.temperatures)) or np.any(temperature > np.max(self.temperatures)):
            min_temp = np.min(self.temperatures)
            max_temp = np.max(self.temperatures)
            
            # Generate an appropriate error message depending on array or single value
            if temperature.size == 1:
                raise ValueError(f"Input temperature ({temperature.item():.2f}°C) is out of bounds. "
                                 f"Valid domain: [{min_temp:.2f}°C:{max_temp:.2f}°C].")
            else:
                raise ValueError(f"One or more input temperatures are out of bounds. "
                                 f"Valid domain: [{min_temp:.2f}°C:{max_temp:.2f}°C].")
        

        return self.resistance_from_temp(temperature)

if __name__ == '__main__':
    file_path = r"../../../Thermistor_R_vs_T.csv"

    # Initialize the ThermistorModel
    thermistor_model = ThermistorModel(file_path, RESISTANCE_COLUMN)

    # Check if the model is available
    if thermistor_model.temp_from_resistance is not None and thermistor_model.resistance_from_temp is not None:
        logger.info("Thermistor model is ready for use.")
        
        # Get the original data for comparison:
        data = pd.read_csv(file_path, sep='\t')
        temperatures = data[TEMP_COLUMN].values  # Extract the temperature and resistance ratio columns
        resistance_ratios = data[RESISTANCE_COLUMN].values
        
        # Create a log-spaced array for resistance ratios
        resistance_ratio_min = np.min(resistance_ratios)
        resistance_ratio_max = np.max(resistance_ratios)
        resistance_ratio_range = np.logspace(np.log10(resistance_ratio_min), np.log10(resistance_ratio_max), 200)

        # Calculate temperature from the model for each resistance ratio in the range
        try:
            temperatures_from_interpolation = thermistor_model.get_temperature(resistance_ratio_range)

            # Plot the results
            plt.figure(figsize=(10, 5))
            plt.plot(resistance_ratio_range, temperatures_from_interpolation, '.g', label='Interpolation Model', ms=2)
            plt.scatter(resistance_ratios, temperatures, label='Original Data Points', color='blue', s=10)
            plt.xscale('log')  # Set x-axis to logarithmic scale for better visualization
            plt.xlabel('Resistance Ratio (R/R(25°C))')
            plt.ylabel('Temperature (°C)')
            plt.title('Thermistor Model Fitting')
            plt.legend()
            plt.grid()
            plt.show()
        except ValueError as ve:
            logger.error(f"Error in model calculation: {ve}")

    else:
        logger.error("Thermistor model function is not available.")

