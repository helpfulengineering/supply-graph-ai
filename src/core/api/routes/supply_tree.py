"""Saved supply-tree solutions are gone; these routes say so (#498).

A match answers "who can build this". That answer used to be persisted, and a
browse, a visualization, eleven derived projections and a TTL grew on top of it.
None of that was chosen: `frontend/src/api/ohm/match.ts` set
`save_solution: true` on every request to obtain an id for
`/visualization/[solutionId]`, because the explorer needed a URL. The server's
own default was `False`.

So a routing convenience became durable storage of who searched for what, read
by anyone holding an id. #498 removed it. A match result is now client-held and
session-bounded, and it leaves OHM two ways: `POST /api/match/export/contacts`
for the facilities and how to reach them, or an RFQ, which already took its
solutions in the request body and needed no change.

**Why these nine still exist as 501 rather than 404.** Each had a caller inside
this repository when it was removed, so something outside may have one too, and
#459 settled the precedent for that case: *"a removed endpoint 404s, which reads
as a wrong URL rather than a decision."* The other sixteen had no caller anywhere
and are simply gone.

#499 closes this out: probe the access logs for real callers, then delete these
too, or redirect whoever is left. A permanent 501 is a decision that has stopped
being re-examined.
"""

from fastapi import APIRouter, HTTPException, status

from ..constants.openapi import RESPONSES_400_401_422_500

router = APIRouter(
    prefix="/api/supply-tree",
    tags=["supply-tree"],
    responses=RESPONSES_400_401_422_500,
)

_GONE = (
    "Saved supply-tree solutions were removed in #498. A match result is not "
    "stored: run the match again, export the facilities as a contact list with "
    "POST /api/match/export/contacts, or generate an RFQ — both take the result "
    "in the request body."
)


def _removed() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_GONE,
    )


# Nine routes, each of which had an in-repo caller when solutions were removed.
# Declared as a table rather than nine near-identical handlers: they differ only
# in method and path, and writing them out would invite one to quietly grow a
# body again.
_REMOVED_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/solutions", "List saved solutions"),
    ("POST", "/solutions/cleanup", "Clean up stale solutions"),
    ("GET", "/solution/{solution_id}", "Get a saved solution"),
    ("DELETE", "/solution/{solution_id}", "Delete a saved solution"),
    ("POST", "/solution/{solution_id}/save", "Save a solution"),
    ("POST", "/solution/{solution_id}/extend", "Extend a solution's TTL"),
    ("GET", "/solution/{solution_id}/staleness", "Check solution staleness"),
    ("GET", "/solution/{solution_id}/hierarchy", "Get a solution's hierarchy"),
    (
        "GET",
        "/solution/{solution_id}/visualization",
        "Get a solution's visualization bundle",
    ),
)

for _method, _path, _summary in _REMOVED_ROUTES:
    router.add_api_route(
        _path,
        _removed,
        methods=[_method],
        summary=f"{_summary} (removed)",
        description=_GONE,
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        responses={501: {"description": "Removed in #498"}},
    )
