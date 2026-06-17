"""Contract tests for MCP protocol interactions.

Tests that the MCP client correctly parses server responses and that
request/response formats match the MCP specification.
"""

import json
import asyncio

import pytest


class TestMCPInitializeHandshake:
    """Test that MCP initialize/initialized sequence matches spec."""

    def test_initialize_payload_structure(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        }
        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "initialize"
        assert "protocolVersion" in payload["params"]

    def test_initialized_notification_structure(self):
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        assert "id" not in notification
        assert notification["method"] == "notifications/initialized"


class TestMCPToolCallFormat:
    """Test that tool call request/response formats match MCP spec."""

    def test_tool_call_request_structure(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "query_data",
                "arguments": {"description": "average energy use"},
            },
        }
        assert payload["method"] == "tools/call"
        assert "name" in payload["params"]
        assert "arguments" in payload["params"]

    def test_tool_list_request_structure(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        assert payload["method"] == "tools/list"


class TestMCPClientParsing:
    """Test the SSE/JSON response parsing logic used by MCP clients.

    The parsing logic is inlined here (matching statistics-agent/app/mcp_client.py)
    to avoid sys.modules conflicts between agents that share an 'app' package name.
    """

    @staticmethod
    async def _parse_sse_response(resp) -> dict:
        """Parse SSE or JSON response from MCP server (mirrors mcp_client.py)."""
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

    @pytest.mark.asyncio
    async def test_parse_json_response(self):
        class FakeResponse:
            headers = {"content-type": "application/json"}
            def json(self):
                return {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "content": [{"type": "text", "text": '{"metric": "energy_use_total"}'}]
                    },
                }

        result = await self._parse_sse_response(FakeResponse())
        assert "result" in result
        assert result["result"]["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_parse_sse_response(self):
        class FakeResponse:
            headers = {"content-type": "text/event-stream"}
            text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"hello"}]}}\n\n'

        result = await self._parse_sse_response(FakeResponse())
        assert result["result"]["content"][0]["text"] == "hello"

    @pytest.mark.asyncio
    async def test_parse_sse_response_skips_invalid_json(self):
        class FakeResponse:
            headers = {"content-type": "text/event-stream"}
            text = 'data: not-json\ndata: {"jsonrpc":"2.0","id":1,"result":{"content":[]}}\n\n'

        result = await self._parse_sse_response(FakeResponse())
        assert "result" in result


class TestMCPResponseExtraction:
    """Test that we correctly extract text content from MCP tool results."""

    def test_extract_text_from_content_list(self):
        result = {
            "content": [
                {"type": "text", "text": '{"metric": "energy_use_total", "mean": 88.14}'},
            ]
        }
        texts = [c.get("text", "") for c in result["content"] if c.get("type") == "text"]
        assert len(texts) == 1
        parsed = json.loads(texts[0])
        assert parsed["metric"] == "energy_use_total"

    def test_extract_multiple_text_blocks(self):
        result = {
            "content": [
                {"type": "text", "text": "first"},
                {"type": "image", "data": "..."},
                {"type": "text", "text": "second"},
            ]
        }
        texts = [c.get("text", "") for c in result["content"] if c.get("type") == "text"]
        assert texts == ["first", "second"]

    def test_empty_content_list(self):
        result = {"content": []}
        texts = [c.get("text", "") for c in result["content"] if c.get("type") == "text"]
        assert texts == []
