"""
Predefined query tools for ResStock data.

Each internal tool validates column names against whitelists, builds parameterized SQL,
executes via aiosqlite, and returns JSON. The query_data() function is the MCP-exposed
entry point: it uses an LLM to route natural language requests to the right internal tool.
"""

import json
import logging
import statistics

import aiosqlite

from app.config import SQLITE_DB_PATH
from app.llm import chat
from app.tracing import tracer

logger = logging.getLogger("query-agent.tools")

METRIC_COLUMNS = {
    "energy_use_total", "energy_use_net",
    "fuel_electricity_total", "fuel_natural_gas_total",
    "fuel_propane_total", "fuel_fuel_oil_total",
    "end_use_electricity_heating", "end_use_electricity_cooling",
    "end_use_electricity_hot_water", "end_use_natural_gas_heating",
    "end_use_natural_gas_hot_water", "end_use_propane_hot_water",
    "end_use_electricity_lighting", "end_use_electricity_cooling_fans",
    "end_use_electricity_heating_fans",
}

BUILDING_COLUMNS = {
    "building_id", "state", "county", "vintage", "vintage_acs",
    "building_type", "floor_area", "stories", "bedrooms", "occupants",
    "heating_fuel", "water_heater_fuel", "hvac_type", "hvac_has_ducts",
    "climate_zone", "area_median_income", "insulation_wall", "insulation_ceiling",
}

METRIC_DESCRIPTIONS = {
    "energy_use_total": "Total site energy (MBtu)",
    "energy_use_net": "Net site energy (MBtu)",
    "fuel_electricity_total": "Total electricity (MBtu)",
    "fuel_natural_gas_total": "Total natural gas (MBtu)",
    "fuel_propane_total": "Total propane (MBtu)",
    "fuel_fuel_oil_total": "Total fuel oil (MBtu)",
    "end_use_electricity_heating": "Electricity for heating (MBtu)",
    "end_use_electricity_cooling": "Electricity for cooling (MBtu)",
    "end_use_electricity_hot_water": "Electricity for hot water (MBtu)",
    "end_use_natural_gas_heating": "Natural gas for heating (MBtu)",
    "end_use_natural_gas_hot_water": "Natural gas for hot water (MBtu)",
    "end_use_propane_hot_water": "Propane for hot water (MBtu)",
    "end_use_electricity_lighting": "Electricity for lighting (MBtu)",
    "end_use_electricity_cooling_fans": "Electricity for cooling fans/pumps (MBtu)",
    "end_use_electricity_heating_fans": "Electricity for heating fans/pumps (MBtu)",
}

BUILDING_DESCRIPTIONS = {
    "building_id": "Unique building identifier",
    "state": "State (always NC)",
    "county": "County (e.g. 'NC, Wake County')",
    "vintage": "Construction decade (e.g. '1990s')",
    "vintage_acs": "ACS vintage grouping (e.g. '1980-99')",
    "building_type": "Building type (e.g. 'Single-Family Detached')",
    "floor_area": "Floor area bin (e.g. '1000-1499')",
    "stories": "Number of stories",
    "bedrooms": "Number of bedrooms",
    "occupants": "Number of occupants",
    "heating_fuel": "Primary heating fuel (Electricity, Natural Gas, Propane, Fuel Oil, None)",
    "water_heater_fuel": "Water heater fuel",
    "hvac_type": "HVAC system type and fuel",
    "hvac_has_ducts": "Has ductwork (Yes/No)",
    "climate_zone": "EnergyStar climate zone (North-Central or South-Central)",
    "area_median_income": "AMI bracket (e.g. '60-80%')",
    "insulation_wall": "Wall insulation (e.g. 'Wood Stud, R-11')",
    "insulation_ceiling": "Ceiling insulation (NULL if not applicable)",
}


def _validate_metric(metric: str) -> str:
    if metric not in METRIC_COLUMNS:
        raise ValueError(
            f"Unknown metric '{metric}'. Valid metrics: {sorted(METRIC_COLUMNS)}"
        )
    return metric


def _validate_building_col(col: str) -> str:
    if col not in BUILDING_COLUMNS:
        raise ValueError(
            f"Unknown building column '{col}'. Valid columns: {sorted(BUILDING_COLUMNS)}"
        )
    return col


def _build_where(filters: dict | None) -> tuple[str, list]:
    if not filters:
        return "", []
    clauses = []
    params = []
    for key, value in filters.items():
        _validate_building_col(key)
        if value is None:
            clauses.append(f"b.{key} IS NULL")
        else:
            clauses.append(f"b.{key} = ?")
            params.append(value)
    return " AND " + " AND ".join(clauses), params


