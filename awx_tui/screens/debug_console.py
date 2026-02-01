"""
AWX TUI - Debug Console Screen

Shows API call logs for debugging and development.
Based on container-registry-card-catalog pattern.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class ApiCallDetailsPanel(Static):
    """Right panel showing detailed API call information"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.call_info = None

    def update_call_info(self, call_info: dict):
        """Update the displayed API call information"""
        self.call_info = call_info
        if call_info:
            # Escape opening markup bracket
            url = str(call_info.get("url", "Unknown")).replace("[", "\\[")
            method = str(call_info.get("method", "UNKN"))
            status_code = call_info.get("status_code", 0)
            duration = str(call_info.get("duration_ms", "Unknown"))
            size_bytes = str(call_info.get("size_bytes", "Unknown"))
            timestamp = str(call_info.get("timestamp", "Unknown"))

            # Status handling - all 2xx codes are success
            status_emoji = "[green]✓[/green]" if 200 <= status_code < 300 else "[red]✗[/red]"
            status_text = f"HTTP Status: {status_code}"

            # Use preview content (first 500 chars) for debug view
            content_display = str(call_info.get("content_preview", "No content")).replace("[", "\\[")

            # Request body (for POST/PUT/PATCH)
            request_body = call_info.get("request_body", "")
            request_body_section = ""
            if request_body:
                # Truncate to 500 chars like response preview
                request_body_preview = str(request_body)[:500]
                request_body_display = request_body_preview.replace("[", "\\[")
                request_body_section = f"\n\nRequest Body (Preview - 500 chars):\n{request_body_display}\n"

            details = f"""Method: {method}
URL: {url}
{status_emoji} {status_text}
Duration: {duration}ms
Size: {size_bytes} bytes
Time: {timestamp}

cURL Command:
curl -X {method} -i "{url}"{request_body_section}
Response Preview:
{content_display}"""

            self.update(details)
        else:
            self.update("Select an API call to view details")


