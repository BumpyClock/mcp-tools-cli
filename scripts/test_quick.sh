#!/bin/bash
# ABOUTME: Quick test runner shell script for Unix-like systems (Linux/macOS)
# ABOUTME: Provides fast test execution with common test configurations

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="fast"
PARALLEL=""
COVERAGE=""
VERBOSE=""
TIMEOUT="30"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL="1"
            shift
            ;;
        -c|--coverage)
            COVERAGE="1"
            shift
            ;;
        -v|--verbose)
            VERBOSE="1"
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -t, --type TYPE     Test type (unit, integration, performance, compatibility, smoke, fast, all)"
            echo "  -p, --parallel      Run tests in parallel"
            echo "  -c, --coverage      Enable coverage reporting"
            echo "  -v, --verbose       Verbose output"
            echo "  --timeout SECONDS   Test timeout (default: 30)"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            TEST_TYPE="$1"
            shift
            ;;
    esac
done

echo -e "${CYAN}🚀 MCP Manager Test Runner${NC}"
echo -e "${CYAN}=========================${NC}"

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ Not in project root directory${NC}"
    exit 1
fi

# Build pytest command
COMMAND="python -m pytest"

case $TEST_TYPE in
    unit)
        COMMAND="$COMMAND tests/ -m unit"
        ;;
    integration)
        COMMAND="$COMMAND tests/integration/"
        ;;
    performance)
        COMMAND="$COMMAND tests/performance/"
        ;;
    compatibility)
        COMMAND="$COMMAND tests/compatibility/"
        ;;
    smoke)
        COMMAND="$COMMAND -m smoke"
        ;;
    fast)
        COMMAND="$COMMAND tests/ -m 'not slow and not performance'"
        ;;
    all)
        COMMAND="$COMMAND tests/"
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        echo "Available types: unit, integration, performance, compatibility, smoke, fast, all"
        exit 1
        ;;
esac

# Add common options
COMMAND="$COMMAND --tb=short -v"

# Add optional flags
if [[ -n "$PARALLEL" ]]; then
    WORKERS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    WORKERS=$((WORKERS > 4 ? 4 : WORKERS))
    COMMAND="$COMMAND -n $WORKERS"
    echo -e "${YELLOW}🔄 Running tests in parallel ($WORKERS workers)${NC}"
fi

if [[ -n "$COVERAGE" ]]; then
    COMMAND="$COMMAND --cov=src/mcp_manager --cov-report=term-missing --cov-report=html:htmlcov"
    echo -e "${YELLOW}📊 Coverage reporting enabled${NC}"
fi

if [[ -n "$VERBOSE" ]]; then
    COMMAND="$COMMAND -vv"
fi

COMMAND="$COMMAND --timeout $TIMEOUT"

# Show command being run
echo -e "${CYAN}Command: $COMMAND${NC}"
echo ""

# Run tests
START_TIME=$(date +%s.%N)

if eval $COMMAND; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)

# Show results
echo ""
echo -e "${CYAN}=========================${NC}"
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ Tests PASSED in ${DURATION}s${NC}"
else
    echo -e "${RED}❌ Tests FAILED in ${DURATION}s${NC}"
fi

# Show coverage report location if generated
if [[ -n "$COVERAGE" && -f "htmlcov/index.html" ]]; then
    echo -e "${YELLOW}📊 Coverage report: htmlcov/index.html${NC}"
fi

exit $EXIT_CODE