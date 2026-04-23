import os


LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    "https://litellm-litemaas.apps.prod.rhoai.rh-aiservices-bu.com/v1",
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/residential_energy.db")

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
  - energy_consumption (REAL): Post-upgrade energy consumption value for this row
  - fuel (TEXT): Fuel type for this end use. Values:
      'electricity', 'natural_gas', 'propane', 'fuel_oil'
  - use (TEXT): End-use category. Values:
      'heating', 'cooling', 'hot_water', 'lighting', 'appliances', 'cooking'
  - time (TEXT): Month in YYYY-MM format, e.g. '2024-01', '2024-02', ... '2024-12'
  - baseline (REAL): Baseline energy consumption (before upgrade) for this building/use/month
  - delta (REAL): Change from baseline (negative = savings, positive = increase).
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

  UPGRADE SCENARIOS (implicit via which rows have non-zero delta):
  Each row represents a specific upgrade applied to a building's end use.
  The upgrade type is inferred from which end-use has a delta:
    - heat_pump_hvac: delta on 'heating' and 'cooling'
    - heat_pump_water_heater: delta on 'hot_water'
    - solar_water_heating: delta on 'hot_water'
    - envelope_upgrade: delta on 'heating' and 'cooling'
    - full_electrification: delta on 'heating', 'cooling', 'hot_water', 'cooking'
    - efficient_lighting: delta on 'lighting'
    - heat_pump_dryer: delta on 'appliances'
    - induction_cooking: delta on 'cooking'

NOTES:
- delta is typically negative (savings). energy_consumption = baseline + delta.
- To get total energy for a building, SUM energy_consumption or baseline grouped by building_id and time.
- To compare scenarios, compare delta values across different end-uses.
- Use GROUP BY state, county, fuel, use, or time for aggregations.
- The table can be large. Always use aggregations and LIMIT.
- ROUND() numeric results to 2 decimal places.
"""
