# Frontend Settings (Auth UI)

The reference frontend authenticates with the same Bearer API keys as the CLI.
This page describes the operator UI on the Settings surface.

## Connect / Session

| Nav label | When |
|---|---|
| **Connect** | No API key in this browser tab |
| **Session** | Key present, but `whoami` is not `admin` |
| **Settings** | `whoami` includes `admin` |

**Session** is always reachable so you can paste a first key (including an env
`API_KEYS` bootstrap token). Other Settings tabs require **admin**.

On Session:

1. Paste the token → **Save** (stored in `sessionStorage` only for this tab).
2. Confirm name, account id, DID (if any), and permission badges.
3. **Clear session** removes the token from the tab.

Optional local seed: `VITE_OHM_API_KEY` in `frontend/.env` (never commit).

## Tabs (admin)

| Tab | Use for |
|---|---|
| **Session** | Paste / clear API key; view whoami |
| **Keys & accounts** | Create accounts; create / list / revoke storage keys |
| **Identities** | Mint / look up / rotate DIDs (**needs an account first**) |
| **Grants** | Issue / revoke capability grants; edge bootstrap |
| **Spaces** | Claim space DIDs |
| **Bindings** | Domain / OAuth binding helpers |
| **Directory** | Directory publish / list |
| **Federation** | Node status, peers, discover, follow, sync |
| **Reputation** | Attestation lookup by subject |

The footer shows a read-only **security policy** badge (mode, grant TTL, mDNS).

## Common workflows

### First login on a new node

1. Ensure the API has `API_KEYS` set ([Getting Started](getting-started.md)).
2. Open **Connect** → paste the env key → Save.
3. Open **Keys & accounts** → **Create account**.
4. Optionally create a named storage key; switch Session to that key; keep the
   env key as break-glass.

### Mint a user identity

1. Create the account (step above) if the Identities **Account** dropdown is empty.
2. **Identities** → select account → kind → name → **Mint**.
3. Copy / record the DID from the result list.

### Publish a design as yourself

1. Session key needs `write` (or `admin`).
2. Designs → **New design** (or Facilities → **New facility**).
3. Authorship / visibility controls on detail pages use the same session.

If create buttons send you to Session, you are not write-capable yet — connect a
key with `write` or `admin`.

## Auth failure banner

401 / 403 from mutations surface a banner with a link to **Open Session**. Fix
by pasting a valid key or using one with the required permission.

## See also

- [Getting Started](getting-started.md)
- [Accounts & API Keys](accounts-and-keys.md)
- [Identities & Grants](identities-and-grants.md)
