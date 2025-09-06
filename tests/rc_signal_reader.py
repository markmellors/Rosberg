# minimal_rc_reader.py

from machine import Pin, time_pulse_us
from pin_defs import RC_STEERING, RC_MODE
import time

# Set up input pins using the same pin assignments
rc_pins = {
    "steering": Pin(RC_STEERING, Pin.IN),
    "mode":     Pin(RC_MODE, Pin.IN),
}

# Default RC input values
rc_inputs = {
    "steering": 1500,
    "mode":     1000,
}

# Function to read RC inputs (copied from rover_control.py)
def read_rc_inputs():
    for key, pin in rc_pins.items():
        try:
            pulse = time_pulse_us(pin, 1, 15000)  # 20ms timeout
            if 900 < pulse < 2200:  # valid range check
                rc_inputs[key] = pulse
        except OSError:
            pass  # ignore timeout errors


# Loop to continuously read and print RC values
while True:
    read_rc_inputs()
    print("Steering:", rc_inputs["steering"], 
          "Mode:", rc_inputs["mode"])
    time.sleep(0.1)
