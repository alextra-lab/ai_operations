"""
Shared authentication router for all services.

This module provides a unified authentication router that can be included
in any service to provide user authentication endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from .database import get_db
from .manager import auth_manager
from .models import (
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
    User,
    UserCreate,
    UserResponse,
    UserUpdate,
)

logger = configure_logging(service_name="auth_router")


def create_auth_router(prefix: str = "/auth", include_user_management: bool = True) -> APIRouter:
    """
    Create an authentication router.

    Args:
        prefix: URL prefix for the router
        include_user_management: Whether to include user management endpoints

    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix=prefix, tags=["Authentication"])

    @router.post("/token", response_model=TokenResponse, summary="Login and get tokens")
    async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db),
    ) -> TokenResponse:
        """
        Authenticate user and return access and refresh tokens.

        Args:
            form_data: OAuth2 form data with username and password
            db: Database session

        Returns:
            Token response with access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        logger.info("Login attempt")
        user = await auth_manager.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning("Login failed: invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens (with multi-role support per ADR-060)
        tokens = await auth_manager.create_user_tokens(user, db)
        # Store refresh token in database
        refresh_payload = auth_manager.verify_token(tokens["refresh_token"])
        if refresh_payload and "exp" in refresh_payload:
            expires_at = datetime.fromtimestamp(refresh_payload["exp"])
            user_id = str(user.id)
            await auth_manager.store_refresh_token(db, user_id, tokens["refresh_token"], expires_at)

        logger.info(
            "User authenticated successfully",
            extra={"user_id": str(user.id)},
        )

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
        )

    @router.post("/refresh", response_model=dict[str, str], summary="Refresh access token")
    async def refresh_token(
        request: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, str]:
        """
        Refresh an access token using a valid refresh token.

        Args:
            request: Refresh token request
            db: Database session

        Returns:
            New access token

        Raises:
            HTTPException: If refresh token is invalid
        """
        logger.info("Refresh token attempt")

        # Validate refresh token format
        payload = auth_manager.verify_token(request.refresh_token)
        if not payload or payload.get("token_type") != "refresh":
            logger.warning("Refresh token failed: invalid format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate refresh token in database
        user = await auth_manager.validate_refresh_token(db, request.refresh_token)
        if not user:
            logger.warning("Refresh token failed: invalid, expired, or revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid, expired, or has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch all user roles from user_roles table (ADR-060 multi-role support)
        roles = []
        try:
            result = await db.execute(
                text("SELECT role FROM user_roles WHERE user_id = :user_id"),
                {"user_id": str(user.id)},
            )
            roles = [row[0] for row in result.fetchall()]
        except Exception as e:
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

        # Create new access token with multi-role support
        access_token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "roles": roles,  # Multiple roles per ADR-060
        }
        new_access_token = auth_manager.create_access_token(data=access_token_data)

        logger.info(
            "Access token refreshed",
            extra={"user_id": str(user.id)},
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    @router.post("/revoke", summary="Revoke refresh token")
    async def revoke_token(
        request: RefreshTokenRequest,
        current_user: TokenPayload = Depends(auth_manager.get_current_user()),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, str]:
        """
        Revoke a refresh token.

        Args:
            request: Refresh token request
            current_user: Current authenticated user
            db: Database session

        Returns:
            Success message

        Raises:
            HTTPException: If token revocation fails
        """
        logger.info(
            "Revoke token attempt",
            extra={"user_id": current_user.user_id},
        )

        success = await auth_manager.revoke_refresh_token(db, request.refresh_token)
        if success:
            logger.info(
                "Token successfully revoked",
                extra={"user_id": current_user.user_id},
            )
            return {"message": "Token successfully revoked"}
        logger.warning(
            "Token revoke failed: invalid or already revoked",
            extra={"user_id": current_user.user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token or token already revoked",
        )

    @router.get("/validate", summary="Validate access token")
    async def validate_token(
        current_user: TokenPayload = Depends(auth_manager.get_current_user()),
    ) -> dict[str, str | list[str]]:
        """
        Validate the current access token and return user information.

        Args:
            current_user: Current authenticated user from token

        Returns:
            User information from token
        """
        logger.info(
            "Token validation request",
            extra={"user_id": current_user.user_id},
        )

        return {
            "username": current_user.sub,
            "user_id": current_user.user_id,
            "roles": current_user.roles,  # Multi-role support per ADR-060
            "token_type": current_user.token_type,
        }

    # User management endpoints (optional)
    if include_user_management:

        @router.post("/users", response_model=UserResponse, summary="Create new user")
        async def create_user(
            user_data: UserCreate,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> UserResponse:
            """
            Create a new user (admin only).

            Args:
                user_data: User creation data
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                Created user information
            """
            logger.info(
                "Create user request",
                extra={"admin_user_id": current_user.user_id},
            )

            user = await auth_manager.create_user(
                db=db,
                username=user_data.username,
                password=user_data.password,
                full_name=user_data.full_name,
                email=user_data.email,
                role=user_data.role,
                metadata=user_data.metadata,
            )

            return UserResponse(**user.to_dict())

        @router.get("/users", response_model=dict, summary="List users")
        async def list_users(
            search: str | None = None,
            role: str | None = None,
            status: str | None = None,
            limit: int = 20,
            offset: int = 0,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            """
            List all users with pagination and filtering (admin only).

            Args:
                search: Search by username or full_name
                role: Filter by role
                status: Filter by status (active/inactive)
                limit: Max results per page
                offset: Results offset
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                UserListResponse with pagination
            """
            logger.info(
                "List users request",
                extra={
                    "admin_user_id": current_user.user_id,
                    "limit": limit,
                    "offset": offset,
                },
            )

            # Build query
            query = select(User)

            # Apply filters
            if search:
                query = query.where(
                    (User.username.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
                )
            if role:
                query = query.where(User.role == role)
            if status:
                is_active = status.lower() == "active"
                query = query.where(User.is_active == is_active)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # Apply pagination
            query = query.offset(offset).limit(limit)
            result = await db.execute(query)
            users = result.scalars().all()

            # Build response
            items = [
                {
                    **user.to_dict(),
                    "session_count": 0,  # TODO: Count active sessions
                }
                for user in users
            ]

            return {"items": items, "total": total, "limit": limit, "offset": offset}

        @router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID")
        async def get_user(
            user_id: str,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> UserResponse:
            """
            Get a user by ID (admin only).

            Args:
                user_id: User ID
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                User information

            Raises:
                HTTPException: If user not found
            """
            logger.info(
                "Get user request",
                extra={"admin_user_id": current_user.user_id, "target_user_id": user_id},
            )

            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            return UserResponse(**user.to_dict())

        @router.put("/users/{user_id}", response_model=UserResponse, summary="Update user")
        async def update_user(
            user_id: str,
            user_data: UserUpdate,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> UserResponse:
            """
            Update a user (admin only).

            Args:
                user_id: User ID
                user_data: User update data
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                Updated user information

            Raises:
                HTTPException: If user not found
            """
            logger.info(
                "Update user request",
                extra={"admin_user_id": current_user.user_id, "target_user_id": user_id},
            )

            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            await db.commit()
            await db.refresh(user)

            return UserResponse(**user.to_dict())

        @router.get("/me", response_model=UserResponse, summary="Get current user")
        async def get_current_user_info(
            current_user: TokenPayload = Depends(auth_manager.get_current_user()),
            db: AsyncSession = Depends(get_db),
        ) -> UserResponse:
            """
            Get current user information.

            Args:
                current_user: Current authenticated user
                db: Database session

            Returns:
                Current user information

            Raises:
                HTTPException: If user not found
            """
            user = await db.get(User, current_user.user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            return UserResponse(**user.to_dict())

        @router.delete("/users/{user_id}", summary="Deactivate user")
        async def deactivate_user(
            user_id: str,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            """
            Deactivate a user by setting is_active=False (admin only).

            Args:
                user_id: User ID to deactivate
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                Success message

            Raises:
                HTTPException: If user not found or attempting self-deactivation
            """
            # Prevent self-deactivation
            if user_id == current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate your own account",
                )

            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            user.is_active = False  # type: ignore[assignment]

            # Revoke all refresh tokens
            from .models import RefreshToken

            result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
            tokens = result.scalars().all()
            for token in tokens:
                token.revoked = True  # type: ignore[assignment]
                token.revoked_at = datetime.now()  # type: ignore[assignment]

            await db.commit()

            logger.info(
                "User deactivated",
                extra={"admin_user_id": current_user.user_id, "target_user_id": user_id},
            )

            return {"message": f"User {user.username} deactivated successfully"}

        @router.post("/users/{user_id}/reset-password", summary="Reset user password")
        async def reset_password(
            user_id: str,
            new_password: str,
            force_logout: bool = True,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            """
            Reset a user's password (admin only).

            Args:
                user_id: User ID
                new_password: New password
                force_logout: Whether to revoke all sessions
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                Success message

            Raises:
                HTTPException: If user not found
            """
            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            # Update password
            user.hashed_password = auth_manager.get_password_hash(new_password)  # type: ignore[assignment]

            # Force logout if requested
            if force_logout:
                from .models import RefreshToken

                result = await db.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
                tokens = result.scalars().all()
                for token in tokens:
                    token.revoked = True  # type: ignore[assignment]
                    token.revoked_at = datetime.now()  # type: ignore[assignment]

            await db.commit()

            logger.info(
                "Password reset by admin",
                extra={
                    "admin_user_id": current_user.user_id,
                    "target_user_id": user_id,
                    "force_logout": force_logout,
                },
            )

            return {
                "message": f"Password reset for user {user.username}",
                "force_logout": force_logout,
            }

        @router.get("/users/{user_id}/sessions", summary="Get user sessions")
        async def get_sessions(
            user_id: str,
            _current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> list[dict]:
            """
            Get active sessions for a user (admin only).

            Args:
                user_id: User ID
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                List of active sessions
            """
            from .models import RefreshToken

            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at > datetime.now(),
                )
            )
            sessions = result.scalars().all()

            return [
                {
                    "id": str(session.id),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "revoked": session.revoked,
                }
                for session in sessions
            ]

        @router.delete("/users/{user_id}/sessions/{session_id}", summary="Force logout")
        async def force_logout(
            user_id: str,
            session_id: str,
            current_user: TokenPayload = Depends(auth_manager.admin_required()),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            """
            Revoke a user session, forcing logout (admin only).

            Args:
                user_id: User ID
                session_id: Session ID to revoke
                current_user: Current authenticated admin user
                db: Database session

            Returns:
                Success message

            Raises:
                HTTPException: If session not found
            """
            from .models import RefreshToken

            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.id == session_id, RefreshToken.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
                )

            session.revoked = True  # type: ignore[assignment]
            session.revoked_at = datetime.now()  # type: ignore[assignment]
            await db.commit()

            logger.info(
                "Session revoked by admin",
                extra={
                    "admin_user_id": current_user.user_id,
                    "target_user_id": user_id,
                    "session_id": session_id,
                },
            )

            return {"message": "Session revoked successfully"}

    return router


# Default router with full user management
auth_router = create_auth_router()

# Router without user management (for services that only need authentication)
auth_router_minimal = create_auth_router(include_user_management=False)
