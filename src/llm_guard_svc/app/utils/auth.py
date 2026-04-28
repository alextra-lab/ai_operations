"""
LLM Guard service authentication utilities - now using unified auth system.

This module provides backward compatibility while transitioning to the unified auth system.
"""

# Import from unified auth system
from shared.auth import (
    admin_required as admin_auth_required,
)
from shared.auth import (
    auth_manager as jwt_validator,
)
from shared.auth import (
    get_current_user,
)
from shared.auth import (
    service_required as service_auth_required,
)

# Backward compatibility aliases
get_current_admin_user = admin_auth_required

# Export for backward compatibility
__all__ = [
    "admin_auth_required",
    "get_current_admin_user",
    "get_current_user",
    "jwt_validator",
    "service_auth_required",
]
