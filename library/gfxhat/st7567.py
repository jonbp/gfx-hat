"""Library for the ST7567 128x64 SPI LCD."""
import RPi.GPIO as GPIO
import spidev
import time
import random

SPI_SPEED_HZ = 8000000

WIDTH = 128
HEIGHT = 64

PIN_CS = 8
PIN_RST = 5
PIN_DC = 6

ST7567_PAGESIZE = 128

ST7567_DISPOFF = 0xae         # 0xae: Display OFF (sleep mode) */
ST7567_DISPON = 0xaf          # 0xaf: Display ON in normal mode */

ST7567_SETSTARTLINE = 0x40    # 0x40-7f: Set display start line */
ST7567_STARTLINE_MASK = 0x3f

ST7567_REG_RATIO = 0x20

ST7567_SETPAGESTART = 0xb0    # 0xb0-b7: Set page start address */
ST7567_PAGESTART_MASK = 0x07

ST7567_SETCOLL = 0x00         # 0x00-0x0f: Set lower column address */
ST7567_COLL_MASK = 0x0f
ST7567_SETCOLH = 0x10         # 0x10-0x1f: Set higher column address */
ST7567_COLH_MASK = 0x0f

ST7567_SEG_DIR_NORMAL = 0xa0  # 0xa0: Column address 0 is mapped to SEG0 */
ST7567_SEG_DIR_REV = 0xa1     # 0xa1: Column address 128 is mapped to SEG0 */

ST7567_DISPNORMAL = 0xa6      # 0xa6: Normal display */
ST7567_DISPINVERSE = 0xa7     # 0xa7: Inverse display */

ST7567_DISPRAM = 0xa4         # 0xa4: Resume to RAM content display */
ST7567_DISPENTIRE = 0xa5      # 0xa5: Entire display ON */

ST7567_BIAS_1_9 = 0xa2        # 0xa2: Select BIAS setting 1/9 */
ST7567_BIAS_1_7 = 0xa3        # 0xa3: Select BIAS setting 1/7 */

ST7567_ENTER_RMWMODE = 0xe0   # 0xe0: Enter the Read Modify Write mode */
ST7567_EXIT_RMWMODE = 0xee    # 0xee: Leave the Read Modify Write mode */
ST7567_EXIT_SOFTRST = 0xe2    # 0xe2: Software RESET */

ST7567_SETCOMNORMAL = 0xc0    # 0xc0: Set COM output direction, normal mode */
ST7567_SETCOMREVERSE = 0xc8   # 0xc8: Set COM output direction, reverse mode */

ST7567_POWERCTRL_VF = 0x29    # 0x29: Control built-in power circuit */
ST7567_POWERCTRL_VR = 0x2a    # 0x2a: Control built-in power circuit */
ST7567_POWERCTRL_VB = 0x2c    # 0x2c: Control built-in power circuit */
ST7567_POWERCTRL = 0x2f       # 0x2c: Control built-in power circuit */

ST7567_REG_RES_RR0 = 0x21     # 0x21: Regulation Resistior ratio */
ST7567_REG_RES_RR1 = 0x22     # 0x22: Regulation Resistior ratio */
ST7567_REG_RES_RR2 = 0x24     # 0x24: Regulation Resistior ratio */

ST7567_SETCONTRAST = 0x81     # 0x81: Set contrast control */

ST7567_SETBOOSTER = 0xf8      # Set booster level */
ST7567_SETBOOSTER4X = 0x00    # Set booster level */
ST7567_SETBOOSTER5X = 0x01    # Set booster level */

ST7567_NOP = 0xe3             # 0xe3: NOP Command for no operation */

ST7565_STARTBYTES = 0


