"""
AWX TUI - Sleek Dashboard Instance Groups Panel

Displays AWX instance groups in a DataTable with capacity bars.
"""

from typing import TYPE_CHECKING

from textual.widgets import DataTable

from awx_tui.dashboards.sleek.widgets import BorderPanel

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class GroupsPanel:
    """
    Manages the INSTANCE GROUPS panel showing AWX instance groups.

    Displays each group with:
    - Name (truncated)
    - Capacity bar (visual percentage)
    - Running forks
    - Running jobs
    - Total jobs run
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard

    def setup_table(self) -> None:
        """Configure DataTable columns for instance groups."""
        try:
            table = self.dashboard.query_one("#groups-table", DataTable)
            table.add_column("Name", width=13)
            table.add_columns("Capacity", "Forks", "Jobs", "Total")
        except Exception:
            pass

    def update(self, groups: list) -> None:
        """Update INSTANCE GROUPS DataTable with current data."""
        # Update BorderPanel title with count
        groups_panel = self.dashboard.query_one("#groups-panel", BorderPanel)
        groups_panel.update_title(f"INSTANCE GROUPS ({len(groups)})")

        table = self.dashboard.query_one("#groups-table", DataTable)
        table.clear()

        for group in groups:
            name = group.get("name", "Unknown")
            capacity = group.get("capacity", 0)
            consumed = group.get("consumed_capacity", 0)
            forks = group.get("running_forks", 0)
            jobs = group.get("jobs_running", 0)
            total = group.get("jobs_total", 0)

            # Calculate capacity percentage (remaining)
            capacity_pct = int(((capacity - consumed) / capacity * 100) if capacity > 0 else 0)
            capacity_bar = self.dashboard._build_capacity_bar(capacity_pct, num_blocks=5)
            capacity_display = f"{capacity_bar} {capacity_pct}%"

            table.add_row(name, capacity_display, str(forks), str(jobs), str(total))
