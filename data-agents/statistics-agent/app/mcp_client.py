import json
import logging

import httpx

from app.config import QUERY_AGENT_MCP_URL
from app.tracing import tracer

logger = logging.getLogger("statistics-agent.mcp_client")


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on the Query Agent MCP server via JSON-RPC over HTTP."""
    with tracer.start_as_current_span("mcp_call") as span:
        span.set_attribute("mcp.tool", tool_name)
        span.set_attribute("mcp.arguments", json.dumps(arguments))

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                QUERY_AGENT_MCP_URL,
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            )
            resp.raise_for_status()

            data = resp.json()
            if "error" in data:
                logger.error("MCP error: %s", data["error"])
                return json.dumps({"error": data["error"]})

            result = data.get("result", {})
            content_list = result.get("content", [])
            texts = [c.get("text", "") for c in content_list if c.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(result)


async def query_data(description: str) -> str:
    return await call_mcp_tool("query_data", {"description": description})


async def execute_sql(sql: str) -> str:
    return await call_mcp_tool("execute_sql", {"sql": sql})


async def list_tables() -> str:
    return await call_mcp_tool("list_tables", {})


async def get_schema() -> str:
    return await call_mcp_tool("get_schema", {})