class ST7567:
    """Class to drive the ST7567 128x64 SPI LCD."""

    def __init__(self, pin_rst=PIN_RST, pin_dc=PIN_DC, spi_bus=0, spi_cs=0, spi_speed=SPI_SPEED_HZ):
        """Initialise the ST7567 class.

        :param pin_rst: BCM GPIO pin number for reset
        :param pin_dc: BCM GPIO pin number for data/command
        :param spi_bus: SPI bus ID
        :param spi_cs: SPI chipselect ID (0/1 not BCM pin number)
        :param spi_speed: SPI speed (hz)

        """
        self._is_setup = False
        self.pin_rst = pin_rst
        self.pin_dc = pin_dc
        self.spi_bus = spi_bus
        self.spi_cs = spi_cs
        self.spi_speed = spi_speed

        self.rotated = False

        self.clear()

    def setup(self):
        """Set up GPIO and initialise the ST7567 device."""
        if self._is_setup:
            return True

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin_rst, GPIO.OUT)
        GPIO.setup(self.pin_dc, GPIO.OUT)

        self.spi = spidev.SpiDev()
        self.spi.open(self.spi_bus, self.spi_cs)
        self.spi.max_speed_hz = self.spi_speed

        self._reset()
        self._init()

        self._is_setup = True

    def dimensions(self):
        """Return the ST7567 display dimensions."""
        return (WIDTH, HEIGHT)

    def clear(self):
        """Clear the python display buffer."""
        self.buf = bytearray(WIDTH * HEIGHT // 8)

    def _command(self, data):
        GPIO.output(self.pin_dc, 0)
        self.spi.writebytes(data)

    def _data(self, data):
        GPIO.output(self.pin_dc, 1)
        self.spi.writebytes(data)

    def _reset(self):
        GPIO.output(self.pin_rst, 0)
        time.sleep(0.01)
        GPIO.output(self.pin_rst, 1)
        time.sleep(0.1)

    def _init(self):
        self._command([
            ST7567_BIAS_1_7,          # Bais 1/7 (0xA2 = Bias 1/9)
            ST7567_SEG_DIR_NORMAL,
            ST7567_SETCOMREVERSE,     # Reverse COM - vertical flip
            ST7567_DISPNORMAL,        # Inverse display (0xA6 normal)
            ST7567_SETSTARTLINE | 0,  # Start at line 0
            ST7567_POWERCTRL,
            ST7567_REG_RATIO | 3,
            ST7567_DISPON,
            ST7567_SETCONTRAST,       # Set contrast
            58                        # Contrast value
        ])

    def set_pixel(self, x, y, value):
        """Set a single pixel in the python display buffer.

        :param x: X position (from 0 to 127)
        :param y: Y position (from 0 to 63)
        :param value: pixel state 1 = On, 0 = Off

        """
        if self.rotated:
            x = (WIDTH - 1) - x
            y = (HEIGHT - 1) - y
        offset = ((y // 8) * WIDTH) + x
        bit = y % 8
        self.buf[offset] &= ~(1 << bit)
        self.buf[offset] |= (value & 1) << bit

    def set_image(self, image):
        """Copy a PIL image straight into the display buffer.

        This is dramatically faster than calling :meth:`set_pixel` for
        every pixel, as it packs the whole frame in one pass (using numpy
        when available, otherwise a pure-Python fallback).

        The image must match the display dimensions (128x64). It is
        converted to 1-bit mode if necessary; any non-zero pixel is "on".

        :param image: a PIL ``Image`` instance, 128x64 pixels

        """
        if tuple(image.size) != (WIDTH, HEIGHT):
            raise ValueError('image must be {}x{} pixels'.format(WIDTH, HEIGHT))

        if image.mode != '1':
            image = image.convert('1')

        if self.rotated:
            image = image.rotate(180)

        try:
            import numpy
            arr = numpy.unpackbits(numpy.frombuffer(image.tobytes(), dtype=numpy.uint8))
            arr = arr.reshape(HEIGHT // 8, 8, WIDTH)
            weights = (1 << numpy.arange(8, dtype=numpy.uint8)).reshape(1, 8, 1)
            packed = (arr * weights).sum(axis=1).astype(numpy.uint8)
            self.buf = bytearray(packed.flatten().tobytes())
        except ImportError:
            buf = bytearray(WIDTH * HEIGHT // 8)
            px = image.load()
            for page in range(HEIGHT // 8):
                base = page * WIDTH
                y0 = page * 8
                for x in range(WIDTH):
                    byte = 0
                    for bit in range(8):
                        if px[x, y0 + bit]:
                            byte |= 1 << bit
                    buf[base + x] = byte
            self.buf = buf

    def show(self):
        """Update the ST7567 display with the buffer contents."""
        self.setup()
        self._command([ST7567_ENTER_RMWMODE])
        for page in range(8):
            offset = page * ST7567_PAGESIZE
            self._command([ST7567_SETPAGESTART | page, ST7567_SETCOLL, ST7567_SETCOLH])
            self._data(self.buf[offset:offset + ST7567_PAGESIZE])
        self._command([ST7567_EXIT_RMWMODE])

    def contrast(self, value):
        """Update the ST7567 display contrast.

        :param value: contrast value from 0 to 63

        """
        self.setup()
        value = max(0, min(63, int(value)))
        self._command([ST7567_SETCONTRAST, value])

    def set_display(self, on):
        """Turn the display on or off.

        Turning the display off puts the panel into a low-power sleep
        state without losing the buffer contents.

        :param on: True to wake the display, False to sleep it

        """
        self.setup()
        self._command([ST7567_DISPON if on else ST7567_DISPOFF])

    def invert(self, value):
        """Invert the display in hardware.

        This swaps on/off pixels for the whole panel without modifying
        the buffer, so it's effectively instant.

        :param value: True for inverse, False for normal

        """
        self.setup()
        self._command([ST7567_DISPINVERSE if value else ST7567_DISPNORMAL])


if __name__ == '__main__':  # pragma: no cover
    st7567 = ST7567()
    st7567.setup()

    for x in range(64):
        st7567.set_pixel(x, x, 1)
        st7567.set_pixel(64 - x, x, 1)
        st7567.set_pixel(x + 2, x, 1)
    st7567.show()

    time.sleep(2.0)

    try:
        while True:
            for x in range(128):
                for y in range(64):
                    st7567.set_pixel(x, y, random.randint(0, 1))
            st7567.show()

    except KeyboardInterrupt:
        pass
