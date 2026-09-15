# TULPAR T6 V2.1 hardware

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator), Clevo NL5xLU `1558:a741`
**Verified on:** Ubuntu 24.04.4 LTS · kernel 6.17.0-23-generic · 2026-08-13
**See also:** [set up a TULPAR T6 V2.1](../how-to/set-up-a-tulpar-t6-v21.md)

What is in this machine, what drives each part, and what stays broken.

## Components

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

> **Why the patched Tuxedo driver?** Monster reports DMI vendor `MONSTER` but
  the upstream `tuxedo-drivers` only allows `TUXEDO`. See [unlock the keyboard
  backlight and touchpad](../how-to/unlock-keyboard-backlight-and-touchpad.md).


## Windows-to-Linux driver mapping

This is the row-by-row equivalent for everything in the [Monster Tulpar T6 V21
driver
page](https://support.monsternotebook.com/tr/product/tulpar-t6-v21-ai-creator-bilgisayar/drivers-and-downloads/).

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
| NVIDIA GPU | `nvidia-driver-580-open` (Ubuntu) | ✅ works — see [restore NVIDIA after a kernel upgrade](../how-to/restore-nvidia-after-a-kernel-upgrade.md) |
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


## Known limitations

- **The webcam disconnects about 7 seconds into every boot.** `uvcvideo`
  detects and binds the Chicony USB UVC camera (`04f2:b7e7`), then the EC kills
  the USB device because the privacy switch defaults to off. Toggle the
  hardware shutter or `Fn`+`F10`. No driver build is needed.
- **`it87` cannot control fan PWM here.** The in-tree module does not support
  EC chip ID `0x5570`. Fan curves belong to the EC firmware and TUXEDO Control
  Center, reached through the patched `tuxedo_io` interface. RPM reading still
  works over ACPI hwmon.
- **`xe` loads alongside `i915`** on Meteor Lake, but `i915` stays the active
  KMS driver on Ubuntu 24.04 and Mesa drives both. Do not blacklist `xe` — it
  provides compute paths that oneAPI uses.
- **PRIME defaults to `on-demand`,** so Intel renders everything. Run
  `sudo prime-select nvidia` to hand rendering to the RTX 4070.
