import logging
import os

from mcp.server.fastmcp import FastMCP

from app.config import MCP_HOST, MCP_PORT, MCP_AUTH_TOKEN, SQLITE_DB_PATH
from app.tools import query_data, execute_sql, list_tables, describe_table, get_schema
from app.init_db import main as init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("query-agent")

if not os.path.exists(SQLITE_DB_PATH) or os.path.getsize(SQLITE_DB_PATH) == 0:
    logger.info("Database not found at %s, initializing...", SQLITE_DB_PATH)
    init_database()

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
