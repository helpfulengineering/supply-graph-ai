#!/usr/bin/env sh
#
# Install and start an Open Hardware Manager node. No prompts, no arguments.
#
# Published as a release asset with a checksum, so the documented path is to
# fetch it, check it, and read it before running it:
#
#   curl -fsSLO https://openhardwaremanager.org/install.sh
#   curl -fsSLO https://github.com/helpfulengineering/supply-graph-ai/releases/latest/download/install.sh.sha256
#   sha256sum -c install.sh.sha256
#   sh install.sh
#
# The one-liner works too, for those who want it:
#
#   curl -fsSL https://openhardwaremanager.org/install.sh | sh
#
# Installation and configuration are deliberately separate. This script's job
# ends at a healthy, reachable instance; everything that needs a decision —
# which storage, which LLM — is configured afterwards through the running
# instance, in Settings.
#
# That separation is what makes it non-interactive rather than merely quiet. A
# piped script cannot prompt: its stdin is the script text, so a `read` either
# swallows the rest of the script or hits end-of-file. Rather than working
# around that with /dev/tty, there is nothing to ask.
#
# POSIX sh, not bash: the one-liner above runs under whatever /bin/sh is, which
# on Debian and Alpine is not bash.
#
# Environment:
#   OHM_VERSION   pin a version (default: the latest release)
#   OHM_PORT      host port for the web interface (default: 8080)
#   OHM_API_PORT  host port for the API (default: 8001)
#   OHM_DATA_DIR  host directory for data and configuration
#                 (default: ~/.ohm/node)
#   OHM_NAME      name prefix for the containers (default: ohm)

set -eu

IMAGE_REPO="${OHM_IMAGE_REPO:-touchthesun/openhardwaremanager}"
FRONTEND_REPO="${OHM_FRONTEND_REPO:-touchthesun/openhardwaremanager-frontend}"
RELEASES_API="${OHM_RELEASES_API:-https://api.github.com/repos/helpfulengineering/supply-graph-ai/releases/latest}"
# Two containers, because a node is two things. The API serves /v1; the web
# interface is a separate image that serves the pages and reverse-proxies /v1
# to the API, so the browser talks to one origin and there is no CORS to get
# wrong. Installing only the API would produce something healthy that an
# operator cannot open — and the next step this script prints, pasting a key
# into Settings, is a page the API does not serve.
PORT="${OHM_PORT:-8080}"
API_PORT="${OHM_API_PORT:-8001}"
DATA_DIR="${OHM_DATA_DIR:-$HOME/.ohm/node}"
NAME="${OHM_NAME:-ohm}"
API_NAME="${NAME}-api"
WEB_NAME="${NAME}-web"
NETWORK="${NAME}-net"
HEALTH_TIMEOUT="${OHM_HEALTH_TIMEOUT:-180}"

# One mount, not two. A fresh install writes its object storage and its
# configuration in different places, and if either is left in the container
# they die on the first upgrade — the configuration silently, which is worse,
# because the node comes back up pointed at whatever the environment says.
#
# Both live under /app/storage because the image's entrypoint already chowns
# that path to the unprivileged user it drops to; a volume mounted anywhere
# else would be root-owned and unwritable. The object store gets a subdirectory
# rather than the mount root, so the config file is not itself an object in the
# bucket it configures — it would otherwise be listed, served, and erased by a
# storage wipe.
CONTAINER_MOUNT="/app/storage"
CONTAINER_OBJECTS="${CONTAINER_MOUNT}/objects"
CONTAINER_CONFIG="${CONTAINER_MOUNT}/config/storage-config.json"

die() {
    printf '\n[X] %s\n' "$1" >&2
    shift
    for line in "$@"; do printf '    %s\n' "$line" >&2; done
    exit 1
}

say() { printf '  %s\n' "$1"; }

# A secret with no dependency on openssl, which is not everywhere. Hex from
# urandom is fine for both uses: the admin key is a bearer token, and the
# encryption salt and password are fed to PBKDF2.
mint() {
    if [ -r /dev/urandom ]; then
        LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom 2>/dev/null | dd bs=1 count=48 2>/dev/null
    else
        die "Cannot generate a secret: /dev/urandom is not readable." \
            "This host cannot mint the credentials a node needs."
    fi
}

fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$1" 2>/dev/null
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$1" 2>/dev/null
    else
        return 1
    fi
}

printf '\nOpen Hardware Manager\n\n'

