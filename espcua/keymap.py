"""USB HID Keycode and Modifier Mappings for Keyboard Emulation."""

# Modifier Bitmasks
KEYBOARD_MOD_NONE   = 0x00
KEYBOARD_MOD_LCTRL  = 0x01
KEYBOARD_MOD_LSHIFT = 0x02
KEYBOARD_MOD_LALT   = 0x04
KEYBOARD_MOD_LGUI   = 0x08
KEYBOARD_MOD_RCTRL  = 0x10
KEYBOARD_MOD_RSHIFT = 0x20
KEYBOARD_MOD_RALT   = 0x40
KEYBOARD_MOD_RGUI   = 0x80

# Special Key Names to USB HID Keycodes
SPECIAL_KEY_MAP = {
    # Control & Navigation
    "enter": 0x28,
    "return": 0x28,
    "escape": 0x29,
    "esc": 0x29,
    "backspace": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "printscreen": 0x46,
    "scrolllock": 0x47,
    "pause": 0x48,
    "insert": 0x49,
    "home": 0x4A,
    "pageup": 0x4B,
    "delete": 0x4C,
    "del": 0x4C,
    "end": 0x4D,
    "pagedown": 0x4E,
    "right": 0x4F,
    "left": 0x50,
    "down": 0x51,
    "up": 0x52,
    "capslock": 0x39,
    "numlock": 0x53,

    # Function Keys F1 - F24
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D,
    "f5": 0x3E, "f6": 0x3F, "f7": 0x40, "f8": 0x41,
    "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "f13": 0x68, "f14": 0x69, "f15": 0x6A, "f16": 0x6B,
    "f17": 0x6C, "f18": 0x6D, "f19": 0x6E, "f20": 0x6F,
    "f21": 0x70, "f22": 0x71, "f23": 0x72, "f24": 0x73,

    # Keypad
    "kp_slash": 0x54,
    "kp_asterisk": 0x55,
    "kp_minus": 0x56,
    "kp_plus": 0x57,
    "kp_enter": 0x58,
    "kp_1": 0x59, "kp_2": 0x5A, "kp_3": 0x5B,
    "kp_4": 0x5C, "kp_5": 0x5D, "kp_6": 0x5E,
    "kp_7": 0x5F, "kp_8": 0x60, "kp_9": 0x61,
    "kp_0": 0x62, "kp_dot": 0x63,
}

