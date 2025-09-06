
from lcd import LCD_1inch3, WHITE, BLACK
import vga2_8x16 as font
import system_state

lcd = LCD_1inch3()

def update_display():
    lcd.fill(WHITE)
    y = 0
    for line in system_state.display_lines:
        lcd.draw_text(font, line, 5, y, BLACK)
        y += font.HEIGHT + 2
    draw_button_labels()
    lcd.show()

def force_display():
    lcd.fill(0x8CBD)  # Light blue background to indicate paused screen
    y = 0
    for line in system_state.display_lines:
        lcd.draw_text(font, line, 5, y, BLACK)
        y += font.HEIGHT + 2
    draw_button_labels()
    lcd.show()

def draw_button_labels():
    # Row just above bottom
    lcd.draw_text(font, "screen", 30, 200, BLACK)
    lcd.draw_text(font, "logging", 150, 200, BLACK)

    # Bottom row
    lcd.draw_text(font, "start", 10, 220, BLACK)
    lcd.draw_text(font, "stop", 70, 220, BLACK)
    lcd.draw_text(font, "start", 130, 220, BLACK)
    lcd.draw_text(font, "stop", 190, 220, BLACK)