# --- Docker ---------------------------------------------------------------
command -v docker >/dev/null 2>&1 || die \
    "Docker is not installed." \
    "OHM runs as a container. Install Docker, then run this again:" \
    "  https://docs.docker.com/get-docker/"

docker info >/dev/null 2>&1 || die \
    "Docker is installed but not running." \
    "Start Docker Desktop (or the docker service) and run this again."

say "Docker: ok"

# --- Version --------------------------------------------------------------
# Resolved at install time rather than hardcoded. A pinned version in this file
# would need a row in the version registry, whose own guidance prefers floating
# pointers to registry rows.
if [ -n "${OHM_VERSION:-}" ]; then
    VERSION="${OHM_VERSION#v}"
    say "Version: ${VERSION} (pinned)"
else
    TAG=$(fetch "$RELEASES_API" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
    [ -n "$TAG" ] || die \
        "Could not resolve the latest release." \
        "Check network access to api.github.com, or pin a version:" \
        "  OHM_VERSION=0.11.1 sh install.sh"
    VERSION="${TAG#v}"
    say "Version: ${VERSION} (latest release)"
fi

IMAGE="${IMAGE_REPO}:${VERSION}"
FRONTEND_IMAGE="${FRONTEND_REPO}:${VERSION}"

# --- Port -----------------------------------------------------------------
in_use=$(docker ps --format '{{.Ports}}' 2>/dev/null || true)
for p in "$PORT" "$API_PORT"; do
    if printf '%s' "$in_use" | grep -q ":${p}->"; then
        die "Port ${p} is already in use by another container." \
            "Free it, or choose other ports:" \
            "  OHM_PORT=9080 OHM_API_PORT=9001 sh install.sh"
    fi
done

existing=$(docker ps -a --format '{{.Names}}' 2>/dev/null || true)
for n in "$API_NAME" "$WEB_NAME"; do
    if printf '%s' "$existing" | grep -qx "${n}"; then
        die "A container named '${n}' already exists." \
            "Remove the old node if you meant to reinstall:" \
            "  docker rm -f ${API_NAME} ${WEB_NAME}" \
            "Or install alongside it under another name:" \
            "  OHM_NAME=ohm-2 OHM_PORT=9080 OHM_API_PORT=9001 sh install.sh"
    fi
done

say "Ports ${PORT} and ${API_PORT}: free"

# --- Secrets --------------------------------------------------------------
# The most important thing this script does besides starting the container.
# Credential storage refuses to operate under the built-in default encryption
# keys, so a node installed without a minted secret is one whose FIRST
# configuration action fails — it starts, it looks healthy, and it cannot be
# given storage credentials.
# Both spellings, deliberately. OHM_ENCRYPTION_* is the current name; images
# published before that rename (#371, which landed after v0.11.1) read only
# LLM_ENCRYPTION_*, ignore the new names, and then refuse to start in
# production because they see no encryption configured. Since this script
# installs the LATEST RELEASE by default, it has to work with the images that
# actually exist, not only with the ones the current source would produce.
#
# Harmless on newer images: the resolver prefers OHM_ and only warns when it
# falls back, which it will not do while both are set. Remove the LLM_ pair
# once the oldest supported release understands OHM_.
ADMIN_KEY="ohm_$(mint)"
ENCRYPTION_SALT=$(mint)
ENCRYPTION_PASSWORD=$(mint)

[ -n "$ADMIN_KEY" ] && [ -n "$ENCRYPTION_SALT" ] && [ -n "$ENCRYPTION_PASSWORD" ] || die \
    "Failed to mint credentials." \
    "Without them the node could not be configured after install."

say "Credentials: minted"

# --- Data directory -------------------------------------------------------
mkdir -p "$DATA_DIR" || die \
    "Could not create ${DATA_DIR}." \
    "Choose a writable location:" \
    "  OHM_DATA_DIR=/srv/ohm sh install.sh"

say "Data: ${DATA_DIR}"

# --- Start ----------------------------------------------------------------
printf '  Pulling %s ...\n' "$IMAGE"
docker pull "$IMAGE" >/dev/null 2>&1 || die \
    "Could not pull ${IMAGE}." \
    "Check the version exists and that this host can reach Docker Hub."

printf '  Pulling %s ...\n' "$FRONTEND_IMAGE"
docker pull "$FRONTEND_IMAGE" >/dev/null 2>&1 || die \
    "Could not pull ${FRONTEND_IMAGE}." \
    "Check the version exists and that this host can reach Docker Hub."

# A user-defined network, so the web container can reach the API by name.
docker network create "$NETWORK" >/dev/null 2>&1 || true

# LLM is enabled with no credential on purpose. It resolves from the credential
# store before the environment, and enabled-with-nothing-configured reports
# cleanly as unavailable — so "enabled" here means "a key added in Settings
# works without a restart". Installing with it disabled would produce a node
# that can never be given an LLM without reinstalling.
docker run -d \
    --name "$API_NAME" \
    --network "$NETWORK" \
    --restart unless-stopped \
    -p "${API_PORT}:8001" \
    -v "${DATA_DIR}:${CONTAINER_MOUNT}" \
    -e "API_KEYS=${ADMIN_KEY}" \
    -e "OHM_ENCRYPTION_SALT=${ENCRYPTION_SALT}" \
    -e "OHM_ENCRYPTION_PASSWORD=${ENCRYPTION_PASSWORD}" \
    -e "LLM_ENCRYPTION_SALT=${ENCRYPTION_SALT}" \
    -e "LLM_ENCRYPTION_PASSWORD=${ENCRYPTION_PASSWORD}" \
    -e "STORAGE_PROVIDER=local" \
    -e "LOCAL_STORAGE_PATH=${CONTAINER_OBJECTS}" \
    -e "OHM_STORAGE_CONFIG_PATH=${CONTAINER_CONFIG}" \
    -e "LLM_ENABLED=true" \
    -e "ENVIRONMENT=production" \
    "$IMAGE" >/dev/null || die \
    "The API container failed to start." \
    "See what it said with:  docker logs ${API_NAME}"

say "API: started"

# --- Health ---------------------------------------------------------------
# The API first, because the web container proxies to it and would come up
# looking fine while every page it serves failed.
printf '  Waiting for the API '
elapsed=0
healthy=""
while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    if fetch "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
        healthy="yes"
        break
    fi
    if [ -z "$(docker ps -q -f "name=^${API_NAME}$")" ]; then
        printf '\n'
        die "The API container exited while starting." \
            "See why with:  docker logs ${API_NAME}"
    fi
    printf '.'
    sleep 3
    elapsed=$((elapsed + 3))
done
printf '\n'

if [ -z "$healthy" ]; then
    # A half-installed node is worse than none: the next run would fail on the
    # name collision and the operator would have to work out why themselves.
    docker rm -f "$API_NAME" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
    die "The API did not become healthy within ${HEALTH_TIMEOUT}s." \
        "The container has been removed so you can run this again." \
        "If it keeps happening, start it by hand to see the logs:" \
        "  docker run --rm ${IMAGE}"
fi

say "API: healthy"

docker run -d \
    --name "$WEB_NAME" \
    --network "$NETWORK" \
    --restart unless-stopped \
    -p "${PORT}:8080" \
    -e "API_UPSTREAM_URL=http://${API_NAME}:8001" \
    "$FRONTEND_IMAGE" >/dev/null || {
    docker rm -f "$API_NAME" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
    die "The web container failed to start." \
        "The API container has been removed so you can run this again."
}

printf '  Waiting for the web interface '
elapsed=0
web_up=""
while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    if fetch "http://localhost:${PORT}/" >/dev/null 2>&1; then
        web_up="yes"
        break
    fi
    printf '.'
    sleep 3
    elapsed=$((elapsed + 3))
done
printf '\n'

[ -n "$web_up" ] || die \
    "The API is healthy but the web interface did not answer on port ${PORT}." \
    "The API is still running and usable at http://localhost:${API_PORT}." \
    "See what the web container said with:  docker logs ${WEB_NAME}"

say "Web: ready"

# --- Done -----------------------------------------------------------------
cat <<EOF

  Your node is running.

    Open        http://localhost:${PORT}
    API         http://localhost:${API_PORT}
    Admin key   ${ADMIN_KEY}

  Save that key somewhere safe. It is shown once and is not stored anywhere
  you can read it back from.

  Next: open http://localhost:${PORT}/settings/session and paste the key, then
  configure storage at http://localhost:${PORT}/settings/storage. The node
  starts on local storage in ${DATA_DIR}, which works — point it at a cloud
  provider when you want to.

    docker logs ${API_NAME}                  what the API is doing
    docker stop ${API_NAME} ${WEB_NAME}      stop the node
    docker start ${API_NAME} ${WEB_NAME}     start it again

EOF
