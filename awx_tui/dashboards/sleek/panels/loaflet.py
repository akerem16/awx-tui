"""
AWX TUI - Sleek Dashboard Loaflet Panel

Displays recent notifications in a mini "loaf" format.
Each notification is displayed in a rounded box with timestamp in the border.
"""

import re
from typing import TYPE_CHECKING

from rich.cells import cell_len
from rich.markup import escape as rich_escape
from textual.widgets import Static

from awx_tui.dashboards.sleek.widgets import BorderPanel, get_border_style

# Regex to strip Rich markup tags (handles Textual CSS vars like [$text-success])
_MARKUP_RE = re.compile(r"\[[^\]]*\]")

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class LoafletPanel:
    """
    Manages the LOAFLET panel showing recent notifications.

    Displays all toast notifications with timestamps in a scrollable panel.
    Each notification is rendered as a rounded box with time in the title.
    Shows a fun ASCII cow when no notifications exist.
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard
        self._chars = get_border_style("rounded")

    def _get_box_width(self) -> int:
        """Get the width for notification boxes based on panel size."""
        try:
            loaf_panel = self.dashboard.query_one("#mini-loaf-panel", BorderPanel)
            # Panel width minus:
            # - 2 for the BorderPanel's own borders
            # - 2 for the scrollbar (always reserve space to avoid wrap when scrollbar appears)
            return max(20, loaf_panel.size.width - 4)
        except Exception:
            return 27  # Fallback

    def _get_display_width(self, text: str) -> int:
        """Get the display width of text, accounting for Rich markup and wide chars."""
        # Strip Rich markup and calculate cell width (handles double-width Unicode)
        plain_text = _MARKUP_RE.sub("", text)
        return cell_len(plain_text)

    def _wrap_text(self, message: str, max_width: int) -> list[str]:
        """Wrap text to fit within max_width, returning as many lines as needed.

        Strips all Rich markup tags (including Textual CSS vars like [$text-success])
        before wrapping for accurate width calculation.
        """
        # Strip Rich markup tags using regex (handles Textual CSS vars that
        # Text.from_markup() doesn't recognize as valid Rich styles)
        plain_msg = _MARKUP_RE.sub("", message)

        # Simple word wrap on plain text
        words = plain_msg.split()
        lines = []
        current_line = ""

        for word in words:
            if not current_line:
                test_line = word
            else:
                test_line = current_line + " " + word

            if cell_len(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                # Break long words across lines if needed
                while cell_len(current_line) > max_width:
                    # Try to break at path separators for nicer wrapping
                    break_point = self._find_break_point(current_line, max_width)
                    lines.append(current_line[:break_point])
                    current_line = current_line[break_point:]

        # Add final line
        if current_line:
            lines.append(current_line)

        return lines if lines else [""]

    def _find_break_point(self, text: str, max_width: int) -> int:
        """Find optimal break point for long text, preferring path separators."""
        # Find the furthest position that fits within max_width
        break_at = 0
        for i in range(len(text)):
            if cell_len(text[: i + 1]) <= max_width:
                break_at = i + 1
            else:
                break

        if break_at == 0:
            break_at = 1  # At minimum, take one character

        # Look for path separator within the valid range to break there
        last_slash = text.rfind("/", 0, break_at)
        if last_slash > 0:  # Found a slash (not at position 0)
            return last_slash + 1  # Break after the slash

        return break_at

    def _build_notification_box(self, time_str: str, message: str, width: int) -> list[str]:
        """Build a notification box with time in the border.

        Format:
        ╭ HH:MM:SS ────────────────╮
        │ Message text here...    │
        ╰─────────────────────────╯
        """
        c = self._chars

        # Top line: ╭ HH:MM:SS ─────────────────╮
        # Layout: ╭(1) + space(1) + time(8) + space(1) + dashes(fill) + ╮(1) = width
        # fill = width - 12
        fill_dashes = max(1, width - 12)
        top = f"{c.top_left} {time_str} {c.horizontal * fill_dashes}{c.top_right}"

        # Content width for message: width - 4 (│ + space + space + │)
        content_width = width - 4
        lines = [top]

        # Wrap message to fit (as many lines as needed)
        wrapped = self._wrap_text(message, content_width)

        for line in wrapped:
            # Pad to proper width (calculate before escaping for accurate width)
            padding = content_width - cell_len(line)
            padded = line + " " * max(0, padding)
            # Escape any Rich markup characters to prevent display issues
            # (e.g., [$text-success] would otherwise be interpreted as markup)
            # Must happen AFTER padding calculation but BEFORE adding our own markup
            padded = rich_escape(padded)
            # Colorize checkmarks and X's (Unicode chars, not affected by escaping)
            padded = padded.replace("✓", "[green]✓[/green]")
            padded = padded.replace("✗", "[red]✗[/red]")
            padded = padded.replace("✔", "[green]✔[/green]")
            padded = padded.replace("✖", "[red]✖[/red]")
            lines.append(f"{c.vertical} {padded} {c.vertical}")

        # Bottom line: ╰─────────────────────────╯
        bot = f"{c.bottom_left}{c.horizontal * (width - 2)}{c.bottom_right}"
        lines.append(bot)

        return lines

    def update(self) -> None:
        """Update mini loaf with recent notifications."""
        # Get all notifications from app (panel scrolls if needed)
        notifications = self.dashboard.app.notification_log if self.dashboard.app.notification_log else []

        # Update BorderPanel title with count (dashes auto-calculated)
        total_count = len(self.dashboard.app.notification_log)
        loaf_panel = self.dashboard.query_one("#mini-loaf-panel", BorderPanel)
        loaf_panel.update_title(f"LOAFLET ({total_count})")

        # Get dynamic width
        width = self._get_box_width()

        if not notifications:
            # Build empty state with rounded border box
            c = self._chars
            content_width = width - 4  # Account for │ + space on each side

            # Center the text
            line1 = "No toasts"
            line2 = "yet!"
            line1_padded = line1.center(content_width)
            line2_padded = line2.center(content_width)

            # Build box with rounded corners
            top = f"{c.top_left}{c.horizontal * (width - 2)}{c.top_right}"
            mid1 = f"{c.vertical} {line1_padded} {c.vertical}"
            mid2 = f"{c.vertical} {line2_padded} {c.vertical}"
            bot = f"{c.bottom_left}{c.horizontal * (width - 2)}{c.bottom_right}"

            # Cow says moo
            cow = """        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
               ||----w |
               ||     ||"""

            # Content is 9 lines: 4 for box + 5 for cow
            content_lines = 9

            # Get available height from the BorderPanel (subtract 4 for borders + footer)
            try:
                panel_height = loaf_panel.size.height
                # BorderPanel has 1 line for top border, 1 for bottom, and 2 for footer
                available_height = panel_height - 4
            except Exception:
                available_height = 0

            # Calculate padding to center vertically (need reasonable height)
            if available_height > content_lines + 2:
                padding = (available_height - content_lines) // 2
                top_padding = "\n" * padding
                bottom_padding = "\n" * padding
            else:
                top_padding = ""
                bottom_padding = ""

            ascii_bread = f"{top_padding}{top}\n{mid1}\n{mid2}\n{bot}\n{cow}{bottom_padding}"
            self.dashboard.query_one("#mini-loaf-content", Static).update(ascii_bread)
            return

        # Build mini loaf display (most recent first, reversed)
        # Each notification is a rounded box with time in the border
        lines = []
        for notif in reversed(notifications):
            timestamp = notif["timestamp"]
            message = notif["message"]

            # Format time (HH:MM:SS)
            time_str = timestamp.strftime("%H:%M:%S")

            # Build notification box and add to lines
            box_lines = self._build_notification_box(time_str, message, width)
            lines.extend(box_lines)

        self.dashboard.query_one("#mini-loaf-content", Static).update("\n".join(lines))
