# GFX HAT Simulator

A desktop GUI simulator for the [Pimoroni GFX HAT](https://shop.pimoroni.com/products/gfx-hat).

It lets you develop and run programs written for the `gfxhat` library on a
normal computer — no Raspberry Pi or HAT required. The simulator faithfully
models the real hardware:

* the **128×64 monochrome ST7567 LCD**
* the **6-zone RGB backlight** (SN3218)
* the **6 touch buttons** and their **button LEDs** (CAP1166)

Your program imports `gfxhat` exactly as it would on real hardware; the
simulator transparently stands in for the I²C/SPI/GPIO devices and renders
everything in a window.

## Requirements

* Python 3
* [Pillow](https://pypi.org/project/Pillow/)
* Tkinter (bundled with most Python installs; on some Linux distros it's a
  separate `python3-tk` package)

The bundled `gfxhat` library is found automatically — you do not need to
install it.

## Running

From the `simulator/` directory:

```bash
# Run the built-in demo
python -m gfxhat_sim

# Run a program written for the GFX HAT
python -m gfxhat_sim ../examples/hello-world.py
python -m gfxhat_sim ../examples/menu-options.py
```

Any extra arguments after the script path are passed through to it.

## Controls

Click a button on screen, or use the keyboard:

| Button         | Keys              |
| -------------- | ----------------- |
| UP             | `↑` / `W`         |
| DOWN           | `↓` / `S`         |
| BACK           | `Esc` / `B`       |
| MINUS / LEFT   | `←` / `A` / `-`   |
| SELECT / ENTER | `Enter` / `Space` / `E` |
| PLUS / RIGHT   | `→` / `D` / `+`   |

Press and hold work as you'd expect (press / held / release events fire just
like on hardware).

Other keys:

* `G` — toggle a light pixel-measuring grid over the LCD (off by default;
  faint lines per pixel, stronger every 8 px)
* `Q` — quit (or close the window)

## How it works

`gfxhat` talks to four hardware libraries: `RPi.GPIO`, `spidev`, `cap1xxx`,
and `sn3218`. On import, `gfxhat_sim` installs fake versions of these into
`sys.modules` before `gfxhat` loads, so the real, unmodified library runs
against them.

* `fake_spidev` **decodes the actual ST7567 command/data stream** (using the
  data/command pin tracked by `fake_rpi`) to reconstruct the LCD frame buffer
  — the same byte protocol the real chip receives.
* `fake_sn3218` decodes the 18-byte backlight buffer into six RGB zones.
* `fake_cap1xxx` records touch-event handlers and button-LED state.
* `device.py` holds all of this shared state behind a lock.
* `render.py` is a Tkinter GUI that polls the state ~30 fps and turns mouse
  clicks and key presses into touch events.

The GUI owns the main thread (required by Tk); your program runs on a worker
thread.

```
gfxhat_sim/
├── __init__.py      # installs the fake hardware modules on import
├── __main__.py      # entry point + built-in demo
├── device.py        # shared simulated hardware state
├── fake_rpi.py      # fake RPi.GPIO (tracks the DC pin)
├── fake_spidev.py   # fake spidev (decodes the ST7567 SPI stream)
├── fake_cap1xxx.py  # fake CAP1166 touch controller
├── fake_sn3218.py   # fake SN3218 backlight driver
├── keyboard.py      # keyboard → button mappings
└── render.py        # Tkinter GUI
```

## Note on the bundled examples

The examples in `../examples/` were written for an older Pillow and call the
removed `ImageFont.getsize`. The simulator restores a compatible `getsize`
shim on import, so they run unmodified here.
