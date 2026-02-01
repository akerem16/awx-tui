"""
AWX TUI - Sleek Dashboard Instances Panel

Displays AWX controller instances in a DataTable with capacity bars.
"""

from typing import TYPE_CHECKING

from textual.widgets import DataTable

from awx_tui.dashboards.sleek.widgets import BorderPanel

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class InstancesPanel:
    """
    Manages the INSTANCES panel showing AWX controller instances.

    Displays each instance with:
    - Hostname (truncated)
    - Capacity bar (visual percentage)
    - Running forks
    - Running jobs
    - Total jobs run
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard

    def setup_table(self) -> None:
        """Configure DataTable columns for instances."""
        try:
            table = self.dashboard.query_one("#instances-table", DataTable)
            table.add_column("Hostname", width=13)
            table.add_columns("Capacity", "Forks", "Jobs", "Total")
        except Exception:
            pass

    def update(self, instances: list) -> None:
        """Update INSTANCES DataTable with current data."""
        # Update BorderPanel title with count
        instances_panel = self.dashboard.query_one("#instances-panel", BorderPanel)
        instances_panel.update_title(f"INSTANCES ({len(instances)})")

        table = self.dashboard.query_one("#instances-table", DataTable)
        table.clear()

        for inst in instances:
            hostname = inst.get("hostname", "Unknown")
            capacity = inst.get("capacity", 0)
            consumed = inst.get("consumed_capacity", 0)
            forks = inst.get("running_forks", 0)
            jobs = inst.get("jobs_running", 0)
            total = inst.get("jobs_total", 0)

            # Calculate capacity percentage (remaining)
            capacity_pct = int(((capacity - consumed) / capacity * 100) if capacity > 0 else 0)
            capacity_bar = self.dashboard._build_capacity_bar(capacity_pct, num_blocks=5)
            capacity_display = f"{capacity_bar} {capacity_pct}%"

            table.add_row(hostname, capacity_display, str(forks), str(jobs), str(total))
