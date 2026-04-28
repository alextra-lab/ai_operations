"""
Shared user management models for all services.

This module provides unified user models and database operations
that can be used across all services in the AI Operations Platform system.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811 (type alias)
from sqlalchemy.orm import declarative_base, relationship

# Create a shared base for SQLAlchemy models
Base = declarative_base()


class UserRole(str, Enum):
    """Standard user roles across all services."""

    ADMIN = "admin"
    CORPUS_ADMIN = "corpus_admin"  # Corpus/document management
    DEVELOPER = "developer"  # Use case development (team-scoped)
    USE_CASE_ADMIN = "use_case_admin"  # Use case super admin (all teams)
    TOOLS_ADMIN = "tools_admin"  # Tools/MCP management
    ROLE_ADMIN = "role_admin"  # Role management
    SERVICE = "service"
    USER = "user"
    USE_CASE_PUBLISHER = "use_case_publisher"  # Use case approval and publishing
    CONVERSATIONS_PRIVILEGED = (
        "conversations_privileged"  # Privileged access to Conversations UI/API
    )

    @classmethod
    def all_roles(cls) -> list[str]:
        return [role.value for role in cls]

    @classmethod
    def privileged_roles(cls) -> list[str]:
        return [cls.ADMIN.value, cls.SERVICE.value]

    @classmethod
    def corpus_management_roles(cls) -> list[str]:
        """Roles that can manage document collections and corpus."""
        return [cls.ADMIN.value, cls.CORPUS_ADMIN.value]

    @classmethod
    def conversations_roles(cls) -> list[str]:
        """Roles allowed to access Conversations UI/API."""
        return [cls.ADMIN.value, cls.CONVERSATIONS_PRIVILEGED.value]


class User(Base):  # type: ignore[misc,valid-type]
    """
    Unified user model for all services.

    Uses UUID as primary key for consistency across services.
    """

    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    center_id = Column(String, nullable=True)  # Organization/center identifier

    # Metadata for additional user properties
    user_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert user to dictionary for API responses."""
        return {
            "id": str(self.id),
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "metadata": self.user_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
            "last_login": self.last_login.isoformat() if self.last_login is not None else None,
        }


class RefreshToken(Base):  # type: ignore[misc,valid-type]
    """
    Refresh token model for JWT token management.
    """

    __tablename__ = "refresh_tokens"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    user = relationship("User", back_populates="refresh_tokens")


# Pydantic models for API schemas
class UserBase(BaseModel):
    """Base user schema."""

    username: str
    full_name: str | None = None
    email: str | None = None
    role: str = UserRole.USER
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict, alias="user_metadata")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class UserResponse(UserBase):
    """Schema for user API responses."""

    id: str
    created_at: str | None = None
    updated_at: str | None = None
    last_login: str | None = None

    model_config = {"from_attributes": True}


class TokenPayload(BaseModel):
    """
    Standard JWT token payload across all services.

    Supports multi-role assignment per ADR-060.
    """

    sub: str  # username
    user_id: str  # UUID as string
    roles: list[str] = Field(default_factory=list)  # Multiple roles per user (ADR-060)
    scopes: list[str] = Field(default_factory=list)  # Optional scopes for fine-grained access
    exp: int
    iat: int
    iss: str
    token_type: str  # "access" or "refresh"

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return UserRole.ADMIN.value in self.roles

    def is_service(self) -> bool:
        """Check if user has service or admin role."""
        return any(role in self.roles for role in UserRole.privileged_roles())

    def has_role(self, required_role: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            required_role: The role to check for

        Returns:
            True if user has the role, False otherwise
        """
        return required_role in self.roles

    def has_any_role(self, required_roles: list[str]) -> bool:
        """
        Check if user has any of the required roles.

        Args:
            required_roles: List of roles to check for

        Returns:
            True if user has at least one of the required roles, False otherwise
        """
        return any(role in self.roles for role in required_roles)

    def has_all_roles(self, required_roles: list[str]) -> bool:
        """
        Check if user has all of the required roles.

        Args:
            required_roles: List of roles to check for

        Returns:
            True if user has all of the required roles, False otherwise
        """
        return all(role in self.roles for role in required_roles)

    def has_scope(self, required_scope: str) -> bool:
        """
        Check if token has specific scope.

        Args:
            required_scope: The scope to check for

        Returns:
            True if the token has the required scope, False otherwise
        """
        return required_scope in self.scopes

    def has_any_scope(self, required_scopes: list[str]) -> bool:
        """
        Check if token has any of the required scopes.

        Args:
            required_scopes: List of scopes to check for

        Returns:
            True if the token has at least one of the required scopes, False otherwise
        """
        return any(scope in self.scopes for scope in required_scopes)


class LoginRequest(BaseModel):
    """Schema for login requests."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token requests."""

    refresh_token: str
