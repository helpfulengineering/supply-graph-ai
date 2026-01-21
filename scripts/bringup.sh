#!/bin/bash
set -e

# =============================================================================
# Open Hardware Manager Bring-up Script
# =============================================================================
# This script initializes the development environment for Open Hardware Manager.
# It handles configuration, container orchestration, and LLM setup.

# Default configuration
DEFAULT_MODEL="llama3.1:8b"
ENV_FILE=".env"
TEMPLATE_FILE="env.template"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_LLM_FILE="docker-compose.llm.yml"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Initialize the Open Hardware Manager development environment.

Options:
  --help                Show this help message
  --clean               Stop containers and remove volumes (docker-compose down -v)
  --reset               Deep clean: Remove ignored files and build artifacts (git clean -fdX).
                        WARNING: This removes .env and venv! Use with caution.
  --force               Skip confirmation prompts for --reset
  --with-llm            Enable LLM support (checks for local Ollama or starts container)
  --model <name>        Specify Ollama model to pull (default: $DEFAULT_MODEL)
  --env-file <path>     Source env file (default: $ENV_FILE)
  --rebuild             Force rebuild of container images

Examples:
  ./scripts/bringup.sh --with-llm
  ./scripts/bringup.sh --clean --with-llm --model mistral
  ./scripts/bringup.sh --reset
EOF
    exit 1
}

# Parse arguments
CLEAN=false
RESET=false
FORCE=false
WITH_LLM=false
MODEL="$DEFAULT_MODEL"
REBUILD=false
LLM_CONTAINER_NEEDED=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --help) usage ;;
        --clean) CLEAN=true ;;
        --reset) RESET=true ;;
        --force) FORCE=true ;;
        --with-llm) WITH_LLM=true ;;
        --model) MODEL="$2"; shift ;;
        --env-file) ENV_FILE="$2"; shift ;;
        --rebuild) REBUILD=true ;;
        *) log_error "Unknown parameter: $1"; usage ;;
    esac
    shift
done

# =============================================================================
# Pre-flight Checks
# =============================================================================
command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed."; exit 1; }

# Check for python3 (required for cross-platform helper scripts)
command -v python3 >/dev/null 2>&1 || { log_error "python3 is required but not installed."; exit 1; }

command -v docker-compose >/dev/null 2>&1 || {
    # Try 'docker compose' as fallback
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        log_error "docker-compose is required but not installed."; exit 1;
    fi
}
: "${DOCKER_COMPOSE_CMD:=docker-compose}"

# =============================================================================
# Cleanup / Reset
# =============================================================================
if [ "$RESET" = true ]; then
    if [ "$FORCE" = false ]; then
        read -p "WARNING: --reset will remove all ignored files (including .env, venv, build artifacts). Are you sure? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Reset cancelled."
            exit 0
        fi
    fi
    log_info "Performing deep clean..."
    git clean -fdX
    # Also perform standard clean
    CLEAN=true
fi

if [ "$CLEAN" = true ]; then
    log_info "Cleaning up Docker resources..."
    $DOCKER_COMPOSE_CMD down -v --remove-orphans
    if [ "$RESET" = true ]; then
        # If resetting, we probably deleted .env, so we stop here or continue to re-init
        log_info "Clean complete."
    fi
fi

# =============================================================================
# Environment Setup
# =============================================================================
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$TEMPLATE_FILE" ]; then
        log_info "Creating $ENV_FILE from $TEMPLATE_FILE..."
        cp "$TEMPLATE_FILE" "$ENV_FILE"
    else
        log_error "$TEMPLATE_FILE not found. Cannot create configuration."
        exit 1
    fi
fi

