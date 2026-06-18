"""Shared, thread-safe state for the GFX HAT simulator.

A single :class:`Device` instance models everything the real hardware
exposes to the ``gfxhat`` library:

* the 128x64 ST7567 LCD frame buffer (in the chip's native page layout)
* the six-zone RGB backlight (SN3218)
* the six button LEDs and their global brightness (CAP1166)
* the registry of touch-button event handlers

The fake hardware modules (``fake_*``) write into this state, and the GUI
(:mod:`gfxhat_sim.render`) reads from it to draw each frame. All access is
guarded by a lock because the user's script runs on a worker thread while
the GUI runs on the main thread.
"""
import threading

WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8

NUM_BUTTONS = 6
NUM_ZONES = 6

# gfxhat.touch button constants, indexed 0..5
BUTTON_NAMES = ['up', 'down', 'back', 'minus', 'select', 'plus']
BUTTON_LABELS = ['UP', 'DOWN', 'BACK', 'MINUS / LEFT', 'SELECT / ENTER', 'PLUS / RIGHT']

EVENTS = ('press', 'release', 'held')


class Device:
    """Holds the full simulated hardware state behind a single lock."""

    def __init__(self):
        self._lock = threading.RLock()

        # ST7567 frame buffer, native layout: byte = (y // 8) * WIDTH + x,
        # bit = y % 8. Matches gfxhat.st7567 exactly.
        self.framebuffer = bytearray(WIDTH * PAGES)
        self.contrast = 42  # matches gfxhat.st7567 ST7567_DEFAULT_CONTRAST
        self.display_on = True
        self.display_inverse = False

        # Backlight: six (r, g, b) zones, left to right.
        self.backlight = [(0, 0, 0) for _ in range(NUM_ZONES)]

        # Button LEDs: per-button on/off plus a single global brightness
        # (the CAP1166 only has one global duty-cycle control).
        self.leds = [False for _ in range(NUM_BUTTONS)]
        self.led_brightness = 1.0

        # Touch handlers: {channel: {event: [handler, ...]}}
        self._handlers = {}
        self._held = [False for _ in range(NUM_BUTTONS)]

    # -- LCD -------------------------------------------------------------
    def write_page_data(self, page, col, data):
        """Write a run of data bytes into the frame buffer for one page.

        :param page: page index (0..7)
        :param col: starting column
        :param data: iterable of byte values
        :returns: the column position after the written run

        """
        with self._lock:
            base = page * WIDTH
            for value in data:
                if 0 <= col < WIDTH:
                    self.framebuffer[base + col] = value & 0xff
                col += 1
            return col

    def get_pixel(self, x, y):
        """Return the on/off state (0 or 1) of one LCD pixel."""
        offset = (y // 8) * WIDTH + x
        return (self.framebuffer[offset] >> (y % 8)) & 1

    def snapshot_framebuffer(self):
        """Return an immutable copy of the frame buffer for rendering."""
        with self._lock:
            return bytes(self.framebuffer)

    def clear_lcd(self):
        with self._lock:
            self.framebuffer = bytearray(WIDTH * PAGES)

    # -- Backlight -------------------------------------------------------
    def set_backlight_buffer(self, buf):
        """Decode an 18-byte SN3218 buffer into six RGB zones.

        Mirrors the channel ordering used by ``gfxhat.backlight``:
        zone display order is remapped via ``LED_MAP`` and each zone is
        stored as ``b, g, r``.
        """
        led_map = [2, 1, 0, 5, 4, 3]
        with self._lock:
            zones = []
            for display in range(NUM_ZONES):
                base = led_map[display] * 3
                b, g, r = buf[base], buf[base + 1], buf[base + 2]
                zones.append((r, g, b))
            self.backlight = zones

    def snapshot_backlight(self):
        with self._lock:
            return list(self.backlight)

    # -- Button LEDs -----------------------------------------------------
    def set_led(self, cap_channel, state):
        """Set a button LED by its CAP1166 channel.

        ``gfxhat.touch`` maps button index ``i`` to CAP channel ``5 - i``
        (``LED_MAPPING``), so we invert that to recover the button index.
        """
        button = 5 - cap_channel
        if 0 <= button < NUM_BUTTONS:
            with self._lock:
                self.leds[button] = bool(state)

    def set_led_brightness(self, brightness):
        with self._lock:
            self.led_brightness = max(0.0, min(1.0, brightness))

    def snapshot_leds(self):
        with self._lock:
            return list(self.leds), self.led_brightness

    # -- Touch handlers --------------------------------------------------
    def register_handler(self, channel, event, handler):
        with self._lock:
            self._handlers.setdefault(channel, {}).setdefault(event, []).append(handler)

    def _dispatch(self, channel, event):
        with self._lock:
            handlers = list(self._handlers.get(channel, {}).get(event, []))
        for handler in handlers:
            try:
                handler(channel, event)
            except SystemExit:
                raise
            except Exception as exception:  # noqa: BLE001 - surface, don't crash GUI
                import traceback
                print("Error in touch handler for channel {} ({}):".format(channel, event))
                traceback.print_exc()
                del exception

    def press(self, channel):
        """Simulate a button press (and start a held state)."""
        if not self._held[channel]:
            self._held[channel] = True
            self._dispatch(channel, 'press')

    def release(self, channel):
        """Simulate a button release."""
        if self._held[channel]:
            self._held[channel] = False
            self._dispatch(channel, 'release')

    def is_held(self, channel):
        return self._held[channel]


#: The process-wide singleton used by both the fakes and the GUI.
device = Device()
