"""Entry point for the GFX HAT simulator.

Usage::

    python -m gfxhat_sim                 # run the built-in demo
    python -m gfxhat_sim some_script.py  # run a program written for gfxhat

The GUI must own the main thread (a Tk requirement, especially on macOS),
so the target program runs on a daemon worker thread while the window's
event loop runs here. Closing the window ends the process.
"""
import os
import runpy
import sys
import threading

import gfxhat_sim  # noqa: F401 - importing installs the fake hardware modules
from .render import Simulator


def _run_script(path):
    """Execute a user program as if it were ``__main__``."""
    # Make the script's own directory importable, like normal execution.
    script_dir = os.path.dirname(os.path.abspath(path))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    try:
        runpy.run_path(path, run_name='__main__')
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except Exception:  # noqa: BLE001 - report, but keep the GUI usable
        import traceback
        traceback.print_exc()


def _run_demo():
    """A small built-in program so the simulator does something on its own."""
    import time
    import colorsys
    from gfxhat import lcd, backlight, touch, fonts
    from PIL import Image, ImageDraw, ImageFont

    width, height = lcd.dimensions()
    image = Image.new('P', (width, height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(fonts.AmaticSCBold, 28)

    led_states = [False] * 6

    def handler(channel, event):
        if event == 'press':
            led_states[channel] = not led_states[channel]
            touch.set_led(channel, led_states[channel])

    for channel in range(6):
        touch.on(channel, handler)

    title = 'GFX HAT'
    subtitle = 'Simulator'
    try:
        tw = draw.textlength(title, font=font)
    except AttributeError:
        tw = font.getsize(title)[0]

    start = time.time()
    while True:
        t = time.time() - start

        # Cycle the backlight through a rainbow.
        for zone in range(6):
            hue = (t * 0.15 + zone / 6.0) % 1.0
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
            backlight.set_pixel(zone, r, g, b)
        backlight.show()

        # Draw the title and a little bouncing marker.
        image.paste(0, (0, 0, width, height))
        draw.text(((width - tw) / 2, 6), title, 1, font)
        draw.text((width / 2 - 28, 38), subtitle, 1,
                  ImageFont.truetype(fonts.AmaticSC, 18))
        bx = int((width - 8) * (0.5 + 0.5 * __import__('math').sin(t * 2)))
        draw.rectangle((bx, height - 6, bx + 6, height - 2), 1)

        for x in range(width):
            for y in range(height):
                lcd.set_pixel(x, y, image.getpixel((x, y)))
        lcd.show()

        time.sleep(1.0 / 30)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv:
        script = argv[0]
        if not os.path.isfile(script):
            print("error: no such script: {}".format(script), file=sys.stderr)
            return 2
        # Hand the rest of the args to the script.
        sys.argv = [script] + argv[1:]
        target = lambda: _run_script(script)  # noqa: E731
        title = 'GFX HAT Simulator - {}'.format(os.path.basename(script))
    else:
        target = _run_demo
        title = 'GFX HAT Simulator - demo'

    worker = threading.Thread(target=target, daemon=True)
    worker.start()

    sim = Simulator(title=title)
    sim.run()

    # Window closed: tear everything down (the worker is a daemon thread
    # that may be blocked in signal.pause() or an infinite loop).
    os._exit(0)


if __name__ == '__main__':
    sys.exit(main())
