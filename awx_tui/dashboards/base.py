"""
Base Dashboard - Abstract base class for all dashboards

All dashboard implementations must inherit from BaseDashboard and implement
the required abstract methods.
"""

from datetime import datetime

from textual.screen import Screen


class BaseDashboard(Screen):
    """
    Abstract base class for all dashboards.

    Provides:
    - Auto-refresh orchestration
    - Refresh locking (prevent concurrent refreshes)
    - Client access via instance manager
    - Common helper methods for fetching data
    - Lifecycle management (suspend/resume)

    Subclasses must implement:
    - fetch_data(client) - Fetch all data the dashboard needs
    - update_display(data) - Update UI with fetched data
    - compose() - Define dashboard layout
    """

    # Must be set by subclass
    CSS_PATH = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refreshing = False
        self._refresh_start_time = None
        self._refresh_timer = None
        self._screen_active = True  # Track whether screen should be refreshing

    async def on_mount(self) -> None:
        """
        Initialize dashboard and start auto-refresh.

        Subclasses can override to add custom initialization,
        but should call super().on_mount() to enable auto-refresh.
        """
        # Trigger initial data load
        self.set_timer(0.1, lambda: self.run_worker(self._refresh()))

        # Start auto-refresh timer
        refresh_interval = self.app.app_config.preferences.get("dashboard_refresh_interval", 5)
        if refresh_interval > 0:
            self._refresh_timer = self.set_interval(refresh_interval, self._auto_refresh_callback)

    def _auto_refresh_callback(self):
        """Timer callback to trigger background refresh"""
        # Only refresh if this screen is active and visible
        if self._screen_active and self.app.screen is self:
            self.run_worker(self._refresh())

    async def _refresh(self) -> None:
        """
        Orchestrate dashboard refresh (base class implementation).

        Handles:
        - Refresh locking (prevent concurrent refreshes)
        - Timeout detection (reset stuck refreshes)
        - Client access
        - Error handling
        - Calling subclass fetch_data() and update_display()
        """
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
            client = self.app.instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            # Fetch data from subclass
            if isinstance(client, AWXClient):
                async with client:
                    data = await self.fetch_data(client)
            else:
                data = await self.fetch_data(client)

            # Update display from subclass
            self.update_display(data)

        except Exception as e:
            import traceback

            self.app.log.error(f"Dashboard refresh error: {e}\n{traceback.format_exc()}")
            self.app.notify(f"Error refreshing dashboard: {e}", severity="error")
        finally:
            self._refreshing = False
            self._refresh_start_time = None

    async def fetch_data(self, client):
        """
        Fetch all data this dashboard needs.

        Args:
            client: AWX API client

        Returns:
            dict: Data needed by this dashboard (structure defined by subclass)

        This method MUST be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement fetch_data()")

    def update_display(self, data):
        """
        Update dashboard UI with fetched data.

        Args:
            data: Data returned from fetch_data()

        This method MUST be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement update_display()")

    # ========================================================================
    # Helper methods - Optional, subclasses can use these
    # ========================================================================

    async def fetch_running_jobs(self, client, page_size=200):
        """
        Helper: Fetch currently running jobs.

        Args:
            client: AWX API client
            page_size: Number of results to fetch

        Returns:
            dict: API response with running jobs
        """
        return await client.get(
            "/api/v2/unified_jobs/", {"status__in": "pending,waiting,running", "page_size": page_size}
        )

    async def fetch_recent_jobs(self, client, page_size=25):
        """
        Helper: Fetch recently completed jobs.

        Args:
            client: AWX API client
            page_size: Number of results to fetch

        Returns:
            dict: API response with recent jobs
        """
        return await client.get(
            "/api/v2/unified_jobs/",
            {"status__in": "successful,failed,error,canceled", "page_size": page_size, "order_by": "-finished"},
        )

    async def fetch_instances(self, client):
        """
        Helper: Fetch AWX instances.

        Args:
            client: AWX API client

        Returns:
            dict: API response with instances
        """
        return await client.get("/api/v2/instances/")

    async def fetch_instance_groups(self, client):
        """
        Helper: Fetch AWX instance groups.

        Args:
            client: AWX API client

        Returns:
            dict: API response with instance groups
        """
        return await client.get("/api/v2/instance_groups/")

    async def fetch_ping(self, client):
        """
        Helper: Fetch AWX ping data (version, license, etc).

        Args:
            client: AWX API client

        Returns:
            dict: API response with ping data
        """
        return await client.get("/api/v2/ping/")

    # ========================================================================
    # Lifecycle methods
    # ========================================================================

    def on_screen_suspend(self) -> None:
        """Stop auto-refresh when screen is suspended (navigated away)"""
        self._screen_active = False
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None

    def on_screen_resume(self) -> None:
        """Resume auto-refresh when screen is resumed"""
        self._screen_active = True
        refresh_interval = self.app.app_config.preferences.get("dashboard_refresh_interval", 5)
        if refresh_interval > 0:
            self._refresh_timer = self.set_interval(refresh_interval, self._auto_refresh_callback)
        # Trigger immediate refresh on resume
        self.run_worker(self._refresh())

    # ========================================================================
    # Common action handlers - Subclasses can override
    # ========================================================================

    def action_refresh(self) -> None:
        """Manual refresh trigger (usually bound to 'r' or 'f5')"""
        self.run_worker(self._refresh())

    def action_back_to_instances(self) -> None:
        """Return to instance selection screen"""
        self.app.pop_screen()
