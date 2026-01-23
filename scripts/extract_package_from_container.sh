#!/bin/bash
# Extract package from Docker container to host
# Usage: ./scripts/extract_package_from_container.sh [container_name] [package_path_in_container] [destination_path]

set -e

CONTAINER_NAME="${1:-ohm-api}"
PACKAGE_PATH="${2:-/app/test-data/microlab/package}"
DEST_PATH="${3:-./test-data/microlab/package}"

echo "Extracting package from container..."
echo "Container: $CONTAINER_NAME"
echo "Source: $PACKAGE_PATH"
echo "Destination: $DEST_PATH"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container '$CONTAINER_NAME' is not running"
    exit 1
fi

# Check if package exists in container
if ! docker exec "$CONTAINER_NAME" test -d "$PACKAGE_PATH"; then
    echo "Error: Package directory '$PACKAGE_PATH' does not exist in container"
    echo "Available directories in /app/test-data:"
    docker exec "$CONTAINER_NAME" find /app/test-data -type d -maxdepth 3 2>/dev/null || true
    exit 1
fi

# Create destination directory
mkdir -p "$(dirname "$DEST_PATH")"

# Copy package from container
echo "Copying package files..."
docker cp "${CONTAINER_NAME}:${PACKAGE_PATH}" "$DEST_PATH"

# Count files
FILE_COUNT=$(find "$DEST_PATH" -type f | wc -l | tr -d ' ')
echo "✅ Package extracted successfully!"
echo "   Files: $FILE_COUNT"
echo "   Location: $DEST_PATH"
