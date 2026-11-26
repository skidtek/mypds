#!/usr/bin/env bash
# Update: backup → new release → migrations → switch → health check → roll back on failure.
# Usage (as root):  ./update.sh /path/to/mypds-X.Y.Z.tar.gz
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"
require_root
ARCHIVE="${1:-}"
[ -f "$ARCHIVE" ] || die "Usage: $0 /path/to/mypds-X.Y.Z.tar.gz"
if [ -f "$ARCHIVE.sha256" ]; then
  (cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256") || die "SHA-256 checksum mismatch."
else
  warn "No .sha256 file next to the archive: integrity not checked."
fi

previous="$(readlink -f "$APP_DIR/current")"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
tar -C "$work" -xzf "$ARCHIVE"
src="$(find "$work" -mindepth 1 -maxdepth 1 -type d | head -1)"

say "Backing up before the update"
"$HERE/backup.sh"

dest="$(install_release "$src" | tail -1)"
say "Stopping the service"
systemctl stop "$SERVICE"
ln -sfn "$dest" "$APP_DIR/current"
say "Migrations"
if ! run_as_app "$APP_DIR/current/venv/bin/mypds" migrate; then
  warn "Migrations failed: switching back to $previous"
  ln -sfn "$previous" "$APP_DIR/current"; systemctl start "$SERVICE"
  die "Update cancelled. If the database was partly migrated, restore the backup (docs/install.md#restoring)."
fi
install -m 0644 "$dest"/deploy/systemd/*.service "$dest"/deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start "$SERVICE"
if wait_ready; then
  say "Updated to $(cat "$dest/VERSION")."
  # Keep the last 3 releases
  ls -1dt "$APP_DIR"/releases/* | tail -n +4 | while read -r old; do [ "$old" != "$previous" ] && rm -rf "$old"; done
else
  warn "The service does not answer: switching back to $previous"
  systemctl stop "$SERVICE"; ln -sfn "$previous" "$APP_DIR/current"; systemctl start "$SERVICE"
  die "Update cancelled. The database may have been migrated: see docs/install.md#restoring if the previous version does not start."
fi
