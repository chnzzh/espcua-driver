"""ESPCUA: Host-side adapter for ESP32-P4 IP-KVM and CUA-Driver."""

from espcua.keymap import (
    KEYBOARD_MOD_LCTRL,
    KEYBOARD_MOD_LSHIFT,
    KEYBOARD_MOD_LALT,
    KEYBOARD_MOD_LGUI,
    char_to_hid,
    name_to_hid,
    parse_hotkey,
)
from espcua.client import ESPCUAClient
from espcua.adapter import ESPCUADriver

__all__ = [
    "ESPCUAClient",
    "ESPCUADriver",
    "KEYBOARD_MOD_LCTRL",
    "KEYBOARD_MOD_LSHIFT",
    "KEYBOARD_MOD_LALT",
    "KEYBOARD_MOD_LGUI",
    "char_to_hid",
    "name_to_hid",
    "parse_hotkey",
]

__version__ = "1.0.0"