# Function to update .env file using Python for cross-platform reliability
# Avoids sed BSD/GNU differences and Windows file locking issues
update_env() {
    local key=$1
    local value=$2
    local file=$3

    python3 -c "
import sys, re

key = sys.argv[1]
value = sys.argv[2]
file_path = sys.argv[3]

with open(file_path, 'r') as f:
    content = f.read()

# Check if key exists
pattern = re.compile(f'^{re.escape(key)}=.*', re.MULTILINE)
if pattern.search(content):
    # Replace existing
    new_content = pattern.sub(f'{key}={value}', content)
else:
    # Append
    new_content = content + f'\n{key}={value}'

with open(file_path, 'w') as f:
    f.write(new_content)
" "$key" "$value" "$file"
}

# =============================================================================
# LLM Configuration
# =============================================================================
COMPOSE_FLAGS="-f $COMPOSE_FILE"

if [ "$WITH_LLM" = true ]; then
    log_info "Configuring LLM support..."

    # Enable LLM in .env
    update_env "LLM_ENABLED" "true" "$ENV_FILE"

    # Check if Ollama is running locally using Python (reliable across OS)
    if python3 -c "import socket; s = socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('localhost', 11434)) == 0 else 1)" 2>/dev/null; then
        log_info "Detected local Ollama running on port 11434."

        # Configure host networking for container to reach host
        if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
            # Mac or Windows (Git Bash/Cygwin)
            OLLAMA_URL="http://host.docker.internal:11434"
        else
            # Linux: Access host via default gateway IP usually 172.17.0.1
            OLLAMA_URL="http://172.17.0.1:11434"
        fi

        update_env "OLLAMA_BASE_URL" "$OLLAMA_URL" "$ENV_FILE"
        log_info "Configured OLLAMA_BASE_URL to $OLLAMA_URL"

    else
        log_info "Local Ollama not detected. Starting containerized Ollama..."
        LLM_CONTAINER_NEEDED=true
        COMPOSE_FLAGS="$COMPOSE_FLAGS -f $COMPOSE_LLM_FILE"

        # Point to the container service name
        update_env "OLLAMA_BASE_URL" "http://ohm-ollama:11434" "$ENV_FILE"
    fi
else
    # Ensure LLM is disabled if not requested (optional, but good for consistency)
    # Actually, we might want to leave it alone if the user manually set it,
    # but for a "bringup" script, enforcing state is often desired.
    pass=true
fi

# =============================================================================
# Launch
# =============================================================================
log_info "Starting environment..."
UP_FLAGS="-d"
if [ "$REBUILD" = true ]; then
    UP_FLAGS="$UP_FLAGS --build"
fi

# Run docker-compose
# shellcheck disable=SC2086
$DOCKER_COMPOSE_CMD $COMPOSE_FLAGS up $UP_FLAGS

# =============================================================================
# Post-Launch Setup
# =============================================================================
if [ "$LLM_CONTAINER_NEEDED" = true ]; then
    log_info "Waiting for Ollama container to be ready..."

    # Simple wait loop
    MAX_RETRIES=30
    COUNT=0
    while [ $COUNT -lt $MAX_RETRIES ]; do
        if docker exec ohm-ollama ollama list >/dev/null 2>&1; then
            break
        fi
        sleep 2
        COUNT=$((COUNT+1))
        echo -n "."
    done
    echo ""

    if [ $COUNT -eq $MAX_RETRIES ]; then
        log_error "Ollama container failed to start within timeout."
    else
        log_info "Ollama is ready. Checking for model: $MODEL"

        # Check if model exists
        if ! docker exec ohm-ollama ollama list | grep -q "$MODEL"; then
            log_info "Pulling model $MODEL (this may take a while)..."
            # Run pull in background or foreground? Foreground so user knows it's happening.
            docker exec ohm-ollama ollama pull "$MODEL"
        else
            log_info "Model $MODEL already exists."
        fi
    fi
fi

log_info "Environment is up and running!"
log_info "API: http://localhost:8001"
if [ "$WITH_LLM" = true ]; then
    log_info "LLM Support: Enabled"
fi
