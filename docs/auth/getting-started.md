# Getting Started (Auth Bootstrap)

This page covers the **first admin credential** on a new OHM node — local Docker,
Azure Container Apps, or any other host that runs the API container.

## Header format

All authenticated requests use:

```http
Authorization: Bearer <token>
```

The CLI reads the same token from `OHM_API_KEY`. The reference frontend stores it
in **sessionStorage** (Settings → Session / **Connect** in the nav).

## Bootstrap with `API_KEYS`

Every deployment needs at least one **environment key** so an operator can
authenticate before any storage-backed keys exist.

```bash
# Generate a strong token (example)
openssl rand -hex 32

# Set on the API process (comma-separated for multiple keys)
export API_KEYS="<generated-token>"
```

**Properties of env keys**

- Full access: `read`, `write`, and `admin`
- Cannot be revoked individually (change or remove `API_KEYS` and restart)
- Attributed to the built-in **root account** for write attribution
- Do **not** automatically create a row in the accounts list used for DID minting

!!! warning "Production"
    Prefer storing `API_KEYS` as a **Container App secret** or Key Vault
    reference, not as plain text in a checked-in file. Treat env keys as
    break-glass admin credentials; mint named storage keys for day-to-day use.

### Azure Container Apps

On the **API** container (not the frontend):

1. Add a secret named e.g. `api-keys` with your token value(s).
2. Map it to the environment variable `API_KEYS`.
3. Redeploy / restart so the process picks up the value.

The same variable is used on other hosts; see the
[Container Guide](../development/container-guide.md) for Docker, Cloud Run, and
ACI examples.

### Auth mode

Default is **hybrid** (env keys and storage keys both accepted):

```bash
AUTH_MODE=hybrid   # or env | storage
```

Leave `hybrid` for bootstrap; you can tighten to `storage` later once env keys
are retired.

## Connect the UI

1. Open the frontend (local: typically `http://localhost:5173`).
2. Click **Connect** in the nav (becomes **Session** / **Settings** after auth).
3. Paste the env key into **Settings → Session** and Save.
4. Confirm `whoami` shows `admin` under permissions.

Without a session key:

- Catalog browse still works in peacetime-dev when write auth is relaxed.
- **New design** / **New facility** send you to Session to connect.
- Admin tabs (Keys, Identities, Federation, …) appear only after `whoami`
  reports `admin`.

### Optional local seed

For local frontend-only convenience (never commit secrets):

```bash
# frontend/.env — gitignored
VITE_OHM_API_KEY=<same-token-as-API_KEYS>
```

If `sessionStorage` is empty, the UI seeds once from this variable.

## CLI

```bash
export OHM_API_KEY="<same-token>"
ohm identity whoami
ohm identity security-policy
```

## What to do next

1. [Create an account](accounts-and-keys.md) under **Keys & accounts**.
2. Create a named **storage key** for daily use (optional but recommended).
3. [Mint a DID](identities-and-grants.md) if you need self-sovereign identity /
   grants / signed provenance.
4. Walk the [Frontend Settings](frontend.md) tabs as needed.

## See also

- [Accounts & API Keys](accounts-and-keys.md)
- [API Authentication](../api/auth.md)
- [Security Modes](../architecture/security-modes.md)
