# ADR: Member sign-in — password and session cookie

## Status

Accepted — not yet implemented.

## Date

2026-10-31

## Context

Today a person signs in to the web UI by pasting a bearer API token, which the
frontend keeps in `sessionStorage` — per tab, gone when the tab closes.
Registration shows two copy-once secrets (the token and a recovery code) plus a
DID. A first-time user's verdict (#561): *"I'm going to lose those three keys."*

Nodes are about to gain **members** — volunteers who just want to share designs
or offer a printer — for whom pasting a 40-character token on every visit is a
barrier to joining at all. No email infrastructure exists, and OHM targets LAN
and field nodes reached by IP address.

## Decision

Members sign in with **username and password**, which the server exchanges for
an **`httpOnly` session cookie**. The existing **recovery code is the password
reset path**; no email is introduced. Signup shows exactly one thing to keep:
the recovery code.

Bearer API tokens remain for the CLI and API, issued from Settings rather than
at signup. Cookie-authenticated writes require CSRF protection; the login
endpoint is rate limited.

## Considered options

- **Passkeys (WebAuthn) as the only method.** Phishing-resistant and smoother,
  but WebAuthn requires a secure context and a domain as relying-party ID, so it
  fails on nodes reached by LAN IP — the crisis-mode field node this project
  exists for. May be added later as a second method.
- **Keep tokens, persist them in `localStorage`, offer a credentials file.**
  Cheapest, but leaves a long-lived bearer token readable by any XSS, and still
  makes the member move a file between devices.
- **Email magic links.** Requires email infrastructure and deliverability, and
  excludes people without reliable email.

## Consequences

- The API gains a second authentication mechanism alongside Bearer; every
  route's authorization must behave the same under both.
- Passwords are a new credential class stored on the node, under the same
  object store as other credential material (`auth/`).

## Related

- [Identity Model](identity-model.md)
- [Security Modes](security-modes.md)
