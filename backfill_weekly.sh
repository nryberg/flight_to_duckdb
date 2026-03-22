#!/bin/bash
# Backfill missing weekly parquet aggregations and upload to MinIO

SCRIPT_DIR="/mnt/usb3/tinkerboard/flight_to_duckdb"
DAILY_DIR="/mnt/usb3/tinkerboard/flights/daily"
WEEKLY_DIR="/mnt/usb3/tinkerboard/flights/weekly"
PYTHON="$SCRIPT_DIR/venv/bin/python3"
MC_ALIAS="littlebox"
BUCKET="flight-parquet"

cd "$SCRIPT_DIR"

DATES=(
    2026-02-01
    2026-02-08
    2026-02-15
    2026-02-22
    2026-03-01
)

echo "=== Downloading missing daily files from MinIO ==="
for end_date in "${DATES[@]}"; do
    # Calculate the 7 days for this week (Mon-Sun)
    start_date=$(date -d "$end_date - 6 days" +%Y-%m-%d)
    echo "Fetching daily files for week $start_date to $end_date"
    current="$start_date"
    while [ "$(date -d "$current" +%s)" -le "$(date -d "$end_date" +%s)" ]; do
        file="flights_daily_${current}.parquet"
        if [ ! -f "$DAILY_DIR/$file" ]; then
            mc cp "$MC_ALIAS/$BUCKET/daily/$file" "$DAILY_DIR/$file" 2>/dev/null && echo "  Downloaded $file" || echo "  Not found: $file"
        else
            echo "  Already exists: $file"
        fi
        current=$(date -d "$current + 1 day" +%Y-%m-%d)
    done
done

echo ""
echo "=== Aggregating missing weekly files ==="
for date in "${DATES[@]}"; do
    echo ""
    echo "--- Week ending $date ---"
    $PYTHON aggregate_weekly.py \
        --daily-dir "$DAILY_DIR" \
        --weekly-dir "$WEEKLY_DIR" \
        --end-date "$date"
done

echo ""
echo "=== Uploading weekly files to MinIO ==="
$PYTHON upload_to_minio.py --level weekly --days-back 12

echo ""
echo "=== Done ==="
