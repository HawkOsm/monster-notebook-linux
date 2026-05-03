# Monster Notebook Linux Driver Fix

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+

Fixes everything that breaks after a kernel upgrade on Monster (Clevo-based) notebooks:
- Keyboard backlight dead / stuck off
- Touchpad locked (disabled at the hardware level)
- NVIDIA driver not communicating (`nvidia-smi` fails)
- GPU never used — all rendering on Intel iGPU ("CPU") instead of RTX 4070
- Temperature and fan sensors missing or unlabeled

---

## Why This Happens

### Keyboard Backlight

The `tuxedo-drivers` package (which controls the Clevo keyboard hardware) contains a compatibility gate that only allows itself to load on systems where the DMI vendor string is exactly `"TUXEDO"`. Monster notebooks report `"MONSTER"` — so the driver refuses to initialize and exits silently with `No such device`.

On kernel 6.17+, an additional problem appears: the kernel ships a built-in `tuxedo_io` v0.3.9 while the DKMS package provides v0.3.6, causing a module version collision.

### Touchpad Locked

The Embedded Controller (EC) on Clevo boards has a hardware-level touchpad enable/disable flag. This flag survives reboots. When the Tuxedo driver fails to load, the EC register can get stuck at `0` (disabled) with no way to toggle it back — because the `/dev/tuxedo_io` device that controls the EC never loads.

### NVIDIA Driver

Ubuntu ships pre-built NVIDIA kernel module packages keyed per kernel version. When you jump to a new kernel (e.g. `6.17.0-23`), the matching package (`linux-modules-nvidia-580-open-6.17.0-23-generic`) must be installed. If you have the Tuxedo apt repository enabled, its epoch-versioned NVIDIA packages (`2:580.126.09`) block apt from upgrading to Ubuntu's newer `580.142` build — which is what the per-kernel package depends on.

---

## The Fix

### One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/HawkOsm/monster-notebook-keyboard-driver-problem-fix/main/fix.sh | sudo bash
```

Or download and inspect first (recommended):

```bash
wget https://raw.githubusercontent.com/HawkOsm/monster-notebook-keyboard-driver-problem-fix/main/fix.sh
cat fix.sh          # read it before running anything as root
sudo bash fix.sh
```

**Reboot after the script finishes.** Everything is configured to restore automatically on every boot.

---

## What the Script Does (step by step)

| Step | Action |
|------|--------|
| 1 | Installs `tuxedo-drivers-dkms` from the Tuxedo repo if not already present |
| 2 | Patches `tuxedo_compatibility_check.c` to accept `"MONSTER"` as a valid DMI vendor |
| 3 | Forces a clean DKMS rebuild for the running kernel |
| 4 | Creates `/etc/modules-load.d/tuxedo.conf` so all required modules autoload at boot |
| 5 | Loads the modules immediately (no reboot needed to test) |
| 6 | Sets keyboard backlight to full brightness |
| 7 | Reads the EC touchpad register via `/dev/tuxedo_io` IOCTL and sets it to `1` (enabled) |
| 8 | Installs `tuxedo-touchpad-enable.service` — a systemd oneshot that re-enables the touchpad after every boot |
| 9 | Updates initramfs |

---

## NVIDIA Fix (separate step — only needed if `nvidia-smi` fails)

Run this **after** `fix.sh`:

```bash
wget https://raw.githubusercontent.com/HawkOsm/monster-notebook-keyboard-driver-problem-fix/main/fix_nvidia.sh
sudo bash fix_nvidia.sh
```

Or manually:

```bash
# 1. Pin Ubuntu's NVIDIA packages above the Tuxedo repo epoch
sudo tee /etc/apt/preferences.d/nvidia-ubuntu-pin << 'EOF'
Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-updates
Pin-Priority: 1001

Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-security
Pin-Priority: 1001
EOF

# 2. Upgrade NVIDIA to 580.142 and install kernel modules
sudo apt-get update
sudo apt-get install -y --allow-downgrades \
  nvidia-kernel-common-580=580.142-0ubuntu0.24.04.1 \
  nvidia-driver-580-open=580.142-0ubuntu0.24.04.1 \
  linux-modules-nvidia-580-open-$(uname -r)

