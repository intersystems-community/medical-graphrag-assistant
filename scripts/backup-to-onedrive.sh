#!/bin/bash
# Backup medical-graphrag-assistant to OneDrive
# Uses rsync for efficient incremental backups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="~/Library/CloudStorage/OneDrive-InterSystemsCorporation/backups/medical-graphrag-assistant"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Backing up to OneDrive..."
echo "Source: $REPO_ROOT"
echo "Destination: $BACKUP_DIR"
echo ""

# rsync options:
# -a: archive mode (preserves permissions, timestamps, etc.)
# -v: verbose
# --delete: remove files in dest that don't exist in source
# --exclude: skip these patterns

rsync -av --delete \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '*.pyc' \
    --exclude '__pycache__/' \
    --exclude '.venv/' \
    --exclude 'venv/' \
    --exclude 'node_modules/' \
    --exclude '.DS_Store' \
    "$REPO_ROOT/" "$BACKUP_DIR/"

echo ""
echo "Backup complete: $(date)"
echo "Files synced to OneDrive - will automatically upload to cloud"
