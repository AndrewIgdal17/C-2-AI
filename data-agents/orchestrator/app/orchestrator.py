import asyncio
import json
import logging
import time

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

UNITS: electricity=kWh, natural_gas=therms, propane=gallons, fuel_oil=gallons.
COST: No cost column exists. Costs are computed from energy using rates:
  electricity=$0.12/kWh, natural_gas=$1.10/therm, propane=$2.50/gal, fuel_oil=$3.50/gal.
For cost/dollar questions, tell agents to compute cost = energy * rate.

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

Question: {question}

Statistics from analysis:
{stats_summary}

Visualizations created:
{viz_descriptions}

CRITICAL RULES:
- Always include units: kWh for electricity, therms for natural gas, gallons for propane/fuel oil, USD for costs.
- Never say "units" generically. Say "kWh", "therms", "$X.XX", etc.
- Costs are estimated at: electricity $0.12/kWh, natural_gas $1.10/therm, propane $2.50/gal, fuel_oil $3.50/gal.
- If the statistics include cost data, present it prominently.
- If they don't include cost data but the user asked about costs, compute approximate dollar amounts from the energy values and rates above.
- Your output must be plain English prose only. Do not echo or repeat the raw data you were given as input.

Write a clear, well-structured report that:
1. Opens with a direct answer in 1-2 sentences, with specific numbers and units
2. Presents key statistics in context
3. References any charts/visualizations created
4. Notes caveats briefly (1-2 sentences max)

