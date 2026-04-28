"""
Unified authentication manager for all services.

This module provides a centralized authentication manager that handles
JWT token creation, validation, and user management across all services.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from .base import AuthManager
from .models import RefreshToken, TokenPayload, User, UserRole

logger = configure_logging(service_name="auth_manager")


class UnifiedAuthManager(AuthManager):
    """
    Unified authentication manager that extends the base AuthManager
    with database operations and FastAPI-specific functionality.
    """

    def __init__(
        self,
        secret: str | None = None,
        algorithm: str = "HS256",
        issuer: str = "ai-operations-platform",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        super().__init__(
            secret=secret,
            algorithm=algorithm,
            issuer=issuer,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
        )
        self.security = HTTPBearer(auto_error=False)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hashed password."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def get_password_hash(self, password: str) -> str:
        """Hash a password for secure storage."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    async def create_user_tokens(self, user: User, db: AsyncSession) -> dict[str, Any]:
        """
        Create both access and refresh tokens for a user.

        Fetches all user roles from user_roles table per ADR-060 multi-role architecture.

        Args:
            user: User object
            db: Database session for fetching user roles

        Returns:
            Dictionary containing access_token, refresh_token, and metadata
        """
        # Fetch all user roles from user_roles table (ADR-060 multi-role support)
        # Query directly using SQL to avoid service-specific imports
        roles = []
        try:
            from sqlalchemy import text

            result = await db.execute(
                text("SELECT role FROM user_roles WHERE user_id = :user_id"),
                {"user_id": str(user.id)},
            )
            roles = [row[0] for row in result.fetchall()]
        except Exception as e:
            # If table doesn't exist or query fails, fall back to legacy role
            logger.warning(
                "Could not fetch roles from user_roles table for user_id=%s: %s. "
                "Falling back to legacy user.role column.",
                str(user.id),
                e,
            )

        # Fallback: if no roles in user_roles table, use legacy user.role column
        role_val = getattr(user, "role", None)
        if not roles and role_val:
            roles = [role_val]
            logger.debug(
                "User user_id=%s has no roles in user_roles table, using legacy role: %s",
                str(user.id),
                role_val,
            )

        # Create access token with multi-role support
        access_token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "roles": roles,  # Multiple roles per ADR-060
        }
        access_token = self.create_access_token(data=access_token_data)

        # Create refresh token
        refresh_token_data = {
            "sub": user.username,
            "user_id": str(user.id),
        }
        refresh_token = self.create_refresh_token(data=refresh_token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": user.to_dict(),
        }

    def verify_token_enhanced(
        self, token: str, request_id: str | None = None
    ) -> TokenPayload | None:
        """
        Enhanced token verification that returns a structured TokenPayload.

        Supports both legacy single-role tokens and new multi-role tokens (ADR-060).

        Args:
            token: JWT token string
            request_id: Optional request ID for logging

        Returns:
            TokenPayload object if valid, None otherwise
        """
        payload = super().verify_token(token)
        if payload is None:
            logger.warning(
                "JWT validation failed for request %s",
                request_id or "no-request-id",
            )
            return None

        # Validate required claims (backward compatible - check for either 'role' or 'roles')
        required_claims = ["sub", "user_id", "exp", "iat", "iss", "token_type"]
        for claim in required_claims:
            if claim not in payload:
                logger.warning(
                    "JWT missing required claim: %s for request %s",
                    claim,
                    request_id or "no-request-id",
                )
                return None

        # Check for role claims (either old single-role or new multi-role)
        if "roles" not in payload and "role" not in payload:
            logger.warning(
                "JWT missing both 'role' and 'roles' claims for request %s",
                request_id or "no-request-id",
            )
            return None

        try:
            # Backward compatibility: Convert single 'role' to 'roles' list
            if "role" in payload and "roles" not in payload:
                role_value = payload["role"]
                if isinstance(role_value, str):
                    payload["roles"] = [role_value]
                else:
                    payload["roles"] = [str(role_value)]
                # Remove legacy 'role' key to avoid Pydantic validation errors
                del payload["role"]
                logger.debug("Converted legacy single role to roles list")

            # Ensure roles is a list
            if not isinstance(payload.get("roles"), list):
                payload["roles"] = [payload.get("roles", "user")]

            return TokenPayload(**payload)
        except Exception as e:
            logger.warning(
                "Failed to parse token payload: %s for request %s",
                e,
                request_id or "no-request-id",
            )
            return None

    def get_user_from_request(
        self,
        credentials: HTTPAuthorizationCredentials | None,
        request_id: str | None = None,
    ) -> TokenPayload:
        """
        Extract and validate user from HTTP request credentials.

        Args:
            credentials: HTTP authorization credentials
            request_id: Optional request ID for logging

        Returns:
            TokenPayload object

        Raises:
            HTTPException: If credentials are invalid
        """
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = self.verify_token_enhanced(credentials.credentials, request_id=request_id)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    def requires_roles(
        self, required_roles: list[str]
    ) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
        """
        Create a FastAPI dependency that requires specific roles.

        Args:
            required_roles: List of required roles

        Returns:
            FastAPI dependency function
        """

        def dependency(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ) -> TokenPayload:
            payload = self.get_user_from_request(credentials)
            if not payload.has_any_role(required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role. Required: {required_roles}, got: {payload.roles}",
                )
            return payload

        return dependency

    def get_current_user(
        self,
    ) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
        """
        FastAPI dependency to get the current authenticated user.

        Returns:
            FastAPI dependency function that returns TokenPayload
        """

        def dependency(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ) -> TokenPayload:
            return self.get_user_from_request(credentials)

        return dependency

    def admin_required(self) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
        """FastAPI dependency requiring admin role."""
        return self.requires_roles([UserRole.ADMIN.value])

    def service_required(
        self,
    ) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
        """FastAPI dependency requiring service or admin role."""
        return self.requires_roles(UserRole.privileged_roles())  # Already returns list[str]

    # Database operations
    async def authenticate_user(
        self, db: AsyncSession, username: str, password: str
    ) -> User | None:
        """
        Authenticate a user with username and password.
        """
        try:
            result = await db.execute(select(User).where(User.username.ilike(username)))
            user = result.scalars().first()
            if not user:
                logger.info("Authentication failed: user not found")
                return None

            is_active = getattr(user, "is_active", True)
            if not is_active:
                logger.info(
                    "Authentication failed: user inactive",
                    extra={"user_id": str(user.id)},
                )
                return None

            hashed = getattr(user, "hashed_password", None) or ""
            if not self.verify_password(password, str(hashed)):
                logger.info(
                    "Authentication failed: invalid password",
                    extra={"user_id": str(user.id)},
                )
                return None

            # Update last login
            user.last_login = datetime.now(UTC)  # type: ignore[assignment]
            await db.commit()

            logger.info(
                "User authenticated successfully",
                extra={"user_id": str(user.id)},
            )
            return user

        except Exception as e:
            logger.error(f"Error during authentication: {e}", exc_info=True)
            return None

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
        full_name: str | None = None,
        email: str | None = None,
        role: str = UserRole.USER,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """
        Create a new user.
        """
        # Check if user already exists
        result = await db.execute(select(User).where(User.username.ilike(username)))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        # Check if email already exists (if provided)
        if email:
            result = await db.execute(select(User).where(User.email.ilike(email)))
            existing_email = result.scalars().first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Validate role
        if role not in UserRole.all_roles():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {UserRole.all_roles()}",
            )

        try:
            # Create user
            hashed_password = self.get_password_hash(password)
            user = User(
                id=uuid.uuid4(),
                username=username,
                full_name=full_name,
                email=email,
                hashed_password=hashed_password,
                role=role,
                metadata=metadata or {},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            logger.info(
                "User created successfully",
                extra={"user_id": str(user.id), "role": role},
            )
            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

    async def store_refresh_token(
        self,
        db: AsyncSession,
        user_id: str | uuid.UUID,
        token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        Store a refresh token in the database.
        """
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)

            refresh_token = RefreshToken(
                token=token,
                user_id=user_id,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            )

            db.add(refresh_token)
            await db.commit()
            await db.refresh(refresh_token)

            logger.info(
                "Refresh token stored",
                extra={"user_id": str(user_id), "expires_at": expires_at.isoformat()},
            )
            return refresh_token

        except Exception as e:
            await db.rollback()
            logger.error(f"Error storing refresh token: {e}", exc_info=True)
            raise

    async def validate_refresh_token(self, db: AsyncSession, token: str) -> User | None:
        """
        Validate a refresh token and return the associated user.
        """
        try:
            result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
            db_token = result.scalars().first()
            if not db_token:
                logger.info("Refresh token validation failed: not found")
                return None

            revoked = getattr(db_token, "revoked", True)
            if revoked:
                logger.info("Refresh token validation failed: revoked")
                return None

            expires_at = getattr(db_token, "expires_at", None)
            if expires_at is not None and expires_at < datetime.now(UTC):
                logger.info("Refresh token validation failed: expired")
                return None

            result = await db.execute(select(User).where(User.id == db_token.user_id))
            user = result.scalars().first()
            user_active = getattr(user, "is_active", False) if user else False
            if not user or not user_active:
                logger.info("Refresh token validation failed: user not found or inactive")
                return None

            logger.info(
                "Refresh token validated successfully",
                extra={"user_id": str(user.id)},
            )
            return user

        except Exception as e:
            logger.error(f"Error validating refresh token: {e}", exc_info=True)
            return None

    async def revoke_refresh_token(self, db: AsyncSession, token: str) -> bool:
        """
        Revoke a refresh token.
        """
        try:
            result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
            db_token = result.scalars().first()
            if not db_token:
                logger.info("Revoke refresh token failed: not found")
                return False

            revoked = getattr(db_token, "revoked", True)
            if revoked:
                logger.info("Revoke refresh token failed: already revoked")
                return False

            db_token.revoked = True  # type: ignore[assignment]
            db_token.revoked_at = datetime.now(UTC)  # type: ignore[assignment]
            await db.commit()

            logger.info("Refresh token revoked successfully")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error revoking refresh token: {e}", exc_info=True)
            return False


# Global instance for use across services
auth_manager = UnifiedAuthManager()

# Export commonly used dependencies
get_current_user = auth_manager.get_current_user()
admin_required = auth_manager.admin_required()
service_required = auth_manager.service_required()
