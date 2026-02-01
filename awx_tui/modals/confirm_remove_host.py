"""
AWX TUI - Confirm Remove Host Modal

Confirmation dialog for removing a host from an inventory.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmRemoveHostModal(ModalScreen[bool]):
    """
    Confirmation modal for removing a host from an inventory

    Args:
        message: Main confirmation message (host removal question)
        details: Optional additional details (disassociation info)

    Returns True if user confirms, False if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmRemoveHostModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 80;
        height: auto;
        border: thick $error 80%;
        background: $surface;
        padding: 1;
    }

    #confirm-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
        background: $boost;
        padding: 1;
        margin-bottom: 1;
    }

    #confirm-message {
        width: 100%;
        content-align: center middle;
        color: $text;
        padding: 1;
        margin-bottom: 0;
    }

    #confirm-details {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        padding: 1;
        margin-bottom: 1;
    }

    #confirm-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 1;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str, details: str = None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.details = details

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static("🛑  Remove Host?  🛑", id="confirm-title")
            yield Static(self.message, id="confirm-message")
            if self.details:
                yield Static(self.details, id="confirm-details")
            with Horizontal(id="confirm-buttons"):
                yield Button("Confirm", variant="error", id="confirm-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-button":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the action (ESC key)"""
        self.dismiss(False)

    def on_mount(self) -> None:
        """Focus the Confirm button by default"""
        self.query_one("#confirm-button", Button).focus()