Write in plain English paragraphs. Keep it under 300 words. Be concise and specific."""


async def _call_agent_streaming(url: str, payload: dict, agent_name: str, event_queue: asyncio.Queue):
    """Call a sub-agent with stream=True, retrying on 503 (Knative cold start)."""
    payload["stream"] = True
    result = None
    t0 = time.time()

    max_retries = 12
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", url, json=payload,
                                         headers={"Accept": "text/event-stream"}) as resp:
                    if resp.status_code == 503:
                        raise httpx.HTTPStatusError("503", request=resp.request, response=resp)
                    resp.raise_for_status()
                    event_type = None
                    try:
                        async for line in resp.aiter_lines():
                            line = line.strip()
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:") and event_type:
                                try:
                                    data = json.loads(line[5:].strip())
                                except json.JSONDecodeError:
                                    event_type = None
                                    continue
                                if event_type == "log":
                                    await event_queue.put(("log", agent_name, data.get("message", "")))
                                elif event_type == "result":
                                    result = data
                                    elapsed = round(time.time() - t0, 1)
                                    await event_queue.put(("log", agent_name, f"Completed in {elapsed}s"))
                                elif event_type == "error":
                                    await event_queue.put(("log", agent_name, f"Error: {data.get('error', 'unknown')}"))
                                event_type = None
                    except httpx.RemoteProtocolError:
                        if result:
                            pass
                        else:
                            result = await _call_agent_sync(url, payload, agent_name, event_queue)
            break

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadError) as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', 0)
            if status in (503, 502, 0) or isinstance(exc, (httpx.ConnectError, httpx.ReadError)):
                wait = min(1 + attempt * 2, 8)
                if attempt == 0:
                    await event_queue.put(("log", agent_name, "Waiting for agent to start (cold start)..."))
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                    continue
            if not result:
                await event_queue.put(("log", agent_name, f"Streaming failed, trying sync..."))
                result = await _call_agent_sync(url, payload, agent_name, event_queue)
            break

        except Exception as exc:
            if not result:
                await event_queue.put(("log", agent_name, f"Streaming failed, trying sync..."))
                result = await _call_agent_sync(url, payload, agent_name, event_queue)
            break

    await event_queue.put(("done", agent_name, result))
    return result


async def _call_agent_sync(url: str, payload: dict, agent_name: str, event_queue: asyncio.Queue):
    """Fallback: call a sub-agent without streaming, with retry for cold start."""
    payload["stream"] = False
    for attempt in range(12):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in (503, 502):
                    await asyncio.sleep(min(1 + attempt * 2, 8))
                    continue
                resp.raise_for_status()
                result = resp.json()
                await event_queue.put(("log", agent_name, "Completed (sync)"))
                return result
        except (httpx.ConnectError, httpx.ReadError):
            await asyncio.sleep(min(1 + attempt * 2, 8))
            continue
        except Exception as exc:
            await event_queue.put(("log", agent_name, f"Agent call failed: {type(exc).__name__}"))
            return None
    await event_queue.put(("log", agent_name, "Agent unavailable after retries"))
    return None


async def process_question(question: str):
    """Process a user question: decompose, dispatch, assemble. Yields SSE events."""
    with tracer.start_as_current_span("process_question") as span:
        span.set_attribute("question", question)
        t_start = time.time()

        yield _sse("log", "orchestrator", "Analyzing your question...")

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
        yield _sse("log", "orchestrator", f"Understood: {understanding}")

        stats_task = plan.get("stats_task")
        viz_task = plan.get("viz_task")
        context = plan.get("context", "")

        event_queue = asyncio.Queue()
        agent_tasks = []
        expected_agents = set()

        if stats_task:
            yield _sse("log", "orchestrator", f"Dispatching to Statistics Agent: {stats_task[:80]}")
            agent_tasks.append(asyncio.create_task(
                _call_agent_streaming(f"{STATS_AGENT_URL}/analyze",
                                      {"task": stats_task, "context": context},
                                      "statistics", event_queue)
            ))
            expected_agents.add("statistics")

        if viz_task:
            yield _sse("log", "orchestrator", f"Dispatching to Visualization Agent: {viz_task[:80]}")
            agent_tasks.append(asyncio.create_task(
                _call_agent_streaming(f"{VIZ_AGENT_URL}/visualize",
                                      {"task": viz_task, "context": context},
                                      "visualization", event_queue)
            ))
            expected_agents.add("visualization")

        if not agent_tasks:
            yield _sse("log", "orchestrator", "Could not determine what to analyze.")
            yield _sse_event("error", {"message": "Could not determine what to analyze."})
            return

        # Relay events from sub-agents in real-time
        stats_result = None
        viz_result = None
        done_agents = set()

        while done_agents != expected_agents:
            try:
                item = await asyncio.wait_for(event_queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

            event_type, agent_name, payload = item
            if event_type == "log":
                yield _sse("log", agent_name, payload)
            elif event_type == "done":
                done_agents.add(agent_name)
                if agent_name == "statistics" and payload:
                    stats_result = payload
                elif agent_name == "visualization" and payload:
                    viz_result = payload

        # Emit structured results
        yield _sse("log", "orchestrator", "All agents finished. Assembling report...")

        stats_summary = ""
        if stats_result:
            stats_summary = stats_result.get("summary", "")
            if stats_result.get("statistics"):
                stats_summary += f"\n\nKey metrics: {json.dumps(stats_result['statistics'], indent=2)}"
            yield _sse_event("statistics", stats_result)

        viz_descriptions = "No visualizations generated."
        if viz_result and viz_result.get("charts"):
            charts = viz_result["charts"]
            descs = [c.get("description", c.get("title", "")) for c in charts]
            viz_descriptions = "\n".join(f"- {d}" for d in descs)
            yield _sse_event("charts", {
                "charts": [
                    {
                        "title": c.get("title", ""),
                        "description": c.get("description", ""),
                        "chart_type": c.get("chart_type", "bar"),
                        "chart_data": c.get("chart_data"),
                        "x_label": c.get("x_label", ""),
                        "y_label": c.get("y_label", ""),
                        "image_base64": c.get("image_base64", ""),
                    }
                    for c in charts
                ]
            })

        yield _sse("log", "orchestrator", "Writing final report...")

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

        elapsed = round(time.time() - t_start, 1)
        yield _sse("log", "orchestrator", f"Done ({elapsed}s total)")
        yield _sse_event("done", {})


def _sse(event_type: str, agent: str, message: str) -> str:
    """Emit a structured log event with agent name."""
    data = json.dumps({"agent": agent, "message": message})
    payload = f"event: {event_type}\ndata: {data}\n\n"
    if len(payload) < 256:
        payload += f": {'.' * (256 - len(payload))}\n\n"
    return payload


def _sse_event(event_type: str, data: dict) -> str:
    payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    if len(payload) < 256:
        payload += f": {'.' * (256 - len(payload))}\n\n"
    return payload
