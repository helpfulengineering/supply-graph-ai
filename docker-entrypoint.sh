#!/bin/bash
set -e

# Default values
MODE=${1:-"api"}
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-"8000"}

# Function to start the API server
start_api() {
    echo "Starting Open Matching Engine API server..."
    echo "Host: $API_HOST"
    echo "Port: $API_PORT"
    echo "Environment: ${ENV:-development}"
    
    # Start the FastAPI server
    exec python run.py
}

# Function to run CLI commands
run_cli() {
    echo "Running Open Matching Engine CLI..."
    shift  # Remove the first argument (mode)
    
    # If no arguments provided, show help
    if [ $# -eq 0 ]; then
        exec python -m src.cli.main --help
    else
        # Pass all remaining arguments to the CLI
        exec python -m src.cli.main "$@"
    fi
}

# Function to show help
show_help() {
    echo "Open Matching Engine Container"
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
    echo "  API_HOST     API server host (default: 0.0.0.0)"
    echo "  API_PORT     API server port (default: 8000)"
    echo "  LOG_LEVEL    Logging level (default: INFO)"
    echo "  DEBUG        Enable debug mode (default: false)"
    echo "  CORS_ORIGINS CORS allowed origins (default: *)"
    echo "  API_KEYS     Comma-separated API keys"
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
