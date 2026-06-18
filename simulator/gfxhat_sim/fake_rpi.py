"""A minimal fake of ``RPi.GPIO`` for the simulator.

The ST7567 driver toggles the data/command (DC) pin around each SPI
transfer. We record that pin's state here so the fake ``spidev`` knows
whether incoming bytes are commands or pixel data. Everything else is a
no-op.
"""
from .device import device

# Constants the library reads off the module.
BCM = 'BCM'
BOARD = 'BOARD'
OUT = 'OUT'
IN = 'IN'
HIGH = 1
LOW = 0

# Pins used by gfxhat.st7567.
PIN_DC = 6

# Tracked pin output states, exposed for the fake spidev.
pin_state = {}


def setmode(mode):
    """No-op: accept the pin numbering mode."""


def setwarnings(flag):
    """No-op: accept the warnings flag."""


def setup(pin, mode, **kwargs):
    """No-op: accept a pin direction configuration."""
    pin_state.setdefault(pin, 0)


def output(pin, value):
    """Record a pin's output level; track DC for command/data routing."""
    pin_state[pin] = int(value)


def input(pin):
    return pin_state.get(pin, 0)


def cleanup(*args, **kwargs):
    pin_state.clear()


def is_command():
    """Return True if the DC pin is low (command mode)."""
    return pin_state.get(PIN_DC, 0) == 0


# Reference the shared device so the import side-effect graph mirrors the
# real modules; harmless but keeps linters from flagging the import.
_device = device
