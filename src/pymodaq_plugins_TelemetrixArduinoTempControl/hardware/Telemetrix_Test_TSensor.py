import time
import logging
from telemetrix import telemetrix
from collections import deque
from thermistor_model import ThermistorModel 

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Global variables to store recent analog values and their average
n_points_average = 4
last_analog_values = deque(maxlen=n_points_average)  # Store the last n values, here n=5 for example
last_analog_value = -1

# Arduino board constants
VCC = 5.0              # Supply voltage (5V for Arduino)
ARDUINO_ANALOG_PIN_VOLTAGE = 5 # Range of Arduino analog pin (5V)

def analog_callback(data):
    """
    Callback function to handle analog input readings with sliding average.
    """
    global last_analog_value
    _, new_analog_value = data[1], data[2]
    # logger.debug(f"Raw analog value received: {new_analog_value}")
    
    # Append the new reading to the deque, automatically removing the oldest if at max length
    last_analog_values.append(new_analog_value)
    
    # Calculate the smoothed value as the average of the values in the deque
    last_analog_value = sum(last_analog_values) / len(last_analog_values)
    
    # logger.debug(f"Raw analog value received: {analog_value}")
    # logger.debug(f"Smoothed analog value (last {len(last_analog_values)} readings): {last_analog_value}")


def read_thermistor_resistance(analog_value, mode = 'VCC_Rth_R_GND'):
    """
    Calculate the thermistor resistance from the analog reading, with the series resistor connected to VCC.
    """
    # Calculate the voltage at the junction of the series resistor and thermistor
    voltage = analog_value * (ARDUINO_ANALOG_PIN_VOLTAGE / 1023.0)
    
    try:
        # Calculate the thermistor resistance using the voltage divider formula
        if mode == 'VCC_Rth_R_GND':
            thermistor_resistance = SERIES_RESISTOR * ((VCC - voltage) / voltage)
        elif mode == 'VCC_R_Rth_GND':
            thermistor_resistance = SERIES_RESISTOR * (voltage / (VCC - voltage))
    except ZeroDivisionError:
        logger.error("Division by zero encountered while calculating thermistor resistance.")
        thermistor_resistance = float('inf')  # Set resistance to infinity if there's a division by zero
    
    logger.debug(f"Analog value: {analog_value}, Voltage: {voltage:.2f}, Thermistor resistance: {thermistor_resistance:.2f}")
    return thermistor_resistance


def calculate_temperature(thermistor_model):
    """
    Calculate the temperature based on the last analog reading.
    """
    if last_analog_value is None:
        logger.warning("No analog reading available.")
        return None
    thermistor_resistance = read_thermistor_resistance(last_analog_value)
    resistance_ratio = thermistor_resistance / THERMISTOR_25C
    logger.debug(f'Resistance ratio: {resistance_ratio:.3f}')
    try:
        temperature = thermistor_model.get_temperature(resistance_ratio)
        logger.info(f"Calculated temperature: {temperature:.2f}°C")
    except:
        temperature = None
        logger.warning(f'Unknown value for temperature (resistance_ratio={resistance_ratio:.2e})')
    return temperature



if __name__ == '__main__':
    
    # Constants
    THERMISTOR_PIN = 4 # Analog pin where thermistor is connected
    THERMISTOR_25C = 10000  # Value of the thermistor in ohms at 25°C
    SERIES_RESISTOR = 10000  # Value of the known resistor in ohms

    # Initialize the Telemetrix instance
    board = telemetrix.Telemetrix()
    last_analog_value = None  # Global to store the last analog reading
    
    # Load thermistor data
    file_path = "../../../Thermistor_R_vs_T.csv"
    resistance_column = 'Type 8016'
    thermistor_model = ThermistorModel(file_path, resistance_column)
    
    if thermistor_model is None:
        logger.error("Thermistor data could not be loaded.")
    else:
        # Set pin mode and attach callback
        board.set_pin_mode_analog_input(THERMISTOR_PIN, callback=analog_callback)
        try:
            while True:
                temperature = calculate_temperature(thermistor_model)
                if temperature is not None:
                    print(f"Temperature: {temperature:.2f}°C")
                time.sleep(1)
        except KeyboardInterrupt:
            board.shutdown()
            logger.info("Telemetrix session ended.")
        except Exception:
            board.shutdown()
            logger.info("Telemetrix session ended on unknown error.")
            import traceback 
            traceback.print_exc() 
