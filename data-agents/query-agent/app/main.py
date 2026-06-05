import logging

from mcp.server.fastmcp import FastMCP

from app.config import MCP_HOST, MCP_PORT
from app.tools import query_data, list_available_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("query-agent")

mcp = FastMCP(
    "query-agent",
    host=MCP_HOST,
    port=MCP_PORT,
)

mcp.tool()(query_data)
mcp.tool()(list_available_data)

if __name__ == "__main__":
    logger.info("Starting Query Agent MCP server on %s:%s", MCP_HOST, MCP_PORT)
    mcp.run(transport="streamable-http")
