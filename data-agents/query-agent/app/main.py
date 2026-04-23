import logging
import os

from mcp.server.fastmcp import FastMCP

from app.config import MCP_HOST, MCP_PORT, MCP_AUTH_TOKEN
from app.tools import query_data, execute_sql, list_tables, describe_table, get_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("query-agent")

mcp = FastMCP(
    "query-agent",
    host=MCP_HOST,
    port=MCP_PORT,
)

mcp.tool()(query_data)
mcp.tool()(execute_sql)
mcp.tool()(list_tables)
mcp.tool()(describe_table)
mcp.tool()(get_schema)

if __name__ == "__main__":
    logger.info("Starting Query Agent MCP server on %s:%s", MCP_HOST, MCP_PORT)
    mcp.run(transport="streamable-http")
