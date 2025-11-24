#!/bin/bash
#
# Setup Python virtual environment for flight data parquet pipeline
# This script creates a venv and installs all required dependencies
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Python Virtual Environment Setup"
echo "========================================="
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}"
    echo "Please install Python 3.7 or higher first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${BLUE}Found:${NC} $PYTHON_VERSION"

# Extract major.minor version (e.g., "3.10" from "Python 3.10.12")
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${BLUE}Python version:${NC} $PYTHON_VER"
echo ""

# Check if python3-venv is available (needed on Debian/Ubuntu/Armbian)
echo "Checking for python3-venv package..."
if ! python3 -m venv --help &>/dev/null 2>&1; then
    echo -e "${YELLOW}WARNING: python3-venv module not available${NC}"
    echo ""
    echo "On Armbian/Debian/Ubuntu systems, you need to install the version-specific venv package:"
    echo -e "  ${BLUE}sudo apt install -y python${PYTHON_VER}-venv${NC}"
    echo ""
    read -p "Do you want to install python${PYTHON_VER}-venv now? (requires sudo) (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing python${PYTHON_VER}-venv..."

        # Try version-specific package first (e.g., python3.10-venv)
        sudo apt install -y python${PYTHON_VER}-venv

        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}Version-specific package failed, trying python3-venv...${NC}"
            sudo apt install -y python3-venv
        fi

        # Verify installation
        if ! python3 -m venv --help &>/dev/null 2>&1; then
            echo -e "${RED}ERROR: Failed to install python3-venv${NC}"
            echo ""
            echo "Please install it manually:"
            echo "  sudo apt update"
            echo "  sudo apt install -y python${PYTHON_VER}-venv"
            echo ""
            echo "Then run this script again."
            exit 1
        fi

        echo -e "${GREEN}✓${NC} python3-venv installed successfully"
        echo ""
    else
        echo ""
        echo "Please install python3-venv manually and run this script again:"
        echo "  sudo apt update"
        echo "  sudo apt install -y python${PYTHON_VER}-venv"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} python3-venv is available"
    echo ""
fi

# Check if venv already exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists at:${NC} venv/"
    echo ""
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing venv..."
        rm -rf venv
    else
        echo "Using existing venv. To reinstall packages, activate it and run:"
        echo "  source venv/bin/activate"
        echo "  pip install --upgrade duckdb folium"
        exit 0
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
    echo ""
    echo "If you see 'ensurepip is not available', you may need to install python3-venv:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3-venv"
    exit 1
fi

echo -e "${GREEN}✓${NC} Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip --quiet

echo -e "${GREEN}✓${NC} pip upgraded"
echo ""

# Install required packages
echo "Installing required packages..."
echo ""

echo -e "${BLUE}[1/2]${NC} Installing duckdb..."
pip install duckdb

echo ""
echo -e "${BLUE}[2/2]${NC} Installing folium (for visualization)..."
pip install folium

echo ""
echo -e "${GREEN}✓${NC} All packages installed successfully"
echo ""

# Verify installations
echo "Verifying installations..."
DUCKDB_VERSION=$(python3 -c "import duckdb; print(duckdb.__version__)" 2>/dev/null)
FOLIUM_VERSION=$(python3 -c "import folium; print(folium.__version__)" 2>/dev/null)

if [ -n "$DUCKDB_VERSION" ]; then
    echo -e "${GREEN}✓${NC} DuckDB version: $DUCKDB_VERSION"
else
    echo -e "${RED}✗${NC} DuckDB installation failed"
fi

if [ -n "$FOLIUM_VERSION" ]; then
    echo -e "${GREEN}✓${NC} Folium version: $FOLIUM_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Folium installation failed (optional, only needed for visualization)"
fi

echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Virtual environment location:"
echo "  $SCRIPT_DIR/venv"
echo ""
echo "To activate the virtual environment manually:"
echo -e "  ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "To deactivate when done:"
echo -e "  ${BLUE}deactivate${NC}"
echo ""
echo "To run scripts with the venv without activating:"
echo -e "  ${BLUE}venv/bin/python3 script.py${NC}"
echo ""
echo "Next steps:"
echo "  1. Test manual capture: venv/bin/python3 capture_hourly.py"
echo "  2. Set up cron jobs: ./setup_parquet_cron.sh"
echo ""

# Deactivate venv
deactivate
