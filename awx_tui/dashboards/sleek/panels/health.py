"""
AWX TUI - Sleek Dashboard Health Panel

Displays system health status, performance metrics, and recent failures.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class HealthPanel:
    """
    Manages the HEALTH panel showing system health and performance.

    Three sections:
    - SYSTEM STATUS: Capacity bar, DB, Dispatcher, Receptor status
    - PERFORMANCE (24H): Jobs/min, Tasks/sec, Avg/Longest run times
    - RECENT JOB FAILURES (24H): List of recent failed jobs
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard

    def update(
        self, ping: dict, running_jobs: list, recent_jobs: list, instances: list, task_events_24h: int = 0
    ) -> None:
        """Update HEALTH panel with system health and performance metrics."""
        # Calculate capacity from instances
        total_capacity = sum(inst.get("capacity", 0) for inst in instances)
        total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
        capacity_pct = int(((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0)

        # Build capacity bar (5 blocks like stats panel)
        capacity_bar = self.dashboard._build_capacity_bar(capacity_pct, num_blocks=5)
        capacity_display = f"{capacity_bar} {capacity_pct}%"

        # HEALTH section
        # Check database status (if instances exist and have heartbeats)
        db_status = "[green]✓[/green] OK" if instances and len(instances) > 0 else "[red]✗[/red] DOWN"

        # Check dispatcher status (check if any instances are in ready state)
        ready_instances = [i for i in instances if i.get("node_state") == "ready" or i.get("enabled", True)]
        dispatcher_status = "[green]✓[/green] OK" if ready_instances else "[red]✗[/red] DOWN"

        # Check receptor status (check if instances have receptor addresses/nodes configured)
        receptor_configured = any(i.get("listener_port") or i.get("node_type") for i in instances)
        receptor_status = "[green]✓[/green] OK" if receptor_configured else "[red]✗[/red] DOWN"

        # Calculate cluster age from earliest instance creation (currently unused)
        # cluster_age = self._calculate_cluster_age(instances)

        # PERFORMANCE section - filter to last 24 hours
        now = datetime.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Filter jobs to last 24 hours (recent_jobs is actually graph_jobs with 500 jobs from 7 days)
        jobs_24h = []
        for job in recent_jobs:
            finished = job.get("finished")
            if finished:
                try:
                    job_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                    if job_time.replace(tzinfo=None) > twenty_four_hours_ago:
                        jobs_24h.append(job)
                except Exception:
                    pass

        # Jobs per hour = total jobs in 24h / 24
        jobs_per_hour = len(jobs_24h) / 24.0 if jobs_24h else 0.0

        # Tasks per second = task events in 24h / (24 * 60 * 60)
        tasks_per_sec = task_events_24h / 86400.0 if task_events_24h > 0 else 0.0

        # Average job duration from jobs in last 24 hours
        avg_duration = self._calculate_avg_duration(jobs_24h)
        avg_run = self._format_duration(avg_duration)

        # Calculate longest job duration from jobs in last 24 hours
        max_duration = self._calculate_max_duration(jobs_24h)
        longest_run = self._format_duration(max_duration)

        # FAILURES section - recent failed jobs in last 24 hours
        failures_text = self._get_recent_failures(recent_jobs, now)

        # Build three separate sections (leading space for padding)
        system_status = f""" [bold]SYSTEM STATUS[/bold]
 Capacity: {capacity_display}
 DB:       {db_status}
 Dsptchr:  {dispatcher_status}
 Receptor: {receptor_status}"""

        capacity_metrics = f"""[bold]PERFORMANCE (24H)[/bold]
Jobs/hr:    {jobs_per_hour:.1f}
Tasks/sec:  {tasks_per_sec:.1f}
Avg Run:    {avg_run}
Lngst Run:  {longest_run}"""

        failures_section = f"""[bold]RECENT JOB FAILURES (24H)[/bold]
{failures_text}"""

        try:
            self.dashboard.query_one("#health-system-status", Static).update(system_status)
            self.dashboard.query_one("#health-capacity", Static).update(capacity_metrics)
            self.dashboard.query_one("#health-failures", Static).update(failures_section)
        except Exception:
            pass  # Widget not ready yet

    def _calculate_cluster_age(self, instances: list) -> str:
        """Calculate cluster age from earliest instance creation."""
        if not instances:
            return "Unknown"

        # Try to find the oldest instance creation time
        oldest_time = None
        for inst in instances:
            created = inst.get("created")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if oldest_time is None or created_dt < oldest_time:
                        oldest_time = created_dt
                except Exception:
                    pass

        if not oldest_time:
            return "N/A"

        # Calculate age from oldest instance
        now = datetime.now()
        age_delta = now - oldest_time.replace(tzinfo=None)
        days = age_delta.days
        hours = age_delta.seconds // 3600

        if days >= 365:
            years = days // 365
            remaining_days = days % 365
            if remaining_days > 0:
                return f"{years}y {remaining_days}d"
            return f"{years}y"
        elif days >= 30:
            months = days // 30
            remaining_days = days % 30
            if remaining_days > 0:
                return f"{months}mo {remaining_days}d"
            return f"{months}mo"
        elif days > 0:
            return f"{days}d"
        else:
            return f"{hours}h"

    def _calculate_avg_duration(self, jobs: list) -> float:
        """Calculate average job duration from completed jobs."""
        total_duration = 0
        duration_count = 0
        for job in jobs:
            started = job.get("started")
            finished = job.get("finished")
            if started and finished:
                try:
                    start_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    finish_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                    duration = (finish_time - start_time).total_seconds()
                    total_duration += duration
                    duration_count += 1
                except Exception:
                    pass

        return total_duration / duration_count if duration_count > 0 else 0

    def _calculate_max_duration(self, jobs: list) -> float:
        """Calculate longest job duration from completed jobs."""
        max_duration = 0
        for job in jobs:
            started = job.get("started")
            finished = job.get("finished")
            if started and finished:
                try:
                    start_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    finish_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                    duration = (finish_time - start_time).total_seconds()
                    if duration > max_duration:
                        max_duration = duration
                except Exception:
                    pass

        return max_duration

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable string."""
        if seconds >= 60:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        return f"{int(seconds)}s"

    def _get_recent_failures(self, recent_jobs: list, now: datetime) -> str:
        """Get recent failed jobs in last 24 hours."""
        twenty_four_hours_ago = now - timedelta(hours=24)
        recent_failures = []

        for job in recent_jobs:
            if job.get("status") == "failed":
                finished = job.get("finished")
                if finished:
                    try:
                        job_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                        if job_time.replace(tzinfo=None) > twenty_four_hours_ago:
                            job_id = job.get("id", "?")
                            job_name = job.get("name", "Unknown")[:35]  # Truncate to fit panel width
                            recent_failures.append((job_id, job_name))
                    except Exception:
                        pass

        # Build failures list (show up to 5 most recent)
        failures_lines = []
        for job_id, job_name in recent_failures[:5]:
            failures_lines.append(f"[red]✗[/red] #{job_id} {job_name}")

        # If no failures, show success message
        if not failures_lines:
            return "[green]✓[/green] No failures"
        return "\n".join(failures_lines)
