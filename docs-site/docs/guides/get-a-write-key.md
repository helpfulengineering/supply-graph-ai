---
title: Get a write key
area: identity
surface: api
---

# Get a write key

Reading OHM needs nothing. Browsing designs, searching facilities, running a
match — all of it works with no credential at all. **Writing is the part that
needs a key**: saving a facility, adding a design, importing a collection.

This page is about getting that key on a node you run.

## Which node are you writing to?

Two very different situations, and the difference matters more than anything
else on this page.

**Someone else's node** — you need a key from whoever runs it. There is no
self-service signup; a node operator issues credentials. Ask them.

**Your own node** — you already have everything you need. The rest of this page
is for you.

## First, a warning worth reading

`API_KEYS` is not, on its own, a switch that turns write protection on.

Whether writes are checked depends on the node's **posture**, which comes from
`ENVIRONMENT`:

| `ENVIRONMENT` | Anonymous write | Why |
|---|---|---|
| `development` (the default) | **Accepted** | Dev and test flows stay frictionless |
| `production` | Rejected, `401` | Write auth enforced |

That first row surprises people. On a development node, an anonymous `POST`
succeeds **even with `API_KEYS` set** — the key is accepted if you send it, and
not required if you don't.

So if your node is reachable by anyone but you, setting a key is not enough:

```bash
ENVIRONMENT=production
```

Crisis and shielded security modes always enforce writes, whatever `ENVIRONMENT`
says. See [Security Modes](https://github.com/helpfulengineering/supply-graph-ai/blob/main/docs/architecture/security-modes.md).

!!! note "One more thing production needs"

    A node in `production` refuses to start without `OHM_ENCRYPTION_SALT` and
    `OHM_ENCRYPTION_PASSWORD`, which protect stored language-model credentials.
    Generate them once:

    ```bash
    echo "OHM_ENCRYPTION_SALT=$(openssl rand -hex 16)" >> .env
    echo "OHM_ENCRYPTION_PASSWORD=$(openssl rand -hex 32)" >> .env
    ```

    Without them the container exits on boot with a message naming both.

## Step 1 — the bootstrap credential

A new node has no users, so the first credential comes from the environment:

```bash
echo "API_KEYS=$(openssl rand -hex 32)" >> .env
docker compose up -d
```

Check it worked. `whoami` tells you who the node thinks you are:

```bash
curl -s http://localhost:8001/v1/api/identity/whoami \
  -H "Authorization: Bearer $YOUR_API_KEY"
```

```json
{
  "key_id": "00000000-0000-0000-0000-000000000000",
  "name": "Environment Key",
  "permissions": ["read", "write", "admin"],
  "account_id": "00000000-0000-0000-0000-000000000001",
  "subject_did": null
}
```

The all-zero `key_id` is the tell: this credential comes from the environment,
not from storage. It carries `admin`, so it can create everything else.

Without a token the same call returns:

```json
{"detail":"Missing authentication token. Expected 'Authorization: Bearer <token>' header"}
```

## Step 2 — create a named key

You *can* write with the bootstrap token. You should not, for the same reason
you don't hand out the root password: it is admin-scoped, it lives in your
`.env`, and rotating it means restarting the node.

Make a narrower key instead:

```bash
curl -s -X POST http://localhost:8001/v1/api/identity/keys \
  -H "Authorization: Bearer $YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name": "facility-editor", "permissions": ["read", "write"]}'
```

```json
{
  "key_id": "e987bb03-98dc-4562-bd8c-1be360998b2b",
  "name": "facility-editor",
  "permissions": ["read", "write"],
  "created_at": "2026-08-29T04:04:08.532361",
  "revoked": false,
  "token": "cG0D1wKnYMwClHWv-Xw4yLYEwhhVyEWEfOdf3R5kD3Q"
}
```

**Copy `token` now.** It is returned exactly once. Ask for the key again and the
field is empty:

```bash
curl -s http://localhost:8001/v1/api/identity/keys \
  -H "Authorization: Bearer $YOUR_API_KEY"
```

```json
[{"key_id": "e987bb03-…", "name": "facility-editor", "revoked": false, "token": null}]
```

That is deliberate — the node stores a hash, not the secret. Lose it and you
create another key; there is no recovery path, and that is the point.

In the web interface the same thing lives under **Settings → Keys & accounts**,
visible when your current credential carries `admin`.

## Step 3 — use it

Send it as a bearer token:

```bash
curl -s -X POST http://localhost:8001/v1/api/okw/create \
  -H "Authorization: Bearer $WRITE_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"content": {
        "name": "Lab Test Workshop",
        "location": {"address": {"city": "Portland", "country": "US"}},
        "facility_status": "Active"
      }}'
```

`201` and the stored facility comes back with its `id`. Note the `content`
wrapper — the facility goes inside it.

In the web interface, paste the token into **Settings → Session** and the
browser sends it for you. That is what the facility form means when it says you
need a write key before saving.

## Step 4 — revoke it when you're done

```bash
curl -s -X DELETE http://localhost:8001/v1/api/identity/keys/$KEY_ID \
  -H "Authorization: Bearer $YOUR_API_KEY"
```

The next write with that token is refused:

```
401
```

and the key stays in the listing with `"revoked": true`, so the record of what
existed does not disappear along with the access.

## What to expect, in one table

Measured on a node running 0.11.1 with `ENVIRONMENT=production`:

| Request | Result |
|---|---|
| Read, no credential | `200` — reads are open |
| Write, no credential | `401` |
| Write, invalid token | `401` |
| Write, valid write key | `201` |
| Write, revoked key | `401` |

On `ENVIRONMENT=development`, the second row is `201` instead. If that is not
what you want, see the warning above.

## Where to go next

- [Use the OHM API](use-the-api.md#authenticating) — the wider API surface
- [Run your own node](run-your-own-node.md#before-anyone-else-can-reach-it) — securing a node before it is reachable
- [Who can see your data](who-can-see-your-data.md) — visibility, which is a separate question from write access
