from machine import Pin, I2C
import time
import struct

# I2C0 on GP2=SDA, GP3=SCL
i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=100000)

BNO055_ADDR = 0x28  # default when ADR pin = low

# Registers
CHIP_ID = 0x00
PAGE_ID = 0x07
OPR_MODE = 0x3D
PWR_MODE = 0x3E
UNIT_SEL = 0x3B

# Euler angles (little endian, 1/16° units)
EUL_HEADING = 0x1A
EUL_ROLL    = 0x1C
EUL_PITCH   = 0x1E

# Modes
CONFIGMODE = 0x00
NDOF       = 0x0C
PWR_NORMAL = 0x00

def write8(reg, val):
    i2c.writeto_mem(BNO055_ADDR, reg, bytes([val]))

def read8(reg):
    return i2c.readfrom_mem(BNO055_ADDR, reg, 1)[0]

def read16(reg):
    data = i2c.readfrom_mem(BNO055_ADDR, reg, 2)
    return struct.unpack('<h', data)[0]

def init_bno():
    # check chip ID
    cid = read8(CHIP_ID)
    print("Chip ID:", hex(cid))  # should be 0xA0

    # select page 0
    write8(PAGE_ID, 0x00)
    time.sleep_ms(10)

    # power mode normal
    write8(PWR_MODE, PWR_NORMAL)
    time.sleep_ms(10)

    # set units (optional, default is deg, dps, C)
    # write8(UNIT_SEL, 0x00)

    # operation mode = NDOF fusion
    write8(OPR_MODE, NDOF)
    time.sleep_ms(20)

init_bno()

while True:
    heading = read16(EUL_HEADING) / 16.0
    roll    = read16(EUL_ROLL)    / 16.0
    pitch   = read16(EUL_PITCH)   / 16.0
    print("Heading: %.2f  Roll: %.2f  Pitch: %.2f" % (heading, roll, pitch))
    time.sleep(0.2)
