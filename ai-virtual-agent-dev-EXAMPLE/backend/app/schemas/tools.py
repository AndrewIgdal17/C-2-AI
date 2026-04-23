"""Tool-related schemas."""

from pydantic import BaseModel


class ToolAssociationInfo(BaseModel):
    """Schema for tool association information."""

    toolgroup_id: str
