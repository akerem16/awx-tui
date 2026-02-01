"""
AWX TUI - Utility Functions

Shared utility functions used across the application.
"""

from datetime import datetime


def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as time elapsed with two-level granularity

    Args:
        timestamp_str: ISO 8601 timestamp string (e.g., '2025-11-26T12:34:56Z')

    Returns:
        Formatted time string with two levels of precision:
        - Days + hours: "2d 5h"
        - Hours + minutes: "11h 5m"
        - Minutes + seconds: "15m 13s"
        - Just seconds: "45s"
        - Just now: "< 1s"
        - Invalid: "N/A"

    Examples:
        >>> format_time_ago('2025-11-25T00:00:00Z')  # 1 day, 5 hours ago
        '1d 5h'

        >>> format_time_ago('2025-11-26T01:30:00Z')  # 11 hours, 15 mins ago
        '11h 15m'
    """
    if not timestamp_str:
        return "N/A"

    try:
        finished_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(finished_time.tzinfo)
        delta = now - finished_time

        total_seconds = int(delta.total_seconds())

        if delta.days > 0:
            # Days + hours (e.g., "2d 5h")
            hours = delta.seconds // 3600
            return f"{delta.days}d {hours}h"
        elif total_seconds >= 3600:
            # Hours + minutes (e.g., "11h 5m")
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        elif total_seconds >= 60:
            # Minutes + seconds (e.g., "15m 13s")
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        elif total_seconds > 0:
            # Just seconds (e.g., "45s")
            return f"{total_seconds}s"
        else:
            # Just now
            return "< 1s"
    except (ValueError, AttributeError):
        return "N/A"


def format_playbook_path(playbook_path: str, max_length: int) -> str:
    """Format playbook path to fit in max_length, showing complete folder names from right to left

    Args:
        playbook_path: Full playbook path (e.g., '/path/to/playbooks/deploy.yml')
        max_length: Maximum characters to display

    Returns:
        Formatted path with complete folder names (e.g., 'to/playbooks/deploy')

    Examples:
        >>> format_playbook_path('/very/long/path/to/playbooks/deploy.yml', 20)
        'playbooks/deploy'

        >>> format_playbook_path('/short/path.yml', 50)
        'short/path'
    """
    if playbook_path == "N/A" or not playbook_path:
        return "N/A"

    # Strip extensions
    path = playbook_path.replace(".yml", "").replace(".yaml", "")

    # Remove leading slash
    if path.startswith("/"):
        path = path[1:]

    # If it fits, return as-is
    if len(path) <= max_length:
        return path

    # Split into parts and build from right to left
    parts = path.split("/")
    result_parts = []
    current_length = 0

    for part in reversed(parts):
        # Calculate length with separator (except for first part)
        part_length = len(part) + (1 if result_parts else 0)

        if current_length + part_length <= max_length:
            result_parts.insert(0, part)
            current_length += part_length
        else:
            break

    return "/".join(result_parts) if result_parts else path[-max_length:]
