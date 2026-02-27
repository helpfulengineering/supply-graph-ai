#!/bin/bash
# Diagnostic script for API_PORT environment variable issues
# Run this script to identify potential causes of the API_PORT resolution problem

set -e

echo "=========================================="
echo "API_PORT Environment Variable Diagnostic"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track issues found
ISSUES_FOUND=0

echo "1. Checking Docker Compose version..."
COMPOSE_VERSION=$(docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "not found")
if [[ "$COMPOSE_VERSION" == *"not found"* ]]; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} $COMPOSE_VERSION"
    # Check if version supports ${VAR:-default} syntax (rough check)
    if [[ "$COMPOSE_VERSION" =~ v([0-9]+)\. ]]; then
        MAJOR_VERSION="${BASH_REMATCH[1]}"
        if [ "$MAJOR_VERSION" -lt 2 ]; then
            echo -e "${YELLOW}⚠ Warning: Docker Compose v1.x may not fully support \${VAR:-default} syntax${NC}"
        fi
    fi
fi
echo ""

echo "2. Checking .env file location..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file found at: $(pwd)/.env"
else
    echo -e "${RED}✗ .env file not found in current directory${NC}"
    echo "   Current directory: $(pwd)"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

echo "3. Checking API_PORT in .env file..."
if [ -f ".env" ]; then
    API_PORT_LINE=$(grep "^API_PORT=" .env 2>/dev/null || echo "")
    if [ -z "$API_PORT_LINE" ]; then
        echo -e "${GREEN}✓${NC} API_PORT not set in .env (will use default from docker-compose.yml)"
    else
        echo "   Found: $API_PORT_LINE"
        
        # Check for circular reference or unresolved variable syntax
        if [[ "$API_PORT_LINE" == *'${API_PORT:-'* ]] || [[ "$API_PORT_LINE" == *'${API_PORT'* ]]; then
            echo -e "${RED}✗ CIRCULAR REFERENCE OR UNRESOLVED VARIABLE DETECTED${NC}"
            echo "   .env contains: API_PORT=\${API_PORT:-...}"
            echo "   This creates a circular reference that prevents proper resolution."
            echo "   Note: python-dotenv does NOT perform shell-style variable substitution."
            echo "   It will set API_PORT to the literal string, which will cause issues."
            echo "   Fix: Change to API_PORT=8001 (or remove the line)"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Check for quotes
        if [[ "$API_PORT_LINE" == *'"'* ]] || [[ "$API_PORT_LINE" == *"'"* ]]; then
            echo -e "${YELLOW}⚠ Warning: API_PORT value contains quotes${NC}"
            echo "   Quotes may prevent variable substitution"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Check for spaces around =
        if [[ "$API_PORT_LINE" =~ API_PORT[[:space:]]*=[[:space:]]* ]]; then
            echo -e "${YELLOW}⚠ Warning: Spaces detected around = sign${NC}"
            echo "   Should be: API_PORT=8001 (no spaces)"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Extract and validate value
        API_PORT_VALUE=$(echo "$API_PORT_LINE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
        if [[ "$API_PORT_VALUE" =~ ^[0-9]+$ ]]; then
            echo -e "${GREEN}✓${NC} API_PORT value is numeric: $API_PORT_VALUE"
        else
            echo -e "${RED}✗ API_PORT value is not numeric: $API_PORT_VALUE${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi
else
    echo -e "${YELLOW}⚠ Skipping (no .env file)${NC}"
fi
echo ""

echo "4. Checking shell environment for API_PORT..."
SHELL_API_PORT="${API_PORT:-not set}"
if [ "$SHELL_API_PORT" == "not set" ]; then
    echo -e "${GREEN}✓${NC} API_PORT not set in shell environment"
else
    echo "   Shell API_PORT: $SHELL_API_PORT"
    if [[ "$SHELL_API_PORT" == *'${'* ]]; then
        echo -e "${RED}✗ Shell API_PORT contains unresolved variable syntax${NC}"
        echo "   This will be passed literally to Docker Compose"
        echo "   Fix: unset API_PORT"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    elif [[ "$SHELL_API_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}✓${NC} Shell API_PORT is numeric"
    else
        echo -e "${YELLOW}⚠ Warning: Shell API_PORT is not numeric${NC}"
    fi
fi
echo ""

echo "5. Checking docker-compose.yml syntax..."
if [ -f "docker-compose.yml" ]; then
    if docker-compose config > /dev/null 2>&1 || docker compose config > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} docker-compose.yml syntax is valid"
        
        # Check resolved API_PORT value
        echo "   Checking resolved API_PORT value..."
        RESOLVED=$(docker-compose config 2>/dev/null | grep -A 1 "API_PORT:" | tail -1 | xargs || docker compose config 2>/dev/null | grep -A 1 "API_PORT:" | tail -1 | xargs || echo "not found")
        if [[ "$RESOLVED" == *'${API_PORT:-'* ]]; then
            echo -e "${RED}✗ API_PORT not resolved - still contains literal string${NC}"
            echo "   Resolved value: $RESOLVED"
            echo "   This indicates Docker Compose is not resolving the variable substitution"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        elif [[ "$RESOLVED" =~ ^[0-9]+$ ]] || [[ "$RESOLVED" == *'"8001"'* ]] || [[ "$RESOLVED" == *"'8001'"* ]]; then
            echo -e "${GREEN}✓${NC} API_PORT resolves correctly: $RESOLVED"
        else
            echo -e "${YELLOW}⚠ Resolved value: $RESOLVED${NC}"
        fi
    else
        echo -e "${RED}✗ docker-compose.yml has syntax errors${NC}"
        echo "   Run: docker-compose config (or docker compose config) to see errors"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}✗ docker-compose.yml not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

echo "6. Checking for multiple .env files..."
ENV_FILES=$(find . -maxdepth 2 -name ".env" -type f 2>/dev/null | grep -v node_modules | grep -v ".git")
ENV_COUNT=$(echo "$ENV_FILES" | wc -l | xargs)
if [ "$ENV_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠ No .env files found${NC}"
elif [ "$ENV_COUNT" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} One .env file found: $ENV_FILES"
else
    echo -e "${YELLOW}⚠ Multiple .env files found:${NC}"
    echo "$ENV_FILES" | while read -r file; do
        echo "   - $file"
    done
    echo "   Docker Compose reads from: $(pwd)/.env"
fi
echo ""

echo "7. Checking .dockerignore for .env..."
if [ -f ".dockerignore" ]; then
    if grep -qE "^\.env$|^\.env " .dockerignore 2>/dev/null; then
        echo -e "${YELLOW}⚠ .env is in .dockerignore${NC}"
        echo "   This shouldn't affect Docker Compose, but worth noting"
    else
        echo -e "${GREEN}✓${NC} .env not in .dockerignore"
    fi
else
    echo -e "${GREEN}✓${NC} No .dockerignore file (not an issue)"
fi
echo ""

echo "8. Checking for python-dotenv unresolved variable issue..."
if [ -f ".env" ]; then
    # Check if .env contains unresolved variable syntax that python-dotenv would load literally
    if grep -q "^API_PORT=\${" .env 2>/dev/null; then
        echo -e "${YELLOW}⚠ Warning: .env contains unresolved variable syntax${NC}"
        echo "   python-dotenv does NOT perform shell-style variable substitution."
        echo "   If .env contains API_PORT=\${API_PORT:-8001}, it will be set to the literal string."
        echo "   The Python code now handles this gracefully, but the shell script will still fail."
        echo "   Fix: Change to API_PORT=8001 in .env"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✓${NC} No unresolved variable syntax in .env"
    fi
else
    echo -e "${YELLOW}⚠ Skipping (no .env file)${NC}"
fi
echo ""

echo "=========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No obvious issues found${NC}"
    echo ""
    echo "If the problem persists, try:"
    echo "  1. Remove API_PORT from .env entirely (let docker-compose.yml handle it)"
    echo "  2. Set API_PORT=8001 explicitly in .env"
    echo "  3. Check Docker Compose logs: docker-compose up --no-start"
    echo ""
    echo "Note: The Python code has been updated to handle unresolved variable"
    echo "      substitution gracefully, but the shell script (docker-entrypoint.sh)"
    echo "      will still fail before Python runs if the variable isn't resolved."
else
    echo -e "${RED}✗ Found $ISSUES_FOUND potential issue(s)${NC}"
    echo ""
    echo "Please review the issues above and fix them."
fi
echo "=========================================="

exit $ISSUES_FOUND
