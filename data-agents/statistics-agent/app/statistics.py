import json
import logging

from app.llm import chat
from app.mcp_client import query_data, execute_sql, get_schema
from app.tracing import tracer

logger = logging.getLogger("statistics-agent.statistics")

SYSTEM_PROMPT = """You are a statistics analyst for residential energy and electrification data.
You receive a task describing what statistics to compute. You have access to a database
with a single table called 'upgrade' containing building energy data across upgrade scenarios.

Key columns: building_id, energy_consumption, fuel, use (end-use like heating/cooling/hot_water),
time (YYYY-MM), baseline, delta (change from upgrade, negative=savings), characteristics
(building type), vintage, occupants, county, state.

UNITS by fuel type: electricity=kWh, natural_gas=therms, propane=gallons, fuel_oil=gallons.
COST RATES (no cost column exists — compute from energy * rate):
  electricity: $0.12/kWh, natural_gas: $1.10/therm, propane: $2.50/gallon, fuel_oil: $3.50/gallon.
For dollar/cost questions, ask for energy delta and multiply by the rate.
Example query: "Average delta for electricity hot_water in TX, also compute delta * 0.12 as cost_savings_usd"

Your workflow:
1. Determine which summary statistics are relevant
2. Formulate data queries as natural language descriptions
3. You'll receive query results as JSON
4. Compute or interpret the statistics — always include proper units (kWh, therms, USD, etc.)
5. Return a structured analysis

When formulating queries, be specific about:
- What aggregations to apply (AVG, SUM, COUNT, etc.)
- What filters (state, fuel type, end-use, time period, etc.)
- What groupings to use (by state, by use, by fuel, etc.)
- For cost questions: ask the query to multiply delta by the fuel rate in the SQL

Return your analysis as JSON with this structure:
{
  "summary": "Plain English summary of findings",
  "statistics": {
    "key_metric_name": number_or_short_string,
    ...
  },
  "tables": [
    {
      "title": "Table title",
      "headers": ["col1", "col2"],
      "rows": [["val1", "val2"], ...]
    }
  ]
}

FORMATTING RULES:
- "statistics" values must be scalars only (numbers or short strings). These render as headline cards. Never put objects, arrays, or distributions here.
- Distributions and breakdowns belong in "tables".
- "summary" must mention the key quantitative findings (medians, percentages, totals) in prose, because downstream consumers read "summary" but not "tables".

Return ONLY the JSON, no markdown fences or explanation outside the JSON."""


async def analyze(task: str, context: str = "", log_callback=None):
    """Run statistical analysis. log_callback(msg) is called for progress updates."""
    async def log(msg):
        logger.info(msg)
        if log_callback:
            await log_callback(msg)

    with tracer.start_as_current_span("analyze") as span:
        span.set_attribute("task", task)

        await log(f"Planning analysis for: {task[:100]}")

        planning_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Additional context: {context}\n\n"
                    "First, plan what data queries you need. List each query as a "
                    "natural language description, one per line, prefixed with 'QUERY: '. "
                    "Then I will fetch the data and you can compute statistics."
                ),
            },
        ]

        plan = await chat(planning_messages)
        span.set_attribute("plan", plan[:500])

        queries = []
        for line in plan.split("\n"):
            line = line.strip()
            if line.upper().startswith("QUERY:"):
                queries.append(line[6:].strip())
            elif line.upper().startswith("- QUERY:"):
                queries.append(line[8:].strip())

        if not queries:
            queries = [task]

        await log(f"Planned {len(queries)} data queries")

        query_results = []
        for i, q in enumerate(queries[:10]):
            await log(f"Query {i+1}/{min(len(queries),10)}: {q[:80]}")
            result = await query_data(q)
            try:
                parsed = json.loads(result)
                row_count = len(parsed) if isinstance(parsed, list) else 0
                await log(f"  -> Got {row_count} rows")
            except json.JSONDecodeError:
                await log(f"  -> Got response ({len(result)} chars)")
            query_results.append({"query": q, "result": result})

        results_text = "\n\n".join(
            f"Query: {qr['query']}\nResult: {qr['result'][:3000]}"
            for qr in query_results
        )

        await log("Computing statistics from query results...")

        analysis_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Here are the query results:\n\n{results_text}\n\n"
                    "Now compute the statistics and return the JSON analysis."
                ),
            },
        ]

        analysis_raw = await chat(analysis_messages)
        span.set_attribute("analysis_length", len(analysis_raw))

        cleaned = analysis_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            await log(f"Analysis complete: {result.get('summary', '')[:80]}")
            return result
        except json.JSONDecodeError:
            await log("Analysis complete (text format)")
            return {
                "summary": cleaned,
                "statistics": {},
                "tables": [],
            }
