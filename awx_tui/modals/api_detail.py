"""
AWX TUI - API Detail Modal

Shows full API call details with navigation between calls.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static


class ApiDetailModal(ModalScreen):
    """Modal screen for displaying full API call details with navigation"""

    CSS = """
    ApiDetailModal {
        align: center middle;
    }

    #modal_container {
        width: 90%;
        height: 80%;
        border: solid $primary;
        background: $surface;
        layout: vertical;
    }

    #panes_container {
        height: 1fr;
        padding: 1;
        layout: horizontal;
    }

    #request_pane {
        width: 50%;
        margin-right: 1;
        layout: vertical;
    }

    #response_pane {
        width: 50%;
        layout: vertical;
    }

    .pane_title {
        height: 1;
        text-align: center;
        background: $boost;
        color: $text;
        border: solid $accent;
    }

    .pane_content {
        height: 1fr;
        padding: 1;
        border: solid $accent;
        border-top: none;
        overflow-y: auto;
    }

    #button_container {
        height: 3;
        dock: bottom;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("pageup", "prev_call", "Previous Call"),
        ("pagedown", "next_call", "Next Call"),
        ("up", "prev_call", "Previous Call"),
        ("down", "next_call", "Next Call"),
        ("escape", "close", "Close"),
        ("backspace", "close", "Close"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, api_calls_data: list, current_index: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.api_calls_data = api_calls_data
        self.current_index = current_index

    def compose(self) -> ComposeResult:
        """Create the modal layout"""
        with Vertical(id="modal_container"):
            # Two panes for request and response
            with Horizontal(id="panes_container"):
                # Request pane
                with Vertical(id="request_pane"):
                    yield Static("REQUEST", classes="pane_title")
                    with ScrollableContainer(classes="pane_content"):
                        yield Static(self._format_request(), id="request_content")

                # Response pane
                with Vertical(id="response_pane"):
                    yield Static("RESPONSE", classes="pane_title")
                    with ScrollableContainer(classes="pane_content"):
                        yield Static(self._format_response(), id="response_content")

            # Button container at bottom
            with Horizontal(id="button_container"):
                yield Button("Open in Advanced API Mode", id="open_api_mode_btn", variant="success")
                yield Button("OK", id="ok_btn", variant="primary")

    def _get_title(self) -> str:
        """Get modal title with navigation info"""
        current_call = self.api_calls_data[self.current_index]
        total = len(self.api_calls_data)
        return f"API Call {self.current_index + 1} of {total} - {current_call.get('url', 'Unknown')} | PageUp/PageDown to navigate"

    def _format_request(self) -> str:
        """Format the request details"""
        call = self.api_calls_data[self.current_index]

        method = call.get("method", "UNKN")
        url = call.get("url", "Unknown")
        instance = call.get("instance", "Unknown")

        # Escape opening markup bracket
        escaped_url = str(url).replace("[", "\\[")

        content_lines = [
            f"Method: {method}",
            f"URL: {escaped_url}",
            f"Instance: {instance}",
            f"Timestamp: {call.get('timestamp', 'Unknown')}",
            "",
            "cURL Command:",
            f'curl -X {method} -i "{escaped_url}"',
            "",
        ]

        # Add request headers if available
        request_headers = call.get("request_headers", {})
        if request_headers:
            content_lines.extend(["Request Headers:", self._format_headers(request_headers), ""])

        # Add request body if available (for POST/PUT/PATCH)
        request_body = call.get("request_body", "")
        if request_body:
            # Truncate to 500 chars like response preview
            request_body_preview = str(request_body)[:500]
            escaped_body = request_body_preview.replace("[", "\\[")
            content_lines.extend(["Request Body (Preview - 500 chars):", f"{escaped_body}"])

        return "\n".join(content_lines)

    def _format_headers(self, headers: dict) -> str:
        """Format headers for display, highlighting X-* headers"""
        if not headers:
            return "No headers"

        formatted = []
        # Show X-* headers first
        x_headers = {k: v for k, v in headers.items() if k.startswith("X-") or k.startswith("x-")}
        other_headers = {k: v for k, v in headers.items() if not (k.startswith("X-") or k.startswith("x-"))}

        if x_headers:
            for key, value in x_headers.items():
                formatted.append(f"  {key}: {value}")

        # Show other important headers
        for key, value in list(other_headers.items())[:10]:
            formatted.append(f"  {key}: {value}")

        if len(other_headers) > 10:
            formatted.append(f"  ... and {len(other_headers) - 10} more")

        return "\n".join(formatted)

    def _format_response(self) -> str:
        """Format the response details"""
        call = self.api_calls_data[self.current_index]

        status_code = call.get("status_code", 0)

        # Status handling - all 2xx codes are success
        status_emoji = "[green]✓[/green]" if 200 <= status_code < 300 else "[red]✗[/red]"
        status_text = f"HTTP Status: {status_code}"

        content_lines = [
            f"{status_emoji} {status_text}",
            f"Duration: {call.get('duration_ms', 'Unknown')}ms",
            f"Size: {call.get('size_bytes', 'Unknown')} bytes",
            "",
        ]

        # Add response headers if available
        response_headers = call.get("response_headers", {})
        if response_headers:
            content_lines.extend(["Response Headers:", self._format_headers(response_headers), ""])

        # Show full response content if available, otherwise fall back to preview
        full_content = call.get("response_content_full")
        if full_content:
            # Escape opening markup bracket
            escaped_content = str(full_content).replace("[", "\\[")
            content_lines.extend(["Response Body (Full):", f"{escaped_content}"])
        else:
            # Fallback to preview
            preview = call.get("content_preview") or call.get("response_content", "No content available")
            escaped_preview = str(preview).replace("[", "\\[")
            content_lines.extend(["Response Body (Preview - 500 chars):", f"{escaped_preview}"])

        # Add error info if available
        if call.get("error"):
            content_lines.extend(["", "Error Details:", f"{call.get('error')}"])

        return "\n".join(content_lines)

    def _update_content(self):
        """Update the modal content for current index"""
        # Update request content
        request_widget = self.query_one("#request_content", Static)
        request_widget.update(self._format_request())

        # Update response content
        response_widget = self.query_one("#response_content", Static)
        response_widget.update(self._format_response())

    def action_prev_call(self) -> None:
        """Navigate to previous API call"""
        if self.current_index > 0:
            self.current_index -= 1
            self._update_content()
            self._update_parent_selection()

    def action_next_call(self) -> None:
        """Navigate to next API call"""
        if self.current_index < len(self.api_calls_data) - 1:
            self.current_index += 1
            self._update_content()
            self._update_parent_selection()

    def _update_parent_selection(self) -> None:
        """Update the parent debug console selection"""
        try:
            # Find the debug console screen in the stack
            debug_screen = None
            for screen in self.app.screen_stack:
                if hasattr(screen, "__class__") and screen.__class__.__name__ == "DebugConsoleScreen":
                    debug_screen = screen
                    break

            if debug_screen and hasattr(debug_screen, "api_call_data"):
                try:
                    # Update the cursor position in the API call list
                    api_table = debug_screen.query_one("#api_call_list", DataTable)
                    if api_table:
                        # Ensure we don't go out of bounds and table has rows
                        max_rows = api_table.row_count
                        data_length = len(debug_screen.api_call_data)

                        if max_rows > 0 and 0 <= self.current_index < min(max_rows, data_length):
                            # Set cursor coordinate directly
                            api_table.cursor_coordinate = (self.current_index, 0)
                            # Update the details panel
                            if hasattr(debug_screen, "update_details_for_row"):
                                debug_screen.update_details_for_row(self.current_index)
                except Exception:
                    pass
        except Exception:
            pass

    def action_close(self) -> None:
        """Close the modal"""
        self.dismiss()

    def on_key(self, event) -> None:
        """Handle key presses in modal"""
        if event.key == "enter":
            # ENTER should close the modal
            self.dismiss()
            event.stop()
            event.prevent_default()

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "ok_btn":
            self.dismiss()
        elif event.button.id == "open_api_mode_btn":
            self.action_open_advanced_api_mode()

    def action_open_advanced_api_mode(self) -> None:
        """Open Advanced API Mode with current API call"""
        # Get current API call data
        call_data = self.api_calls_data[self.current_index]

        # Extract pre-population data (reuse logic from debug console)
        prepopulate_data = self._extract_prepopulate_data(call_data)

        # Close this modal first
        self.dismiss()

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
