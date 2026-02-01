"""
AWX TUI - BorderPanel Widget

A custom Textual widget that renders its own borders with support for:
- Shared borders with adjacent panels (via attach_* parameters)
- Titled headers with automatic dash calculation
- Sizing controlled via CSS (not widget parameters)
"""

from __future__ import annotations

from typing import Literal, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from .border_styles import BorderCharSet, get_border_style

# Type aliases
Side = Literal["top", "right", "bottom", "left"]


class BorderStatic(Static):
    """A static widget for rendering border lines."""

    DEFAULT_CSS = """
    BorderStatic {
        width: 100%;
        height: 1;
        color: $primary;
    }
    """


class VerticalBorderStatic(Static):
    """A static widget for rendering vertical border characters.

    Supports junction characters at specific rows where horizontal
    borders from adjacent panels connect.
    """

    DEFAULT_CSS = """
    VerticalBorderStatic {
        width: 1;
        height: 100%;
        color: $primary;
    }
    """

    def __init__(self, char: str = "│", junction_char: str = "├", junction_rows: Optional[set] = None, **kwargs):
        """Initialize vertical border.

        Args:
            char: Default character for the vertical line (│)
            junction_char: Character to use at junction rows (├)
            junction_rows: Set of row indices where junctions occur
        """
        super().__init__("", **kwargs)
        self._char = char
        self._junction_char = junction_char
        self._junction_rows: set = junction_rows or set()

    def add_junction(self, row: int) -> None:
        """Add a junction at the specified row."""
        self._junction_rows.add(row)
        self._update_content()

    def set_junctions(self, rows: set) -> None:
        """Set all junction rows."""
        self._junction_rows = rows
        self._update_content()

    def on_mount(self) -> None:
        """Update content after mount."""
        self._update_content()

    def on_resize(self, event) -> None:
        """Update content when resized."""
        self._update_content()

    def _update_content(self) -> None:
        """Fill with vertical bar characters, using junction chars at specified rows."""
        height = self.size.height
        if height > 0:
            chars = []
            for row in range(height):
                if row in self._junction_rows:
                    chars.append(self._junction_char)
                else:
                    chars.append(self._char)
            content = "\n".join(chars)
            self.update(content)


