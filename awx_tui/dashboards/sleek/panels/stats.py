"""
AWX TUI - Sleek Dashboard Stats Panel

Displays resource counts (jobs, orgs, projects, etc.) in ASCII boxes.
Uses border_styles for consistent rounded corners.
"""

from typing import TYPE_CHECKING

from textual.widgets import Static

from awx_tui.dashboards.sleek.widgets import get_border_style

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class StatsPanel:
    """
    Manages the RESOURCES panel showing counts of AWX resources.

    Displays counts for:
    - Jobs (total, successful, failed)
    - Orgs, Hosts
    - Projects, Job Templates
    - Workflows, Inventories
    - Credentials, Execution Environments
    """

    # Total width available inside the RESOURCES BorderPanel
    # 28 chars wide (corners + 26 inner chars)
    PANEL_WIDTH = 28

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard
        self._chars = get_border_style("rounded")

    def _build_jobs_box(self, total: int, successful: int, failed: int) -> list[str]:
        """Build the Jobs summary box with dynamic alignment."""
        c = self._chars
        width = self.PANEL_WIDTH

        # Top line: ╭ Jobs ────────────────────╮
        title = "Jobs"
        title_part = f" {title} "
        remaining = width - len(title_part) - 2
        top = f"{c.top_left}{title_part}{c.horizontal * remaining}{c.top_right}"

        # Middle line: │ total           ✓ success  ✗ fail │
        # Justified: total left-aligned, success/failed right-aligned

        # Content width inside borders: width - 4 (│ + space on each side)
        content_width = width - 4

        # Left part: total count (left-aligned)
        total_str = f"{total:,}"

        # Right part: success and failed counts
        success_str = f"[green]✓[/green] {successful}"
        failed_str = f"[red]✗[/red] {failed}"
        right_part = f"{success_str}  {failed_str}"

        # Calculate display lengths (Rich markup doesn't count)
        total_display_len = len(total_str)
        success_display_len = 2 + len(str(successful))  # "✓ N"
        failed_display_len = 2 + len(str(failed))  # "✗ N"
        right_display_len = success_display_len + 2 + failed_display_len  # includes "  " between

        # Calculate middle spacing for justified alignment
        middle_space = max(1, content_width - total_display_len - right_display_len)

        content = f"{total_str}{' ' * middle_space}{right_part}"
        mid = f"{c.vertical} {content} {c.vertical}"

        # Bottom line: ╰──────────────────────────╯
        bot = f"{c.bottom_left}{c.horizontal * (width - 2)}{c.bottom_right}"

        return [top, mid, bot]

    def _build_resource_row(self, left_title: str, left_val: int, right_title: str, right_val: int) -> list[str]:
        """Build a row of two resource boxes with + buttons.

        Each box is 14 chars wide: ╭─ Title ─┬───╮
        Two boxes = 14 + 14 = 28 chars total (no space between).
        """
        c = self._chars
        val_width = 6  # Width for the value display

        def build_single_box(title: str, value: int) -> tuple[str, str, str]:
            # Truncate title to 5 chars max
            title_str = title[:5]

            # Top: ╭ Title ──┬───╮ (14 chars total)
            # Layout: ╭(1) + space(1) + title(N) + space(1) + ─(fill+1) + ┬(1) + ───(3) + ╮(1)
            # fill+1 = 6 - len(title) to maintain 14 char width
            fill_dashes = 6 - len(title_str)
            top = f"{c.top_left} {title_str} {c.horizontal * fill_dashes}{c.t_down}{c.horizontal * 3}{c.top_right}"

            # Mid: │ value  │ + │ (14 chars)
            # │(1) + space(1) + value(6) + space(1) + │(1) + space(1) + +(1) + space(1) + │(1) = 14
            val_str = f"{value:,}"[:val_width].ljust(val_width)
            mid = f"{c.vertical} {val_str} {c.vertical} + {c.vertical}"

            # Bot: ╰────────┴───╯ (14 chars)
            # ╰(1) + ────────(8) + ┴(1) + ───(3) + ╯(1) = 14
            bot = f"{c.bottom_left}{c.horizontal * 8}{c.t_up}{c.horizontal * 3}{c.bottom_right}"

            return top, mid, bot

        left_box = build_single_box(left_title, left_val)
        right_box = build_single_box(right_title, right_val)

        return [
            f"{left_box[0]}{right_box[0]}",
            f"{left_box[1]}{right_box[1]}",
            f"{left_box[2]}{right_box[2]}",
        ]

    def update(
        self,
        unified_jobs_resp: dict,
        _ping_resp: dict,
        graph_jobs: list,
        orgs_resp: dict,
        projects_resp: dict,
        templates_resp: dict,
        workflows_resp: dict,
        inventories_resp: dict,
        hosts_resp: dict,
        exec_envs_resp: dict,
        credentials_resp: dict,
    ) -> None:
        """Update RESOURCES section with real counts."""
        total_jobs = unified_jobs_resp.get("count", 0)

        # Count successful and failed jobs from graph_jobs
        successful_jobs = sum(1 for job in graph_jobs if job.get("status") == "successful")
        failed_jobs = sum(1 for job in graph_jobs if job.get("status") == "failed")

        # Get counts from responses
        orgs_count = orgs_resp.get("count", 0)
        projects_count = projects_resp.get("count", 0)
        templates_count = templates_resp.get("count", 0)
        workflows_count = workflows_resp.get("count", 0)
        inventories_count = inventories_resp.get("count", 0)
        hosts_count = hosts_resp.get("count", 0)
        exec_envs_count = exec_envs_resp.get("count", 0)
        credentials_count = credentials_resp.get("count", 0)

        # Build all boxes
        lines = []
        lines.extend(self._build_jobs_box(total_jobs, successful_jobs, failed_jobs))
        lines.extend(self._build_resource_row("Orgs", orgs_count, "Hosts", hosts_count))
        lines.extend(self._build_resource_row("Projs", projects_count, "JTs", templates_count))
        lines.extend(self._build_resource_row("WFs", workflows_count, "Invs", inventories_count))
        lines.extend(self._build_resource_row("Creds", credentials_count, "EEs", exec_envs_count))

        self.dashboard.query_one("#stats-content", Static).update("\n".join(lines))
