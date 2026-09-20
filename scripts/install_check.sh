#!/usr/bin/env sh
#
# Run the real installer against images built from this tree, and check that
# what it produced is a node an operator can actually use.
#
# Why this exists: every defect in the 0.12.2 clean-box install log shipped
# because CI tested artifacts an operator never runs and never ran the one they
# do. The installer was a regex over its own text; the images were curled under
# ENVIRONMENT=test with no mount; nothing asked Docker whether a container was
# healthy or minted an identity in a container running as the unprivileged user
# the image really uses. This does what an operator does, and asserts on what
# an operator would see.
#
# Usage:  OHM_CHECK_API_IMAGE=<tag> OHM_CHECK_WEB_IMAGE=<tag> sh scripts/install_check.sh
#         (or `make install-check`, which builds both images first)
#
# The installer runs `docker pull` unconditionally, so a locally built image
# cannot be installed directly. A throwaway registry on localhost serves them
# instead, which leaves scripts/install.sh exactly as shipped. Docker treats a
# localhost registry as insecure by default, so nothing needs configuring.
#
# Every check runs even after one fails, so a single run names everything that
# is wrong rather than the first thing. Exit 0 only if all passed.
#
# Environment:
#   OHM_CHECK_API_IMAGE    the API image to install       (required)
#   OHM_CHECK_WEB_IMAGE    the web image to install       (required)
#   OHM_CHECK_PORT         host port for the web UI       (default 18080)
#   OHM_CHECK_API_PORT     host port for the API          (default 18001)
#   OHM_CHECK_REGISTRY_PORT  throwaway registry port      (default 5055; not
#                          5000, which macOS uses for AirPlay)
#   OHM_CHECK_INSTALLER    installer to run   (default: install.sh beside this
#                          script; point it at another copy to see the checks
#                          fail against a known-broken one)
#   OHM_CHECK_KEEP=1       leave everything running for debugging

set -u

API_IMAGE="${OHM_CHECK_API_IMAGE:?set OHM_CHECK_API_IMAGE to the API image tag}"
WEB_IMAGE="${OHM_CHECK_WEB_IMAGE:?set OHM_CHECK_WEB_IMAGE to the web image tag}"
PORT="${OHM_CHECK_PORT:-18080}"
API_PORT="${OHM_CHECK_API_PORT:-18001}"
REG_PORT="${OHM_CHECK_REGISTRY_PORT:-5055}"
NAME="ohm-ic"
API="${NAME}-api"
WEB="${NAME}-web"
NETWORK="${NAME}-net"
REGISTRY="${NAME}-registry"
VERSION="citest"

HERE=$(cd "$(dirname "$0")" && pwd)
INSTALLER="${OHM_CHECK_INSTALLER:-${HERE}/install.sh}"
WORK=$(mktemp -d)
DATA="${WORK}/data"
INSTALL_LOG="${WORK}/install.log"
mkdir -p "$DATA"

failures=0
passes=0

pass() { passes=$((passes + 1)); printf '  ok    %s\n' "$1"; }
fail() {
    failures=$((failures + 1))
    printf '  FAIL  %s\n' "$1"
    shift
    for line in "$@"; do printf '          %s\n' "$line"; done
}

# The data directory is chowned to the container's unprivileged user by the
# image's entrypoint, so on a Linux host the runner can neither read nor delete
# what is in it. Do both from inside a container, which is root.
in_data() { docker run --rm -v "${DATA}:/d" alpine:3 sh -c "$1"; }

teardown() {
    if [ "${OHM_CHECK_KEEP:-}" = "1" ]; then
        printf '\nOHM_CHECK_KEEP=1: leaving the node running (%s, data in %s)\n' "$NAME" "$DATA"
        return
    fi
    docker rm -f "$API" "$WEB" "$REGISTRY" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
    docker rmi "localhost:${REG_PORT}/ohm-api:${VERSION}" "localhost:${REG_PORT}/ohm-web:${VERSION}" >/dev/null 2>&1 || true
    in_data 'rm -rf /d/* /d/.[!.]*' >/dev/null 2>&1 || true
    rm -rf "$WORK"
}
trap teardown EXIT

diagnostics() {
    printf '\n--- diagnostics ---\n'
    docker ps -a --filter "name=${NAME}" || true
    printf '\n--- installer output ---\n'
    cat "$INSTALL_LOG" 2>/dev/null || true
    for c in "$API" "$WEB"; do
        printf '\n--- %s (last 40 lines) ---\n' "$c"
        docker logs --tail 40 "$c" 2>&1 || true
    done
}

http_code() { curl -s -o /dev/null -m 20 -w '%{http_code}' "$@"; }

# --- Refuse to run on top of something ----------------------------------------
docker info >/dev/null 2>&1 || { echo "Docker is not running."; exit 2; }
if docker ps -a --format '{{.Names}}' | grep -q "^${NAME}-"; then
    echo "Containers named ${NAME}-* already exist; remove them first:"
    echo "  docker rm -f ${API} ${WEB} ${REGISTRY}"
    exit 2
