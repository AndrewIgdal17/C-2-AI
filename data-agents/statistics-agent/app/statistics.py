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

Your workflow:
1. Determine which summary statistics are relevant (mean, median, min, max, percentiles,
   group-by aggregations, comparisons across scenarios, etc.)
2. Formulate data queries as natural language descriptions
3. You'll receive query results as JSON
4. Compute or interpret the statistics
5. Return a structured analysis

When formulating queries, be specific about:
- What aggregations to apply (AVG, SUM, COUNT, etc.)
- What filters (state, fuel type, end-use, time period, etc.)
- What groupings to use (by state, by use, by fuel, etc.)

Return your analysis as JSON with this structure:
{
  "summary": "Plain English summary of findings",
  "statistics": {
    "key_metric_name": value_or_object,
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

Return ONLY the JSON, no markdown fences or explanation outside the JSON."""


async def analyze(task: str, context: str = "") -> dict:
    """Run statistical analysis by querying data and computing stats."""
    with tracer.start_as_current_span("analyze") as span:
        span.set_attribute("task", task)

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
        logger.info("Statistics plan: %s", plan[:300])

        queries = []
        for line in plan.split("\n"):
            line = line.strip()
            if line.upper().startswith("QUERY:"):
                queries.append(line[6:].strip())
            elif line.upper().startswith("- QUERY:"):
                queries.append(line[8:].strip())

        if not queries:
            queries = [task]

        query_results = []
        for q in queries[:5]:
            logger.info("Executing query: %s", q)
            result = await query_data(q)
            query_results.append({"query": q, "result": result})

        results_text = "\n\n".join(
            f"Query: {qr['query']}\nResult: {qr['result'][:3000]}"
            for qr in query_results
        )

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
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM analysis as JSON, wrapping as text")
            return {
                "summary": cleaned,
                "statistics": {},
                "tables": [],
            }
