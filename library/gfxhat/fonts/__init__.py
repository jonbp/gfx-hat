"""Basic font helper module.

Exposes the bundled fonts as module-level paths, eg: ``fonts.AmaticSC``,
suitable for passing straight to ``PIL.ImageFont.truetype`` or a BDF loader.

The bitmap fonts (Bitbuntu, Bitocra) are bundled here and have no equivalent
in fonts-python, so the fonts ship with this library rather than as external
dependencies.
"""
import os

font_directory = os.path.abspath(os.path.dirname(__file__))


def _font(filename):
    return os.path.join(font_directory, filename)


# Explicit font definitions keep the names visible to linters/IDEs rather
# than injecting them into globals() at import time.
AmaticSC = _font('AmaticSC-Regular.ttf')
AmaticSCBold = _font('AmaticSC-Bold.ttf')
Bitbuntu = _font('Bitbuntu.bdf')
BitbuntuFull = _font('Bitbuntu-Full.bdf')
Bitocra13Full = _font('Bitocra-13-Full.bdf')
BitocraFull = _font('Bitocra-Full.bdf')
FredokaOne = _font('FredokaOne-Regular.ttf')
PressStart2P = _font('PressStart2P-Regular.ttf')

font_files = {
    'AmaticSC': AmaticSC,
    'AmaticSCBold': AmaticSCBold,
    'Bitbuntu': Bitbuntu,
    'BitbuntuFull': BitbuntuFull,
    'Bitocra13Full': Bitocra13Full,
    'BitocraFull': BitocraFull,
    'FredokaOne': FredokaOne,
    'PressStart2P': PressStart2P,
}


def load_fonts(extension=None):
    """Return the mapping of bundled font names to file paths.

    Retained for backwards compatibility; fonts are now defined explicitly
    at module level and are available as soon as this module is imported.

    :param extension: Unused, kept for backwards compatibility

    """
    return font_files
