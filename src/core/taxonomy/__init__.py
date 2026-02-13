"""
Process Taxonomy module.

Provides a canonical process taxonomy as the single source of truth
for manufacturing process identification across the entire system.
"""

from src.core.taxonomy.process_taxonomy import ProcessTaxonomy, taxonomy

__all__ = ["ProcessTaxonomy", "taxonomy"]
