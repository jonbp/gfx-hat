"""GFX HAT desktop simulator.

Importing this package installs fake hardware modules into ``sys.modules``
so that the unmodified ``gfxhat`` library (and any program written against
it) runs on a normal desktop, driving an on-screen GUI instead of real
silicon.

Typical use::

    python -m gfxhat_sim path/to/your_script.py

Importing :mod:`gfxhat_sim` for its side effects is enough to make
``import gfxhat`` work; the GUI is started by :mod:`gfxhat_sim.__main__`.
"""
import os
import sys

__version__ = '1.0.0'

_installed = False


def _add_library_to_path():
    """Make the bundled ``gfxhat`` library importable if it isn't already."""
    try:
        import gfxhat  # noqa: F401
        return
    except ImportError:
        pass

    here = os.path.dirname(os.path.abspath(__file__))
    library = os.path.normpath(os.path.join(here, '..', '..', 'library'))
    if os.path.isdir(os.path.join(library, 'gfxhat')) and library not in sys.path:
        sys.path.insert(0, library)


def _install_pillow_shim():
    """Restore ``ImageFont.getsize`` for examples written against old Pillow.

    Pillow 10 removed ``FreeTypeFont.getsize``; the bundled examples still
    call it. We add a thin shim based on ``getbbox`` so those examples run
    unmodified. No-op on Pillow versions that still provide ``getsize``.
    """
    try:
        from PIL import ImageFont
    except ImportError:
        return

    font_cls = getattr(ImageFont, 'FreeTypeFont', None)
    if font_cls is None or hasattr(font_cls, 'getsize'):
        return

    def getsize(self, text, *args, **kwargs):
        left, top, right, bottom = self.getbbox(text, *args, **kwargs)
        return (right - left, bottom - top)

    font_cls.getsize = getsize


def _install_signal_shim():
    """Tolerate ``signal.signal`` being called off the main thread.

    Programs written for the HAT routinely install SIGINT/SIGTERM handlers
    so Ctrl+C can clean up. The simulator runs the user's program on a
    worker thread (the GUI owns the main thread), and CPython only allows
    ``signal.signal`` on the main thread. We swallow such calls from worker
    threads so the program keeps running; the GUI handles quitting.
    """
    import signal
    import threading

    real_signal = signal.signal

    def safe_signal(signalnum, handler):
        if threading.current_thread() is threading.main_thread():
            return real_signal(signalnum, handler)
        return None  # ignored: not the main thread

    signal.signal = safe_signal


def install():
    """Install the fake hardware modules. Safe to call more than once."""
    global _installed
    if _installed:
        return

    _add_library_to_path()
    _install_pillow_shim()
    _install_signal_shim()

    from . import fake_rpi, fake_spidev, fake_cap1xxx, fake_sn3218

    # RPi.GPIO is a submodule import; provide both the package and submodule.
    import types
    rpi_pkg = types.ModuleType('RPi')
    rpi_pkg.GPIO = fake_rpi
    sys.modules['RPi'] = rpi_pkg
    sys.modules['RPi.GPIO'] = fake_rpi

    sys.modules['spidev'] = fake_spidev
    sys.modules['cap1xxx'] = fake_cap1xxx
    sys.modules['sn3218'] = fake_sn3218

    _installed = True


# Install on import so ``import gfxhat_sim`` is enough.
install()
