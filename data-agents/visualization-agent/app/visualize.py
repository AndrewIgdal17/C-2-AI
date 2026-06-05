import json
import logging

from app.llm import chat
from app.mcp_client import query_data
from app.tracing import tracer

logger = logging.getLogger("visualization-agent.visualize")

COLORS = ['#5b8def', '#FF5722', '#4CAF50', '#FFC107', '#9C27B0', '#00BCD4', '#E91E63', '#8BC34A']

SYSTEM_PROMPT = """You are a data visualization expert for residential building energy data from NREL's ResStock model.

DATABASE: 14,217 residential buildings in North Carolina, baseline (no upgrades). All energy values are annual MBtu.

ENERGY METRICS AVAILABLE:
- energy_use_total, energy_use_net
- fuel_electricity_total, fuel_natural_gas_total, fuel_propane_total, fuel_fuel_oil_total
- end_use_electricity_heating, end_use_electricity_cooling, end_use_electricity_hot_water
- end_use_natural_gas_heating, end_use_natural_gas_hot_water, end_use_propane_hot_water
- end_use_electricity_lighting, end_use_electricity_cooling_fans, end_use_electricity_heating_fans

A value of 0.0 means the building does not use that fuel. Do not exclude zeros.
This is baseline data only — no upgrades applied. Do not create charts about retrofits, upgrades, savings, or counterfactual scenarios.

BUILDING CHARACTERISTICS AVAILABLE:
- state, county, climate_zone (North-Central or South-Central)
- vintage, building_type, floor_area, stories, bedrooms, occupants
- heating_fuel (Electricity, Natural Gas, Propane, Fuel Oil, None)
- water_heater_fuel, hvac_type, hvac_has_ducts
- area_median_income (0-30% through 120-150%)
- insulation_wall, insulation_ceiling

Given a task, output a JSON array of chart specs. Each spec describes the chart and the data query:

[
  {
    "title": "Chart Title",
    "description": "What this chart shows",
    "query": "Natural language description of the data needed",
    "chart_type": "bar|line|doughnut|horizontalBar|boxplot|violin",
    "x_key": "column name for labels from the query result",
    "y_key": "column name for values from the query result",
    "group_key": "optional column for grouping/series",
    "x_label": "X axis label with units",
    "y_label": "Y axis label with units"
  }
]

QUERY TIPS:
- For bar charts of energy data: request grouped/aggregated data (e.g. "average heating energy by vintage")
- For boxplot/violin: request raw per-building values of a NUMERIC ENERGY METRIC grouped by a characteristic
  (e.g. "distribution of total energy by heating fuel type")
- For building stock composition (building type, vintage, floor area, heating fuel, etc.):
  request a COUNT/SUMMARY of that characteristic, NOT a distribution.
  Say "count of buildings by floor_area" NOT "raw floor_area values".
  Building characteristics are categorical text, not numeric metrics.
- For doughnut: request counts by category (e.g. "building count by heating fuel")
- For line charts: request data with a sequential grouping (e.g. "energy by vintage decade")

The query result will include a "_tool" field indicating what type of data was returned.
Common result structures:
- Grouped stats: {"data": [{"group": "...", "mean": ..., "count": ...}]}
- Distribution: {"groups": {"cat1": [values], "cat2": [values]}} or {"values": [...]}
- Stock summary: {"data": [{"value": "...", "count": ..., "percentage": ...}]}
- Metric stats: {"mean": ..., "median": ..., "p25": ..., "p75": ..., ...}
- Comparison: {"data": [{"group": "...", "metric1": ..., "metric2": ...}]}

Return ONLY JSON, no markdown fences."""


