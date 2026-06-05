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
