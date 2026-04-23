# Residential Electrification Data Agent System

A multi-agent LLM system that lets non-technical users ask natural language questions about
messy residential electrification data and receive written reports with summary statistics
and data visualizations.

Built for the conference talk: **"What Can LLMs Do with Messy Residential Electrification Data?"**

## Architecture

```
┌─────────────────────────────────┐
│     Orchestrator Agent          │  ← User-facing. Receives NL question,
│     (FastAPI, always-on)        │     decomposes it, dispatches to sub-agents,
│                                 │     assembles final report.
└──────┬──────────────┬───────────┘
       │              │
       ▼              ▼
┌──────────────┐ ┌──────────────┐
│  Statistics  │ │ Visualization│  ← Sub-agents (Knative, scale-to-zero)
│  Sub-Agent   │ │  Sub-Agent   │     Each decides WHAT to compute/plot,
│  (FastAPI)   │ │  (FastAPI)   │     then delegates data access to the
└──────┬───────┘ └──────┬───────┘     Query Agent below.
       │              │
       ▼              ▼
    ┌─────────────────────┐
    │   Query Sub-Agent   │  ← MCP Server (Knative, scale-to-zero).
    │   (FastMCP)         │     Translates to SQL, executes, returns JSON.
    └─────────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │   SQLite Database   │  ← Pre-loaded with residential energy data.
    │   (container)       │
    └─────────────────────┘
```

All agents communicate via HTTP. The Query Agent exposes an MCP server (Model Context Protocol)
over streamable-http. OpenTelemetry traces flow through an OTel Collector to Grafana Tempo,
visualized in Grafana.

## Quick Start (Local with Docker Compose)

### Prerequisites

- Docker and Docker Compose (or Podman with compose)
- An API key for the LLM endpoint

### Steps

```bash
# 1. Clone and navigate
cd data-agents

# 2. Configure environment
cp .env.example .env
# Edit .env and set LLM_API_KEY

# 3. Start all services
cd deploy/local
docker compose up --build

# 4. Open the UI
# Frontend:  http://localhost:3000
# Grafana:   http://localhost:3001
# API docs:  http://localhost:8000/docs
```

### Service Ports (Local)

| Service              | Port | Description                    |
|----------------------|------|--------------------------------|
| Frontend             | 3000 | Chat UI (nginx)                |
| Orchestrator         | 8000 | User-facing API                |
| Statistics Agent     | 8001 | Stats computation              |
| Visualization Agent  | 8002 | Chart generation               |
| Query Agent (MCP)    | 8003 | Database access via MCP        |
| OTel Collector       | 4317 | OTLP gRPC receiver             |
| Grafana              | 3001 | Trace visualization            |

## Deploy to OpenShift

### Prerequisites

- `oc` CLI authenticated to an OpenShift cluster
- Knative Serving installed on the cluster
- Access to push images to the internal registry

### Steps

```bash
# 1. Create the project
oc new-project data-agents-demo

# 2. Build and push images
REGISTRY=$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}')
docker login -u $(oc whoami) -p $(oc whoami -t) $REGISTRY

for component in orchestrator statistics-agent visualization-agent query-agent database frontend; do
  docker build -t $REGISTRY/data-agents-demo/$component:latest -f $component/Containerfile $component/
  docker push $REGISTRY/data-agents-demo/$component:latest
done

# 3. Update the LLM API key in the secret
oc apply -f deploy/openshift/secrets.yaml
oc set data secret/agent-secrets --from-literal=LLM_API_KEY=<your-api-key>

# 4. Apply all manifests
oc apply -f deploy/openshift/configmaps.yaml
oc apply -f deploy/openshift/sqlite-deployment.yaml
oc apply -f deploy/openshift/otel-collector.yaml
oc apply -f deploy/openshift/grafana.yaml
oc apply -f deploy/openshift/query-agent-ksvc.yaml
oc apply -f deploy/openshift/stats-agent-ksvc.yaml
oc apply -f deploy/openshift/viz-agent-ksvc.yaml
oc apply -f deploy/openshift/orchestrator.yaml
oc apply -f deploy/openshift/frontend.yaml

# 5. Get the frontend URL
oc get route data-agents-ui -o jsonpath='{.spec.host}'
```

