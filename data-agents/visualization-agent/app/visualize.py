import base64
import io
import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.llm import chat
from app.mcp_client import query_data
from app.tracing import tracer

logger = logging.getLogger("visualization-agent.visualize")

SYSTEM_PROMPT = """You are a data visualization expert for residential energy and electrification data.
You receive a task describing what visualizations to create. You have access to a database
with a single 'upgrade' table: building_id, energy_consumption, fuel, use (heating/cooling/hot_water/
lighting/appliances/cooking), time (YYYY-MM), baseline, delta (negative=savings), characteristics,
vintage, occupants, county, state.

Your workflow:
1. Determine what chart types are appropriate (bar, grouped bar, line/time series,
   histogram, box plot, heatmap, scatter, stacked bar, etc.)
2. Formulate data queries as natural language descriptions
3. You'll receive query results as JSON arrays of objects
4. Write matplotlib Python code to generate each chart

When formulating queries, be specific about aggregations, groupings, and filters.

For your response, output a JSON array of chart specifications:
[
  {
    "title": "Chart Title",
    "description": "What this chart shows",
    "query": "Natural language data query",
    "chart_type": "bar|line|histogram|scatter|heatmap|box|stacked_bar",
    "code_hint": "Brief note about how to structure the matplotlib code"
  }
]

Return ONLY the JSON array, no markdown fences."""

CHART_CODE_PROMPT = """Write matplotlib Python code to create a chart.
The data is available as a Python variable called `data` which is a list of dicts.

Requirements:
- Use plt.figure(figsize=(10, 6)) for sizing
- Set a descriptive title, axis labels, and legend where appropriate
- Use a clean style: plt.style.use('seaborn-v0_8-whitegrid') if available
- Use colors from this palette: ['#2196F3', '#FF5722', '#4CAF50', '#FFC107', '#9C27B0', '#00BCD4']
- Rotate x-axis labels 45 degrees if there are more than 5 categories
- Call plt.tight_layout() at the end
- Save the figure to a variable called `fig` (fig = plt.gcf())
- Do NOT call plt.show() or plt.savefig()

Chart specification:
- Title: {title}
- Type: {chart_type}
- Description: {description}
- Hint: {code_hint}

Sample data (first 3 rows): {sample_data}
All column names: {columns}

Return ONLY Python code, no markdown fences or explanation."""


def _execute_chart_code(code: str, data: list[dict]) -> str | None:
    """Execute matplotlib code and return base64 PNG, or None on failure."""
    try:
        plt.close("all")
        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except Exception:
            pass

        local_vars = {
            "data": data,
            "plt": plt,
            "np": np,
            "json": json,
        }
        exec(code, {"__builtins__": __builtins__}, local_vars)

        fig = local_vars.get("fig", plt.gcf())
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close("all")
        return b64
    except Exception as exc:
        logger.error("Chart code execution failed: %s", exc)
        plt.close("all")
        return None


async def create_visualizations(task: str, context: str = "") -> list[dict]:
    """Create visualizations for the given task."""
    with tracer.start_as_current_span("create_visualizations") as span:
        span.set_attribute("task", task)

        plan_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Task: {task}\nAdditional context: {context}",
            },
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
        except json.JSONDecodeError:
            logger.warning("Failed to parse chart plan, attempting single chart")
            chart_specs = [{
                "title": "Data Visualization",
                "description": task,
                "query": task,
                "chart_type": "bar",
                "code_hint": "Create an appropriate chart for the data",
            }]

        charts = []
        for spec in chart_specs[:3]:
            with tracer.start_as_current_span("generate_chart") as chart_span:
                chart_span.set_attribute("chart.title", spec.get("title", ""))

                query_desc = spec.get("query", task)
                data_raw = await query_data(query_desc)

                try:
                    data = json.loads(data_raw)
                    if isinstance(data, dict) and "error" in data:
                        logger.error("Query error: %s", data["error"])
                        continue
                except json.JSONDecodeError:
                    logger.error("Failed to parse query result")
                    continue

                if not data:
                    logger.warning("Empty data for chart: %s", spec.get("title"))
                    continue

                sample = data[:3]
                columns = list(data[0].keys()) if data else []

                code_messages = [
                    {
                        "role": "user",
                        "content": CHART_CODE_PROMPT.format(
                            title=spec.get("title", "Chart"),
                            chart_type=spec.get("chart_type", "bar"),
                            description=spec.get("description", ""),
                            code_hint=spec.get("code_hint", ""),
                            sample_data=json.dumps(sample),
                            columns=columns,
                        ),
                    },
                ]

                code_raw = await chat(code_messages)
                code = code_raw.strip()
                if code.startswith("```"):
                    code = code.split("\n", 1)[-1]
                if code.endswith("```"):
                    code = code.rsplit("```", 1)[0]
                code = code.strip()

                image_b64 = _execute_chart_code(code, data)
                if image_b64:
                    charts.append({
                        "title": spec.get("title", "Chart"),
                        "description": spec.get("description", ""),
                        "image_base64": image_b64,
                    })

        span.set_attribute("charts.count", len(charts))
        return charts
