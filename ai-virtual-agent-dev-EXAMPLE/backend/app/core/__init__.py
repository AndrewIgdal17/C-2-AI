"""
Core functionality package - utilities, auth, exceptions, etc.
"""

from .auth import (
    get_mock_dev_headers,
    get_or_create_dev_user,
    is_local_dev_mode,
)
from .feature_flags import is_attachments_feature_enabled

__all__ = [
    "is_local_dev_mode",
    "get_or_create_dev_user",
    "get_mock_dev_headers",
    "is_attachments_feature_enabled",
]