class DebugConsoleScreen(Screen):
    """Screen for viewing API call debug information"""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #api_call_list {
        width: 60%;
        border: solid $primary;
        margin: 1;
    }

    #api_call_details {
        width: 40%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("backspace", "back", "Back"),
        ("ctrl+q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("ctrl+x", "purge", "Purge All"),
        ("ctrl+t", "open_in_advanced_api_mode", "API Mode"),
        ("ctrl+d", "no_action", ""),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_call_data = []
        self.last_click_time = 0
        self.last_clicked_row = -1

    def compose(self) -> ComposeResult:
        """Create the debug console layout"""
        yield Header()
        with Horizontal():
            # Left panel - API call list
            api_table = DataTable(id="api_call_list", cursor_type="row")
            api_table.add_columns("Time", "Method", "Instance", "Endpoint", "Status", "Size", "Duration")
            yield api_table

            # Right panel - API call details
            yield ApiCallDetailsPanel(id="api_call_details")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the debug console"""
        self.title = "Debug Console - API Calls"
        self.load_api_calls()

        # Auto-select last row (most recent call) on initial load
        api_table = self.query_one("#api_call_list", DataTable)
        if self.api_call_data:
            last_row = len(self.api_call_data) - 1
            api_table.cursor_coordinate = (last_row, 0)
            self.update_details_for_row(last_row)
        else:
            # No API calls yet - show placeholder
            details_panel = self.query_one("#api_call_details", ApiCallDetailsPanel)
            details_panel.update("Select an API call to view details")

    def load_api_calls(self) -> None:
        """Load API calls from app's API call log"""
        api_table = self.query_one("#api_call_list", DataTable)

        # Clear existing data
        api_table.clear()
        self.api_call_data = []

        # Get API call log from app
        if hasattr(self.app, "api_call_log"):
            # Load API calls
            for call in self.app.api_call_log:
                # Extract instance name and endpoint
                instance = call.get("instance", "Unknown")
                endpoint = call.get("endpoint", call.get("url", ""))

                # Format size
                size_bytes = call.get("size_bytes", 0)
                if size_bytes > 1024:
                    size = f"{size_bytes / 1024:.1f}KB"
                else:
                    size = f"{size_bytes}B"

                # Status with emoji - all 2xx codes are success, 4xx/5xx are errors
                status_code = call.get("status_code", 0)
                if 200 <= status_code < 300:
                    status = f"[green]✓[/green] {status_code}"
                elif status_code == 0:
                    status = "[red]✗[/red] ERR"
                elif status_code >= 400:
                    status = f"[red]✗[/red] {status_code}"
                else:
                    status = f"⚠ {status_code}"

                api_table.add_row(
                    call.get("timestamp", "Unknown"),
                    call.get("method", "UNKN"),
                    instance,
                    endpoint,
                    status,
                    size,
                    f"{call.get('duration_ms', 0):,}ms",
                )
                self.api_call_data.append(call)

    def update_details_for_row(self, row_index: int) -> None:
        """Update details panel for given row index"""
        details_panel = self.query_one("#api_call_details", ApiCallDetailsPanel)

        if 0 <= row_index < len(self.api_call_data):
            call = self.api_call_data[row_index]
            details_panel.update_call_info(call)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle API call row highlighting (auto-select)"""
        self.update_details_for_row(event.cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle API call selection and double-click detection"""
        import time

        current_time = time.time()

        # Double-click detection (within 500ms of previous click on same row)
        if (
            current_time - self.last_click_time < 0.5
            and self.last_clicked_row == event.cursor_row
            and 0 <= event.cursor_row < len(self.api_call_data)
        ):

            # Double-click detected - show API detail modal
            self.show_api_detail_modal(self.api_call_data[event.cursor_row])
            event.stop()  # Prevent event bubbling
        else:
            # Single click - update details
            self.update_details_for_row(event.cursor_row)

        # Update click tracking and stop event bubbling
        self.last_click_time = current_time
        self.last_clicked_row = event.cursor_row
        event.stop()  # Prevent event bubbling

    def on_key(self, event) -> None:
        """Handle key presses"""
        # Only handle ENTER if we're focused on the debug console specifically
        if event.key == "enter":
            # Check if the API table is focused
            api_table = self.query_one("#api_call_list", DataTable)
            if api_table.has_focus and hasattr(api_table, "cursor_coordinate") and api_table.cursor_coordinate:
                row_index = api_table.cursor_coordinate[0]
                if 0 <= row_index < len(self.api_call_data):
                    self.show_api_detail_modal(self.api_call_data[row_index])
                event.stop()  # Prevent event bubbling

    def show_api_detail_modal(self, call_data: dict) -> None:
        """Show API call details in modal"""
        from awx_tui.modals.api_detail import ApiDetailModal

        # Find the index of the selected call
        api_table = self.query_one("#api_call_list", DataTable)
        current_index = (
            api_table.cursor_coordinate[0]
            if hasattr(api_table, "cursor_coordinate") and api_table.cursor_coordinate
            else 0
        )

        # Pass all API calls and current index for navigation
        modal = ApiDetailModal(self.api_call_data, current_index)
        self.app.push_screen(modal)

    def auto_refresh_callback(self) -> None:
        """Auto-refresh API call list (silent, preserves selection)"""
        api_table = self.query_one("#api_call_list", DataTable)

        # Remember currently selected row index
        current_row = None
        if hasattr(api_table, "cursor_coordinate") and api_table.cursor_coordinate:
            current_row = api_table.cursor_coordinate[0]

        # Reload API calls
        self.load_api_calls()

        # Restore selection if possible, otherwise select last row (most recent)
        if current_row is not None and current_row < len(self.api_call_data):
            api_table.cursor_coordinate = (current_row, 0)
            self.update_details_for_row(current_row)
        elif self.api_call_data:
            # Select last row (most recent call)
            last_row = len(self.api_call_data) - 1
            api_table.cursor_coordinate = (last_row, 0)
            self.update_details_for_row(last_row)

    def action_refresh(self) -> None:
        """Refresh API call list (manual, shows notification)"""
        self.auto_refresh_callback()
        self.notify("API call list refreshed")

    def action_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()

    def action_purge(self) -> None:
        """Purge all API call data"""
        if hasattr(self.app, "api_call_log"):
            self.app.api_call_log.clear()
            self.notify("API call log purged", severity="warning")
            # Reload the list
            self.load_api_calls()

    def action_no_action(self) -> None:
        """Do nothing - prevents Ctrl+D from opening debug console within debug console"""
        pass

    def action_open_in_advanced_api_mode(self) -> None:
        """Open Advanced API Mode with currently selected API call"""
        api_table = self.query_one("#api_call_list", DataTable)

        # Get currently selected row
        if not hasattr(api_table, "cursor_coordinate") or not api_table.cursor_coordinate:
            self.notify("No API call selected", severity="warning", timeout=2)
            return

        row_index = api_table.cursor_coordinate[0]
        if not (0 <= row_index < len(self.api_call_data)):
            self.notify("No API call selected", severity="warning", timeout=2)
            return

        # Get selected API call data
        call_data = self.api_call_data[row_index]

        # Extract pre-population data from API call
        prepopulate_data = self._extract_prepopulate_data(call_data)

        # Open Advanced API Mode with pre-populated data
        from awx_tui.screens.advanced_api_mode import AdvancedAPIModeScreen

        self.app.push_screen(AdvancedAPIModeScreen(prepopulate_data=prepopulate_data))

    def _extract_prepopulate_data(self, call_data: dict) -> dict:
        """Extract pre-population data from debug log API call entry"""
        import json
        from urllib.parse import urlparse

        prepopulate = {}

        # Method (GET, POST, etc.)
        prepopulate["method"] = call_data.get("method", "GET")

        # Endpoint - strip API base path since it's shown in the header
        endpoint = call_data.get("endpoint", "")

        # Strip common API base paths to show just the resource path
        # This makes it easier to edit - base path is shown in instance header
        if endpoint.startswith("/api/v2/"):
            endpoint = endpoint.replace("/api/v2/", "", 1)
        elif endpoint.startswith("/api/controller/v2/"):
            endpoint = endpoint.replace("/api/controller/v2/", "", 1)

        # Extract query parameters from full URL if present
        full_url = call_data.get("url", "")
        if full_url and "?" in full_url:
            # Parse URL to get query string
            parsed = urlparse(full_url)
            if parsed.query:
                # Append query params to endpoint
                endpoint = f"{endpoint}?{parsed.query}"

        prepopulate["endpoint"] = endpoint

        # Request body (if POST/PUT/PATCH)
        request_body = call_data.get("request_body", "")
        prepopulate["request_body"] = request_body if request_body else ""

        # Request headers
        request_headers = call_data.get("request_headers", {})
        prepopulate["request_headers"] = request_headers

        # Response body (previous response, read-only)
        response_content = call_data.get("response_content_full", "")
        if response_content:
            # Try to parse as JSON
            try:
                response_json = json.loads(response_content)
                prepopulate["response_body"] = response_json
            except json.JSONDecodeError:
                prepopulate["response_body"] = response_content

        # Response headers
        response_headers = call_data.get("response_headers", {})
        prepopulate["response_headers"] = response_headers

        # Instance name (for temporary override in Advanced API Mode)
        # Don't switch the global instance, just use this for the API Mode session
        prepopulate["instance_name"] = call_data.get("instance_name")

        return prepopulate

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
