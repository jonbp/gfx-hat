"""Keyboard bindings for the simulator's touch buttons.

Maps each GFX HAT button (by ``gfxhat.touch`` channel index) to the
Tk key symbols that trigger it, and provides a human-readable hint shown
in the GUI.
"""

# channel index -> list of Tk keysyms (lower-cased)
KEY_BINDINGS = {
    0: ['up', 'w'],            # UP
    1: ['down', 's'],          # DOWN
    2: ['escape', 'b'],        # BACK
    3: ['left', 'a', 'minus'],  # MINUS / LEFT
    4: ['return', 'space', 'e'],  # SELECT / ENTER
    5: ['right', 'd', 'plus', 'equal'],  # PLUS / RIGHT
}

# Short hint strings shown beneath each button.
KEY_HINTS = {
    0: '↑ / W',
    1: '↓ / S',
    2: 'Esc / B',
    3: '← / A',
    4: 'Enter / Space',
    5: '→ / D',
}


def channel_for_keysym(keysym):
    """Return the button channel bound to a Tk keysym, or None."""
    keysym = keysym.lower()
    for channel, keys in KEY_BINDINGS.items():
        if keysym in keys:
            return channel
    return None
