# X-Rite ICC Extraction — ABANDONED (2026-05-15)

The Windows-on-temp-partition plan was abandoned 2026-05-15 after a
frustrating session — too much hassle for a cosmetic color fix on a
laptop panel that already looks acceptable uncalibrated.

## What was actually done before abandonment
- Monster recovery USB wiped + rewritten as Win11 25H2 installer (image
  backup preserved, see below).
- `xrite-resize.service` was scheduled to run on boot to shrink
  `nvme0n1p1` and create a 100 GiB Windows partition. Its UUID guard
  refused to run all 3 boot attempts (UUID mismatch + late ordering),
  so **no partition changes happened**. Service has been removed.
- Win11 ISO + pre-staged X-Rite tooling were deleted on cleanup.

## What's left on disk

| Item | Location | Notes |
|---|---|---|
| Monster recovery USB image | `~/Documents/Important/monster-recovery-usb-backup/monster-recovery-usb-full.img` | 14.6 GB. Re-flash the physical USB with `sudo dd if=…full.img of=/dev/sdX bs=64M` if you ever need the factory recovery USB back. |
| Color-cal background | `fix-color-calibration.md` | Why this matters, what didn't work. |
| Driver map | `monster-notebook-drivers.md` | S3 URL for `Xrite Color Assistant.zip` is documented there. |

## Watching for a Linux-friendly release

A weekly Claude Code routine watches the Monster driver page and the
S3 bucket for any new file matching ICC / ICM / Linux / "color
profile". If something useful appears it will message into the chat.

- Page watched: `https://support.monsternotebook.com/tr/product/tulpar-t6-v21-ai-creator-bilgisayar/drivers-and-downloads/`
- S3 prefix watched: `https://mnstr-support-files.s3.eu-central-1.amazonaws.com/Drivers/Tulpar%20Serisi/Tulpar%20T6/Tulpar%20T6%20V2.1/`
- Last-checked timestamp + baseline file list: `~/.local/state/xrite-watch/`

To revive the Windows-install plan in the future, this doc's git history
contains the previous step-by-step.
