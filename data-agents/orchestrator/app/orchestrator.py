import asyncio
import json
import logging

import httpx

from app.config import STATS_AGENT_URL, VIZ_AGENT_URL
from app.llm import chat
from app.tracing import tracer

logger = logging.getLogger("orchestrator.orchestrator")

DECOMPOSE_PROMPT = """You are the orchestrator for a residential electrification data analysis system.
You receive natural language questions about residential building energy data and must decompose
them into sub-tasks for two specialist agents:

1. **Statistics Agent**: Computes summary statistics, comparisons, averages, distributions,
   group-by analyses, etc. Good for numerical answers and data tables.
2. **Visualization Agent**: Creates charts and graphs. Good for visual comparisons, trends,
   distributions, geographic patterns, etc.

The database has a single table called 'upgrade' with one row per building per upgrade
scenario per end-use per month. Key columns:
- building_id, state, county, characteristics (building type), vintage, occupants
- fuel (electricity, natural_gas, propane, fuel_oil)
- use (heating, cooling, hot_water, lighting, appliances, cooking)
- time (month in YYYY-MM format)
- baseline (pre-upgrade energy), delta (change from upgrade, negative = savings)
- energy_consumption (post-upgrade = baseline + delta)

Upgrade types: heat_pump_hvac, heat_pump_water_heater, solar_water_heating,
envelope_upgrade, full_electrification, efficient_lighting, heat_pump_dryer, induction_cooking

For each sub-task, provide a clear, specific instruction that tells the agent exactly what to analyze.

Return JSON with this structure:
{
  "understanding": "Your interpretation of the question in one sentence",
  "stats_task": "Specific task for the Statistics Agent (or null if not needed)",
  "viz_task": "Specific task for the Visualization Agent (or null if not needed)",
  "context": "Any additional context both agents should know"
}

Return ONLY JSON, no markdown fences."""

REPORT_PROMPT = """You are writing a data analysis report for a non-technical audience about
residential building energy and electrification.

You received the following question: {question}

Here are the results from the analysis agents:

STATISTICS:
{stats_summary}

VISUALIZATIONS:
{viz_descriptions}

Write a clear, well-structured report that:
1. Opens with a direct answer to the question in 1-2 sentences
2. Presents the key statistics in context (explain what the numbers mean)
3. References the charts/visualizations that were created
4. Notes any caveats or limitations
5. Keeps the language accessible — no jargon without explanation

Write in plain English. Use paragraphs, not bullet points for the main narrative.
Keep it under 400 words."""


async def _call_stats_agent(task: str, context: str) -> dict:
    """Call the Statistics Sub-Agent."""
    with tracer.start_as_current_span("call_stats_agent") as span:
        span.set_attribute("task", task)
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{STATS_AGENT_URL}/analyze",
                json={"task": task, "context": context},
            )
            resp.raise_for_status()
            result = resp.json()
            span.set_attribute("stats.summary_length", len(result.get("summary", "")))
            return result


async def _call_viz_agent(task: str, context: str) -> dict:
    """Call the Visualization Sub-Agent."""
    with tracer.start_as_current_span("call_viz_agent") as span:
        span.set_attribute("task", task)
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{VIZ_AGENT_URL}/visualize",
                json={"task": task, "context": context},
            )
            resp.raise_for_status()
            result = resp.json()
            span.set_attribute("viz.chart_count", len(result.get("charts", [])))
            return result


async def process_question(question: str):
    """Process a user question: decompose, dispatch, assemble. Yields SSE events."""
    with tracer.start_as_current_span("process_question") as span:
        span.set_attribute("question", question)

        yield _sse_event("status", {"message": "Analyzing your question..."})

        decompose_messages = [
            {"role": "system", "content": DECOMPOSE_PROMPT},
            {"role": "user", "content": question},
        ]
        plan_raw = await chat(decompose_messages)
        cleaned = plan_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            plan = json.loads(cleaned)
        except json.JSONDecodeError:
            plan = {
                "understanding": question,
                "stats_task": question,
                "viz_task": question,
                "context": "",
            }

        understanding = plan.get("understanding", "")
        yield _sse_event("status", {"message": f"I understand: {understanding}"})

        stats_task = plan.get("stats_task")
        viz_task = plan.get("viz_task")
        context = plan.get("context", "")

        tasks = []
        task_names = []
        if stats_task:
            tasks.append(_call_stats_agent(stats_task, context))
            task_names.append("stats")
            yield _sse_event("status", {"message": "Dispatching to Statistics Agent..."})
        if viz_task:
            tasks.append(_call_viz_agent(viz_task, context))
            task_names.append("viz")
            yield _sse_event("status", {"message": "Dispatching to Visualization Agent..."})

        if not tasks:
            yield _sse_event("error", {"message": "Could not determine what to analyze."})
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        stats_result = None
        viz_result = None
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.error("Agent %s failed: %s", name, result)
                yield _sse_event("status", {"message": f"{name} agent encountered an error"})
            elif name == "stats":
                stats_result = result
            elif name == "viz":
                viz_result = result

        yield _sse_event("status", {"message": "Assembling report..."})

        stats_summary = ""
        if stats_result:
            stats_summary = stats_result.get("summary", "")
            if stats_result.get("statistics"):
                stats_summary += f"\n\nKey metrics: {json.dumps(stats_result['statistics'], indent=2)}"
            yield _sse_event("statistics", stats_result)

        viz_descriptions = "No visualizations generated."
        if viz_result and viz_result.get("charts"):
            descs = [c.get("description", c.get("title", "")) for c in viz_result["charts"]]
            viz_descriptions = "\n".join(f"- {d}" for d in descs)
            yield _sse_event("charts", {
                "charts": [
                    {
                        "title": c.get("title", ""),
                        "description": c.get("description", ""),
                        "image_base64": c.get("image_base64", ""),
                    }
                    for c in viz_result["charts"]
                ]
            })

        report_messages = [
            {
                "role": "user",
                "content": REPORT_PROMPT.format(
                    question=question,
                    stats_summary=stats_summary or "No statistics computed.",
                    viz_descriptions=viz_descriptions,
                ),
            },
        ]
        report = await chat(report_messages, temperature=0.3)
        yield _sse_event("report", {"text": report})
        yield _sse_event("done", {})


def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
