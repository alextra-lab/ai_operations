"""
Shared authentication module for AI Operations Platform.

This module provides unified authentication and user management
across all services in the system.
"""

from .base import AuthManager
from .database import get_db, init_database, test_database_connection
from .manager import (
    UnifiedAuthManager,
    admin_required,
    auth_manager,
    get_current_user,
    service_required,
)
from .models import (
    RefreshToken,
    TokenPayload,
    TokenResponse,
    User,
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
)
from .router import auth_router, auth_router_minimal, create_auth_router
from .scopes import requires_any_scope, requires_scope

__all__ = [
    # Base classes
    "AuthManager",
    "RefreshToken",
    "TokenPayload",
    "TokenResponse",
    "UnifiedAuthManager",
    # Models
    "User",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "UserUpdate",
    "admin_required",
    # Manager and dependencies
    "auth_manager",
    # Routers
    "auth_router",
    "auth_router_minimal",
    "create_auth_router",
    "get_current_user",
    # Database
    "get_db",
    "init_database",
    "requires_any_scope",
    # Scope-based dependencies
    "requires_scope",
    "service_required",
    "test_database_connection",
]
