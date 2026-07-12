# Monster Notebook Linux

Field guides for running Linux on Monster (Clevo/TONGFANG-based) notebooks —
every fix here was hit, diagnosed, and verified on real hardware. Monster
ships rebadged Clevo barebones, so most of this applies equally to TUXEDO,
XMG/Schenker, System76 and other machines built on the same shells.

**Machines behind this repo:**

- **Monster TULPAR T6 V2.1 AI Creator** — Ubuntu 26.04, kernel 7.0 (daily driver)
- **Monster ABRA A5 V20.2** — Ubuntu 22.04, kernel 6.8

---

## Setting Up a Fresh Install? Start Here

1. [monster-notebook-drivers.md](monster-notebook-drivers.md) — the Windows→Linux
   driver map for all Monster SKUs, what's always broken out of the box, and the
   recommended baseline install.
2. Your model's file: [tulpar-t6-v21.md](tulpar-t6-v21.md) — full per-SKU setup
   (hardware table, NPU, webcam, audio, color, verification checklist).
3. [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) — you will need this one;
   the keyboard backlight and touchpad are dead on every Monster until the
   `tuxedo-drivers` DMI patch is in.

## Find Your Problem

| Symptom | Guide |
|---------|-------|
| Keyboard backlight dead / touchpad locked at hardware level | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |
| `nvidia-smi` fails after a kernel upgrade | [fix-nvidia.md](fix-nvidia.md) |
| Everything renders on the Intel iGPU, dGPU idle | [fix-gpu-prime.md](fix-gpu-prime.md) |
| **Machine hard-freezes at random — no logs, only a power cycle helps** | [fix-nvme-freeze-aspm.md](fix-nvme-freeze-aspm.md) |
| Login screen comes up black/broken on some boots (hybrid graphics, Wayland) | [fix-gdm-black-greeter.md](fix-gdm-black-greeter.md) |
| Boot takes ~2 minutes, long freeze after login | [fix-slow-boot-snapd.md](fix-slow-boot-snapd.md) |
| Bluetooth peripherals crash-disconnect (Intel AX211, `Hardware error 0x0c`) | [fix-bluetooth-ax211.md](fix-bluetooth-ax211.md) |
| TUXEDO Control Center shows no fan/temperature (ABRA A5) | [fix-tuxedo-fan-temp-abra.md](fix-tuxedo-fan-temp-abra.md) |
| Want a terminal thermal dashboard (temps, fans, GPU power) | [temps-monitoring.md](temps-monitoring.md) |
| Panel color calibration vs the Windows X-Rite profile | [fix-color-calibration.md](fix-color-calibration.md) |

## Guides

### Stability

- **[fix-nvme-freeze-aspm.md](fix-nvme-freeze-aspm.md)** — random total hard
  freezes traced to the DRAM-less Phison controller in the GOODRAM PX600 root
  SSD failing to wake from PCIe ASPM L1. Includes the full diagnosis story
  (the panic that masqueraded as bad RAM), the `pcie_aspm=off` fix, the VMD
  caveat, and two bonus fixes found along the way (GRUB recordfail slow boots,
  Thunderbolt dock D3cold log spam).
- **[fix-bluetooth-ax211.md](fix-bluetooth-ax211.md)** — Intel AX211 BT
  firmware crashes (`Hardware error 0x0c`) killing keyboard/headset
  connections. Firmware build bisection (3243 stable; 3604/3831/3882 all
  crash), the `linux-firmware` hold that protects it, A2DP/PipeWire tuning for
  glitch-free audio, and the USB-dongle escape hatch.

### Graphics & Boot

- **[fix-nvidia.md](fix-nvidia.md)** — `nvidia-smi` broken after a kernel
  upgrade: the Tuxedo apt repo's epoch-pinned NVIDIA packages block Ubuntu's
  per-kernel modules. Fix with an apt pin.
- **[fix-gpu-prime.md](fix-gpu-prime.md)** — switch PRIME from `on-demand`
  (Intel renders everything) to `nvidia` mode, and back.
