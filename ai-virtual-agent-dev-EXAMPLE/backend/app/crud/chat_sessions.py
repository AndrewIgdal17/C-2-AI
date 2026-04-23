"""CRUD operations for chat sessions."""

import logging
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chat import ChatSession
from .base import CRUDBase

logger = logging.getLogger(__name__)


class CRUDChatSession(CRUDBase[ChatSession, dict, dict]):
    """CRUD operations for chat sessions."""

    async def get_by_agent(
        self, db: AsyncSession, *, agent_id, user_id, limit: int = 50
    ) -> List[ChatSession]:
        """Get chat sessions by agent ID and user ID (both UUIDs)."""
        try:
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.agent_id == agent_id)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(
                f"Error getting sessions by agent {agent_id} for user {user_id}: {str(e)}"
            )
            raise

    async def get_with_agent(
        self, db: AsyncSession, *, session_id, user_id
    ) -> Optional[ChatSession]:
        """Get chat session with agent relationship, ensuring user owns the session.

        Args:
            session_id: Session UUID (string or UUID object)
            user_id: User UUID (string or UUID object)
        """
        try:
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .where(ChatSession.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting session {session_id} for user {user_id}: {str(e)}"
            )
            raise

    async def create_session(
        self, db: AsyncSession, *, session_data: dict
    ) -> ChatSession:
        """Create a new chat session."""
        try:
            db_obj = ChatSession(**session_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating session: {str(e)}")
            raise

    async def delete_session(self, db: AsyncSession, *, session_id, user_id) -> bool:
        """Delete a chat session and related data, ensuring user owns the session.

        Args:
            session_id: Session UUID (string or UUID object)
            user_id: User UUID (string or UUID object)
        """
        try:
            # First check if the session exists and user owns it
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .where(ChatSession.user_id == user_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                # Session doesn't exist or user doesn't own it
                return False

            # Delete the session (CASCADE will handle any related data)
            await db.execute(delete(ChatSession).where(ChatSession.id == session_id))

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Error deleting session {session_id} for user {user_id}: {str(e)}"
            )
            raise


chat_sessions = CRUDChatSession(ChatSession)
