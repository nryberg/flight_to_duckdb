#!/bin/bash
#
# Deploy Parquet pipeline scripts to tinkerboard
# This script copies all necessary files to tinkerboard for execution
#

set -e  # Exit on error

# Configuration
REMOTE_HOST="tinkerboard"
REMOTE_USER="${REMOTE_USER:-$(whoami)}"
REMOTE_DIR="${REMOTE_DIR:-/home/$(whoami)/flight_to_duckdb}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================="
echo "Deploy Parquet Pipeline to Tinkerboard"
echo "========================================="
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Remote host: $REMOTE_HOST"
echo "  Remote user: $REMOTE_USER"
echo "  Remote directory: $REMOTE_DIR"
echo ""

# Check if we can connect to tinkerboard
echo "Testing connection to tinkerboard..."
if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${YELLOW}WARNING: Cannot connect to $REMOTE_HOST${NC}"
    echo "Please ensure:"
    echo "  1. Tinkerboard is online"
    echo "  2. SSH is configured (you may need to set up SSH keys)"
    echo "  3. Hostname 'tinkerboard' is resolvable (or update REMOTE_HOST)"
    exit 1
fi
echo -e "${GREEN}✓${NC} Connection successful"
echo ""

# Create remote directory structure
echo "Creating remote directory structure..."
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR/parquet/{hourly,daily,weekly}"
echo -e "${GREEN}✓${NC} Directory structure created"
echo ""

# Copy Python scripts
echo "Copying Python scripts..."
scp capture_hourly.py aggregate_daily.py aggregate_weekly.py "$REMOTE_HOST:$REMOTE_DIR/"
echo -e "${GREEN}✓${NC} Python scripts copied"
echo ""

# Copy setup scripts
echo "Copying setup scripts..."
scp setup_parquet_cron_tinkerboard.sh "$REMOTE_HOST:$REMOTE_DIR/setup_parquet_cron.sh"
scp setup_venv.sh "$REMOTE_HOST:$REMOTE_DIR/"
echo -e "${GREEN}✓${NC} Setup scripts copied"
echo ""

# Make scripts executable on remote
echo "Making scripts executable..."
ssh "$REMOTE_HOST" "chmod +x $REMOTE_DIR/*.py $REMOTE_DIR/setup_parquet_cron.sh $REMOTE_DIR/setup_venv.sh"
echo -e "${GREEN}✓${NC} Scripts are now executable"
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. SSH into tinkerboard:"
echo -e "   ${BLUE}ssh $REMOTE_HOST${NC}"
echo ""
echo "2. Navigate to the deployment directory:"
echo -e "   ${BLUE}cd $REMOTE_DIR${NC}"
echo ""
echo "3. Set up Python virtual environment:"
echo -e "   ${BLUE}./setup_venv.sh${NC}"
echo ""
echo "4. Set up the cron jobs:"
echo -e "   ${BLUE}./setup_parquet_cron.sh${NC}"
echo ""
echo "5. Test the hourly capture manually:"
echo -e "   ${BLUE}venv/bin/python3 capture_hourly.py --backup-dir littlebox:/mnt/usb3/tinkerboard/flights/hourly${NC}"
echo ""
echo "Note: Files are backed up to littlebox:/mnt/usb3/tinkerboard/flights/ via rsync"
echo "      Make sure SSH keys are configured for passwordless access to littlebox."