fi

# --- Serve the images ---------------------------------------------------------
printf 'Serving the images from a throwaway registry on localhost:%s\n' "$REG_PORT"
docker run -d --name "$REGISTRY" -p "127.0.0.1:${REG_PORT}:5000" registry:2 >/dev/null \
    || { echo "Could not start the registry on port ${REG_PORT}."; exit 2; }
for i in $(seq 1 30); do
    curl -fsS "http://localhost:${REG_PORT}/v2/" >/dev/null 2>&1 && break
    sleep 1
done
docker tag "$API_IMAGE" "localhost:${REG_PORT}/ohm-api:${VERSION}" \
    && docker tag "$WEB_IMAGE" "localhost:${REG_PORT}/ohm-web:${VERSION}" \
    && docker push -q "localhost:${REG_PORT}/ohm-api:${VERSION}" >/dev/null \
    && docker push -q "localhost:${REG_PORT}/ohm-web:${VERSION}" >/dev/null \
    || { echo "Could not push the images to the local registry."; exit 2; }

# --- Run the installer, as shipped --------------------------------------------
printf '\nRunning %s\n' "$INSTALLER"
OHM_IMAGE_REPO="localhost:${REG_PORT}/ohm-api" \
OHM_FRONTEND_REPO="localhost:${REG_PORT}/ohm-web" \
OHM_VERSION="$VERSION" \
OHM_DATA_DIR="$DATA" \
OHM_NAME="$NAME" \
OHM_PORT="$PORT" \
OHM_API_PORT="$API_PORT" \
    sh "$INSTALLER" >"$INSTALL_LOG" 2>&1
install_status=$?
KEY=$(sed -n 's/^ *Admin key *\(ohm_[a-f0-9]*\).*/\1/p' "$INSTALL_LOG" | head -n 1)

printf '\nChecks\n'

# 1. It ran, and told the operator the one thing they need.
if [ "$install_status" -eq 0 ] && [ -n "$KEY" ]; then
    pass "the installer exits 0 and prints an admin key"
else
    fail "the installer exits 0 and prints an admin key" \
        "exit status ${install_status}; key found: $([ -n "$KEY" ] && echo yes || echo no)"
    diagnostics
    exit 1   # nothing below means anything without a node
fi

# 2. Docker's own verdict on both containers: what `docker ps` shows an operator.
#    The 0.12.2 web image served normally while reporting "unhealthy" forever.
for c in "$API" "$WEB"; do
    if out=$(sh "${HERE}/wait_container_healthy.sh" "$c" 2>&1); then
        pass "${c} reports healthy"
    else
        fail "${c} reports healthy" "$out"
    fi
done

# 3. The web UI answers, and it proxies /v1 to the API. Through the proxy, so the
#    path an operator's browser takes is the path tested.
[ "$(http_code "http://localhost:${PORT}/")" = "200" ] \
    && pass "the web interface answers on :${PORT}" \
    || fail "the web interface answers on :${PORT}"
code=$(http_code -H "Authorization: Bearer ${KEY}" "http://localhost:${PORT}/v1/api/identity/whoami")
[ "$code" = "200" ] \
    && pass "the admin key authenticates through the web proxy" \
    || fail "the admin key authenticates through the web proxy" "GET /v1/api/identity/whoami -> HTTP ${code}"

# 4. The raw API is published on loopback only. A bare `-p 8001:8001` binds every
#    interface, which is how the API used to be exposed to a cafe network.
host_ip=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "8001/tcp") 0).HostIp}}' "$API" 2>/dev/null)
[ "$host_ip" = "127.0.0.1" ] \
    && pass "the API port is published on 127.0.0.1 only" \
    || fail "the API port is published on 127.0.0.1 only" "published on '${host_ip}'"

