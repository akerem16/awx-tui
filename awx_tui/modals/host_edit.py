"""
AWX TUI - Host Edit Modal

Modal for creating or editing inventory hosts.
"""

import json
from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Static, TextArea


class HostEditModal(ModalScreen[bool]):
    """
    Host Edit Modal - Create or edit an inventory host

    Args:
        inventory_id: ID of the inventory to add host to (create mode)
        host_data: Existing host data for editing (edit mode). If None, create mode.

    Returns True if saved, False if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=False),
        Binding("ctrl+j", "preview_json", "Preview JSON", show=True),
    ]

    CSS = """
    HostEditModal {
        align: center middle;
    }

    #host-dialog {
        width: 100;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #host-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    .field-row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    .field-label {
        width: 15;
        padding-right: 2;
        text-align: right;
    }

    .field-input {
        width: 1fr;
    }

    Input {
        margin: 0;
        padding: 0 1;
        border: solid $accent;
        height: 3;
        background: $boost;
    }

    TextArea {
        margin: 0;
        padding: 0 1;
        border: solid $accent;
        background: $boost;
    }

    #variables-row {
        height: auto;
        margin-bottom: 1;
    }

    #variables-label-row {
        height: auto;
        margin-bottom: 0;
    }

    #variables_area {
        height: 8;
        width: 100%;
    }

    #host-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(
        self, inventory_id: int, host_data: Optional[Dict[str, Any]] = None, inventory_name: str = "Unknown", **kwargs
    ):
        super().__init__(**kwargs)
        self.inventory_id = inventory_id
        self.host_data = host_data
        self.inventory_name = inventory_name
        self.is_edit_mode = host_data is not None

    def compose(self) -> ComposeResult:
        with Vertical(id="host-dialog"):
            if self.is_edit_mode:
                title = "Edit Host"
            else:
                title = f"Add Host to Inventory '{self.inventory_name}'"
            yield Static(title, id="host-title")

            # Name field
            with Horizontal(classes="field-row"):
                yield Static("Name *:", classes="field-label")
                yield Input(placeholder="Host name (required)", id="name", classes="field-input")

            # Description field
            with Horizontal(classes="field-row"):
                yield Static("Description:", classes="field-label")
                yield Input(placeholder="Optional description", id="description", classes="field-input")

            # Enabled checkbox
            with Horizontal(classes="field-row"):
                yield Static("Enabled:", classes="field-label")
                yield Checkbox("", id="enabled", value=True, classes="field-input")

            # Variables field
            with Vertical(id="variables-row"):
                with Horizontal(id="variables-label-row"):
                    yield Static("Variables:", classes="field-label")
                    yield Static("(JSON format)", classes="field-input")

                yield TextArea("{\n  \n}", language="json", id="variables_area")

            # Buttons
            with Horizontal(id="host-buttons"):
                save_label = "Save" if self.is_edit_mode else "Add"
                yield Button(save_label, variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Initialize form with host data if in edit mode"""
        if self.is_edit_mode and self.host_data:
            # Populate fields with existing host data
            name_input = self.query_one("#name", Input)
            description_input = self.query_one("#description", Input)
            enabled_checkbox = self.query_one("#enabled", Checkbox)
            variables_area = self.query_one("#variables_area", TextArea)

            name_input.value = self.host_data.get("name", "")
            description_input.value = self.host_data.get("description", "")
            enabled_checkbox.value = self.host_data.get("enabled", True)

            # Format variables as JSON
            variables = self.host_data.get("variables", "")
            if variables:
                try:
                    # If variables is a string, parse it
                    if isinstance(variables, str):
                        variables_dict = json.loads(variables) if variables else {}
                    else:
                        variables_dict = variables
                    variables_area.text = json.dumps(variables_dict, indent=2)
                except:
                    variables_area.text = variables if variables else "{\n  \n}"
            else:
                variables_area.text = "{\n  \n}"

        # Focus name input
        self.query_one("#name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            self.action_save()
        else:
            self.action_cancel()

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build host data from current form values (no validation)
        host_data, notes = self._build_host_data_for_preview()

        # Determine endpoint and method based on mode
        if self.is_edit_mode:
            host_id = self.host_data.get("id")
            endpoint = f"/api/v2/hosts/{host_id}/"
            method = "PATCH"
            title = "Host Update - API Payload Preview"
        else:
            endpoint = f"/api/v2/inventories/{self.inventory_id}/hosts/"
            method = "POST"
            title = f"Create Host in Inventory '{self.inventory_name}' - API Payload Preview"

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(json_data=host_data, title=title, endpoint=endpoint, method=method, notes=notes)
        )

    def _build_host_data_for_preview(self) -> tuple:
        """Build host data dict from current form values (for preview, no validation)

        Returns:
            tuple: (host_data dict, notes list)
        """
        # Get form values
        name_input = self.query_one("#name", Input)
        description_input = self.query_one("#description", Input)
        enabled_checkbox = self.query_one("#enabled", Checkbox)
        variables_area = self.query_one("#variables_area", TextArea)

        # Parse variables (lenient, no validation)
        variables_text = variables_area.text.strip()
        try:
            variables_dict = json.loads(variables_text) if variables_text else {}
        except json.JSONDecodeError:
            variables_dict = {}  # Preview continues even with invalid JSON

        host_data = {
            "name": name_input.value.strip(),
            "description": description_input.value.strip(),
            "enabled": enabled_checkbox.value,
            "variables": json.dumps(variables_dict) if variables_dict else "",
        }

        # Build notes
        notes = []
        if self.is_edit_mode:
            host_id = self.host_data.get("id")
            notes.append(f"PATCH to /api/v2/hosts/{host_id}/")
        else:
            notes.append(f"POST to /api/v2/inventories/{self.inventory_id}/hosts/")
            notes.append(f"Host will be created and associated with inventory '{self.inventory_name}'")

        return host_data, notes

    def action_save(self) -> None:
        """Validate and save host"""
        self.run_worker(self._save_host())

    async def _save_host(self) -> None:
        """Save host data"""
        # Validate required fields
        name_input = self.query_one("#name", Input)
        if not name_input.value.strip():
            self.notify("Name is required", severity="error")
            name_input.focus()
            return

        # Validate JSON variables
        variables_area = self.query_one("#variables_area", TextArea)
        variables_text = variables_area.text.strip()

        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON in variables: {e}", severity="error", timeout=5)
                variables_area.focus()
                return
        else:
            variables_dict = {}

        # Build host data payload
        description_input = self.query_one("#description", Input)
        enabled_checkbox = self.query_one("#enabled", Checkbox)

        host_payload = {
            "name": name_input.value.strip(),
            "description": description_input.value.strip(),
            "enabled": enabled_checkbox.value,
            "variables": json.dumps(variables_dict) if variables_dict else "",
        }

        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if self.is_edit_mode:
                # PATCH to update existing host
                host_id = self.host_data.get("id")

                if isinstance(client, AWXClient):
                    async with client:
                        await client.patch(f"/api/v2/hosts/{host_id}/", data=host_payload)
                else:
                    await client.patch(f"/api/v2/hosts/{host_id}/", data=host_payload)

                self.notify(f"Host '{name_input.value}' updated", timeout=2)
            else:
                # POST to create new host (associates with inventory automatically)
                if isinstance(client, AWXClient):
                    async with client:
                        await client.post(f"/api/v2/inventories/{self.inventory_id}/hosts/", data=host_payload)
                else:
                    await client.post(f"/api/v2/inventories/{self.inventory_id}/hosts/", data=host_payload)

                self.notify(f"Host '{name_input.value}' created", timeout=2)

            # Dismiss with success
            self.dismiss(True)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to save host: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to save host: {e}", severity="error", timeout=5)

    def action_cancel(self) -> None:
        """Cancel and close modal"""
        self.dismiss(False)
