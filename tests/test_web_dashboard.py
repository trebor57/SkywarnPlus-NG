"""Regression tests for WebDashboard composition and route wiring."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROUTES_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "skywarnplus_ng" / "web" / "routes.py"
)


def _dashboard_handler_names_from_routes() -> set[str]:
    tree = ast.parse(ROUTES_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "dashboard":
                names.add(node.attr)
    return names


def test_routes_reference_dashboard_handlers():
    names = _dashboard_handler_names_from_routes()
    assert "websocket_handler" in names
    assert "api_status_handler" in names
    assert len(names) >= 40


def test_web_dashboard_exposes_all_routed_handlers():
    pytest.importorskip("aiohttp")
    from skywarnplus_ng.web.server import WebDashboard

    required = _dashboard_handler_names_from_routes()
    missing = sorted(name for name in required if not hasattr(WebDashboard, name))
    assert not missing, f"WebDashboard missing handlers: {missing}"
    for name in required:
        assert callable(getattr(WebDashboard, name)), name


def test_web_dashboard_mro_includes_mixins():
    pytest.importorskip("aiohttp")
    from skywarnplus_ng.web.handlers import (
        AlertsApiMixin,
        AuthHandlersMixin,
        ConfigApiMixin,
        DatabaseApiMixin,
        HealthLogsApiMixin,
        NotificationsApiMixin,
        PageHandlersMixin,
        StatusApiMixin,
        UpdatesMetricsApiMixin,
        WebsocketHandlersMixin,
    )
    from skywarnplus_ng.web.server import WebDashboard

    mro_names = {c.__name__ for c in WebDashboard.__mro__}
    for mixin in (
        WebsocketHandlersMixin,
        AuthHandlersMixin,
        NotificationsApiMixin,
        ConfigApiMixin,
        DatabaseApiMixin,
        UpdatesMetricsApiMixin,
        HealthLogsApiMixin,
        AlertsApiMixin,
        StatusApiMixin,
        PageHandlersMixin,
    ):
        assert mixin.__name__ in mro_names
