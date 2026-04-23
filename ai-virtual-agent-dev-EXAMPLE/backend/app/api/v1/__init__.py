"""API v1 package."""

from fastapi import APIRouter

from . import (
    agent_templates,
    attachments,
    chat_sessions,
    guardrails,
    knowledge_bases,
    mcp_servers,
    tools,
    users,
    validate,
    virtual_agents,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(agent_templates.router)
api_router.include_router(attachments.router)
api_router.include_router(chat_sessions.router)
api_router.include_router(guardrails.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(mcp_servers.router)
api_router.include_router(tools.router)
api_router.include_router(users.router)
api_router.include_router(validate.router)
api_router.include_router(virtual_agents.router)
