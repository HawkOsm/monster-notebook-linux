# Monster TULPAR T6 V2.1 (AI Creator) — Linux Setup

A complete driver / firmware / userspace setup guide for the **Monster TULPAR T6 V2.1 AI Creator** notebook on Linux.

**Tested on:** Ubuntu 24.04.4 LTS · Kernel 6.17.0-23-generic

---

## Hardware Identified

| Component | Detected as | Linux driver |
|-----------|-------------|--------------|
| Chassis | Clevo NL5xLU / `1558:a741` | n/a |
| CPU | Intel Core Ultra 7 155H (Meteor Lake) | `intel_pstate`, `intel_idle` |
| iGPU | Intel Arc Graphics (MTL-P) `8086:7d55` | `i915` (also `xe`) |
| dGPU | NVIDIA RTX 4070 Max-Q `10de:2820` | `nvidia` (proprietary) |
| NPU | Intel Meteor Lake VPU `8086:7d1d` | `intel_vpu` |
| Wi-Fi | Intel Wi-Fi 6E AX211 | `iwlwifi` |
| Bluetooth | Intel AX211 BT | `btusb` + `btintel` |
| Audio codec | Realtek ALC269 (HD-Audio over SOF) | `snd_sof_pci_intel_mtl` |
| LAN | Realtek RTL8168 1 GbE | `r8169` |
| SD card reader | O2 Micro `1217:8621` | `sdhci-pci` |
| NVMe slot 1 | Micron 2550 (DRAM-less) | `nvme` |
| NVMe slot 2 | Phison PS5021-E21 (DRAM-less) | `nvme` |
| Embedded controller | ITE IT5570E | `tuxedo-drivers` (patched) |
| Webcam | Chicony / SunplusIT USB2.0 UVC `04f2:b7e7` | `uvcvideo` (in-tree) — but the camera disconnects ~7s after boot; toggle the privacy switch (see below) |
| Thunderbolt 4 | Intel MTL-P NHI | `thunderbolt` |
| Fingerprint reader | not present on this SKU | n/a |

> **Why the patched Tuxedo driver?** Monster reports DMI vendor `MONSTER` but the upstream `tuxedo-drivers` only allows `TUXEDO`. See [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md).

---

## Driver Mapping — Windows → Linux

