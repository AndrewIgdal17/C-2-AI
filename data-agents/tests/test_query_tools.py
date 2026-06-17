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


# ============================================================================
# Integration tests against 1,000-building ResStock sample (seed=42)
# ============================================================================


@pytest.mark.asyncio
class TestDescribeMetricResearch:
    """Validate describe_metric against 1,000 real ResStock buildings."""

    async def test_energy_use_total_distribution(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await describe_metric("energy_use_total"))
        ev = expected_values["describe_energy_use_total"]

        assert result["count"] == ev["count"]
        assert result["mean"] == ev["mean"]
        assert result["std"] == ev["std"]
        assert result["min"] == ev["min"]
        assert result["p25"] == ev["p25"]
        assert result["median"] == ev["median"]
        assert result["p75"] == ev["p75"]
        assert result["max"] == ev["max"]
        assert result["unit"] == "MBtu"

    async def test_filtered_by_electric_heating(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await describe_metric("energy_use_total", {"heating_fuel": "Electricity"}))
        ev = expected_values["describe_energy_use_total_electric"]

        assert result["count"] == ev["count"]
        assert result["mean"] == ev["mean"]
        assert result["median"] == ev["median"]

    async def test_zero_values_are_real_not_excluded(self, research_db, monkeypatch):
        """Buildings that don't use natural gas should have 0.0, not be excluded."""
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await describe_metric("fuel_natural_gas_total"))
        assert result["count"] == 1000
        assert result["min"] == 0.0

    async def test_propane_mostly_zero(self, research_db, monkeypatch):
        """Most buildings don't use propane — median should be 0."""
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await describe_metric("fuel_propane_total"))
        assert result["count"] == 1000
        assert result["median"] == 0.0


@pytest.mark.asyncio
class TestMetricByGroupResearch:
    """Validate metric_by_group against 1,000 real ResStock buildings."""

    async def test_energy_by_heating_fuel(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await metric_by_group("energy_use_total", "heating_fuel"))
        ev = expected_values["metric_by_group_heating_fuel"]

        groups = {r["group"]: r for r in result["data"]}
        for fuel, expected_group in ev.items():
            assert groups[fuel]["count"] == expected_group["count"], f"{fuel} count mismatch"
            assert groups[fuel]["mean"] == expected_group["mean"], f"{fuel} mean mismatch"

    async def test_multi_group(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await metric_by_group("energy_use_total", ["climate_zone", "heating_fuel"]))
        assert len(result["data"]) == expected_values["multi_group_count"]

    async def test_gas_homes_use_more_energy(self, research_db, monkeypatch):
        """Gas-heated homes should have higher total energy than electric (known NC pattern)."""
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await metric_by_group("energy_use_total", "heating_fuel"))
        groups = {r["group"]: r["mean"] for r in result["data"]}
        assert groups["Natural Gas"] > groups["Electricity"]


@pytest.mark.asyncio
class TestBuildingStockSummaryResearch:
    """Validate building_stock_summary against 1,000 real ResStock buildings."""

    async def test_heating_fuel_counts(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await building_stock_summary("heating_fuel"))
        ev = expected_values["stock_summary_heating_fuel"]

        assert result["total"] == ev["total"]
        counts = {r["value"]: r["count"] for r in result["data"]}
        for fuel, expected_count in ev["counts"].items():
            assert counts[fuel] == expected_count, f"{fuel}: got {counts.get(fuel)}, expected {expected_count}"

    async def test_climate_zone_counts(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await building_stock_summary("climate_zone"))
        ev = expected_values["stock_summary_climate_zone"]

        assert result["total"] == ev["total"]
        counts = {r["value"]: r["count"] for r in result["data"]}
        for zone, expected_count in ev["counts"].items():
            assert counts[zone] == expected_count

    async def test_electricity_dominant(self, research_db, monkeypatch):
        """Electricity should be the most common heating fuel in NC (known fact)."""
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await building_stock_summary("heating_fuel"))
        top_fuel = result["data"][0]
        assert top_fuel["value"] == "Electricity"
        assert top_fuel["percentage"] > 50.0


@pytest.mark.asyncio
class TestDistributionResearch:
    """Validate distribution queries against 1,000 real ResStock buildings."""

    async def test_ungrouped_returns_all_values(self, research_db, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await distribution("energy_use_total"))
        assert len(result["values"]) == 1000
        assert result["stats"]["count"] == 1000

    async def test_grouped_by_heating_fuel(self, research_db, expected_values, monkeypatch):
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await distribution("energy_use_total", group_by="heating_fuel"))
        ev = expected_values["metric_by_group_heating_fuel"]

        for fuel, expected_group in ev.items():
            assert len(result["groups"][fuel]) == expected_group["count"]

    async def test_values_are_non_negative(self, research_db, monkeypatch):
        """Energy values in MBtu should never be negative (physical constraint)."""
        monkeypatch.setattr("app.tools.SQLITE_DB_PATH", research_db)
        result = json.loads(await distribution("energy_use_total"))
        assert all(v >= 0 for v in result["values"])