# 3. Load the driver
sudo modprobe nvidia
nvidia-smi
```

---

## GPU PRIME Fix (all rendering on Intel instead of NVIDIA)

On Ubuntu, hybrid graphics defaults to `on-demand` PRIME mode: Intel drives the display, NVIDIA sits idle. Everything appears to run on "CPU" because the iGPU is doing all the rendering.

```bash
sudo bash fix_gpu_prime.sh
# then reboot
```

Verify after reboot:
```bash
glxinfo | grep "OpenGL renderer"
# NVIDIA GeForce RTX 4070 Laptop GPU
```

To go back to power-saving mode (Intel only, better battery life):
```bash
sudo prime-select on-demand && sudo reboot
```

---

## Temperature & Fan Monitoring

Sensors are split across multiple subsystems on this hardware. After running `fix.sh`, install the monitoring script:

```bash
sudo cp temps.py /usr/local/bin/temps && sudo chmod +x /usr/local/bin/temps
```

Then run:
```bash
temps
```

Output:
```
╔════════════════════════════════════════╗
║  Monster TULPAR T6 V2.1 - Thermals    ║
╠════════════════════════════════════════╣
║  CPU Package   : 61.0C               ║
║  CPU Max Core  : 62C                 ║
║  NVMe 0        : 28.0C               ║
║  NVMe 1        : 32.0C               ║
╠════════════════════════════════════════╣
║  GPU Temp      : 43C                 ║
║  GPU Fan (smi) : EC-controlled       ║
║  GPU Power     : 17W                 ║
║  GPU Clock     : 2370MHz             ║
╠════════════════════════════════════════╣
║  CPU Fan       : 2298 RPM            ║
║  DGPU Fan      : 2274 RPM            ║
╚════════════════════════════════════════╝
```

### What's working natively in `sensors`

| Sensor | Source | Status |
|--------|--------|--------|
| CPU package + all cores | `coretemp` | Working |
| Both NVMe drives | `nvme` hwmon | Working |
| CPU Fan RPM | ACPI hwmon (`INTC1063:00`) | Working |
| DGPU Fan RPM | ACPI hwmon (`INTC1063:01`) | Working |
| GPU temperature | `nvidia-smi` / NVIDIA hwmon | Working (NVIDIA hwmon appears after reboot in PRIME nvidia mode) |
| System ACPI temp | `acpitz` | Working |

Note: The ITE IT5570E embedded controller (chip ID `0x5570`) is not supported by the standard `it87` kernel module. Fan RPM is read via ACPI hwmon which is accurate. Fan PWM control is handled by the EC firmware and the Tuxedo Control Center.

---

## Manual Controls (after fix)

### Keyboard Backlight

```bash
# Check current brightness (0–255)
cat /sys/class/leds/rgb:kbd_backlight/brightness

# Set brightness (replace 200 with any value 0–255)
echo 200 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness

# Turn off
echo 0 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
```

Keyboard shortcuts (hold `Fn`):

| Keys | Action |
|------|--------|
| `Fn` + `/` | Toggle backlight on/off |
| `Fn` + `*` | Cycle colors |
| `Fn` + `+` | Brightness up |
| `Fn` + `-` | Brightness down |

### Touchpad

The touchpad toggle is `Fn` + `F1` (varies by model). If the touchpad locks again after a reboot the installed systemd service will re-enable it automatically. To re-enable it manually:

```bash
sudo python3 /usr/local/bin/tuxedo-touchpad-enable.py
```

---

## Troubleshooting

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': No such device`**
The compatibility patch wasn't applied or the DKMS rebuild used a cached build. Run:
```bash
sudo dkms unbuild tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms build   tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms install tuxedo-drivers/4.22.2 -k $(uname -r) --force
```

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': Operation not permitted`**
Run without `sudo` by mistake, or kernel lockdown is active. Check: `cat /sys/kernel/security/lockdown`. Should read `[none]`.

**Touchpad still locked after reboot**
Check the service ran: `systemctl status tuxedo-touchpad-enable.service`. If failed, run `sudo python3 /usr/local/bin/tuxedo-touchpad-enable.py` and inspect the output.

**NVIDIA: `couldn't communicate with the NVIDIA driver`**
The kernel module package for your exact kernel version is missing. Run `fix_nvidia.sh` (see above).

---

## Scripts in this repo

| File | Purpose |
|------|---------|
| `fix.sh` | Main fix: keyboard backlight + touchpad EC unlock |
| `fix_nvidia.sh` | NVIDIA driver upgrade for new kernels |
| `fix_gpu_prime.sh` | Switch PRIME to NVIDIA mode (GPU takes over all rendering) |
| `temps.py` | Thermal dashboard: CPU/GPU temp, both fan RPMs, NVMe |
| `tuxedo-touchpad-enable.py` | Standalone touchpad EC unlock script (used by systemd service) |

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
| Driver package | tuxedo-drivers 4.22.2 |
| NVIDIA driver | 580.142 |
