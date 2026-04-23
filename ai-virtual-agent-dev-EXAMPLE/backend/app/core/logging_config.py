"""
Centralized logging configuration for the AI Virtual Agent Quickstart backend.

This module provides consistent logging setup across all backend components,
including structured logging, log levels, and formatting for production
and development environments.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure logging for the entire application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=_get_handlers(log_file, format_string),
        force=True,  # Force reconfiguration even if already configured
    )

    # Set the root logger level explicitly
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    # Set specific loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Ensure our backend loggers use DEBUG level
    logging.getLogger("backend").setLevel(logging.DEBUG)
    logging.getLogger("backend.app").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api.v1").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api.v1.chat").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api.v1.chat_sessions").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api.v1.llama_stack").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.api.v1.knowledge_bases").setLevel(logging.DEBUG)
    logging.getLogger("backend.app.services.chat").setLevel(logging.DEBUG)


def _get_handlers(log_file: Optional[str], format_string: str) -> list:
    """Get logging handlers for console and optionally file output."""
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)

    return handlers
