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
