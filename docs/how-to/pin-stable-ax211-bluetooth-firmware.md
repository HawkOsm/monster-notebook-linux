# Pin stable AX211 Bluetooth firmware

**Status:** verified
**Applies to:** Intel AX211 combo card, USB `8087:0033`, in the Monster TULPAR
T6 V2.1 (and any machine with the same chip)
**Verified on:** Ubuntu 26.04 · kernel 7.0 · Arch Linux · kernel 7.1.8 ·
2026-08-13
**Symptom:** Bluetooth peripherals disconnect repeatedly. The kernel log shows
`Bluetooth: hciN: Hardware error 0x0c` followed by
`Retrieving Intel exception info failed (-16)`.
**See also:** [why the AX211 Bluetooth firmware crashes](../explanation/ax211-bluetooth-firmware-crashes.md),
[AX211 Bluetooth configuration](../reference/ax211-bluetooth-configuration.md)

Replace the shipped firmware with build **3243** (timestamp 2024.18), the only
build that runs clean on this silicon, and stop package upgrades putting the
crashy one back.

Every newer build tested crashes, including the current upstream HEAD. The
[explanation](../explanation/ax211-bluetooth-firmware-crashes.md) has the full
build-by-build results.

## Before you start

Build 3243 is no longer shipped by any current distribution, so you need a
copy. This repository caches one at
`firmware-cache/ibt-0180-0041.sfi.stable-3243`, but that path is gitignored —
the blob is Intel-licensed and is not published here. Re-derive it from the
Arch Linux Archive:

```bash
curl -O https://archive.archlinux.org/packages/l/linux-firmware/linux-firmware-20240703.e94a2a3b-1-any.pkg.tar.zst
tar --zstd -xf linux-firmware-20240703.e94a2a3b-1-any.pkg.tar.zst \
    usr/lib/firmware/intel/ibt-0180-0041.sfi.zst -O | zstd -d -o ibt-0180-0041.sfi.stable-3243
sha256sum ibt-0180-0041.sfi.stable-3243   # expect fceb7e375d020357b3ca10dbad2fb5be6ec8a4d6bbb07feb35dc3869dfa440e9
```

> **Back up whatever you currently have before overwriting it.** On a system
> already running 3243, the live `/lib/firmware/intel/ibt-0180-0041.sfi` may be
> the only copy on disk.

## Confirm the diagnosis

```bash
sudo dmesg | grep -E "hci[0-9]+: Firmware (Version|timestamp|SHA1)" | tail -10
# expect: a build other than 3243 — 3604, 3831 or 3882
```

```bash
journalctl -k -b | grep "Hardware error"
```

## Fix

### 1. Install the stable blob

**Arch** ships the firmware compressed as
`/usr/lib/firmware/intel/ibt-0180-0041.sfi.zst`, and the kernel's firmware
loader prefers an uncompressed `.sfi` with the same base name if one sits
beside it. Dropping the blob in is enough — `pacman` does not own that
filename, so `pacman -Syu` can never overwrite it. No hold and no pacman hook
is needed.

```bash
sudo cp firmware-cache/ibt-0180-0041.sfi.stable-3243 \
        /usr/lib/firmware/intel/ibt-0180-0041.sfi
sudo systemctl stop bluetooth
sudo modprobe -r btusb btintel
sudo modprobe btusb
sudo systemctl start bluetooth
journalctl -k -b | grep -E "Firmware (timestamp|SHA1)" | tail -2
# expect: Firmware timestamp 2024.18 buildtype 1 build 3243 / SHA1: 0xa8bb3f39
```

**Ubuntu** ships it uncompressed, so the file you are replacing is the one apt
owns. Copy the blob into place the same way, then protect it in step 2.

### 2. Stop upgrades from replacing it

Arch needs nothing here — see above.

On **Ubuntu**, hold the package:

```bash
sudo apt-mark hold linux-firmware
```

If you ever need to lift the hold, save the blob somewhere apt cannot reach
first:

```bash
# BEFORE anything else — save the stable blob somewhere an upgrade can't touch
sudo cp /lib/firmware/intel/ibt-0180-0041.sfi /root/ibt-0180-0041.sfi.stable-3243
sudo apt-mark unhold linux-firmware
# ... after any linux-firmware upgrade, put 3243 back:
sudo cp /root/ibt-0180-0041.sfi.stable-3243 /lib/firmware/intel/ibt-0180-0041.sfi
sudo modprobe -r btusb btintel && sudo modprobe btusb
sudo apt-mark hold linux-firmware
```

## Verify

```bash
sudo dmesg | grep -E "Firmware (timestamp|Version)" | tail -3
# expect: Firmware timestamp 2024.18 buildtype 1 build 3243
```

Then watch for crashes. On a bad build this fills in minutes; on 3243 it stays
empty:

```bash
journalctl -k -f | grep -E "Hardware error|hci"
```

## Roll back

To return to the distribution's firmware:

```bash
sudo apt-mark unhold linux-firmware
sudo apt-get install --reinstall linux-firmware
sudo systemctl stop bluetooth && sudo modprobe -r btusb btintel && sudo modprobe btusb && sudo systemctl start bluetooth
```

On Arch, delete the uncompressed `.sfi` you added and the loader falls back to
the packaged `.sfi.zst`.

If you kept a copy of a specific newer build — to test whether a future
release is finally stable, for instance:

```bash
sudo cp /lib/firmware/intel/ibt-0180-0041.sfi.upstream-3882 /lib/firmware/intel/ibt-0180-0041.sfi
sudo systemctl stop bluetooth && sudo modprobe -r btusb btintel && sudo modprobe btusb && sudo systemctl start bluetooth
```

## Trade-offs

You are pinning firmware, so you will not receive Intel's fixes for this chip
either. Re-test newer builds occasionally rather than assuming the pin is
permanent.

## Troubleshooting

**Useful diagnostic commands**

```bash
# Firmware crashes in current boot
journalctl -k -b | grep "Hardware error\|hci"

# Live monitor
journalctl -k -f | grep -E "Hardware error|hci|Bluetooth: "

# What firmware is loaded right now (build + sha1 + timestamp)
sudo dmesg | grep -E "hci[0-9]+: Firmware (Version|timestamp|SHA1)" | tail -10

# AX211 USB power state (should be "on")
cat /sys/bus/usb/devices/3-10/power/control

# Reload btusb (re-loads firmware without reboot)
sudo systemctl stop bluetooth && sudo modprobe -r btusb && sudo modprobe btusb && sudo systemctl start bluetooth

# Hot-recover BT after a crash storm
sudo rfkill block bluetooth && sudo rfkill unblock bluetooth

# Confirm WiFi band (5 GHz = good for AX211 coexistence)
iw dev | grep -E "channel|freq"
```

**Crashes continue on 3243**

Confirm the blob actually loaded — the verify step reads the build number from
the kernel, not from the file. If Arch is still loading the `.zst`, check that
your uncompressed file sits in the same directory with the exact base name.

**Nothing helps**

The chip itself is the problem. A
[USB Bluetooth adapter](use-a-usb-bluetooth-adapter.md) sidesteps it entirely.
