import os


LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    "https://litellm-litemaas.apps.prod.rhoai.rh-aiservices-bu.com/v1",
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B")

STATS_AGENT_URL = os.getenv("STATS_AGENT_URL", "http://statistics-agent:8001")
VIZ_AGENT_URL = os.getenv("VIZ_AGENT_URL", "http://visualization-agent:8002")

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
