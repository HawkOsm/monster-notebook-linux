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
| Steam fails with "Missing X server or $DISPLAY" | [fix-steam-x11-socket.md](fix-steam-x11-socket.md) |
| Temperature and fan sensor monitoring | [temps-monitoring.md](temps-monitoring.md) |

---

## Guides

### [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md)

Fixes the keyboard backlight and the hardware-locked touchpad. The root cause is that `tuxedo-drivers` rejects systems where the DMI vendor is `"MONSTER"` instead of `"TUXEDO"`. This guide walks through patching the source, rebuilding the DKMS module, and installing a persistent systemd service so the touchpad re-enables itself on every boot.

### [fix-nvidia.md](fix-nvidia.md)

Fixes `nvidia-smi` failures after a kernel upgrade. The Tuxedo apt repository uses an epoch-pinned NVIDIA package that blocks Ubuntu's per-kernel module packages from installing. This guide shows how to pin Ubuntu's packages at a higher priority and upgrade to the correct version.

### [fix-gpu-prime.md](fix-gpu-prime.md)

Switches the GPU PRIME profile from the default `on-demand` mode (Intel renders everything) to `nvidia` mode (RTX 4070 renders everything). Also covers how to switch back for better battery life.

### [fix-steam-x11-socket.md](fix-steam-x11-socket.md)

Fixes Steam exiting with "Missing X server or $DISPLAY" / "SDL_Init failed: No available video device" on this machine. The cause is anything that replaces `/tmp/.X11-unix/X0` with a broken symlink — typically a stray user-systemd unit or `tmpfiles.d` drop-in that runs `ln -sf X1 /tmp/.X11-unix/X0` on every login. Steam's pressure-vessel sandbox cannot fall back to the abstract socket. Includes both the clean relog fix and a no-relog AF_UNIX proxy script.

### [temps-monitoring.md](temps-monitoring.md)

Sets up a terminal thermal dashboard showing CPU package and core temperatures, NVMe drive temps, GPU temperature, GPU power and clock speed, and both fan RPMs.

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
