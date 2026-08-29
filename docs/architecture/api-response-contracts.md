# API response contracts

How a route's response shape reaches the frontend without anyone guessing it.

## The problem this exists to prevent

A route that returns a bare `dict` produces no response schema. `openapi-typescript`
then generates no type for it, and the frontend fills the vacuum with a
hand-written one — a guess, written from reading the route, that the compiler
cannot check against anything.

That guess goes wrong silently. In #369 the hierarchy route returned
`root_components` as a list of objects while the frontend had typed it as a list
of strings; rendering an entry threw React error #31 and took down the whole
visualization page. The test fixture had been hand-written from the same wrong
guess, so the suite was green against a shape the API had never returned.

Three things had to fail together, and all three were avoidable:

- the route declared no response model, so codegen had nothing to emit;
- the client used an unchecked `as` cast, so TypeScript could not object;
- the fixture encoded the same guess, so tests agreed with the bug.

## The procedure

For any route the frontend calls:

**1. Capture the real response first.** Exercise the route against a seeded
server or a `TestClient` and keep the JSON. Write the model from what the route
actually returns, not from reading its code.

**2. Test-lock the capture before you add the model.** This is the step that
cannot be skipped, because **`response_model` filters**: FastAPI drops any field
the model does not declare, silently, from the JSON. A model written by reading
the route can therefore delete a field a client depends on — the same class of
bug the model is meant to close, introduced by the fix for it.

The lock is a test asserting the payload is field-identical before and after.
`tests/api/test_supply_tree_hierarchy_contract.py` is the worked example: it
freezes a golden capture and fails loudly if the model filters anything.

**3. Keep free-form sub-payloads free-form.** Where a route embeds an arbitrary
serialised object (`SupplyTree.to_dict()`, for instance), model it as
`Dict[str, Any]`. A strict model there filters any field that dict later grows —
the same trap, one level down.

**4. Regenerate and delete the cast.** Run `npm run gen:api`, then remove the
hand-written type the missing model had forced. If a cast survives, say in a
comment why.

**5. Parse at the client boundary.** Generated types close the *authoring* gap;
they say nothing about the *deployment* gap, where a server changes after the
bundle was built. `parsePayload` in `src/api/ohm/parse.ts` turns that drift into
an error naming the endpoint and the field, instead of a minified React error
inside a render.

Use `z.looseObject`, never bare `z.object` — the latter strips undeclared keys,
which rebuilds the filtering hazard at the client. Describe only the fields the
UI reads; restating the whole generated type in a second place just creates
something else that can go stale.

**6. Derive fixtures from the capture.** A fixture written by hand is a second
guess, and it will agree with the first one. The corrected fixture must fail
against the old code — if it doesn't, it isn't testing the contract.

## Enforcement

`make ready` fails when a route the frontend calls has no response model, with
an allowlist for routes not yet converted (#374). An intentional exception is a
recorded row, not an absence — the same pattern as `tests/parity/manifest.py`.
