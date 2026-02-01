"""
AWX TUI - Confirm Sync Modal

Simple confirmation dialog for project sync operations.
"""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmSyncModal(ModalScreen[bool]):
    """
    Confirmation modal for project sync

    Returns True if user confirms, False if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmSyncModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #confirm-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #project-info {
        width: 100%;
        color: $text;
        margin: 1 0;
        padding: 1;
        background: $boost;
        border: solid $accent;
    }

    #confirm-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, project_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.project_data = project_data

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static("Sync Project", id="confirm-title")
            yield Static(self._format_project_info(), id="project-info")
            with Horizontal(id="confirm-buttons"):
                yield Button("Sync", variant="primary", id="sync-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _format_project_info(self) -> str:
        """Format project information for display"""
        name = self.project_data.get("name", "Unknown")
        org = self.project_data.get("summary_fields", {}).get("organization", {}).get("name", "N/A")
        scm_url = self.project_data.get("scm_url", "N/A")
        scm_branch = self.project_data.get("scm_branch", "")
        scm_revision = self.project_data.get("scm_revision", "N/A")
        status = self.project_data.get("status", "unknown")
        last_updated = self.project_data.get("last_updated")

        # Status emoji
        status_emoji = {
            "successful": "[green]✓[/green]",
            "ok": "[green]✓[/green]",
            "failed": "[red]✗[/red]",
            "error": "[red]✗[/red]",
            "running": "🏃",
            "pending": "⏳",
            "waiting": "⏳",
            "canceled": "⚠",
            "never updated": "⏳",
            "new": "⏳",
            "missing": "❓",
        }.get(status, "❓")

        # Format last sync time
        last_sync_str = "Never"
        if last_updated:
            try:
                sync_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                last_sync_str = sync_time.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                last_sync_str = "N/A"

        # Build commit/branch display
        # Show branch only if different from revision
        if scm_branch and scm_branch != scm_revision and scm_branch != "N/A":
            commit_display = f"Commit: {scm_revision} (branch: {scm_branch})"
        else:
            commit_display = f"Commit: {scm_revision}"

        # Build info display
        info_lines = [
            f"Project: {name}",
            f"Organization: {org}",
            f"SCM URL: {scm_url}",
            commit_display,
            "",
            f"Last Sync: {last_sync_str}",
            f"Last Status: {status_emoji} {status.title()}",
        ]

        return "\n".join(info_lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sync-button":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the sync (ESC key)"""
        self.dismiss(False)

    def on_mount(self) -> None:
        """Focus the Sync button by default"""
        self.query_one("#sync-button", Button).focus()
