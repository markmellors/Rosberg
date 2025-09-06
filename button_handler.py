import lcd
import system_state
import display_utils
from display_utils import lcd
import logging_utils
import time

def check_buttons(gps_data):
    if lcd.button_pressed("X"):
        system_state.display_enabled = False
        display_utils.force_display()
        time.sleep(0.2)

    if lcd.button_pressed("Y"):
        system_state.display_enabled = True

    if lcd.button_pressed("B") and not system_state.logging:
        logging_utils.start_logging(gps_data)

    if lcd.button_pressed("A") and system_state.logging:
        logging_utils.stop_logging()