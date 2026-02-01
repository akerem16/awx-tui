"""
AWX TUI - Sleek Dashboard Panel Modules

Each panel module handles a specific section of the dashboard.
Panels are UI-only - they receive data and update widgets, no API calls.
"""

from .groups import GroupsPanel
from .health import HealthPanel
from .instances import InstancesPanel
from .job_status import JobStatusPanel
from .jobs import JobsPanel
from .loaflet import LoafletPanel
from .stats import StatsPanel

__all__ = [
    "HealthPanel",
    "JobStatusPanel",
    "InstancesPanel",
    "GroupsPanel",
    "JobsPanel",
    "StatsPanel",
    "LoafletPanel",
]
