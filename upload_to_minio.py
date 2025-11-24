#!/usr/bin/env python3
"""
Upload hourly Parquet files to MinIO object storage.
Reads credentials from .env file and uploads files to configured bucket.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error


def upload_hourly_files(hourly_dir: str, bucket_name: str, minio_endpoint: str,
                        access_key: str, secret_key: str, days_back: int = 1,
                        delete_after_upload: bool = False):
    """
    Upload hourly Parquet files to MinIO.

    Args:
        hourly_dir: Directory containing hourly Parquet files
        bucket_name: MinIO bucket name
        minio_endpoint: MinIO server endpoint (host:port)
        access_key: MinIO access key
        secret_key: MinIO secret key
        days_back: Number of days back to upload (default: 1 = yesterday's files)
        delete_after_upload: Delete local files after successful upload
    """
    hourly_path = Path(hourly_dir)

    if not hourly_path.exists():
        print(f"ERROR: Hourly directory not found: {hourly_dir}", file=sys.stderr)
        sys.exit(1)

    # Initialize MinIO client
    # Remove http:// or https:// from endpoint if present
    endpoint = minio_endpoint.replace('http://', '').replace('https://', '')

    # Determine if we should use secure connection (https)
    secure = minio_endpoint.startswith('https://')

    print(f"Connecting to MinIO at {endpoint} (secure={secure})...")
    try:
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
    except Exception as e:
        print(f"ERROR: Failed to connect to MinIO: {e}", file=sys.stderr)
        sys.exit(1)

    # Create bucket if it doesn't exist
    try:
        if not client.bucket_exists(bucket_name=bucket_name):
            print(f"Creating bucket: {bucket_name}")
            client.make_bucket(bucket_name=bucket_name)
            print(f"✓ Bucket '{bucket_name}' created")
        else:
            print(f"✓ Bucket '{bucket_name}' exists")
    except S3Error as e:
        print(f"ERROR: Failed to check/create bucket: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate date range for files to upload
    end_date = datetime.now() - timedelta(days=1)  # Yesterday
    start_date = end_date - timedelta(days=days_back - 1)

    print(f"\nLooking for files from {start_date.date()} to {end_date.date()}...")

    # Find files to upload
    pattern = "flights_hourly_*.parquet"
    all_files = sorted(hourly_path.glob(pattern))

    if not all_files:
        print(f"No hourly files found matching pattern: {pattern}")
        return

    # Filter files by date range
    files_to_upload = []
    for file_path in all_files:
        # Extract date from filename: flights_hourly_YYYY-MM-DD_HH00.parquet
        try:
            filename = file_path.name
            date_str = filename.split('_')[2]  # Gets YYYY-MM-DD
            file_date = datetime.strptime(date_str, '%Y-%m-%d')

            if start_date.date() <= file_date.date() <= end_date.date():
                files_to_upload.append(file_path)
        except (IndexError, ValueError) as e:
            print(f"WARNING: Could not parse date from filename {filename}: {e}")
            continue

    if not files_to_upload:
        print(f"No files found in date range {start_date.date()} to {end_date.date()}")
        return

    print(f"Found {len(files_to_upload)} files to upload")

    # Upload files
    uploaded_count = 0
    failed_count = 0
    deleted_count = 0

    for file_path in files_to_upload:
        filename = file_path.name
        object_name = f"hourly/{filename}"  # Store in hourly/ prefix

        try:
            # Check if file already exists
            try:
                client.stat_object(bucket_name=bucket_name, object_name=object_name)
                print(f"⊘ {filename} - already exists, skipping")
                continue
            except S3Error as e:
                if e.code != 'NoSuchKey':
                    raise
                # File doesn't exist, proceed with upload

            # Upload file
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print(f"↑ Uploading {filename} ({file_size_mb:.2f} MB)...", end=' ')

            client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=str(file_path),
                content_type='application/octet-stream'
            )

            print("✓")
            uploaded_count += 1

            # Delete local file if requested
            if delete_after_upload:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    print(f"  🗑 Deleted local file: {filename}")
                except Exception as e:
                    print(f"  WARNING: Failed to delete local file {filename}: {e}")

        except S3Error as e:
            print(f"✗ ERROR uploading {filename}: {e}", file=sys.stderr)
            failed_count += 1
        except Exception as e:
            print(f"✗ ERROR processing {filename}: {e}", file=sys.stderr)
            failed_count += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"Upload Summary:")
    print(f"  Uploaded: {uploaded_count} files")
    print(f"  Skipped:  {len(files_to_upload) - uploaded_count - failed_count} files (already exist)")
    print(f"  Failed:   {failed_count} files")
    if delete_after_upload:
        print(f"  Deleted:  {deleted_count} local files")
    print(f"{'='*50}")

    if failed_count > 0:
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Upload hourly Parquet files to MinIO object storage'
    )
    parser.add_argument('--hourly-dir', default='/mnt/usb3/tinkerboard/flights/hourly',
                       help='Directory containing hourly Parquet files')
    parser.add_argument('--bucket', default='flight-parquet',
                       help='MinIO bucket name (default: flight-parquet)')
    parser.add_argument('--days-back', type=int, default=1,
                       help='Number of days back to upload (default: 1)')
    parser.add_argument('--delete-after-upload', action='store_true',
                       help='Delete local files after successful upload')
    parser.add_argument('--env-file', default='.env',
                       help='Path to .env file with MinIO credentials (default: .env)')

    args = parser.parse_args()

    # Load environment variables from .env file
    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"ERROR: Environment file not found: {args.env_file}", file=sys.stderr)
        print(f"\nCreate a .env file with the following variables:", file=sys.stderr)
        print(f"  MINIO_ENDPOINT=100.107.134.23:9000", file=sys.stderr)
        print(f"  MINIO_ACCESS_KEY=your_access_key", file=sys.stderr)
        print(f"  MINIO_SECRET_KEY=your_secret_key", file=sys.stderr)
        print(f"\nSee .env.example for a template.", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_path)

    # Get MinIO configuration from environment
    minio_endpoint = os.getenv('MINIO_ENDPOINT')
    access_key = os.getenv('MINIO_ACCESS_KEY')
    secret_key = os.getenv('MINIO_SECRET_KEY')

    if not all([minio_endpoint, access_key, secret_key]):
        print("ERROR: Missing required environment variables in .env file:", file=sys.stderr)
        if not minio_endpoint:
            print("  - MINIO_ENDPOINT", file=sys.stderr)
        if not access_key:
            print("  - MINIO_ACCESS_KEY", file=sys.stderr)
        if not secret_key:
            print("  - MINIO_SECRET_KEY", file=sys.stderr)
        sys.exit(1)

    print("="*50)
    print("MinIO Hourly Parquet Upload")
    print("="*50)
    print(f"MinIO endpoint: {minio_endpoint}")
    print(f"Bucket: {args.bucket}")
    print(f"Hourly directory: {args.hourly_dir}")
    print(f"Days back: {args.days_back}")
    print(f"Delete after upload: {args.delete_after_upload}")
    print("="*50)
    print()

    try:
        upload_hourly_files(
            args.hourly_dir,
            args.bucket,
            minio_endpoint,
            access_key,
            secret_key,
            args.days_back,
            args.delete_after_upload
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
