"""MoM SPARQL bridge — query Maps of Making for spaces matching an OHM process."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx

from ..taxonomy import taxonomy

logger = logging.getLogger(__name__)

MOM_SPARQL_ENDPOINT = "https://mapsofmaking.org/sparql/query"

# 24h default TTL: MoM's space directory is slow-changing, and the all-spaces
# query is heavy (thousands of rows), so we avoid re-querying on every map load.
MOM_CACHE_TTL_SECONDS = 24 * 60 * 60

_SPARQL_TEMPLATE = """
SELECT DISTINCT ?space ?name ?lat ?lon WHERE {{
  GRAPH ?g {{
    ?space a <https://nicolasdb.github.io/mapsofmaking_ontology/ns#Space> ;
           <https://schema.org/name> ?name ;
           <https://schema.org/geo> [ <https://schema.org/latitude> ?lat ;
                                       <https://schema.org/longitude> ?lon ] ;
           <https://schema.org/knowsAbout> ?tag .
  }}
  GRAPH <urn:mak:ontology/mom> {{
    ?concept <http://www.w3.org/2004/02/skos/core#prefLabel>|
             <http://www.w3.org/2004/02/skos/core#altLabel> ?tag ;
             <http://www.w3.org/2002/07/owl#sameAs> <{wikidata_iri}> .
  }}
}}
"""


async def query_mom_spaces_for_process(
    canonical_id: str,
    endpoint: str = MOM_SPARQL_ENDPOINT,
    timeout: float = 10.0,
) -> list[dict]:
    """Query MoM SPARQL for spaces that have a given manufacturing process.

    Args:
        canonical_id: OHM canonical process ID (e.g. "laser_cutting").
        endpoint: MoM SPARQL endpoint URL.
        timeout: Request timeout in seconds.

    Returns:
        List of dicts with keys: space (IRI), name, lat, lon.
        Returns empty list if the process has no Wikidata QID or the endpoint
        returns no results.
    """
    wikidata_iri = taxonomy.get_wikidata_iri(canonical_id)
    if not wikidata_iri:
        return []

    sparql = _SPARQL_TEMPLATE.format(wikidata_iri=wikidata_iri)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            endpoint,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
    response.raise_for_status()

    bindings = response.json().get("results", {}).get("bindings", [])
    return [
        {
            "space": b["space"]["value"],
            "name": b["name"]["value"],
            "lat": float(b["lat"]["value"]),
            "lon": float(b["lon"]["value"]),
        }
        for b in bindings
    ]


async def fetch_mom_facilities_for_manifest(
    manifest: object,
    endpoint: str = MOM_SPARQL_ENDPOINT,
    timeout: float = 10.0,
) -> list:
    """Fetch ManufacturingFacility stubs from MoM for processes required by an OKH manifest.

    Extracts all required process names from the manifest, resolves each to a
    Wikidata IRI via the taxonomy, and queries MoM's SPARQL endpoint.  Spaces
    that match multiple required processes are returned as a single facility with
    all matched processes listed so the matching pipeline can score them correctly.

    Args:
        manifest: OKHManifest instance.
        endpoint: MoM SPARQL endpoint URL.
        timeout: HTTP request timeout per query in seconds.

    Returns:
        List of ManufacturingFacility objects.  Empty if no processes resolve
        to Wikidata IRIs or the endpoint returns no results.
    """
    from ..models.okw import FacilityStatus, Location, ManufacturingFacility

    # Gather required process names from both flat list and structured specs
    process_names: list[str] = []
    if getattr(manifest, "manufacturing_processes", None):
        process_names.extend(manifest.manufacturing_processes)
    if hasattr(manifest, "extract_requirements"):
        for req in manifest.extract_requirements():
            pname = getattr(req, "process_name", None)
            if pname and pname not in process_names:
                process_names.append(pname)

    if not process_names:
        return []

    # Query MoM per process; accumulate space IRI → {name, lat, lon, processes}
    space_data: dict[str, dict] = {}
    for process_name in process_names:
        cid = taxonomy.normalize(process_name)
        if not cid:
            continue
        for space in await query_mom_spaces_for_process(
            cid, endpoint=endpoint, timeout=timeout
        ):
            iri = space["space"]
            if iri not in space_data:
                space_data[iri] = {
                    "name": space["name"],
                    "lat": space["lat"],
                    "lon": space["lon"],
                    "processes": [],
                }
            space_data[iri]["processes"].append(process_name)

    # One ManufacturingFacility stub per unique MoM space
    return [
        ManufacturingFacility(
            name=data["name"],
            location=Location(gps_coordinates=f"{data['lat']}, {data['lon']}"),
            facility_status=FacilityStatus.ACTIVE,
            manufacturing_processes=data["processes"],
        )
        for data in space_data.values()
    ]


# All spaces with coordinates — for the network surface. Pulls the fields the
# unified /api/okw/spaces surface filters/displays on (city, country, status,
# url, process tags), aggregating the multi-valued knowsAbout tags per space.
_ALL_SPACES_SPARQL = """
PREFIX schema: <https://schema.org/>
PREFIX mom: <https://nicolasdb.github.io/mapsofmaking_ontology/ns#>
SELECT ?space ?name ?lat ?lon
       (SAMPLE(?city_) AS ?city) (SAMPLE(?country_) AS ?country)
       (SAMPLE(?state_) AS ?state) (SAMPLE(?url_) AS ?url)
       (GROUP_CONCAT(DISTINCT ?tag; SEPARATOR="|") AS ?tags)
