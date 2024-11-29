import time
import threading
import logging
from telemetrix import telemetrix

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Initialize the Telemetrix instance
board = telemetrix.Telemetrix()

# Define the LED pins
LED_PIN_1 = 8  # First LED pin
LED_PIN_2 = 2   # Second LED pin

# Set the pin modes to OUTPUT
board.set_pin_mode_digital_output(LED_PIN_1)
board.set_pin_mode_digital_output(LED_PIN_2)

# Create an event to signal threads to stop
stop_event = threading.Event()

def blink_led(pin, frequency):
    """Blink an LED on the specified pin at the given frequency."""
    logger.debug(f"Starting to blink LED on pin {pin} at {frequency} s")
    while not stop_event.is_set():
        board.digital_write(pin, 1)  # Turn the LED on
        logger.debug(f"LED on pin {pin} turned ON")
        time.sleep(frequency)         # Wait for the defined frequency
        board.digital_write(pin, 0)  # Turn the LED off
        logger.debug(f"LED on pin {pin} turned OFF")
        time.sleep(frequency)         # Wait for the defined frequency

if __name__ == '__main__':
    try:
        # Define the frequencies (in seconds)
        frequency_for_led_1 = 6  # Frequency for LED on pin 13 (1 Hz)
        frequency_for_led_2 = 11  # Frequency for LED on pin 2 (2 Hz)

        # Create threads for each LED
        thread1 = threading.Thread(target=blink_led, args=(LED_PIN_1, frequency_for_led_1))
        thread2 = threading.Thread(target=blink_led, args=(LED_PIN_2, frequency_for_led_2))

        # Start the threads
        thread1.start()
        thread2.start()

        logger.debug("LED blinking threads started.")

        # Keep the main thread running to allow the LEDs to blink
        while True:
            time.sleep(0.1)  # Adjust as needed to keep the main thread alive

    except KeyboardInterrupt:
        # Signal threads to stop
        stop_event.set()
        
        logger.debug("Received KeyboardInterrupt, stopping threads.")
        
        # Wait for threads to finish
        thread1.join()
        thread2.join()

        # Clean up the Telemetrix session
        board.shutdown()
        logger.debug("Telemetrix session ended.")
