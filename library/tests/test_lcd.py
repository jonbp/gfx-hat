# noqa D100
from unittest import mock
import pytest
from PIL import Image


def test_st7567_init(GPIO):
    """Test that the ST7567 initialises correctly."""
    from gfxhat import lcd

    lcd.st7567.setup()

    GPIO.setmode.assert_called_once_with(GPIO.BCM)
    GPIO.setup.assert_has_calls([
        mock.call(6, GPIO.OUT),
        mock.call(5, GPIO.OUT)
    ], any_order=True)


def test_st7567_rotate():
    """Test that the ST7567 rotate feature works."""
    from gfxhat import lcd

    lcd.rotation(0)
    lcd.set_pixel(0, 0, 1)
    assert lcd.get_rotation() == 0

    lcd.rotation(180)
    lcd.set_pixel(0, 0, 1)
    assert lcd.get_rotation() == 180

    with pytest.raises(ValueError):
        lcd.rotation(90)


def test_st7567_clear():
    """Test that clear doesn't explode."""
    from gfxhat import lcd

    lcd.clear()


def test_st7567_show(spidev):
    """Test that show tries to enter RMWMODE over SPI."""
    from gfxhat import lcd, st7567

    lcd.show()

    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_ENTER_RMWMODE])
    ])


def test_st7567_contrast(spidev):
    """Test that set_contrast tries to write over SPI."""
    from gfxhat import lcd, st7567

    lcd.contrast(11)

    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_SETCONTRAST, 11])
    ])


def test_st7567_contrast_clamped(spidev):
    """Test that out-of-range contrast values are clamped to 0-63."""
    from gfxhat import lcd, st7567

    lcd.contrast(999)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_SETCONTRAST, 63])
    ])

    lcd.contrast(-5)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_SETCONTRAST, 0])
    ])


def test_st7567_set_display(spidev):
    """Test that set_display sends DISPON/DISPOFF."""
    from gfxhat import lcd, st7567

    lcd.set_display(False)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_DISPOFF])
    ])

    lcd.set_display(True)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_DISPON])
    ])


def test_st7567_invert(spidev):
    """Test that invert sends DISPINVERSE/DISPNORMAL."""
    from gfxhat import lcd, st7567

    lcd.invert(True)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_DISPINVERSE])
    ])

    lcd.invert(False)
    spidev.SpiDev().writebytes.assert_has_calls([
        mock.call([st7567.ST7567_DISPNORMAL])
    ])


def test_st7567_set_image_wrong_size():
    """Test that set_image rejects images of the wrong size."""
    from gfxhat import lcd

    with pytest.raises(ValueError):
        lcd.set_image(Image.new('1', (64, 32)))


def test_st7567_set_image_matches_set_pixel():
    """Test that set_image packs the buffer identically to set_pixel."""
    from gfxhat import st7567

    width, height = st7567.WIDTH, st7567.HEIGHT

    image = Image.new('1', (width, height))
    pixels = image.load()
    for x in range(width):
        pixels[x, x % height] = 1  # a diagonal we can verify

    by_image = st7567.ST7567()
    by_image.rotated = False
    by_image.set_image(image)

    by_pixel = st7567.ST7567()
    by_pixel.rotated = False
    for x in range(width):
        for y in range(height):
            by_pixel.set_pixel(x, y, 1 if pixels[x, y] else 0)

    assert by_image.buf == by_pixel.buf


def test_st7567_dimensions(spidev):
    """Test that lcd.dimensions returns the constants defined in st7567."""
    from gfxhat import lcd, st7567

    assert lcd.dimensions() == (st7567.WIDTH, st7567.HEIGHT)
