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
        echo "Updating package list..."
        sudo apt update
        echo ""

        echo "Installing python${PYTHON_VER}-venv and dependencies..."

        # Install venv, development headers, and build tools (needed for compiling packages)
        sudo apt install -y \
            python${PYTHON_VER}-venv \
            python${PYTHON_VER}-dev \
            python${PYTHON_VER}-distutils \
            build-essential \
            cmake \
            git \
            2>/dev/null

        # If version-specific failed, try generic
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}Version-specific packages not found, trying generic packages...${NC}"
            sudo apt install -y python3-venv python3-dev python3-pip python3-distutils build-essential cmake git
        fi

        echo ""
        echo "Verifying installation..."

        # Verify installation by trying to import venv
        if ! python3 -m venv --help &>/dev/null 2>&1; then
            echo -e "${RED}ERROR: venv module still not available after installation${NC}"
            echo ""
            echo "Please try installing these packages manually:"
            echo "  sudo apt update"
            echo "  sudo apt install -y python${PYTHON_VER}-venv python${PYTHON_VER}-dev python${PYTHON_VER}-distutils build-essential"
            echo ""
            echo "If that doesn't work, try:"
            echo "  sudo apt install -y python3-full python3-dev build-essential"
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
echo "This may take several minutes as packages compile for ARM architecture..."
echo ""

echo -e "${BLUE}[1/3]${NC} Installing pandas..."
pip install pandas --no-cache-dir

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} pandas installation failed"
else
    echo -e "${GREEN}✓${NC} pandas installed"
fi

echo ""
echo -e "${BLUE}[2/3]${NC} Installing duckdb (this may take 5-10 minutes to compile)..."
pip install duckdb --no-cache-dir

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} DuckDB installation failed"
    echo ""
    echo "DuckDB compilation requires significant resources. You may need to:"
    echo "  1. Ensure you have at least 2GB of free RAM"
    echo "  2. Add swap space if needed: sudo fallocate -l 2G /swapfile"
    echo "  3. Install additional dependencies: sudo apt install -y cmake git build-essential"
    echo ""
    echo "Skipping DuckDB for now..."
else
    echo -e "${GREEN}✓${NC} DuckDB installed"
fi

echo ""
echo -e "${BLUE}[3/3]${NC} Installing folium (for visualization - optional)..."
pip install folium --no-cache-dir 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠${NC} Folium installation failed (optional, only needed for visualization)"
else
    echo -e "${GREEN}✓${NC} Folium installed"
fi

echo ""
echo -e "${GREEN}✓${NC} All packages installed successfully"
echo ""

# Verify installations
echo "Verifying installations..."
PANDAS_VERSION=$(python3 -c "import pandas; print(pandas.__version__)" 2>/dev/null)
DUCKDB_VERSION=$(python3 -c "import duckdb; print(duckdb.__version__)" 2>/dev/null)
FOLIUM_VERSION=$(python3 -c "import folium; print(folium.__version__)" 2>/dev/null)

if [ -n "$PANDAS_VERSION" ]; then
    echo -e "${GREEN}✓${NC} pandas version: $PANDAS_VERSION"
else
    echo -e "${RED}✗${NC} pandas installation failed"
fi

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
