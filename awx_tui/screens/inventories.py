"""
AWX TUI - Inventories Screen

Browse and manage AWX inventories.
"""

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
        title_text = (
            f"{app_name} - Inventories @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"
        )

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


class InventoriesScreen(Screen):
    """
    Inventories screen - browse and manage inventories

    Layout:
    - Header
    - TopPanel (rotating title, instance status, metrics, refresh time)
    - Filter input
    - Full-width inventories table
    - Footer
    """

    CSS_PATH = "inventories.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_dashboard", "Back"),
        ("1", "goto_dashboard", "Dashboard"),
        ("2", "goto_historic_jobs", "Historic Jobs"),
        ("3", "goto_active_jobs", "Active Jobs"),
        ("4", "goto_projects", "Projects"),
        ("5", "goto_templates", "Templates"),
        ("6", "goto_inventories", "Inventories"),
        ("ctrl+f", "focus_filter", "Filter"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refreshing = False
        self._refresh_start_time = None
        self._refresh_timer = None  # TopPanel metrics refresh timer
        self._table_refresh_timer = None  # Table refresh timer (optional)
        self._inventories_data = []  # Store all loaded inventories
        self._filtered_inventories_data = []  # Filtered inventories for display
        self._table_last_updated = None  # Track when inventories table was last refreshed

    def compose(self) -> ComposeResult:
        """Create inventories layout"""
        yield Header()
        yield TopPanel().add_class("top-panel")
        yield Input(placeholder="Filter: name:prod org:myorg (Ctrl+F)", id="filter-input")
        with Container(id="inventories-container"):
            yield Static("INVENTORIES (0)", id="inventories-header", classes="table-header")
            yield DataTable(id="inventories-table", cursor_type="row")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data"""
        # Update title to show screen context
        self.app._update_title()

        # Set up Inventories table
        inventories_table = self.query_one("#inventories-table", DataTable)
        inventories_table.add_columns("ID", "Name", "Organization", "Description", "Hosts")

        # Focus the table by default (not the filter input)
        inventories_table.focus()

        # Trigger initial data load
        self.set_timer(0.1, lambda: self.run_worker(self._load_data()))

        # Start TopPanel metrics auto-refresh (always enabled, default 5 seconds)
        top_panel_refresh = self.app.app_config.preferences.get("inventories_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Inventories table refresh (disabled by default - manual refresh only)
        # Press 'r' to manually refresh, or configure inventories_table_refresh_interval > 0
        table_refresh = self.app.app_config.preferences.get("inventories_table_refresh_interval", 0)
        if table_refresh > 0:
            self._table_refresh_timer = self.set_interval(table_refresh, self.auto_refresh_table)

    async def _load_data(self) -> None:
        """Load inventories data"""
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

            self.app.log.error(f"Inventories load error: {e}\n{traceback.format_exc()}")
            self.notify(f"Error loading inventories: {e}", severity="error")
        finally:
            self._refreshing = False
            self._refresh_start_time = None

    async def _fetch_and_display(self, client) -> None:
        """Fetch inventories data and display"""
        # Get configured page size (default 200)
        page_size = self.app.app_config.preferences.get("inventories_page_size", 200)

        # Fetch regular inventories only (kind="" means normal inventory, not smart)
        inventories_resp = await client.get("/api/v2/inventories/", params={"page_size": page_size, "kind": ""})
        self._inventories_data = inventories_resp.get("results", [])
        self._filtered_inventories_data = self._inventories_data.copy()

        # Apply current filter if any
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value:
            self._apply_filter(filter_input.value)

        # Update table
        self._table_last_updated = datetime.now()
        self._update_inventories_table()

        # Fetch capacity metrics for TopPanel
        ping_resp = await client.get("/api/v2/ping/")
        running_jobs = ping_resp.get("active_jobs", 0)
        capacity_pct = 100 - int(ping_resp.get("capacity", {}).get("percent_capacity_remaining", 0))

        # Update top panel
        top_panel = self.query_one(TopPanel)
        top_panel.update_metrics(running_jobs=running_jobs, capacity_pct=capacity_pct)

    def _update_inventories_table(self) -> None:
        """Update inventories DataTable from self._filtered_inventories_data"""
        # Use filtered inventories data
        inventories = self._filtered_inventories_data if self._filtered_inventories_data else self._inventories_data

        # Sort inventories by organization, then name
        def sort_key(inv):
            summary = inv.get("summary_fields", {})
            return (summary.get("organization", {}).get("name", "ZZZ").lower(), inv.get("name", "ZZZ").lower())

        inventories = sorted(inventories, key=sort_key)

        # Build header with count (show X/Y when filtering)
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value and len(self._filtered_inventories_data) != len(self._inventories_data):
            # Filtering active - show filtered/total
            header_text = f"INVENTORIES ({len(self._filtered_inventories_data)}/{len(self._inventories_data)})"
        else:
            # No filter or filter matches all - show just count
            header_text = f"INVENTORIES ({len(inventories)})"

        if self._table_last_updated:
            header_text += f" - Last Updated: {self._table_last_updated.strftime('%H:%M:%S')}"

        self.query_one("#inventories-header").update(header_text)

        table = self.query_one("#inventories-table", DataTable)

        # Save current inventory ID to restore position
        selected_inventory_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_inventory_id = table.get_row_at(cursor_row)[0]  # First column is inventory ID
            except:
                pass

        table.clear()

        new_cursor_row = 0
        for idx, inventory in enumerate(inventories):
            inv_id = str(inventory.get("id", 0))
            name = inventory.get("name", "Unknown")[:40]
            description = inventory.get("description", "")[:50]

            # Get summary fields
            summary = inventory.get("summary_fields", {})
            org = summary.get("organization", {}).get("name", "N/A")[:20]

            # Get host count
            hosts_count = inventory.get("total_hosts", 0)

            # Track if this is the previously selected inventory
            if selected_inventory_id and inv_id == selected_inventory_id:
                new_cursor_row = idx

            table.add_row(inv_id, name, org, description, str(hosts_count))

        # Restore cursor position
        if table.row_count > 0:
            if new_cursor_row < table.row_count:
                table.cursor_coordinate = (new_cursor_row, 0)

    def _apply_filter(self, filter_text: str) -> None:
        """Apply filter to inventories list"""
        if not filter_text.strip():
            self._filtered_inventories_data = self._inventories_data.copy()
            return

        # Parse filter tokens
        tokens = filter_text.lower().split()
        filtered = []

        for inventory in self._inventories_data:
            match = True

            # Extract searchable fields
            inv_id = str(inventory.get("id", ""))
            name = inventory.get("name", "").lower()
            description = inventory.get("description", "").lower()

            summary = inventory.get("summary_fields", {})
            org = summary.get("organization", {}).get("name", "").lower()

            # Check each filter token
            for token in tokens:
                token_match = False

                # Field-specific filters
                if ":" in token:
                    field, value = token.split(":", 1)
                    # Handle comma-separated values (OR logic)
                    values = [v.strip() for v in value.split(",")]

                    if field == "name":
                        token_match = any(v in name for v in values)
                    elif field == "org":
                        token_match = any(v in org for v in values)
                    elif field == "description":
                        token_match = any(v in description for v in values)
                    elif field == "id":
                        token_match = any(v in inv_id for v in values)
                else:
                    # Plain text search across all fields
                    if token in name or token in org or token in description or token in inv_id:
                        token_match = True

                if not token_match:
                    match = False
                    break

            if match:
                filtered.append(inventory)

        self._filtered_inventories_data = filtered

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes"""
        if event.input.id == "filter-input":
            self._apply_filter(event.value)
            self._update_inventories_table()

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
                    ping_resp = await client.get("/api/v2/ping/")
            else:
                ping_resp = await client.get("/api/v2/ping/")

            running_jobs = ping_resp.get("active_jobs", 0)
            capacity_pct = 100 - int(ping_resp.get("capacity", {}).get("percent_capacity_remaining", 0))

            top_panel = self.query_one(TopPanel)
            top_panel.update_metrics(running_jobs=running_jobs, capacity_pct=capacity_pct)

        except Exception as e:
            self.app.log.error(f"Top panel refresh error: {e}")

    def action_refresh(self) -> None:
        """Manual refresh"""
        self.run_worker(self._load_data())
        self.notify("Refreshing inventories...", timeout=1)

    def action_focus_filter(self) -> None:
        """Focus the filter input"""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.focus()

    # Navigation actions
    def action_back_to_dashboard(self) -> None:
        """Navigate to dashboard (ESC)"""
        dashboard_class = self.app.get_dashboard_class()
        self.app.pop_screen()
        self.app.push_screen(dashboard_class())

    def action_goto_dashboard(self) -> None:
        """Navigate to dashboard (key: 1)"""
        dashboard_class = self.app.get_dashboard_class()
        self.app.pop_screen()
        self.app.push_screen(dashboard_class())

    def action_goto_historic_jobs(self) -> None:
        """Navigate to historic jobs (key: 2)"""
        from awx_tui.screens.historic_jobs import HistoricJobsScreen

        self.app.pop_screen()
        self.app.push_screen(HistoricJobsScreen())

    def action_goto_active_jobs(self) -> None:
        """Navigate to active jobs (key: 3)"""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        self.app.pop_screen()
        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Navigate to projects (key: 4)"""
        from awx_tui.screens.projects import ProjectsScreen

        self.app.pop_screen()
        self.app.push_screen(ProjectsScreen())

    def action_goto_templates(self) -> None:
        """Navigate to templates (key: 5)"""
        from awx_tui.screens.templates import TemplatesScreen

        self.app.pop_screen()
        self.app.push_screen(TemplatesScreen())

    def action_goto_inventories(self) -> None:
        """Navigate to inventories (key: 6) - Already here"""
        pass

    def on_screen_resume(self) -> None:
        """Trigger immediate refresh when screen is shown again"""
        # Refresh data to show any changes made in edit screen
        self.run_worker(self._load_data())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle inventory selection - open edit screen"""
        table = self.query_one("#inventories-table", DataTable)
        if table.row_count == 0:
            return

        try:
            row_index = event.cursor_row
            inventory_id = int(table.get_row_at(row_index)[0])

            # Open update inventory screen
            from awx_tui.screens.update_inventory import UpdateInventoryScreen

            self.app.push_screen(UpdateInventoryScreen(inventory_id))

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to select inventory: {e}")
