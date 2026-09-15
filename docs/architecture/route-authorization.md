# Route authorization

## The problem this exists to prevent

`#478` was found by hand. The whole `/v1/api/package` surface — including
`DELETE` — reached its handler with no `Authorization` header, in every security
mode, with `API_KEYS` set. Nothing in the build objected, because nothing was
looking.

It was also not the only one. When the gate below was written and the question
asked of every route at once, the answer was **59 mutating routes that authorize
nothing**: packages, the whole asset surface, supply-trees and saved solutions,
`taxonomy/reload`, `okh/scaffold`, the rules routes and `rfq/generate`.
`POST /v1/api/taxonomy/reload` answered `200` to an anonymous caller on a
production-configured node.

Anonymous **read** is deliberate — OHM is a public catalogue. Anonymous **write**
is what nobody appears to have chosen.

## The invariant

Every route with a mutating method (`POST`, `PUT`, `PATCH`, `DELETE`) either
resolves an authorization dependency, or is declared in
`tests/parity/test_auth_ratchet.py` — in one of two lists that mean different
things.

**`ANONYMOUS_BY_DESIGN`** is for routes that must never require a credential, and
each row cites the source that says so. There are four, in two groups:

- the **peer protocol** (`/federation/sync/digest`, `/federation/okw/sync/digest`),
  anonymous by necessity because a peer identifies itself with a DID it signs
  for, not with one of our API keys, and bounded by the federation rate limiter
  instead;
- **onboarding and recovery** (`/identity/register`, `/identity/recover`),
  because a node operator should not be the only way to become someone on a
  node, and because the credential recovery returns is the one the caller lost.
  These are gated by `SecurityPolicy.open_registration`, not by a key.

**`READS_EXPRESSED_AS_POST`** is for routes that use a mutating method only
because the query needs a body. They are not writes, and a write permission on a
read would be theatre: the same data is already reachable through a public `GET`
on the same surface. Each row **names that `GET`**, so the claim is checkable
rather than asserted. `POST /v1/api/asset/salvage-match` is the first — it reads
every asset through `AssetService.list()`, persists nothing, and returns what
`GET /v1/api/asset` already serves to anyone.

A row here makes two claims, and both must be verified against the handler rather
than inferred from the route name: that nothing is persisted, and that the
equivalent read is public. If that `GET` ever gains a guard, the row is wrong and
must move.

What governs *reads* is scope rather than authentication —
`test_viewer_scope_ratchet.py`. Be aware it covers `okh_service` and
`okw_service` only, so a surface outside those two has nothing watching the
breadth of what it returns. Assets are such a surface: `AssetService` has no
visibility plane at all.

**`UNAUTHENTICATED_DEBT`** is everything else that authorizes nothing today. A
row there is a debt, tracked by #478, #344 and the per-surface split
(#483–#487). **Adding a row to make a build pass is the failure this gate exists
to prevent.**

## The procedure for removing a row

**1. Decide whether the route writes anything.** The gate keys off the HTTP
method, which is a proxy and an imperfect one — this API uses `POST` for
computation as well as for writes, so some rows are stateless request/response
endpoints that need no credential. Read the handler. Do not infer it from the
route name.

**2. If it does not persist, find out whether the equivalent read is public.**
If it is, the route belongs in `READS_EXPRESSED_AS_POST` with that `GET` named.
If it is *not* — the read is guarded but the POST-shaped twin is not — then the
route is a hole rather than a read, and it needs the same guard its twin has.

`ANONYMOUS_BY_DESIGN` is not the destination for either case. It is for routes
that must *never* authenticate, not for routes that merely need not.

**3. If it writes, give it a dependency.** `require_write` for ordinary
mutations, `require_admin` for operator surfaces, `require_admin_strict` for
operations that must never be anonymous even outside production — credential
management is the existing example. `require_write` and `require_admin` are
policy-gated: under `SecurityPolicy.require_auth_for_writes = False` they resolve
an optional user for attribution rather than refusing, so adding one does not
break development flows.

**4. Delete the row.** The gate fails if you do not — a route that now
authorizes while still declared is an error, which is what keeps the list
shrinking rather than rotting.

**5. Check the 401 documentation.** 48 of the original 59 document a `401` they
cannot return, inherited from a shared `responses=` constant on their router.
Adding an auth dependency makes that documentation true, which is why it is not
separately gated — see "What this deliberately does not check" below.

## Enforcement

`make ready` fails when a mutating route authorizes nothing and is not declared.
The gate is `tests/parity/test_auth_ratchet.py`, run by `make parity`
(`make ready` step [5/13]).

It is a ratchet and fails in both directions, like `tests/parity/manifest.py` and
`test_response_models.py`:

- a mutating route that is unauthenticated and undeclared fails the build, so the
  class cannot reopen through a new endpoint;
- a declared route that has since been protected also fails, so the list shrinks
  as the work lands.

The assertion is set equality, which gives both directions from one statement.

**It introspects the built application, not the route source.** A dependency can
be declared on the route, on the `APIRouter`, or on the parent app —
`routes/package.py` used none of the three — so a source parse would have to
model all three to be correct. Walking the app's dependant tree asks the question
the way the server answers it. `test_viewer_scope_ratchet.py` parses source for a
different question (whether a call site passes a `viewer` argument) and is a
precedent for ratchet shape, not for this detection.

`require_write` and `require_admin` are closures built by `require_permission`,
so they cannot be distinguished by name — the gate matches the qualified name
they share, which also catches any future inline `require_permission("…")`
without needing to be told about it.

## What this deliberately does not check

**That a route's declared OpenAPI `security` matches what it enforces.** The
mismatch is real and measured — 48 mutating routes document a `401` they cannot
return, and 25 authorize but document no `401` at all — but neither direction can
be asserted green today without a second debt list, and both resolve as a side
effect of the rows above being paid down. A gate that cannot fail is not
evidence; one whose failures are already counted elsewhere is noise. Tracked
separately rather than approximated here.
