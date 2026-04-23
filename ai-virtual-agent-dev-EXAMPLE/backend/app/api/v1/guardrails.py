"""
Guardrails API endpoints for configuring AI safety policies.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.guardrails import guardrail
from ...database import get_db
from ...schemas import GuardrailCreate, GuardrailResponse

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.post("/", response_model=GuardrailResponse, status_code=status.HTTP_201_CREATED)
async def create_guardrail(item: GuardrailCreate, db: AsyncSession = Depends(get_db)):
    """Create a new guardrail with specified rules and configuration."""
    return await guardrail.create(db, obj_in=item)


@router.get("/", response_model=List[GuardrailResponse])
async def read_guardrails(db: AsyncSession = Depends(get_db)):
    """Retrieve all guardrails from the database."""
    return await guardrail.get_multi(db)


@router.get("/{guardrail_id}", response_model=GuardrailResponse)
async def read_guardrail(guardrail_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific guardrail by its ID."""
    item = await guardrail.get(db, id=guardrail_id)
    if not item:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return item


@router.put("/{guardrail_id}", response_model=GuardrailResponse)
async def update_guardrail(
    guardrail_id: UUID,
    item: GuardrailCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing guardrail's rules and configuration."""
    db_item = await guardrail.get(db, id=guardrail_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return await guardrail.update(db, db_obj=db_item, obj_in=item)


@router.delete("/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(guardrail_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a guardrail from the database."""
    removed = await guardrail.remove(db, id=guardrail_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return None
