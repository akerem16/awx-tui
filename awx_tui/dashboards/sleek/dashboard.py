"""
AWX TUI - Sleek Dashboard

Compact dashboard with sidebar stats and mini loaf.
Features combined tables and streamlined layout.

Layout managed here, panel update logic in panels/ modules.
"""

import re
from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static

from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard
from awx_tui.dashboards.sleek.panels import (
    GroupsPanel,
    HealthPanel,
    InstancesPanel,
    JobsPanel,
    JobStatusPanel,
    LoafletPanel,
    StatsPanel,
)
from awx_tui.dashboards.sleek.widgets import BorderPanel, get_border_style


class TopPanel(Static):
    """Top panel with rotating title, instance health, running jobs, and last refresh time.

    Renders its own rounded borders using border_styles for consistency.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chars = get_border_style("rounded")
        self.last_refresh_time = None
        self.mount_time = None
        self.running_jobs_count = 0
        self.capacity_pct = 0
        self.instance_status = "unknown"
        self.instance_name = "No instance"
        self.response_time = "N/A"

    def on_mount(self) -> None:
        """Initial display update and start auto-refresh timer."""
        # Defer initial render to ensure layout is settled
        self.call_later(self.update_display)
        self.set_interval(1.0, self.update_display)

    def on_show(self) -> None:
        """Redraw when widget becomes visible (e.g., returning to screen)."""
        # Force clear and full redraw to remove any stale content from other screens
        self.update("")
        self.refresh()
        self.call_later(self.update_display)

    def on_resize(self) -> None:
        """Redraw borders when widget size changes."""
        self.update_display()

    def update_display(self):
        """Update top panel display with current data."""
        # Skip if width not yet available (will be called again on resize)
        if self.size.width < 10:
            self.update("")  # Clear stale content
            return

        if hasattr(self.app, "current_app_name"):
            app_name = self.app.current_app_name
        else:
            app_name = "AWX TUI"

        if hasattr(self.app, "instance_manager"):
            instance_manager = self.app.instance_manager
            current_instance = instance_manager.current_instance
            if current_instance:
                self.instance_name = current_instance

                config = self.app.app_config.instances.get(current_instance)
                if config:
                    if hasattr(config, "last_status"):
                        self.instance_status = config.last_status or "unknown"
                    if hasattr(config, "last_response_time"):
                        self.response_time = config.last_response_time or "N/A"

        status_emoji_map = {
            "online": "[green]✓[/green]",
            "slow": "[yellow]![/yellow]",
            "very_slow": "[red]!![/red]",
            "offline": "[red]✗[/red]",
            "error": "[red]✗[/red]",
            "unknown": "?",
            "ready": "[green]✓[/green]",
        }
        status_emoji = status_emoji_map.get(self.instance_status, "?")
        status_text = self.instance_status.replace("_", " ").title()

        title_text = (
            f"{app_name} - Dashboard @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"
        )

        # Build bordered content using border_styles
        c = self._chars
        width = self.size.width if self.size.width > 0 else 80
        inner_width = width - 2  # Account for left/right borders

        # Calculate display length (Rich markup doesn't count toward display width)
        # Format: "{app_name} - Dashboard @ {instance_name} {indicator} {status_text} ({response_time})"
        # Fixed parts: " - Dashboard @ " (15) + spaces around indicator (2) + " (" (2) + ")" (1) = 20 chars
        # Status indicator length: 1 char for most, 2 for "!!" (very_slow)
        indicator_display_len = len(re.sub(r"\[.*?\]", "", status_emoji))  # Strip Rich markup
        text_display_len = (
            len(app_name)
            + len(self.instance_name)
            + indicator_display_len
            + len(status_text)
            + len(self.response_time)
            + 20
        )

        # Center the title text
        padding_total = inner_width - text_display_len
        pad_left = max(0, padding_total // 2)
        pad_right = max(0, padding_total - pad_left)

        top = f"[bold $primary]{c.top_left}{c.horizontal * inner_width}{c.top_right}[/]"
        mid = (
            f"[bold $primary]{c.vertical}[/]{' ' * pad_left}{title_text}{' ' * pad_right}[bold $primary]{c.vertical}[/]"
        )
        bot = f"[bold $primary]{c.bottom_left}{c.horizontal * inner_width}{c.bottom_right}[/]"

        self.update(f"{top}\n{mid}\n{bot}")

    def update_metrics(self, running_jobs: int = 0, capacity_pct: int = 0):
        """Update running jobs count and capacity percentage."""
        self.running_jobs_count = running_jobs
        self.capacity_pct = capacity_pct
        self.last_refresh_time = datetime.now()
        self.update_display()


@register_dashboard("sleek")
class SleekDashboard(BaseDashboard):
    """
    Sleek compact dashboard with sidebar layout:

    Main area (82%): Instances/Groups + Jobs Graph (top) | Combined Jobs table (bottom)
    Sidebar (18%): Stats + Mini Loaf (last 5 notifications)
    """

    CSS_PATH = "sleek.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_instances", "Back"),
        ("1", "goto_dashboard", "Dashboard"),
        ("2", "goto_historic_jobs", "Historic Jobs"),
        ("3", "goto_active_jobs", "Active Jobs"),
        ("4", "goto_projects", "Projects"),
        ("5", "goto_templates", "Templates"),
        ("6", "goto_inventories", "Inventories"),
        ("ctrl+d", "debug_console", "Debug"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._running_jobs_data = []
        self._recent_jobs_data = []

        # Initialize panel managers
        self._health_panel = HealthPanel(self)
        self._job_status_panel = JobStatusPanel(self)
        self._instances_panel = InstancesPanel(self)
        self._groups_panel = GroupsPanel(self)
        self._jobs_panel = JobsPanel(self)
        self._stats_panel = StatsPanel(self)
        self._loaflet_panel = LoafletPanel(self)

    def compose(self) -> ComposeResult:
        """Create dashboard layout with stats on right side using BorderPanel widgets."""
        yield Header()
        yield TopPanel(id="sleek-top-panel")
        with Container(id="dashboard-container", classes="sleek-dashboard"):
            with Horizontal(id="main-layout"):
                # Left column: Main content
                with Vertical(id="content-column"):
                    # Top row: HEALTH/JOB STATUS (left) | INSTANCES/GROUPS (right)
                    with Horizontal(id="top-row"):
                        # Left: HEALTH (top) and JOB STATUS (bottom) stacked
                        with Vertical(id="health-graphs-column"):
                            yield BorderPanel(
                                Horizontal(
                                    Static("", id="health-system-status"),
                                    Static("", id="health-capacity"),
                                    Static("", id="health-failures"),
                                    id="health-content",
                                ),
                                title="HEALTH",
                                attach_bottom=True,
                                connect_right=True,
                                border_style="rounded",
                                id="health-panel",
                            )

                            yield BorderPanel(
                                Horizontal(
                                    DataTable(id="jobs-graph-table", show_cursor=False),
                                    Static("", id="jobs-graph-visual"),
                                    id="graphs-content",
                                ),
                                title="JOB STATUS (last 7 days)",
                                attach_top=True,
                                attach_bottom=True,
                                connect_right=True,
                                border_style="rounded",
                                id="graphs-panel",
                            )

                        # Right: Instances and Instance Groups stacked
                        with Vertical(id="instances-column"):
                            yield BorderPanel(
                                DataTable(id="instances-table", show_cursor=False),
                                title="INSTANCES (0)",
                                attach_bottom=True,
                                attach_left=True,
                                connect_right=True,
                                border_style="rounded",
                                id="instances-panel",
                            )

                            yield BorderPanel(
                                DataTable(id="groups-table", show_cursor=False),
                                title="INSTANCE GROUPS (0)",
                                attach_top=True,
                                attach_bottom=True,
                                attach_left=True,
                                connect_right=True,
                                border_style="rounded",
                                id="groups-panel",
                            )

                    # JOBS panel - responsive height
                    yield BorderPanel(
                        DataTable(id="jobs-table", cursor_type="row", zebra_stripes=True),
                        title="JOBS (0)",
                        attach_top=True,
                        connect_right=True,
                        border_style="rounded",
                        id="jobs-panel",
                    )

                # Right column: RESOURCES + MINI LOAF
                with Vertical(id="stats-column"):
                    yield BorderPanel(
                        Static("", id="stats-content"),
                        title="RESOURCES",
                        attach_bottom=True,
                        attach_left=True,
                        border_style="rounded",
                        id="stats-panel",
                    )

                    yield BorderPanel(
                        Vertical(
                            VerticalScroll(Static("", id="mini-loaf-content"), id="mini-loaf-scroll"),
                            Static("ctrl+o for the full loaf", id="mini-loaf-footer"),
                            id="loaf-content",
                        ),
                        title="LOAFLET (0)",
                        attach_top=True,
                        attach_left=True,
                        border_style="rounded",
                        id="mini-loaf-panel",
                    )

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data."""
        # Set up tables via panel managers
        self._instances_panel.setup_table()
        self._groups_panel.setup_table()
        self._job_status_panel.setup_table()
        self._jobs_panel.setup_table()

        # Call parent on_mount to trigger initial data load and start auto-refresh timer
        await super().on_mount()

    def on_resize(self) -> None:
        """Handle terminal resize - update size-dependent components."""
        # Re-render loaflet panel (cow centering depends on panel height)
        self._loaflet_panel.update()

    async def fetch_data(self, client):
        """
        Fetch all data for sleek dashboard.

        Returns:
            dict: Dashboard data with keys for all panels
        """
        import asyncio

        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        async def safe_get(endpoint, params=None, description=""):
            """Wrapper to catch exceptions per-endpoint."""
            try:
                return await client.get(endpoint, params=params)
            except Exception as e:
                self.app.log.error(f"Failed to fetch {description}: {e}")
                return {}

        results = await asyncio.gather(
            safe_get(
                "/api/v2/unified_jobs/", {"status__in": "pending,waiting,running", "page_size": 200}, "running jobs"
            ),
            safe_get(
                "/api/v2/unified_jobs/",
                {"status__in": "successful,failed,error,canceled", "page_size": 25, "order_by": "-finished"},
                "recent jobs",
            ),
            safe_get(
                "/api/v2/unified_jobs/",
                {"finished__gte": seven_days_ago, "page_size": 500, "order_by": "-finished"},
                "graph data",
            ),
            safe_get("/api/v2/instances/", None, "instances"),
            safe_get("/api/v2/instance_groups/", None, "instance groups"),
            safe_get("/api/v2/ping/", None, "ping"),
            safe_get("/api/v2/unified_jobs/", {"page_size": 1}, "unified jobs count"),
            safe_get("/api/v2/organizations/", {"page_size": 1}, "organizations count"),
            safe_get("/api/v2/projects/", {"page_size": 1}, "projects count"),
            safe_get("/api/v2/job_templates/", {"page_size": 1}, "job templates count"),
            safe_get("/api/v2/workflow_job_templates/", {"page_size": 1}, "workflow templates count"),
            safe_get("/api/v2/inventories/", {"page_size": 1}, "inventories count"),
            safe_get("/api/v2/hosts/", {"page_size": 1}, "hosts count"),
            safe_get("/api/v2/execution_environments/", {"page_size": 1}, "execution environments count"),
            safe_get("/api/v2/credentials/", {"page_size": 1}, "credentials count"),
            safe_get("/api/v2/job_events/", {"page_size": 1}, "job events count"),
            # Task events in last 24h (runner_on_ok, runner_on_failed, runner_on_skipped, runner_on_unreachable)
            safe_get(
                "/api/v2/job_events/",
                {
                    "created__gte": twenty_four_hours_ago,
                    "event__in": "runner_on_ok,runner_on_failed,runner_on_skipped,runner_on_unreachable",
                    "page_size": 1,
                },
                "task events 24h",
            ),
        )

        (
            running_resp,
            recent_resp,
            graph_resp,
            instances_resp,
            groups_resp,
            ping_resp,
            unified_jobs_resp,
            orgs_resp,
            projects_resp,
            templates_resp,
            workflows_resp,
            inventories_resp,
            hosts_resp,
            exec_envs_resp,
            credentials_resp,
            job_events_resp,
            task_events_24h_resp,
        ) = results

        running_jobs = running_resp.get("results", [])
        running_jobs_count = len(running_jobs)

        instances = instances_resp.get("results", [])
        total_capacity = sum(inst.get("capacity", 0) for inst in instances)
        total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
        capacity_pct = int(((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0)

        # Get task events count from 24h response
        task_events_24h_count = task_events_24h_resp.get("count", 0)

        return {
            "running_jobs": running_resp.get("results", []),
            "recent_jobs": recent_resp.get("results", []),
            "graph_jobs": graph_resp.get("results", []),
            "instances": instances_resp.get("results", []),
            "groups": groups_resp.get("results", []),
            "ping": ping_resp,
            "counts": {
                "unified_jobs": unified_jobs_resp,
                "orgs": orgs_resp,
                "projects": projects_resp,
                "templates": templates_resp,
                "workflows": workflows_resp,
                "inventories": inventories_resp,
                "hosts": hosts_resp,
                "exec_envs": exec_envs_resp,
                "credentials": credentials_resp,
                "job_events": job_events_resp,
            },
            "metrics": {
                "running_jobs_count": running_jobs_count,
                "capacity_pct": capacity_pct,
                "task_events_24h": task_events_24h_count,
            },
        }

    def update_display(self, data):
        """Update dashboard UI with fetched data via panel managers."""
        # Update TopPanel with current metrics
        try:
            top_panel = self.query_one(TopPanel)
            metrics = data["metrics"]
            top_panel.update_metrics(running_jobs=metrics["running_jobs_count"], capacity_pct=metrics["capacity_pct"])
        except Exception:
            pass

        # Delegate to panel managers
        self._instances_panel.update(data["instances"])
        self._groups_panel.update(data["groups"])
        self._job_status_panel.update(data["graph_jobs"])
        self._health_panel.update(
            data["ping"],
            data["running_jobs"],
            data["graph_jobs"],
            data["instances"],
            data["metrics"]["task_events_24h"],
        )

        counts = data["counts"]
        self._stats_panel.update(
            counts["unified_jobs"],
            data["ping"],
            data["graph_jobs"],
            counts["orgs"],
            counts["projects"],
            counts["templates"],
            counts["workflows"],
            counts["inventories"],
            counts["hosts"],
            counts["exec_envs"],
            counts["credentials"],
        )

        self._loaflet_panel.update()
        self._jobs_panel.update(data["running_jobs"], data["recent_jobs"])

    def _build_capacity_bar(self, capacity_pct: int, num_blocks: int = 10) -> str:
        """Build colored capacity bar with configurable block count and dithering."""
        block_size = 100 // num_blocks
        full_blocks = capacity_pct // block_size
        remainder = capacity_pct % block_size

        if capacity_pct >= 60:
            color = "#008000"  # Green
        elif capacity_pct > 30:
            color = "#CCCC00"  # Yellow (hex for consistent DataTable rendering)
        elif capacity_pct >= 10:
            color = "#FF8C00"  # Orange (hex for consistent DataTable rendering)
        else:
            color = "#CC0000"  # Red (hex for consistent DataTable rendering)

        bar = ""
        for i in range(num_blocks):
            if i < full_blocks:
                bar += "█"
            elif i == full_blocks and remainder > 0:
                if remainder >= block_size * 0.7:
                    bar += "▓"
                elif remainder >= block_size * 0.4:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"

        return f"[{color}]{bar}[/{color}]"

    def action_refresh(self) -> None:
        """Manual refresh dashboard data."""
        self.app.notify("Refreshing dashboard...", timeout=1)
        super().action_refresh()

    def action_debug_console(self) -> None:
        """Open debug console."""
        self.app.action_toggle_debug()

    def action_goto_dashboard(self) -> None:
        """Go to dashboard (already here)."""
        pass

    def action_goto_historic_jobs(self) -> None:
        """Navigate to Historic Jobs screen."""
        from awx_tui.screens.historic_jobs import HistoricJobsScreen

        self.app.push_screen(HistoricJobsScreen())

    def action_goto_active_jobs(self) -> None:
        """Navigate to Active Jobs screen."""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Navigate to Projects screen."""
        from awx_tui.screens.projects import ProjectsScreen

        self.app.push_screen(ProjectsScreen())

    def action_goto_templates(self) -> None:
        """Navigate to templates."""
        from awx_tui.screens.templates import TemplatesScreen

        self.app.pop_screen()
        self.app.push_screen(TemplatesScreen())

    def action_goto_inventories(self) -> None:
        """Navigate to inventories."""
        from awx_tui.screens.inventories import InventoriesScreen

        self.app.pop_screen()
        self.app.push_screen(InventoriesScreen())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on job table row - open job detail."""
        if event.data_table.id != "jobs-table":
            return

        try:
            job_id = int(event.data_table.get_row_at(event.cursor_row)[0])

            job_type = "job"
            all_jobs = self._running_jobs_data + self._recent_jobs_data

            for job in all_jobs:
                if job.get("id") == job_id:
                    job_type = job.get("type", "job")
                    break

            from awx_tui.modals.job_detail import JobDetailModal

            self.app.push_screen(JobDetailModal(job_id, job_type))
        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to open job detail: {e}")
            self.notify("Error opening job detail", severity="error")