# ASCII characters to (keycode, modifier)
ASCII_TO_HID = {
    '\n': (0x28, KEYBOARD_MOD_NONE),
    '\r': (0x28, KEYBOARD_MOD_NONE),
    '\t': (0x2B, KEYBOARD_MOD_NONE),
    '\b': (0x2A, KEYBOARD_MOD_NONE),
    ' ':  (0x2C, KEYBOARD_MOD_NONE),
    '!':  (0x1E, KEYBOARD_MOD_LSHIFT),
    '"':  (0x34, KEYBOARD_MOD_LSHIFT),
    '#':  (0x20, KEYBOARD_MOD_LSHIFT),
    '$':  (0x21, KEYBOARD_MOD_LSHIFT),
    '%':  (0x22, KEYBOARD_MOD_LSHIFT),
    '&':  (0x24, KEYBOARD_MOD_LSHIFT),
    '\'': (0x34, KEYBOARD_MOD_NONE),
    '(':  (0x26, KEYBOARD_MOD_LSHIFT),
    ')':  (0x27, KEYBOARD_MOD_LSHIFT),
    '*':  (0x25, KEYBOARD_MOD_LSHIFT),
    '+':  (0x2E, KEYBOARD_MOD_LSHIFT),
    ',':  (0x36, KEYBOARD_MOD_NONE),
    '-':  (0x2D, KEYBOARD_MOD_NONE),
    '.':  (0x37, KEYBOARD_MOD_NONE),
    '/':  (0x38, KEYBOARD_MOD_NONE),
    '0':  (0x27, KEYBOARD_MOD_NONE),
    '1':  (0x1E, KEYBOARD_MOD_NONE),
    '2':  (0x1F, KEYBOARD_MOD_NONE),
    '3':  (0x20, KEYBOARD_MOD_NONE),
    '4':  (0x21, KEYBOARD_MOD_NONE),
    '5':  (0x22, KEYBOARD_MOD_NONE),
    '6':  (0x23, KEYBOARD_MOD_NONE),
    '7':  (0x24, KEYBOARD_MOD_NONE),
    '8':  (0x25, KEYBOARD_MOD_NONE),
    '9':  (0x26, KEYBOARD_MOD_NONE),
    ':':  (0x33, KEYBOARD_MOD_LSHIFT),
    ';':  (0x33, KEYBOARD_MOD_NONE),
    '<':  (0x36, KEYBOARD_MOD_LSHIFT),
    '=':  (0x2E, KEYBOARD_MOD_NONE),
    '>':  (0x37, KEYBOARD_MOD_LSHIFT),
    '?':  (0x38, KEYBOARD_MOD_LSHIFT),
    '@':  (0x1F, KEYBOARD_MOD_LSHIFT),
    '[':  (0x2F, KEYBOARD_MOD_NONE),
    '\\': (0x31, KEYBOARD_MOD_NONE),
    ']':  (0x30, KEYBOARD_MOD_NONE),
    '^':  (0x23, KEYBOARD_MOD_LSHIFT),
    '_':  (0x2D, KEYBOARD_MOD_LSHIFT),
    '`':  (0x35, KEYBOARD_MOD_NONE),
    '{':  (0x2F, KEYBOARD_MOD_LSHIFT),
    '|':  (0x31, KEYBOARD_MOD_LSHIFT),
    '}':  (0x30, KEYBOARD_MOD_LSHIFT),
    '~':  (0x35, KEYBOARD_MOD_LSHIFT),
}

# Populate lowercase letters a-z (0x04 - 0x1D)
for _i, _ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    ASCII_TO_HID[_ch] = (0x04 + _i, KEYBOARD_MOD_NONE)
    ASCII_TO_HID[_ch.upper()] = (0x04 + _i, KEYBOARD_MOD_LSHIFT)


def char_to_hid(char: str) -> tuple[int, int]:
    """Maps a single character to (keycode, modifier_bitmask).

    Returns (0, 0) if character is unknown.
    """
    if len(char) != 1:
        return 0, 0
    return ASCII_TO_HID.get(char, (0, 0))


def name_to_hid(key_name: str) -> tuple[int, int]:
    """Maps a key name or single character to (keycode, modifier_bitmask)."""
    norm = key_name.strip().lower()

    # Modifiers alone
    if norm in ("ctrl", "control", "lctrl", "left_ctrl"):
        return 0, KEYBOARD_MOD_LCTRL
    if norm in ("rctrl", "right_ctrl"):
        return 0, KEYBOARD_MOD_RCTRL
    if norm in ("shift", "lshift", "left_shift"):
        return 0, KEYBOARD_MOD_LSHIFT
    if norm in ("rshift", "right_shift"):
        return 0, KEYBOARD_MOD_RSHIFT
    if norm in ("alt", "lalt", "left_alt", "option"):
        return 0, KEYBOARD_MOD_LALT
    if norm in ("ralt", "right_alt", "altgr"):
        return 0, KEYBOARD_MOD_RALT
    if norm in ("gui", "win", "cmd", "command", "super", "windows"):
        return 0, KEYBOARD_MOD_LGUI

    if norm in SPECIAL_KEY_MAP:
        return SPECIAL_KEY_MAP[norm], KEYBOARD_MOD_NONE

    if len(key_name) == 1:
        return char_to_hid(key_name)

    return 0, 0


def parse_hotkey(keys: list[str]) -> tuple[list[int], int]:
    """Parses a list of key names into keycodes and combined modifier bitmask."""
    keycodes = []
    combined_mod = KEYBOARD_MOD_NONE

    for k in keys:
        kc, mod = name_to_hid(k)
        if mod != KEYBOARD_MOD_NONE:
            combined_mod |= mod
        if kc > 0 and kc not in keycodes:
            keycodes.append(kc)

    return keycodes[:6], combined_mod