This is the row-by-row equivalent for everything in the [Monster Tulpar T6 V21 driver page](https://support.monsternotebook.com/tr/product/tulpar-t6-v21-ai-creator-bilgisayar/drivers-and-downloads/).

| Windows driver | Linux equivalent | Status on stock Ubuntu 24.04 |
|---|---|---|
| Chipset Driver (Intel) | in-tree (`pci`, `intel-lpss`, `i801_smbus`, `mei_me`) | ✅ works |
| Speed Shift (Intel) | `intel_pstate` (in-tree) | ✅ works |
| Serial IO (Intel) | `intel-lpss-pci` (in-tree) | ✅ works |
| HID Driver (Intel) | `i2c_hid`, `hid_generic` (in-tree) | ✅ works |
| TXT Driver (Intel) | `intel_txt` (in-tree) | ✅ works |
| PMT Driver (Intel) | `intel_vsec`, `pmt_telemetry` (in-tree) | ✅ works |
| DTT — Dynamic Tuning (Intel) | `processor_thermal_device_pci` + `thermald` | ✅ works (install `thermald`) |
| Management Engine (Intel) | `mei`, `mei_me` (in-tree) + `fwupd` for ME firmware | ✅ works |
| GNA (Intel) | (n/a — superseded by NPU on Meteor Lake) | n/a |
| NPU (Intel) | `intel_vpu` kernel module + Intel NPU userspace driver | ⚠️ kernel ✅, userspace = manual install (see § NPU) |
| Intel GPU | `i915` / `xe` + `intel-media-va-driver-non-free` + `intel-opencl-icd` | ✅ works (install user-space tools) |
| NVIDIA GPU | `nvidia-driver-580-open` (Ubuntu) | ✅ works — see [fix-nvidia.md](fix-nvidia.md) |
| Wi-Fi (Intel) | `iwlwifi` + `linux-firmware` | ✅ works |
| Bluetooth (Intel) | `btusb` + `btintel` + `linux-firmware` | ✅ works |
| Audio (Realtek over SOF) | `snd_sof_pci_intel_mtl` + `firmware-sof-signed` | ✅ works |
| Sound Blaster | EasyEffects + community presets | optional (see § Audio) |
| LAN (Realtek RTL8168) | `r8169` (in-tree) | ✅ works |
| Card Reader (O2 Micro) | `sdhci-pci` (in-tree) | ✅ works |
| RAID / IRST (Intel VMD) | `vmd` module — but the BIOS on this unit ships with VMD off | ✅ works (no action) |
| Webcam (USB UVC — Chicony `04f2:b7e7`) | `uvcvideo` (in-tree) | ⚠️ driver works; webcam-kill switch off by default — toggle hardware shutter or `Fn`+`F10` (see § Webcam) |
| X-rite Color Assistant | `colord` + DisplayCAL | optional (see § Color) |
| Control Center (Monster) | `tuxedo-control-center` | ✅ works |

---

## Required Setup (start here)

These guides cover the things that are broken out-of-the-box and **must** be done for the laptop to be usable:

1. **[fix-keyboard-touchpad.md](fix-keyboard-touchpad.md)** — keyboard backlight + hardware-locked touchpad. Required.
2. **[fix-nvidia.md](fix-nvidia.md)** — pin Ubuntu's NVIDIA packages above the Tuxedo repo.
3. **[fix-gpu-prime.md](fix-gpu-prime.md)** — switch PRIME to NVIDIA mode (or leave on `on-demand` for battery life).

---

## Recommended Userspace Install

Install the GPU/AI/diagnostic userspace that is missing on a stock Ubuntu install:

```bash
sudo apt-get install -y \
    vainfo \
    intel-gpu-tools \
    vulkan-tools \
    intel-opencl-icd \
    clinfo \
    intel-media-va-driver-non-free \
    thermald \
    fwupd \
    powertop
```

**What each gives you:**

| Package | What it enables |
|---|---|
| `vainfo` | Verify VA-API hardware video decode/encode |
| `intel-gpu-tools` | `intel_gpu_top` — live iGPU utilization meter |
| `vulkan-tools` | `vulkaninfo`, `vkcube` — Vulkan diagnostics |
| `intel-opencl-icd` + `clinfo` | OpenCL on Intel iGPU (Blender, Darktable, etc.) |
| `intel-media-va-driver-non-free` | HEVC / VP9 / AV1 hardware decode through VA-API |
| `thermald` | Intel Dynamic Thermal Tuning equivalent — already installed by default but worth verifying |
| `fwupd` | Firmware updates (UEFI, NVMe, ME, TBT) via LVFS |
| `powertop` | Power-draw inspector / autotune |

Verify after install:

```bash
vainfo                                    # see VA-API note below if this fails
vulkaninfo --summary                      # should list both Intel Arc + NVIDIA
clinfo -l                                 # should list "Intel(R) OpenCL Graphics"
intel_gpu_top                             # live iGPU dashboard
fwupdmgr refresh && fwupdmgr get-updates  # check for firmware updates
```

### VA-API in NVIDIA PRIME mode

When `prime-select nvidia` is active, the default DRM device is the NVIDIA card and a bare `vainfo` will try the (missing) `nvidia_drv_video.so`. Force the Intel iHD backend on the iGPU's render node:

```bash
LIBVA_DRIVER_NAME=iHD vainfo --display drm --device /dev/dri/renderD128
```

To make this permanent for video apps (Firefox, MPV, etc.), export both env vars in `~/.profile` or a desktop-file `Exec=` line:

```bash
export LIBVA_DRIVER_NAME=iHD
export LIBVA_DRM_DEVICE=/dev/dri/renderD128
```

---

## NPU (Intel AI Boost) — Userspace Install

The kernel module `intel_vpu` is in Ubuntu 24.04 and loads automatically. To actually run inference on the NPU you also need the userspace driver from Intel.

```bash
# Add Intel's package repository for level-zero / NPU
ARCH=$(dpkg --print-architecture)
curl -s https://repositories.intel.com/gpu/intel-graphics.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/intel-graphics.gpg
echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu noble unified" \
  | sudo tee /etc/apt/sources.list.d/intel-gpu.list

sudo apt-get update
sudo apt-get install -y intel-level-zero-gpu level-zero intel-npu-level-zero
```

> The `intel-npu-level-zero` package name has shifted between releases. If the install fails, search `apt-cache search npu | grep -i intel` and pick the matching package (`intel-driver-compiler-npu`, `intel-fw-npu`, `level-zero-npu`).

Verify:

```bash
sudo dmesg | grep -i vpu        # kernel sees the NPU
ls /dev/accel/                  # /dev/accel/accel0 exists
```

For OpenVINO inference, install `openvino` from Intel's repo or `pip install openvino` and target `device='NPU'`.

---

## Webcam — USB UVC, Killed by Privacy Switch

**Important: the Tulpar T6 V2.1 AI Creator does NOT use Intel IPU6.** Initial inspection suggested IPU6 (because of `INTC1062` ACPI nodes), but those are EC temperature sensors. The webcam is actually a standard USB UVC device:

```
usb 3-7: Chicony USB2.0 Camera (04f2:b7e7) — UVC 1.50
```

The driver (`uvcvideo`) is already in-tree and loads at boot. **The camera then disconnects ~7 seconds later** because the firmware/EC kills the USB device when the privacy switch is in the off position. This is hardware, not software.

To bring the camera back:

| Toggle | Where |
|---|---|
| Hardware shutter slider | Top bezel above the screen (Clevo NL5x usually has one) |
| `Fn` + `F10` | Common Clevo webcam-kill keybind — try this first |
| BIOS setting | Aptio Setup → Advanced → I/O Configuration → "Camera" / "Webcam" |

After toggling on:

```bash
lsusb | grep -i chicony           # should show 04f2:b7e7
ls /dev/video*                    # /dev/video0, /dev/video1 should appear
v4l2-ctl --list-devices           # detailed camera info
cheese                            # GUI test (sudo apt install cheese)
```

If `lsusb` shows the camera but `/dev/video*` is missing, run `sudo modprobe uvcvideo` and check `dmesg`. If the camera disappears again seconds later, the EC kill is still active — the switch is in software-off, not hardware-off.

> No IPU6 driver build is needed. The MIPI / IPU6 path discussed in [monster-notebook-drivers.md](monster-notebook-drivers.md) applies to other Monster SKUs that ship with Intel MIPI cameras, not this one.

---

## Audio — Sound Blaster Replacement

Windows ships Creative Sound Blaster Connect for tuning. The Linux equivalent is **EasyEffects** (PipeWire-based).

```bash
sudo apt-get install -y easyeffects
```

Community presets that work well on Clevo NL5x: <https://github.com/Digitalone1/EasyEffects-Presets>.

Microphone input on the AI Creator runs through SOF (Sound Open Firmware) DSP and exposes a digital mic array. The default UCM2 profile in Ubuntu 24.04 handles it. Check `pavucontrol` → Input devices to confirm the array is visible.

---

## Color Management — X-rite Equivalent

If you do color-critical work:

```bash
sudo apt-get install -y colord gnome-color-manager argyll
```

For ICC profile creation with a colorimeter, install **DisplayCAL** from Flatpak:

```bash
flatpak install flathub net.displaycal.DisplayCAL
```

If you have an existing `.icc` profile from Windows, copy it to `~/.local/share/icc/` and assign it via Settings → Color.

---

## Firmware Updates (LVFS)

The notebook is supported by LVFS. Run periodically:

```bash
fwupdmgr refresh
fwupdmgr get-updates
fwupdmgr update
```

Available firmware on this SKU: NVIDIA dGPU vBIOS, Intel ME, Intel iGPU, NVMe SSDs, UEFI (where the OEM publishes — Monster currently does not push UEFI updates through LVFS, but Intel ME and the SSDs do).

---

## Verification Checklist

After running the steps above:

```bash
# Hardware
nvidia-smi                                        # NVIDIA RTX 4070 visible
glxinfo | grep "OpenGL renderer"                  # NVIDIA in nvidia mode, Intel in on-demand
vainfo | head -20                                 # VA-API entrypoints listed
vulkaninfo --summary                              # Both GPUs present
clinfo -l                                         # Intel + NVIDIA OpenCL platforms
ls /dev/accel/accel0                              # NPU character device (after userspace install)
ls /dev/video0                                    # Camera (after IPU6 install)

# Tuxedo / Monster
cat /sys/class/leds/rgb:kbd_backlight/brightness  # keyboard backlight responds
systemctl is-active tuxedo-touchpad-enable        # touchpad re-enable service active
lsmod | grep tuxedo                               # tuxedo modules loaded

# Power / thermal
sensors | grep -E 'Package|Fan'                   # CPU pkg + fan RPM
temps                                             # Full thermal dashboard (see temps-monitoring.md)
systemctl is-active thermald                      # active

# Connectivity
nmcli device status                               # wifi + ethernet listed
bluetoothctl show                                 # adapter present
boltctl                                           # Thunderbolt OK
```

---

## Known Limitations

- **Webcam disconnects at boot.** The Chicony USB UVC camera (`04f2:b7e7`) is detected and bound to `uvcvideo`, then disconnected ~7 s later by the EC because the privacy switch defaults to off. Toggle the hardware shutter or `Fn`+`F10`. No driver build needed — see § Webcam.
- **Fan PWM control via `it87` is not available** — the EC chip ID `0x5570` is not supported by the in-tree `it87` module. Fan curves are managed by the EC firmware and TUXEDO Control Center via the patched `tuxedo_io` interface. RPM reading still works through ACPI hwmon.
- **`xe` is loaded alongside `i915`** for Meteor Lake but `i915` remains the active KMS driver in Ubuntu 24.04. Mesa drives both. Do not blacklist `xe`; it provides compute paths used by oneAPI.
- **NVIDIA `prime-select on-demand` is the default.** All rendering goes through Intel by default. To make the RTX 4070 drive everything, switch with `sudo prime-select nvidia`.
