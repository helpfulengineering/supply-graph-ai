"""
Authentication service for API key management and validation.

This service handles API key creation, validation, permission checking,
and integrates with storage for persistence.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import bcrypt
from fastapi import HTTPException, status

from src.config import settings

from ..models.auth import APIKey, APIKeyCreate, APIKeyResponse, AuthenticatedUser
from ..services.storage_service import StorageService
from ..storage.auth_storage import AuthStorage

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for authentication and authorization."""

    _instance = None
    _cache: Dict[UUID, Tuple[APIKey, datetime]] = {}
    _cache_ttl = timedelta(minutes=5)

    def __init__(self):
        """Initialize authentication service."""
        self._auth_storage: Optional[AuthStorage] = None
        self._initialized = False

    @classmethod
    async def get_instance(cls) -> "AuthenticationService":
        """Get singleton instance of authentication service."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self) -> None:
        """Initialize the service with dependencies."""
        if self._initialized:
            return

        try:
            storage_service = await StorageService.get_instance()
            self._auth_storage = AuthStorage(storage_service)
            self._initialized = True
            logger.info("Authentication service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {e}")
            # Service can still work with env keys even if storage fails
            self._initialized = True

    def _hash_token(self, token: str) -> str:
        """
        Hash a token using bcrypt.

        Args:
            token: Plain text token to hash

        Returns:
            Hashed token string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(token.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def _verify_token(self, token: str, key_hash: str) -> bool:
        """
        Verify a token against its hash.

        Args:
            token: Plain text token to verify
            key_hash: Hashed token to verify against

        Returns:
            True if token matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(token.encode("utf-8"), key_hash.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return False

    def _generate_token(self, length: int = 32) -> str:
        """
        Generate a secure random token.

        Args:
            length: Length of token in bytes (default 32)

        Returns:
            Base64-encoded token string
        """
        import base64

        token_bytes = secrets.token_bytes(length)
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")
        return token

    async def validate_api_key(self, token: str) -> AuthenticatedUser:
        """
        Validate an API key token and return authenticated user.

        Args:
            token: Plain text API key token

        Returns:
            AuthenticatedUser with key_id, name, and permissions

        Raises:
            HTTPException with 401 if invalid/expired/revoked
        """
        # Check AUTH_MODE setting to determine which sources to check
        auth_mode = getattr(settings, "AUTH_MODE", "hybrid")

        # Check environment variable keys if mode allows
        if auth_mode in ("env", "hybrid"):
            env_user = self._check_env_keys(token)
            if env_user:
                return env_user

        # Check storage-based keys if mode allows
        if auth_mode in ("storage", "hybrid"):
            if self._auth_storage:
                try:
                    # List all keys and find matching one
                    keys = await self._auth_storage.list_keys()

                    for key in keys:
                        if self._verify_token(token, key.key_hash):
                            # Check if key is revoked
                            if key.revoked:
                                logger.warning(
                                    f"Attempted use of revoked key: {key.key_id}"
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="API key has been revoked",
                                )

                            # Check if key is expired
                            if key.expires_at and key.expires_at < datetime.utcnow():
                                logger.warning(
                                    f"Attempted use of expired key: {key.key_id}"
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="API key has expired",
                                )

                            # Update last_used_at
                            key.last_used_at = datetime.utcnow()
                            await self._auth_storage.save_key(key)

                            # Cache the key
                            self._cache[key.key_id] = (key, datetime.utcnow())

                            logger.info(f"Successfully authenticated key: {key.key_id}")
                            return AuthenticatedUser(
                                key_id=key.key_id,
                                name=key.name,
                                permissions=key.permissions,
                            )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error validating API key from storage: {e}")
                    # Fall through to raise 401

        # Token not found
        logger.warning("Invalid API key token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    async def check_permission(
        self, user: AuthenticatedUser, required_permissions: List[str]
    ) -> bool:
        """
        Check if user has required permissions.

        Args:
            user: Authenticated user
            required_permissions: List of required permissions

        Returns:
            True if user has all required permissions
        """
        if not required_permissions:
            return True

        user_permissions = set(user.permissions)

        # Admin has all permissions
        if "admin" in user_permissions:
            return True

        # Check each required permission
        for required in required_permissions:
            # Check exact match
            if required in user_permissions:
                continue

            # Check permission hierarchy: write implies read
            if required == "read" and "write" in user_permissions:
                continue

            # Check domain permissions
            if required.startswith("domain:"):
                if required in user_permissions:
                    continue

            # Permission not found
            return False

        return True

    async def create_api_key(self, key_data: APIKeyCreate) -> APIKeyResponse:
        """
        Create a new API key.

        Args:
            key_data: Key creation data

        Returns:
            APIKeyResponse with generated token (only time it's returned)
        """
        if not self._auth_storage:
            raise RuntimeError("Storage not available for API key creation")

        # Generate token
        token = self._generate_token(
            settings.AUTH_KEY_LENGTH if hasattr(settings, "AUTH_KEY_LENGTH") else 32
        )
        key_hash = self._hash_token(token)

        # Create API key
        api_key = APIKey(
            key_id=uuid4(),
            key_hash=key_hash,
            name=key_data.name,
            description=key_data.description,
            permissions=key_data.permissions,
            created_at=datetime.utcnow(),
            expires_at=key_data.expires_at,
            revoked=False,
            created_by="system",
        )

        # Save to storage
        await self._auth_storage.save_key(api_key)

        logger.info(f"Created new API key: {api_key.key_id}")

        # Return response with token (only time it's returned)
        return APIKeyResponse(
            key_id=api_key.key_id,
            name=api_key.name,
            description=api_key.description,
            permissions=api_key.permissions,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            revoked=api_key.revoked,
            token=token,
        )

    async def revoke_api_key(self, key_id: UUID) -> None:
        """
        Revoke an API key.

        Args:
            key_id: UUID of the key to revoke
        """
        if not self._auth_storage:
            raise RuntimeError("Storage not available for API key revocation")

        # Load key
        key = await self._auth_storage.load_key(key_id)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Revoke key
        key.revoked = True
        await self._auth_storage.save_key(key)

        # Remove from cache
        if key_id in self._cache:
            del self._cache[key_id]

        logger.info(f"Revoked API key: {key_id}")

    async def list_api_keys(self) -> List[APIKeyResponse]:
        """
        List all API keys (without tokens).

        Returns:
            List of APIKeyResponse instances
        """
        if not self._auth_storage:
            return []

        keys = await self._auth_storage.list_keys()

        return [
            APIKeyResponse(
                key_id=key.key_id,
                name=key.name,
                description=key.description,
                permissions=key.permissions,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                revoked=key.revoked,
                token=None,  # Never return tokens in list
            )
            for key in keys
        ]

    def _check_env_keys(self, token: str) -> Optional[AuthenticatedUser]:
        """
        Check environment variable keys (backward compatibility).

        Args:
            token: Plain text token to check

        Returns:
            AuthenticatedUser if token matches env key, None otherwise
        """
        env_keys = getattr(settings, "API_KEYS", [])
        if not env_keys:
            return None

        # Check if token matches any env key
        for env_key in env_keys:
            if env_key and env_key.strip() == token.strip():
                logger.info("Authenticated using environment variable key")
                return AuthenticatedUser(
                    key_id=UUID(
                        "00000000-0000-0000-0000-000000000000"
                    ),  # Dummy UUID for env keys
                    name="Environment Key",
                    permissions=["read", "write", "admin"],  # Env keys have full access
                )

        return None
