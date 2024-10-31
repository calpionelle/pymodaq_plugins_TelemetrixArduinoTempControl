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

# Constants for column names
TEMP_COLUMN = 'T (C)'
RESISTANCE_COLUMN = 'Type 8016'

def load_thermistor_model(file_path, column_name):
    """
    Load thermistor data and return a model function for temperature estimation.

    :param file_path: Path to the CSV file containing thermistor data.
    :param column_name: Name of the column containing the resistance ratio data (R/R(25°C)).
    :return: A model function for temperature estimation or None if loading fails.
    """
    try:
        # Load the CSV file
        data = pd.read_csv(file_path, sep='\t')

        # Extract the temperature and resistance ratio columns
        temperatures = data[TEMP_COLUMN].values
        resistance_ratios = data[column_name].values

        # Ensure the data is not empty
        if len(temperatures) == 0 or len(resistance_ratios) == 0:
            raise ValueError("Loaded data columns are empty.")

        # Create a function for temperature from resistance ratios using interpolation
        temp_from_resistance = interp1d(
            resistance_ratios, temperatures, kind='linear', fill_value="extrapolate"
        )

        logger.info("Using interpolation model.")

        # Return a function that checks the bounds
        def bounded_temp_from_resistance(r):
            r = np.asarray(r)  # Ensure r is a numpy array
            if np.any(r < np.min(resistance_ratios)) or np.any(r > np.max(resistance_ratios)):
                raise ValueError(f"Input resistance ratio is out of bounds. Valid domain: [{np.min(resistance_ratios):.2e}:{np.max(resistance_ratios):.2e}].")
            return temp_from_resistance(r)

        return bounded_temp_from_resistance

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except ValueError as ve:
        logger.error(f"Value error: {ve}")
    except Exception as e:
        logger.error(f"Error loading thermistor data: {e}")

    return None

if __name__ == '__main__':
    file_path = r"../../../Thermistor_R_vs_T.csv"

    # Load the interpolation model
    temp_from_interpolation = load_thermistor_model(file_path, RESISTANCE_COLUMN)

    # Check if the model is available
    if temp_from_interpolation is not None:
        logger.info("Model is ready for use.")
        
        # Get the original data for comparison:
        data = pd.read_csv(file_path, sep='\t')
        temperatures = data[TEMP_COLUMN].values  # Extract the temperature and resistance ratio columns
        resistance_ratios = data[RESISTANCE_COLUMN].values
        
        # Create a log-spaced array for resistance ratios
        resistance_min = np.min(resistance_ratios)
        resistance_max = np.max(resistance_ratios)
        
        resistance_range = np.logspace(np.log10(resistance_min), np.log10(resistance_max), 200)

        # Calculate temperature from the interpolation model
        temperatures_from_interpolation = temp_from_interpolation(resistance_range)

        # Plot the results
        plt.figure(figsize=(10, 5))
        plt.plot(resistance_range, temperatures_from_interpolation, '.g', label='Interpolation Model', ms=2)
        plt.scatter(resistance_ratios, temperatures, label='Original Data Points', color='blue', s=10)
        plt.xscale('log')  # Set x-axis to logarithmic scale for better visualization
        plt.xlabel('Resistance Ratio (R/R(25°C))')
        plt.ylabel('Temperature (°C)')
        plt.title('Thermistor Model Fitting')
        plt.legend()
        plt.grid()
        plt.show()
    else:
        logger.error("Model function is not available.")
