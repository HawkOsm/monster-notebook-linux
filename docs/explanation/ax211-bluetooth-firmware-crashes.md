# Why the AX211 Bluetooth firmware crashes

**Status:** verified
**Applies to:** Intel AX211 combo card, USB `8087:0033`
**Verified on:** Ubuntu 26.04 · kernel 7.0 · Arch Linux · kernel 7.1.8 ·
2026-08-13
**See also:** [pin stable AX211 Bluetooth firmware](../how-to/pin-stable-ax211-bluetooth-firmware.md),
[use a USB Bluetooth adapter](../how-to/use-a-usb-bluetooth-adapter.md)

## In short

Intel's Bluetooth firmware for this chip regressed after build 3243 and never
recovered. Build 3243 runs clean; every later build tested crashes with
`Hardware error 0x0c`, including the current upstream HEAD. There is no fix to
wait for — pin 3243, or route around the chip with a USB adapter.

## The symptom

```text
Bluetooth: hciN: Hardware error 0x0c
Bluetooth: hciN: Retrieving Intel exception info failed (-16)
```

Cadence depends on the kernel. On kernel 6.8 the gap is usually about 13
minutes; on 6.17 and 7.0 it drops to every 1–3 minutes. Once the chip enters a
degraded state it storms, crashing every 30 seconds or so. After each crash the
peripherals drop, `bluetoothd` recovers the link within a few seconds, and the
interruption is long enough to lose keystrokes or need a physical wake.

## The hardware

| Property | Value |
|---|---|
| Chip | Intel AX211 combo (Wi-Fi + Bluetooth), reported by `iwlwifi` as `Intel(R) Wi-Fi 6E AX211` |
| USB ID | `8087:0033` |
| USB topology | Bluetooth half at `usb 3-10` on the internal USB 2.0 hub, path `pci0000:00/0000:00:14.0/usb3` |
| Driver stack | `btusb` (transport) + `btintel` (Intel quirks) |
| Firmware file | `/lib/firmware/intel/ibt-0180-0041.sfi` |
| DDC file | `/lib/firmware/intel/ibt-0180-0041.ddc`, a symlink to `ibt-0040-0041.ddc` |

## Which builds crash

| Build | Timestamp | SHA1 | sha256 (first 16) | Status on this chip |
|---|---|---|---|---|
| **3243** | **2024.18** | **0xa8bb3f39** | **`fceb7e375d020357`** | ✅ **Stable — no Hardware error 0x0c** |
| 3604 | 2024.48 | 0xc115e35a | `acc84f47e763c740` | ❌ Hardware error 0x0c within ~4 min idle (tested 2026-05-17) |
| 3831 | 2025.13 | 0x47cf9d0e | `e3c16c3c4024a84e` | ❌ Crashes within 15 s of load |
| 3882 | 2025.20 | 0x937bca4a | `205f22d76408283b` | ❌ Crashes every ~13 min on 6.8, every 1–3 min on 6.17 / 7.0; **upstream HEAD as of 2025-10-10** |

3243 is the build that originally shipped with Ubuntu 24.04, and first appears
upstream in `linux-firmware-20240703.e94a2a3b-1`. Build 3604 came from the
January 2025 upstream commit `7ccc69cfa4`, taken from `endlessm/linux-firmware`
and cross-verified against `pop-os/linux-firmware`.

## The wrong turn worth knowing about

On 2026-05-13 this investigation concluded that firmware was ruled out. That
conclusion was wrong, and the reason it was wrong is the useful part: it had
only tested two *newer* builds against each other. Both crashed, which looked
like evidence that the firmware was not the variable — when it actually meant
both samples were on the same side of the regression.

Build 3243 was never tested until 2026-05-15, and it ran clean immediately.

**The general lesson: when two versions of a component behave identically
badly, that is not evidence the component is innocent. It is evidence you have
not sampled widely enough.** Reach for the oldest version you can still obtain
before dismissing a suspect.

A fresh Arch install in 2026-08 (kernel `7.1.8-arch1-3`) shipped
`linux-firmware-intel 20260622-1`, which puts down build 3882 — the same crashy
build — confirming nothing has changed upstream.

## What else was ruled out

- **Wi-Fi/Bluetooth 2.4 GHz coexistence.** The classic AX211 failure mode is
  the two radios fighting over a shared RF frontend. This system's Wi-Fi runs
  on 5 GHz (channel 52, 5260 MHz), verified with `iw dev`, so the in-chip
  coexistence path is not active.
- **USB autosuspend.** Already mitigated by
  `/etc/udev/rules.d/99-bluetooth-autosuspend.rules`, which forces
  `power/control=on` for the AX211, plus `btusb.enable_autosuspend=0` on the
  kernel command line. Confirmed: `/sys/bus/usb/devices/3-10/power/control`
  reads `on`.
- **Suspend-related crash storms.** A separate cascading fault: lid-close
  suspend failed because `tracker-miner-fs-3` hung in D-state on fuse I/O, and
  logind retried suspend six times in two minutes. Each failed suspend
  brutalised the firmware. Fixed with a logind drop-in at
  `/etc/systemd/logind.conf.d/01-no-auto-suspend.conf` so only user-initiated
  suspend happens. This is a real contributing factor but not the root cause.

## Why a kernel change will not save you

The crashes are below the driver, in firmware. Newer kernels ship newer
`btintel` and `btusb` patches but cannot fix chip-level faults, and in practice
the newer kernels here made the cadence worse rather than better. On a system
constrained to upstream LTS kernels — Ubuntu 24.04's `linux-image-generic`, the
6.8 series — userspace buffer and codec tuning is the most that can be done in
software. The external USB adapter remains the only definitive fix.

## References

- Linux kernel `btusb` and `btintel` source: `drivers/bluetooth/btusb.c` and
  `drivers/bluetooth/btintel.c`
- The linux-firmware tree:
  <https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/>
