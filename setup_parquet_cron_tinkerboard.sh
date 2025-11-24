#!/bin/bash
#
# Setup cron jobs for the Parquet data pipeline on Tinkerboard
# This script configures automated hourly, daily, and weekly aggregation
# with backup to /mnt/usb3/tinkerboard/flights/
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Backup directory on the USB drive
BACKUP_BASE="/mnt/usb3/tinkerboard/flights"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Parquet Pipeline Cron Setup (Tinkerboard)"
echo "========================================="
echo ""
echo "This script will set up automated cron jobs for:"
echo "  1. Hourly capture  - Run every hour (with backup to $BACKUP_BASE/hourly)"
echo "  2. Daily aggregation - Run daily at 1:00 AM (with backup to $BACKUP_BASE/daily)"
echo "  3. Weekly aggregation - Run weekly on Monday at 2:00 AM (with backup to $BACKUP_BASE/weekly)"
echo ""

# Check if Python scripts exist
if [ ! -f "capture_hourly.py" ] || [ ! -f "aggregate_daily.py" ] || [ ! -f "aggregate_weekly.py" ]; then
    echo -e "${RED}ERROR: Required Python scripts not found!${NC}"
    echo "Make sure capture_hourly.py, aggregate_daily.py, and aggregate_weekly.py exist."
    exit 1
fi

# Check if backup directory exists or can be created
if [ ! -d "$BACKUP_BASE" ]; then
    echo -e "${YELLOW}WARNING: Backup directory $BACKUP_BASE does not exist${NC}"
    echo "Attempting to create it..."
    if mkdir -p "$BACKUP_BASE"/{hourly,daily,weekly} 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Backup directory created"
    else
        echo -e "${RED}ERROR: Cannot create backup directory${NC}"
        echo "Please ensure /mnt/usb3/tinkerboard/flights/ is accessible and writable"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✓${NC} Backup directory exists: $BACKUP_BASE"
    # Create subdirectories
    mkdir -p "$BACKUP_BASE"/{hourly,daily,weekly}
fi
echo ""

# Make scripts executable
chmod +x capture_hourly.py aggregate_daily.py aggregate_weekly.py

# Find python3 path
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}ERROR: python3 not found in PATH${NC}"
    exit 1
fi
echo "Using Python: $PYTHON_PATH"
echo ""

# Generate cron entries
CRON_ENTRIES=$(cat <<EOF
# Flight Data Parquet Pipeline (Tinkerboard)
# Managed by setup_parquet_cron.sh
# Backup location: $BACKUP_BASE

# Hourly capture - runs at the top of every hour
# Captures current flight data and backs up to USB drive
0 * * * * cd ${SCRIPT_DIR} && ${PYTHON_PATH} capture_hourly.py --backup-dir ${BACKUP_BASE}/hourly >> parquet_hourly.log 2>&1

# Daily aggregation - runs at 1:00 AM every day
# Aggregates previous day's hourly files and backs up to USB drive
0 1 * * * cd ${SCRIPT_DIR} && ${PYTHON_PATH} aggregate_daily.py --backup-dir ${BACKUP_BASE}/daily >> parquet_daily.log 2>&1

# Weekly aggregation - runs at 2:00 AM every Monday
# Aggregates previous week's daily files and backs up to USB drive
0 2 * * 1 cd ${SCRIPT_DIR} && ${PYTHON_PATH} aggregate_weekly.py --backup-dir ${BACKUP_BASE}/weekly >> parquet_weekly.log 2>&1
EOF
)

echo "The following cron entries will be added:"
echo ""
echo "${CRON_ENTRIES}"
echo ""
echo -e "${YELLOW}WARNING: This will modify your crontab!${NC}"
echo ""

# Ask for confirmation
read -p "Do you want to add these cron jobs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Backup current crontab
BACKUP_FILE="crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
crontab -l > "$BACKUP_FILE" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Current crontab backed up to: $BACKUP_FILE"
else
    echo "No existing crontab found (this is OK if it's your first time using cron)"
fi

# Add new cron entries
(crontab -l 2>/dev/null; echo ""; echo "$CRON_ENTRIES") | crontab -

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Cron jobs added successfully!"
    echo ""
    echo "Schedule:"
    echo "  - Hourly capture:     Every hour at :00"
    echo "  - Daily aggregation:  Every day at 1:00 AM"
    echo "  - Weekly aggregation: Every Monday at 2:00 AM"
    echo ""
    echo "Backup locations:"
    echo "  - Hourly:  $BACKUP_BASE/hourly/"
    echo "  - Daily:   $BACKUP_BASE/daily/"
    echo "  - Weekly:  $BACKUP_BASE/weekly/"
    echo ""
    echo "Logs will be written to:"
    echo "  - parquet_hourly.log"
    echo "  - parquet_daily.log"
    echo "  - parquet_weekly.log"
    echo ""
    echo "To view current cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "To edit cron jobs manually:"
    echo "  crontab -e"
    echo ""
    echo "To remove all cron jobs:"
    echo "  crontab -r"
    echo ""
    echo -e "${GREEN}Test the setup by running:${NC}"
    echo "  python3 capture_hourly.py --backup-dir $BACKUP_BASE/hourly"
else
    echo -e "${RED}ERROR: Failed to add cron jobs${NC}"
    exit 1
fi
