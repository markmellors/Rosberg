from machine import Pin, I2C
import time

# Use I2C1 on GP2 (SDA), GP3 (SCL)
i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000, timeout=200000)

print("Scanning I2C bus...")
while True:
    devices = i2c.scan()
    if devices:
        print("I2C devices found:", [hex(d) for d in devices])
    else:
        print("No I2C devices found")
    time.sleep(2)
