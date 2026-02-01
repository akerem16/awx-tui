"""
AWX TUI - Sleek Dashboard Jobs Panel

Displays combined running and recent jobs in a DataTable.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from textual.widgets import DataTable

from awx_tui.dashboards.sleek.widgets import BorderPanel
from awx_tui.utils import format_playbook_path

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class JobsPanel:
    """
    Manages the JOBS panel showing running and recent jobs.

    Displays jobs with:
    - ID, Type emoji, Status emoji
    - Name, User, Project, Playbook, Template
    - Inventory, EE (Execution Environment), Time/Status
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard

    def setup_table(self) -> None:
        """Configure DataTable columns for jobs."""
        try:
            table = self.dashboard.query_one("#jobs-table", DataTable)
            table.add_columns(
                "ID", "", "", "Name", "User", "Project", "Playbook", "Template", "Inventory", "EE", "Time/Status"
            )
            table.focus()
        except Exception:
            pass

    def update(self, running_jobs: list, recent_jobs: list) -> None:
        """Update combined JOBS table with running jobs first, then recent jobs."""
        # Store both for job type lookup
        self.dashboard._running_jobs_data = running_jobs
        self.dashboard._recent_jobs_data = recent_jobs

        # Update BorderPanel title with counts
        running_count = len(running_jobs)
        recent_count = len(recent_jobs)
        total_count = running_count + recent_count

        if running_count > 0:
            title = f"JOBS ({total_count} total - {running_count} running, {recent_count} recent)"
        else:
            title = f"JOBS ({total_count})"

        jobs_panel = self.dashboard.query_one("#jobs-panel", BorderPanel)
        jobs_panel.update_title(title)

        table = self.dashboard.query_one("#jobs-table", DataTable)

        # Save current job ID to restore position
        selected_job_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_job_id = table.get_row_at(cursor_row)[0]
            except Exception:
                pass

        table.clear()

        new_cursor_row = 0
        row_idx = 0

        # Add running jobs first
        for job in running_jobs:
            row_data = self._format_job_row(job, is_running=True)
            jid = row_data[0]

            if selected_job_id and jid == selected_job_id:
                new_cursor_row = row_idx

            table.add_row(*row_data)
            row_idx += 1

        # Add recent jobs
        for job in recent_jobs:
            row_data = self._format_job_row(job, is_running=False)
            jid = row_data[0]

            if selected_job_id and jid == selected_job_id:
                new_cursor_row = row_idx

            table.add_row(*row_data)
            row_idx += 1

        # Restore cursor position
        if table.row_count > 0:
            found_same_job = False
            if selected_job_id:
                try:
                    if table.get_row_at(new_cursor_row)[0] == selected_job_id:
                        found_same_job = True
                except Exception:
                    pass

            if found_same_job:
                table.cursor_coordinate = (new_cursor_row, 0)
            else:
                table.cursor_coordinate = (min(cursor_row, table.row_count - 1), 0)

    def _format_job_row(self, job: dict, is_running: bool) -> tuple:
        """Format a job into a table row tuple."""
        jid = str(job.get("id", 0))
        name = job.get("name", "Unknown")[:25]
        user = job.get("summary_fields", {}).get("created_by", {}).get("username", "N/A")[:16]
        summary = job.get("summary_fields", {})
        status = job.get("status", "unknown")[:10]

        # Job type emoji
        job_type = job.get("type", "job")
        type_emoji = {
            "job": "🚀",
            "project_update": "🔄",
            "inventory_update": "📥",
            "workflow_job": "🔗",
            "system_job": "🔧",
            "ad_hoc_command": "⚡",
        }.get(job_type, "❓")

        # Status emoji
        status_emoji = {
            "successful": "[#008000]✓[/#008000]",
            "failed": "[red]✗[/red]",
            "running": "🏃",
            "pending": "⏳",
            "waiting": "⏳",
            "canceled": "⚠",
            "error": "❗",
        }.get(status, "❓")

        # Get type-specific fields
        project, playbook, template, inventory, exec_env = self._get_job_fields(job, job_type, summary)

        # Format timestamp
        if is_running:
            time_status_str = self._format_started_time(job.get("started"))
        else:
            time_status_str = self._format_finished_time(job.get("finished"))

        return (
            jid,
            type_emoji,
            status_emoji,
            name,
            user,
            project,
            playbook,
            template,
            inventory,
            exec_env,
            time_status_str,
        )

    def _get_job_fields(self, job: dict, job_type: str, summary: dict) -> tuple:
        """Extract job fields based on job type."""
        if job_type == "project_update":
            project_data = summary.get("project", {})
            project = project_data.get("name", "N/A")[:16]
            playbook = "GIT Sync"
            template = project
            scm_url = job.get("scm_url", "")
            if scm_url:
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(scm_url)
                    inventory = parsed.netloc[:16] if parsed.netloc else "N/A"
                except Exception:
                    inventory = "N/A"
            else:
                inventory = "N/A"
            exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:16]

        elif job_type == "inventory_update":
            source = job.get("source", "N/A")
            project = source[:16]
            playbook = "(inventory sync)"[:16]
            inventory_data = summary.get("inventory", {})
            inventory = inventory_data.get("name", "N/A")[:16]
            inv_source = summary.get("inventory_source", {})
            template = inv_source.get("name", "N/A")[:16]
            exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:16]

        elif job_type == "workflow_job":
            project = "N/A"
            playbook = "(workflow)"
            workflow_template = summary.get("workflow_job_template", {})
            template = workflow_template.get("name", "N/A")[:16]
            inventory = "N/A"
            exec_env = "N/A"

        elif job_type == "system_job":
            project = "system"
            system_job_type = job.get("job_type", "N/A")
            playbook = system_job_type[:16]
            system_template = summary.get("system_job_template", {})
            template = system_template.get("name", "N/A")[:16]
            inventory = "AWX"
            exec_env = "N/A"

        elif job_type == "ad_hoc_command":
            project = "N/A"
            module_name = job.get("module_name", "N/A")
            playbook = module_name[:16]
            template = "N/A"
            inventory = summary.get("inventory", {}).get("name", "N/A")[:16]
            exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:16]

        else:
            # Regular job
            project = summary.get("project", {}).get("name", "N/A")[:16]
            playbook_raw = job.get("playbook", "N/A")
            playbook = format_playbook_path(playbook_raw, max_length=16)
            template = summary.get("job_template", {}).get("name", "N/A")[:16]
            inventory = summary.get("inventory", {}).get("name", "N/A")[:16]
            exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:16]

        return (project, playbook, template, inventory, exec_env)

    def _format_started_time(self, started: str) -> str:
        """Format started timestamp for running jobs."""
        if not started:
            return "N/A"
        try:
            job_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
            return job_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return "N/A"

    def _format_finished_time(self, finished: str) -> str:
        """Format finished timestamp for recent jobs."""
        if not finished:
            return "?"
        try:
            job_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
            return job_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return "?"
