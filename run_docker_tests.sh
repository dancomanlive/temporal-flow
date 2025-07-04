#!/usr/bin/env bash

# Docker test runner script for Temporal Flow Engine
# This script runs tests in a containerized environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Temporal Flow Engine Tests in Docker${NC}"
echo "=================================================="

# Run tests with coverage
echo -e "${YELLOW}Running tests with coverage...${NC}"
docker compose --profile test run --rm test-runner

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All Docker tests passed!${NC}"
    echo -e "${GREEN}📊 Coverage report available at htmlcov/index.html${NC}"
else
    echo -e "${RED}❌ Some Docker tests failed!${NC}"
    exit 1
fi
