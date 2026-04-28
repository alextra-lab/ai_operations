from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from shared.config.loader import load_jwt_config


class AuthManager:
    """
    Shared JWT AuthManager for token creation and verification.
    """

    def __init__(
        self,
        secret: str | None = None,
        algorithm: str = "HS256",
        issuer: str = "ai-operations-platform",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        _secret = secret or load_jwt_config().secret
        if not _secret or _secret == "mysecretkey":
            raise RuntimeError(
                "JWT_SECRET is missing or insecure! Set a strong value in your environment."
            )
        self.secret: str = _secret
        self.algorithm = algorithm
        self.issuer = issuer
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()
        now = datetime.utcnow()
        expire = now + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "iss": self.issuer,
                "token_type": "access",
            }
        )
        return str(jwt.encode(to_encode, self.secret, algorithm=self.algorithm))

    def create_refresh_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()
        now = datetime.now(UTC)
        expire = now + (expires_delta or timedelta(days=self.refresh_token_expire_days))
        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "iss": self.issuer,
                "token_type": "refresh",
            }
        )
        return str(jwt.encode(to_encode, self.secret, algorithm=self.algorithm))

    def verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
            )
            return dict(payload) if payload else None
        except JWTError:
            return None
