# Fix: ~70 Seconds Added to Every Boot (snapd-desktop-integration)

**Symptom:** boot takes ~2 minutes wall-clock, with a long dead pause between
the GDM login and a usable GNOME session. `systemd-analyze` looks innocent
(userspace a few seconds) because the stall is in the *user* session, not the
system boot.

**Tested on:** Ubuntu 26.04 · GNOME 50 (but this is generic Ubuntu-with-snaps,
not Monster-specific)

---

## Why This Happens

The `snapd-desktop-integration` snap's user service can get into a
crash-restart loop at session start (theming/portal handshake fails, systemd
restarts it, repeat). Each round trip blocks the session's startup transaction
until the loop gives up — here that was ~70 seconds of staring at a frozen
desktop, every single boot.

## Confirming

```bash
systemd-analyze blame --user | head            # the usual suspects list
journalctl --user -b | grep -i snapd-desktop   # look for repeated restarts/failures
```

## The Fix

Mask the user service — GNOME neither needs it for anything essential (it
handles snap theme/cursor syncing) nor misses it visibly:

```bash
systemctl --user mask snap.snapd-desktop-integration.snapd-desktop-integration.service
```

Reboot. On this machine boot went from ~2 minutes to a few seconds of
userspace (the remaining ~30 s of a cold start is firmware + GRUB loading a
large initramfs — see [fix-gdm-black-greeter.md](fix-gdm-black-greeter.md)
for why the initramfs is big).

Rollback:

```bash
systemctl --user unmask snap.snapd-desktop-integration.snapd-desktop-integration.service
```
