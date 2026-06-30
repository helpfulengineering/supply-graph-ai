"""MoM SPARQL bridge — query Maps of Making for spaces matching an OHM process."""

from __future__ import annotations

import httpx

from ..taxonomy import taxonomy

MOM_SPARQL_ENDPOINT = "https://mapsofmaking.org/sparql/query"

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
