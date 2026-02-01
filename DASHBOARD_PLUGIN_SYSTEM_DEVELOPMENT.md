# Dashboard Plugin System - Developer Guide

**Version:** 1.0
**Last Updated:** 2025-12-02
**Authors:** Claude Sonnet 4.5, John Mitchell, Andrew Potozniak

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Creating a New Dashboard](#creating-a-new-dashboard)
5. [BaseDashboard API Reference](#basedashboard-api-reference)
6. [Fetching Data](#fetching-data)
7. [Updating the Display](#updating-the-display)
8. [Accessing Additional Data Sources](#accessing-additional-data-sources)
9. [CSS Styling](#css-styling)
10. [Registration and Loading](#registration-and-loading)
11. [Testing](#testing)
12. [Best Practices](#best-practices)
13. [Examples](#examples)

---

## Overview

The AWX TUI dashboard plugin system provides a framework for creating multiple dashboard layouts with different UI/UX paradigms. Each dashboard is a self-contained module that:

- Inherits from `BaseDashboard` abstract class
- Implements two core methods: `fetch_data()` and `update_display()`
- Registers itself via the `@register_dashboard()` decorator
- Has its own CSS file for styling

**Key Benefits:**
- **Persona-specific UX**: Different layouts for different user types (admins, developers, operators)
- **Per-instance customization**: Each AWX instance can use a different dashboard
- **No code duplication**: Auto-refresh and lifecycle management handled by `BaseDashboard`
- **Easy to add**: Create new dashboards without modifying core code

**Existing Dashboards:**
- `classic`: Original 6-panel layout with detailed metrics (for admins)
- `sleek`: Compact sidebar layout with mini loaf (for users)

---

## Quick Start

**5-Minute Dashboard Creation:**

```python
# awx_tui/dashboards/minimal.py
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Header, Footer
from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard


@register_dashboard('minimal')
class MinimalDashboard(BaseDashboard):
    """Minimal dashboard showing only running jobs"""

    CSS = """
    Screen {
        layout: vertical;
    }

    #jobs-table {
        height: 1fr;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        jobs_table = DataTable(id="jobs-table", cursor_type="row")
        jobs_table.add_columns("ID", "Name", "Status")
        yield jobs_table
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize and start auto-refresh"""
        await super().on_mount()  # Critical: triggers auto-refresh

    async def fetch_data(self, client):
        """Fetch all data needed for this dashboard"""
        # Use helper methods from BaseDashboard
        running_jobs = await self.fetch_running_jobs(client, page_size=50)

        return {
            'running_jobs': running_jobs
        }

    def update_display(self, data):
        """Update UI with fetched data"""
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.clear()

        for job in data['running_jobs']:
            jobs_table.add_row(
                str(job.get('id', 0)),
                job.get('name', 'Unknown'),
                job.get('status', 'unknown')
            )
```

**Register the dashboard:**

```python
# awx_tui/dashboards/__init__.py
# Add this import to trigger registration
try:
    from .minimal import MinimalDashboard  # noqa: F401
except ImportError:
    pass  # Minimal dashboard not yet created
```

**Use it:**

```yaml
# config.yaml
instances:
  dev1:
    url: https://awx.dev.example.com
    auth:
      method: token
      username: admin
      token: your-token
    dashboard: minimal  # <-- Use new dashboard
```

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  AWX TUI Application                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Instance Selection Screen                  │   │
│  │  - Reads instance.dashboard from config            │   │
│  │  - Calls get_dashboard(name) to load class        │   │
│  │  - Pushes dashboard screen to app                 │   │
│  └───────────────────┬────────────────────────────────┘   │
│                      │                                      │
│                      ▼                                      │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Dashboard Registry (__init__.py)           │   │
│  │  - DASHBOARD_REGISTRY dict                         │   │
│  │  - @register_dashboard() decorator                 │   │
│  │  - get_dashboard() loader with fallback           │   │
│  └───────────────────┬────────────────────────────────┘   │
│                      │                                      │
│         ┌────────────┴────────────┐                        │
│         ▼                         ▼                        │
│  ┌─────────────┐          ┌─────────────┐                │
│  │   Classic   │          │    Sleek    │  (+ more)      │
│  │  Dashboard  │          │  Dashboard  │                │
│  └──────┬──────┘          └──────┬──────┘                │
│         │                         │                        │
│         └────────────┬────────────┘                        │
│                      ▼                                      │
│  ┌────────────────────────────────────────────────────┐   │
│  │            BaseDashboard (base.py)                 │   │
│  │  - Auto-refresh orchestration                      │   │
│  │  - Lifecycle management (mount/suspend/resume)     │   │
│  │  - Abstract: fetch_data(), update_display()       │   │
│  │  - Helpers: fetch_running_jobs(), etc.            │   │
│  └───────────────────┬────────────────────────────────┘   │
│                      │                                      │
│                      ▼                                      │
│  ┌────────────────────────────────────────────────────┐   │
│  │         AWX API Client (client.py)                 │   │
│  │  - GET/POST/PUT/PATCH/DELETE methods              │   │
│  │  - Authentication handling                         │   │
│  │  - API call logging                                │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User selects instance
   └─> Instance Selection reads instance.dashboard config
       └─> Calls get_dashboard('sleek') from registry
           └─> Returns SleekDashboard class
               └─> Pushes SleekDashboard() screen to app

2. Dashboard mounts (on_mount called)
   └─> super().on_mount() triggers BaseDashboard._refresh()
       └─> Acquires refresh lock
           └─> Gets AWXClient from instance_manager
               └─> Calls SleekDashboard.fetch_data(client)
                   └─> Returns dict of data
                       └─> Calls SleekDashboard.update_display(data)
                           └─> Updates UI widgets with data

3. Auto-refresh timer fires every N seconds
   └─> BaseDashboard._auto_refresh_callback()
       └─> (repeats step 2 cycle)

4. User presses 'r' or F5
   └─> Dashboard.action_refresh()
       └─> super().action_refresh() triggers refresh
           └─> (same as step 2)
```

---

## Creating a New Dashboard

### Step 1: Create Dashboard File

Create a new Python file in `awx_tui/dashboards/`:

```bash
touch awx_tui/dashboards/myboard.py
```

### Step 2: Implement Dashboard Class

```python
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Header, Footer
from textual.containers import Container, Horizontal, Vertical

from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard


@register_dashboard('myboard')
class MyDashboard(BaseDashboard):
    """
    My custom dashboard layout

    Shows X, Y, and Z in a unique arrangement optimized for [persona].
    """

    # Option 1: Inline CSS
    CSS = """
    Screen {
        layout: vertical;
    }

    #my-panel {
        height: 1fr;
        border: solid $primary;
    }
    """

    # Option 2: External CSS file (recommended for complex layouts)
    CSS_PATH = "myboard.tcss"

    # Optional: Custom keybindings
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_instances", "Back"),
        # Add custom bindings here
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize any dashboard-specific state
        self._cached_data = {}

    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        yield Header()

        # Your custom layout here
        with Container(id="my-container"):
            yield Static("Loading...", id="my-panel")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize dashboard and start auto-refresh"""
        self.title = "My Dashboard"

        # Set up any widgets (tables, etc.)
        # ...

        # CRITICAL: Call parent on_mount to trigger auto-refresh
        await super().on_mount()

    async def fetch_data(self, client):
        """
        Fetch all data this dashboard needs.

        Args:
            client: AWXClient instance for this instance

        Returns:
            dict: Data to pass to update_display()
        """
        import asyncio

        # Use helper methods from BaseDashboard
        running_jobs = await self.fetch_running_jobs(client, page_size=100)
        recent_jobs = await self.fetch_recent_jobs(client, page_size=25)
        instances = await self.fetch_instances(client)

        # Or make custom API calls
        custom_data = await client.get('/api/v2/my_endpoint/')

        # Fetch multiple endpoints in parallel
        results = await asyncio.gather(
            client.get('/api/v2/projects/'),
            client.get('/api/v2/inventories/'),
            client.get('/api/v2/credentials/'),
        )
        projects_resp, inventories_resp, credentials_resp = results

        # Return all data as dict
        return {
            'running_jobs': running_jobs,
            'recent_jobs': recent_jobs,
            'instances': instances,
            'custom_data': custom_data,
            'projects': projects_resp.get('results', []),
            'inventories': inventories_resp.get('results', []),
            'credentials': credentials_resp.get('results', []),
        }

    def update_display(self, data):
        """
        Update dashboard UI with fetched data.

        Args:
            data: dict returned from fetch_data()
        """
        # Extract data
        running_jobs = data['running_jobs']
        instances = data['instances']

        # Update widgets
        panel = self.query_one("#my-panel", Static)
        panel.update(f"Running jobs: {len(running_jobs)}")

        # Update tables, charts, etc.
        # ...

    def action_refresh(self) -> None:
        """Manual refresh (r key or F5)"""
        self.notify("Refreshing...", timeout=1)
        super().action_refresh()
```

### Step 3: Create CSS File (Optional)

If using `CSS_PATH`, create `awx_tui/dashboards/myboard.tcss`:

```css
/* My Dashboard Styles */

Screen {
    background: $surface;
}

#my-container {
    width: 100%;
    height: 100%;
    layout: vertical;
}

#my-panel {
    height: 1fr;
    border: solid $primary;
    padding: 1 2;
}

DataTable {
    height: auto;
}
```

### Step 4: Register Dashboard

Add import to `awx_tui/dashboards/__init__.py`:

```python
# Import dashboard implementations to trigger @register_dashboard decorators
try:
    from .classic import ClassicDashboard  # noqa: F401
except ImportError:
    pass

try:
    from .sleek import SleekDashboard  # noqa: F401
except ImportError:
    pass

try:
    from .myboard import MyDashboard  # noqa: F401
except ImportError:
    pass  # MyDashboard not yet created
```

### Step 5: Update CLI Choices (Optional)

If you want the dashboard to appear in `--dashboard` CLI argument choices:

```python
# awx_tui/main.py
parser.add_argument(
    "--dashboard",
    type=str,
    metavar="NAME",
    choices=["classic", "sleek", "myboard"],  # Add here
    help="Dashboard layout to use"
)
```

### Step 6: Use Dashboard

```yaml
# config.yaml
instances:
  my-instance:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: xxx
    dashboard: myboard  # <-- Your new dashboard
```

Or via environment variable:

```bash
export AWX_DASHBOARD=myboard
awx-tui
```

Or via CLI argument:

```bash
awx-tui --host https://awx.example.com --token xxx --dashboard myboard
```

---

## BaseDashboard API Reference

### Abstract Methods (Must Implement)

#### `async fetch_data(client) -> dict`

**Purpose:** Fetch all data the dashboard needs from AWX API.

**Called by:** `BaseDashboard._refresh()` during auto-refresh cycle

**Arguments:**
- `client`: `AWXClient` instance for the current instance

**Returns:**
- `dict`: Data to pass to `update_display()`

**Pattern:**
```python
async def fetch_data(self, client):
    import asyncio

    # Fetch data in parallel for performance
    results = await asyncio.gather(
        self.fetch_running_jobs(client),
        self.fetch_recent_jobs(client),
        self.fetch_instances(client),
        # ... more API calls
    )

    return {
        'running_jobs': results[0],
        'recent_jobs': results[1],
        'instances': results[2],
        # ... more data
    }
```

**Error Handling:**
- Wrap individual calls in try/except if you want to continue on partial failure
- `BaseDashboard._refresh()` catches exceptions and shows error notification

---

#### `update_display(data) -> None`

**Purpose:** Update the dashboard UI with fetched data.

**Called by:** `BaseDashboard._refresh()` after `fetch_data()` completes

**Arguments:**
- `data`: `dict` returned from `fetch_data()`

**Returns:** `None`

**Pattern:**
```python
def update_display(self, data):
    # Extract data
    running_jobs = data['running_jobs']
    instances = data['instances']

    # Update widgets
    table = self.query_one("#jobs-table", DataTable)
    table.clear()

    for job in running_jobs:
        table.add_row(
            str(job['id']),
            job['name'],
            job['status']
        )
```

**Important:**
- This is a **synchronous** method (not async)
- Should only update UI, not make API calls
- Use `self.query_one()` to get widget references
- Update tables, labels, charts, etc.

---

### Helper Methods (Available to Use)

#### `async fetch_running_jobs(client, page_size=200) -> list`

Fetch running/pending/waiting jobs.

```python
running_jobs = await self.fetch_running_jobs(client, page_size=100)
# Returns: [{'id': 1, 'name': 'Deploy', 'status': 'running', ...}, ...]
```

---

#### `async fetch_recent_jobs(client, page_size=25) -> list`

Fetch recent completed jobs (successful, failed, canceled).

```python
recent_jobs = await self.fetch_recent_jobs(client, page_size=50)
# Returns: [{'id': 2, 'name': 'Deploy', 'status': 'successful', ...}, ...]
```

---

#### `async fetch_instances(client) -> list`

Fetch AWX controller instances.

```python
instances = await self.fetch_instances(client)
# Returns: [{'hostname': 'awx-1', 'capacity': 100, ...}, ...]
```

---

#### `async fetch_instance_groups(client) -> list`

Fetch AWX instance groups.

```python
groups = await self.fetch_instance_groups(client)
# Returns: [{'name': 'default', 'capacity': 200, ...}, ...]
```

---

### Lifecycle Methods

#### `async on_mount() -> None`

**Called when:** Dashboard screen is mounted (first displayed)

**Pattern:**
```python
async def on_mount(self) -> None:
    """Initialize dashboard and start auto-refresh"""
    self.title = "My Dashboard"

    # Set up widgets (add table columns, etc.)
    jobs_table = self.query_one("#jobs-table", DataTable)
    jobs_table.add_columns("ID", "Name", "Status")

    # CRITICAL: Call parent to trigger auto-refresh
    await super().on_mount()
```

**Important:**
- **MUST** call `await super().on_mount()` at the end
- Parent method triggers initial refresh and starts auto-refresh timer

---

#### `on_screen_suspend() -> None`

**Called when:** Dashboard screen is hidden (user navigates away)

**Default behavior:** Stops auto-refresh timer

**Override pattern:**
```python
def on_screen_suspend(self) -> None:
    """Called when dashboard is hidden"""
    super().on_screen_suspend()  # Stop auto-refresh

    # Custom cleanup here
    self.my_custom_timer.stop()
```

---

#### `on_screen_resume() -> None`

**Called when:** Dashboard screen is shown again (user navigates back)

**Default behavior:** Restarts auto-refresh timer

**Override pattern:**
```python
def on_screen_resume(self) -> None:
    """Called when dashboard is shown again"""
    super().on_screen_resume()  # Restart auto-refresh

    # Custom resume logic here
    self.my_custom_timer.start()
```

---

### Refresh Methods

#### `action_refresh() -> None`

**Purpose:** Manual refresh trigger (bound to 'r' and F5 keys)

**Pattern:**
```python
def action_refresh(self) -> None:
    """Manual refresh dashboard data"""
    self.notify("Refreshing...", timeout=1)
    super().action_refresh()  # Trigger refresh
```

**Important:**
- Call `super().action_refresh()` to trigger actual refresh
- `BaseDashboard` handles the refresh logic

---

### Configuration Access

#### `self.app.app_config`

Access application configuration:

```python
# Get refresh interval
refresh_interval = self.app.app_config.preferences.get('dashboard_refresh_interval', 5)

# Get current instance config
instance_name = self.app.instance_manager.current_instance
instance_config = self.app.app_config.instances.get(instance_name)
```

---

#### `self.app.instance_manager`

Access instance manager:

```python
# Get current instance name
current = self.app.instance_manager.current_instance

# Get client for current instance
client = self.app.instance_manager.get_client()

# Get client for specific instance
client = self.app.instance_manager.get_client('dev2')
```

---

## Fetching Data

### Using BaseDashboard Helpers

The simplest approach - use built-in helper methods:

```python
async def fetch_data(self, client):
    running_jobs = await self.fetch_running_jobs(client, page_size=100)
    recent_jobs = await self.fetch_recent_jobs(client, page_size=25)
    instances = await self.fetch_instances(client)
    groups = await self.fetch_instance_groups(client)

    return {
        'running_jobs': running_jobs,
        'recent_jobs': recent_jobs,
        'instances': instances,
        'groups': groups,
    }
```

---

### Making Custom API Calls

For data not covered by helpers:

```python
async def fetch_data(self, client):
    # Single endpoint
    projects_resp = await client.get('/api/v2/projects/')
    projects = projects_resp.get('results', [])

    # With query parameters
    jobs_resp = await client.get('/api/v2/jobs/', params={
        'status__in': 'successful,failed',
        'page_size': 50,
        'order_by': '-finished'
    })

    # POST request
    launch_resp = await client.post('/api/v2/job_templates/5/launch/', data={
        'limit': 'webservers'
    })

    return {
        'projects': projects,
        'jobs': jobs_resp.get('results', []),
        'launch': launch_resp,
    }
```

---

### Parallel API Calls

For best performance, fetch multiple endpoints in parallel:

```python
async def fetch_data(self, client):
    import asyncio

    # Define async functions for each data source
    async def safe_get(endpoint, params=None, description=""):
        """Wrapper to catch exceptions per-endpoint"""
        try:
            return await client.get(endpoint, params=params)
        except Exception as e:
            self.app.log.error(f"Failed to fetch {description}: {e}")
            return {}

    # Fetch all in parallel
    results = await asyncio.gather(
        safe_get('/api/v2/projects/', None, "projects"),
        safe_get('/api/v2/inventories/', None, "inventories"),
        safe_get('/api/v2/job_templates/', None, "templates"),
        safe_get('/api/v2/credentials/', None, "credentials"),
        safe_get('/api/v2/organizations/', {'page_size': 1}, "org count"),
    )

    # Unpack results
    projects_resp, inventories_resp, templates_resp, creds_resp, orgs_resp = results

    return {
        'projects': projects_resp.get('results', []),
        'inventories': inventories_resp.get('results', []),
        'templates': templates_resp.get('results', []),
        'credentials': creds_resp.get('results', []),
        'org_count': orgs_resp.get('count', 0),
    }
```

---

### Calculating Derived Data

Perform calculations in `fetch_data()` to keep `update_display()` simple:

```python
async def fetch_data(self, client):
    import asyncio
    from datetime import datetime, timedelta

    # Fetch raw data
    jobs_resp = await client.get('/api/v2/unified_jobs/', params={
        'finished__gte': (datetime.now() - timedelta(days=7)).isoformat(),
        'page_size': 500
    })

    jobs = jobs_resp.get('results', [])

    # Calculate metrics
    success_count = sum(1 for j in jobs if j.get('status') == 'successful')
    failed_count = sum(1 for j in jobs if j.get('status') == 'failed')
    avg_duration = sum(j.get('elapsed', 0) for j in jobs) / len(jobs) if jobs else 0

    # Group by day
    jobs_by_day = {}
    for job in jobs:
        finished = job.get('finished', '')
        if finished:
            day = finished.split('T')[0]
            jobs_by_day[day] = jobs_by_day.get(day, 0) + 1

    return {
        'jobs': jobs,
        'success_count': success_count,
        'failed_count': failed_count,
        'avg_duration': avg_duration,
        'jobs_by_day': jobs_by_day,
    }
```

---

## Updating the Display

### Widget Access

Use `self.query_one()` to get widget references:

```python
def update_display(self, data):
    # Get single widget by ID
    jobs_table = self.query_one("#jobs-table", DataTable)
    stats_label = self.query_one("#stats-label", Static)

    # Get widget by class
    from awx_tui.dashboards.sleek import TopPanel
    top_panel = self.query_one(TopPanel)

    # Get multiple widgets
    all_tables = self.query("DataTable")
    for table in all_tables:
        table.clear()
```

---

### Updating Tables

**DataTable Pattern:**

```python
def update_display(self, data):
    jobs_table = self.query_one("#jobs-table", DataTable)

    # Clear existing rows
    jobs_table.clear()

    # Add new rows
    for job in data['running_jobs']:
        jobs_table.add_row(
            str(job.get('id', 0)),
            job.get('name', 'Unknown'),
            job.get('status', 'unknown'),
            job.get('created', 'N/A')
        )

    # Preserve cursor position (optional)
    if jobs_table.row_count > 0:
        jobs_table.cursor_coordinate = (0, 0)
```

---

### Updating Static Text

```python
def update_display(self, data):
    stats_label = self.query_one("#stats-label", Static)

    running_count = len(data['running_jobs'])
    success_count = data['success_count']

    stats_text = f"""Running: {running_count}
Successful (7d): {success_count}
Failed (7d): {data['failed_count']}"""

    stats_label.update(stats_text)
```

---

### Building Progress Bars

Textual-compatible Unicode progress bars:

```python
def _build_capacity_bar(self, capacity_pct: int) -> str:
    """Build colored capacity bar with 10 blocks"""
    full_blocks = capacity_pct // 10
    remainder = capacity_pct % 10

    # Determine color
    if capacity_pct >= 60:
        color = "green"
    elif capacity_pct > 30:
        color = "yellow"
    else:
        color = "red"

    # Build bar with dithering
    bar = ""
    for i in range(10):
        if i < full_blocks:
            bar += "█"  # Full block
        elif i == full_blocks and remainder > 0:
            # Dithered blocks
            if remainder >= 7:
                bar += "▓"
            elif remainder >= 4:
                bar += "▒"
            else:
                bar += "░"
        else:
            bar += "░"  # Empty block

    return f"[{color}]{bar}[/{color}] {capacity_pct}%"

# Usage
def update_display(self, data):
    capacity_pct = 75
    bar = self._build_capacity_bar(capacity_pct)
    label = self.query_one("#capacity", Static)
    label.update(bar)
    # Displays: [green]███████▓░░[/green] 75%
```

---

### Formatting Timestamps

```python
from datetime import datetime

def update_display(self, data):
    for job in data['running_jobs']:
        started = job.get('started')
        if started:
            try:
                job_time = datetime.fromisoformat(started.replace('Z', '+00:00'))
                time_str = job_time.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, AttributeError):
                time_str = "N/A"
        else:
            time_str = "Not started"

        # Use time_str in table
```

---

## Accessing Additional Data Sources

The AWX TUI app exposes additional data sources beyond AWX API.

### Notification Log (The Loaf)

Access all application notifications:

```python
def update_display(self, data):
    # Get last 10 notifications
    notifications = self.app.notification_log[-10:] if self.app.notification_log else []

    # Build notification display
    lines = []
    for notif in reversed(notifications):  # Most recent first
        timestamp = notif['timestamp']  # datetime object
        severity = notif['severity']     # 'information', 'warning', 'error', 'success'
        message = notif['message']       # str
        source = notif['source']         # Screen class name

        time_str = timestamp.strftime('%H:%M:%S')
        lines.append(f"{time_str} [{severity}] {message}")

    loaf_widget = self.query_one("#mini-loaf", Static)
    loaf_widget.update("\n".join(lines))
```

**Notification Structure:**
```python
{
    'timestamp': datetime.now(),
    'severity': 'information',  # 'information', 'warning', 'error', 'success'
    'message': 'Job completed successfully',
    'title': '',  # Optional
    'source': 'ClassicDashboard',  # Screen class name
    'timeout': 2.0,
}
```

**Configuration:**
- Max entries: `self.app.app_config.preferences.get('loaf_max_entries', 1000)`
- Auto-capped when exceeded (keeps most recent)

---

### API Call Log (Debug Console)

Access all API calls made by the app:

```python
def update_display(self, data):
    # Get last 20 API calls
    api_calls = self.app.api_call_log[-20:] if self.app.api_call_log else []

    # Build API call display
    for call in reversed(api_calls):  # Most recent first
        timestamp = call['timestamp']           # str (HH:MM:SS)
        method = call['method']                 # 'GET', 'POST', etc.
        instance_name = call['instance_name']   # 'dev2'
        endpoint = call['endpoint']             # '/api/v2/jobs/'
        url = call['url']                       # Full URL
        status_code = call['status_code']       # 200, 404, etc.
        duration_ms = call['duration_ms']       # 234
        size_bytes = call['size_bytes']         # 1024

        # Optional fields (may be None)
        request_headers = call.get('request_headers', {})
        response_headers = call.get('response_headers', {})
        content_preview = call.get('content_preview', '')  # First 200 chars
        response_content_full = call.get('response_content_full', '')  # Full response
        query_params = call.get('query_params', {})

        # Display
        print(f"{timestamp} {method} {endpoint} -> {status_code} ({duration_ms}ms)")
```

**API Call Structure:**
```python
{
    'timestamp': '10:34:12',
    'method': 'GET',
    'instance': 'dev2',  # Deprecated, use instance_name
    'instance_name': 'dev2',
    'endpoint': '/api/v2/jobs/',
    'url': 'https://awx.dev2.example.com/api/v2/jobs/',
    'status_code': 200,
    'duration_ms': 234,
    'size_bytes': 1024,
    'request_headers': {...},
    'response_headers': {...},
    'content_preview': '{...}',  # Truncated
    'response_content_full': '{...}',  # Full JSON
    'query_params': {'status__in': 'running', 'page_size': '50'},
}
```

**Configuration:**
- Max entries: `self.app.app_config.preferences.get('debug_console_max_entries', 1000)`
- Auto-capped when exceeded (keeps most recent)

---

### Instance Manager

Access instance configuration and clients:

```python
def update_display(self, data):
    # Get current instance
    current_instance = self.app.instance_manager.current_instance  # 'dev2'

    # Get instance config
    config = self.app.app_config.instances.get(current_instance)
    instance_url = config.url if config else 'Unknown'
    instance_status = config.last_status if config else 'unknown'

    # Get all instance names
    all_instances = self.app.instance_manager.get_instance_names()
    # Returns: ['dev2', 'dev1', 'staging', '@env-vars']

    # Get client for specific instance
    client = self.app.instance_manager.get_client('dev1')
```

---

### Application Title

Access rotating app name:

```python
def update_display(self, data):
    app_name = self.app.current_app_name
    # Returns: 'AWX TUI', 'Rage Tater Automation Interface', etc.

    # Use in display
    title_widget = self.query_one("#title", Static)
    title_widget.update(f"{app_name} - Dashboard")
```

---

## CSS Styling

### Inline CSS

For simple dashboards, use inline CSS:

```python
@register_dashboard('simple')
class SimpleDashboard(BaseDashboard):
    CSS = """
    Screen {
        background: $surface;
        layout: vertical;
    }

    #my-panel {
        height: 1fr;
        border: solid $primary;
        padding: 1 2;
    }

    DataTable {
        height: auto;
    }
    """
```

---

### External CSS File

For complex layouts, use external CSS:

```python
@register_dashboard('complex')
class ComplexDashboard(BaseDashboard):
    CSS_PATH = "complex.tcss"
```

Then create `awx_tui/dashboards/complex.tcss`:

```css
/* Complex Dashboard Styles */

Screen {
    background: $surface;
}

/* Layout containers */
#dashboard-container {
    width: 100%;
    height: 100%;
}

#main-layout {
    width: 100%;
    height: 100%;
    layout: horizontal;
}

#content-column {
    width: 82%;
    height: 100%;
}

#sidebar-column {
    width: 18%;
    height: 100%;
}

/* Panels */
#instances-panel {
    height: 1fr;
    border: solid $primary;
    padding: 0 1;
    border-title-align: left;
}

/* Tables */
DataTable {
    height: auto;
}

/* Custom widgets */
.my-custom-class {
    color: $accent;
    text-style: bold;
}
```

---

### **CRITICAL: CSS Namespacing to Prevent Conflicts**

**When creating a new dashboard, you MUST scope all CSS rules under a unique dashboard-specific class to prevent style conflicts when users switch between dashboards.**

**Problem:**
Textual doesn't fully clear CSS when switching screens. If multiple dashboards use the same widget IDs (e.g., `#instances-panel`, `#jobs-table`) with different CSS rules, switching between dashboards causes style conflicts that can hide widgets or break layouts.

**Solution:**
Add a unique container class and scope all CSS rules under it.

**Step 1: Add Container Class in Python**

```python
def compose(self) -> ComposeResult:
    yield Header()
    yield TopPanel()
    with Container(id="dashboard-container", classes="myboard-dashboard"):  # <-- Unique class
        # Your layout here
        yield DataTable(id="jobs-table")
    yield Footer()
```

**Step 2: Scope ALL CSS Rules Under That Class**

**❌ WRONG - Global rules will conflict:**
```css
#dashboard-container {
    width: 100%;
}

#jobs-table {
    height: 1fr;
}

.section-header {
    color: $text-muted;
}
```

**✅ CORRECT - Scoped under dashboard class:**
```css
.myboard-dashboard {
    width: 100%;
}

.myboard-dashboard #jobs-table {
    height: 1fr;
}

.myboard-dashboard .section-header {
    color: $text-muted;
}
```

**Real-World Example from Classic Dashboard:**

```python
# awx_tui/dashboards/classic.py
def compose(self) -> ComposeResult:
    yield Header()
    yield TopPanel()
    with Container(id="dashboard-container", classes="classic-dashboard"):
        with Horizontal(id="instances-row"):
            with Vertical(id="instances-panel"):
                yield DataTable(id="instances-table")
```

```css
/* awx_tui/dashboards/classic.tcss */

.classic-dashboard {
    width: 100%;
    height: 100%;
}

.classic-dashboard #instances-row {
    height: 10;
    border: solid $primary;
}

.classic-dashboard #instances-panel {
    width: 1fr;
    padding: 0 1;
}

.classic-dashboard #instances-table {
    height: 1fr;
}
```

**What to Scope:**
- ✅ **All ID selectors** (`#my-widget` → `.myboard-dashboard #my-widget`)
- ✅ **All class selectors** (`.my-class` → `.myboard-dashboard .my-class`)
- ✅ **Layout containers** (`#dashboard-container` → `.myboard-dashboard`)
- ⚠️  **Global element selectors** - Use sparingly, scope if specific to your dashboard
  - `Screen` - Usually safe (but consider scoping if you change background)
  - `DataTable`, `Static`, etc. - **MUST scope** if changing from defaults

**Exception - Global Element Selectors (use with caution):**
These can remain unscoped if they're truly generic and won't conflict:

```css
DataTable {
    height: auto;  /* Safe - common default across all dashboards */
}
```

But if your dashboard needs different DataTable styling than others, scope it:

```css
.myboard-dashboard DataTable {
    height: 1fr;  /* Specific to this dashboard */
    border: solid $accent;
}
```

**Testing:**
After creating your dashboard, **test switching between dashboards**:
1. Load Dashboard A (classic)
2. Navigate to Dashboard B (myboard)
3. Navigate back to Dashboard A
4. Verify ALL widgets still appear and look correct

If widgets disappear or styles break, you have a CSS namespacing issue.

---

### Textual CSS Variables

Use built-in Textual color variables:

```css
/* Theme colors */
$primary       /* Primary accent color */
$secondary     /* Secondary accent color */
$accent        /* Accent color */
$surface       /* Background surface */
$text          /* Default text color */
$text-muted    /* Muted text color */

/* Status colors */
$success       /* Green for success */
$warning       /* Yellow/orange for warnings */
$error         /* Red for errors */

/* Example usage */
#success-panel {
    border: solid $success;
    color: $success;
}

#error-panel {
    border: solid $error;
    color: $error;
}
```

---

### Layout Patterns

**Horizontal Split:**
```css
#container {
    layout: horizontal;
}

#left-panel {
    width: 60%;
}

#right-panel {
    width: 40%;
}
```

**Vertical Split:**
```css
#container {
    layout: vertical;
}

#top-panel {
    height: 10;  /* Fixed height */
}

#bottom-panel {
    height: 1fr;  /* Fill remaining space */
}
```

**Grid Layout:**
```css
#container {
    layout: grid;
    grid-size: 2 2;  /* 2 columns, 2 rows */
}
```

---

## Registration and Loading

### Registration Pattern

The `@register_dashboard()` decorator adds the dashboard to the global registry:

```python
from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard

@register_dashboard('myboard')
class MyDashboard(BaseDashboard):
    pass
```

**Behind the scenes:**
```python
# In awx_tui/dashboards/__init__.py
DASHBOARD_REGISTRY['myboard'] = MyDashboard
```

---

### Loading Pattern

When an instance is selected, the dashboard is loaded:

```python
# In awx_tui/screens/instance_selection.py
from awx_tui.dashboards import get_dashboard

instance_config = self.app.app_config.instances.get(instance_name)
dashboard_name = instance_config.dashboard if instance_config else 'classic'
dashboard_class = get_dashboard(dashboard_name, self.app.app_config)
self.app.push_screen(dashboard_class())
```

**`get_dashboard()` behavior:**
- If `dashboard_name` exists in registry: return that class
- If `dashboard_name` not found: log warning, return `'classic'`
- If `'classic'` not found: raise error (should never happen)

---

### Import Mechanism

For registration to work, the dashboard module **must be imported**:

```python
# awx_tui/dashboards/__init__.py

# Import dashboard implementations to trigger @register_dashboard decorators
try:
    from .classic import ClassicDashboard  # noqa: F401
except ImportError:
    pass  # Classic dashboard not yet created

try:
    from .sleek import SleekDashboard  # noqa: F401
except ImportError:
    pass  # Sleek dashboard not yet created

try:
    from .myboard import MyDashboard  # noqa: F401
except ImportError:
    pass  # MyDashboard not yet created
```

**Why `# noqa: F401`?**
- Tells linters to ignore "imported but unused" warnings
- We import to trigger the decorator, not to use the class directly

---

## Testing

### Manual Testing

**Test with Mock Mode:**
```bash
# Use your dashboard with mock data
awx-tui --mock --dashboard myboard
```

**Test with Real Instance:**
```yaml
# config.yaml
instances:
  test-awx:
    url: https://awx.test.example.com
    auth:
      method: token
      username: admin
      token: your-token
    dashboard: myboard  # <-- Test dashboard
```

```bash
awx-tui
# Select test-awx instance
```

**Test with Environment Variable:**
```bash
export AWX_DASHBOARD=myboard
export AWX_HOST=https://awx.test.example.com
export AWX_TOKEN=your-token
awx-tui
```

---

### Automated Testing

**Unit Test Pattern:**

```python
# tests/test_myboard.py
import pytest
from awx_tui.dashboards.myboard import MyDashboard
from awx_tui.dashboards import get_dashboard, DASHBOARD_REGISTRY


def test_dashboard_registered():
    """Test dashboard is in registry"""
    assert 'myboard' in DASHBOARD_REGISTRY
    assert DASHBOARD_REGISTRY['myboard'] == MyDashboard


def test_get_dashboard():
    """Test get_dashboard loader"""
    DashboardClass = get_dashboard('myboard')
    assert DashboardClass == MyDashboard


def test_get_dashboard_fallback():
    """Test fallback to classic for invalid name"""
    DashboardClass = get_dashboard('invalid-name')
    assert DashboardClass == DASHBOARD_REGISTRY['classic']
```

**Integration Test Pattern:**

```python
# tests/test_myboard_integration.py
import pytest
from textual.pilot import Pilot
from awx_tui.app import AWXTUIApp
from awx_tui.dashboards.myboard import MyDashboard


@pytest.mark.asyncio
async def test_myboard_renders():
    """Test dashboard renders without errors"""
    app = AWXTUIApp(mock_mode=True)

    async with app.run_test() as pilot:
        # Push dashboard screen
        app.push_screen(MyDashboard())

        # Wait for screen to load
        await pilot.pause()

        # Check screen is active
        assert isinstance(app.screen, MyDashboard)

        # Check widgets exist
        assert app.screen.query_one("#my-panel")
```

---

### Debugging Tips

**Enable Debug Logging:**
```bash
awx-tui --debug --dashboard myboard
```

**Check Dashboard Registration:**
```python
# In your dashboard file, add at bottom:
if __name__ == "__main__":
    from awx_tui.dashboards import DASHBOARD_REGISTRY
    print(f"Registered dashboards: {list(DASHBOARD_REGISTRY.keys())}")
    print(f"MyDashboard registered: {'myboard' in DASHBOARD_REGISTRY}")
```

**Textual DevTools:**
```bash
# Run with textual devtools for live CSS editing
textual run --dev awx_tui.main:main
```

**Print Debug Info:**
```python
def update_display(self, data):
    # Log to Textual debug console (Ctrl+D)
    self.app.log.info(f"Updating display with {len(data['running_jobs'])} jobs")

    # Or use notify for quick debug
    self.notify(f"Jobs: {len(data['running_jobs'])}", timeout=1)
```

---

## Best Practices

### 1. Separation of Concerns

**Do:**
- Fetch data in `fetch_data()` (API calls, calculations)
- Update UI in `update_display()` (widget updates only)

**Don't:**
- Make API calls in `update_display()`
- Update UI in `fetch_data()`

---

### 2. Parallel API Calls

**Do:**
```python
async def fetch_data(self, client):
    import asyncio
    results = await asyncio.gather(
        client.get('/api/v2/projects/'),
        client.get('/api/v2/inventories/'),
    )
    return {'projects': results[0], 'inventories': results[1]}
```

**Don't:**
```python
async def fetch_data(self, client):
    # Sequential - slow!
    projects = await client.get('/api/v2/projects/')
    inventories = await client.get('/api/v2/inventories/')
    return {'projects': projects, 'inventories': inventories}
```

---

### 3. Error Handling

**Do:**
```python
async def fetch_data(self, client):
    async def safe_get(endpoint, description):
        try:
            return await client.get(endpoint)
        except Exception as e:
            self.app.log.error(f"Failed to fetch {description}: {e}")
            return {}

    projects = await safe_get('/api/v2/projects/', "projects")
    return {'projects': projects.get('results', [])}
```

**Don't:**
```python
async def fetch_data(self, client):
    # Will crash dashboard on API error
    projects = await client.get('/api/v2/projects/')
    return {'projects': projects['results']}
```

---

### 4. Call Parent Methods

**Do:**
```python
async def on_mount(self):
    # Setup
    await super().on_mount()  # Triggers auto-refresh

def action_refresh(self):
    self.notify("Refreshing...")
    super().action_refresh()  # Triggers refresh
```

**Don't:**
```python
async def on_mount(self):
    # Setup
    # Forgot super().on_mount() - auto-refresh won't work!

def action_refresh(self):
    # Reimplementing refresh - don't do this!
    self.run_worker(self.load_data())
```

---

### 5. Preserve Cursor Position

**Do:**
```python
def update_display(self, data):
    table = self.query_one("#jobs-table", DataTable)

    # Save cursor
    cursor_row = 0
    if table.cursor_coordinate:
        cursor_row = table.cursor_coordinate[0]

    table.clear()
    # ... add rows ...

    # Restore cursor
    if table.row_count > 0:
        cursor_row = min(cursor_row, table.row_count - 1)
        table.cursor_coordinate = (cursor_row, 0)
```

**Don't:**
```python
def update_display(self, data):
    table = self.query_one("#jobs-table", DataTable)
    table.clear()
    # ... add rows ...
    # Cursor jumps to top every refresh - annoying!
```

---

### 6. Efficient Calculations

**Do:**
```python
async def fetch_data(self, client):
    jobs = await client.get('/api/v2/jobs/')

    # Calculate once in fetch
    success_count = sum(1 for j in jobs if j['status'] == 'successful')

    return {'jobs': jobs, 'success_count': success_count}

def update_display(self, data):
    # Use pre-calculated value
    label.update(f"Success: {data['success_count']}")
```

**Don't:**
```python
def update_display(self, data):
    # Recalculate every display update - inefficient!
    success_count = sum(1 for j in data['jobs'] if j['status'] == 'successful')
    label.update(f"Success: {success_count}")
```

---

### 7. Use Configuration

**Do:**
```python
async def on_mount(self):
    # Read from config
    refresh_interval = self.app.app_config.preferences.get(
        'dashboard_refresh_interval', 5
    )
    await super().on_mount()
```

**Don't:**
```python
async def on_mount(self):
    # Hardcoded - user can't customize
    refresh_interval = 5
```

---

### 8. Clean Widget IDs

**Do:**
```python
# CSS/compose
yield DataTable(id="jobs-table")
yield Static(id="stats-panel")

# Access
table = self.query_one("#jobs-table", DataTable)
```

**Don't:**
```python
# No IDs - hard to reference
yield DataTable()
yield Static()

# Fragile access
table = self.query("DataTable")[0]  # Breaks if order changes
```

---

## Examples

### Example 1: Minimal Dashboard

Shows only running jobs in a simple table.

```python
# awx_tui/dashboards/minimal.py
from textual.app import ComposeResult
from textual.widgets import DataTable, Header, Footer
from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard


@register_dashboard('minimal')
class MinimalDashboard(BaseDashboard):
    """Minimal dashboard - running jobs only"""

    CSS = """
    #jobs-table {
        height: 1fr;
        border: solid $primary;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "back_to_instances", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        table = DataTable(id="jobs-table", cursor_type="row")
        table.add_columns("ID", "Name", "Status", "Started")
        yield table
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Minimal Dashboard"
        await super().on_mount()

    async def fetch_data(self, client):
        running_jobs = await self.fetch_running_jobs(client)
        return {'running_jobs': running_jobs}

    def update_display(self, data):
        table = self.query_one("#jobs-table", DataTable)
        table.clear()

        for job in data['running_jobs']:
            table.add_row(
                str(job.get('id', 0)),
                job.get('name', 'Unknown'),
                job.get('status', 'unknown'),
                job.get('started', 'N/A')
            )
```

---

### Example 2: Metrics Dashboard

Shows high-level metrics and charts.

```python
# awx_tui/dashboards/metrics.py
from datetime import datetime, timedelta
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Header, Footer
from textual.containers import Horizontal, Vertical
from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard


@register_dashboard('metrics')
class MetricsDashboard(BaseDashboard):
    """Metrics dashboard with stats and graphs"""

    CSS_PATH = "metrics.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            # Left: Stats
            with Vertical(id="stats-column"):
                yield Static("Loading...", id="stats-panel")

            # Right: Graph
            with Vertical(id="graph-column"):
                table = DataTable(id="graph-table", show_cursor=False)
                table.add_columns("Date", "Success", "Failed")
                yield table
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Metrics Dashboard"
        await super().on_mount()

    async def fetch_data(self, client):
        import asyncio

        # Fetch jobs from last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        results = await asyncio.gather(
            self.fetch_running_jobs(client),
            client.get('/api/v2/unified_jobs/', params={
                'finished__gte': seven_days_ago,
                'page_size': 500
            }),
        )

        running_jobs = results[0]
        all_jobs_resp = results[1]
        all_jobs = all_jobs_resp.get('results', [])

        # Calculate metrics
        success_count = sum(1 for j in all_jobs if j.get('status') == 'successful')
        failed_count = sum(1 for j in all_jobs if j.get('status') == 'failed')

        # Group by day
        jobs_by_day = {}
        for job in all_jobs:
            finished = job.get('finished', '')
            if finished:
                day = finished.split('T')[0]
                status = job.get('status')
                if day not in jobs_by_day:
                    jobs_by_day[day] = {'success': 0, 'failed': 0}
                if status == 'successful':
                    jobs_by_day[day]['success'] += 1
                elif status == 'failed':
                    jobs_by_day[day]['failed'] += 1

        return {
            'running_count': len(running_jobs),
            'success_count': success_count,
            'failed_count': failed_count,
            'jobs_by_day': jobs_by_day,
        }

    def update_display(self, data):
        # Update stats
        stats = f"""Running Jobs: {data['running_count']}
Successful (7d): {data['success_count']}
Failed (7d): {data['failed_count']}"""

        stats_panel = self.query_one("#stats-panel", Static)
        stats_panel.update(stats)

        # Update graph
        graph_table = self.query_one("#graph-table", DataTable)
        graph_table.clear()

        for day in sorted(data['jobs_by_day'].keys(), reverse=True):
            counts = data['jobs_by_day'][day]
            graph_table.add_row(
                day,
                str(counts['success']),
                str(counts['failed'])
            )
```

---

### Example 3: Split Dashboard

Classic split layout with instances on left, jobs on right.

```python
# awx_tui/dashboards/split.py
from textual.app import ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Horizontal, Vertical
from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard


@register_dashboard('split')
class SplitDashboard(BaseDashboard):
    """Split dashboard - instances left, jobs right"""

    CSS = """
    #main-layout {
        layout: horizontal;
    }

    #left-panel {
        width: 50%;
        border: solid $primary;
    }

    #right-panel {
        width: 50%;
        border: solid $secondary;
    }

    DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            # Left: Instances
            with Vertical(id="left-panel"):
                instances_table = DataTable(id="instances-table", show_cursor=False)
                instances_table.add_columns("Host", "Capacity", "Jobs")
                yield instances_table

            # Right: Jobs
            with Vertical(id="right-panel"):
                jobs_table = DataTable(id="jobs-table", cursor_type="row")
                jobs_table.add_columns("ID", "Name", "Status")
                yield jobs_table
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Split Dashboard"
        await super().on_mount()

    async def fetch_data(self, client):
        import asyncio

        results = await asyncio.gather(
            self.fetch_instances(client),
            self.fetch_running_jobs(client),
        )

        return {
            'instances': results[0],
            'running_jobs': results[1],
        }

    def update_display(self, data):
        # Update instances table
        instances_table = self.query_one("#instances-table", DataTable)
        instances_table.clear()

        for inst in data['instances']:
            instances_table.add_row(
                inst.get('hostname', 'unknown'),
                f"{inst.get('capacity', 0)}",
                f"{inst.get('jobs_running', 0)}"
            )

        # Update jobs table
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.clear()

        for job in data['running_jobs']:
            jobs_table.add_row(
                str(job.get('id', 0)),
                job.get('name', 'Unknown'),
                job.get('status', 'unknown')
            )
```

---

## FAQ

**Q: Can I use custom widgets in my dashboard?**

A: Yes! Define custom widget classes and compose them:

```python
class MyCustomWidget(Static):
    def on_mount(self):
        self.update("Custom widget content")

class MyDashboard(BaseDashboard):
    def compose(self):
        yield MyCustomWidget(id="custom")
```

---

**Q: How do I add custom keyboard shortcuts?**

A: Override `BINDINGS`:

```python
class MyDashboard(BaseDashboard):
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("x", "my_custom_action", "Custom"),
    ]

    def action_my_custom_action(self):
        self.notify("Custom action triggered!")
```

---

**Q: Can I disable auto-refresh?**

A: Yes, check config or override lifecycle methods:

```python
async def on_mount(self):
    # Check config
    auto_refresh = self.app.app_config.preferences.get('dashboard_auto_refresh', True)
    if not auto_refresh:
        return  # Don't call super().on_mount()

    await super().on_mount()
```

---

**Q: How do I show a loading indicator?**

A: Update UI before calling `super().on_mount()`:

```python
async def on_mount(self):
    # Show loading state
    panel = self.query_one("#main-panel", Static)
    panel.update("Loading dashboard...")

    # Trigger refresh (will call update_display)
    await super().on_mount()
```

---

**Q: Can I make API calls to non-AWX endpoints?**

A: Yes, use any HTTP library (but you'll need to handle auth):

```python
async def fetch_data(self, client):
    import aiohttp

    # AWX data
    jobs = await self.fetch_running_jobs(client)

    # External API
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/metrics') as resp:
            external_data = await resp.json()

    return {
        'jobs': jobs,
        'external': external_data
    }
```

---

**Q: How do I persist dashboard-specific state?**

A: Use instance variables:

```python
class MyDashboard(BaseDashboard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._user_preferences = {
            'sort_order': 'desc',
            'filter': 'all'
        }

    def update_display(self, data):
        # Use self._user_preferences
        sort_order = self._user_preferences['sort_order']
```

---

**Q: Can I access modal results in my dashboard?**

A: Yes, use `push_screen()` with callback:

```python
def action_open_modal(self):
    from awx_tui.modals.job_detail import JobDetailModal

    def handle_result(result):
        self.notify(f"Modal returned: {result}")

    self.app.push_screen(JobDetailModal(job_id=123), callback=handle_result)
```

---

## Conclusion

The dashboard plugin system provides a flexible framework for creating custom AWX TUI layouts. Key points:

- **Inherit from `BaseDashboard`** for auto-refresh and lifecycle management
- **Implement `fetch_data()` and `update_display()`** as the core contract
- **Use `@register_dashboard()`** decorator and import in `__init__.py`
- **Follow best practices** for performance and maintainability
- **Access additional data** (notifications, API logs) for rich displays

For questions or contributions, see the main AWX TUI repository.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-02
**Maintainers:** Ansible Community
