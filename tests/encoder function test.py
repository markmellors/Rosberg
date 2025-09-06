from machine import Pin
import time

A = Pin(2, Pin.IN, Pin.PULL_UP)
B = Pin(3, Pin.IN, Pin.PULL_UP)

count = 0
prev = (A.value() << 1) | B.value()

# Pre-allocate everything used in IRQ
TRANS = bytearray((
    0,255,  1,0,
    1,0,    0,255,
    255,0,  0,1,
    0,1,    255,0
))
# Map 255 -> -1 without allocs
def _delta(idx):
    d = TRANS[idx]
    return -1 if d == 255 else d

def _state():
    return (A.value() << 1) | B.value()

def _irq(_pin):
    # Hard IRQ safe: no allocations, no prints
    global prev, count
    curr = _state()
    idx = (prev << 2) | curr
    d = _delta(idx)
    if d != 0:
        count += d
        prev = curr
    else:
        prev = curr

A.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=_irq, hard=True)
B.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=_irq, hard=True)

# main loop
last = count
t0 = time.ticks_ms()
while True:
    time.sleep_ms(200)
    c = count
    dt = time.ticks_diff(time.ticks_ms(), t0) or 1
    dc = c - last
    print("count:", c, " rate:", (dc*1000)/dt)
    last = c
    t0 = time.ticks_ms()
