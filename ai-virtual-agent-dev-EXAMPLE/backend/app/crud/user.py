"""
CRUD operations for User model.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..schemas.user import UserCreate, UserUpdate
from .base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(
        self, db: AsyncSession, *, username: str
    ) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_users_with_agent(
        self, db: AsyncSession, *, agent_id: UUID
    ) -> List[User]:
        """Get all users that have access to a specific agent."""
        result = await db.execute(select(User).where(User.agent_ids.any(agent_id)))
        return result.scalars().all()

    async def get_by_username_or_email(
        self, db: AsyncSession, *, username: str = None, email: str = None
    ) -> Optional[User]:
        """Get user by username or email."""
        if not username and not email:
            return None

        query = select(User)
        if username and email:
            query = query.where((User.username == username) | (User.email == email))
        elif username:
            query = query.where(User.username == username)
        elif email:
            query = query.where(User.email == email)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        username: str = None,
        email: str = None,
        role: str = "user",
        agent_ids: List[UUID] = None,
    ) -> User:
        """Create a new user with transaction management."""
        try:
            from ..models import RoleEnum, User

            user_data = {
                "username": username,
                "email": email,
                "role": RoleEnum(role) if role else RoleEnum.user,
                "agent_ids": agent_ids or [],
            }
            db_obj = User(**user_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def update_agent_assignment(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        agent_ids_to_add: List[UUID] = None,
        agent_ids_to_remove: List[UUID] = None,
    ) -> User:
        """Update user's agent assignments with transaction management."""
        try:
            user = await self.get(db, id=user_id)
            if not user:
                return None

            current_agents = set(user.agent_ids or [])

            if agent_ids_to_add:
                current_agents.update(agent_ids_to_add)
            if agent_ids_to_remove:
                current_agents.difference_update(agent_ids_to_remove)

            user.agent_ids = list(current_agents)
            await db.commit()
            await db.refresh(user)
            return user
        except Exception:
            await db.rollback()
            raise


user = CRUDUser(User)
