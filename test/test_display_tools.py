"""Tests for curated display tools (show_table, show_detail, etc.).

These test the template functions directly, exercising both the Prefab
UI path (when prefab-ui is installed) and the JSON fallback path.
"""

import importlib
import sys
from typing import Any
from unittest.mock import patch

import pytest


def _load_display_tools() -> Any:
    """Import the display_tools module, reloading to pick up current state."""
    mod_name = "mcp_generator.templates.display_tools"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# JSON fallback tests (run regardless of prefab-ui availability)
# ---------------------------------------------------------------------------


class TestShowTableFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        with patch.dict(sys.modules, {"prefab_ui": None, "prefab_ui.app": None}):
            mod = _load_display_tools()
            prev = mod.PREFAB_AVAILABLE
            mod.PREFAB_AVAILABLE = False
            try:
                result = mod.show_table(
                    title="Test",
                    columns=[{"key": "id", "label": "ID"}],
                    rows=[{"id": 1}],
                )
                assert isinstance(result, dict)
                assert result["title"] == "Test"
                assert len(result["rows"]) == 1
            finally:
                mod.PREFAB_AVAILABLE = prev

    def test_includes_columns_in_fallback(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_table(
                title="T",
                columns=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}],
                rows=[],
            )
            assert len(result["columns"]) == 2
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowDetailFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_detail(
                title="Record",
                fields=[{"label": "Name", "value": "Alice"}],
            )
            assert isinstance(result, dict)
            assert result["title"] == "Record"
            assert result["fields"][0]["value"] == "Alice"
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowChartFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_chart(
                title="Revenue",
                data=[{"month": "Jan", "val": 100}],
                x_axis="month",
                y_axes=[{"key": "val", "label": "Value"}],
            )
            assert isinstance(result, dict)
            assert result["chart_type"] == "bar"
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowFormFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_form(
                title="New Pet",
                fields=[{"name": "name", "label": "Name"}],
                submit_tool="add_pet",
            )
            assert isinstance(result, dict)
            assert result["submit_tool"] == "add_pet"
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowComparisonFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_comparison(
                title="Plans",
                items=[{"name": "A", "price": "$10"}, {"name": "B", "price": "$20"}],
            )
            assert isinstance(result, dict)
            assert len(result["items"]) == 2
        finally:
            mod.PREFAB_AVAILABLE = prev


# ---------------------------------------------------------------------------
# New tools: show_metrics, show_timeline, show_progress
# ---------------------------------------------------------------------------


class TestShowMetricsFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_metrics(
                title="Dashboard",
                metrics=[
                    {"label": "Revenue", "value": "$42K"},
                    {"label": "Users", "value": "1,234"},
                ],
            )
            assert isinstance(result, dict)
            assert result["title"] == "Dashboard"
            assert len(result["metrics"]) == 2
        finally:
            mod.PREFAB_AVAILABLE = prev

    def test_accepts_optional_fields(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_metrics(
                title="KPIs",
                metrics=[
                    {
                        "label": "Revenue",
                        "value": "$42K",
                        "delta": "+12%",
                        "trend": "up",
                        "trend_sentiment": "positive",
                        "description": "vs last month",
                        "sparkline": [10, 25, 18, 30, 42],
                    },
                ],
                columns=3,
                subtitle="Monthly overview",
            )
            assert result["metrics"][0]["sparkline"] == [10, 25, 18, 30, 42]
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowTimelineFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_timeline(
                title="Order History",
                events=[
                    {"title": "Order placed", "timestamp": "2026-04-20 10:30"},
                    {"title": "Shipped", "timestamp": "2026-04-21 14:00"},
                ],
            )
            assert isinstance(result, dict)
            assert result["title"] == "Order History"
            assert len(result["events"]) == 2
        finally:
            mod.PREFAB_AVAILABLE = prev

    def test_accepts_optional_event_fields(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_timeline(
                title="Activity",
                events=[
                    {
                        "title": "Deployed",
                        "timestamp": "2026-04-20",
                        "status": "completed",
                        "description": "v2.1.0 to production",
                        "badge": "Success",
                        "badge_variant": "success",
                    },
                ],
            )
            assert result["events"][0]["status"] == "completed"
        finally:
            mod.PREFAB_AVAILABLE = prev


class TestShowProgressFallback:
    def test_returns_json_when_prefab_unavailable(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_progress(
                title="Onboarding",
                steps=[
                    {"label": "Sign up", "status": "completed"},
                    {"label": "Verify email", "status": "active"},
                    {"label": "Set password", "status": "pending"},
                ],
            )
            assert isinstance(result, dict)
            assert result["title"] == "Onboarding"
            assert len(result["steps"]) == 3
        finally:
            mod.PREFAB_AVAILABLE = prev

    def test_accepts_step_descriptions(self) -> None:
        mod = _load_display_tools()
        prev = mod.PREFAB_AVAILABLE
        mod.PREFAB_AVAILABLE = False
        try:
            result = mod.show_progress(
                title="Pipeline",
                steps=[
                    {"label": "Build", "status": "completed", "description": "2m 15s"},
                    {"label": "Test", "status": "active", "description": "Running 247 tests"},
                ],
                subtitle="CI/CD Pipeline",
            )
            assert result["steps"][1]["description"] == "Running 247 tests"
        finally:
            mod.PREFAB_AVAILABLE = prev


# ---------------------------------------------------------------------------
# Prefab UI integration tests (only run when prefab-ui is installed)
# ---------------------------------------------------------------------------

_mod = _load_display_tools()
_HAS_PREFAB = _mod.PREFAB_AVAILABLE

prefab_only = pytest.mark.skipif(not _HAS_PREFAB, reason="prefab-ui not installed")


@prefab_only
class TestShowTablePrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_table(
            title="Pets",
            columns=[{"key": "name", "label": "Name"}],
            rows=[{"name": "Buddy"}],
        )
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowDetailPrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_detail(
            title="Pet",
            fields=[{"label": "Name", "value": "Buddy"}],
        )
        assert isinstance(result, PrefabApp)

    def test_badge_variant_renders(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_detail(
            title="Pet",
            fields=[{"label": "Status", "value": "active", "variant": "success"}],
        )
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowChartPrefab:
    def test_returns_prefab_app_bar(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_chart(
            title="Sales",
            data=[{"month": "Jan", "revenue": 100}],
            x_axis="month",
            y_axes=[{"key": "revenue", "label": "Revenue"}],
            chart_type="bar",
        )
        assert isinstance(result, PrefabApp)

    def test_returns_prefab_app_line(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_chart(
            title="Trend",
            data=[{"x": 1, "y": 10}, {"x": 2, "y": 20}],
            x_axis="x",
            y_axes=[{"key": "y", "label": "Y"}],
            chart_type="line",
        )
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowFormPrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_form(
            title="Add Pet",
            fields=[{"name": "name", "label": "Name", "required": True}],
            submit_tool="add_pet",
        )
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowComparisonPrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_comparison(
            title="Plans",
            items=[{"name": "A", "price": "$10"}, {"name": "B", "price": "$20"}],
        )
        assert isinstance(result, PrefabApp)

    def test_empty_items_renders(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_comparison(title="Empty", items=[])
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowMetricsPrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_metrics(
            title="KPIs",
            metrics=[
                {"label": "Revenue", "value": "$42K"},
                {"label": "Users", "value": "1,234"},
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_sparkline_renders(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_metrics(
            title="Trends",
            metrics=[
                {
                    "label": "Revenue",
                    "value": "$42K",
                    "delta": "+12%",
                    "trend": "up",
                    "trend_sentiment": "positive",
                    "sparkline": [10, 25, 18, 30, 42],
                },
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_custom_columns(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_metrics(
            title="Two-Col",
            metrics=[{"label": "A", "value": "1"}, {"label": "B", "value": "2"}],
            columns=2,
        )
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowTimelinePrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_timeline(
            title="Events",
            events=[
                {"title": "Created", "timestamp": "2026-04-20 10:30", "status": "completed"},
                {"title": "Updated", "timestamp": "2026-04-20 11:00", "status": "active"},
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_badge_renders(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_timeline(
            title="Feed",
            events=[
                {
                    "title": "Deployed",
                    "timestamp": "2026-04-20",
                    "badge": "v2.1.0",
                    "badge_variant": "success",
                },
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_all_status_colors(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        events = [
            {"title": f"Event {s}", "timestamp": "2026-01-01", "status": s}
            for s in ["completed", "active", "pending", "error", "cancelled", "unknown"]
        ]
        result = mod.show_timeline(title="Statuses", events=events)
        assert isinstance(result, PrefabApp)


@prefab_only
class TestShowProgressPrefab:
    def test_returns_prefab_app(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_progress(
            title="Setup",
            steps=[
                {"label": "Step 1", "status": "completed"},
                {"label": "Step 2", "status": "active"},
                {"label": "Step 3", "status": "pending"},
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_all_completed(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_progress(
            title="Done",
            steps=[
                {"label": "A", "status": "completed"},
                {"label": "B", "status": "completed"},
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_all_pending(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_progress(
            title="Not Started",
            steps=[
                {"label": "A", "status": "pending"},
                {"label": "B", "status": "pending"},
            ],
        )
        assert isinstance(result, PrefabApp)

    def test_step_descriptions_render(self) -> None:
        from prefab_ui.app import PrefabApp

        mod = _load_display_tools()
        result = mod.show_progress(
            title="Pipeline",
            steps=[
                {"label": "Build", "status": "completed", "description": "2m 15s"},
                {"label": "Test", "status": "active", "description": "Running"},
            ],
            subtitle="CI Status",
        )
        assert isinstance(result, PrefabApp)
