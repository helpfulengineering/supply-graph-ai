#!/bin/sh
# Container health, for whichever process this image is running.
#
# One image serves two very different things. The API answers HTTP, so curling
# /health is the right question. A Celery worker answers no HTTP at all, so the
# same check can never pass — a worker consuming tasks perfectly reported 63
# consecutive failures, and an orchestrator acting on that restart-loops a
# healthy process.
#
# The mode is recorded by docker-entrypoint.sh, which is the only thing that
# knows it. Anything else — inspecting the process table, guessing from env —
# re-derives a fact we already have.

set -eu

MODE_FILE=/tmp/ohm-container-mode
MODE=$(cat "$MODE_FILE" 2>/dev/null || echo api)

case "$MODE" in
worker)
    # Asks this worker specifically, through the broker: it fails if the broker
    # is unreachable or the worker has stopped answering, which is the failure
    # worth restarting for.
    celery -A src.core.jobs.celery_app.celery_app inspect ping \
        -d "celery@$(hostname)" --timeout 5 2>/dev/null | grep -q pong
    ;;
*)
    curl -fsS "http://localhost:${PORT:-8001}/health" >/dev/null
    ;;
esac
