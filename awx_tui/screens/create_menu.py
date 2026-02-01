"""
AWX TUI - Create Menu Screen

Allows users to select which type of resource to create.
Accessed via 'C' key from anywhere in the app.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class CreateMenuScreen(Screen):
    """
    Create Menu - Select what to create

    Features:
    - DataTable showing Construct and Description for each create option
    - Keyboard navigation: 1-4 to jump to specific option, Enter to select
    - Context-aware: pre-selects option based on calling screen
    - Escape to exit Create Mode
    """

    CSS = """
    CreateMenuScreen {
        align: center middle;
    }

    #create_menu_container {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 2;
    }

    #create_menu_top {
        text-align: center;
        margin-bottom: 1;
    }

    #create_menu_help {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 1;
    }

    #create_options_table {
        height: auto;
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("1", "select_option(0)", "Project", show=True),
        Binding("2", "select_option(1)", "Template", show=True),
        Binding("3", "select_option(2)", "Credential", show=True),
        Binding("4", "select_option(3)", "Inventory", show=True),
        Binding("5", "select_option(4)", "Hosts", show=True),
        Binding("c", "null", "", show=False),  # Hide global 'C' binding
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]

    # Map of create types: (construct_name, description, type_key)
    CREATE_OPTIONS = [
        ("Project", "SCM project with playbooks", "project"),
        ("Job Template", "Playbook execution template", "job_template"),
        ("Credential", "Authentication credential", "credential"),
        ("Inventory", "Host inventory", "inventory"),
        ("Hosts", "Individual inventory host", "hosts"),
    ]

    def __init__(self, context_screen: str = None, **kwargs):
        """
        Initialize Create Menu

        Args:
            context_screen: Name of calling screen for context-aware selection
        """
        super().__init__(**kwargs)
        self.context_screen = context_screen

    def compose(self) -> ComposeResult:
        """Create Create Menu layout"""
        yield Header()

        with Vertical(id="create_menu_container"):
            yield Static("", id="create_menu_top")
            yield Static("Select what to create (1-5 or arrow keys + Enter)", id="create_menu_help")

            # Create options table
            table = DataTable(id="create_options_table", cursor_type="row")
            table.add_columns("Construct", "Description")
            yield table

        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen and set context-aware selection"""
        # Update title with app name and instance info
        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        instance_manager = self.app.instance_manager
        instance_name = instance_manager.current_instance if instance_manager else "No Instance"
        self.title = f"{app_name} - Create Mode for {instance_name}"

        # Update top panel (compact, accent colored)
        top_widget = self.query_one("#create_menu_top", Static)
        top_widget.update(
            f"[bold $accent]{app_name}[/bold $accent]\n[bold $accent]Create Mode for {instance_name}[/bold $accent]"
        )

        # Populate table
        table = self.query_one("#create_options_table", DataTable)
        for construct, description, _ in self.CREATE_OPTIONS:
            table.add_row(construct, description)

        # Set initial selection based on context
        initial_index = self._get_context_index()
        if 0 <= initial_index < len(self.CREATE_OPTIONS):
            table.cursor_coordinate = (initial_index, 0)

    def _get_context_index(self) -> int:
        """Get initial selection index based on calling screen"""
        context_map = {
            "ProjectsScreen": 0,  # Project
            "TemplatesScreen": 1,  # Job Template
            # We don't have Inventory/Credential screens yet, but reserve slots
        }
        return context_map.get(self.context_screen, 0)  # Default to Project

    def action_select_option(self, index: int) -> None:
        """Handle number key press (1-4)"""
        if 0 <= index < len(self.CREATE_OPTIONS):
            table = self.query_one("#create_options_table", DataTable)
            table.cursor_coordinate = (index, 0)
            self._navigate_to_create_screen(index)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or click)"""
        self._navigate_to_create_screen(event.cursor_row)

    def _navigate_to_create_screen(self, index: int) -> None:
        """Navigate to the selected create screen"""
        if index < 0 or index >= len(self.CREATE_OPTIONS):
            return

        _, _, create_type = self.CREATE_OPTIONS[index]

        if create_type == "project":
            from awx_tui.screens.create_project import CreateProjectScreen

            self.app.push_screen(CreateProjectScreen())
        elif create_type == "job_template":
            from awx_tui.screens.create_job_template import CreateJobTemplateScreen

            self.app.push_screen(CreateJobTemplateScreen())
        elif create_type == "credential":
            from awx_tui.screens.create_credential import CreateCredentialScreen

            self.app.push_screen(CreateCredentialScreen())
        elif create_type == "inventory":
            from awx_tui.screens.create_inventory import CreateInventoryScreen

            self.app.push_screen(CreateInventoryScreen())
        elif create_type == "hosts":
            from awx_tui.screens.create_hosts import CreateHostsScreen

            self.app.push_screen(CreateHostsScreen())

    def action_close(self) -> None:
        """Close Create Menu and exit Create Mode"""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
