#!/bin/bash
set -e
BACKUP_DIR="$HOME/shelter-backups"
mkdir -p "$BACKUP_DIR"
DATE=$(date +"%Y-%m-%d_%H-%M")
BACKUP_FILE="$BACKUP_DIR/db_$DATE.sql"

echo "💾 backup..."
docker compose exec -T postgres pg_dump -U shelter shelter > "$BACKUP_FILE"

echo "🐳 updating..."
docker compose down
docker compose up -d --build

docker compose exec backend python init_data.py || true

echo "✅ updated"
echo "backup: $BACKUP_FILE"
