"""A fake ``sn3218`` 18-channel LED driver for the RGB backlight.

``gfxhat.backlight`` packs its six RGB zones into an 18-byte buffer and
calls :func:`output`. We hand that straight to the shared device, which
decodes it into per-zone colours for the GUI.
"""
from .device import device


def enable():
    """No-op: power on the LED driver."""


def disable():
    """No-op."""


def enable_leds(mask):
    """No-op: accept the per-channel enable mask."""


def output(buf):
    """Push an 18-byte brightness buffer to the simulated backlight."""
    device.set_backlight_buffer(list(buf))


def reset():
    """No-op."""
