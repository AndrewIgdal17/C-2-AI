"""Pydantic schemas for model management."""

from typing import Any

from pydantic import BaseModel, Field


class ModelBase(BaseModel):
    """Base model schema with common fields."""

    model_id: str = Field(..., description="Unique identifier for the model")
    provider_id: str | None = Field(None, description="Provider ID (e.g., 'vllm')")
    provider_model_id: str | None = Field(
        None, description="Model ID in the provider system"
    )
    model_type: str = Field(
        default="llm", description="Type of model (llm or embedding)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional model metadata"
    )


class ModelCreate(ModelBase):
    """Schema for creating a new model."""

    pass


class ModelUpdate(BaseModel):
    """Schema for updating a model."""

    provider_id: str | None = None
    provider_model_id: str | None = None
    metadata: dict[str, Any] | None = None


class ModelRead(ModelBase):
    """Schema for reading a model."""

    created_at: str | None = None
    is_shield: bool = Field(
        default=False, description="Whether this model is used as a shield"
    )

    class Config:
        from_attributes = True
