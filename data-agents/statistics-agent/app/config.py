import os


LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    "https://litemaas.rhoai.rh-aiservices-bu.com/v1",
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B")

QUERY_AGENT_MCP_URL = os.getenv("QUERY_AGENT_MCP_URL", "http://query-agent:8003/mcp")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
