import json
import logging

import httpx

from app.config import QUERY_AGENT_MCP_URL
from app.tracing import tracer

logger = logging.getLogger("statistics-agent.mcp_client")

_SESSION_ID = None


async def _get_session(client: httpx.AsyncClient) -> str:
    """Initialize an MCP session and return the session ID."""
    global _SESSION_ID
    if _SESSION_ID:
        return _SESSION_ID

    init_payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "statistics-agent", "version": "1.0"},
        },
    }

    resp = await client.post(
        QUERY_AGENT_MCP_URL,
        json=init_payload,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    resp.raise_for_status()

    session_id = resp.headers.get("mcp-session-id")
    if session_id:
        _SESSION_ID = session_id

    await client.post(
        QUERY_AGENT_MCP_URL,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={
            "Content-Type": "application/json",
            **({"mcp-session-id": session_id} if session_id else {}),
        },
    )

    return _SESSION_ID or ""


async def _parse_sse_response(resp: httpx.Response) -> dict:
    """Parse SSE or JSON response from MCP server."""
    content_type = resp.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        text = resp.text
        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
        return {}
    else:
        return resp.json()


async def call_mcp_tool(tool_name: str, arguments: dict, _retry: bool = True) -> str:
    """Call a tool on the Query Agent MCP server with automatic session retry."""
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

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                session_id = await _get_session(client)

                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                }
                if session_id:
                    headers["mcp-session-id"] = session_id

                resp = await client.post(QUERY_AGENT_MCP_URL, json=payload, headers=headers)
                resp.raise_for_status()

                data = await _parse_sse_response(resp)

                if "error" in data:
                    logger.warning("MCP error, clearing session: %s", data["error"])
                    global _SESSION_ID
                    _SESSION_ID = None
                    if _retry:
                        return await call_mcp_tool(tool_name, arguments, _retry=False)
                    return json.dumps({"error": data["error"]})

                result = data.get("result", {})
                content_list = result.get("content", [])
                texts = [c.get("text", "") for c in content_list if c.get("type") == "text"]
                return "\n".join(texts) if texts else json.dumps(result)
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as exc:
            logger.warning("MCP request failed (%s), clearing session and retrying", exc)
            _SESSION_ID = None
            if _retry:
                return await call_mcp_tool(tool_name, arguments, _retry=False)
            return json.dumps({"error": str(exc)})


async def query_data(description: str) -> str:
    return await call_mcp_tool("query_data", {"description": description})


async def execute_sql(sql: str) -> str:
    return await call_mcp_tool("execute_sql", {"sql": sql})


async def list_tables() -> str:
    return await call_mcp_tool("list_tables", {})


async def get_schema() -> str:
    return await call_mcp_tool("get_schema", {})
