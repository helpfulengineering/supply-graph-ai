#!/bin/bash

# Container Test Script for Open Matching Engine
# This script tests the containerized OHM application

set -e

echo "🧪 Testing Open Matching Engine Containerization"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_build() {
    echo -e "\n${YELLOW}📦 Testing Docker build...${NC}"
    if docker build -t ome-test . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker build successful${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker build failed${NC}"
        return 1
    fi
}

test_api_startup() {
    echo -e "\n${YELLOW}🚀 Testing API server startup...${NC}"
    
    # Start container in background
    CONTAINER_ID=$(docker run -d -p 8001:8001 \
        -e API_KEYS="test-key-123" \
        -e LOG_LEVEL="INFO" \
        ome-test api)
    
    # Wait for startup
    echo "Waiting for API server to start..."
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API server started successfully${NC}"
        echo -e "${GREEN}✅ Health check passed${NC}"
        
        # Test API docs
        if curl -f http://localhost:8001/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API documentation accessible${NC}"
        else
            echo -e "${YELLOW}⚠️  API documentation not accessible${NC}"
        fi
        
        # Cleanup
        docker stop $CONTAINER_ID > /dev/null 2>&1
        docker rm $CONTAINER_ID > /dev/null 2>&1
        return 0
    else
        echo -e "${RED}❌ API server failed to start or health check failed${NC}"
        
        # Show logs for debugging
        echo "Container logs:"
        docker logs $CONTAINER_ID
        docker stop $CONTAINER_ID > /dev/null 2>&1
        docker rm $CONTAINER_ID > /dev/null 2>&1
        return 1
    fi
}

test_cli_help() {
    echo -e "\n${YELLOW}💻 Testing CLI help command...${NC}"
    
    if docker run --rm ome-test cli --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅ CLI help command works${NC}"
        return 0
    else
        echo -e "${RED}❌ CLI help command failed${NC}"
        return 1
    fi
}

test_cli_version() {
    echo -e "\n${YELLOW}📋 Testing CLI version command...${NC}"
    
    if docker run --rm ome-test cli version > /dev/null 2>&1; then
        echo -e "${GREEN}✅ CLI version command works${NC}"
        return 0
    else
        echo -e "${RED}❌ CLI version command failed${NC}"
        return 1
    fi
}

test_environment_variables() {
    echo -e "\n${YELLOW}🔧 Testing environment variable support...${NC}"
    
    # Test custom API port
    CONTAINER_ID=$(docker run -d -p 8001:8001 \
        -e API_PORT="8001" \
        -e API_KEYS="test-key-456" \
        -e LOG_LEVEL="DEBUG" \
        ome-test api)
    
    sleep 5
    
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Environment variables work correctly${NC}"
        docker stop $CONTAINER_ID > /dev/null 2>&1
        docker rm $CONTAINER_ID > /dev/null 2>&1
        return 0
    else
        echo -e "${RED}❌ Environment variables test failed${NC}"
        docker stop $CONTAINER_ID > /dev/null 2>&1
        docker rm $CONTAINER_ID > /dev/null 2>&1
        return 1
    fi
}

test_docker_compose() {
    echo -e "\n${YELLOW}🐳 Testing Docker Compose...${NC}"
    
    # Start services
    if docker-compose up -d ome-api > /dev/null 2>&1; then
        sleep 10
        
        # Test health endpoint
        if curl -f http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker Compose setup works${NC}"
            docker-compose down > /dev/null 2>&1
            return 0
        else
            echo -e "${RED}❌ Docker Compose health check failed${NC}"
            docker-compose down > /dev/null 2>&1
            return 1
        fi
    else
        echo -e "${RED}❌ Docker Compose startup failed${NC}"
        docker-compose down > /dev/null 2>&1
        return 1
    fi
}

# Main test execution
main() {
    echo "Starting containerization tests..."
    
    TESTS_PASSED=0
    TESTS_TOTAL=6
    
    # Run tests
    test_build && ((TESTS_PASSED++))
    test_api_startup && ((TESTS_PASSED++))
    test_cli_help && ((TESTS_PASSED++))
    test_cli_version && ((TESTS_PASSED++))
    test_environment_variables && ((TESTS_PASSED++))
    test_docker_compose && ((TESTS_PASSED++))
    
    # Summary
    echo -e "\n${YELLOW}📊 Test Summary${NC}"
    echo "==============="
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}/$TESTS_TOTAL"
    
    if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
        echo -e "\n${GREEN}🎉 All tests passed! Containerization is working correctly.${NC}"
        echo -e "\n${YELLOW}Next steps:${NC}"
        echo "1. Copy env.template to .env and configure your settings"
        echo "2. Run: docker-compose up ome-api"
        echo "3. Access API docs at: http://localhost:8001/docs"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed. Please check the output above.${NC}"
        exit 1
    fi
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed or not in PATH${NC}"
    exit 1
fi

# Run main function
main "$@"
