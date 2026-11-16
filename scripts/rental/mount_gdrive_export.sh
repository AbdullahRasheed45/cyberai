#!/usr/bin/env bash
# Mount a Google Drive remote as the durable evidence/adapter export
# destination for the rental trial. See docs/DURABLE_EXPORT_GDRIVE.md for the
# one-time setup (rclone config + OAuth) that must happen on your OWN machine
# before this script is useful -- this script does no OAuth and holds no
# credentials; it only mounts whatever remote an already-copied
# ~/.config/rclone/rclone.conf defines.
#
# Usage (on the rental instance, after copying rclone.conf over):
#   RCLONE_REMOTE=gdrive:cyberai-trial scripts/rental/mount_gdrive_export.sh
#
# Then:
#   export EVIDENCE_EXPORT_DIR=/mnt/durable/cyberai-trial
#
# scripts/rental/50_export.py and rental.report.copy_verified_bundle are
# unmodified by this: they already copy into $EVIDENCE_EXPORT_DIR and verify
# the write by reading the bytes back. That read-back proves the FUSE mount
# round-tripped correctly on this instance; it does NOT prove the data
# survives provider deletion. Verify that separately, from outside the
# instance, before stopping billing -- see docs/DURABLE_EXPORT_GDRIVE.md.
set -euo pipefail

REMOTE="${RCLONE_REMOTE:?set RCLONE_REMOTE, e.g. gdrive:cyberai-trial}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/durable/cyberai-trial}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone not found; installing to \$HOME/.local/bin (no root required)" >&2
  curl -fsSL https://rclone.org/install.sh | bash -s -- --install-dir "$HOME/.local/bin"
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -f "$HOME/.config/rclone/rclone.conf" ]; then
  echo "Missing \$HOME/.config/rclone/rclone.conf -- copy it from your own" >&2
  echo "machine first (see docs/DURABLE_EXPORT_GDRIVE.md step 1 of 'Per-session use')." >&2
  exit 1
fi

mkdir -p "$MOUNT_POINT"
rclone mount "$REMOTE" "$MOUNT_POINT" \
  --daemon \
  --vfs-cache-mode writes

for _ in $(seq 1 20); do
  mountpoint -q "$MOUNT_POINT" && break
  sleep 0.5
done

if ! mountpoint -q "$MOUNT_POINT"; then
  echo "Mount did not come up at $MOUNT_POINT" >&2
  exit 1
fi

echo "Mounted $REMOTE at $MOUNT_POINT. Use:"
echo "  export EVIDENCE_EXPORT_DIR=$MOUNT_POINT"
