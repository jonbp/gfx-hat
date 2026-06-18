"""Tkinter GUI for the GFX HAT simulator.

Renders a board-accurate likeness of the GFX HAT: a black PCB with the
40-pin header along the top edge, the 2.15" LCD edge-lit by the six-zone
RGB backlight, and the six capacitive touch pads in a row below the screen
(up, down, back, minus, select, plus) each with its silkscreen icon and
white LED.

The GUI polls the shared :data:`device` state each frame; mouse clicks and
key presses are translated into touch events. The GUI owns the main thread;
the user's program runs on a worker thread (see :mod:`gfxhat_sim.__main__`).
"""
import tkinter as tk

from PIL import Image, ImageTk

from .device import device, WIDTH, HEIGHT, NUM_BUTTONS, NUM_ZONES
from . import keyboard

SCALE = 5
LCD_W = WIDTH * SCALE            # 640
LCD_H = HEIGHT * SCALE           # 320

# Board / window geometry.
OUTER = 18                       # gap between window edge and PCB
BOARD_PAD = 40                   # PCB border around its contents
HEADER_H = 26                    # 40-pin header strip
GLOW_H = 9                       # RGB backlight glow strip thickness
GAP_TOP = 48                     # header -> LCD (room for the GFX HAT label)
GAP_MID = 30                     # LCD -> buttons
PAD = 86                         # touch pad size (square)
BUTTON_AREA_H = PAD + 26         # pad + key hint text

BOARD_W = LCD_W + 2 * BOARD_PAD
BOARD_H = (HEADER_H + GAP_TOP + GLOW_H + LCD_H + GLOW_H + GAP_MID
           + BUTTON_AREA_H + BOARD_PAD)
CANVAS_W = BOARD_W + 2 * OUTER
CANVAS_H = BOARD_H + 2 * OUTER

# Colours.
PANEL = (168, 178, 156)          # unlit LCD glass, slightly green-grey
PIXEL_ON = (18, 22, 28)          # a lit (dark) pixel
WINDOW_BG = '#2a2d33'            # desk behind the board
BOARD_FILL = '#0c0d10'           # black PCB
BOARD_EDGE = '#34373d'
PAD_FILL = '#15171c'
PAD_EDGE = '#3a3e46'
PAD_PRESSED = '#23364a'
ICON_IDLE = '#c6cad2'
SILK = '#6f7682'                 # silkscreen text colour
LED_WHITE = (236, 242, 250)      # white touch LED
GRID_MINOR = '#9aa09a'           # per-pixel measuring grid
GRID_MAJOR = '#6f756f'           # every 8th line (LCD page boundary)

