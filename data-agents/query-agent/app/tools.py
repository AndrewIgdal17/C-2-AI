import json
import logging

import aiosqlite

from app.config import SQLITE_DB_PATH, DATA_DICTIONARY
from app.llm import chat
from app.tracing import tracer

logger = logging.getLogger("query-agent.tools")

SYSTEM_PROMPT = f"""You are a SQL expert for a residential electrification energy database (SQLite).
Your job is to translate natural language data requests into valid SQLite SQL queries.

{DATA_DICTIONARY}

RULES:
- Return ONLY the SQL query, no explanation, no markdown fences.
- Use only columns from the 'upgrade' table described above.
- There is only ONE table called 'upgrade'. Do NOT reference any other tables.
- Use aggregations (AVG, SUM, MAX, COUNT) with GROUP BY when the request asks for summaries or comparisons. If the request asks for individual values, distributions, or raw data, return individual rows without aggregation.
- Limit results to 200 rows max for aggregated queries. For queries that return individual rows without GROUP BY, limit to 10000 rows.
- Use ROUND() for numeric results to 2 decimal places.
- delta is negative = savings. energy_consumption = baseline + delta.
- UNITS: electricity=kWh, natural_gas=therms, propane=gallons, fuel_oil=gallons. Include units in column aliases (e.g. "avg_delta_kwh"), never concatenate unit strings into data values.
- COST QUESTIONS: There is NO cost column. Compute costs using CASE:
    delta * CASE fuel WHEN 'electricity' THEN 0.12 WHEN 'natural_gas' THEN 1.10
    WHEN 'propane' THEN 2.50 WHEN 'fuel_oil' THEN 3.50 END
  For cost savings, multiply negative delta by the rate (result will be negative = savings).
- To compare upgrades, look at AVG(delta) or SUM(delta) grouped by use, state, etc.
- If the request is ambiguous, make reasonable assumptions and proceed."""


async def _execute_query(sql: str) -> list[dict]:
    """Execute a SQL query and return results as a list of dicts."""
    async with aiosqlite.connect(SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return []
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


async def query_data(description: str) -> str:
    """Translate a natural language data request into SQL, execute it, and return JSON results.

    Args:
        description: A natural language description of the data you need.
                     Example: "Average monthly electricity cost by state for baseline scenario"
    """
    with tracer.start_as_current_span("query_data") as span:
        span.set_attribute("query.description", description)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ]
        sql = (await chat(messages)).strip()
        sql = sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        span.set_attribute("query.sql", sql)
        logger.info("Generated SQL: %s", sql)

        try:
            results = await _execute_query(sql)
            span.set_attribute("query.row_count", len(results))
            return json.dumps(results, default=str)
        except Exception as exc:
            logger.error("SQL execution failed: %s — SQL: %s", exc, sql)
            span.set_attribute("query.error", str(exc))
            return json.dumps({"error": str(exc), "sql": sql})


async def execute_sql(sql: str) -> str:
    """Execute a raw SQL query directly against the database and return JSON results.

    Args:
        sql: A valid SQLite SQL query to execute.
    """
    with tracer.start_as_current_span("execute_sql") as span:
        span.set_attribute("query.sql", sql)
        try:
            results = await _execute_query(sql)
            span.set_attribute("query.row_count", len(results))
            return json.dumps(results, default=str)
        except Exception as exc:
            logger.error("SQL execution failed: %s — SQL: %s", exc, sql)
            span.set_attribute("query.error", str(exc))
            return json.dumps({"error": str(exc), "sql": sql})


async def list_tables() -> str:
    """List all tables in the database."""
    with tracer.start_as_current_span("list_tables"):
        results = await _execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return json.dumps([r["name"] for r in results])


async def describe_table(table_name: str) -> str:
    """Get column info and sample data for a specific table.

    Args:
        table_name: Name of the table to describe.
    """
    with tracer.start_as_current_span("describe_table") as span:
        span.set_attribute("table.name", table_name)
        safe_name = table_name.replace('"', '').replace("'", "").replace(";", "")

        schema = await _execute_query(f'PRAGMA table_info("{safe_name}")')
        count_result = await _execute_query(f'SELECT COUNT(*) as cnt FROM "{safe_name}"')
        sample = await _execute_query(f'SELECT * FROM "{safe_name}" LIMIT 5')

        return json.dumps({
            "table": safe_name,
            "columns": schema,
            "row_count": count_result[0]["cnt"] if count_result else 0,
            "sample_rows": sample,
        }, default=str)


async def get_schema() -> str:
    """Return the full data dictionary describing all tables, columns, types, and units."""
    return DATA_DICTIONARY
