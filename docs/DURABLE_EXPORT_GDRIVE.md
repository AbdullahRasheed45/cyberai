# Durable export to Google Drive

Purpose: make Google Drive the durable, off-instance destination that
`EVIDENCE_EXPORT_DIR` points at during the rental trial (see
`RENTAL_START_HERE.md`'s export section). Google Drive only counts as "storage
outside the rental instance" once set up and verified this way -- a bare
folder path proves nothing by itself (`docs/EXECUTION_ENVIRONMENTS.md`,
"Evidence and export").

No code in this repo changes for this to work: `scripts/rental/50_export.py`
and `rental.report.copy_verified_bundle` already copy the evidence bundle into
whatever directory `EVIDENCE_EXPORT_DIR` names and verify the write by reading
the bytes back. Mounting Drive as that directory is the only new piece.

## One-time setup (on your own machine -- never on the rental instance)

1. Install `rclone` locally: https://rclone.org/downloads/
2. `rclone config` -> `n` (new remote) -> name it `gdrive` -> type `drive` ->
   leave client_id/client_secret blank (use rclone's own) -> scope `drive` ->
   follow the browser OAuth prompt it opens. This writes a token into
   `~/.config/rclone/rclone.conf` (Windows: `%APPDATA%\rclone\rclone.conf`).
3. In Drive, create (or reuse) a folder for this project's evidence, e.g.
   `cyberai-trial`.
4. **`rclone.conf` contains an OAuth refresh token -- a credential.** Never
   commit it to this repo and never bake it into a container image. It stays
   on your machine and gets copied to the rental instance per session (below),
   where it is gone the moment the instance is deleted.
5. Rehearse the round trip now, before renting anything:
   ```
   echo durability-test > test.txt
   rclone copy test.txt gdrive:cyberai-trial
   rclone cat gdrive:cyberai-trial/test.txt
   ```
   Confirm the bytes match. This is the "verify copy and readback before
   booking" step `RENTAL_START_HERE.md`'s pre-flight checklist already asks
   for -- do it with the real destination before you pay for anything.

## Per-session use (on the rental instance)

1. After connecting (post `provider_probe.py`), copy your local `rclone.conf`
   to the instance. It is not in git and should never be:
   ```
   scp ~/.config/rclone/rclone.conf <instance-host>:~/.config/rclone/rclone.conf
   ```
2. Mount the remote and point the existing export step at it:
   ```
   RCLONE_REMOTE=gdrive:cyberai-trial scripts/rental/mount_gdrive_export.sh
   export EVIDENCE_EXPORT_DIR=/mnt/durable/cyberai-trial
   ```
3. Run the rental lifecycle as documented in `RENTAL_START_HERE.md`. The
   export step copies into `$EVIDENCE_EXPORT_DIR` and verifies the read-back
   hash, unmodified.
4. That read-back only proves the FUSE mount round-tripped correctly while
   the instance was alive -- `rental/report.py`'s own docstring says this is
   not proof the data survives provider deletion. Before you stop billing,
   verify from OUTSIDE the instance: open the file in Drive's web UI, or from
   your own machine run
   ```
   rclone cat gdrive:cyberai-trial/<bundle>.tar.gz | sha256sum
   ```
   and compare to the hash recorded in that run's `export_result.json`.
5. Delete the instance only after that independent check passes.

## Why Drive is sized fine for this

The export bundle is the evidence/log files plus the LoRA adapter, not the
base model. With the owner's attention-only default
(`DECISIONS_TO_REVISIT.md` R-012), the adapter is ~13M parameters / ~27 MB;
across a full trial's run matrix, total export size is realistically
low-single-digit GB. A free 15 GB Drive account covers this trial; no paid
tier is needed.

The large numbers in `docs/ENVERGE_SETUP.md` (FP8 ~31.2 GB, BF16 ~61.1 GB)
are base-model downloads that live on the ephemeral rental disk only and are
re-fetched from Hugging Face each session -- they are never copied to Drive.

## Revisit

This is a cloud-rental-specific mechanism, logged as `DECISIONS_TO_REVISIT.md`
R-013. When the physical DGX Spark is owned, re-evaluate whether export still
needs to leave the machine at all, or whether local durable storage (NVMe/NAS)
replaces this.
