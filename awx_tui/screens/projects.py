"""
AWX TUI - Projects Screen

Browse and manage AWX projects with sync capabilities.
"""

import re
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static


class TopPanel(Static):
    """Top panel with rotating title, instance health, running jobs, and last refresh time."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_refresh_time = None
        self.running_jobs_count = 0
        self.capacity_pct = 0
        self.instance_status = "unknown"
        self.instance_name = "No instance"
        self.response_time = "N/A"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="top-panel-layout"):
            # Column 1 (50%) - Rotating title @ instance + health + response time
            yield Static("Loading...", classes="top-title")

            # Column 2 (25%) - Running jobs + capacity
            yield Static("🚀 -- | Cap: --%", classes="top-jobs")

            # Column 3 (25%) - Last refresh timestamp
            yield Static("⏱ LOADING", classes="top-refresh")

    def on_mount(self) -> None:
        """Initial display update and start auto-refresh timer."""
        self.update_display()
        # Auto-update every second (for rotating title and timestamp)
        self.set_interval(1.0, self.update_display)

    def update_display(self):
        """Update top panel display with current data."""
        # Get current app name from rotating titles
        if hasattr(self.app, "current_app_name"):
            app_name = self.app.current_app_name
        else:
            app_name = "AWX TUI"

        # Get current instance info
        if hasattr(self.app, "instance_manager"):
            instance_manager = self.app.instance_manager
            current_instance = instance_manager.current_instance
            if current_instance:
                self.instance_name = current_instance

                # Get instance config for status and response time
                config = self.app.app_config.instances.get(current_instance)
                if config:
                    if hasattr(config, "last_status"):
                        self.instance_status = config.last_status or "unknown"
                    # Get response time from last ping check (stored during instance selection)
                    if hasattr(config, "last_response_time"):
                        self.response_time = config.last_response_time or "N/A"

        # Instance health with emoji
        status_emoji_map = {
            "online": "[green]✓[/green]",
            "slow": "⚠",
            "very_slow": "🐌",
            "offline": "✗",
            "error": "[red]✗[/red]",
            "unknown": "❓",
            "ready": "[green]✓[/green]",
        }
        status_emoji = status_emoji_map.get(self.instance_status, "❓")
        status_text = self.instance_status.replace("_", " ").title()

        # Column 1: Title - Screen @ Instance + Status (response time)
        title_text = f"{app_name} - Projects @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"

        # Column 2: Running jobs + capacity bar
        bar = self._build_capacity_bar(self.capacity_pct)
        jobs_text = f"🚀 {self.running_jobs_count} | {bar} {self.capacity_pct}%"

        # Column 3: Last refresh timestamp (24hr format)
        if self.last_refresh_time:
            refresh_text = f"⏱ {self.last_refresh_time.strftime('%H:%M:%S')}"
        else:
            refresh_text = "⏱ LOADING"

        # Update the three columns
        try:
            self.query_one(".top-title", Static).update(title_text)
            self.query_one(".top-jobs", Static).update(jobs_text)
            self.query_one(".top-refresh", Static).update(refresh_text)
        except:
            pass  # Ignore if widgets not found during startup

    def update_metrics(self, running_jobs: int = 0, capacity_pct: int = 0):
        """Update running jobs count and capacity percentage."""
        self.running_jobs_count = running_jobs
        self.capacity_pct = capacity_pct
        self.last_refresh_time = datetime.now()
        self.update_display()

    def _build_capacity_bar(self, capacity_pct: int) -> str:
        """Build colored capacity bar with 10 blocks and dithering"""
        full_blocks = capacity_pct // 10
        remainder = capacity_pct % 10

        # Determine color based on capacity level
        if capacity_pct >= 60:
            color = "green"
        elif capacity_pct > 30:
            color = "yellow"
        elif capacity_pct >= 10:
            color = "orange1"
        else:
            color = "red"

        # Build capacity bar with 10 blocks total
        bar = ""
        for i in range(10):
            if i < full_blocks:
                bar += "█"
            elif i == full_blocks and remainder > 0:
                if remainder >= 7:
                    bar += "▓"
                elif remainder >= 4:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"

        return f"[{color}]{bar}[/{color}]"


class ProjectsScreen(Screen):
    """
    Projects screen - browse and manage AWX projects

    Layout:
    - Header
    - TopPanel (rotating title, instance status, metrics, refresh time)
    - Full-width projects table
    - Footer
    """

    CSS_PATH = "projects.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_dashboard_esc", "Back"),
        ("1", "back_to_dashboard", "Dashboard"),
        ("2", "goto_historic_jobs", "Historic Jobs"),
        ("3", "goto_active_jobs", "Active Jobs"),
        ("4", "goto_projects", "Projects"),
        ("5", "goto_templates", "Templates"),
        ("6", "goto_inventories", "Inventories"),
        ("ctrl+s", "sync_project", "Sync"),
        ("ctrl+f", "focus_filter", "Filter"),
        ("ctrl+d", "debug_console", "Debug"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refreshing = False
        self._refresh_start_time = None
        self._refresh_timer = None  # TopPanel metrics refresh timer
        self._table_refresh_timer = None  # Table refresh timer
        self._projects_data = []  # Store all loaded projects
        self._filtered_projects_data = []  # Filtered projects for display
        self._current_refresh_interval = 10  # Track current refresh interval
        self._table_last_updated = None  # Track when projects table was last refreshed

    def compose(self) -> ComposeResult:
        """Create projects layout"""
        yield Header()
        yield TopPanel().add_class("top-panel")
        yield Input(
            placeholder="Filter: name:deploy status:successful scm_type:git org:myorg branch:main (Ctrl+F)",
            id="filter-input",
        )
        with Container(id="projects-container"):
            yield Static("PROJECTS (0)", id="projects-header", classes="table-header")
            yield DataTable(id="projects-table", cursor_type="row")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data"""
        # Update title to show screen context
        self.app._update_title()

        # Set up Projects table
        projects_table = self.query_one("#projects-table", DataTable)
        projects_table.add_columns(
            "ID", "", "", "", "Name", "Org", "SCM", "URL", "Branch", "Commit", "Default Env", "Last Sync"
        )

        # Focus the table by default (not the filter input)
        projects_table.focus()

        # Trigger initial data load
        self.set_timer(0.1, lambda: self.run_worker(self._load_data()))

        # Start TopPanel metrics auto-refresh (always enabled, default 5 seconds)
        top_panel_refresh = self.app.app_config.preferences.get("projects_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Projects table refresh (dynamic: 3s if syncing, 10s idle)
        # Start with 10 seconds - will adjust after first load
        self._table_refresh_timer = self.set_interval(10.0, self.auto_refresh_table)

    async def _load_data(self) -> None:
        """Load projects data"""
        # Skip if already refreshing (with timeout check)
        if self._refreshing:
            timeout = self.app.app_config.preferences.get("dashboard_refresh_timeout", 30)
            if self._refresh_start_time:
                elapsed = (datetime.now() - self._refresh_start_time).total_seconds()
                if elapsed > timeout:
                    self.app.log.warning(f"Refresh stuck for {elapsed}s (timeout: {timeout}s), resetting lock")
                    self._refreshing = False
                    self._refresh_start_time = None
                else:
                    return
            else:
                return

        self._refreshing = True
        self._refresh_start_time = datetime.now()
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    await self._fetch_and_display(client)
            else:
                await self._fetch_and_display(client)

        except Exception as e:
            import traceback

            self.app.log.error(f"Projects load error: {e}\n{traceback.format_exc()}")
            self.app.notify(f"Error loading projects: {e}", severity="error")
        finally:
            self._refreshing = False
            self._refresh_start_time = None

    async def _fetch_and_display(self, client) -> None:
        """Fetch and display all data"""
        # Get configured page size (default 200)
        page_size = self.app.app_config.preferences.get("projects_page_size", 200)

        try:
            # Fetch projects
            projects_resp = await client.get(
                "/api/v2/projects/", params={"page_size": page_size, "order_by": "organization__name,name"}
            )
        except Exception as e:
            raise Exception(f"Failed to fetch projects: {e}") from e

        # Calculate metrics for TopPanel
        try:
            running_resp = await client.get(
                "/api/v2/unified_jobs/", params={"status__in": "pending,waiting,running", "page_size": 200}
            )
            running_jobs_count = len(running_resp.get("results", []))
        except Exception as e:
            running_jobs_count = 0
            self.app.log.warning(f"Failed to fetch running jobs: {e}")

        # Try to fetch instances for capacity calculation (optional)
        capacity_pct = 0
        try:
            instances_resp = await client.get("/api/v2/instances/")
            instances = instances_resp.get("results", [])
            total_capacity = sum(inst.get("capacity", 0) for inst in instances)
            total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
            capacity_pct = int(((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0)
        except Exception as e:
            self.app.log.warning(f"Failed to fetch instances for capacity: {e}")

        # Update TopPanel with current metrics
        try:
            top_panel = self.query_one(TopPanel)
            top_panel.update_metrics(running_jobs=running_jobs_count, capacity_pct=capacity_pct)
        except:
            pass  # TopPanel not found or not ready

        # Store fetched projects
        self._projects_data = projects_resp.get("results", [])

        # Update table last refreshed timestamp
        self._table_last_updated = datetime.now()

        # Re-apply current filter if any
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value:
            self._filter_projects(filter_input.value)
        else:
            # No filter, show all projects
            self._filtered_projects_data = self._projects_data.copy()
            self._update_projects_table()

        # Adjust refresh interval based on sync status
        self._adjust_refresh_interval()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes"""
        if event.input.id == "filter-input":
            self._filter_projects(event.value)

    def _filter_projects(self, search_term: str) -> None:
        """Filter projects based on search term with advanced filtering"""
        if not search_term.strip():
            # No filter, show all projects
            self._filtered_projects_data = self._projects_data.copy()
            self._update_projects_table()
            return

        search_term = search_term.lower().strip()
        filtered = []

        # Parse filter terms
        filter_patterns = {
            "name": r"name:([^\s]+)",
            "status": r"status:([^\s]+)",
            "scm_type": r"scm_type:([^\s]+)",
            "org": r"org:([^\s]+)",
            "branch": r"branch:([^\s]+)",
        }

        # Parse all filters
        filters = {}

        for key, pattern in filter_patterns.items():
            match = re.search(pattern, search_term)
            if match:
                # Split by comma for OR logic
                filters[key] = [v.strip() for v in match.group(1).split(",")]

        # Remove filter keywords from search term to get plain text search
        plain_search = search_term
        for pattern in filter_patterns.values():
            plain_search = re.sub(pattern, "", plain_search)
        plain_search = plain_search.strip()

        # Filter projects
        for project in self._projects_data:
            # Get project fields for filtering
            name = project.get("name", "").lower()
            status = project.get("status", "").lower()
            scm_type = project.get("scm_type", "").lower()
            org = project.get("summary_fields", {}).get("organization", {}).get("name", "").lower()
            branch = project.get("scm_branch", "").lower()
            url = project.get("scm_url", "").lower()

            # Check inclusion filters (AND logic between different filter types)
            matches = True

            if "name" in filters:
                if not any(n in name for n in filters["name"]):
                    matches = False

            if "status" in filters:
                if not any(s in status for s in filters["status"]):
                    matches = False

            if "scm_type" in filters:
                if not any(t in scm_type for t in filters["scm_type"]):
                    matches = False

            if "org" in filters:
                if not any(o in org for o in filters["org"]):
                    matches = False

            if "branch" in filters:
                if not any(b in branch for b in filters["branch"]):
                    matches = False

            # Plain text search (searches across multiple fields)
            if plain_search and matches:
                text_match = (
                    plain_search in name
                    or plain_search in org
                    or plain_search in scm_type
                    or plain_search in branch
                    or plain_search in url
                )
                if not text_match:
                    matches = False

            if matches:
                filtered.append(project)

        self._filtered_projects_data = filtered
        self._update_projects_table()

    def _update_projects_table(self) -> None:
        """Update projects DataTable from self._filtered_projects_data"""
        # Use filtered projects data
        projects = self._filtered_projects_data if self._filtered_projects_data else self._projects_data

        # Build header with count (show X/Y when filtering)
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value and len(self._filtered_projects_data) != len(self._projects_data):
            # Filtering active - show filtered/total
            header_text = f"PROJECTS ({len(self._filtered_projects_data)}/{len(self._projects_data)})"
        else:
            # No filter or filter matches all - show just count
            header_text = f"PROJECTS ({len(projects)})"

        if self._table_last_updated:
            header_text += f" - Last Updated: {self._table_last_updated.strftime('%H:%M:%S')}"

        self.query_one("#projects-header").update(header_text)

        table = self.query_one("#projects-table", DataTable)

        # Save current project ID (from first column) to restore position
        selected_project_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_project_id = table.get_row_at(cursor_row)[0]  # First column is project ID
            except:
                pass

        table.clear()

        new_cursor_row = 0
        for idx, project in enumerate(projects):
            pid = str(project.get("id", 0))
            name = project.get("name", "Unknown")[:30]
            org = project.get("summary_fields", {}).get("organization", {}).get("name", "N/A")[:15]
            scm_type = project.get("scm_type", "N/A")[:10]
            scm_url = project.get("scm_url", "N/A")[:40]

            # Show last 8 characters of branch
            branch_full = project.get("scm_branch", "N/A")
            branch = branch_full[-8:] if branch_full != "N/A" and len(branch_full) > 0 else "N/A"

            # Show last 8 characters of commit hash
            commit_full = project.get("scm_revision", "N/A")
            commit = commit_full[-8:] if commit_full != "N/A" and len(commit_full) > 0 else "N/A"

            default_env = project.get("summary_fields", {}).get("default_environment", {}).get("name", "N/A")[:20]
            status = project.get("status", "unknown")

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

            # Icon flags (show emoji or blank)
            update_on_launch_icon = "🔄" if project.get("scm_update_on_launch") else ""
            allow_override_icon = "📝" if project.get("allow_override") else ""

            # Format last sync timestamp
            last_sync_str = "N/A"
            last_updated = project.get("last_updated")
            if last_updated:
                try:
                    sync_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    last_sync_str = sync_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    last_sync_str = "N/A"

            # Track if this is the previously selected project
            if selected_project_id and pid == selected_project_id:
                new_cursor_row = idx

            table.add_row(
                pid,
                status_emoji,
                update_on_launch_icon,
                allow_override_icon,
                name,
                org,
                scm_type,
                scm_url,
                branch,
                commit,
                default_env,
                last_sync_str,
            )

        # Restore cursor to same project ID if found, otherwise use same row number
        if table.row_count > 0:
            # Check if we found the same project in the new list
            found_same_project = False
            if selected_project_id:
                try:
                    if table.get_row_at(new_cursor_row)[0] == selected_project_id:
                        found_same_project = True
                except:
                    pass

            if found_same_project:
                table.cursor_coordinate = (new_cursor_row, 0)
            else:
                # Fall back to same row number (clamped to table size)
                table.cursor_coordinate = (min(cursor_row, table.row_count - 1), 0)

    def _adjust_refresh_interval(self) -> None:
        """Dynamically adjust table refresh interval based on project sync status"""
        # Get configured intervals (default: 3s with syncing, 10s idle)
        refresh_with_syncing = self.app.app_config.preferences.get("projects_refresh_with_syncing", 3)
        refresh_idle = self.app.app_config.preferences.get("projects_refresh_idle", 10)

        # Check if any projects are syncing
        any_syncing = any(p.get("status") in ("running", "pending", "waiting") for p in self._projects_data)

        # Determine appropriate interval
        if any_syncing:
            desired_interval = refresh_with_syncing
        else:
            desired_interval = refresh_idle

        # Only restart timer if interval changed
        if self._table_refresh_timer:
            if not hasattr(self, "_current_refresh_interval") or self._current_refresh_interval != desired_interval:
                self._table_refresh_timer.stop()
                self._table_refresh_timer = self.set_interval(desired_interval, self.auto_refresh_table)
                self._current_refresh_interval = desired_interval

    def auto_refresh_top_panel(self) -> None:
        """Auto-refresh TopPanel metrics only (silent, no table reload)"""
        # Only refresh if this screen is currently visible (on top of stack)
        if self.app.screen is self:
            self.run_worker(self._refresh_top_panel_metrics())

    def auto_refresh_table(self) -> None:
        """Auto-refresh table data (silent)"""
        # Only refresh if this screen is currently visible (on top of stack)
        if self.app.screen is self:
            self.run_worker(self._load_data())

    async def _refresh_top_panel_metrics(self) -> None:
        """Refresh only TopPanel metrics (running jobs, capacity)"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    # Fetch only running jobs and instances for metrics
                    running_resp = await client.get(
                        "/api/v2/unified_jobs/", params={"status__in": "pending,waiting,running", "page_size": 200}
                    )
                    instances_resp = await client.get("/api/v2/instances/")

                    # Calculate and update metrics
                    running_jobs_count = len(running_resp.get("results", []))
                    instances = instances_resp.get("results", [])
                    total_capacity = sum(inst.get("capacity", 0) for inst in instances)
                    total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
                    capacity_pct = int(
                        ((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0
                    )

                    top_panel = self.query_one(TopPanel)
                    top_panel.update_metrics(running_jobs=running_jobs_count, capacity_pct=capacity_pct)
        except Exception as e:
            self.app.log.error(f"Failed to refresh TopPanel metrics: {e}")

    def action_refresh(self) -> None:
        """Manual refresh"""
        self.app.notify("Refreshing projects...", timeout=1)
        self.run_worker(self._load_data())

    def action_sync_project(self) -> None:
        """Sync selected project (with confirmation)"""
        table = self.query_one("#projects-table", DataTable)

        # Get selected project
        if not table.cursor_coordinate or table.row_count == 0:
            self.notify("No project selected", severity="warning")
            return

        try:
            cursor_row = table.cursor_coordinate[0]
            project_id = int(table.get_row_at(cursor_row)[0])
            project_name = table.get_row_at(cursor_row)[2]  # Name is now column 2 (after ID and status emoji)

            # Find project data
            projects_data = self._filtered_projects_data if self._filtered_projects_data else self._projects_data
            project = None
            for p in projects_data:
                if p.get("id") == project_id:
                    project = p
                    break

            if not project:
                self.notify("Project not found", severity="error")
                return

            # Show confirmation modal
            from awx_tui.modals.confirm_sync import ConfirmSyncModal

            def handle_sync_confirmation(confirmed: bool) -> None:
                """Handle the confirmation result"""
                if confirmed:
                    self.run_worker(self._trigger_sync(project_id, project_name))

            self.app.push_screen(ConfirmSyncModal(project), handle_sync_confirmation)

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to sync project: {e}")
            self.notify("Error syncing project", severity="error")

    async def _trigger_sync(self, project_id: int, project_name: str) -> None:
        """Trigger project update (sync)"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.post(f"/api/v2/projects/{project_id}/update/", data={})
            else:
                response = await client.post(f"/api/v2/projects/{project_id}/update/", data={})

            # Get the job ID from the response
            job_id = response.get("id", "unknown")
            self.notify(f"Project sync started: {project_name} (Job #{job_id})", timeout=5)

            # Trigger a refresh to show the new status
            self.run_worker(self._load_data())

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to trigger project sync: {e}\n{traceback.format_exc()}")
            self.notify(f"Failed to sync project: {e}", severity="error")

    def action_back_to_dashboard_esc(self) -> None:
        """Return to dashboard screen (escape key)"""
        self.app.pop_screen()

    def action_back_to_dashboard(self) -> None:
        """Return to dashboard screen (1 key)"""
        self.app.pop_screen()

    def action_debug_console(self) -> None:
        """Open debug console"""
        self.app.action_toggle_debug()

    def action_focus_filter(self) -> None:
        """Focus the filter input"""
        self.query_one("#filter-input", Input).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - open update project screen"""
        table = self.query_one("#projects-table", DataTable)

        try:
            cursor_row = event.cursor_row
            project_id = int(table.get_row_at(cursor_row)[0])

            # Open update project screen
            from awx_tui.screens.update_project import UpdateProjectScreen

            self.app.push_screen(UpdateProjectScreen(project_id))

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to open project update: {e}")
            self.notify("Error opening project", severity="error")

    def action_goto_historic_jobs(self) -> None:
        """Navigate to Historic Jobs screen"""
        from awx_tui.screens.historic_jobs import HistoricJobsScreen

        # Pop current screen, then push new screen (replace, don't stack)
        self.app.pop_screen()
        self.app.push_screen(HistoricJobsScreen())

    def action_goto_active_jobs(self) -> None:
        """Navigate to Active Jobs screen"""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        # Pop current screen, then push new screen (replace, don't stack)
        self.app.pop_screen()
        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Go to projects (already here, do nothing)"""
        pass

    def action_goto_templates(self) -> None:
        """Navigate to templates (key: 5)"""
        from awx_tui.screens.templates import TemplatesScreen

        self.app.pop_screen()
        self.app.push_screen(TemplatesScreen())

    def action_goto_inventories(self) -> None:
        """Navigate to inventories (key: 6)"""
        from awx_tui.screens.inventories import InventoriesScreen

        self.app.pop_screen()
        self.app.push_screen(InventoriesScreen())

    def on_screen_suspend(self) -> None:
        """Stop auto-refresh timers when screen is hidden (navigated away)"""
        if self._refresh_timer:
            self._refresh_timer.stop()
        if self._table_refresh_timer:
            self._table_refresh_timer.stop()

    def on_screen_resume(self) -> None:
        """Resume auto-refresh timers when screen is shown again and trigger immediate refresh"""
        # Trigger immediate refresh to show any changes made in update screen
        self.run_worker(self._load_data())

        # Resume TopPanel metrics refresh (always enabled by default)
        top_panel_refresh = self.app.app_config.preferences.get("projects_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Resume table refresh with dynamic interval based on sync status
        refresh_with_syncing = self.app.app_config.preferences.get("projects_refresh_with_syncing", 3)
        refresh_idle = self.app.app_config.preferences.get("projects_refresh_idle", 10)

        # Check if any projects are syncing
        any_syncing = any(p.get("status") in ("running", "pending", "waiting") for p in self._projects_data)

        # Use appropriate interval based on current sync status
        if any_syncing:
            interval = refresh_with_syncing
        else:
            interval = refresh_idle

        self._table_refresh_timer = self.set_interval(interval, self.auto_refresh_table)
        self._current_refresh_interval = interval
