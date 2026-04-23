"""Schemas for MCP servers API."""

from typing import Any, Dict

from pydantic import BaseModel


class MCPServerBase(BaseModel):
    """Base schema for MCP server."""

    toolgroup_id: str
    name: str
    description: str = ""
    endpoint_url: str
    configuration: Dict[str, Any] = {}


class MCPServerCreate(MCPServerBase):
    """Schema for creating MCP servers."""

    pass


class MCPServerRead(MCPServerBase):
    """Schema for reading MCP servers."""

    provider_id: str


class MCPServerUpdate(BaseModel):
    """Schema for updating MCP servers."""

    name: str = None
    description: str = None
    endpoint_url: str = None
    configuration: Dict[str, Any] = None
