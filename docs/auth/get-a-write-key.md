# Get a write key (3 steps)

Creating or editing facilities (and designs) needs a session key with **`write`**
or **`admin`**. Browse still works without one.

## Step 1 — Bootstrap the API (once per node)

Ensure the API process has an env bootstrap token:

```bash
export API_KEYS="$(openssl rand -hex 32)"
```

On Azure / Docker, set `API_KEYS` as a secret on the **API** container, then
restart. Details: [Getting Started](getting-started.md).

## Step 2 — Connect in the UI

1. Open the frontend → **Connect** (or **Settings → Session**).
2. Paste the `API_KEYS` token → **Save**.
3. Confirm permissions include `admin` (env keys are break-glass admin).

Optional local convenience (never commit): `VITE_OHM_API_KEY` in `frontend/.env`.

## Step 3 — Day-to-day write key (recommended)

1. **Settings → Keys & accounts** → create an account (person or space).
2. Create a named storage key with **`write`** (or `admin` if you need Settings).
3. Switch Session to that key; keep the env key for emergencies only.

Then return to **Facilities → New facility** (or Edit) and Save.

## CLI equivalent

```bash
export OHM_API_KEY="<token-with-write>"
ohm identity whoami
ohm okw create --file facility.json   # or use the UI form
```

## See also

- [Frontend Settings](frontend.md) — Session / Connect UX
- [Accounts & API Keys](accounts-and-keys.md) — permissions and revocation
- [API Authentication](../api/auth.md) — header format and enforcement
