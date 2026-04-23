"""
Knowledge Base schemas.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from .base import BaseSchema, TimestampMixin


class KnowledgeBaseBase(BaseModel):
    """Base knowledge base schema."""

    name: str
    version: str
    embedding_model: str
    provider_id: Optional[str] = None
    is_external: bool = False
    status: Optional[str] = None
    source: Optional[str] = None
    source_configuration: Optional[Union[Dict[str, Any], List[str]]] = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Schema for creating a knowledge base."""

    vector_store_name: str
    vector_store_id: Optional[str] = None

    def pipeline_model_dict(self) -> Dict[str, Any]:
        """Generate dictionary for ingestion pipeline API."""
        base = {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "embedding_model": self.embedding_model,
            "vector_store_name": self.vector_store_name,
        }
        if self.source == "URL":
            return base | {"urls": self.source_configuration}

        if isinstance(self.source_configuration, dict):
            return base | {k.lower(): v for k, v in self.source_configuration.items()}
        else:
            return base | {"config": self.source_configuration}


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base."""

    name: Optional[str] = None
    version: Optional[str] = None
    embedding_model: Optional[str] = None
    provider_id: Optional[str] = None
    is_external: Optional[bool] = None
    status: Optional[str] = None
    source: Optional[str] = None
    source_configuration: Optional[Dict[str, Any]] = None
    vector_store_id: Optional[str] = None


class KnowledgeBaseInDB(KnowledgeBaseBase, TimestampMixin, BaseSchema):
    """Schema for knowledge base as stored in database."""

    vector_store_name: str
    vector_store_id: Optional[str] = None
    created_by: Optional[UUID] = None


class KnowledgeBaseResponse(KnowledgeBaseInDB):
    """Schema for knowledge base in API responses."""

    pass
