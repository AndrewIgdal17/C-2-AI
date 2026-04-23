"""
Tools API endpoints for managing MCP servers and builtin tools.

This module provides endpoints to retrieve and manage tool groups, including
both MCP (Model Context Protocol) servers and LlamaStack builtin tools.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from ...api.llamastack import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_tool_groups(request: Request):
    """
    Get all available tool groups from LlamaStack (both MCP servers and
    builtin tools).

    This endpoint fetches all tool groups directly from LlamaStack, including:
    - MCP servers
    - Builtin tools available through LlamaStack

    Returns:
        List of tool groups with their metadata and configuration
    """
    tool_groups = {}

    # Get all toolgroups from LlamaStack
    try:
        client = get_client_from_request(request)
        toolgroups = await client.toolgroups.list()

        for toolgroup in toolgroups:
            toolgroup_id = str(toolgroup.identifier)
            provider_id = getattr(toolgroup, "provider_id", "unknown")

            # Get configuration if available
            config = getattr(toolgroup, "config", {})

            tool_groups[toolgroup_id] = {
                "toolgroup_id": toolgroup_id,
                "name": getattr(toolgroup, "provider_resource_id", toolgroup_id),
                "description": config.get(
                    "description", f"Tool group for {toolgroup_id}"
                ),
                "endpoint_url": (
                    config.get("endpoint_url")
                    if provider_id == "model-context-protocol"
                    else None
                ),
                "configuration": config,
                "provider_id": provider_id,
                "created_at": None,  # LlamaStack doesn't provide timestamps
                "updated_at": None,  # LlamaStack doesn't provide timestamps
            }
    except Exception as e:
        logger.error(f"Failed to fetch toolgroups from LlamaStack: {str(e)}")

    # Also get individual tools from LlamaStack for backward compatibility
    try:
        response = await client.tools.list()
        if isinstance(response, list):
            llamastack_tools = [item.__dict__ for item in response]
        elif isinstance(response, dict):
            llamastack_tools = response.get("data", [])
        elif hasattr(response, "data"):
            llamastack_tools = response.data
        else:
            llamastack_tools = []

        # Group tools by toolgroup_id and add any missing ones
        for tool in llamastack_tools:
            toolgroup_id = tool.get("toolgroup_id", tool.get("identifier"))
            if toolgroup_id and toolgroup_id not in tool_groups:
                provider_id = tool.get("provider_id", "unknown")
                tool_groups[toolgroup_id] = {
                    "toolgroup_id": toolgroup_id,
                    "name": tool.get("identifier", toolgroup_id),
                    "description": tool.get("description", f"Tools for {toolgroup_id}"),
                    "endpoint_url": (
                        tool.get("metadata", {}).get("endpoint")
                        if provider_id == "model-context-protocol"
                        else None
                    ),
                    "configuration": tool.get("metadata", {}),
                    "provider_id": provider_id,
                    "created_at": None,
                    "updated_at": None,
                }
    except Exception as e:
        logger.warning(f"Failed to fetch individual tools from LlamaStack: {str(e)}")

    return list(tool_groups.values())
