"""Unit tests for visualization-agent chart data builders.

Uses importlib to load visualize.py after stubbing its external dependencies,
avoiding sys.path conflicts with the query-agent's identically-named 'app' package.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

_viz_agent_dir = Path(__file__).parent.parent / "visualization-agent"

_app_pkg = types.ModuleType("app")
_app_pkg.__path__ = [str(_viz_agent_dir / "app")]
sys.modules.setdefault("app", _app_pkg)

for stub in ("app.llm", "app.mcp_client", "app.tracing"):
    sys.modules.setdefault(stub, MagicMock())

_viz_spec = importlib.util.spec_from_file_location(
    "app.visualize", _viz_agent_dir / "app" / "visualize.py")
_viz_mod = importlib.util.module_from_spec(_viz_spec)
_viz_spec.loader.exec_module(_viz_mod)

_build_boxplot_data = _viz_mod._build_boxplot_data
_build_grouped_bar = _viz_mod._build_grouped_bar
_build_summary_chart = _viz_mod._build_summary_chart
_build_compare_chart = _viz_mod._build_compare_chart
_build_describe_chart = _viz_mod._build_describe_chart
_build_distribution_bar = _viz_mod._build_distribution_bar
_build_generic_bar = _viz_mod._build_generic_bar


class TestBuildBoxplotData:
    def test_grouped_data(self):
        data = {
            "metric": "energy_use_total",
            "groups": {
                "Electricity": [85.2, 68.9],
                "Natural Gas": [112.5],
            },
        }
        result = _build_boxplot_data(data)
        assert result is not None
        assert result["labels"] == ["Electricity", "Natural Gas"]
        assert len(result["datasets"]) == 1
        assert len(result["datasets"][0]["data"]) == 2

    def test_ungrouped_values(self):
        data = {"metric": "energy_use_total", "values": [85.2, 112.5, 95.8]}
        result = _build_boxplot_data(data)
        assert result is not None
        assert result["labels"] == ["All Buildings"]

    def test_empty_data_returns_none(self):
        assert _build_boxplot_data({}) is None


class TestBuildGroupedBar:
    def test_basic_grouped_bar(self):
        data = {
            "metric": "energy_use_total",
            "data": [
                {"group": "Electricity", "count": 2, "mean": 77.05, "median": 77.05},
                {"group": "Natural Gas", "count": 1, "mean": 112.5, "median": 112.5},
            ],
        }
        spec = {"x_key": "group", "y_key": "mean"}
        result = _build_grouped_bar(data, spec)
        assert result is not None
        assert result["labels"] == ["Electricity", "Natural Gas"]
        assert result["datasets"][0]["data"] == [77.05, 112.5]

    def test_empty_data_returns_none(self):
        assert _build_grouped_bar({"data": []}, {}) is None


class TestBuildSummaryChart:
    def test_bar_chart(self):
        data = {
            "column": "heating_fuel",
            "data": [
                {"value": "Electricity", "count": 2, "percentage": 40.0},
                {"value": "Natural Gas", "count": 1, "percentage": 20.0},
            ],
        }
        result = _build_summary_chart(data, "bar")
        assert result is not None
        assert result["labels"] == ["Electricity", "Natural Gas"]
        assert result["datasets"][0]["data"] == [2, 1]

    def test_doughnut_chart_has_per_segment_colors(self):
        data = {
            "column": "heating_fuel",
            "data": [
                {"value": "Electricity", "count": 2, "percentage": 40.0},
                {"value": "Natural Gas", "count": 1, "percentage": 20.0},
            ],
        }
        result = _build_summary_chart(data, "doughnut")
        assert isinstance(result["datasets"][0]["backgroundColor"], list)


class TestBuildDescribeChart:
    def test_produces_six_bar_labels(self):
        data = {"metric": "energy_use_total", "min": 68.9, "p25": 78.3,
                "median": 85.2, "mean": 88.14, "p75": 95.8, "max": 112.5}
        result = _build_describe_chart(data)
        assert result["labels"] == ["Min", "P25", "Median", "Mean", "P75", "Max"]
        assert result["datasets"][0]["data"] == [68.9, 78.3, 85.2, 88.14, 95.8, 112.5]


class TestBuildCompareChart:
    def test_grouped_comparison(self):
        data = {
            "metrics": ["fuel_electricity_total", "fuel_natural_gas_total"],
            "data": [
                {"group": "Electricity", "fuel_electricity_total": 77.05, "fuel_natural_gas_total": 0.0},
                {"group": "Natural Gas", "fuel_electricity_total": 42.3, "fuel_natural_gas_total": 70.2},
            ],
        }
        result = _build_compare_chart(data)
        assert result is not None
        assert len(result["datasets"]) == 2
        assert result["labels"] == ["Electricity", "Natural Gas"]

    def test_no_metrics_returns_none(self):
        assert _build_compare_chart({"metrics": []}) is None