WHERE {
  GRAPH ?g {
    ?space a mom:Space ;
           schema:name ?name ;
           schema:geo [ schema:latitude ?lat ; schema:longitude ?lon ] .
    OPTIONAL { ?space schema:addressLocality ?city_ }
    OPTIONAL { ?space mom:countryCode ?country_ }
    OPTIONAL { ?space mom:operationalState ?state_ }
    OPTIONAL { ?space schema:url ?url_ }
    OPTIONAL { ?space schema:knowsAbout ?tag }
  }
} GROUP BY ?space ?name ?lat ?lon
"""


def _normalize_process_tags(concat: str) -> list[str]:
    """Map MoM's ``knowsAbout`` slugs (e.g. "laser|cnc") to canonical OHM process
    ids via the taxonomy, so the process filter is consistent with local OKW."""
    processes: list[str] = []
    for raw in (concat or "").split("|"):
        raw = raw.strip()
        if not raw:
            continue
        cid = taxonomy.normalize(raw)
        if cid and cid not in processes:
            processes.append(cid)
    return processes


def _cell(binding: dict, key: str) -> "str | None":
    """Value of a SPARQL result cell, or None when absent/empty."""
    return binding.get(key, {}).get("value") or None


async def fetch_all_mom_spaces(
    endpoint: str = MOM_SPARQL_ENDPOINT,
    timeout: float = 30.0,
) -> list[dict]:
    """Fetch every MoM space with coordinates, enriched for the network surface.

    Args:
        endpoint: MoM SPARQL endpoint URL.
        timeout: Request timeout in seconds.

    Returns:
        List of dicts: space (IRI), name, lat, lon, city, country, status, url,
        processes (canonical OHM process ids).

    Raises:
        httpx.HTTPError: If the endpoint is unreachable or returns an error. The
            caller (cache) is responsible for graceful degradation; raising here
            lets the cache distinguish a genuine empty result from a fetch
            failure and keep serving stale data.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            endpoint,
            data={"query": _ALL_SPACES_SPARQL},
            headers={"Accept": "application/sparql-results+json"},
        )
    response.raise_for_status()

    spaces: list[dict] = []
    for b in response.json().get("results", {}).get("bindings", []):
        try:
            lat = float(b["lat"]["value"])
            lon = float(b["lon"]["value"])
        except (KeyError, ValueError, TypeError):
            # Skip malformed rows rather than failing the whole fetch.
            continue
        spaces.append(
            {
                "space": b["space"]["value"],
                "name": _cell(b, "name") or "",
                "lat": lat,
                "lon": lon,
                "city": _cell(b, "city"),
                "country": _cell(b, "country"),
                "status": _cell(b, "state"),
                "url": _cell(b, "url"),
                "processes": _normalize_process_tags(_cell(b, "tags") or ""),
            }
        )
    return spaces


class MoMSpacesCache:
    """TTL cache for the MoM all-spaces map layer.

    Serves the last successful fetch for ``ttl_seconds`` (default 24h). On a
    refresh failure it keeps serving stale data and reports ``available=True``
    if any data was ever fetched, so the map degrades gracefully. Other events
    (e.g. an admin action, a new facility) can force a refresh via
    :meth:`refresh` or drop the cache via :meth:`invalidate`.
    """

    def __init__(self, ttl_seconds: float = MOM_CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: Optional[list[dict]] = None
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    def is_fresh(self) -> bool:
        return (
            self._data is not None
            and (time.monotonic() - self._fetched_at) < self.ttl_seconds
        )

    async def get(self, force_refresh: bool = False) -> tuple[list[dict], bool]:
        """Return ``(spaces, available)``.

        ``available`` is True when MoM data is present (fresh or stale). A single
        in-flight refresh is serialized so a cold cache doesn't trigger a
        thundering herd of SPARQL queries.
        """
        if force_refresh or not self.is_fresh():
            async with self._lock:
                # Re-check under the lock: another coroutine may have refreshed.
                if force_refresh or not self.is_fresh():
                    await self._refresh_locked()
        return (self._data or [], self._data is not None)

    async def refresh(self) -> bool:
        """Force a refresh (the cache-refresh hook). Returns True on success."""
        async with self._lock:
            return await self._refresh_locked()

    async def _refresh_locked(self) -> bool:
        try:
            self._data = await fetch_all_mom_spaces()
            self._fetched_at = time.monotonic()
            return True
        except Exception as e:  # noqa: BLE001 — degrade gracefully, keep stale data
            logger.warning("MoM all-spaces refresh failed; keeping stale data: %s", e)
            return False

    def invalidate(self) -> None:
        """Drop cached data so the next ``get`` refetches (cache-refresh hook)."""
        self._data = None
        self._fetched_at = 0.0


# Process-wide cache instance for the map layer.
mom_spaces_cache = MoMSpacesCache()
