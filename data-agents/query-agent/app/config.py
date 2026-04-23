import os


LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    "https://litellm-litemaas.apps.prod.rhoai.rh-aiservices-bu.com/v1",
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/tmp/residential_energy.db")

MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8003"))

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"

DATA_DICTIONARY = """
=== RESIDENTIAL ELECTRIFICATION DATA DICTIONARY ===

DATABASE: residential_energy.db

TABLE: upgrade
  One row per building per upgrade scenario per end-use per month.

  COLUMNS:
  - id (INTEGER, PK): Auto-increment row ID
  - building_id (INTEGER): Unique building identifier (500 buildings, IDs 1-500)
  - energy_consumption (REAL): Post-upgrade energy consumption for this row.
      UNITS depend on the 'fuel' column:
        electricity -> kWh (kilowatt-hours)
        natural_gas -> therms
        propane -> gallons
        fuel_oil -> gallons
  - fuel (TEXT): Fuel type for this end use. Values:
      'electricity', 'natural_gas', 'propane', 'fuel_oil'
  - use (TEXT): End-use category. Values:
      'heating', 'cooling', 'hot_water', 'lighting', 'appliances', 'cooking'
  - time (TEXT): Month in YYYY-MM format, e.g. '2024-01' through '2024-12'
  - baseline (REAL): Baseline energy consumption (before upgrade). Same units as energy_consumption.
  - delta (REAL): Energy change from baseline (negative = savings). Same units as energy_consumption.
      energy_consumption = baseline + delta
  - characteristics (TEXT): Building type. Values:
      'single-family_detached', 'single-family_attached', 'mobile_home',
      'multi-family_2-4', 'multi-family_5+'
  - vintage (TEXT): Construction era. Values:
      '<1950', '1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s'
  - occupants (INTEGER): Number of occupants (1-6)
  - county (TEXT): County name (e.g. 'Harris', 'Wake', 'Los Angeles')
  - state (TEXT): US state abbreviation. Values:
      'TX', 'NC', 'CA', 'FL', 'NY', 'GA', 'VA', 'PA', 'IL', 'OH'

  HOW TO QUERY UPGRADE SCENARIOS:
  There is NO 'upgrade_scenario' or 'scenario' column! Upgrades are identified by
  which end-use (the 'use' column) has a non-zero delta. To find rows representing
  an upgrade, filter: WHERE delta != 0 (or delta < 0 for savings).

  To query a specific upgrade type, filter on the 'use' column:
    - Solar water heating / heat pump water heater: WHERE use = 'hot_water' AND delta < 0
    - Heat pump HVAC / envelope upgrade: WHERE use IN ('heating', 'cooling') AND delta < 0
    - Efficient lighting: WHERE use = 'lighting' AND delta < 0
    - Induction cooking: WHERE use = 'cooking' AND delta < 0
    - Heat pump dryer: WHERE use = 'appliances' AND delta < 0
    - Full electrification: WHERE delta < 0 (across multiple end-uses)

  DO NOT try to filter on a column called 'upgrade_scenario' or 'scenario' — it does not exist.

COST ESTIMATION (no cost column in the table — compute from energy values):
  Use these average retail rates to estimate dollar costs and savings:
    electricity:  $0.12 per kWh
    natural_gas:  $1.10 per therm
    propane:      $2.50 per gallon
    fuel_oil:     $3.50 per gallon

  To compute cost savings, multiply delta by the rate for the row's fuel type.
  Example SQL for monthly electricity cost savings:
    SELECT ROUND(AVG(delta) * 0.12, 2) AS avg_monthly_savings_usd
    FROM upgrade WHERE fuel = 'electricity' AND delta < 0

  Example SQL for total annual savings across all fuels:
    SELECT fuel,
      ROUND(SUM(delta) * CASE fuel
        WHEN 'electricity' THEN 0.12
        WHEN 'natural_gas' THEN 1.10
        WHEN 'propane' THEN 2.50
        WHEN 'fuel_oil' THEN 3.50
      END, 2) AS total_savings_usd
    FROM upgrade WHERE delta < 0 GROUP BY fuel

NOTES:
- There is NO separate cost column. All dollar amounts must be computed from energy * rate.
- delta is negative when the upgrade saves energy; energy_consumption = baseline + delta.
- Always include the units in results: kWh, therms, gallons, or USD.
- To get total energy for a building: SUM over building_id and time.
- Use GROUP BY state, county, fuel, use, or time for aggregations.
- Always use aggregations and LIMIT. ROUND() to 2 decimal places.
"""
