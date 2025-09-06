# pin_defs.py
# Centralized GPIO assignments for all subsystems

# ==== LCD SPI Display ====
LCD_SCK     = 10
LCD_MOSI    = 11
LCD_CS      = 9
LCD_DC      = 8
LCD_RST     = 12
LCD_BL      = 13

# ==== Buttons ====
BTN_CTRL    = 0
BTN_R       = 1
BTN_UP      = 16
BTN_A       = 15
BTN_L       = 28
BTN_B       = 17
BTN_X       = 19
BTN_Y       = 21
BTN_DOWN    = 20

# ==== GPS (LC29H DA) ====
GPS_SDA     = 2
GPS_SCL     = 3
GPS_RX      = 4  # Pico receives on this pin
GPS_TX      = 5  # Pico transmits on this pin
GPS_PPS     = 18
GPS_WAKE    = 14
GPS_WIRES   = 27  # WI/RES pin, only use if needed

# ==== RC Receiver Inputs ====
RC_STEERING = 6
RC_MODE     = 7

# ==== Motor / Servo Outputs ====
STEER_PWM   = 22

# ==== Ultrasonic Sensor ====
ULTRASONIC_TRIG = 26
ULTRASONIC_ECHO = 25