async def create_visualizations(task: str, context: str = "", log_callback=None) -> list[dict]:
    """Create chart specifications by querying data."""
    async def log(msg):
        logger.info(msg)
        if log_callback:
            await log_callback(msg)

    with tracer.start_as_current_span("create_visualizations") as span:
        span.set_attribute("task", task)

        await log(f"Planning charts for: {task[:80]}")

        plan_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\nContext: {context}"},
        ]

        plan_raw = await chat(plan_messages)
        cleaned = plan_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            chart_specs = json.loads(cleaned)
            if isinstance(chart_specs, dict):
                chart_specs = [chart_specs]
        except json.JSONDecodeError:
            logger.warning("Failed to parse chart plan: %s", cleaned[:200])
            chart_specs = [{
                "title": "Energy Overview",
                "description": task,
                "query": "Distribution statistics for total energy use",
                "chart_type": "bar",
                "x_key": "", "y_key": "",
                "x_label": "", "y_label": "",
            }]

        await log(f"Will generate {len(chart_specs[:10])} chart(s)")

        charts = []
        for idx, spec in enumerate(chart_specs[:10]):
            with tracer.start_as_current_span("generate_chart") as cs:
                title = spec.get("title", "Chart")
                cs.set_attribute("chart.title", title)
                chart_type = spec.get("chart_type", "bar")

                await log(f"Chart {idx+1}: {title}")
                await log(f"  Querying: {spec.get('query', task)[:80]}")

                data_raw = await query_data(spec.get("query", task))
                try:
                    data = json.loads(data_raw)
                    if isinstance(data, dict) and "error" in data:
                        await log(f"  Query error: {data['error'][:60]}")
                        continue
                except json.JSONDecodeError:
                    await log("  Failed to parse query result")
                    continue

                tool_used = data.get("_tool", "")
                chart_data = _build_chartjs_from_tool(data, tool_used, chart_type, spec)

                if chart_data:
                    await log(f"  Chart '{title}' ready")
                    charts.append({
                        "title": title,
                        "description": spec.get("description", ""),
                        "chart_type": chart_type,
                        "chart_data": chart_data,
                        "x_label": spec.get("x_label", ""),
                        "y_label": spec.get("y_label", ""),
                    })
                else:
                    await log(f"  Could not build chart data for '{title}'")

        span.set_attribute("charts.count", len(charts))
        return charts


def _build_chartjs_from_tool(data: dict, tool_name: str, chart_type: str, spec: dict) -> dict | None:
    """Transform tool result into Chart.js-compatible data structure."""
    if not data:
        return None

    if chart_type in ("boxplot", "violin"):
        return _build_boxplot_data(data)

    if tool_name == "metric_by_group":
        return _build_grouped_bar(data, spec)

    if tool_name == "building_stock_summary":
        return _build_summary_chart(data, chart_type)

    if tool_name == "compare_metrics":
        return _build_compare_chart(data)

    if tool_name == "describe_metric":
        return _build_describe_chart(data)

    if tool_name == "distribution":
        return _build_distribution_bar(data)

    if "data" in data and isinstance(data["data"], list) and data["data"]:
        return _build_generic_bar(data, spec)

    return None


def _build_boxplot_data(data: dict) -> dict | None:
    if "groups" in data:
        labels = sorted(data["groups"].keys())
        return {
            "labels": labels,
            "datasets": [{
                "label": data.get("metric", "Value").replace("_", " ").title(),
                "data": [data["groups"][l] for l in labels],
                "backgroundColor": COLORS[0] + "40",
                "borderColor": COLORS[0],
            }],
        }
    if "values" in data:
        return {
            "labels": ["All Buildings"],
            "datasets": [{
                "label": data.get("metric", "Value").replace("_", " ").title(),
                "data": [data["values"]],
                "backgroundColor": COLORS[0] + "40",
                "borderColor": COLORS[0],
            }],
        }
    return None


def _build_grouped_bar(data: dict, spec: dict) -> dict | None:
    rows = data.get("data", [])
    if not rows:
        return None
    x_key = spec.get("x_key", "group")
    y_key = spec.get("y_key", "mean")
    labels = [str(r.get(x_key, r.get("group", ""))) for r in rows]
    values = [round(float(r.get(y_key, r.get("mean", 0)) or 0), 2) for r in rows]
    return {
        "labels": labels,
        "datasets": [{
            "label": data.get("metric", "").replace("_", " ").title(),
            "data": values,
            "backgroundColor": COLORS[:len(values)],
            "borderColor": COLORS[:len(values)],
            "borderWidth": 1,
        }],
    }