# 5. What the storage page reads: the node starts configured, on the mount.
storage=$(curl -s -m 20 -H "Authorization: Bearer ${KEY}" "http://localhost:${PORT}/v1/api/storage/config")
storage_ok=$(printf '%s' "$storage" | python3 -c '
import json, sys
try:
    c = json.load(sys.stdin)["data"]["config"]
    print("yes" if c["provider"] == "local" and c["bucket"] == "/app/storage/objects" and c["configured"] else "no")
except Exception:
    print("no")
')
[ "$storage_ok" = "yes" ] \
    && pass "storage is configured on the mount (local, /app/storage/objects)" \
    || fail "storage is configured on the mount (local, /app/storage/objects)" "GET /v1/api/storage/config -> ${storage}"

# 6. A node with nothing in it says so. Scaffolding writes a placeholder under
#    each prefix, and health and the OKW listing used to count it: an empty node
#    reported one design and one facility, the second with no name.
health=$(curl -s -m 20 "http://localhost:${API_PORT}/health")
health_counts=$(printf '%s' "$health" | python3 -c '
import json, sys
try:
    s = json.load(sys.stdin)["storage"]
    print(s["okh_count"], s["okw_count"])
except Exception:
    print("? ?")
')
total_of() {
    curl -s -m 30 -H "Authorization: Bearer ${KEY}" "http://localhost:${PORT}/v1/api/$1" | python3 -c '
import json, sys
def find(o):
    if isinstance(o, dict):
        if "total_items" in o:
            return o["total_items"]
        for v in o.values():
            r = find(v)
            if r is not None:
                return r
    return None
try:
    print(find(json.load(sys.stdin)))
except Exception:
    print("?")
'
}
okh_total=$(total_of okh)
okw_total=$(total_of okw)
counts="health=[${health_counts}] listings=[${okh_total} ${okw_total}]"
if [ "$health_counts" = "0 0" ] && [ "$okh_total" = "0" ] && [ "$okw_total" = "0" ]; then
    pass "an empty node reports 0 designs and 0 facilities everywhere"
else
    fail "an empty node reports 0 designs and 0 facilities everywhere" \
        "$counts  (okh, okw)" \
        "a scaffold placeholder is being counted as an object by some reader"
fi

# 7. What the API's own document promises a client. Read through the web proxy,
#    as anyone finding the spec from the UI would: the scheme must be the one the
#    server enforces (it declared apiKey, and refused what it declared), and the
#    paths are relative to the /v1 server url (correct, and depended on by the UI).
spec_ok=$(curl -s -m 30 "http://localhost:${PORT}/v1/openapi.json" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    schemes = d["components"]["securitySchemes"].values()
    bearer = bool(schemes) and all(x["type"] == "http" and x["scheme"].lower() == "bearer" for x in schemes)
    print("yes" if bearer and d["servers"] == [{"url": "/v1"}] else "no")
except Exception:
    print("no")
')
[ "$spec_ok" = "yes" ] \
    && pass "the served OpenAPI document declares http bearer, with /v1 as its server" \
    || fail "the served OpenAPI document declares http bearer, with /v1 as its server" \
        "GET /v1/openapi.json through the web proxy did not declare that"

# 8. The flow that 500ed on a clean install: mint an identity in the container as
#    the unprivileged user, and prove its key landed on the mount, not in the
#    container's writable layer.
reg=$(curl -s -m 30 -w '\n%{http_code}' -X POST "http://localhost:${PORT}/v1/api/identity/register" \
    -H 'Content-Type: application/json' -d '{"display_name":"install-check"}')
reg_code=$(printf '%s' "$reg" | tail -n 1)
DID=$(printf '%s' "$reg" | sed '$d' | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("identity", {}).get("did") or d.get("did") or "")
except Exception:
    print("")
')
if [ "$reg_code" = "201" ] && [ -n "$DID" ]; then
    pass "an identity can be minted (HTTP 201)"
else
    fail "an identity can be minted (HTTP 201)" "POST /v1/api/identity/register -> HTTP ${reg_code}: $(printf '%s' "$reg" | sed '$d' | head -c 200)"
fi

if [ -n "$DID" ] && in_data "test -f '/d/federation/identities/${DID}.json'" >/dev/null 2>&1; then
    pass "its key is on the mounted data directory"
else
    fail "its key is on the mounted data directory" \
        "expected <data dir>/federation/identities/${DID:-<did>}.json" \
        "left at its default the key store writes under a home the image does not create"
fi

# 9. Durability: recreate the API container with the same mount, as an operator
#    does to upgrade or to turn on federation, and read the identity back. Keys
#    that lived in the container die here.
envfile="${WORK}/api.env"
docker inspect "$API" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -E '^(API_KEYS=|OHM_|LLM_|LOCAL_STORAGE_PATH=|ENVIRONMENT=|STORAGE_PROVIDER=)' >"$envfile"
docker rm -f "$API" >/dev/null 2>&1
docker run -d --name "$API" --network "$NETWORK" --restart unless-stopped \
    -p "127.0.0.1:${API_PORT}:8001" -v "${DATA}:/app/storage" --env-file "$envfile" \
    "localhost:${REG_PORT}/ohm-api:${VERSION}" >/dev/null 2>&1
up=""
for i in $(seq 1 60); do
    curl -fsS "http://localhost:${API_PORT}/health" >/dev/null 2>&1 && { up=yes; break; }
    sleep 2
done
if [ -z "$up" ]; then
    fail "the identity survives recreating the API container" "the recreated API never became healthy"
else
    code=$(http_code -H "Authorization: Bearer ${KEY}" "http://localhost:${API_PORT}/v1/api/identity/identities/${DID}")
    [ "$code" = "200" ] \
        && pass "the identity survives recreating the API container" \
        || fail "the identity survives recreating the API container" \
            "GET /v1/api/identity/identities/${DID} -> HTTP ${code} after recreate"
fi

# --- Verdict -------------------------------------------------------------------
printf '\n%s passed, %s failed\n' "$passes" "$failures"
if [ "$failures" -ne 0 ]; then
    diagnostics
    exit 1
fi
