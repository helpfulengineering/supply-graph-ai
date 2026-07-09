#!/bin/bash
set -e

# Named Docker volumes are often root-owned; ensure ohm can write storage/federation/logs.
if [ "$(id -u)" = "0" ] && [ -z "${OHM_DROPPED_PRIVS:-}" ]; then
    FED_DIR="${OHM_FEDERATION_DATA_DIR:-/app/storage/federation}"
    mkdir -p /app/storage /app/logs "${FED_DIR}"
    chown -R ohm:ohm /app/storage /app/logs "${FED_DIR}" 2>/dev/null || true
    export OHM_DROPPED_PRIVS=1
    exec runuser -u ohm -- "$0" "$@"
fi

# Default values
MODE=${1:-"api"}
API_HOST=${API_HOST:-"0.0.0.0"}
# Support PORT env var (Cloud Run) and API_PORT (backward compatibility)
API_PORT=${PORT:-${API_PORT:-"8001"}}

# Function to start the API server
start_api() {
    echo "Starting Open Hardware Manager API server..."
    echo "Host: $API_HOST"
    echo "Port: $API_PORT"
    echo "Environment: ${ENVIRONMENT:-${ENV:-development}}"

    # Determine if we should use Gunicorn (production) or uvicorn (development)
    ENVIRONMENT=${ENVIRONMENT:-${ENV:-development}}
    USE_GUNICORN=${USE_GUNICORN:-"auto"}

    # Auto-detect: use Gunicorn in production, uvicorn in development
    if [ "$USE_GUNICORN" = "auto" ]; then
        if [ "$ENVIRONMENT" = "production" ]; then
            USE_GUNICORN="true"
        else
            USE_GUNICORN="false"
        fi
    fi

    if [ "$USE_GUNICORN" = "true" ] || [ "$USE_GUNICORN" = "1" ]; then
        echo "Starting with Gunicorn (production mode)..."
        echo "=== Port Configuration Debug ==="
        echo "PORT env var (from Cloud Run): ${PORT:-<not set>}"
        echo "API_PORT env var: ${API_PORT:-<not set>}"
        # Export PORT for gunicorn.conf.py to read (Cloud Run sets PORT=8080)
        export PORT=${PORT:-${API_PORT:-8001}}
        echo "Final PORT value: ${PORT}"
        echo "Gunicorn will bind to: 0.0.0.0:${PORT}"
        echo "================================"
        # Use Gunicorn with uvicorn workers for production
        # Note: bind address is configured in gunicorn.conf.py to use PORT env var
        # Workers/timeout come from gunicorn.conf.py (GUNICORN_WORKERS / GUNICORN_TIMEOUT).
        exec gunicorn src.core.main:app \
            --config gunicorn.conf.py \
            --worker-class uvicorn.workers.UvicornWorker \
            --access-logfile - \
            --error-logfile - \
            --log-level "${LOG_LEVEL:-info}" \
            --graceful-timeout 30 \
            --keep-alive 5
    else
        echo "Starting with Uvicorn (development mode)..."
        # Use uvicorn directly for development (with auto-reload)
        # The installed package ensures proper module resolution
        exec uvicorn src.core.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --reload \
            --reload-dir src
    fi
}

# Function to run CLI commands
run_cli() {
    echo "Running Open Hardware Manager CLI..."
    shift  # Remove the first argument (mode)

    # If no arguments provided, show help
    # Use the installed 'ohm' command if available, otherwise fall back to module execution
    if [ $# -eq 0 ]; then
        if command -v ohm >/dev/null 2>&1; then
            exec ohm --help
        else
            exec python -m src.cli.main --help
        fi
    else
        if command -v ohm >/dev/null 2>&1; then
            exec ohm "$@"
        else
            exec python -m src.cli.main "$@"
        fi
    fi
}

# Function to show help
show_help() {
    echo "Open Hardware Manager Container"
    echo ""
    echo "Usage:"
    echo "  docker run <image> [api|cli] [options]"
    echo ""
    echo "Modes:"
    echo "  api     Start the FastAPI server (default)"
    echo "  cli     Run CLI commands"
    echo "  help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Start API server"
    echo "  docker run <image> api"
    echo ""
    echo "  # Run CLI command"
    echo "  docker run <image> cli okh validate /path/to/file.okh.json"
    echo ""
    echo "  # Run CLI with help"
    echo "  docker run <image> cli --help"
    echo ""
    echo "Environment Variables:"
    echo "  API_HOST          API server host (default: 0.0.0.0)"
    echo "  API_PORT          API server port (default: 8001)"
    echo "  PORT              Cloud Run port (overrides API_PORT if set)"
    echo "  ENVIRONMENT       Environment: development or production (default: development)"
    echo "  USE_GUNICORN      Use Gunicorn: true/false/auto (default: auto)"
    echo "  LOG_LEVEL         Logging level (default: INFO)"
    echo "  DEBUG             Enable debug mode (default: false)"
    echo "  CORS_ORIGINS      CORS allowed origins (default: *)"
    echo "  API_KEYS          Comma-separated API keys"
    echo "  SECRETS_PROVIDER  Secrets provider: env/aws/gcp/azure (default: auto-detect)"
    echo "  USE_SECRETS_MANAGER  Enable secrets manager: true/false (default: false)"
    echo ""
    echo "For more CLI options, use: docker run <image> cli --help"
}

# Main logic
case "$MODE" in
    "api")
        start_api
        ;;
    "cli")
        run_cli "$@"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Use 'help' to see available options"
        exit 1
        ;;
esac