def _build_summary_chart(data: dict, chart_type: str) -> dict | None:
    rows = data.get("data", [])
    if not rows:
        return None
    labels = [str(r["value"]) for r in rows]
    values = [r["count"] for r in rows]
    bg = COLORS[:len(values)] if chart_type == "doughnut" else COLORS[0]
    return {
        "labels": labels,
        "datasets": [{
            "label": data.get("column", "").replace("_", " ").title(),
            "data": values,
            "backgroundColor": bg,
            "borderColor": COLORS[:len(values)] if chart_type == "doughnut" else COLORS[0],
            "borderWidth": 1,
        }],
    }


def _build_compare_chart(data: dict) -> dict | None:
    metrics = data.get("metrics", [])
    if not metrics:
        return None

    if "data" in data and isinstance(data["data"], list):
        labels = [str(r.get("group", "")) for r in data["data"]]
        datasets = []
        for i, m in enumerate(metrics):
            values = [round(float(r.get(m, 0) or 0), 2) for r in data["data"]]
            datasets.append({
                "label": m.replace("_", " ").title(),
                "data": values,
                "backgroundColor": COLORS[i % len(COLORS)],
                "borderColor": COLORS[i % len(COLORS)],
                "borderWidth": 1,
            })
        return {"labels": labels, "datasets": datasets}

    if "data" in data and isinstance(data["data"], dict):
        labels = [m.replace("_", " ").title() for m in metrics]
        values = [round(float(data["data"].get(m, {}).get("mean", 0) or 0), 2) for m in metrics]
        return {
            "labels": labels,
            "datasets": [{
                "label": "Mean (MBtu)",
                "data": values,
                "backgroundColor": COLORS[:len(values)],
                "borderColor": COLORS[:len(values)],
                "borderWidth": 1,
            }],
        }
    return None


def _build_describe_chart(data: dict) -> dict | None:
    labels = ["Min", "P25", "Median", "Mean", "P75", "Max"]
    values = [data.get(k, 0) for k in ["min", "p25", "median", "mean", "p75", "max"]]
    values = [round(float(v), 2) if v is not None else 0 for v in values]
    return {
        "labels": labels,
        "datasets": [{
            "label": data.get("metric", "").replace("_", " ").title(),
            "data": values,
            "backgroundColor": COLORS[0],
            "borderColor": COLORS[0],
            "borderWidth": 1,
        }],
    }


def _build_distribution_bar(data: dict) -> dict | None:
    if "groups" in data:
        labels = sorted(data["groups"].keys())
        import statistics as st
        values = [round(st.mean(data["groups"][l]), 2) if data["groups"][l] else 0 for l in labels]
        return {
            "labels": labels,
            "datasets": [{
                "label": data.get("metric", "").replace("_", " ").title(),
                "data": values,
                "backgroundColor": COLORS[:len(values)],
                "borderColor": COLORS[:len(values)],
                "borderWidth": 1,
            }],
        }
    return None


def _build_generic_bar(data: dict, spec: dict) -> dict | None:
    """Fallback for unrecognized tool results that have a data array."""
    rows = data["data"]
    if not rows or not isinstance(rows[0], dict):
        return None
    columns = list(rows[0].keys())
    x_key = spec.get("x_key", columns[0])
    y_key = spec.get("y_key", columns[1] if len(columns) > 1 else columns[0])
    labels = [str(r.get(x_key, "")) for r in rows]
    values = []
    for r in rows:
        try:
            values.append(round(float(r.get(y_key, 0) or 0), 2))
        except (ValueError, TypeError):
            values.append(0)
    return {
        "labels": labels,
        "datasets": [{
            "label": y_key.replace("_", " ").title(),
            "data": values,
            "backgroundColor": COLORS[:len(values)],
            "borderColor": COLORS[:len(values)],
            "borderWidth": 1,
        }],
    }
