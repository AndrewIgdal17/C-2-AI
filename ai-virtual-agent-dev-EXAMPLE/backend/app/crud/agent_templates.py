"""
CRUD operations for Agent Template and Template Suite models.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import AgentTemplate, TemplateSuite
from ..schemas.agent import (
    AgentTemplateCreate,
    AgentTemplateUpdate,
    TemplateSuiteCreate,
    TemplateSuiteUpdate,
)
from .base import CRUDBase


class CRUDAgentTemplate(
    CRUDBase[AgentTemplate, AgentTemplateCreate, AgentTemplateUpdate]
):
    """CRUD operations for AgentTemplate."""

    async def get_by_name(
        self, db: AsyncSession, *, name: str
    ) -> Optional[AgentTemplate]:
        """Get template by name."""
        result = await db.execute(
            select(AgentTemplate).where(AgentTemplate.name == name)
        )
        return result.scalars().first()

    async def get_by_suite(
        self, db: AsyncSession, *, suite_id: uuid.UUID
    ) -> List[AgentTemplate]:
        """Get all templates in a suite."""
        result = await db.execute(
            select(AgentTemplate).where(AgentTemplate.suite_id == suite_id)
        )
        return result.scalars().all()

    async def get_with_suite(
        self, db: AsyncSession, *, template_id: uuid.UUID
    ) -> Optional[AgentTemplate]:
        """Get template with suite information."""
        result = await db.execute(
            select(AgentTemplate)
            .options(selectinload(AgentTemplate.suite))
            .where(AgentTemplate.id == template_id)
        )
        return result.scalar_one_or_none()


class CRUDTemplateSuite(
    CRUDBase[TemplateSuite, TemplateSuiteCreate, TemplateSuiteUpdate]
):
    """CRUD operations for TemplateSuite."""

    async def get_by_category(
        self, db: AsyncSession, *, category: str
    ) -> List[TemplateSuite]:
        """Get all suites in a category."""
        result = await db.execute(
            select(TemplateSuite).where(TemplateSuite.category == category)
        )
        return result.scalars().all()

    async def get_with_templates(
        self, db: AsyncSession, *, suite_id: uuid.UUID
    ) -> Optional[TemplateSuite]:
        """Get suite with all templates."""
        result = await db.execute(
            select(TemplateSuite)
            .options(selectinload(TemplateSuite.templates))
            .where(TemplateSuite.id == suite_id)
        )
        return result.scalar_one_or_none()


agent_template = CRUDAgentTemplate(AgentTemplate)
template_suite = CRUDTemplateSuite(TemplateSuite)
