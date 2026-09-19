#!/usr/bin/env sh
#
# Wait for a container's own HEALTHCHECK to report healthy; fail loudly if it
# does not.
#
# `curl /health` from the host asks whether the app answers. This asks what the
# image says about itself — the state `docker ps` shows an operator — and the
# two can disagree: the 0.12.2 frontend served normally while reporting
# "unhealthy" for its whole life, because its check probed `localhost`, which
# resolves to ::1 first inside the container while the server listens on IPv4
# only. Every gate that curled the app passed.
#
# A container with no HEALTHCHECK fails too. Passing vacuously would let a
# deleted check read as a healthy one.
#
# Usage: wait_container_healthy.sh <container> [timeout_seconds]   (default 150)
#
# Exit 0 only for "healthy". The timeout must exceed the image's start-period
# plus one interval; the shipped intervals are 30s, so the default allows for
# the first probe and a retry.

set -eu

name="${1:?usage: wait_container_healthy.sh <container> [timeout_seconds]}"
timeout="${2:-150}"

fail() {
    printf '\n[X] %s: %s\n' "$name" "$1" >&2
    docker inspect --format \
        '{{if .State.Health}}{{range .State.Health.Log}}    probe exit={{.ExitCode}} output={{printf "%q" .Output}}{{"\n"}}{{end}}{{end}}' \
        "$name" >&2 2>/dev/null || true
    printf '    --- last log lines ---\n' >&2
    docker logs --tail 20 "$name" >&2 2>&1 || true
    exit 1
}

elapsed=0
while :; do
    state=$(docker inspect --format \
        '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$name" 2>/dev/null) || fail "no such container"

    case "$state" in
    "true healthy")
        printf '%s: healthy after %ss\n' "$name" "$elapsed"
        exit 0
        ;;
    *" none")
        fail "the image defines no HEALTHCHECK"
        ;;
    "true unhealthy")
        fail "reported unhealthy after ${elapsed}s"
        ;;
    "false "*)
        fail "exited before it became healthy"
        ;;
    esac

    if [ "$elapsed" -ge "$timeout" ]; then
        fail "still '${state#* }' after ${timeout}s"
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