# Precompute which backlight zone lights each LCD column.
_COLUMN_ZONE = [min(NUM_ZONES - 1, (x * NUM_ZONES) // WIDTH) for x in range(WIDTH)]

# Touch pads, left to right, with the icon printed on the GFX HAT silkscreen.
PAD_ICONS = ['up', 'down', 'back', 'minus', 'select', 'plus']


def _blend(a, b, t):
    """Linear blend of two RGB tuples by factor t (0..1 -> a..b)."""
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _clamp8(v):
    return max(0, min(255, int(v)))


def _hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*[_clamp8(c) for c in rgb])


class Simulator:
    """The simulator window."""

    def __init__(self, title='GFX HAT Simulator'):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=WINDOW_BG)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg=WINDOW_BG, highlightthickness=0,
        )
        self.canvas.pack()

        # LCD position within the canvas.
        self._lcd_x = OUTER + BOARD_PAD
        self._lcd_y = OUTER + HEADER_H + GAP_TOP + GLOW_H

        # Touch pad hit rectangles: (channel, x0, y0, x1, y1).
        self._button_rects = []
        self._compute_button_rects()

        self._photo = None
        self._active_mouse_channel = None
        self._show_grid = False

        self._bind_events()
        self._schedule_redraw()

    # -- layout ----------------------------------------------------------
    def _compute_button_rects(self):
        top = self._lcd_y + LCD_H + GLOW_H + GAP_MID
        # Spread the pads evenly across the LCD width.
        slot = LCD_W / NUM_BUTTONS
        for channel in range(NUM_BUTTONS):
            cx = self._lcd_x + slot * (channel + 0.5)
            x0 = cx - PAD / 2
            x1 = cx + PAD / 2
            y0 = top
            y1 = top + PAD
            self._button_rects.append((channel, x0, y0, x1, y1))

    # -- events ----------------------------------------------------------
    def _bind_events(self):
        self.root.bind('<KeyPress>', self._on_key_press)
        self.root.bind('<KeyRelease>', self._on_key_release)
        self.canvas.bind('<ButtonPress-1>', self._on_mouse_down)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _on_key_press(self, event):
        key = event.keysym.lower()
        if key == 'q':
            self._on_close()
            return
        if key == 'g':
            self._show_grid = not self._show_grid
            return
        channel = keyboard.channel_for_keysym(event.keysym)
        if channel is not None:
            device.press(channel)

    def _on_key_release(self, event):
        channel = keyboard.channel_for_keysym(event.keysym)
        if channel is not None:
            device.release(channel)

    def _on_mouse_down(self, event):
        for channel, x0, y0, x1, y1 in self._button_rects:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self._active_mouse_channel = channel
                device.press(channel)
                return

    def _on_mouse_up(self, event):
        if self._active_mouse_channel is not None:
            device.release(self._active_mouse_channel)
            self._active_mouse_channel = None

    def _on_close(self):
        self.root.destroy()

    # -- canvas helpers --------------------------------------------------
    def _round_rect(self, x0, y0, x1, y1, r, **kwargs):
        """Draw a rounded rectangle as a smoothed polygon."""
        points = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_icon(self, name, cx, cy, size, color):
        """Draw a button's silkscreen icon centred at (cx, cy)."""
        c = self.canvas
        s = size / 2.0
        w = max(2, int(size / 8))
        if name == 'up':
            c.create_line(cx - s, cy + s * 0.45, cx, cy - s * 0.45,
                          cx + s, cy + s * 0.45, fill=color, width=w,
                          capstyle='round', joinstyle='round')
        elif name == 'down':
            c.create_line(cx - s, cy - s * 0.45, cx, cy + s * 0.45,
                          cx + s, cy - s * 0.45, fill=color, width=w,
                          capstyle='round', joinstyle='round')
        elif name == 'minus':
            c.create_line(cx - s, cy, cx + s, cy, fill=color,
                          width=w, capstyle='round')
        elif name == 'plus':
            c.create_line(cx - s, cy, cx + s, cy, fill=color,
                          width=w, capstyle='round')
            c.create_line(cx, cy - s, cx, cy + s, fill=color,
                          width=w, capstyle='round')
        elif name == 'select':
            c.create_oval(cx - s * 0.62, cy - s * 0.62,
                          cx + s * 0.62, cy + s * 0.62, fill=color, outline=color)
        elif name == 'back':
            # A chevron pointing left.
            c.create_line(cx + s * 0.45, cy - s, cx - s * 0.45, cy,
                          cx + s * 0.45, cy + s, fill=color, width=w,
                          capstyle='round', joinstyle='round')

    # -- rendering -------------------------------------------------------
    def _render_lcd_image(self):
        fb = device.snapshot_framebuffer()
        zones = device.snapshot_backlight()
        display_on = device.display_on
        inverse = device.display_inverse

        column_off = []
        for x in range(WIDTH):
            zone = zones[_COLUMN_ZONE[x]]
            intensity = sum(zone) / (3 * 255.0)
            base = _blend(PANEL, zone, 0.35 * intensity)
            column_off.append(_blend((150, 158, 140), base, 0.6))

        pixels = []
        for y in range(HEIGHT):
            row_base = (y // 8) * WIDTH
            bit = y % 8
            for x in range(WIDTH):
                on = (fb[row_base + x] >> bit) & 1
                if inverse:
                    on = not on
                if not display_on:
                    pixels.append(_blend(column_off[x], (40, 44, 40), 0.5))
                elif on:
                    pixels.append(PIXEL_ON)
                else:
                    pixels.append(column_off[x])

        img = Image.new('RGB', (WIDTH, HEIGHT))
        img.putdata(pixels)
        return img.resize((LCD_W, LCD_H), Image.NEAREST)

    def _draw_grid(self):
        """Overlay a light pixel-measuring grid on the LCD."""
        gx, gy = self._lcd_x, self._lcd_y
        for i in range(1, WIDTH):
            x = gx + i * SCALE
            color = GRID_MAJOR if i % 8 == 0 else GRID_MINOR
            self.canvas.create_line(x, gy, x, gy + LCD_H, fill=color)
        for j in range(1, HEIGHT):
            y = gy + j * SCALE
            color = GRID_MAJOR if j % 8 == 0 else GRID_MINOR
            self.canvas.create_line(gx, y, gx + LCD_W, y, fill=color)

    def _draw_header(self):
        """Draw the 40-pin GPIO header along the top edge of the board."""
        x0 = OUTER + BOARD_PAD
        x1 = OUTER + BOARD_W - BOARD_PAD
        y0 = OUTER + 6
        y1 = y0 + HEADER_H - 10
        self.canvas.create_rectangle(x0, y0, x1, y1, fill='#161616', outline='#000000')
        pins = 20
        step = (x1 - x0) / pins
        for i in range(pins):
            px = x0 + step * (i + 0.5)
            for row, py in ((0, y0 + 5), (1, y1 - 5)):
                self.canvas.create_rectangle(
                    px - 2, py - 2, px + 2, py + 2,
                    fill='#caa84a', outline='#8a722a',
                )

    def _redraw(self):
        if not self._window_alive():
            return
        self.canvas.delete('all')

        zones = device.snapshot_backlight()
        leds, brightness = device.snapshot_leds()

        # PCB.
        self._round_rect(
            OUTER, OUTER, OUTER + BOARD_W, OUTER + BOARD_H, 22,
            fill=BOARD_FILL, outline=BOARD_EDGE, width=2,
        )
        # Mounting holes in the corners.
        for hx in (OUTER + 16, OUTER + BOARD_W - 16):
            for hy in (OUTER + 16, OUTER + BOARD_H - 16):
                self.canvas.create_oval(hx - 5, hy - 5, hx + 5, hy + 5,
                                        fill='#000000', outline='#3a3e46')

        self._draw_header()

        # Silkscreen label.
        self.canvas.create_text(
            OUTER + BOARD_W / 2, OUTER + HEADER_H + GAP_TOP / 2,
            text='GFX HAT', anchor='center', fill=SILK,
            font=('TkDefaultFont', 22, 'bold'),
        )

        # RGB backlight glow strips above and below the LCD (6 zones).
        zone_w = LCD_W / NUM_ZONES
        for i in range(NUM_ZONES):
            zx0 = self._lcd_x + i * zone_w
            zx1 = self._lcd_x + (i + 1) * zone_w
            color = _hex(zones[i])
            self.canvas.create_rectangle(
                zx0, self._lcd_y - GLOW_H, zx1, self._lcd_y,
                fill=color, outline='')
            self.canvas.create_rectangle(
                zx0, self._lcd_y + LCD_H, zx1, self._lcd_y + LCD_H + GLOW_H,
                fill=color, outline='')

        # LCD bezel + image.
        self.canvas.create_rectangle(
            self._lcd_x - 5, self._lcd_y - 5,
            self._lcd_x + LCD_W + 5, self._lcd_y + LCD_H + 5,
            fill='#06070a', outline='#3a3d44', width=2,
        )
        image = self._render_lcd_image()
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(self._lcd_x, self._lcd_y, anchor='nw', image=self._photo)

        if self._show_grid:
            self._draw_grid()

        # Touch pads.
        for channel, x0, y0, x1, y1 in self._button_rects:
            pressed = device.is_held(channel)
            on = leds[channel]

            if pressed:
                fill = PAD_PRESSED
            else:
                fill = PAD_FILL
            self._round_rect(x0, y0, x1, y1, 14, fill=fill,
                             outline=PAD_EDGE, width=2)

            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2

            # White LED glow when lit (scaled by global brightness).
            if on:
                level = max(0.12, brightness)
                glow = _blend((22, 24, 28), LED_WHITE, level)
                inset = 9
                self._round_rect(x0 + inset, y0 + inset, x1 - inset, y1 - inset,
                                 9, fill=_hex(glow), outline='')
                icon_color = '#0b0c0f'
            else:
                icon_color = ICON_IDLE

            self._draw_icon(PAD_ICONS[channel], cx, cy, PAD * 0.42, icon_color)

            # Key hint below the pad.
            self.canvas.create_text(
                cx, y1 + 13, text=keyboard.KEY_HINTS[channel],
                fill=SILK, font=('TkDefaultFont', 8),
            )

        # Footer hint: grid toggle (with current state) and quit.
        grid_state = 'on' if self._show_grid else 'off'
        self.canvas.create_text(
            OUTER + BOARD_W / 2, OUTER + BOARD_H - 16,
            text='Grid (G): {}     ·     Quit (Q)'.format(grid_state),
            fill=SILK, font=('TkDefaultFont', 9),
        )

        self._schedule_redraw()

    def _schedule_redraw(self):
        self.root.after(33, self._redraw)

    def _window_alive(self):
        try:
            return bool(self.root.winfo_exists())
        except tk.TclError:
            return False

    def run(self):
        self.root.mainloop()
