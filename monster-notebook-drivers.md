# Monster Notebook — Linux Driver Reference (General)

A vendor-to-Linux driver mapping that applies across Monster Notebook SKUs (Tulpar, Abra, Huma, Semruk lines).

Monster ships rebadged **Clevo / TONGFANG** barebones (chassis IDs `1558:xxxx`). Driver behavior is therefore the same as on Clevo / TUXEDO / XMG / Schenker / System76 Oryx-class machines built on the same shells.

---

## Why This Reference Exists

Monster's official download page lists Windows drivers per SKU. Linux drivers don't map 1-to-1: most are in-tree kernel modules; some are user-space packages; a handful (Intel IPU6 camera, some EC features) need vendor PPAs or out-of-tree DKMS.

This page is the **lookup table**: pick a row from your laptop's Monster driver list, get the Linux equivalent.

For a per-SKU walkthrough, see the model files (e.g. [tulpar-t6-v21.md](tulpar-t6-v21.md)).

---

## Universal Driver Map

| Windows driver (Monster) | Vendor | Linux equivalent | Install |
|---|---|---|---|
| Chipset Driver | Intel | in-tree (`pci`, `intel-lpss`, `i801_smbus`, `mei_me`) | none — kernel ≥ 6.0 |
| Speed Shift / HWP | Intel | `intel_pstate` (in-tree) | none |
| Serial IO | Intel | `intel-lpss-pci` (in-tree) | none |
| HID Driver | Intel | `i2c_hid`, `hid_generic` (in-tree) | none |
| TXT Driver | Intel | `intel_txt` (in-tree) | none |
| PMT Driver | Intel | `intel_vsec`, `pmt_telemetry` (in-tree) | none |
| Management Engine (ME) | Intel | `mei`, `mei_me` (in-tree); firmware via `fwupd` / LVFS | `sudo apt install fwupd` |
| Dynamic Tuning (DTT) | Intel | `processor_thermal_device_pci` + `thermald` daemon | `sudo apt install thermald` |
| GNA Driver | Intel | (deprecated; replaced by NPU on Meteor Lake+) | n/a |
| NPU Driver | Intel | `intel_vpu` kernel module (≥ kernel 6.7) + Intel NPU level-zero userspace | manual — see [tulpar-t6-v21.md § NPU](tulpar-t6-v21.md#npu-intel-ai-boost--userspace-install) |
| Intel GPU Driver | Intel | `i915` (≤ Raptor Lake) / `xe` (≥ Battlemage) + `intel-media-va-driver` + `intel-opencl-icd` + `mesa-vulkan-drivers` | `sudo apt install intel-media-va-driver-non-free intel-opencl-icd mesa-vulkan-drivers vulkan-tools intel-gpu-tools vainfo` |
| NVIDIA GPU Driver | NVIDIA | `nvidia-driver-XXX-open` (Ubuntu) | `ubuntu-drivers autoinstall` — but on Monster, see [fix-nvidia.md](fix-nvidia.md) for the Tuxedo apt pin issue |
| Wi-Fi Driver — Intel AX2xx / BE2xx | Intel | `iwlwifi` (in-tree) + `linux-firmware` | none |
| Wi-Fi Driver — Realtek RTL8852/8922 | Realtek | `rtw89` (in-tree, kernel ≥ 6.0) | none |
| Wi-Fi Driver — MediaTek MT7922 | MediaTek | `mt7921e` (in-tree) | none |
| Bluetooth — Intel | Intel | `btusb` + `btintel` + `linux-firmware` | none |
| Bluetooth — Realtek | Realtek | `btusb` + `btrtl` + `linux-firmware` | none |
| Audio — Realtek codec via SOF | Realtek + Intel | `snd_sof_pci_intel_*` + `firmware-sof-signed` | none on modern Ubuntu |
| Sound Blaster (Creative) | Creative | EasyEffects (PipeWire) | `sudo apt install easyeffects` |
| LAN — Realtek RTL8111/8168 (1 GbE) | Realtek | `r8169` (in-tree) | none |
| LAN — Realtek RTL8125 (2.5 GbE) | Realtek | `r8169` (in-tree, kernel ≥ 6.0). For older kernels: `r8125-dkms` from PPA | usually none |
| Card Reader — Realtek RTS525A / RTS5260 | Realtek | `rtsx_pci` (in-tree) | none |
| Card Reader — O2 Micro | O2 Micro | `sdhci-pci` (in-tree) | none |
| RAID / Intel VMD (IRST) | Intel | `vmd` module (in-tree) | usually disable in BIOS unless you set up VMD intentionally |
| Webcam — USB UVC (most Monster SKUs, e.g. Chicony `04f2:b7e7`) | various | `uvcvideo` (in-tree) | none — but check the privacy switch / `Fn`+`F10` if `/dev/video*` is missing |
| Webcam — Intel IPU6 + IVSC + MIPI sensor (some recent Meteor Lake / Lunar Lake SKUs) | Intel | in-tree on kernel ≥ 6.10 (`intel-ipu6-isys`, `ivsc-csi`); userspace via `libcamera` + `ipu6-camera-bins` + `ipu6-camera-hal` | check first: `lsusb` for a Chicony/SunplusIT/Realtek UVC device. If missing and ACPI shows `INTC1094` or `INTC10A1`, then it really is IPU6; install `linux-oem-24.04` for the supported path |
| X-rite Color Assistant | X-rite | `colord` + DisplayCAL | `sudo apt install colord gnome-color-manager argyll` + `flatpak install net.displaycal.DisplayCAL` |
| Fingerprint reader (Goodix / Synaptics / ELAN) | various | `libfprint` + `fprintd` | `sudo apt install fprintd libpam-fprintd` (some ELAN models need the `tod` proprietary driver) |
| Control Center (Monster) | Monster (rebadged TUXEDO TCC) | `tuxedo-control-center` + `tuxedo-drivers-dkms` (patched for `MONSTER` DMI) | see [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |

---

## What Is Always Broken Out-of-the-Box

These are the items that need manual fixes on every Monster SKU because of the `MONSTER` DMI vendor or because Ubuntu's default kernel is missing the userspace.

| Issue | Cause | Fix |
|---|---|---|
| Keyboard backlight dead | `tuxedo-drivers` rejects `DMI_VENDOR != "TUXEDO"` | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |
| Touchpad locked at hardware level | EC flag stuck `0` because `tuxedo_io` never loaded | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) |
| Fan curves not configurable | EC PWM behind Tuxedo modules | [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md) (modules) + Tuxedo Control Center |
| `nvidia-smi` fails after kernel upgrade | Tuxedo apt repo blocks Ubuntu's epoch-versioned NVIDIA pkg | [fix-nvidia.md](fix-nvidia.md) |
| Webcam absent (`/dev/video*` missing) | First suspect: privacy switch / `Fn`+`F10` killed the USB UVC. Confirm with `lsusb` — if you see e.g. Chicony `04f2:b7e7` then it is UVC and a hardware toggle. Only if the camera is genuinely MIPI/IPU6 (no UVC USB ID, ACPI `INTC1094`/`INTC10A1` present) do you need the IPU6 path. | [tulpar-t6-v21.md § Webcam](tulpar-t6-v21.md#webcam--usb-uvc-killed-by-privacy-switch) |
| GPU PRIME defaults to Intel-only | Ubuntu default is `on-demand` | [fix-gpu-prime.md](fix-gpu-prime.md) — `sudo prime-select nvidia` |

---

## Stack Layers Worth Knowing

```
┌──────────────────────────────────────────┐
│  GUI: tuxedo-control-center (Electron)   │  Settings UI
├──────────────────────────────────────────┤
│  daemon: tccd (DBus)                     │  Profile management
├──────────────────────────────────────────┤
│  CLI:  tuxedo-cc-wmi-cli                 │  Direct WMI access
├──────────────────────────────────────────┤
│  kernel modules (tuxedo-drivers-dkms)    │
│    ├─ tuxedo_compatibility_check         │  DMI gate (PATCHED for MONSTER)
│    ├─ tuxedo_keyboard                    │  RGB / fn keys
│    ├─ tuxedo_io                          │  EC ioctl interface (touchpad, fans)
│    ├─ clevo_acpi  /  clevo_wmi           │  Vendor ACPI/WMI methods
│    └─ ite_829x                           │  ITE per-key RGB
├──────────────────────────────────────────┤
│  hardware: Clevo barebones + ITE EC      │
└──────────────────────────────────────────┘
```

The two layers that always need your attention on Monster are **the DMI gate** (patched at the kernel-module source level) and **the apt repo conflict** (resolved with the `nvidia-ubuntu-pin` preferences file). Everything else is upstream-clean.

---

## Recommended Baseline Install

Run on every Monster Notebook fresh install:

```bash
# Tooling
sudo apt-get install -y \
    fwupd thermald powertop \
    intel-media-va-driver-non-free intel-opencl-icd clinfo \
    vainfo intel-gpu-tools vulkan-tools mesa-vulkan-drivers mesa-utils \
    pavucontrol easyeffects

# Tuxedo stack (with the MONSTER DMI patch from fix-keyboard-touchpad.md)
sudo apt-get install -y tuxedo-drivers-dkms tuxedo-control-center
```

Then follow the per-SKU model file for the remaining SKU-specific work (camera, NPU, color profile, etc.).

---

## Per-SKU Model Files

| Model | Guide |
|---|---|
| Tulpar T6 V2.1 (AI Creator, Meteor Lake) | [tulpar-t6-v21.md](tulpar-t6-v21.md) |

Add new SKUs by following the structure of the Tulpar T6 V21 file: hardware table → Windows-to-Linux row mapping → required setup → recommended userspace → SKU-specific gotchas.
