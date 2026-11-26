#!/usr/bin/env bash
# Backup: database (pg_dump -Fc) + configuration + data. secret.key is included in the local
# archive (0600 root) but MUST also be kept off this machine (docs/install.md#backups).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"
require_root
KEEP="${MYPDS_BACKUP_KEEP:-14}"
stamp="$(date +%Y%m%d-%H%M%S)"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
install -d -m 0700 "$BACKUP_DIR"

runuser -u postgres -- pg_dump -Fc mypds > "$work/mypds.dump"
cp -a "$ETC_DIR" "$work/etc"
[ -d "$DATA_DIR" ] && cp -a "$DATA_DIR" "$work/data"
readlink -f "$APP_DIR/current" | xargs basename > "$work/VERSION" 2>/dev/null || true

out="$BACKUP_DIR/mypds-$stamp.tar.gz"
tar -C "$work" -czf "$out" .
chmod 0600 "$out"
echo "Backup: $out ($(du -h "$out" | cut -f1))"
ls -1t "$BACKUP_DIR"/mypds-*.tar.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f
