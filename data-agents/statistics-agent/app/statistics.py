import json
import logging

from app.llm import chat
from app.mcp_client import query_data
from app.tracing import tracer

logger = logging.getLogger("statistics-agent.statistics")

SYSTEM_PROMPT = """You are a statistics analyst for residential building energy data from NREL's ResStock model.

DATABASE: 14,217 residential buildings in North Carolina, baseline (no upgrades). All energy values are annual MBtu.

ENERGY METRICS AVAILABLE:
- energy_use_total — Total site energy across all fuels
- fuel_electricity_total, fuel_natural_gas_total, fuel_propane_total, fuel_fuel_oil_total — Totals by fuel
- end_use_electricity_heating, end_use_electricity_cooling — Space conditioning
- end_use_electricity_hot_water, end_use_natural_gas_hot_water, end_use_propane_hot_water — Water heating
- end_use_natural_gas_heating — Gas space heating
- end_use_electricity_lighting — Interior lighting
- end_use_electricity_cooling_fans, end_use_electricity_heating_fans — Fan/pump loads

A value of 0.0 means the building does not use that fuel for that end use. Do not exclude zeros.

BUILDING CHARACTERISTICS AVAILABLE:
- state (always NC), county, climate_zone (North-Central or South-Central)
- vintage, building_type, floor_area, stories, bedrooms, occupants
- heating_fuel (Electricity, Natural Gas, Propane, Fuel Oil, None) — most important stratifier
- water_heater_fuel, hvac_type, hvac_has_ducts
- area_median_income (0-30%, 30-60%, 60-80%, 80-100%, 100-120%, 120-150%)
- insulation_wall, insulation_ceiling

Your workflow:
1. Determine which summary statistics are relevant
2. Formulate data queries as natural language descriptions
3. You'll receive query results as JSON
4. Interpret the statistics — always include proper units (MBtu)
5. Return a structured analysis

When formulating queries, describe what you need in plain English. Be specific about:
- Which energy metric you want (use the names above)
- How to group or stratify the results (by which building characteristic)
- Any filters to apply (e.g. "only gas-heated homes", "only North-Central climate zone")
- Whether you need summary statistics, grouped comparisons, or raw distributions

IMPORTANT: Building characteristics (occupants, bedrooms, vintage, heating_fuel, etc.) are NOT energy metrics.
- For counts/percentages of a characteristic: ask for a "building stock summary" or "count by category"
- For numeric stats on occupants/bedrooms/stories: ask for "average/median occupants" or "summary statistics for occupants"
- Do NOT request these as energy metric distributions

ANALYTICAL GUIDELINES:
- Always stratify by heating_fuel when analyzing energy use — gas and electric homes differ fundamentally
- Report distributions (median, percentiles, share with zero), not just means
- All units are annual MBtu
- This is baseline data only — no upgrades applied. Do not answer questions about retrofits, upgrades, savings, or counterfactual scenarios.

Return your analysis as JSON with this structure:
{
  "summary": "Plain English summary with key quantitative findings",
  "statistics": {
    "key_metric_name": number_or_short_string,
    ...
  },
  "tables": [
    {"title": "Table title", "headers": ["col1", "col2"], "rows": [["val1", "val2"], ...]}
  ]
}

FORMATTING RULES:
- "statistics" values must be scalars only (numbers or short strings). These render as headline cards.
- Distributions and breakdowns belong in "tables".
- "summary" must mention key quantitative findings in prose.

Return ONLY the JSON, no markdown fences."""


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
                if isinstance(parsed, dict) and "error" in parsed:
                    await log(f"  -> Error: {parsed['error'][:60]}")
                else:
                    await log(f"  -> Got result ({len(result)} chars)")
            except json.JSONDecodeError:
                await log(f"  -> Got response ({len(result)} chars)")
            query_results.append({"query": q, "result": result})

        query_results = [qr for qr in query_results if '"error"' not in qr["result"][:50]]

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
