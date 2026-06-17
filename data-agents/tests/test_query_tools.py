"""Unit tests for query-agent tool functions."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

_query_agent_path = str(Path(__file__).parent.parent / "query-agent")
sys.path.insert(0, _query_agent_path)

from app.tools import (
    _validate_metric,
    _validate_building_col,
    _build_where,
    _compute_percentiles,
    describe_metric,
    metric_by_group,
    distribution,
    building_stock_summary,
    compare_metrics,
    list_available_data,
    METRIC_COLUMNS,
    BUILDING_COLUMNS,
)


class TestValidateMetric:
    def test_valid_metric_returns_name(self):
        assert _validate_metric("energy_use_total") == "energy_use_total"

    def test_all_metrics_validate(self):
        for m in METRIC_COLUMNS:
            assert _validate_metric(m) == m

    def test_invalid_metric_raises(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            _validate_metric("not_a_real_metric")

    def test_building_col_as_metric_raises(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            _validate_metric("heating_fuel")


class TestValidateBuildingCol:
    def test_valid_column_returns_name(self):
        assert _validate_building_col("heating_fuel") == "heating_fuel"

    def test_all_columns_validate(self):
        for col in BUILDING_COLUMNS:
            assert _validate_building_col(col) == col

    def test_invalid_column_raises(self):
        with pytest.raises(ValueError, match="Unknown building column"):
            _validate_building_col("nonexistent_column")

    def test_metric_as_building_col_raises(self):
        with pytest.raises(ValueError, match="Unknown building column"):
            _validate_building_col("energy_use_total")


class TestBuildWhere:
    def test_none_filters_returns_empty(self):
        clause, params = _build_where(None)
        assert clause == ""
        assert params == []

    def test_empty_filters_returns_empty(self):
        clause, params = _build_where({})
        assert clause == ""
        assert params == []

    def test_single_filter(self):
        clause, params = _build_where({"heating_fuel": "Electricity"})
        assert "b.heating_fuel = ?" in clause
        assert params == ["Electricity"]

    def test_multiple_filters(self):
        clause, params = _build_where({"heating_fuel": "Natural Gas", "climate_zone": "South-Central"})
        assert "b.heating_fuel = ?" in clause
        assert "b.climate_zone = ?" in clause
        assert len(params) == 2

    def test_null_filter_value(self):
        clause, params = _build_where({"insulation_ceiling": None})
        assert "b.insulation_ceiling IS NULL" in clause
        assert params == []

    def test_invalid_column_raises(self):
        with pytest.raises(ValueError, match="Unknown building column"):
            _build_where({"fake_column": "value"})


class TestComputePercentiles:
    def test_empty_list(self):
        result = _compute_percentiles([])
        assert result["count"] == 0
        assert result["mean"] is None

    def test_single_value(self):
        result = _compute_percentiles([42.0])
        assert result["count"] == 1
        assert result["mean"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0

    def test_known_distribution(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        result = _compute_percentiles(values)
        assert result["count"] == 8
        assert result["mean"] == 4.5
        assert result["min"] == 1.0
        assert result["max"] == 8.0
        assert result["median"] == 4.5

    def test_std_with_two_values(self):
        result = _compute_percentiles([0.0, 10.0])
        assert result["count"] == 2
        assert result["std"] > 0


@pytest.mark.asyncio
class TestDescribeMetric:
    async def test_basic_metric(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await describe_metric("energy_use_total"))
        assert result["count"] == 5
        assert result["metric"] == "energy_use_total"
        assert result["unit"] == "MBtu"
        assert result["min"] == 68.9
        assert result["max"] == 112.5

    async def test_with_filter(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await describe_metric("energy_use_total", {"heating_fuel": "Electricity"}))
        assert result["count"] == 2
        assert result["filters"] == {"heating_fuel": "Electricity"}

    async def test_invalid_metric_returns_error(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await describe_metric("fake_metric"))
        assert "error" in result


@pytest.mark.asyncio
class TestMetricByGroup:
    async def test_group_by_single_column(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await metric_by_group("energy_use_total", "heating_fuel"))
        assert "data" in result
        groups = {r["group"] for r in result["data"]}
        assert "Electricity" in groups
        assert "Natural Gas" in groups

    async def test_group_by_list(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await metric_by_group("energy_use_total", ["climate_zone", "heating_fuel"]))
        assert "data" in result
        assert len(result["data"]) > 0


@pytest.mark.asyncio
class TestBuildingStockSummary:
    async def test_heating_fuel_summary(self, test_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", test_db)
        result = json.loads(await building_stock_summary("heating_fuel"))
        assert result["total"] == 5
        fuel_counts = {r["value"]: r["count"] for r in result["data"]}
        assert fuel_counts["Electricity"] == 2
        assert fuel_counts["Natural Gas"] == 1


@pytest.mark.asyncio
class TestListAvailableData:
    async def test_returns_metrics_and_characteristics(self):
        result = json.loads(await list_available_data())
        assert "metrics" in result
        assert "building_characteristics" in result
        assert "energy_use_total" in result["metrics"]
        assert "heating_fuel" in result["building_characteristics"]
