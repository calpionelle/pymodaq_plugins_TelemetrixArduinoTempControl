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
VCC = 5.0  # Supply voltage (5V for Arduino)
ARDUINO_ANALOG_PIN_VOLTAGE = 5  # Range of Arduino analog pin (5V)
ARDUINO_ANALOG_BITS = 10  # Number of bits on analog pins

class ThermistorReader:
    
    def __init__(self, pin, thR_model, board=None, com_port=None, ip_port=31335, buffer_size=4, series_mode='VCC_Rth_R_GND', series_resistor=1e4):
        self.pin = pin
        self.thR_model = thR_model
        self.board = board
        self.com_port = com_port
        self.ip_port = ip_port
        self.series_resistor = series_resistor
        self.series_mode = series_mode
        self._buffer = deque(maxlen=buffer_size)
        self._temperature = None

    def open_connection(self):
        if self.board is None:
            logger.debug('Establishing connection with Arduino...')
            self.board = telemetrix.Telemetrix(com_port=self.com_port, ip_port=self.ip_port)
        elif not isinstance(self.board, telemetrix.Telemetrix):
            raise ConnectionError("Invalid board instance provided.")
        
        self.board.set_pin_mode_analog_input(self.pin, callback=self._analog_callback)

    def close_connection(self):
        logger.debug('Closing Arduino connection...')
        if self.board:
            self.board.shutdown()
            self.board = None

    def __enter__(self):
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    def _analog_callback(self, data):
        analog_value = data[2]
        logger.debug(f"Received analog value: {analog_value}")
        self._buffer.append(analog_value)
        self._update_temperature()

    def _update_temperature(self):
        resistance = self.calculate_thermistor_resistance()
        if resistance is None:
            logger.warning("No analog reading available.")
            self._temperature = None
        else:
            try:
                self._temperature = self.thR_model.get_temperature(resistance)
                logger.debug(f"Calculated temperature: {self._temperature:.2f}°C")
            except Exception as e:
                logger.warning(f"Temperature calculation error: {e}")
                self._temperature = None

    def calculate_thermistor_resistance(self):
        if not self._buffer:
            logger.warning("No data available for resistance calculation.")
            return None
        
        avg_value = np.mean(self._buffer)
        voltage = avg_value * (ARDUINO_ANALOG_PIN_VOLTAGE / (2**ARDUINO_ANALOG_BITS - 1))
        
        try:
            if self.series_mode == 'VCC_Rth_R_GND':
                resistance = self.series_resistor * ((VCC - voltage) / voltage)
            elif self.series_mode == 'VCC_R_Rth_GND':
                resistance = self.series_resistor * (voltage / (VCC - voltage))
            else:
                raise ValueError(f"Unknown series mode: {self.series_mode}")
            logger.debug(f"Analog avg: {avg_value}, Voltage: {voltage:.2f}V, Resistance: {resistance:.2f}Ω")
            return resistance
        except ZeroDivisionError:
            logger.error("Division by zero encountered during resistance calculation.")
            return float('inf')

    def get_temperature(self):
        return self._temperature

if __name__ == '__main__':
    THERMISTOR_PIN = 4  # Analog pin where thermistor is connected
    THERMISTOR_25C = 10000  # Resistance at 25°C
    SERIES_RESISTOR = 10000  # Known resistor in ohms

    # Load thermistor model from CSV file
    file_path = "../../../Thermistor_R_vs_T.csv"
    resistance_column = 'Type 8016'
    thR_model = ThermistorModel(file_path, ref_R=THERMISTOR_25C, resistance_col_label=resistance_column)

    with ThermistorReader(THERMISTOR_PIN, thR_model, series_resistor=SERIES_RESISTOR) as thermistor_reader:
        try:
            while True:
                temperature = thermistor_reader.get_temperature()
                if temperature is not None:
                    print(f"Temperature: {temperature:.2f}°C")
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Session ended.")
        except Exception as e:
            logger.error(f"Error: {e}")
