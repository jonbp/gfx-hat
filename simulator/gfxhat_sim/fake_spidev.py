"""A fake ``spidev`` that decodes the ST7567 command/data stream.

The real GFX HAT LCD is driven entirely over SPI: ``gfxhat.st7567`` sends
command bytes (DC pin low) to position the page/column cursor and set
options, then data bytes (DC pin high) that are the actual pixel pages.

This module reconstructs the frame buffer by interpreting that exact byte
stream, so the unmodified driver runs against it as if it were silicon.
"""
from . import fake_rpi
from .device import device

# ST7567 command opcodes we care about (others are accepted and ignored).
_DISPOFF = 0xae
_DISPON = 0xaf
_SETPAGESTART = 0xb0          # 0xb0..0xb7
_SETCOLL = 0x00              # 0x00..0x0f, low column nibble
_SETCOLH = 0x10              # 0x10..0x1f, high column nibble
_DISPNORMAL = 0xa6
_DISPINVERSE = 0xa7
_SETCONTRAST = 0x81          # followed by one value byte


class SpiDev:
    """Stand-in for ``spidev.SpiDev`` that drives the simulated LCD."""

    def __init__(self, *args, **kwargs):
        self.max_speed_hz = 0
        self.mode = 0
        self._page = 0
        self._col = 0
        self._expect_contrast = False

    def open(self, bus, cs):
        """No-op: accept the bus/chip-select selection."""

    def close(self):
        """No-op."""

    def xfer(self, data):
        self.writebytes(data)
        return [0] * len(data)

    def xfer2(self, data):
        self.writebytes(data)
        return [0] * len(data)

    def writebytes(self, data):
        """Route a transfer to the command parser or the frame buffer."""
        if fake_rpi.is_command():
            self._handle_command(list(data))
        else:
            self._col = device.write_page_data(self._page, self._col, data)

    # spidev exposes writebytes2 on newer kernels; alias it.
    writebytes2 = writebytes

    def _handle_command(self, data):
        for byte in data:
            if self._expect_contrast:
                device.contrast = byte
                self._expect_contrast = False
                continue

            if byte == _SETCONTRAST:
                self._expect_contrast = True
            elif _SETPAGESTART <= byte <= _SETPAGESTART + 7:
                self._page = byte - _SETPAGESTART
            elif _SETCOLL <= byte <= _SETCOLL + 0x0f:
                self._col = (self._col & 0xf0) | (byte - _SETCOLL)
            elif _SETCOLH <= byte <= _SETCOLH + 0x0f:
                self._col = (self._col & 0x0f) | ((byte - _SETCOLH) << 4)
            elif byte == _DISPON:
                device.display_on = True
            elif byte == _DISPOFF:
                device.display_on = False
            elif byte == _DISPNORMAL:
                device.display_inverse = False
            elif byte == _DISPINVERSE:
                device.display_inverse = True
            # All other commands (bias, power, RMW enter/exit, etc.) are
            # accepted and have no visible effect in the simulator.
