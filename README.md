# Monster Notebook Linux Fix

A collection of step-by-step guides for fixing common hardware issues on Monster (Clevo-based) notebooks running Linux.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+

---

## What's Covered

| Problem | Guide |
|---------|-------|
| Keyboard backlight dead or stuck off | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |
| Touchpad locked (disabled at the hardware level) | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |
| `nvidia-smi` fails after a kernel upgrade | [fix-nvidia.md](fix-nvidia.md) |
| All rendering on Intel iGPU instead of RTX 4070 | [fix-gpu-prime.md](fix-gpu-prime.md) |
| Temperature and fan sensor monitoring | [temps-monitoring.md](temps-monitoring.md) |
| TUXEDO Control Center shows no fan/temperature at all (ABRA A5) | [fix-tuxedo-fan-temp-abra.md](fix-tuxedo-fan-temp-abra.md) |

---

## Guides

### [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md)

Fixes the keyboard backlight and the hardware-locked touchpad. The root cause is that `tuxedo-drivers` rejects systems where the DMI vendor is `"MONSTER"` instead of `"TUXEDO"`. This guide walks through patching the source, rebuilding the DKMS module, and installing a persistent systemd service so the touchpad re-enables itself on every boot.

### [fix-nvidia.md](fix-nvidia.md)

Fixes `nvidia-smi` failures after a kernel upgrade. The Tuxedo apt repository uses an epoch-pinned NVIDIA package that blocks Ubuntu's per-kernel module packages from installing. This guide shows how to pin Ubuntu's packages at a higher priority and upgrade to the correct version.

### [fix-gpu-prime.md](fix-gpu-prime.md)

Switches the GPU PRIME profile from the default `on-demand` mode (Intel renders everything) to `nvidia` mode (RTX 4070 renders everything). Also covers how to switch back for better battery life.

### [temps-monitoring.md](temps-monitoring.md)

Sets up a terminal thermal dashboard showing CPU package and core temperatures, NVMe drive temps, GPU temperature, GPU power and clock speed, and both fan RPMs.

### [fix-tuxedo-fan-temp-abra.md](fix-tuxedo-fan-temp-abra.md)

Fixes TUXEDO Control Center's dashboard showing no fan speed or temperature on the ABRA A5. The root cause is that the OEM firmware doesn't fully answer the standard Clevo WMI fan-info calls, so `tccd` gives up on its whole sensor update cycle. This guide ships a board-specific out-of-tree hwmon driver that feeds `tccd` a real CPU temperature (from the package thermal MSR, same source as coretemp) and live fan duty percent (from the reverse-engineered EC MMIO registers) through the hwmon path `tccd` already supports, instead of the broken WMI path. Includes the patched driver source in [`tuxedo-abra-fan-fix/`](tuxedo-abra-fan-fix/).

---

## Tested Configuration

| Component | Details |
|-----------|---------|
| Laptop | Monster TULPAR T6 V2.1 |
| CPU | Intel Core Ultra 7 155H (Meteor Lake) |
| GPU | NVIDIA GeForce RTX 4070 Laptop |
| EC | ITE IT5570E |
| OS | Ubuntu 24.04 LTS |
| Kernel | 6.17.0-23-generic |
| Tuxedo drivers | tuxedo-drivers 4.22.2 |
| NVIDIA driver | 580.142 |

| Component | Details |
|-----------|---------|
| Laptop | Monster ABRA A5 V20.2 |
| CPU | Intel Core i5-13500H (Raptor Lake) |
| GPU | NVIDIA GeForce RTX 4050 Laptop |
| BIOS | N.1.13MON07 |
| OS | Ubuntu 22.04 LTS |
| Kernel | 6.8.0-124-generic |
| Tuxedo drivers | tuxedo-drivers 4.22.2 |
| Board-specific driver | tuxedo-abra-fan 1.0 (out-of-tree, EC MMIO) |
