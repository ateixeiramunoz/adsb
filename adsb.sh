#!/bin/bash
#
# ADS-B Data Collection Toolchain - One Script to Rule Them All
#
# This script starts dump1090 and runs the appropriate Python collector.
# Usage:
#   ./adsb.sh csv    # Run CSV logger
#   ./adsb.sh db     # Run database logger (when implemented)
#   ./adsb.sh api    # Run API server (when implemented)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DUMP1090_CMD="${DUMP1090_CMD:-dump1090}"
DUMP1090_HOST="${ADSB_HOST:-127.0.0.1}"
DUMP1090_PORT="${ADSB_PORT:-30003}"
STARTUP_DELAY=3  # seconds to wait for dump1090 to start

# Mode selection
MODE="${1:-csv}"

# Function to check if dump1090 is available
check_dump1090() {
    if ! command -v "$DUMP1090_CMD" &> /dev/null; then
        echo -e "${RED}Error: $DUMP1090_CMD not found in PATH${NC}"
        echo "Please install dump1090 or set DUMP1090_CMD environment variable"
        exit 1
    fi
}

# Function to check if port is already in use
check_port() {
    if lsof -Pi :"$DUMP1090_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Port $DUMP1090_PORT is already in use${NC}"
        echo "Assuming dump1090 is already running..."
        return 0
    fi
    return 1
}

# Function to start dump1090
start_dump1090() {
    echo -e "${GREEN}Starting dump1090...${NC}"
    "$DUMP1090_CMD" --net --interactive > /dev/null 2>&1 &
    DUMP1090_PID=$!
    echo "dump1090 started with PID: $DUMP1090_PID"
    
    # Wait for dump1090 to start listening
    echo "Waiting for dump1090 to start..."
    for i in {1..10}; do
        if lsof -Pi :"$DUMP1090_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}dump1090 is ready on $DUMP1090_HOST:$DUMP1090_PORT${NC}"
            return 0
        fi
        sleep 0.5
    done
    
    echo -e "${RED}Error: dump1090 failed to start or is not listening on port $DUMP1090_PORT${NC}"
    kill $DUMP1090_PID 2>/dev/null || true
    exit 1
}

# Function to cleanup on exit
cleanup() {
    if [ -n "$DUMP1090_PID" ] && kill -0 "$DUMP1090_PID" 2>/dev/null; then
        echo -e "\n${YELLOW}Stopping dump1090 (PID: $DUMP1090_PID)...${NC}"
        kill "$DUMP1090_PID" 2>/dev/null || true
        wait "$DUMP1090_PID" 2>/dev/null || true
    fi
    if [ -n "$CSV_PID" ] && kill -0 "$CSV_PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping CSV logger (PID: $CSV_PID)...${NC}"
        kill "$CSV_PID" 2>/dev/null || true
        wait "$CSV_PID" 2>/dev/null || true
    fi
    if [ -n "$HTTP_PID" ] && kill -0 "$HTTP_PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping HTTP server (PID: $HTTP_PID)...${NC}"
        kill "$HTTP_PID" 2>/dev/null || true
        wait "$HTTP_PID" 2>/dev/null || true
    fi
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Main execution
case "$MODE" in
    csv)
        echo "=== ADS-B CSV Logger ==="
        check_dump1090
        
        # Check if dump1090 is already running
        if ! check_port; then
            start_dump1090
            sleep "$STARTUP_DELAY"
        fi
        
        # Run the CSV logger
        echo -e "${GREEN}Starting CSV logger...${NC}"
        python3 adsb_to_csv.py
        ;;
    
    db)
        echo "=== ADS-B Database Logger ==="
        echo -e "${YELLOW}Database logger (Step 2) not yet implemented.${NC}"
        echo "See SPEC.md for implementation details."
        exit 1
        ;;
    
    api)
        echo "=== ADS-B HTTP API Server ==="
        echo -e "${YELLOW}HTTP API server (Step 3) not yet implemented.${NC}"
        echo "See SPEC.md for implementation details."
        exit 1
        ;;
    
    live)
        echo "=== ADS-B Live Capture + Map ==="
        check_dump1090
        
        # Check if dump1090 is already running
        if ! check_port; then
            start_dump1090
            sleep "$STARTUP_DELAY"
        fi
        
        # Check if folium is installed
        if ! python3 -c "import folium" 2>/dev/null; then
            echo -e "${RED}Error: folium is not installed.${NC}"
            echo "Install it with: pip install folium"
            exit 1
        fi
        
        # Start CSV logger in background
        echo -e "${GREEN}Starting CSV logger in background...${NC}"
        python3 adsb_to_csv.py &
        CSV_PID=$!
        
        # Wait a moment for some data to accumulate
        sleep 3
        
        # Start HTTP server in background
        HTTP_PORT="${ADSB_HTTP_PORT:-8000}"
        
        # Check if port is already in use and kill all existing processes
        EXISTING_PIDS=$(lsof -ti:"$HTTP_PORT" 2>/dev/null || true)
        if [ -n "$EXISTING_PIDS" ]; then
            echo -e "${YELLOW}Port $HTTP_PORT is already in use (PIDs: $EXISTING_PIDS)${NC}"
            echo -e "${YELLOW}Killing existing process(es)...${NC}"
            echo "$EXISTING_PIDS" | xargs kill -9 2>/dev/null || true
            sleep 2
            # Verify port is now free
            if lsof -ti:"$HTTP_PORT" >/dev/null 2>&1; then
                echo -e "${RED}Warning: Port $HTTP_PORT still in use after kill attempt${NC}"
            fi
        fi
        
        echo -e "${GREEN}Starting HTTP server on port $HTTP_PORT...${NC}"
        python3 serve_map.py --port "$HTTP_PORT" &
        HTTP_PID=$!
        sleep 2
        
        # Verify server started
        if ! kill -0 "$HTTP_PID" 2>/dev/null; then
            echo -e "${RED}Error: HTTP server failed to start${NC}"
            echo "Try a different port: python3 serve_map.py --port 8001"
            exit 1
        fi
        
        # Check if port is listening
        if ! lsof -i :"$HTTP_PORT" >/dev/null 2>&1; then
            echo -e "${YELLOW}Warning: Server started but port $HTTP_PORT may not be listening yet${NC}"
            sleep 1
        else
            echo -e "${GREEN}HTTP server is ready on port $HTTP_PORT${NC}"
        fi
        
        # Start map watcher
        echo -e "${GREEN}Starting map watcher...${NC}"
        echo -e "${YELLOW}Map will be saved to: adsb_map.html${NC}"
        echo -e "${GREEN}Open http://127.0.0.1:$HTTP_PORT/adsb_map.html in your browser${NC}"
        echo -e "${YELLOW}Map updates automatically every second!${NC}"
        echo ""
        
        # Run map watcher (this will run in foreground)
        python3 watch_map.py
        
        # If we get here, map watcher exited, cleanup
        kill $CSV_PID 2>/dev/null || true
        kill $HTTP_PID 2>/dev/null || true
        ;;
    
    *)
        echo "Usage: $0 {csv|db|api|live}"
        echo ""
        echo "Modes:"
        echo "  csv  - Run CSV logger (Step 1)"
        echo "  db   - Run database logger (Step 2 - TODO)"
        echo "  api  - Run HTTP API server (Step 3 - TODO)"
        echo "  live - Run CSV logger + auto-update map (one command to rule them all!)"
        exit 1
        ;;
esac


