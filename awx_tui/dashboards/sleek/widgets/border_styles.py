"""
AWX TUI - Border Styles

Defines character sets for drawing box borders in the terminal.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class BorderCharSet:
    """Character set for drawing borders.

    Attributes:
        top_left: Top-left corner (e.g., '┌')
        top_right: Top-right corner (e.g., '┐')
        bottom_left: Bottom-left corner (e.g., '└')
        bottom_right: Bottom-right corner (e.g., '┘')
        horizontal: Horizontal line (e.g., '─')
        vertical: Vertical line (e.g., '│')
        t_down: T-junction pointing down (e.g., '┬')
        t_up: T-junction pointing up (e.g., '┴')
        t_right: T-junction pointing right (e.g., '├')
        t_left: T-junction pointing left (e.g., '┤')
        cross: 4-way cross junction (e.g., '┼')
    """

    # Corners
    top_left: str = "┌"
    top_right: str = "┐"
    bottom_left: str = "└"
    bottom_right: str = "┘"

    # Edges
    horizontal: str = "─"
    vertical: str = "│"

    # T-junctions (for shared borders)
    t_down: str = "┬"  # ─┬─ (top edge, attaches below)
    t_up: str = "┴"  # ─┴─ (bottom edge, attaches above)
    t_right: str = "├"  # │├─ (left edge, attaches right)
    t_left: str = "┤"  # ─┤│ (right edge, attaches left)

    # Cross (4-way junction)
    cross: str = "┼"


# Predefined character sets
BORDER_STYLES: Dict[str, BorderCharSet] = {
    "solid": BorderCharSet(),
    "double": BorderCharSet(
        top_left="╔",
        top_right="╗",
        bottom_left="╚",
        bottom_right="╝",
        horizontal="═",
        vertical="║",
        t_down="╦",
        t_up="╩",
        t_right="╠",
        t_left="╣",
        cross="╬",
    ),
    "heavy": BorderCharSet(
        top_left="┏",
        top_right="┓",
        bottom_left="┗",
        bottom_right="┛",
        horizontal="━",
        vertical="┃",
        t_down="┳",
        t_up="┻",
        t_right="┣",
        t_left="┫",
        cross="╋",
    ),
    "rounded": BorderCharSet(
        top_left="╭",
        top_right="╮",
        bottom_left="╰",
        bottom_right="╯",
        horizontal="─",
        vertical="│",
        t_down="┬",
        t_up="┴",
        t_right="├",
        t_left="┤",
        cross="┼",
    ),
}


def get_border_style(name: str) -> BorderCharSet:
    """Get a border character set by name.

    Args:
        name: Style name ('solid', 'double', 'heavy', 'rounded')

    Returns:
        BorderCharSet for the requested style, defaults to 'solid' if not found
    """
    return BORDER_STYLES.get(name, BORDER_STYLES["solid"])
