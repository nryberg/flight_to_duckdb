#!/bin/bash
#
# Sync raw flight data from tinkerboard to littlebox
# This script runs on TINKERBOARD and syncs /run/dump1090-fa/ to littlebox
#
# Schedule: Every 20 minutes via cron
# Cron entry: */20 * * * * /path/to/sync_raw_to_littlebox.sh >> sync_raw.log 2>&1
#

set -e

# Configuration
REMOTE_HOST="littlebox"
REMOTE_DIR="/mnt/usb3/tinkerboard/raw"
LOCAL_DIR="/run/dump1090-fa"

# Timestamp for logging
echo "========================================="
echo "Sync started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# Check if local directory exists
if [ ! -d "$LOCAL_DIR" ]; then
    echo "ERROR: Local directory not found: $LOCAL_DIR"
    echo "Is dump1090-fa running?"
    exit 1
fi

# Check if we can reach littlebox
if ! ping -c 1 -W 2 "$REMOTE_HOST" > /dev/null 2>&1; then
    echo "WARNING: Cannot reach $REMOTE_HOST"
    echo "Network may be down. Will retry on next cron run."
    exit 1
fi

# Count files before sync
FILE_COUNT=$(ls -1 "$LOCAL_DIR"/*.json 2>/dev/null | wc -l)
echo "Found $FILE_COUNT JSON files in $LOCAL_DIR"

# Sync raw data to littlebox
# -a: archive mode (preserves permissions, timestamps, etc.)
# -v: verbose
# -z: compress during transfer
# --include: only sync JSON files
# --exclude: exclude everything else
echo ""
echo "Syncing to ${REMOTE_HOST}:${REMOTE_DIR}..."
rsync -avz \
    --include='*.json' \
    --exclude='*' \
    "$LOCAL_DIR/" \
    "${REMOTE_HOST}:${REMOTE_DIR}/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Sync completed successfully"
    echo "  Files synced: $FILE_COUNT"
    echo "  Destination: ${REMOTE_HOST}:${REMOTE_DIR}"
else
    echo ""
    echo "✗ Sync failed"
    exit 1
fi

echo ""
echo "Sync finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
