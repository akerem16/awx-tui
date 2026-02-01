"""Sleek dashboard custom widgets - BorderPanel for styled borders."""

from .border_panel import BorderPanel
from .border_styles import BORDER_STYLES, BorderCharSet, get_border_style

__all__ = [
    "BorderCharSet",
    "BORDER_STYLES",
    "get_border_style",
    "BorderPanel",
]