- **[fix-gdm-black-greeter.md](fix-gdm-black-greeter.md)** — intermittent
  black GDM login screen on hybrid Intel+NVIDIA under Wayland; fixed with
  NVIDIA early KMS in the initramfs, keeping Wayland.
- **[fix-slow-boot-snapd.md](fix-slow-boot-snapd.md)** — ~70 s of every boot
  lost to a crash-looping `snapd-desktop-integration` user service; mask it.

### Input, Fans & Sensors

- **[fix-keyboard-touchpad.md](fix-keyboard-touchpad.md)** — `tuxedo-drivers`
  rejects the `MONSTER` DMI vendor; patch the source, rebuild with DKMS, and
  install a boot service so the touchpad stays enabled. Also covers where the
  backlight controls hide in TUXEDO Control Center.
- **[fix-tuxedo-fan-temp-abra.md](fix-tuxedo-fan-temp-abra.md)** — TCC shows
  no fan/temperature on the ABRA A5 because the OEM firmware half-implements
  the Clevo WMI calls. Ships a board-specific out-of-tree hwmon driver
  ([`tuxedo-abra-fan-fix/`](tuxedo-abra-fan-fix/)) reverse-engineered from the
  DSDT and EC MMIO registers.
- **[temps-monitoring.md](temps-monitoring.md)** — terminal thermal dashboard:
  CPU package/core temps, NVMe temps, GPU temp/power/clocks, fan RPMs.

### Display Color

- **[fix-color-calibration.md](fix-color-calibration.md)** — reality check on
  the X-Rite Pantone factory calibration: the ICC lives in the panel EEPROM,
  not in any installer, and what your options actually are on Linux.
- **[windows-to-go-boot-instructions.md](windows-to-go-boot-instructions.md)** —
  (abandoned, kept for reference) the one-time Windows-To-Go procedure to read
  the factory ICC out of the panel. [xrite-resume-state.md](xrite-resume-state.md)
  records where that effort stopped and what watches for a Linux-friendly release.

### Reference

- **[tulpar-t6-v21.md](tulpar-t6-v21.md)** — complete TULPAR T6 V2.1 setup:
  hardware identification, driver map, NPU activation, webcam privacy-switch
  gotcha, audio, color, firmware updates, verification checklist.
- **[monster-notebook-drivers.md](monster-notebook-drivers.md)** — the general
  Windows→Linux driver reference for all Monster SKUs and the Tuxedo stack
  architecture.
- **[desktop-setup/](desktop-setup/)** — conky dashboards, wallpaper, and GNOME
  theme backup for restoring the desktop after a fresh install.
- **[bios-dumps/](bios-dumps/)** — UEFI Setup variable dumps (TULPAR T6) for
  reference when hunting hidden BIOS options.
- **[idea-monster-linux.md](idea-monster-linux.md)** — notes on whether a
  "monster-linux" project (à la asus-linux) makes sense, or whether upstreaming
  quirks into `tuxedo-drivers` is the smarter play.

---

## Tested Configurations

| Component | TULPAR T6 V2.1 AI Creator | ABRA A5 V20.2 |
|-----------|---------------------------|----------------|
| CPU | Intel Core Ultra 7 155H (Meteor Lake) | Intel Core i5-13500H (Raptor Lake) |
| GPU | NVIDIA RTX 4070 Laptop (Max-Q) | NVIDIA RTX 4050 Laptop |
| EC | ITE IT5570E | — |
| BIOS | 1.07.04TFB | N.1.13MON07 |
| OS | Ubuntu 26.04 LTS | Ubuntu 22.04 LTS |
| Kernel | 7.0.0-15-generic | 6.8.0-124-generic |
| NVIDIA driver | 580.142 (`-open`) | — |
| tuxedo-drivers | 4.22.2 | 4.22.2 (+ `tuxedo-abra-fan` 1.0 out-of-tree) |
| TUXEDO Control Center | 3.0.4 | 2.1.17 |

Guides state the OS/kernel they were written against in their own headers;
several were authored on Ubuntu 24.04 / kernel 6.17 and have survived the
26.04 / kernel 7.0 upgrade unchanged unless noted.
