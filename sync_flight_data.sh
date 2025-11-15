#!/bin/bash
#
# Sync flight data from tinkerboard and load into DuckDB
# This script is designed to be run by cron every 20 minutes
#

# Change to the script directory
cd "$(dirname "$0")" || exit 1

# Log file for cron output
LOG_FILE="sync_flight_data.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "===== Starting flight data sync ====="

# Step 1: Rsync data from tinkerboard
log "Syncing data from tinkerboard:/run/dump1090-fa/ ..."
if rsync -ah --timeout=60 tinkerboard:/run/dump1090-fa/ ./raw/ >> "$LOG_FILE" 2>&1; then
    log "✓ Rsync completed successfully"
else
    log "✗ ERROR: Rsync failed with exit code $?"
    exit 1
fi

# Step 2: Load data into DuckDB
log "Loading data into DuckDB..."
if python3 load_to_duckdb.py >> "$LOG_FILE" 2>&1; then
    log "✓ Database load completed successfully"
else
    log "✗ ERROR: Database load failed with exit code $?"
    exit 1
fi

log "===== Flight data sync completed ====="
echo "" >> "$LOG_FILE"

exit 0
