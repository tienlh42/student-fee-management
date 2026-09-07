#!/usr/bin/env bash
# Khoi phuc Postgres tu file backup do backup_db.sh tao ra.
#
# XOA SACH database hien tai roi nap lai tu backup — khong the hoan tac.
#
#   scripts/restore_db.sh /opt/student-fee-manager/backups/hocphi-20260907-020000.sql.gz
#
# Mac dinh hoi xac nhan. Chi bo qua hoi bang --yes khi ban chac chan (vd: dang
# chay trong quy trinh test restore tu dong, khong phai tay len prod).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/student-fee-manager}"
BACKUP_FILE="${1:-}"
ASSUME_YES=0
for arg in "$@"; do
  [ "$arg" = "--yes" ] && ASSUME_YES=1
done

if [ -z "$BACKUP_FILE" ] || [ "$BACKUP_FILE" = "--yes" ]; then
  echo "Cach dung: $0 <duong-dan-file-backup.sql.gz> [--yes]" >&2
  exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Khong tim thay file: $BACKUP_FILE" >&2
  exit 1
fi

cd "$APP_DIR"
# shellcheck disable=SC1091
set -a; source .env; set +a

echo "!!! Se XOA SACH database '$POSTGRES_DB' va nap lai tu:"
echo "    $BACKUP_FILE"
echo "!!! Du lieu hien tai trong DB se MAT VINH VIEN neu khong backup truoc."

if [ "$ASSUME_YES" -ne 1 ]; then
  read -r -p "Go chinh xac ten database ($POSTGRES_DB) de xac nhan: " CONFIRM
  if [ "$CONFIRM" != "$POSTGRES_DB" ]; then
    echo "Khong khop — huy." >&2
    exit 1
  fi
fi

echo "Dung web de tranh ghi trong luc restore..."
docker compose stop web

echo "Ngat ket noi dang mo toi '$POSTGRES_DB'..."
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
"

echo "Xoa va tao lai database rong..."
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"

echo "Nap du lieu tu backup..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Chay migrate — backup co the cu hon code dang chay..."
docker compose up -d web
docker compose exec -T web python manage.py migrate

echo "$(date -Is) restore ok tu $BACKUP_FILE"
echo "Kiem tra lai du lieu (vd: dang nhap, xem vai hoc sinh/hoa don) truoc khi bao restore thanh cong."
