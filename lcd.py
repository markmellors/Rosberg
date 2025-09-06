from machine import Pin, SPI, PWM
import framebuf
import time
from pin_defs import LCD_CS, LCD_SCK, LCD_MOSI, LCD_DC, LCD_RST, LCD_BL
from pin_defs import BTN_CTRL, BTN_UP, BTN_A, BTN_L, BTN_B, BTN_X, BTN_R, BTN_Y, BTN_DOWN

# Color constants
WHITE = 0xFFFF
BLACK = 0x0000
RED   = 0xF800

# Button GPIO map
BUTTONS = {
    "CTRL": BTN_CTRL,
    "UP": BTN_UP,
    "A": BTN_A,
    "L": BTN_L,
    "B": BTN_B,
    "X": BTN_X,
    "R": BTN_R,
    "Y": BTN_Y,
    "DOWN": BTN_DOWN,
}


class LCD_1inch3:
    def __init__(self):
        # SPI & Pin config
        self.width = 240
        self.height = 240
        self.spi = SPI(1, baudrate=40_000_000, sck=Pin(LCD_SCK), mosi=Pin(LCD_MOSI))
        self.cs = Pin(Pin(LCD_CS), Pin.OUT)
        self.dc = Pin(Pin(LCD_DC), Pin.OUT)
        self.rst = Pin(Pin(LCD_RST), Pin.OUT)
        self.bl = PWM(Pin(LCD_BL))

        # Framebuffer setup
        self.buffer = bytearray(self.width * self.height * 2)
        self.fb = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.RGB565)

        # Button setup
        self.buttons = {name: Pin(pin, Pin.IN, Pin.PULL_UP) for name, pin in BUTTONS.items()}

        self._init_display()
        self.set_backlight(65535)

    def _cmd(self, c):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([c]))
        self.cs(1)

    def _data(self, d):
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([d]))
        self.cs(1)

    def _init_display(self):
        self.rst(1); time.sleep(0.05)
        self.rst(0); time.sleep(0.05)
        self.rst(1); time.sleep(0.05)

        self._cmd(0x36); self._data(0x00)
        self._cmd(0x3A); self._data(0x05)
        self._cmd(0x11); time.sleep(0.12)
        self._cmd(0x29)
        self._cmd(0x21)
        
    def button_pressed(self, name):
        """Return True if named button is currently pressed."""
        pin = self.buttons.get(name)
        if pin is None:
            return False
        return not pin.value()  # Active LOW

    def set_backlight(self, brightness):
        self.bl.freq(1000)
        self.bl.duty_u16(brightness)

    def fill(self, color):
        self.fb.fill(color)

    def fill_rect(self, x, y, w, h, color):
        self.fb.fill_rect(x, y, w, h, color)

    def text(self, string, x, y, color):
        self.fb.text(string, x, y, color)

    def draw_text(self, font, text, x, y, color=0x0000):
        CHAR_WIDTH = font.WIDTH
        CHAR_HEIGHT = font.HEIGHT
        FONT_DATA = memoryview(font.FONT)
        BYTES_PER_ROW = CHAR_WIDTH // 8
        BYTES_PER_CHAR = CHAR_HEIGHT * BYTES_PER_ROW
        FONT_LEN = len(FONT_DATA)

        cursor_x = x
        cursor_y = y

        for ch in text:
            if ch == '\n':
                cursor_x = x  # Reset to starting x
                cursor_y += CHAR_HEIGHT + 1  # Move to next line
                continue

            ch_ord = ord(ch)
            offset = ch_ord * BYTES_PER_CHAR

            if ch_ord < 0 or offset + BYTES_PER_CHAR > FONT_LEN:
                print(f"Skipping unsupported char '{ch}' (ord: {ch_ord})")
                continue

            glyph = FONT_DATA[offset : offset + BYTES_PER_CHAR]

            for row in range(CHAR_HEIGHT):
                row_offset = row * BYTES_PER_ROW

                if BYTES_PER_ROW == 1:
                    bits = glyph[row_offset]
                elif BYTES_PER_ROW == 2:
                    bits = (glyph[row_offset] << 8) | glyph[row_offset + 1]
                else:
                    print(f"Unsupported font width: {CHAR_WIDTH}")
                    continue

                for col in range(CHAR_WIDTH):
                    if bits & (1 << (CHAR_WIDTH - 1 - col)):
                        self.fb.pixel(cursor_x + col, cursor_y + row, color)

            cursor_x += CHAR_WIDTH + 1  # Advance to next char position
        
    def show(self):
        # Swap R and B bytes in place (convert RGB565 → BGR565)
        for i in range(0, len(self.buffer), 2):
            self.buffer[i], self.buffer[i+1] = self.buffer[i+1], self.buffer[i]
    
        # Now continue with the normal RAM write...
        self._cmd(0x2A)
        self._data(0 >> 8); self._data(0 & 0xFF)
        self._data((self.width - 1) >> 8); self._data((self.width - 1) & 0xFF)

        self._cmd(0x2B)
        self._data(0 >> 8); self._data(0 & 0xFF)
        self._data((self.height - 1) >> 8); self._data((self.height - 1) & 0xFF)

        self._cmd(0x2C)
        self.dc(1); self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

