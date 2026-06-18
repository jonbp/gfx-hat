#!/usr/bin/env python

import math
import time

from gfxhat import touch, lcd, backlight, fonts
from PIL import Image, ImageFont, ImageDraw

print("""set-image.py

This example shows the faster whole-frame workflow using lcd.set_image,
plus the hardware sleep and invert controls.

A ticking clock and date are drawn to a PIL image and pushed in one call
each tick - no per-pixel set_pixel loop required.

The SELECT and BACK button LEDs gently pulse to show which controls are
active (LED brightness is global to all touch LEDs in hardware).

  SELECT : toggle the display on/off (hardware sleep)
  BACK   : toggle inverse video (hardware, instant)

Press Ctrl+C to exit.

""")

width, height = lcd.dimensions()

# FredokaOne is a clean, rounded TTF that stays legible at small sizes.
font_time = ImageFont.truetype(fonts.FredokaOne, 24)
font_date = ImageFont.truetype(fonts.FredokaOne, 12)

# A 1-bit image maps straight onto the LCD buffer, so lcd.set_image has
# no colour conversion to do.
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)

state = {'display_on': True, 'inverse': False, 'dirty': True}

# Only these two controls do anything, so light just their button LEDs.
ACTIVE_LEDS = (touch.SELECT, touch.BACK)

# Seconds for one full LED "breath" (fade up and back down).
PULSE_PERIOD = 2.5


def draw_centred(text, font, y):
    """Draw text horizontally centred at vertical position y."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = (width - (right - left)) // 2 - left
    draw.text((x, y - top), text, 1, font=font)


def icon_chevron_left(cx, cy, s=5):
    """A left-pointing chevron button glyph."""
    draw.line((cx + s, cy - s, cx - s, cy), 1, width=2)
    draw.line((cx - s, cy, cx + s, cy + s), 1, width=2)


def icon_circle_dot(cx, cy, r=6):
    """A ring with a solid centre - the SELECT button glyph."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=1)


# A hand-tuned 12x12 crescent: symmetric and evenly weighted so it stays
# legible at LCD size, rather than the lopsided result of carving two discs.
_MOON = [
    '............',
    '...####.....',
    '..####......',
    '.####.......',
    '.####.......',
    '.####.......',
    '.####.......',
    '.####.......',
    '.####.......',
    '..####......',
    '...####.....',
    '............',
]


def icon_moon(cx, cy):
    """Sleep: a crescent moon drawn from a fixed pixel bitmap."""
    ox, oy = cx - 6, cy - 6
    for row, bits in enumerate(_MOON):
        for col, bit in enumerate(bits):
            if bit == '#':
                draw.point((ox + col, oy + row), 1)


def icon_contrast(cx, cy, r=6, inverted=False):
    """Invert: a circle with one half filled; the filled side flips."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    start, end = (90, 270) if inverted else (-90, 90)
    draw.pieslice((cx - r, cy - r, cx + r, cy + r), start, end, fill=1)


def render():
    draw.rectangle((0, 0, width, height), 0)

    draw_centred(time.strftime('%H:%M:%S'), font_time, 1)
    draw_centred(time.strftime('%a %d %b %Y'), font_date, 26)

    # Icon legend: [button] [action] for each control, split either side
    # of a vertical divider.
    draw.line((6, 44, width - 6, 44), 1)
    draw.line((width // 2, 47, width // 2, height - 2), 1)

    cy = 55
    icon_circle_dot(24, cy)
    icon_moon(44, cy)
    icon_chevron_left(88, cy)
    icon_contrast(108, cy, inverted=state['inverse'])

    lcd.set_image(image)
    lcd.show()


def handler(ch, event):
    if event != 'press':
        return

    if ch == touch.SELECT:
        state['display_on'] = not state['display_on']
        lcd.set_display(state['display_on'])
        state['dirty'] = True

    elif ch == touch.BACK:
        state['inverse'] = not state['inverse']
        lcd.invert(state['inverse'])
        state['dirty'] = True


for x in range(6):
    touch.on(x, handler)
    touch.set_led(x, 1 if x in ACTIVE_LEDS else 0)

backlight.set_all(0, 80, 255)
backlight.show()

try:
    last_drawn = None
    last_duty = None

    while True:
        now = time.time()

        # Gently pulse the active button LEDs. Brightness is a single global
        # duty in hardware (and only SELECT/BACK are lit), so we just breathe
        # it with a cosine and only write when the 4-bit duty actually changes.
        level = 0.12 + 0.88 * (0.5 - 0.5 * math.cos(now * 2 * math.pi / PULSE_PERIOD))
        duty = int(round(level * 15))
        if duty != last_duty:
            touch.set_led_brightness(level)
            last_duty = duty

        # Only redraw the LCD when the visible second changes or something
        # toggled - no point pushing identical frames at the pulse rate.
        if state['display_on']:
            stamp = time.strftime('%H:%M:%S')
            if stamp != last_drawn or state['dirty']:
                render()
                last_drawn = stamp
                state['dirty'] = False

        time.sleep(1.0 / 30)

except KeyboardInterrupt:
    pass

finally:
    backlight.set_all(0, 0, 0)
    backlight.show()
    for x in range(6):
        touch.set_led(x, 0)
    lcd.clear()
    lcd.show()
