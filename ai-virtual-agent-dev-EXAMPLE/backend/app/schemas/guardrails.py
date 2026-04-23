"""
Guardrail schemas.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from .base import BaseSchema, TimestampMixin


class GuardrailBase(BaseModel):
    """Base guardrail schema."""

    name: str
    rules: Dict[str, Any]


class GuardrailCreate(GuardrailBase):
    """Schema for creating a guardrail."""

    pass


class GuardrailUpdate(BaseModel):
    """Schema for updating a guardrail."""

    name: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None


class GuardrailInDB(GuardrailBase, TimestampMixin, BaseSchema):
    """Schema for guardrail as stored in database."""

    id: UUID
    created_by: Optional[UUID] = None


class GuardrailResponse(GuardrailInDB):
    """Schema for guardrail in API responses."""

    pass
