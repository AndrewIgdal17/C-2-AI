"""
CRUD operations for Guardrails.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Guardrail
from ..schemas import GuardrailCreate
from .base import CRUDBase


class CRUDGuardrail(CRUDBase[Guardrail, GuardrailCreate, GuardrailCreate]):
    async def create(self, db: AsyncSession, *, obj_in: GuardrailCreate) -> Guardrail:
        """Create guardrail with transaction management."""
        try:
            db_obj = Guardrail(**obj_in.dict())
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def update(
        self, db: AsyncSession, *, db_obj: Guardrail, obj_in: GuardrailCreate
    ) -> Guardrail:
        """Update guardrail with transaction management."""
        try:
            for field, value in obj_in.dict().items():
                setattr(db_obj, field, value)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def remove(self, db: AsyncSession, *, id: UUID) -> Optional[Guardrail]:
        """Remove guardrail with transaction management."""
        try:
            obj = await self.get(db, id=id)
            if obj:
                await db.delete(obj)
                await db.commit()
            return obj
        except Exception:
            await db.rollback()
            raise


guardrail = CRUDGuardrail(Guardrail)
