#!/usr/bin/env python3
"""Deprecated shim: use populate_ohm_storage_from_synthetic_data.py (OHM / Open Hardware Manager)."""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parent / "populate_ohm_storage_from_synthetic_data.py"
    )
    print(
        "populate_ome_from_synthetic_data.py is deprecated; forwarding to "
        "populate_ohm_storage_from_synthetic_data.py",
        file=sys.stderr,
    )
    runpy.run_path(str(target), run_name="__main__")
