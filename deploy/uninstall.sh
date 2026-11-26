#!/usr/bin/env bash
# Uninstall. By default, keeps the database, configuration and backups.
# Usage (as root):  ./uninstall.sh [--purge]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"
require_root
PURGE="${1:-}"
read -rp "Uninstall My Personal Digital Space? [yes/NO] " ok
[ "$ok" = "yes" ] || die "Cancelled."
systemctl disable --now mypds.service mypds-backup.timer 2>/dev/null || true
rm -f /etc/systemd/system/mypds.service /etc/systemd/system/mypds-backup.service /etc/systemd/system/mypds-backup.timer
systemctl daemon-reload
rm -f /etc/sysctl.d/60-mypds-ping.conf
cd / && rm -rf "$APP_DIR"
if [ "$PURGE" = "--purge" ]; then
  read -rp "PURGE: delete the database, the configuration (including secret.key) and the backups? [yes/NO] " ok2
  if [ "$ok2" = "yes" ]; then
    runuser -u postgres -- dropdb --if-exists mypds
    runuser -u postgres -- psql -qc "DROP ROLE IF EXISTS $APP_USER"
    rm -rf "$ETC_DIR" "$DATA_DIR" "$BACKUP_DIR"
    userdel "$APP_USER" 2>/dev/null || true
    say "Purge complete."
  fi
else
  say "Application removed. Kept: the \"mypds\" database, $ETC_DIR, $DATA_DIR, $BACKUP_DIR (see docs/install.md#uninstalling)."
fi
