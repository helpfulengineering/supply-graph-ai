# Accounts & API Keys

## Accounts

An **account** is the custodial unit of identity — a **person** or a **space**
(for example a university FabLab). Accounts:

- Own storage-backed API keys (`created_by`)
- Are what writes are attributed to
- Are the parent object when you **mint a DID**

Env-configured `API_KEYS` map to a fixed **root account** for attribution, but
that does **not** insert a selectable account into the accounts list. To mint
identities or manage named keys, create a real account first.

### Create an account

**UI:** Settings → **Keys & accounts** → Create account (display name + kind).

**CLI:**

```bash
ohm identity accounts create --name "MIT FabLab" --kind space
ohm identity accounts list
ohm identity accounts disable <account_id>
```

**API:**

```http
POST /v1/api/identity/accounts
Content-Type: application/json
Authorization: Bearer <admin-key>

{ "display_name": "MIT FabLab", "kind": "space" }
```

List with `GET /v1/api/identity/accounts`. Disable with
`POST /v1/api/identity/accounts/{account_id}/disable`.

Account and key management require **`admin`** when the active security policy
enforces write auth (production peacetime, and always under crisis/shielded).

## Two kinds of API keys

| Kind | Source | Permissions | Revoke |
|---|---|---|---|
| **Env key** | `API_KEYS` on the API process | Always `read` + `write` + `admin` | Change env and restart |
| **Storage key** | `POST /api/identity/keys` / Keys UI | Chosen at create time | `DELETE` / revoke in UI |

Default auth mode is **`hybrid`**: both kinds are accepted.

### Storage keys (recommended for day-to-day use)

**UI:** Settings → **Keys & accounts** → create key (name + permissions). The
plaintext token is shown **once** — copy it immediately.

**CLI:**

```bash
ohm identity keys create --name "UI session" \
  --permission read --permission write --permission admin
ohm identity keys list
ohm identity keys revoke <key_id>
```

**API:**

```http
POST /v1/api/identity/keys
Authorization: Bearer <admin-key>
Content-Type: application/json

{
  "name": "UI session",
  "permissions": ["read", "write", "admin"],
  "expires_at": null
}
```

List endpoints never re-show the plaintext token. Rotate by creating a
replacement key, switching Session / `OHM_API_KEY` to it, then revoking the old
key (there is no `rotate` endpoint for API keys).

## Permissions

| Permission | Meaning |
|---|---|
| `read` | Read endpoints |
| `write` | Create / update / delete (implies read for most flows) |
| `admin` | Keys, accounts, identity admin surfaces (implies full access) |
| `domain:<name>` | Additive domain-scoped access (e.g. `domain:manufacturing`) |

`admin` implies all permissions. `write` implies `read` in the usual hierarchy.

## Whoami

```bash
ohm identity whoami
# or GET /v1/api/identity/whoami
```

Returns the presenting key’s name, `account_id`, optional `subject_did`, and
effective `permissions`. The frontend Session panel shows the same data after
you save a token.

## Configuration reference

```bash
API_KEYS=...              # comma-separated env bootstrap keys
AUTH_MODE=hybrid          # env | storage | hybrid
AUTH_ENABLE_STORAGE=true
AUTH_CACHE_TTL=300        # seconds
AUTH_KEY_LENGTH=32        # bytes for generated storage keys
```

Write enforcement for OKH/OKW mutations follows the active
[security policy](../architecture/security-modes.md) (`require_auth_for_writes`).

## See also

- [Getting Started](getting-started.md) — first env key on Azure / Docker
- [Identities & Grants](identities-and-grants.md) — mint a DID *after* an account exists
- [API Authentication](../api/auth.md) — developer endpoint patterns