def _compute_percentiles(values: list[float]) -> dict:
    n = len(values)
    if n == 0:
        return {"count": 0, "mean": None, "std": None, "min": None,
                "p25": None, "median": None, "p75": None, "max": None}
    s = sorted(values)
    mean_val = statistics.mean(s)
    return {
        "count": n,
        "mean": round(mean_val, 4),
        "std": round(statistics.stdev(s), 4) if n > 1 else 0.0,
        "min": round(s[0], 4),
        "p25": round(s[n // 4], 4),
        "median": round(statistics.median(s), 4),
        "p75": round(s[(3 * n) // 4], 4),
        "max": round(s[-1], 4),
    }


async def describe_metric(metric: str, filters: dict = None) -> str:
    """Get distribution statistics for a metric (count, mean, std, min, p25, median, p75, max).

    Args:
        metric: Column name from results table (e.g. 'energy_use_total', 'end_use_electricity_heating').
                Valid metrics: energy_use_total, energy_use_net, fuel_electricity_total,
                fuel_natural_gas_total, fuel_propane_total, fuel_fuel_oil_total,
                end_use_electricity_heating, end_use_electricity_cooling, end_use_electricity_hot_water,
                end_use_natural_gas_heating, end_use_natural_gas_hot_water, end_use_propane_hot_water,
                end_use_electricity_lighting, end_use_electricity_cooling_fans, end_use_electricity_heating_fans.
        filters: Optional dict of building characteristic filters
                 (e.g. {"heating_fuel": "Natural Gas", "climate_zone": "South-Central"}).
    """
    with tracer.start_as_current_span("describe_metric") as span:
        span.set_attribute("metric", metric)
        try:
            _validate_metric(metric)
            where_clause, params = _build_where(filters)
            sql = (
                f"SELECT r.{metric} FROM results r "
                f"JOIN buildings b ON r.building_id = b.building_id "
                f"WHERE r.{metric} IS NOT NULL{where_clause}"
            )
            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
            values = [row[0] for row in rows]
            result = _compute_percentiles(values)
            result["metric"] = metric
            result["unit"] = "MBtu"
            if filters:
                result["filters"] = filters
            span.set_attribute("result.count", result["count"])
            return json.dumps(result)
        except Exception as exc:
            logger.error("describe_metric error: %s", exc)
            return json.dumps({"error": str(exc)})


async def metric_by_group(metric: str, group_by, filters: dict = None) -> str:
    """Get a metric aggregated by building characteristic(s) (count, mean, median per group).

    Args:
        metric: Column name from results table (e.g. 'energy_use_total').
        group_by: Column name or list of column names from buildings table to group by
                  (e.g. 'heating_fuel', ['vintage', 'building_type']).
        filters: Optional dict of building characteristic filters.
    """
    with tracer.start_as_current_span("metric_by_group") as span:
        span.set_attribute("metric", metric)
        span.set_attribute("group_by", json.dumps(group_by) if isinstance(group_by, list) else group_by)
        try:
            if isinstance(group_by, list) and not group_by:
                raise ValueError("group_by list cannot be empty")
            _validate_metric(metric)
            if isinstance(group_by, list):
                for col in group_by:
                    _validate_building_col(col)
                group_cols = ", ".join(f"b.{col}" for col in group_by)
                group_by_label = " | ".join(group_by)
            else:
                _validate_building_col(group_by)
                group_cols = f"b.{group_by}"
                group_by_label = group_by
                group_by = [group_by]
            where_clause, params = _build_where(filters)
            sql = (
                f"SELECT {group_cols}, r.{metric} FROM results r "
                f"JOIN buildings b ON r.building_id = b.building_id "
                f"WHERE r.{metric} IS NOT NULL{where_clause} "
                f"ORDER BY {group_cols}"
            )
            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()

            from collections import defaultdict
            n_group_cols = len(group_by)
            groups = defaultdict(list)
            for row in rows:
                group_key = " | ".join(str(row[i]) for i in range(n_group_cols))
                groups[group_key].append(row[n_group_cols])

            result = []
            for group_val in sorted(groups.keys()):
                vals = groups[group_val]
                result.append({
                    "group": group_val,
                    "count": len(vals),
                    "mean": round(statistics.mean(vals), 4),
                    "median": round(statistics.median(vals), 4),
                })

            span.set_attribute("result.groups", len(result))
            return json.dumps({
                "metric": metric, "group_by": group_by_label,
                "unit": "MBtu", "data": result,
            })
        except Exception as exc:
            logger.error("metric_by_group error: %s", exc)
            return json.dumps({"error": str(exc)})


async def distribution(metric: str, group_by: str = None, filters: dict = None) -> str:
    """Get raw per-building values for distribution charts (boxplots, violins, histograms).

    Args:
        metric: Column name from results table.
        group_by: Optional column from buildings to group values by (e.g. 'state', 'heating_fuel').
        filters: Optional dict of building characteristic filters.
    """
    with tracer.start_as_current_span("distribution") as span:
        span.set_attribute("metric", metric)
        try:
            _validate_metric(metric)
            if group_by:
                _validate_building_col(group_by)
            where_clause, params = _build_where(filters)

            if group_by:
                sql = (
                    f"SELECT b.{group_by}, r.{metric} FROM results r "
                    f"JOIN buildings b ON r.building_id = b.building_id "
                    f"WHERE r.{metric} IS NOT NULL{where_clause} "
                    f"ORDER BY b.{group_by}"
                )
            else:
                sql = (
                    f"SELECT r.{metric} FROM results r "
                    f"JOIN buildings b ON r.building_id = b.building_id "
                    f"WHERE r.{metric} IS NOT NULL{where_clause}"
                )

            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()

            if group_by:
                from collections import defaultdict
                groups = defaultdict(list)
                for group_val, val in rows:
                    groups[str(group_val)].append(round(val, 4))
                group_stats = {k: _compute_percentiles(v) for k, v in sorted(groups.items())}
                result = {
                    "metric": metric, "group_by": group_by, "unit": "MBtu",
                    "groups": {k: v for k, v in sorted(groups.items())},
                    "group_stats": group_stats,
                }
            else:
                vals = [round(row[0], 4) for row in rows]
                result = {
                    "metric": metric, "unit": "MBtu",
                    "values": vals,
                    "stats": _compute_percentiles(vals),
                }

            span.set_attribute("result.total_values", len(rows))
            return json.dumps(result)
        except Exception as exc:
            logger.error("distribution error: %s", exc)
            return json.dumps({"error": str(exc)})


async def compare_metrics(metrics: list, group_by: str = None, filters: dict = None) -> str:
    """Compare multiple metrics across buildings, optionally grouped by a characteristic.

    Args:
        metrics: List of column names from results table
                 (e.g. ['end_use_electricity_heating', 'end_use_electricity_cooling']).
        group_by: Optional column from buildings to group by.
        filters: Optional dict of building characteristic filters.
    """
    with tracer.start_as_current_span("compare_metrics") as span:
        span.set_attribute("metrics", json.dumps(metrics))
        try:
            metrics = list(dict.fromkeys(metrics))
            if not metrics:
                raise ValueError("metrics list cannot be empty")
            for m in metrics:
                _validate_metric(m)
            if group_by:
                _validate_building_col(group_by)
            where_clause, params = _build_where(filters)

            metric_cols = ", ".join(f"r.{m}" for m in metrics)
            if group_by:
                sql = (
                    f"SELECT b.{group_by}, {metric_cols} FROM results r "
                    f"JOIN buildings b ON r.building_id = b.building_id "
                    f"WHERE 1=1{where_clause} ORDER BY b.{group_by}"
                )
            else:
                sql = (
                    f"SELECT {metric_cols} FROM results r "
                    f"JOIN buildings b ON r.building_id = b.building_id "
                    f"WHERE 1=1{where_clause}"
                )

            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()

            if group_by:
                from collections import defaultdict
                groups = defaultdict(lambda: {m: [] for m in metrics})
                for row in rows:
                    g = str(row[0])
                    for i, m in enumerate(metrics):
                        if row[i + 1] is not None:
                            groups[g][m].append(row[i + 1])
                data = []
                for g in sorted(groups.keys()):
                    entry = {"group": g}
                    for m in metrics:
                        vals = groups[g][m]
                        entry[m] = round(statistics.mean(vals), 4) if vals else None
                    data.append(entry)
                result = {"metrics": metrics, "group_by": group_by, "unit": "MBtu", "data": data}
            else:
                data = {m: [] for m in metrics}
                for row in rows:
                    for i, m in enumerate(metrics):
                        if row[i] is not None:
                            data[m].append(row[i])
                summary = {}
                for m in metrics:
                    vals = data[m]
                    summary[m] = {
                        "count": len(vals),
                        "mean": round(statistics.mean(vals), 4) if vals else None,
                        "median": round(statistics.median(vals), 4) if vals else None,
                    }
                result = {"metrics": metrics, "unit": "MBtu", "data": summary}

            span.set_attribute("result.rows", len(rows))
            return json.dumps(result)
        except Exception as exc:
            logger.error("compare_metrics error: %s", exc)
            return json.dumps({"error": str(exc)})


async def building_stock_summary(column: str, filters: dict = None) -> str:
    """Get the distribution of a building characteristic (value counts and percentages).

    Args:
        column: Column name from buildings table (e.g. 'heating_fuel', 'vintage', 'climate_zone').
        filters: Optional dict of building characteristic filters.
    """
    with tracer.start_as_current_span("building_stock_summary") as span:
        span.set_attribute("column", column)
        try:
            _validate_building_col(column)
            where_clause, params = _build_where(filters)
            where_sql = f"WHERE 1=1{where_clause}" if where_clause else ""
            sql = (
                f"SELECT b.{column}, COUNT(*) as cnt FROM buildings b "
                f"{where_sql} GROUP BY b.{column} ORDER BY cnt DESC"
            )
            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()

            total = sum(r[1] for r in rows)
            data = [
                {"value": str(r[0]) if r[0] is not None else "NULL",
                 "count": r[1],
                 "percentage": round(100.0 * r[1] / total, 2) if total > 0 else 0}
                for r in rows
            ]

            span.set_attribute("result.categories", len(data))
            return json.dumps({"column": column, "total": total, "data": data})
        except Exception as exc:
            logger.error("building_stock_summary error: %s", exc)
            return json.dumps({"error": str(exc)})


async def describe_building_column(column: str, filters: dict = None) -> str:
    """Get numeric summary statistics for a building characteristic column (count, mean, median, min, max).

    Works on columns that contain numeric-like values (e.g. occupants, bedrooms, stories).
    For purely categorical columns (e.g. heating_fuel, vintage), use building_stock_summary instead.

    Args:
        column: Column name from buildings table (e.g. 'occupants', 'bedrooms', 'stories').
        filters: Optional dict of building characteristic filters.
    """
    with tracer.start_as_current_span("describe_building_column") as span:
        span.set_attribute("column", column)
        try:
            _validate_building_col(column)
            where_clause, params = _build_where(filters)
            where_sql = f"WHERE 1=1{where_clause}" if where_clause else ""
            sql = (
                f"SELECT b.{column} FROM buildings b "
                f"{where_sql}"
            )
            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()

            values = []
            for row in rows:
                try:
                    values.append(float(row[0]))
                except (ValueError, TypeError):
                    continue

            if not values:
                return json.dumps({"error": f"No numeric values found in column '{column}'"})

            result = _compute_percentiles(values)
            result["column"] = column
            if filters:
                result["filters"] = filters
            span.set_attribute("result.count", result["count"])
            return json.dumps(result)
        except Exception as exc:
            logger.error("describe_building_column error: %s", exc)
            return json.dumps({"error": str(exc)})


async def list_available_data() -> str:
    """List all available metrics and building characteristics that can be queried."""
    return json.dumps({
        "metrics": {k: v for k, v in sorted(METRIC_DESCRIPTIONS.items())},
        "building_characteristics": {k: v for k, v in sorted(BUILDING_DESCRIPTIONS.items())},
        "dataset": "14,217 residential buildings in North Carolina, baseline (no upgrades), annual totals in MBtu.",
    })


# === LLM Tool Router ===

_BUILDING_COLS_NO_ID = sorted(BUILDING_COLUMNS - {"building_id"})

TOOL_ROUTER_PROMPT = f"""You are a data query router for a residential building energy database (ResStock, North Carolina).

You receive a natural language data request and must pick the right query tool and fill in its arguments.

AVAILABLE TOOLS:

1. describe_metric(metric, filters?)
   Returns distribution stats (count, mean, std, min, p25, median, p75, max) for one metric.
   Use for: "What's the distribution of...?", "How much energy do buildings use?", summary statistics.

2. metric_by_group(metric, group_by, filters?)
   Returns count, mean, median for one metric grouped by a building characteristic.
   Use for: "Average X by Y", "Compare X across Y", stratified summaries.

3. distribution(metric, group_by?, filters?)
   Returns raw per-building values (for boxplots, violins, histograms).
   Use for: "Show the distribution of...", "Boxplot of...", "Violin plot of...", raw data for charts.

4. compare_metrics(metrics, group_by?, filters?)
   Returns multiple metrics side by side.
   Use for: "Compare heating vs cooling", "Show electricity and gas together".

5. building_stock_summary(column, filters?)
   Returns value counts and percentages for a building characteristic.
   Use for: "What's the breakdown of...?", "How many buildings have...?", stock composition.

6. describe_building_column(column, filters?)
   Returns numeric summary stats (count, mean, median, min, max, p25, p75) for a building characteristic.
   Use for: "What's the average number of occupants?", "How many bedrooms do these homes have?"
   Only works on numeric-like columns (occupants, bedrooms, stories). For categorical columns, use building_stock_summary.

7. list_available_data()
   Returns all available metric and characteristic names. No arguments.

VALID METRIC NAMES (results table, all annual MBtu):
{json.dumps(sorted(METRIC_COLUMNS), indent=2)}

VALID BUILDING CHARACTERISTIC NAMES (buildings table):
{json.dumps(_BUILDING_COLS_NO_ID, indent=2)}

METRIC MEANINGS:
{json.dumps(METRIC_DESCRIPTIONS, indent=2)}

BUILDING CHARACTERISTIC MEANINGS:
{json.dumps(BUILDING_DESCRIPTIONS, indent=2)}

KEY NOTES:
- All energy values are annual MBtu. A value of 0.0 means the building doesn't use that fuel.
- heating_fuel is the most important stratification dimension for energy analysis.
- climate_zone has 2 values: North-Central, South-Central.
- The "filters" argument is a dict mapping building column names to exact string values.
- Only include filters if the user explicitly mentioned a constraint.
- EXACT filter values (use these exactly, not abbreviations):
  heating_fuel: Electricity, Natural Gas, Propane, Fuel Oil, None
  water_heater_fuel: Electricity, Natural Gas, Propane, Fuel Oil
  climate_zone: North-Central, South-Central
  area_median_income: 0-30%, 30-60%, 60-80%, 80-100%, 100-120%, 120-150%
  hvac_has_ducts: Yes, No

Return ONLY a JSON object with "tool" and "args" keys. No explanation, no markdown fences.

Examples:
{{"tool": "describe_metric", "args": {{"metric": "energy_use_total"}}}}
{{"tool": "metric_by_group", "args": {{"metric": "end_use_electricity_heating", "group_by": "heating_fuel"}}}}
{{"tool": "metric_by_group", "args": {{"metric": "energy_use_total", "group_by": ["vintage", "building_type"]}}}}
{{"tool": "distribution", "args": {{"metric": "fuel_electricity_total", "group_by": "climate_zone"}}}}
{{"tool": "building_stock_summary", "args": {{"column": "vintage"}}}}
{{"tool": "compare_metrics", "args": {{"metrics": ["end_use_electricity_heating", "end_use_natural_gas_heating"], "group_by": "vintage"}}}}
{{"tool": "describe_metric", "args": {{"metric": "energy_use_total", "filters": {{"heating_fuel": "Natural Gas"}}}}}}
{{"tool": "describe_building_column", "args": {{"column": "occupants"}}}}
"""

_TOOL_DISPATCH = {
    "describe_metric": describe_metric,
    "metric_by_group": metric_by_group,
    "distribution": distribution,
    "compare_metrics": compare_metrics,
    "building_stock_summary": building_stock_summary,
    "describe_building_column": describe_building_column,
    "list_available_data": list_available_data,
}


async def query_data(description: str) -> str:
    """Translate a natural language data request into a tool call and return the result.

    Args:
        description: A natural language description of the data you need.
                     Example: "Average electricity heating energy by vintage for gas-heated homes"
    """
    with tracer.start_as_current_span("query_data") as span:
        span.set_attribute("query.description", description)

        messages = [
            {"role": "system", "content": TOOL_ROUTER_PROMPT},
            {"role": "user", "content": description},
        ]

        raw = await chat(messages)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            plan = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse tool router response: %s", cleaned[:200])
            span.set_attribute("query.error", "json_parse_failed")
            return json.dumps({"error": f"Failed to parse tool selection: {cleaned[:100]}"})

        tool_name = plan.get("tool", "")
        tool_args = plan.get("args", {})
        span.set_attribute("query.tool", tool_name)
        span.set_attribute("query.args", json.dumps(tool_args))

        if tool_name not in _TOOL_DISPATCH:
            logger.error("Unknown tool: %s", tool_name)
            return json.dumps({"error": f"Unknown tool '{tool_name}'. Valid: {sorted(_TOOL_DISPATCH.keys())}"})

        logger.info("Routing to %s(%s)", tool_name, json.dumps(tool_args)[:80])

        try:
            result_raw = await _TOOL_DISPATCH[tool_name](**tool_args)
            result = json.loads(result_raw)
            result["_tool"] = tool_name
            return json.dumps(result)
        except TypeError as exc:
            logger.error("Tool %s argument error: %s", tool_name, exc)
            return json.dumps({"error": f"Invalid arguments for {tool_name}: {exc}"})
        except Exception as exc:
            logger.error("Tool %s execution error: %s", tool_name, exc)
            return json.dumps({"error": str(exc)})
