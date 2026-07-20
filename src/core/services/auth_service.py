"""
Authentication service for API key management and validation.

This service handles API key creation, validation, permission checking,
and integrates with storage for persistence.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import bcrypt
from fastapi import HTTPException, status

from src.config import settings
from src.config.auth_constants import AUTH_MODE_ENV, AUTH_MODE_HYBRID, AUTH_MODE_STORAGE
from src.config.security_policy import get_security_policy

from ..federation.identity import (
    NodeIdentity,
    generate_identity,
    sign_payload,
    verify_payload,
)
from ..models.account import ROOT_ACCOUNT_ID, Account, AccountCreate
from ..models.auth import APIKey, APIKeyCreate, APIKeyResponse, AuthenticatedUser
from ..models.capability import (
    KNOWN_SCOPE_KINDS,
    CapabilityGrant,
    Scope,
    is_known_verb,
)
from ..models.identity import Identity, IdentityKind, IdentityLink
from ..services.storage_service import StorageService
from ..storage.account_storage import AccountStorage
from ..storage.auth_storage import AuthStorage
from ..storage.grant_store import GrantStore
from ..storage.identity_key_store import IdentityKeyStore

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for authentication and authorization."""

    _instance = None
    _cache: Dict[UUID, Tuple[APIKey, datetime]] = {}
    _cache_ttl = timedelta(minutes=5)

    def __init__(self):
        """Initialize authentication service."""
        self._auth_storage: Optional[AuthStorage] = None
        self._account_storage: Optional[AccountStorage] = None
        self._identity_store: Optional[IdentityKeyStore] = None
        self._grant_store: Optional[GrantStore] = None
        self._node_signing: Optional[NodeIdentity] = None
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
            self._account_storage = AccountStorage(storage_service)
            self._grant_store = GrantStore(storage_service)
            self._identity_store = IdentityKeyStore(
                Path(settings.OHM_FEDERATION_DATA_DIR)
            )
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
        auth_mode = getattr(settings, "AUTH_MODE", AUTH_MODE_HYBRID)

        # Check environment variable keys if mode allows
        if auth_mode in (AUTH_MODE_ENV, AUTH_MODE_HYBRID):
            env_user = self._check_env_keys(token)
            if env_user:
                return env_user

        # Check storage-based keys if mode allows
        if auth_mode in (AUTH_MODE_STORAGE, AUTH_MODE_HYBRID):
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
                                account_id=self._account_id_from_key(key),
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

    @staticmethod
    def _account_id_from_key(key: APIKey) -> UUID:
        """Resolve the owning account for a stored key (``created_by`` holds it)."""
        try:
            return UUID(str(key.created_by))
        except (ValueError, TypeError):
            return ROOT_ACCOUNT_ID

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

        # Bind the key to an owning account (defaults to the root account).
        account_id = key_data.account_id or ROOT_ACCOUNT_ID

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
            created_by=str(account_id),
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
                    account_id=ROOT_ACCOUNT_ID,  # attribute env keys to the root account
                )

        return None

    async def create_account(self, data: AccountCreate) -> Account:
        """Create and persist a new account (person or space)."""
        if not self._account_storage:
            raise RuntimeError("Storage not available for account creation")
        account = Account(display_name=data.display_name, kind=data.kind)
        await self._account_storage.save_account(account)
        logger.info(f"Created account {account.id} ({account.kind.value})")
        return account

    async def list_accounts(self) -> List[Account]:
        """List all accounts (empty when storage is unavailable)."""
        if not self._account_storage:
            return []
        return await self._account_storage.list_accounts()

    async def disable_account(self, account_id: UUID) -> Account:
        """Disable an account so it can no longer be used for new grants/keys."""
        if not self._account_storage:
            raise RuntimeError("Storage not available for account management")
        account = await self._account_storage.load_account(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
            )
        account.disabled = True
        await self._account_storage.save_account(account)
        logger.info(f"Disabled account {account_id}")
        return account

    # ------------------------------------------------------------------
    # Self-sovereign identity (Slice 2)
    # ------------------------------------------------------------------

    def _node_signing_identity(self) -> Optional[NodeIdentity]:
        """Load this node's federation signing identity (trust root), if present.

        Read-only: never creates a node identity as a side effect of authz.
        """
        if self._node_signing is not None:
            return self._node_signing
        path = Path(settings.OHM_FEDERATION_DATA_DIR).expanduser() / "identity.json"
        if path.is_file():
            self._node_signing = NodeIdentity.from_identity_file(
                json.loads(path.read_text(encoding="utf-8"))
            )
        return self._node_signing

    def _signing_key_for(self, did: str) -> Optional[NodeIdentity]:
        """Return a held signing key for ``did`` (node identity or local identity)."""
        node = self._node_signing_identity()
        if node and node.did == did:
            return node
        if self._identity_store:
            return self._identity_store.load_signing_key(did)
        return None

    async def create_identity(
        self,
        account_id: UUID,
        kind: IdentityKind = IdentityKind.PERSON,
        display_name: str = "",
    ) -> Identity:
        """Mint a new Ed25519 identity and bind it to ``account_id`` (custodial)."""
        if not self._identity_store:
            raise RuntimeError("Identity store not available")
        signing_key = generate_identity(display_name or str(account_id))
        identity = Identity(
            did=signing_key.did,
            kind=kind,
            display_name=display_name or str(account_id),
            account_id=str(account_id),
            custodial=True,
        )
        self._identity_store.save(signing_key, identity)
        logger.info(f"Minted identity {identity.did} for account {account_id}")
        return identity

    def get_identity(self, did: str) -> Optional[Identity]:
        """Return the public identity record for ``did``, if held locally."""
        if not self._identity_store:
            return None
        return self._identity_store.load_identity(did)

    async def rotate_identity(self, did: str) -> Identity:
        """Rotate ``did`` to a fresh keypair, linking old -> new (signed by old)."""
        if not self._identity_store:
            raise RuntimeError("Identity store not available")
        old_key = self._identity_store.load_signing_key(did)
        old_identity = self._identity_store.load_identity(did)
        if not old_key or not old_identity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found"
            )

        new_key = generate_identity(old_identity.display_name)
        link = IdentityLink(
            from_did=did,
            to_did=new_key.did,
            reason="rotation",
            signed_by=did,
            signature="",
        )
        link.signature = sign_payload(old_key.private_key, link.signing_payload())

        new_identity = Identity(
            did=new_key.did,
            kind=old_identity.kind,
            display_name=old_identity.display_name,
            account_id=old_identity.account_id,
            custodial=old_identity.custodial,
            links_in=[*old_identity.links_in, link],
        )
        self._identity_store.save(new_key, new_identity)
        logger.info(f"Rotated identity {did} -> {new_key.did}")
        return new_identity

    # ------------------------------------------------------------------
    # Capability grants (Slice 2)
    # ------------------------------------------------------------------

    async def issue_grant(
        self,
        issuer_did: str,
        subject_did: str,
        permissions: List[str],
        scope: Scope,
        ttl_days: Optional[int] = None,
        coarse_floor: Optional[List[str]] = None,
    ) -> CapabilityGrant:
        """Issue and sign a capability grant.

        Slice 2 trust root: the issuer must be a key this node holds (the node
        identity, or a locally-held identity issuing to itself — the edge
        bootstrap / self-asserted case).
        """
        if not self._grant_store:
            raise RuntimeError("Grant store not available")
        signing_key = self._signing_key_for(issuer_did)
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for issuer; cannot issue grant",
            )

        ttl = ttl_days if ttl_days is not None else get_security_policy().grant_ttl_days
        now = datetime.utcnow()
        grant = CapabilityGrant(
            issuer_did=issuer_did,
            subject_did=subject_did,
            permissions=permissions,
            coarse_floor=coarse_floor or ["read"],
            scope=scope,
            issued_at=now,
            expires_at=now + timedelta(days=ttl),
        )
        grant.signature = sign_payload(signing_key.private_key, grant.signing_payload())
        await self._grant_store.save_grant(grant)
        logger.info(f"Issued grant {grant.grant_id} to {subject_did} on {scope.key()}")
        return grant

    async def list_grants(self, subject_did: str) -> List[CapabilityGrant]:
        """List all grants whose subject is ``subject_did``."""
        if not self._grant_store:
            return []
        return await self._grant_store.list_for_subject(subject_did)

    async def revoke_grant(self, grant_id: UUID) -> None:
        """Revoke (delete) a grant by id."""
        if not self._grant_store:
            raise RuntimeError("Grant store not available")
        await self._grant_store.delete_grant(grant_id)
        logger.info(f"Revoked grant {grant_id}")

    def _is_issuer_trusted(self, grant: CapabilityGrant) -> bool:
        """Slice 2 trust root: local node identity, or a self-asserted issuer.

        Self-asserted grants (issuer == subject, e.g. isolated edge bootstrap) are
        honored *locally* but carry no global weight until a peer endorses them.
        """
        node = self._node_signing_identity()
        if node and grant.issuer_did == node.did:
            return True
        return grant.issuer_did == grant.subject_did

    def verify_grant(self, grant: CapabilityGrant) -> bool:
        """Offline validity: signature + time window + known scope kind.

        Does *not* consult the trust root or the requested scope — those are
        applied in :meth:`resolve_capabilities`.
        """
        if not verify_payload(
            grant.issuer_did, grant.signing_payload(), grant.signature
        ):
            return False
        now = datetime.utcnow()
        if grant.not_before and now < grant.not_before:
            return False
        if now >= grant.expires_at:
            return False
        if grant.scope.kind not in KNOWN_SCOPE_KINDS:
            return False  # fail closed on unknown scope kind
        return True

    def _grant_effective_permissions(self, grant: CapabilityGrant) -> Set[str]:
        """Effective permissions a valid, trusted grant confers.

        Known verbs from ``permissions`` unioned with the coarse floor (the floor
        is honored even when the node does not understand the richer verbs).
        """
        known = {p for p in grant.permissions if is_known_verb(p)}
        return known | set(grant.coarse_floor)

    async def resolve_capabilities(self, subject_did: str, scope: Scope) -> Set[str]:
        """Effective permissions for ``subject_did`` on ``scope`` (fully offline).

        Implements the 6-step verification: for each of the subject's grants that
        matches the requested scope, honor it only if it verifies (signature/time/
        known-kind) and its issuer is trusted; union the effective permissions.
        """
        if not self._grant_store:
            return set()
        effective: Set[str] = set()
        for grant in await self._grant_store.list_for_subject(subject_did):
            if grant.scope.key() != scope.key():
                continue
            if not self.verify_grant(grant):
                continue
            if not self._is_issuer_trusted(grant):
                continue  # untrusted issuer -> contributes nothing
            effective |= self._grant_effective_permissions(grant)
        return effective
