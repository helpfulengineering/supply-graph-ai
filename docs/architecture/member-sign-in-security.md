# Member sign-in: security design

## Status

Accepted, 2026-11-01, after review. Implemented (#570, #571). The sections below are that design. "What exists today" describes the node before the change.

## Date

2026-11-01

## Scope

How [member sign-in](member-sign-in-adr.md) is made safe: the session, its
cookie, CSRF protection, password storage, login rate limiting, and how a route
authorises a request identically whether it carries a cookie or a Bearer token.
The ADR decided *what*; this decides *how*, and is what #570's "security design
reviewed and approved" criterion refers to.

## What exists today

- Requests authenticate only with `Authorization: Bearer`. API keys are 32
  random bytes, stored as a SHA-256 digest under `auth/api-keys/` with a digest
  index, and checked with a constant-time compare. Keys can expire and be
  revoked.
- Recovery codes use the same generator and digest scheme. Redeeming one
  revokes every key on the account and issues a new code.
- Rate limits are in-process and keyed by client IP. `register` allows 10 per
  minute and `recover` 5 per minute. Client IP is trusted only from loopback
  and private-range proxies (`FORWARDED_ALLOW_IPS`).
- The UI reaches the API on its own origin through the Next.js `/v1` proxy.
  Default installs serve plain HTTP on a LAN address. TLS, where present, ends
  at a platform ingress.
- No cookies, and no CSRF handling.

## Decisions

### 1. A session is a server-side record, and the cookie is an opaque handle

Signing in creates a **session credential**: 32 random bytes, stored like an API
key, as a SHA-256 digest with a digest index, plus `account_id`, `created_at`,
`last_seen_at`, an idle expiry and an absolute expiry. The cookie holds the raw
value; the node holds only the digest.

It reuses the API-key store with `kind: "session"` rather than adding a third
credential store. Revoking everything on an account, as recovery already does,
then ends that account's sessions too, with no extra code. It is not a signed
token such as a JWT: a server-side record can be revoked at once and leaks
nothing if read.

Each credential is accepted only through its own channel: a session only from
the cookie, an API key only from the `Authorization` header. A session value
pasted into the CLI is refused, so the two classes cannot be confused.

**Lifetime.** A session expires after 30 days without use, and in any case 90
days after sign-in. `last_seen_at` is written at most once an hour, so reads do
not turn into writes. In shielded mode the cookie has no `Max-Age`, so it ends
with the browser session, and the absolute limit follows the policy's
`key_ttl_days`.

**Disabled accounts.** Validation checks `Account.disabled` for sessions, as it
should for keys.

### 2. Cookie attributes

| Attribute | Value | Why |
|---|---|---|
| Name | `__Host-ohm_session` over HTTPS; `ohm_session` over HTTP | The `__Host-` prefix forbids `Domain` and requires `Secure` and `Path=/`, so a sibling subdomain cannot set or shadow it. Browsers reject the prefix without `Secure`, so plain HTTP uses the bare name. |
| `HttpOnly` | always | Script cannot read the credential, so a cross-site scripting bug cannot steal it. |
| `Secure` | when the request scheme is `https` | The scheme comes from the trusted `X-Forwarded-Proto`, the same source HSTS uses. On plain HTTP, `Secure` would stop the browser storing the cookie at all. |
| `SameSite` | `Lax` | The browser does not send it on cross-site `POST`, `PUT` or `DELETE`, but still sends it when someone follows a link into the node. `Strict` would sign a member out every time they arrive from elsewhere. |
| `Path` | `/` | It covers both the UI and `/v1`. |
| `Domain` | never set | A host-only cookie never reaches other subdomains. |
| `Max-Age` | 90 days (none in shielded mode) | This is the absolute lifetime. The idle limit is enforced on the server. |

**Plain HTTP.** On a LAN node without TLS, the cookie travels in clear, exactly
as a Bearer token does today. Peacetime and default modes accept this, and the
sign-in page says the connection is not encrypted. **Shielded mode refuses
password sign-in over plain HTTP.**

**The `/v1` proxy.** `frontend/app/v1/[...path]/route.ts` copies upstream
response headers with `Headers.set`, which keeps only the last `Set-Cookie`.
Sign-in sets two cookies, the session and the CSRF token below, so the proxy
must append each `Set-Cookie` (`getSetCookie()`). This is part of #570, with a
test.

### 3. CSRF protection

Only requests authenticated by the cookie need it. A Bearer token is never
attached automatically by the browser, so Bearer requests are exempt.

For a cookie-authenticated `POST`, `PUT`, `PATCH` or `DELETE`, the server
requires both of these:

1. **A token bound to the session.** Signing in also issues a CSRF token: random,
   with its digest stored on the session record. It is delivered in a readable
   cookie, `ohm_csrf` (`__Host-ohm_csrf` over HTTPS), with `SameSite=Strict`
   and without `HttpOnly`. The frontend echoes it in an `X-OHM-CSRF` header.
   The server compares the header with **the session's stored digest**, not
   with the cookie. A planted cookie therefore does not pass, because it is not
   the token issued to this session.
2. **A same-origin check.** If an `Origin` header is present, it must be the
   node's own origin or one in the CORS allowlist. Otherwise the request is
   refused with 403, before any work is done.

`SameSite=Lax` already stops most cross-site forgery in current browsers. The
token covers older browsers and attacks from a sibling subdomain, which counts
as same-site.

**Sign-in forgery.** `login`, `register` and `recover` set a session, so a
forged form could sign a victim into the attacker's account. Those three
endpoints apply the same-origin check even though no session exists yet.

**Credentialed CORS** stays as it is: allowed only for a named origin list,
never for `*`. Even an allowed origin cannot read this node's `ohm_csrf`
cookie, so it cannot make a cookie-authenticated write.

### 4. Password storage and policy

**Hashing: Argon2id** through `argon2-cffi`, a new dependency (prebuilt wheels
exist for x86-64 and ARM). Parameters follow the OWASP minimum: 19 MiB memory,
2 iterations, parallelism 1. That is small enough for a Raspberry Pi to handle
several sign-ins at once. The parameters are stored in the hash string, and a
successful sign-in rehashes when they have since been raised. The hash lives on
the account record under `auth/`.

*Alternative, if a new dependency is unwelcome:* bcrypt, already used for
legacy API keys, at cost 12. It truncates input at 72 bytes, which the length
limit below must then respect.

**Policy**, following NIST SP 800-63B:
- at least 10 characters and at most 256;
- no composition rules, such as requiring a digit or a symbol;
- refused if it equals the username or the display name.

There is no breached-password lookup: field nodes are often offline. A small
bundled list of common passwords is an option for later.

**Usernames:**
- normalised with NFKC, then lower-cased;
- 3 to 32 characters from `a-z`, `0-9`, `.`, `_` and `-`;
- unique per node, through an index at `auth/usernames/{username}.json`.

The object store has no "create only if absent" write. Within one process, a
lock serialises creation, and the index is read back after writing to confirm
it names the new account. **Two replicas could still race.** Single-replica
nodes, which is every install today, are safe. Shared state for multi-replica
nodes is tracked in #414.

### 5. Login rate limiting and failure responses

- **Per IP:** `login` joins `SENSITIVE_PATH_LIMITS` at 5 a minute, alongside
  `register` (10) and `recover` (5).
- **Per username:** after 5 failures within 15 minutes, that username accepts
  one attempt a minute, from any IP, until 15 minutes pass with no failure.
  This is a slowdown, not a lockout. A lockout would let anyone keep a member
  out by failing on purpose.
- **One answer for every failure:** "Username or password is incorrect.",
  whether the username exists or not. For an unknown username the server still
  runs an Argon2 verify against a fixed dummy hash, so the response time does
  not reveal which usernames exist. Registration necessarily reveals that a
  username is taken; its per-IP limit bounds enumeration.

These counters are per process, like the existing limits. Several workers
multiply the allowance, and a restart resets it. Both are documented today in
`security-modes.md`; shared counters come with #414.

### 6. Session lifecycle

| Event | Effect |
|---|---|
| Sign in | A new session and a new CSRF token, every time. A session value is never reused across sign-ins, so session fixation does not apply. |
| Sign out (`POST /api/identity/logout`) | Deletes the session record and expires both cookies. It needs the CSRF token. |
| Recover (sets a new password, #571) | Revokes every session and API key on the account, issues a new recovery code, and signs in on this device. |
| Account disabled | Every session is refused from the next request on. |
| Idle 30 days, or 90 days since sign-in | Refused; the UI shows the sign-in page. |

### 7. One authorisation rule for cookie and Bearer

There is one resolver, used by `get_current_user`, `get_optional_user`,
`get_viewer` and `require_permission`:

1. If an `Authorization` header is present, it decides, and any cookie is
   ignored. An invalid header behaves as it does today: 401, or anonymous for
   `get_viewer`.
2. Otherwise, the session cookie is used. For an unsafe method, the CSRF check
   in §3 runs here, so no route can forget it.
3. Both paths produce the same `AuthenticatedUser` (account, DID, permissions).
   Everything downstream, including `viewer_scope`, `require_ownership` and
   `can_read`, sees no difference.

**Permissions.** A session carries `read` and `write`, the same as a
self-registered API key. **Admin stays Bearer-only in this version**: a
browser session never holds admin, so a CSRF or XSS bug in the UI cannot reach
admin routes. An operator who needs Settings in the browser pastes an admin key,
as today.

**The auth ratchet** (`tests/parity/test_auth_ratchet.py`) needs no new
dependency names, because the existing dependencies gain cookie support. `login`
joins `register` and `recover` in `ANONYMOUS_BY_DESIGN`.

**Parity test.** One parametrised test runs a representative route set under
both mechanisms and asserts identical outcomes: an anonymous read, an owned
write, another user's write (403), a private read by a non-owner (404) and an
admin route (403 for a session). A further test asserts that a cookie write
without the CSRF header is refused, and that the same write with a Bearer
token is not affected.

### 8. Registration and the API

- `POST /api/identity/register` takes `username`, `password` and
  `display_name`. It sets the session cookies, returns the recovery code, and
  returns **no API token**. The token moves to Settings (#571).
- `POST /api/identity/login` takes `{username, password}`, sets the cookies,
  and returns the same identity body as `whoami`.
- The CLI keeps Bearer tokens. `ohm identity register` without a password keeps
  today's behaviour, returning a token, for one release.
- Browsers that hold a token from an earlier signup keep working. The token
  stays valid until it expires, and the UI prefers the session once one exists.

### 9. Not in scope

- Passkeys: a later, second method (ADR).
- Email: there is none, and recovery codes are the reset path.
- Content Security Policy: it would limit what a cross-site scripting bug can
  do once running, which `HttpOnly` does not. It deserves its own issue.
- Shared rate-limit state across replicas: #414.

## Decided in review

1. **Admin in the browser:** admin stays Bearer-only. A session never carries
   admin.
2. **CLI registration:** password-less `register` (token only) is kept for one
   release, then removed.
3. **Hash:** Argon2id via `argon2-cffi`.
4. **Plain HTTP:** password sign-in is allowed outside shielded mode, with a
   visible warning; shielded mode refuses it.

## Related

- [Member sign-in ADR](member-sign-in-adr.md)
- [Identity model](identity-model.md)
- [Security modes](security-modes.md)
- [Route authorisation](route-authorization.md)
