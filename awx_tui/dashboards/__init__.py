"""
Dashboard Registry - Pluggable dashboard system

Dashboards are registered here and loaded based on user configuration.
"""

from typing import Type

from .base import BaseDashboard

# Dashboard registry - maps dashboard names to their classes
DASHBOARD_REGISTRY: dict[str, Type[BaseDashboard]] = {}


def register_dashboard(name: str):
    """
    Decorator to register a dashboard class.

    Usage:
        @register_dashboard('classic')
        class ClassicDashboard(BaseDashboard):
            ...
    """

    def decorator(cls: Type[BaseDashboard]):
        if not issubclass(cls, BaseDashboard):
            raise TypeError(f"{cls.__name__} must inherit from BaseDashboard")
        DASHBOARD_REGISTRY[name] = cls
        return cls

    return decorator


def get_dashboard(name: str, app_config=None) -> Type[BaseDashboard]:
    """
    Get dashboard class by name, with fallback to 'classic'.

    Args:
        name: Dashboard name from config
        app_config: Optional app config for logging warnings

    Returns:
        Dashboard class (subclass of BaseDashboard)
    """
    if name not in DASHBOARD_REGISTRY:
        # Log warning if app_config provided
        if app_config and hasattr(app_config, "log"):
            app_config.log.warning(
                f"Unknown dashboard '{name}', falling back to 'classic'. "
                f"Available: {', '.join(DASHBOARD_REGISTRY.keys())}"
            )
        # Fallback to classic
        name = "classic"

    return DASHBOARD_REGISTRY[name]


def list_dashboards() -> list[str]:
    """Return list of registered dashboard names"""
    return list(DASHBOARD_REGISTRY.keys())


# Import dashboard implementations to trigger @register_dashboard decorators
# This ensures all dashboards are registered when this module is imported
try:
    from .classic import ClassicDashboard  # noqa: F401
except ImportError:
    pass  # Classic dashboard not yet created

try:
    from .sleek import SleekDashboard  # noqa: F401
except ImportError:
    pass  # Sleek dashboard not yet created


__all__ = [
    "BaseDashboard",
    "DASHBOARD_REGISTRY",
    "register_dashboard",
    "get_dashboard",
    "list_dashboards",
]
