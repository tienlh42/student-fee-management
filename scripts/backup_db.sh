#!/usr/bin/env bash
# Backup Postgres hang dem. Day la app quan ly tien — dung bo qua buoc nay.
#
# Cai dat tren VPS (crontab -e cua user chay docker):
#   15 2 * * * /opt/student-fee-manager/scripts/backup_db.sh >> /var/log/hocphi-backup.log 2>&1
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/student-fee-manager}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

cd "$APP_DIR"
# shellcheck disable=SC1091
set -a; source .env; set +a

mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/${POSTGRES_DB}-${STAMP}.sql.gz"

docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$OUT"
echo "$(date -Is) backup ok: $OUT ($(du -h "$OUT" | cut -f1))"

find "$BACKUP_DIR" -name '*.sql.gz' -mtime "+$KEEP_DAYS" -delete
