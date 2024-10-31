# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 16:14:05 2024

@author: gaignebet
"""

import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import logging

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for column names
TEMP_COLUMN = 'T (C)'
RESISTANCE_COLUMN = 'Type 8016'

def exponential_model(x, A, B, x0):
    """Exponential model function."""
    return A * np.exp(-(x - x0) / B)

def load_thermistor_model(file_path, column_name, model_type='interpolation'):
    """
    Load thermistor data and return a model function for temperature estimation.

    :param file_path: Path to the CSV file containing thermistor data.
    :param column_name: Name of the column containing the resistance ratio data (R/R(25°C)).
    :param model_type: Model type to use ('exponential' or 'interpolation').
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

        if model_type == 'exponential':
            # Fit an exponential model to the data
            exp_params, _ = curve_fit(exponential_model, temperatures, resistance_ratios, p0=(1, 17, 25))
            logger.info(f"Fitted exponential parameters: A={exp_params[0]}, B={exp_params[1]}, x0={exp_params[2]}")
            
            # Create a function for temperature from resistance ratios based on the fitted exponential model
            def temp_from_exp_model(r):
                r = np.asarray(r)  # Ensure r is a numpy array
                if np.any(r < np.min(resistance_ratios)) or np.any(r > np.max(resistance_ratios)):
                    raise ValueError(f"Input resistance ratio is out of bounds. Valid domain: [{np.min(resistance_ratios):.2e}:{np.max(resistance_ratios):.2e}].")
                return -exp_params[1] * np.log(r / exp_params[0]) + exp_params[2]
            
            return temp_from_exp_model

        elif model_type == 'interpolation':
            logger.info("Using interpolation model.")
            
            # Return a function that checks the bounds
            def bounded_temp_from_resistance(r):
                r = np.asarray(r)  # Ensure r is a numpy array
                if np.any(r < np.min(resistance_ratios)) or np.any(r > np.max(resistance_ratios)):
                    raise ValueError(f"Input resistance ratio is out of bounds. Valid domain: [{np.min(resistance_ratios):.2e}:{np.max(resistance_ratios):.2e}].")
                return temp_from_resistance(r)

            return bounded_temp_from_resistance
        
        else:
            logger.error("Invalid model type specified. Use 'exponential' or 'interpolation'.")
            return None

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
    temp_from_interpolation = load_thermistor_model(file_path, RESISTANCE_COLUMN, model_type='interpolation')

    # Load the exponential model
    temp_from_exponential = load_thermistor_model(file_path, RESISTANCE_COLUMN, model_type='exponential')

    # Check if both models are available
    if temp_from_interpolation is not None and temp_from_exponential is not None:
        logger.info("Both models are ready for use.")
        
        # Get the original data for comparison:
        data = pd.read_csv(file_path, sep='\t')
        temperatures = data[TEMP_COLUMN].values # Extract the temperature and resistance ratio columns
        resistance_ratios = data[RESISTANCE_COLUMN].values
        # Create a log-spaced array for resistance ratios
        resistance_min = np.min(resistance_ratios)
        resistance_max = np.max(resistance_ratios)
        
        resistance_range = np.logspace(np.log10(resistance_min), np.log10(resistance_max), 200)

        # Calculate temperature from the interpolation model
        temperatures_from_interpolation = temp_from_interpolation(resistance_range)

        # Calculate temperature from the exponential model
        temperatures_from_exponential = temp_from_exponential(resistance_range)


        # Plot the results
        plt.figure(figsize=(10, 5))
        plt.plot(resistance_range, temperatures_from_interpolation, '.g', label='Interpolation Model', ms=2)
        plt.plot(resistance_range, temperatures_from_exponential, '.r', label='Exponential Model', ms=2)
        plt.scatter(resistance_ratios, temperatures, label='Original Data Points', color='blue', s=10)
        plt.xscale('log')  # Set x-axis to logarithmic scale for better visualization
        plt.xlabel('Resistance Ratio (R/R(25°C))')
        plt.ylabel('Temperature (°C)')
        plt.title('Thermistor Model Fitting')
        plt.legend()
        plt.grid()
        plt.show()
    else:
        logger.error("One or both model functions are not available.")
