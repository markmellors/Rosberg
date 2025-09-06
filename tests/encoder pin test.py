from machine import Pin
import time

# Configure pins as inputs with pull-ups (depends on your sensor wiring)
encoder_A = Pin(2, Pin.IN, Pin.PULL_UP)
encoder_B = Pin(3, Pin.IN, Pin.PULL_UP)

while True:
    a_state = encoder_A.value()
    b_state = encoder_B.value()
    print("A:", a_state, "B:", b_state)
    time.sleep(0.1)  # 100 ms update
