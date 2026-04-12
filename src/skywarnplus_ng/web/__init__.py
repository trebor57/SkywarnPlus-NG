"""
Web dashboard for SkywarnPlus-NG.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server import WebDashboard, WebDashboardError

__all__ = [
    "WebDashboard",
    "WebDashboardError",
]


def __getattr__(name: str):
    if name == "WebDashboard":
        from .server import WebDashboard

        return WebDashboard
    if name == "WebDashboardError":
        from .server import WebDashboardError

        return WebDashboardError
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
