#!/usr/bin/env bash
# Full restore from an archive made by backup.sh.
# Usage (as root):  ./restore.sh /var/backups/mypds/mypds-YYYYMMDD-HHMMSS.tar.gz
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"
require_root
ARCHIVE="${1:-}"
[ -f "$ARCHIVE" ] || die "Usage: $0 /path/to/backup.tar.gz"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
tar -C "$work" -xzf "$ARCHIVE"
[ -f "$work/mypds.dump" ] || die "Invalid archive (mypds.dump missing)."

read -rp "The current database and configuration will be replaced. Continue? [yes/NO] " ok
[ "$ok" = "yes" ] || die "Cancelled."

systemctl stop "$SERVICE" || true
say "Database"
runuser -u postgres -- dropdb --if-exists mypds
runuser -u postgres -- createdb -O "$APP_USER" mypds
runuser -u postgres -- pg_restore --no-owner --role="$APP_USER" -d mypds "$work/mypds.dump"
say "Configuration and data"
cp -a "$work/etc/." "$ETC_DIR/"
[ -d "$work/data" ] && cp -a "$work/data/." "$DATA_DIR/"
chown root:"$APP_USER" "$ETC_DIR" "$ETC_DIR/mypds.env"; chmod 0640 "$ETC_DIR/mypds.env"
chown "$APP_USER:$APP_USER" "$ETC_DIR/secret.key"; chmod 0400 "$ETC_DIR/secret.key"
chown -R "$APP_USER:$APP_USER" "$DATA_DIR"
say "Migrations (in case the backup comes from an older version)"
run_as_app "$APP_DIR/current/venv/bin/mypds" migrate
systemctl start "$SERVICE"
if wait_ready; then say "Restore complete."; else die "The service does not answer: journalctl -u mypds -n 100"; fi
