"""
Authentication service for API key management and validation.

This service handles API key creation, validation, permission checking,
and integrates with storage for persistence.
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import bcrypt
from fastapi import HTTPException, status

from src.config import settings
from src.config.auth_constants import AUTH_MODE_ENV, AUTH_MODE_HYBRID, AUTH_MODE_STORAGE
from src.config.security_policy import (
    allows_full_metadata_logging,
    get_security_policy,
)

from ..federation.identity import (
    NodeIdentity,
    generate_identity,
    sign_payload,
    verify_payload,
)
from ..models.account import ROOT_ACCOUNT_ID, Account, AccountCreate
from ..models.auth import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    AuthenticatedUser,
    RegistrationResponse,
)
from ..models.capability import (
    KNOWN_SCOPE_KINDS,
    CapabilityGrant,
    Scope,
    is_known_verb,
)
from ..models.identity import Identity, IdentityKind, IdentityLink
from ..models.visibility import ANONYMOUS_SCOPE, ViewerScope
from ..models.provenance import RecordProvenance, sign_provenance
from ..models.attestation import (
    KNOWN_ATTESTATION_TYPES,
    Attestation,
    verify_attestation,
)
from ..models.binding import (
    DirectoryEntry,
    IdentityBinding,
    domain_external_id,
    oauth_external_id,
    well_known_document,
    well_known_url,
)
from ..models.space import SpaceClaim
from ..services.domain_bind import WellKnownFetcher, fetch_and_validate_domain
from ..services.storage_service import StorageService
from ..storage.account_storage import AccountStorage
from ..storage.attestation_store import AttestationStore
from ..storage.auth_storage import AuthStorage
from ..storage.binding_store import BindingStore, DirectoryStore
from ..storage.grant_store import GrantStore
from ..storage.identity_key_store import IdentityKeyStore
from ..storage.space_claim_store import SpaceClaimStore

logger = logging.getLogger(__name__)


#: What a credential minted without an operator in the loop may ever carry.
#: Three paths reach it now — registration, recovery-code redemption, and a
#: person minting their own second key — and none may hand out `admin`.
#: Recovery especially, since the account it restores might have held it, and
#: self-service key creation, since otherwise "manage your own keys" would be a
#: route to it. Stated once because two copies of a permission floor is one too
#: many.
SELF_SERVICE_PERMISSIONS = ["read", "write"]


class AuthenticationService:
    """Service for authentication and authorization."""

    _instance = None

    def __init__(self):
        """Initialize authentication service."""
        # None until first asked; see _legacy_keys. Never holds key material.
        self._has_legacy_keys: Optional[bool] = None
        self._auth_storage: Optional[AuthStorage] = None
        self._account_storage: Optional[AccountStorage] = None
        self._identity_store: Optional[IdentityKeyStore] = None
        self._grant_store: Optional[GrantStore] = None
        self._space_claim_store: Optional[SpaceClaimStore] = None
        self._attestation_store: Optional[AttestationStore] = None
        self._binding_store: Optional[BindingStore] = None
        self._directory_store: Optional[DirectoryStore] = None
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
            self._space_claim_store = SpaceClaimStore(storage_service)
            self._attestation_store = AttestationStore(storage_service)
            self._binding_store = BindingStore(storage_service)
            self._directory_store = DirectoryStore(storage_service)
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

    def _verify_token(self, token: str, key: APIKey) -> bool:
        """Verify a presented token against a stored key.

        Digest comparison for keys that carry one, bcrypt for the pre-#409 keys
        that do not. bcrypt is not doing security work for the first group: it
        exists to make guessing a *password* expensive, and these tokens are 256
        bits of CSPRNG output with nothing to guess. Since #409 stores a SHA-256
        of the token beside the bcrypt hash, an attacker holding the store
        already holds the weaker artifact — so bcrypt was costing 186ms on every
        request while raising no floor.

        Compared against the digest on the **key record**, never against the one
        the lookup was made with. That is what keeps a write to the index from
        being an authentication bypass: pointing a digest at someone else's key
        still fails, because that key's own digest does not match the presented
        token.
        """
        try:
            if key.token_digest:
                return secrets.compare_digest(
                    self._token_digest(token), key.token_digest
                )
            return bcrypt.checkpw(token.encode("utf-8"), key.key_hash.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return False

    @staticmethod
    def _token_digest(token: str) -> str:
        """SHA-256 of a token, used purely as a lookup key (#409).

        Deliberately not a stretching function. Stretching defends a *password*,
        whose entropy is low enough to brute-force offline; these tokens are 256
        bits of CSPRNG output, so there is nothing to brute-force and a plain
        digest is as unreversible as anything slower would be. bcrypt still does
        the verification — this only decides which single key to verify against.
        """
        return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

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

    async def _legacy_keys(self) -> List[APIKey]:
        """Keys issued before #409, which have no digest to look up by.

        A bcrypt hash cannot be reversed, so these can never be backfilled — the
        plaintext token exists only wherever its owner put it. They therefore
        keep the old scan, bounded to however many pre-#409 keys a node has
        (operator-made, typically single digits) rather than to every key ever
        issued. The set only shrinks: every key minted from now on is
        addressable, so the scan disappears as the old ones are rotated out.

        Guarded by a one-shot check, because this is also the path an *unknown*
        token takes: without the guard a bogus token would still cost a full
        listing of the key store on every request — no bcrypt, but one object
        read per key, which is the same denial-of-service shape a step quieter.
        Nodes with no pre-#409 keys, which is every new deployment, never list.

        The check memoises only *whether* legacy keys exist, never the keys
        themselves: a cached key object would let a since-revoked key keep
        authenticating from a stale ``revoked`` flag.
        """
        if not self._auth_storage or self._has_legacy_keys is False:
            return []
        legacy = [k for k in await self._auth_storage.list_keys() if not k.token_digest]
        if self._has_legacy_keys is None:
            self._has_legacy_keys = bool(legacy)
            if legacy:
                logger.warning(
                    f"{len(legacy)} API key(s) predate the digest index and still "
                    "require a scan to authenticate; rotate them to remove it"
                )
        return legacy

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
                    # One lookup, then one digest comparison (#409). Before
                    # this, every request bcrypt-checked keys until one matched,
                    # so an invalid token cost a full scan — 186ms per key on
                    # the machine this was measured on — and self-service
                    # registration made the key count grow without bound.
                    candidate = await self._auth_storage.find_by_digest(
                        self._token_digest(token)
                    )
                    keys = [candidate] if candidate else await self._legacy_keys()

                    for key in keys:
                        if self._verify_token(token, key):
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

                            logger.info(f"Successfully authenticated key: {key.key_id}")
                            account_id = self._account_id_from_key(key)
                            return AuthenticatedUser(
                                key_id=key.key_id,
                                name=key.name,
                                permissions=key.permissions,
                                account_id=account_id,
                                subject_did=self._subject_did_for(account_id),
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

    def _subject_did_for(self, account_id: UUID) -> Optional[str]:
        """The primary DID bound to ``account_id``, if this node holds one."""
        if self._identity_store:
            return self._identity_store.find_primary_did(str(account_id))
        return None

    def viewer_scope(self, user: Optional[AuthenticatedUser]) -> ViewerScope:
        """Resolve which records ``user`` may see in a list.

        Walks the rotation chain: a rotated identity carries every DID it
        supersedes, so ownership survives a key rotation. Without this, rotating
        your key hides your own drafts from you.

        ``admin`` is deliberately not consulted — an admin's record scope is
        identical to any other authenticated user's (ADR §9).
        """
        if user is None:
            return ANONYMOUS_SCOPE
        dids: set[str] = set()
        if user.subject_did:
            dids.add(user.subject_did)
            identity = (
                self._identity_store.load_identity(user.subject_did)
                if self._identity_store
                else None
            )
            if identity:
                dids.update(link.from_did for link in identity.links_in)
        return ViewerScope(account_id=str(user.account_id), dids=frozenset(dids))

    async def check_permission(
        self,
        user: AuthenticatedUser,
        required_permissions: List[str],
        scope: Optional[Scope] = None,
    ) -> bool:
        """
        Check if user has required permissions.

        Args:
            user: Authenticated user
            required_permissions: List of required permissions
            scope: When provided and the user has a subject DID, capability grants
                resolved for that DID on ``scope`` are unioned with the key's own
                (implicit-grant) permissions. Omitting ``scope`` preserves the
                legacy flat-key behavior exactly.

        Returns:
            True if user has all required permissions
        """
        if not required_permissions:
            return True

        user_permissions = set(user.permissions)
        if scope is not None and user.subject_did:
            user_permissions |= await self.resolve_capabilities(user.subject_did, scope)

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
            token_digest=self._token_digest(token),
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

        logger.info(f"Revoked API key: {key_id}")

    @staticmethod
    def _owns(key: APIKey, account_id: UUID) -> bool:
        """Whether ``key`` belongs to ``account_id``."""
        return str(key.created_by) == str(account_id)

    async def list_api_keys_for(self, user: AuthenticatedUser) -> List[APIKeyResponse]:
        """The keys ``user`` may see: their own, or all of them for an admin.

        Same scoping move #403 made for records, applied to the identity plane.
        An admin's node-wide view is unchanged; what changes is that an ordinary
        person now has one at all, over their own keys.
        """
        keys = await self.list_api_keys()
        if "admin" in user.permissions:
            return keys
        owned = {
            k.key_id
            for k in (
                await self._auth_storage.list_keys() if self._auth_storage else []
            )
            if self._owns(k, user.account_id)
        }
        return [k for k in keys if k.key_id in owned]

    async def revoke_api_key_for(self, user: AuthenticatedUser, key_id: UUID) -> None:
        """Revoke ``key_id`` if ``user`` may.

        A key belonging to someone else is refused exactly as a key that does
        not exist is: otherwise the error message is an oracle for which key ids
        are real.
        """
        if "admin" not in user.permissions:
            if not self._auth_storage:
                raise RuntimeError("Storage not available for API key revocation")
            key = await self._auth_storage.load_key(key_id)
            if key is None or not self._owns(key, user.account_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
                )
        await self.revoke_api_key(key_id)

    async def revoke_other_keys(self, user: AuthenticatedUser) -> int:
        """Revoke every key on the caller's account except the one in use.

        The realistic panic is "I pasted my key somewhere I should not have",
        and asking someone in that state to enumerate and revoke individually is
        the wrong thing to ask. Returns how many were revoked.
        """
        if not self._auth_storage:
            raise RuntimeError("Storage not available for API key revocation")
        revoked = 0
        for key in await self._auth_storage.list_keys():
            if (
                self._owns(key, user.account_id)
                and key.key_id != user.key_id
                and not key.revoked
            ):
                key.revoked = True
                await self._auth_storage.save_key(key)
                revoked += 1
        logger.info(f"Revoked {revoked} other key(s) for account {user.account_id}")
        return revoked

    async def renew_api_key(
        self, user: AuthenticatedUser, key_id: UUID
    ) -> APIKeyResponse:
        """Push a key's expiry out by the policy TTL, without minting a new one.

        Renewal keeps the same token, so nothing has to be re-pasted anywhere it
        is already stored — which is the whole point of having it rather than
        telling people to create a replacement.
        """
        if not self._auth_storage:
            raise RuntimeError("Storage not available for API key renewal")
        key = await self._auth_storage.load_key(key_id)
        if key is None or (
            "admin" not in user.permissions and not self._owns(key, user.account_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )
        if key.revoked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A revoked key cannot be renewed",
            )
        key.expires_at = datetime.utcnow() + timedelta(
            days=get_security_policy().key_ttl_days
        )
        await self._auth_storage.save_key(key)
        return APIKeyResponse(
            key_id=key.key_id,
            name=key.name,
            description=key.description,
            permissions=key.permissions,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            revoked=key.revoked,
            token=None,
        )

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
            # Constant-time: a plain == leaks the length of the shared prefix,
            # which is a usable oracle against a configured secret.
            if env_key and secrets.compare_digest(env_key.strip(), token.strip()):
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

    async def register(self, display_name: str) -> RegistrationResponse:
        """Self-service onboarding: account + person DID + first key, in one call.

        The permission floor is ``read``+``write`` and never ``admin`` — a node
        must not hand out operator rights to anyone who can reach the endpoint.
        Refused when the active mode closes registration (shielded), where
        onboarding is deliberately an out-of-band, hand-vetted act.
        """
        policy = get_security_policy()
        if not policy.open_registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Self-service registration is disabled in "
                    f"{policy.mode.value} mode; ask an operator to mint an account"
                ),
            )
        account = await self.create_account(AccountCreate(display_name=display_name))
        identity = await self.create_identity(
            account.id, IdentityKind.PERSON, display_name
        )
        key = await self.create_api_key(
            APIKeyCreate(
                name=f"{display_name} (first key)",
                description="Issued by self-service registration",
                permissions=list(SELF_SERVICE_PERMISSIONS),
                account_id=account.id,
                # Bounded, so an abandoned key stops working on its own.
                expires_at=datetime.utcnow()
                + timedelta(days=get_security_policy().key_ttl_days),
            )
        )
        recovery_code = await self._issue_recovery_code(account)
        logger.info(f"Registered account {account.id} with identity {identity.did}")
        return RegistrationResponse(
            account_id=account.id,
            display_name=account.display_name,
            did=identity.did,
            key=key,
            recovery_code=recovery_code,
        )

    async def _issue_recovery_code(self, account: Account) -> str:
        """Mint a fresh recovery code for ``account`` and return it once.

        Same generator as an API token, so the same entropy argument holds: 256
        bits of CSPRNG output has no brute-force surface, which is what makes a
        plain digest a sound lookup key and means guessing is not the threat a
        rate limit has to stop. Only the digest is persisted.
        """
        code = self._generate_token()
        await self._account_storage.bind_recovery_digest(
            account, self._token_digest(code)
        )
        return code

    async def redeem_recovery_code(self, code: str) -> RegistrationResponse:
        """Trade a recovery code for a working key on the same account and DID.

        Serves two cases that want the same outcome — "I lost my token" and "my
        token leaked" — so it revokes the account's existing keys rather than
        adding to them, and replaces the code it consumed.
        """
        policy = get_security_policy()
        if not policy.open_registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Self-service recovery is disabled in "
                    f"{policy.mode.value} mode; ask an operator to reissue a key"
                ),
            )
        if not self._account_storage or not self._auth_storage:
            raise RuntimeError("Storage not available for recovery")

        digest = self._token_digest(code)
        account = await self._account_storage.find_by_recovery_digest(digest)
        # Verified against the account's own stored digest, never against the
        # index that found it: otherwise writing a pointer would be enough to
        # take over an account without holding its code.
        if (
            account is None
            or not account.recovery_digest
            or not secrets.compare_digest(digest, account.recovery_digest)
        ):
            logger.warning("Recovery attempted with an unrecognised code")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="That recovery code is not valid",
            )
        if account.disabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="That account is disabled",
            )

        for existing in await self._auth_storage.list_keys():
            if str(existing.created_by) == str(account.id) and not existing.revoked:
                existing.revoked = True
                await self._auth_storage.save_key(existing)

        key = await self.create_api_key(
            APIKeyCreate(
                name=f"{account.display_name} (recovered)",
                description="Issued by recovery-code redemption",
                # Never inherits what the account held: a way back in, not a way up.
                permissions=list(SELF_SERVICE_PERMISSIONS),
                account_id=account.id,
            )
        )
        replacement = await self._issue_recovery_code(account)
        did = self._subject_did_for(account.id)
        if not did:
            # Recovery that cannot restore the identity binding is not recovery:
            # the DID is what record ownership keys on, so returning a blank one
            # would hand back a key that owns nothing the account made.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="This node no longer holds the identity for that account",
            )
        logger.info(f"Recovered account {account.id}")
        return RegistrationResponse(
            account_id=account.id,
            display_name=account.display_name,
            did=did,
            key=key,
            recovery_code=replacement,
        )

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

    def sign_provenance_if_possible(
        self, provenance: RecordProvenance
    ) -> RecordProvenance:
        """Sign a provenance claim if this node holds the relevant author/space key.

        Best-effort content trust: the signer is the publisher, then the space,
        then the first authoring DID. If no key is held (e.g. a non-DID author or
        a remote subject), the provenance is returned unsigned — an unverified but
        still-federated claim.
        """
        signer = provenance.published_by or provenance.on_behalf_of
        if not signer:
            signer = next(
                (c.subject_did for c in provenance.authored_by if c.subject_did), None
            )
        if signer:
            key = self._signing_key_for(signer)
            if key:
                sign_provenance(provenance, key.private_key, signer)
        return provenance

    def local_node_scope(self) -> Optional[Scope]:
        """The node-scoped :class:`Scope` writes are authorized against, if any.

        ``None`` when this node has no federation identity yet — in which case
        grant-based authorization is simply unavailable and only flat-key
        permissions apply.
        """
        node = self._node_signing_identity()
        return Scope(kind="node", target=node.did) if node else None

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
        """Mint a new Ed25519 identity and bind it to ``account_id`` (custodial).

        Shielded mode disables custodial minting (``custodial_keys_allowed=False``).
        """
        if not self._identity_store:
            raise RuntimeError("Identity store not available")
        if not get_security_policy().custodial_keys_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Custodial identity minting is disabled under the active "
                    "security mode; bring your own key or switch mode"
                ),
            )
        signing_key = generate_identity(display_name or str(account_id))
        identity = Identity(
            did=signing_key.did,
            kind=kind,
            display_name=display_name or str(account_id),
            account_id=str(account_id),
            custodial=True,
        )
        self._identity_store.save(signing_key, identity)
        if allows_full_metadata_logging():
            logger.info(f"Minted identity {identity.did} for account {account_id}")
        else:
            logger.debug("Minted custodial identity")
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

    def _is_followed_peer(self, did: str) -> bool:
        """True if ``did`` is on this node's federation follow allowlist."""
        try:
            from ..federation.store import FederationStore

            if not getattr(settings, "OHM_FEDERATION_ENABLED", False):
                return False
            return FederationStore(Path(settings.OHM_FEDERATION_DATA_DIR)).is_followed(
                did
            )
        except Exception:
            return False

    async def _is_issuer_trusted(self, grant: CapabilityGrant) -> bool:
        """Trust roots (Slices 2 + 5): local node, self-asserted, space admin, peer.

        - Local node identity — always trusted.
        - Self-asserted (issuer == subject) — edge bootstrap; honored locally only.
        - Claimed space admin — trusted for grants whose scope is that space.
        - Followed peer DID — trusted as a local issuer for its cluster.
        """
        node = self._node_signing_identity()
        if node and grant.issuer_did == node.did:
            return True
        if grant.issuer_did == grant.subject_did:
            return True
        if self._is_followed_peer(grant.issuer_did):
            return True
        if grant.scope.kind == "space":
            claim = await self.get_space_claim(grant.scope.target)
            if (
                claim
                and claim.admin_did == grant.issuer_did
                and verify_payload(
                    claim.space_did, claim.signing_payload(), claim.signature
                )
            ):
                return True
        return False

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
            if not await self._is_issuer_trusted(grant):
                continue  # untrusted issuer -> contributes nothing
            effective |= self._grant_effective_permissions(grant)
        return effective

    # ------------------------------------------------------------------
    # Space claims + edge bootstrap (Slice 5)
    # ------------------------------------------------------------------

    async def claim_space(self, space_did: str, admin_did: str) -> SpaceClaim:
        """TOFU-claim ``space_did`` for ``admin_did`` (first claimer wins).

        The space key signs the claim. Requires this node to hold the space
        signing key and for ``space_did`` to be a SPACE identity. Domain
        binding is out of scope for peacetime Slice 5.
        """
        if not self._space_claim_store or not self._identity_store:
            raise RuntimeError("Space claim store not available")

        space = self._identity_store.load_identity(space_did)
        if not space or space.kind is not IdentityKind.SPACE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="space_did must refer to a locally held SPACE identity",
            )
        admin = self._identity_store.load_identity(admin_did)
        if not admin or admin.kind is not IdentityKind.PERSON:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_did must refer to a locally held PERSON identity",
            )

        existing = await self._space_claim_store.load(space_did)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Space already claimed by {existing.admin_did}",
            )

        space_key = self._identity_store.load_signing_key(space_did)
        if not space_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for space; cannot claim",
            )

        claim = SpaceClaim(space_did=space_did, admin_did=admin_did)
        claim.signature = sign_payload(space_key.private_key, claim.signing_payload())
        await self._space_claim_store.save(claim)
        logger.info(f"Space {space_did} claimed by admin {admin_did}")
        return claim

    async def get_space_claim(self, space_did: str) -> Optional[SpaceClaim]:
        """Return the TOFU claim for ``space_did``, if any."""
        if not self._space_claim_store:
            return None
        return await self._space_claim_store.load(space_did)

    async def list_space_claims(self) -> List[SpaceClaim]:
        """List every space claim held by this node."""
        if not self._space_claim_store:
            return []
        return await self._space_claim_store.list_all()

    async def bootstrap_edge_grant(
        self,
        subject_did: str,
        permissions: Optional[List[str]] = None,
        ttl_days: Optional[int] = None,
    ) -> CapabilityGrant:
        """Self-issue a genesis capability on the local node scope (edge bootstrap).

        The subject signs its own grant (issuer == subject). Honored locally;
        carries no global weight until a followed peer endorses the subject.
        """
        scope = self.local_node_scope()
        if scope is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No local node identity; cannot bootstrap edge grant",
            )
        return await self.issue_grant(
            issuer_did=subject_did,
            subject_did=subject_did,
            permissions=permissions or ["write"],
            scope=scope,
            ttl_days=ttl_days,
            coarse_floor=["read", "write"],
        )

    # ------------------------------------------------------------------
    # Attestations (Slice 6)
    # ------------------------------------------------------------------

    async def issue_attestation(
        self,
        type: str,
        subject_did: str,
        issuer_did: Optional[str] = None,
        content_hash: Optional[str] = None,
        claim: Optional[Dict] = None,
        expires_at: Optional[datetime] = None,
    ) -> Attestation:
        """Issue and sign a durable attestation. Issuer must be a held key."""
        if not self._attestation_store:
            raise RuntimeError("Attestation store not available")

        if not issuer_did:
            node = self._node_signing_identity()
            if not node:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No local node identity to issue from; specify issuer_did",
                )
            issuer_did = node.did

        signing_key = self._signing_key_for(issuer_did)
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for issuer; cannot issue attestation",
            )

        attestation = Attestation(
            type=type,
            issuer_did=issuer_did,
            subject_did=subject_did,
            content_hash=content_hash,
            claim=claim or {},
            expires_at=expires_at,
        )
        attestation.signature = sign_payload(
            signing_key.private_key, attestation.signing_payload()
        )
        await self._attestation_store.save(attestation)
        logger.info(
            f"Issued {type} attestation {attestation.attestation_id} "
            f"about {subject_did}"
        )
        return attestation

    async def certify(
        self,
        subject_did: str,
        bundle_hash: str,
        version: str,
        issuer_did: Optional[str] = None,
        claim: Optional[Dict] = None,
        manifest_content_hash: Optional[str] = None,
    ) -> Attestation:
        """Issue a ``certified`` attestation binding firm DID → bundle → version.

        ``bundle_hash`` is the R3 release identity (see ``packaging.pin.bundle_hash``).
        When ``manifest_content_hash`` is provided it is stored in the claim so the
        attestation can ride the matching federation catalog record.
        """
        payload = dict(claim or {})
        payload["version"] = version
        if manifest_content_hash:
            payload["manifest_content_hash"] = manifest_content_hash
        return await self.issue_attestation(
            type="certified",
            subject_did=subject_did,
            issuer_did=issuer_did,
            content_hash=bundle_hash,
            claim=payload,
        )

    async def save_attestation(self, attestation: Attestation) -> None:
        """Persist a (typically federated) attestation without re-signing."""
        if not self._attestation_store:
            raise RuntimeError("Attestation store not available")
        await self._attestation_store.save(attestation)

    async def list_attestations(
        self,
        subject_did: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> List[Attestation]:
        """List attestations filtered by subject and/or content hash."""
        if not self._attestation_store:
            return []
        if subject_did:
            atts = await self._attestation_store.list_for_subject(subject_did)
            if content_hash:
                return [a for a in atts if a.content_hash == content_hash]
            return atts
        if content_hash:
            return await self._attestation_store.list_for_content(content_hash)
        return await self._attestation_store.list_all()

    async def list_attestations_for_catalog(
        self, manifest_content_hash: str
    ) -> List[Attestation]:
        """Attestations that should ride a catalog record for this design hash."""
        if not self._attestation_store:
            return []
        return await self._attestation_store.list_for_catalog(manifest_content_hash)

    async def list_reputation(self, subject_did: str) -> List[Attestation]:
        """Known-type, signature-valid attestations about ``subject_did``.

        No numeric scoring yet — reputation is the filtered attestation set over
        the identity chain. Unknown types are stored/relayed but omitted here.
        """
        out: List[Attestation] = []
        for a in await self.list_attestations(subject_did=subject_did):
            if a.type not in KNOWN_ATTESTATION_TYPES:
                continue
            if not verify_attestation(a):
                continue
            out.append(a)
        return out

    # ------------------------------------------------------------------
    # Bindings + trust-on-follow directory (Slice 7)
    # ------------------------------------------------------------------

    async def start_domain_binding(
        self, subject_did: str, domain: str
    ) -> Dict[str, Any]:
        """Begin a domain bind: issue challenge + well-known document to host.

        Requires a held signing key for ``subject_did``. Does not hit the network.
        """
        if not self._binding_store:
            raise RuntimeError("Binding store not available")
        signing_key = self._signing_key_for(subject_did)
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for subject; cannot start domain bind",
            )

        external_id = domain_external_id(domain)
        existing = await self._binding_store.find_by_external_id(external_id)
        if existing and existing.verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain already bound to {existing.subject_did}",
            )

        challenge = secrets.token_urlsafe(24)
        host = external_id.removeprefix("domain:")
        binding = IdentityBinding(
            subject_did=subject_did,
            kind="domain",
            external_id=external_id,
            challenge=challenge,
            evidence={"domain": host, "well_known_url": well_known_url(host)},
            verified=False,
        )
        # Sign the pending (unverified) claim so the challenge issuer is accountable.
        binding.signature = sign_payload(
            signing_key.private_key, binding.signing_payload()
        )
        await self._binding_store.save(binding)
        doc = well_known_document(subject_did, challenge)
        return {
            "binding": binding,
            "well_known_url": well_known_url(host),
            "well_known_document": doc,
        }

    async def verify_domain_binding(
        self,
        subject_did: str,
        domain: str,
        *,
        fetcher: Optional[WellKnownFetcher] = None,
    ) -> IdentityBinding:
        """Fetch ``.well-known/ohm-did.json`` and mark the binding verified.

        On success, issues a ``domain_bound`` attestation and refreshes the
        trust-on-follow directory entry. ``fetcher`` is injectable for tests.
        """
        if not self._binding_store:
            raise RuntimeError("Binding store not available")

        external_id = domain_external_id(domain)
        binding = await self._binding_store.find_by_external_id(external_id)
        if not binding or binding.subject_did != subject_did:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending domain binding for this subject/domain",
            )
        if binding.verified:
            return binding
        if not binding.challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binding has no challenge; restart domain bind",
            )

        try:
            await fetch_and_validate_domain(
                domain,
                expected_did=subject_did,
                expected_challenge=binding.challenge,
                fetcher=fetcher,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        signing_key = self._signing_key_for(subject_did)
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for subject; cannot finalize domain bind",
            )

        now = datetime.utcnow()
        binding.verified = True
        binding.verified_at = now
        binding.challenge = None  # single-use
        binding.signature = sign_payload(
            signing_key.private_key, binding.signing_payload()
        )
        await self._binding_store.save(binding)

        # Durable reputation fact (Slice 6 substrate).
        await self.issue_attestation(
            type="domain_bound",
            subject_did=subject_did,
            issuer_did=subject_did,
            claim={
                "external_id": external_id,
                "domain": external_id.removeprefix("domain:"),
            },
        )
        await self._refresh_directory_from_bindings(subject_did)
        logger.info(f"Domain binding verified: {external_id} -> {subject_did}")
        return binding

    async def bind_oauth(
        self,
        subject_did: str,
        provider: str,
        external_subject: str,
        evidence: Optional[Dict] = None,
        verified: bool = True,
    ) -> IdentityBinding:
        """Record an OAuth/OIDC external-subject binding.

        The IdP redirect dance is out of band (frontend); this persists the
        resulting binding once claims are accepted. Requires a held subject key.
        """
        if not self._binding_store:
            raise RuntimeError("Binding store not available")
        signing_key = self._signing_key_for(subject_did)
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No signing key held for subject; cannot bind OAuth identity",
            )

        external_id = oauth_external_id(provider, external_subject)
        existing = await self._binding_store.find_by_external_id(external_id)
        if existing and existing.verified and existing.subject_did != subject_did:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"OAuth identity already bound to {existing.subject_did}",
            )

        now = datetime.utcnow() if verified else None
        binding = IdentityBinding(
            binding_id=existing.binding_id if existing else uuid4(),
            subject_did=subject_did,
            kind="oauth",
            external_id=external_id,
            evidence={
                "provider": provider.strip().lower(),
                "external_subject": external_subject.strip(),
                **(evidence or {}),
            },
            verified=verified,
            verified_at=now,
        )
        binding.signature = sign_payload(
            signing_key.private_key, binding.signing_payload()
        )
        await self._binding_store.save(binding)

        if verified:
            await self.issue_attestation(
                type="oauth_bound",
                subject_did=subject_did,
                issuer_did=subject_did,
                claim={
                    "external_id": external_id,
                    "provider": provider.strip().lower(),
                },
            )
            await self._refresh_directory_from_bindings(subject_did)
        logger.info(f"OAuth binding recorded: {external_id} -> {subject_did}")
        return binding

    async def list_bindings(
        self, subject_did: Optional[str] = None
    ) -> List[IdentityBinding]:
        """List bindings, optionally filtered by subject."""
        if not self._binding_store:
            return []
        if subject_did:
            return await self._binding_store.list_for_subject(subject_did)
        return await self._binding_store.list_all()

    async def publish_directory_entry(
        self,
        did: str,
        display_name: str = "",
        base_url: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> DirectoryEntry:
        """Publish/refresh a trust-on-follow directory entry for ``did``."""
        if not self._directory_store:
            raise RuntimeError("Directory store not available")
        verified = [
            b.external_id
            for b in await self.list_bindings(subject_did=did)
            if b.verified
        ]
        if domain is None:
            for ext in verified:
                if ext.startswith("domain:"):
                    domain = ext.removeprefix("domain:")
                    break
        identity = self.get_identity(did)
        entry = DirectoryEntry(
            did=did,
            display_name=display_name or (identity.display_name if identity else ""),
            base_url=base_url,
            domain=domain,
            verified_bindings=verified,
            updated_at=datetime.utcnow(),
        )
        await self._directory_store.save(entry)
        return entry

    async def list_directory(self) -> List[DirectoryEntry]:
        """List the local trust-on-follow directory.

        Under ``registry_attestations=ca_pinned`` (shielded), only entries with a
        verified domain binding are returned — the peacetime directory is
        otherwise unfiltered.
        """
        if not self._directory_store:
            return []
        entries = await self._directory_store.list_all()
        if get_security_policy().registry_attestations != "ca_pinned":
            return entries
        return [
            e
            for e in entries
            if e.domain
            or any(b.startswith("domain:") for b in (e.verified_bindings or []))
        ]

    async def _refresh_directory_from_bindings(self, subject_did: str) -> None:
        """Upsert directory entry after a binding verifies."""
        if not self._directory_store:
            return
        existing = await self._directory_store.load(subject_did)
        await self.publish_directory_entry(
            did=subject_did,
            display_name=existing.display_name if existing else "",
            base_url=existing.base_url if existing else None,
            domain=existing.domain if existing else None,
        )
