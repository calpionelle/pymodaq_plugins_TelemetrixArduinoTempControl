import time
import logging
from telemetrix import telemetrix
from collections import deque
from thermistor_model import ThermistorModel 
import numpy as np 

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Arduino board constants
VCC = 5.0 # Supply voltage (5V for Arduino)
ARDUINO_ANALOG_PIN_VOLTAGE = 5 # Range of Arduino analog pin (5V)
ARDUINO_ANALOG_BITS = 10 # Number of bits on analog pins


class Thermistor_Reader():
    
    def __init__(self, Arduino_pin, thermistor_model, board = None, com_port = None, ip_port=31335, buffer_size = 4, series_mode = 'VCC_Rth_R_GND', series_R_ohm = 1e4):
        
        
        self.Arduino_pin = Arduino_pin
        self.com_port = com_port
        self.ip_port = ip_port
        self.board = board
       

        # Store the model that translates thermistor value into temperature
        self.thermistor_model = thermistor_model
        
        # Initialize buffer for the data acquisition
        self._last_analog_values = deque(maxlen=buffer_size)  # Store the last n values, here n=5 for example
        
        # Resistors connection 
        self.series_R_ohm = series_R_ohm # Value of the constant resistor mounted in series with the thermistor
        self.series_mode = series_mode # Is the constant resistor before or after thermistor 
 
        
    def open_connection(self):
        
        if self.board is None:
            logger.debug('Open connection with Arduino board...')
            self.board = telemetrix.Telemetrix(com_port=self.com_port, ip_port=self.ip_port)
            self.board.set_pin_mode_analog_input(self.Arduino_pin, callback=self._analog_callback)
        elif isinstance(self.board, telemetrix.Telemetrix):
            logger.debug('Connection aready active with Arduino board.')
            self.board.set_pin_mode_analog_input(self.Arduino_pin, callback=self._analog_callback)
        else:
            raise Exception('Exception while trying to connect to the Arduino board')
            import traceback 
            traceback.print_exc()

    def close_connection(self):
        
        logger.debug('Close connection with Arduino board')
        self.board.shutdown()
        
    def set_pin_mode(self):
        logger.debug(f'Set pin mode {self.Arduino_pin} to analog_read')   
        self.board.set_pin_mode_analog_input(self.Arduino_pin, callback=self._analog_callback)
            
    def __enter__(self):
       """
       Enable use of the 'with' statement for safe connection handling.
       """
       self.open_connection()
       return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Ensure connection is closed when exiting the 'with' statement.
        """
        self.close_connection()
    
    def __del__(self):
        """
        Ensure connection is closed upon object destruction.
        """
        self.close_connection()
    
    def _analog_callback(self, data):
        """
        Callback function to handle analog input readings with sliding average.
        """
        _, new_analog_value = data[1], data[2]
        logger.debug(f"Raw analog value received: {new_analog_value}")
        
        # Append the new reading to the deque, automatically removing the oldest if at max length
        self._last_analog_values.append(new_analog_value)
        
        # Update temperature
        self._update_temperature() 
        
        # logger.debug(f"Raw analog value received: {analog_value}")
        # logger.debug(f"Smoothed analog value (last {len(self._last_analog_values)} readings): {_last_analog_value}")

    def _update_temperature(self):
        """
        Calculate the temperature based on the last analog reading.
        :param value: The temperature value to set.
        """
        thermistor_resistance = self.get_thermistor_resistance()
        if thermistor_resistance is None:
            logger.warning("No analog reading available.")
            self._temperature = None
        else:
            logger.debug(f'Thermistor resistance: {thermistor_resistance:.3f}')
            try:
                self._temperature = self.thermistor_model.get_temperature(thermistor_resistance)
                logger.debug(f"Calculated temperature: {self._temperature:.2f}°C")
            except:
                self._temperature = None
                logger.warning(f'Unknown value for temperature (thermistor resistance={thermistor_resistance:.2e})')
                import traceback 
                traceback.print_exc() 
    
    def get_thermistor_resistance(self):
        """
        Calculate the thermistor resistance from the analog reading, with the series resistor connected to VCC.
        """
        # Calculate the smoothed value as the average of the values in the deque
        analog_value = np.mean(self._last_analog_values)
        if analog_value is None:
            logger.warning("No analog reading available.")
            return None 
        
        # Calculate the voltage at the junction of the series resistor and thermistor
        voltage = analog_value * (ARDUINO_ANALOG_PIN_VOLTAGE / (2**ARDUINO_ANALOG_BITS-1))
        
        try:
            # Calculate the thermistor resistance using the voltage divider formula
            if self.series_mode == 'VCC_Rth_R_GND':
                thermistor_resistance = SERIES_RESISTOR * ((VCC - voltage) / voltage)
            elif self.series_mode == 'VCC_R_Rth_GND':
                thermistor_resistance = SERIES_RESISTOR * (voltage / (VCC - voltage))
            else:
                raise Exception(f'Unknown series connection mode: {self.series_mode}')
                
        except ZeroDivisionError:
            logger.error("Division by zero encountered while calculating thermistor resistance.")
            thermistor_resistance = float('inf')  # Set resistance to infinity if there's a division by zero
        
        logger.debug(f"Analog value: {analog_value}, voltage: {voltage:.2f}, Thermistor resistance: {thermistor_resistance:.2f}")
        return thermistor_resistance
    

    def get_temperature(self):
        """
        Get the temperature reading from the instrument.
        
        :return: The current temperature.
        """
        try:
            return self._temperature
        except AttributeError:
            logger.warning('Trying to access temperature from Thermistor while no measurement has been performed yet')
            return None
        



if __name__ == '__main__':
    
    # Constants
    THERMISTOR_PIN = 4 # Analog pin where thermistor is connected
    THERMISTOR_25C = 10000  # Value of the thermistor in ohms at 25°C
    SERIES_RESISTOR = 10000  # Value of the known resistor in ohms
    
    # Create thermistor model from datasheet
    # Load thermistor data
    file_path = "../../../Thermistor_R_vs_T.csv"
    resistance_column = 'Type 8016'
    thermistor_model = ThermistorModel(file_path, ref_R= THERMISTOR_25C, resistance_col_label=resistance_column)

    # Initialize the Thermistor
    thermistor = Thermistor_Reader(Arduino_pin=THERMISTOR_PIN, 
                                   thermistor_model = thermistor_model)
    
    
    if thermistor_model is None:
        logger.error("Thermistor data could not be loaded.")
    else:
        # Set pin mode and attach callback
        with Thermistor_Reader(4, thermistor_model) as thermistor_reader:
            try:
                while True:
                    temperature = thermistor_reader.get_temperature()
                    if temperature is not None:
                        print(f"Temperature: {temperature:.2f}°C")
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Telemetrix session ended.")
            except Exception:
                logger.info("Telemetrix session ended on unknown error.")
                import traceback 
                traceback.print_exc() 
