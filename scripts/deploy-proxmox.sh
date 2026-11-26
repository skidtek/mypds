#!/usr/bin/env bash
# shellcheck disable=SC2029  # paths are fixed here and deliberately expanded locally before going over SSH
# Deploys My Personal Digital Space to a Proxmox VE node, from your computer:
#   1. builds the release archive (scripts/build-release.sh);
#   2. copies it to the node over SSH, with deploy/proxmox/create-ct.sh;
#   3. runs that script on the node, which creates a Debian 13 container and installs MyPDS (interactive).
#
# Usage:  scripts/deploy-proxmox.sh root@pve [--no-build]                 new container
#         scripts/deploy-proxmox.sh root@pve --light [--no-build]         small throwaway container with demo data
#                                                                         (1 vCPU, 1 GB, 6 GB, no start at boot)
#         scripts/deploy-proxmox.sh root@pve --update <CTID> [--no-build] update an existing container (backup,
#                                                                         migrations, automatic rollback)
# CTID, CT_HOSTNAME, CT_STORAGE, CT_DISK_GB, CT_CORES, CT_MEMORY_MB, CT_SWAP_MB, CT_BRIDGE, CT_VLAN, CT_IP, CT_GW,
# CT_ONBOOT, CT_TAGS, DEMO, PUBLIC_ORIGIN, PROXY_IP, ADMIN_USER and ADMIN_NAME, when set here, are passed to the
# node as pre-filled answers. The admin password is always typed on the node.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"
BUILD=1
UPDATE_CT=""
usage() { echo "Usage: $0 root@<proxmox-node> [--update <CTID> | --light] [--no-build]" >&2; exit 1; }
if [ -z "$TARGET" ] || [[ "$TARGET" == -* ]]; then usage; fi
shift
while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --light)
      : "${CT_HOSTNAME:=mypds-light}" "${CT_CORES:=1}" "${CT_MEMORY_MB:=1024}" "${CT_SWAP_MB:=256}" "${CT_DISK_GB:=6}"
      : "${CT_ONBOOT:=0}" "${CT_TAGS:=mypds;demo}" "${DEMO:=1}" "${PUBLIC_ORIGIN:=}"
      export CT_HOSTNAME CT_CORES CT_MEMORY_MB CT_SWAP_MB CT_DISK_GB CT_ONBOOT CT_TAGS DEMO ;;
    --update) [[ "${2:-}" =~ ^[0-9]+$ ]] || usage; UPDATE_CT="$2"; shift ;;
    *) usage ;;
  esac
  shift
done

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/backend/pyproject.toml")"
ARCHIVE="$ROOT/dist/mypds-$VERSION.tar.gz"
if [ "$BUILD" = 1 ] || [ ! -f "$ARCHIVE" ]; then
  "$ROOT/scripts/build-release.sh"
fi
[ -f "$ARCHIVE" ] && [ -f "$ARCHIVE.sha256" ] || { echo "Archive not found: $ARCHIVE" >&2; exit 1; }

REMOTE=/root/mypds-install
echo "==> Copying to $TARGET:$REMOTE"
ssh "$TARGET" "mkdir -p $REMOTE && chmod 700 $REMOTE"
scp -q "$ARCHIVE" "$ARCHIVE.sha256" "$ROOT/deploy/proxmox/create-ct.sh" "$TARGET:$REMOTE/"

if [ -n "$UPDATE_CT" ]; then
  name="mypds-$VERSION.tar.gz"
  echo "==> Updating container $UPDATE_CT to $VERSION"
  # update.sh from the installed release: checks the archive, backs up, migrates, switches, checks, rolls back on failure
  if ssh -t "$TARGET" "set -e; pct status $UPDATE_CT | grep -q running || { echo 'Container $UPDATE_CT is stopped or does not exist' >&2; exit 1; }
    pct push $UPDATE_CT $REMOTE/$name /root/$name && pct push $UPDATE_CT $REMOTE/$name.sha256 /root/$name.sha256
    pct exec $UPDATE_CT -- /opt/mypds/current/deploy/update.sh /root/$name
    pct exec $UPDATE_CT -- rm -f /root/$name /root/$name.sha256"; then
    ssh "$TARGET" "rm -rf $REMOTE"
    echo "==> Container $UPDATE_CT is up to date ($VERSION)."
  else
    echo "Update failed: files left in $TARGET:$REMOTE for investigation." >&2
    exit 1
  fi
  exit 0
fi

# Pre-filled answers (when set locally), passed without interpretation by the remote shell
envs=""
for v in CTID CT_HOSTNAME CT_STORAGE CT_DISK_GB CT_CORES CT_MEMORY_MB CT_SWAP_MB CT_BRIDGE CT_VLAN CT_IP CT_GW \
         CT_ONBOOT CT_TAGS DEMO PUBLIC_ORIGIN PROXY_IP ADMIN_USER ADMIN_NAME; do
  if [ -n "${!v:-}" ]; then envs+=" $v=$(printf '%q' "${!v}")"; fi
done

echo "==> Installing on the node (interactive)"
if ssh -t "$TARGET" "env$envs bash $REMOTE/create-ct.sh $REMOTE/mypds-$VERSION.tar.gz"; then
  ssh "$TARGET" "rm -rf $REMOTE"
else
  echo "Failed: files left in $TARGET:$REMOTE for investigation (to retry: ssh -t $TARGET bash $REMOTE/create-ct.sh $REMOTE/mypds-$VERSION.tar.gz)" >&2
  exit 1
fi
