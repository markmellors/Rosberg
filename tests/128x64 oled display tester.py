from machine import Pin, I2C
import ssd1306

# using default address 0x3C
i2c = I2C(1, sda=Pin(2), scl=Pin(3))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.text('Hello, World!', 0, 46, 1)
display.text('Hello, World!', 0, 55, 1)
display.show()