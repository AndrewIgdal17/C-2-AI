# C2AI — Agent Instructions

Multi-agent LLM system for natural language queries over residential electrification data.
PyData London, June 7 2026. Built by Andy Igdal and Cedric Clyburn (Red Hat).

## Repo layout

- `data-agents/` — the active project (all work happens here)
- `ai-virtual-agent-dev-EXAMPLE/` — Red Hat OpenShift AI quickstart that served as the starting template. Reference only — do not modify.
- `FRONTEND_STYLE_GUIDE.md` — Vercel/Geist design system spec for the frontend UI

## Architecture

Five services, all communicating via HTTP:

| Service | Port | Entry point | Role |
|---|---|---|---|
| Orchestrator | 8000 | `data-agents/orchestrator/app/main.py` | Receives NL question (POST /api/chat), decomposes into sub-tasks, dispatches to stats + viz agents, assembles final report via SSE |
| Statistics Agent | 8001 | `data-agents/statistics-agent/app/main.py` | Decides what stats to compute, calls query agent for data, returns JSON summary |
| Visualization Agent | 8002 | `data-agents/visualization-agent/app/main.py` | Decides what to plot, calls query agent for data, returns Chart.js-compatible data |
| Query Agent (MCP) | 8003 | `data-agents/query-agent/app/main.py` | FastMCP server; translates NL data requests to SQL, executes against SQLite, returns JSON |
| Frontend | 3000 | `data-agents/frontend/index.html` | Chat UI served by nginx; renders charts via Chart.js 4.x |

Observability: OpenTelemetry traces flow through an OTel Collector (gRPC :4317) to Grafana Tempo, visualized in Grafana (:3001).

Key invariant: sub-agents never touch SQLite directly. All data access goes through the query agent MCP server.

## Data model

Single table: `upgrade`. One row per building x end-use x month.

| Column | Type | Notes |
|---|---|---|
| building_id | INTEGER | 500 buildings (IDs 1-500) |
| energy_consumption | REAL | Post-upgrade; units depend on fuel |
| fuel | TEXT | electricity (kWh), natural_gas (therms), propane (gal), fuel_oil (gal) |
| use | TEXT | heating, cooling, hot_water, lighting, appliances, cooking |
| time | TEXT | YYYY-MM (2024-01 through 2024-12) |
| baseline | REAL | Pre-upgrade energy, same units |
| delta | REAL | Change from baseline (negative = savings); energy_consumption = baseline + delta |
| characteristics | TEXT | single-family_detached, single-family_attached, mobile_home, multi-family_2-4, multi-family_5+ |
| vintage | TEXT | <1950 through 2010s |
| occupants | INTEGER | 1-6 |
| county | TEXT | County name |
| state | TEXT | TX, NC, CA, FL, NY, GA, VA, PA, IL, OH |

No upgrade scenario column. Upgrades are identified by delta != 0 on the use column.

No cost column. Costs computed via fuel-specific rates in the query agent system prompt:
electricity $0.12/kWh, natural_gas $1.10/therm, propane $2.50/gal, fuel_oil $3.50/gal.

## Local development

```bash
cd data-agents
cp .env.example .env
# Set LLM_API_KEY in .env

cd deploy/local
docker compose up --build

# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
# Grafana:   http://localhost:3001
```

## Where agent behavior is defined

All agent intelligence lives in four system prompt strings — no config files, no recipe system:

| Prompt | File | Line | What it controls |
|---|---|---|---|
| DECOMPOSE_PROMPT | orchestrator/app/orchestrator.py | 14 | How user questions are split into stats_task + viz_task |
| REPORT_PROMPT | orchestrator/app/orchestrator.py | 52 | How the final written report is framed |
| SYSTEM_PROMPT | statistics-agent/app/statistics.py | 10 | What statistics to compute and how to formulate data queries |
| SYSTEM_PROMPT | visualization-agent/app/visualize.py | 12 | What charts to produce (Chart.js spec format) |

The query agent also has a system prompt (query-agent/app/tools.py line 12) that controls NL-to-SQL translation, plus a data dictionary in query-agent/app/config.py (line 20).

## Query agent MCP tools

The query agent exposes five tools via FastMCP (streamable-http):

| Tool | Purpose |
|---|---|
| query_data(description) | NL description -> LLM generates SQL -> execute -> JSON results |
| execute_sql(sql) | Run raw SQL directly |
| list_tables() | List all tables |
| describe_table(table_name) | Column info + sample rows |
| get_schema() | Full data dictionary text |

## Frontend chart types

Chart.js 4.x renders these types (defined in app.js mapChartType, line 502):
bar, line, doughnut, horizontalBar, grouped_bar, stacked_bar.

There is no histogram type. For distribution charts, request pre-binned data from the query agent.

## Sharp edges

- data-agents/README.md schema section is stale — documents three tables (buildings, energy_consumption, hourly_loads) but code uses a single upgrade table.
- Default LLM_API_BASE points to Red Hat internal infrastructure. Outside Red Hat, set a different OpenAI-compatible endpoint.
- No .gitignore in data-agents/ — .env files are not gitignored at the repo root.
- No automated test suite.