## Environment Variables

| Variable                       | Required | Default                          | Description                              |
|--------------------------------|----------|----------------------------------|------------------------------------------|
| `LLM_API_KEY`                  | Yes      | -                                | API key for the vLLM/LiteLLM endpoint    |
| `LLM_API_BASE`                | No       | `https://litellm-litemaas...`    | OpenAI-compatible LLM endpoint URL       |
| `LLM_MODEL`                   | No       | `Qwen3.6-35B-A3B`               | Model name to use                        |
| `MCP_AUTH_TOKEN`               | No       | `demo-token-2024`                | Shared bearer token for MCP auth         |
| `OTEL_ENABLED`                 | No       | `true`                           | Enable/disable OpenTelemetry tracing     |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No       | `http://otel-collector:4317`     | OTel collector endpoint                  |
| `SQLITE_DB_PATH`              | No       | `/data/residential_energy.db`    | Path to the SQLite database file         |
| `GRAFANA_URL`                  | No       | `http://localhost:3001`          | Grafana URL shown in the frontend        |

## Data

The system ships with a sample data generator that creates realistic residential energy data
for 500 buildings across 10 US states with 6 upgrade scenarios. To use your own data:

1. Place a `.sqlite` file at `data/residential_energy.db`, or
2. Place CSV files in `data/csv/` (filenames must match table names: `buildings.csv`,
   `energy_consumption.csv`, `hourly_loads.csv`)

The database schema includes three tables:
- **buildings**: Building characteristics (state, county, climate zone, type, vintage, sqft, fuel types)
- **energy_consumption**: Monthly energy use by upgrade scenario (electricity, gas, costs)
- **hourly_loads**: Hourly electricity demand and heating/cooling loads

## Example Queries

Try these in the chat interface:

1. *"What happens to electricity demand in Texas if homes use solar water heating?"*
2. *"How do air conditioning upgrades change annual cooling costs in North Carolina?"*
3. *"What's the average natural gas consumption for hot water heating in Wake County?"*
4. *"Compare electricity usage before and after heat pump adoption in the Southeast."*
5. *"Show me the distribution of energy savings from envelope upgrades across climate zones."*

## Observability

Every agent-to-agent call is traced with OpenTelemetry. Click the **Traces** button in the
UI header to open Grafana, where you can:

- View trace waterfalls showing the full path from user question to database query and back
- See latency breakdowns per agent
- Inspect SQL queries generated by the Query Agent
- Track token usage via custom span attributes

## Project Structure

```
data-agents/
├── orchestrator/           # User-facing agent (FastAPI + SSE)
├── statistics-agent/       # Statistics sub-agent (FastAPI)
├── visualization-agent/    # Visualization sub-agent (FastAPI + matplotlib)
├── query-agent/            # MCP server for database access (FastMCP)
├── database/               # SQLite init container
├── frontend/               # Chat UI (HTML/JS/CSS + nginx)
├── grafana/                # Grafana provisioning configs
├── otel-collector/         # OpenTelemetry Collector config
├── deploy/
│   ├── local/              # docker-compose.yaml
│   └── openshift/          # K8s/Knative manifests
├── data/                   # Database files (mount point)
├── .env.example            # Environment variable template
└── README.md
```

## Tech Stack

| Component              | Technology                                       |
|------------------------|--------------------------------------------------|
| Container platform     | OpenShift + Knative Serving (scale-to-zero)      |
| LLM inference          | vLLM (remote, OpenAI-compatible API)             |
| Orchestrator           | Python / FastAPI                                 |
| Sub-agents             | Python / FastAPI (stats, viz) + FastMCP (query)  |
| Database               | SQLite (containerized, pre-loaded)               |
| Observability          | OpenTelemetry + Grafana Tempo + Grafana          |
| Frontend               | HTML / JS / CSS (nginx)                          |
| Inter-agent protocol   | MCP (Model Context Protocol) over HTTP           |