class BorderPanel(Container):
    """
    A panel widget that renders its own borders with support for:
    - Shared borders with adjacent panels
    - Titled headers with automatic dash calculation
    - Sizing controlled via CSS

    Attach Points:
        When a side is "attached", the border on that side is omitted,
        allowing seamless visual connection with a neighboring panel.
        The neighbor panel's border becomes the shared border.

    Example:
        # Panel with title, bottom attached (shares border with panel below)
        BorderPanel(
            DataTable(id="my-table"),
            title="MY PANEL",
            attach_bottom=True,
        )
    """

    DEFAULT_CSS = """
    BorderPanel {
        width: auto;
        height: auto;
        overflow: hidden;
    }

    BorderPanel > .border-layout {
        width: 100%;
        height: 100%;
    }

    BorderPanel > .border-layout > .border-middle {
        width: 100%;
        height: 1fr;
    }

    BorderPanel > .border-layout > .border-middle > .border-content {
        width: 1fr;
        height: 100%;
    }

    BorderPanel > .border-layout > .border-middle > .border-content > * {
        width: 100%;
        height: auto;
    }
    """

    # Reactive properties for dynamic updates
    title: reactive[str] = reactive("", layout=True)
    subtitle: reactive[str] = reactive("", layout=True)

    def __init__(
        self,
        *children: Widget,
        title: str = "",
        subtitle: str = "",
        # Attachment configuration
        attach_top: bool = False,
        attach_right: bool = False,
        attach_bottom: bool = False,
        attach_left: bool = False,
        # Connection configuration (panels connecting from sides, affects corner chars)
        connect_right: bool = False,
        # Styling
        border_style: str = "solid",
        border_color: str = "$primary",
        # Standard widget args
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """Initialize BorderPanel.

        Args:
            *children: Child widgets to compose inside the panel
            title: Title text for the top border (e.g., "INSTANCES (5)")
            subtitle: Subtitle text for the bottom border
            attach_top: If True, omit top border (shares with panel above)
            attach_right: If True, omit right border (shares with panel to right)
            attach_bottom: If True, omit bottom border (shares with panel below)
            attach_left: If True, omit left border (shares with panel to left)
            connect_right: If True, a panel connects from the right (use ┬ corners instead of ┐)
            border_style: Border character style ('solid', 'double', 'heavy', 'rounded')
            border_color: Color for border (Textual CSS color)
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self._children = list(children)
        self.title = title
        self.subtitle = subtitle

        # Attachment state
        self._attach_top = attach_top
        self._attach_right = attach_right
        self._attach_bottom = attach_bottom
        self._attach_left = attach_left

        # Connection state (panels connecting from sides)
        self._connect_right = connect_right

        # Border style
        self._char_set = get_border_style(border_style)
        self._border_color = border_color

        # Store border widgets for updates
        self._top_border: Optional[BorderStatic] = None
        self._bottom_border: Optional[BorderStatic] = None
        self._left_border: Optional[VerticalBorderStatic] = None
        self._right_border: Optional[VerticalBorderStatic] = None

    def compose(self) -> ComposeResult:
        """Compose the border structure with children inside."""
        cs = self._char_set

        with Vertical(classes="border-layout"):
            # Top border
            if self._has_top_border:
                self._top_border = BorderStatic("", classes="border-top")
                yield self._top_border

            # Middle section: left border | content | right border
            with Horizontal(classes="border-middle"):
                # Left border
                if self._has_left_border:
                    self._left_border = VerticalBorderStatic(char=cs.vertical, classes="border-left")
                    yield self._left_border

                # Content container
                with Container(classes="border-content"):
                    yield from self._children

                # Right border
                if self._has_right_border:
                    self._right_border = VerticalBorderStatic(char=cs.vertical, classes="border-right")
                    yield self._right_border

            # Bottom border
            if self._has_bottom_border:
                self._bottom_border = BorderStatic("", classes="border-bottom")
                yield self._bottom_border

    def on_mount(self) -> None:
        """Update border text after mounting."""
        self._update_borders()

    def on_resize(self, event) -> None:
        """Handle resize events to recalculate borders."""
        self._update_borders()

    def _update_borders(self) -> None:
        """Update border content based on current size."""
        width = self.size.width
        if width < 2:
            return

        cs = self._char_set

        # Update top border
        if self._top_border is not None:
            top_line = self._build_horizontal_border(width, cs, is_top=True, title=self.title)
            self._top_border.update(top_line)

        # Update bottom border
        if self._bottom_border is not None:
            bottom_line = self._build_horizontal_border(width, cs, is_top=False, title=self.subtitle)
            self._bottom_border.update(bottom_line)

    def _build_horizontal_border(self, width: int, cs: BorderCharSet, is_top: bool, title: str = "") -> str:
        """Build a horizontal border line with optional title.

        When attach_left is True, we don't render a left corner - the adjacent
        panel's vertical border provides the visual continuity.
        When attach_right is True, we still render a right corner with appropriate junction.
        """
        # Determine left corner (or None if attached)
        left_corner = None
        if not self._attach_left:
            if is_top:
                if self._attach_top:
                    left_corner = cs.t_right  # ├ (panel above connects)
                else:
                    left_corner = cs.top_left  # ┌
            else:
                left_corner = cs.bottom_left  # └

        # Determine right corner
        # connect_right means a panel connects from the right (use junction chars)
        # attach_right means we don't render our right border (panel to right provides it)
        has_right_connection = self._attach_right or self._connect_right

        if is_top:
            if self._attach_top:
                if has_right_connection:
                    right_corner = cs.cross  # ┼ (connects all 4 directions)
                else:
                    right_corner = cs.t_left  # ┤
            else:
                if has_right_connection:
                    right_corner = cs.t_down  # ┬ (connects left, right, down)
                else:
                    right_corner = cs.top_right  # ┐
        else:
            if has_right_connection:
                right_corner = cs.t_up  # ┴ (connects left, right, up)
            else:
                right_corner = cs.bottom_right  # ┘

        # Calculate inner width (between corners)
        corners_count = (0 if left_corner is None else 1) + 1  # Always have right corner
        inner_width = width - corners_count

        if inner_width < 1:
            if left_corner:
                return f"{left_corner}{right_corner}"
            else:
                return right_corner

        if title:
            return self._build_titled_border(left_corner, right_corner, inner_width, cs, title)
        else:
            left_part = left_corner if left_corner else ""
            return f"{left_part}{cs.horizontal * inner_width}{right_corner}"

    def _build_titled_border(
        self, left_corner: Optional[str], right_corner: str, inner_width: int, cs: BorderCharSet, title: str
    ) -> str:
        """Build a border line with a title.

        Format: ┌─ TITLE ────────────────────┐ (with left corner)
        Format: ─ TITLE ─────────────────────┐ (without left corner when attach_left)
        """
        left_part = left_corner if left_corner else ""

        # Format title with spaces and italic styling
        title_text = f" [italic]{title}[/italic] "
        title_len = len(title) + 2  # Only count visible chars (title + 2 spaces)

        if title_len >= inner_width - 2:
            # Title too long, truncate
            # Need room for: left dash (1) + space (1) + title + "..." (3) + space (1) + right dash (1)
            max_title_len = inner_width - 8
            if max_title_len > 0:
                truncated = title[:max_title_len]
                title_text = f" [italic]{truncated}...[/italic] "
                title_len = len(truncated) + 5  # truncated + "..." + 2 spaces
            else:
                # No room for title at all
                return f"{left_part}{cs.horizontal * inner_width}{right_corner}"

        # Calculate dashes
        remaining = inner_width - title_len
        left_dashes = 1  # One dash before title
        right_dashes = remaining - left_dashes

        border_content = cs.horizontal * left_dashes + title_text + cs.horizontal * max(0, right_dashes)

        return f"{left_part}{border_content}{right_corner}"

    def watch_title(self, new_title: str) -> None:
        """Update border when title changes."""
        self._update_borders()

    def watch_subtitle(self, new_subtitle: str) -> None:
        """Update border when subtitle changes."""
        self._update_borders()

    @property
    def _has_top_border(self) -> bool:
        """Whether this panel has a top border.

        Note: attach_top only affects corner characters, not border existence.
        We always render top borders to show titles.
        """
        return True  # Always render top border for titles

    @property
    def _has_bottom_border(self) -> bool:
        """Whether this panel has a bottom border.

        Note: attach_bottom means the panel below will render the shared line,
        so we don't render our bottom border.
        """
        return not self._attach_bottom

    @property
    def _has_left_border(self) -> bool:
        """Whether this panel has a left border."""
        return not self._attach_left

    @property
    def _has_right_border(self) -> bool:
        """Whether this panel has a right border."""
        return not self._attach_right

    def attach(self, side: Side) -> None:
        """Mark a side as attached (shared border with neighbor).

        Note: This only works before compose() is called.
        For dynamic changes, the widget would need to be remounted.

        Args:
            side: Which side to attach ("top", "right", "bottom", "left")
        """
        if side == "top":
            self._attach_top = True
        elif side == "right":
            self._attach_right = True
        elif side == "bottom":
            self._attach_bottom = True
        elif side == "left":
            self._attach_left = True
        self.refresh()

    def detach(self, side: Side) -> None:
        """Remove attachment from a side.

        Note: This only works before compose() is called.
        For dynamic changes, the widget would need to be remounted.

        Args:
            side: Which side to detach ("top", "right", "bottom", "left")
        """
        if side == "top":
            self._attach_top = False
        elif side == "right":
            self._attach_right = False
        elif side == "bottom":
            self._attach_bottom = False
        elif side == "left":
            self._attach_left = False
        self.refresh()

    def update_title(self, title: str) -> None:
        """Update the panel title (triggers re-render with auto-calculated dashes).

        Args:
            title: New title text (e.g., "INSTANCES (5)")
        """
        self.title = title

    def update_subtitle(self, subtitle: str) -> None:
        """Update the panel subtitle (triggers re-render).

        Args:
            subtitle: New subtitle text
        """
        self.subtitle = subtitle

    def add_right_junction(self, row: int) -> None:
        """Add a junction point to the right border at the specified row.

        This renders ├ instead of │ at that row, allowing horizontal
        borders from adjacent panels to visually connect.

        Args:
            row: Row index (0-based, relative to the right border widget)
        """
        if self._right_border is not None:
            self._right_border.add_junction(row)

    def set_right_junctions(self, rows: set) -> None:
        """Set all junction points on the right border.

        Args:
            rows: Set of row indices where junctions should appear
        """
        if self._right_border is not None:
            self._right_border.set_junctions(rows)
