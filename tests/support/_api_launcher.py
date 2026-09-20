"""Runs the real API as a subprocess bound to an OS-assigned port (#539 D10).

Not a test itself (no `test_` prefix, so pytest never collects it) — spawned by
`tests.support.real_process.start_api`. Binds the listening socket and reports
its port on the first stdout line *before* importing the app, so the parent
gets the port back quickly regardless of how long app import/startup takes.
"""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    print(json.dumps({"port": port}), flush=True)

    import uvicorn

    from src.core.main import app

    config = uvicorn.Config(app, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    server.run(sockets=[sock])


if __name__ == "__main__":
    main()
