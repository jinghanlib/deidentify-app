#!/bin/bash
#
# De-Identification App Launcher (Mac/Linux)
# One-command launcher that builds and runs the Docker container
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_NAME="deidentify-app"
IMAGE_NAME="deidentify-app"
PORT=8501

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     De-Identification App - Local PII Removal Tool         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Docker is running
docker_running() {
    docker info >/dev/null 2>&1
}

# Step 1: Check if Docker is installed
echo -e "${YELLOW}[1/5]${NC} Checking Docker installation..."
if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  - Mac: https://docs.docker.com/desktop/install/mac-install/"
    echo "  - Linux: https://docs.docker.com/engine/install/"
    echo ""
    echo "After installing, run this script again."
    exit 1
fi
echo -e "       ${GREEN}✓ Docker is installed${NC}"

# Step 2: Check if Docker is running
echo -e "${YELLOW}[2/5]${NC} Checking if Docker is running..."
if ! docker_running; then
    echo -e "${RED}Error: Docker is not running.${NC}"
    echo ""
    echo "Please start Docker Desktop and run this script again."
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "On Mac, you can start Docker from Applications or run:"
        echo "  open -a Docker"
    fi
    exit 1
fi
echo -e "       ${GREEN}✓ Docker is running${NC}"

# Step 3: Create output directories if needed
echo -e "${YELLOW}[3/5]${NC} Ensuring output directories exist..."
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/output"
mkdir -p "$SCRIPT_DIR/audit"
echo -e "       ${GREEN}✓ Directories ready${NC}"

# Step 4: Build the Docker image if it doesn't exist or if --rebuild is passed
echo -e "${YELLOW}[4/5]${NC} Checking Docker image..."
BUILD_NEEDED=false

if [[ "$1" == "--rebuild" ]] || [[ "$1" == "-r" ]]; then
    echo "       Rebuild requested..."
    BUILD_NEEDED=true
elif ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "       Image not found, building..."
    BUILD_NEEDED=true
fi

if [ "$BUILD_NEEDED" = true ]; then
    echo ""
    echo -e "${YELLOW}Building Docker image (this may take 5-10 minutes on first run)...${NC}"
    echo "The SpaCy language model (~560MB) will be downloaded during build."
    echo ""
    docker build -t "$IMAGE_NAME" .
    echo ""
    echo -e "       ${GREEN}✓ Image built successfully${NC}"
else
    echo -e "       ${GREEN}✓ Image already exists (use --rebuild to force rebuild)${NC}"
fi

# Step 5: Stop any existing container and start a new one
echo -e "${YELLOW}[5/5]${NC} Starting the application..."

# Stop existing container if running
if docker ps -q -f name="$APP_NAME" | grep -q .; then
    echo "       Stopping existing container..."
    docker stop "$APP_NAME" >/dev/null 2>&1 || true
fi

# Remove existing container if it exists
docker rm "$APP_NAME" >/dev/null 2>&1 || true

# Run the container with network isolation
docker run -d \
    --name "$APP_NAME" \
    --network none \
    -p "$PORT:8501" \
    -v "$SCRIPT_DIR/data:/workspace/data:ro" \
    -v "$SCRIPT_DIR/output:/workspace/output" \
    -v "$SCRIPT_DIR/audit:/workspace/audit" \
    --memory="4g" \
    --cpus="2.0" \
    "$IMAGE_NAME" >/dev/null

echo -e "       ${GREEN}✓ Application started${NC}"

# Done!
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    App is running!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Open your browser to: ${BLUE}http://localhost:${PORT}${NC}"
echo ""
echo "Usage:"
echo "  • Place input files in: $SCRIPT_DIR/data/"
echo "  • De-identified files saved to: $SCRIPT_DIR/output/"
echo "  • Audit logs saved to: $SCRIPT_DIR/audit/"
echo ""
echo "Commands:"
echo "  • Stop the app:    docker stop $APP_NAME"
echo "  • View logs:       docker logs $APP_NAME"
echo "  • Rebuild:         ./run.sh --rebuild"
echo ""

# Try to open the browser (optional, won't fail if it doesn't work)
sleep 2
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:$PORT" 2>/dev/null || true
elif command_exists xdg-open; then
    xdg-open "http://localhost:$PORT" 2>/dev/null || true
fi
