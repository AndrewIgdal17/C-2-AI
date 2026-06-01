import json
import logging

from app.llm import chat
from app.mcp_client import query_data
from app.tracing import tracer

logger = logging.getLogger("visualization-agent.visualize")

COLORS = ['#5b8def', '#FF5722', '#4CAF50', '#FFC107', '#9C27B0', '#00BCD4', '#E91E63', '#8BC34A']

SYSTEM_PROMPT = """You are a data visualization expert for residential energy and electrification data.
You have a database with a single 'upgrade' table: building_id, energy_consumption, fuel,
use (heating/cooling/hot_water/lighting/appliances/cooking), time (YYYY-MM), baseline,
delta (negative=savings), characteristics, vintage, occupants, county, state.

UNITS: electricity=kWh, natural_gas=therms, propane=gallons, fuel_oil=gallons.
There is NO upgrade_scenario column. Filter by: use column + delta < 0.

Given a task, output a JSON array of chart specs. Each chart must include:
- A data query that returns rows with clear column names
- The column to use for labels (x axis) and values (y axis)
- Optionally a group column for grouped/stacked charts

[
  {
    "title": "Chart Title",
    "description": "What this chart shows",
    "query": "Natural language data query for the database",
    "chart_type": "bar|line|doughnut|horizontalBar|boxplot|violin",
    "x_key": "column name from query results for labels",
    "y_key": "column name from query results for values",
    "group_key": "optional column name for grouping/series",
    "x_label": "X axis label with units",
    "y_label": "Y axis label with units"
  }
]

For boxplot or violin charts:
- The query must return enough data points for a meaningful distribution (at least 20+ values per category).
- x_key is the category column (e.g. state, fuel, vintage).
- y_key is the numeric column whose distribution you want to show.
- Aggregation is fine if the result still has many rows (e.g. GROUP BY building_id to get one total per building, then boxplot across buildings).
- The frontend computes min, q1, median, q3, max, and outliers automatically from the raw values.

Return ONLY JSON, no markdown fences."""


async def create_visualizations(task: str, context: str = "", log_callback=None) -> list[dict]:
    """Create chart specifications by querying data and structuring it for frontend rendering."""
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
                "title": "Data Overview",
                "description": task,
                "query": task,
                "chart_type": "bar",
                "x_key": "", "y_key": "",
                "x_label": "", "y_label": "",
            }]

        await log(f"Will generate {len(chart_specs[:3])} chart(s)")

        charts = []
        for idx, spec in enumerate(chart_specs[:10]):
            with tracer.start_as_current_span("generate_chart") as cs:
                title = spec.get("title", "Chart")
                cs.set_attribute("chart.title", title)

                await log(f"Chart {idx+1}: {title}")
                await log(f"  Querying data: {spec.get('query', task)[:80]}")

                data_raw = await query_data(spec.get("query", task))
                try:
                    data = json.loads(data_raw)
                    if isinstance(data, dict) and "error" in data:
                        await log(f"  Query error: {data['error'][:60]}")
                        continue
                except json.JSONDecodeError:
                    await log("  Failed to parse query result")
                    continue

                if not data:
                    await log(f"  No data returned for chart: {title}")
                    continue

                await log(f"  Got {len(data)} data points, building chart data...")

                columns = list(data[0].keys())
                x_key = spec.get("x_key", columns[0] if columns else "")
                y_key = spec.get("y_key", columns[1] if len(columns) > 1 else columns[0])
                group_key = spec.get("group_key")
                chart_type = spec.get("chart_type", "bar")

                chart_data = _build_chartjs_data(
                    data, chart_type, x_key, y_key, group_key
                )

                if chart_data:
                    await log(f"  Chart '{title}' ready ({len(data)} points)")
                    charts.append({
                        "title": title,
                        "description": spec.get("description", ""),
                        "chart_type": chart_type,
                        "chart_data": chart_data,
                        "x_label": spec.get("x_label", x_key.replace("_", " ").title()),
                        "y_label": spec.get("y_label", y_key.replace("_", " ").title()),
                    })

        span.set_attribute("charts.count", len(charts))
        return charts


def _build_chartjs_data(data: list[dict], chart_type: str, x_key: str, y_key: str,
                        group_key: str = None) -> dict | None:
    """Transform query results into Chart.js-compatible data structure."""
    if not data:
        return None

    columns = list(data[0].keys())
    if x_key not in data[0]:
        x_key = columns[0] if columns else ""
    if y_key not in data[0]:
        y_key = columns[1] if len(columns) > 1 else columns[0]

    if not x_key or not y_key:
        return None

    if chart_type in ("boxplot", "violin"):
        from collections import defaultdict
        groups = defaultdict(list)
        for row in data:
            try:
                groups[str(row[x_key])].append(float(row[y_key]))
            except (ValueError, TypeError):
                continue
        labels = sorted(groups.keys())
        return {
            "labels": labels,
            "datasets": [{
                "label": y_key.replace("_", " ").title(),
                "data": [groups[label] for label in labels],
                "backgroundColor": COLORS[0] + "40",
                "borderColor": COLORS[0],
            }],
        }

    if group_key and group_key in data[0]:
        groups = sorted(set(str(row[group_key]) for row in data))
        labels = sorted(set(str(row[x_key]) for row in data))

        datasets = []
        for i, grp in enumerate(groups):
            values = []
            for label in labels:
                matches = [row[y_key] for row in data
                           if str(row[x_key]) == label and str(row[group_key]) == grp]
                values.append(round(float(matches[0]), 2) if matches else 0)
            datasets.append({
                "label": str(grp),
                "data": values,
                "backgroundColor": COLORS[i % len(COLORS)],
                "borderColor": COLORS[i % len(COLORS)],
                "borderWidth": 1,
            })

        return {"labels": labels, "datasets": datasets}
    else:
        labels = [str(row[x_key]) for row in data]
        values = [round(float(row[y_key]), 2) if row[y_key] is not None else 0 for row in data]

        return {
            "labels": labels,
            "datasets": [{
                "label": y_key.replace("_", " ").title(),
                "data": values,
                "backgroundColor": COLORS[:len(values)] if chart_type in ("bar", "doughnut", "horizontalBar") else COLORS[0],
                "borderColor": COLORS[:len(values)] if chart_type == "doughnut" else COLORS[0],
                "borderWidth": chart_type == "line" and 2 or 1,
                "fill": chart_type == "line",
                "tension": 0.3,
            }],
        }
