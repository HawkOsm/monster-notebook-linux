# Set up a TULPAR T6 V2.1

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator), Clevo NL5xLU `1558:a741`
**Verified on:** Ubuntu 24.04.4 LTS · kernel 6.17.0-23-generic · 2026-08-13
**Symptom:** a fresh Linux install on this machine is missing GPU, NPU and
diagnostic userspace, the webcam disappears seconds after boot, and the
keyboard backlight and touchpad do not work at all.
**See also:** [TULPAR T6 V2.1 hardware](../reference/tulpar-t6-v21-hardware.md)

Everything needed to take this SKU from a stock install to a working machine.
Work through it in order.

## Before you start

Three things are broken out of the box and have their own guides. Do these
first — the rest of this page assumes they are done.

1. [Unlock the keyboard backlight and touchpad](unlock-keyboard-backlight-and-touchpad.md).
   Required; the machine is barely usable without it.
2. [Restore NVIDIA after a kernel upgrade](restore-nvidia-after-a-kernel-upgrade.md)
   — pin Ubuntu's NVIDIA packages above the Tuxedo repository.
3. Decide how PRIME renders. Ubuntu defaults to `on-demand`, where Intel
   drives the display and the dGPU wakes per application — the right default
   on battery. Run `sudo prime-select nvidia` and reboot to hand everything to
   the RTX 4070. This is stock Ubuntu behaviour and is covered by
   [ArchWiki's PRIME page](https://wiki.archlinux.org/title/PRIME).

## Fix

### 1. Install the missing userspace

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

| Package | What it enables |
|---|---|
| `vainfo` | Verify VA-API hardware video decode/encode |
| `intel-gpu-tools` | `intel_gpu_top` — live iGPU utilization meter |
| `vulkan-tools` | `vulkaninfo`, `vkcube` — Vulkan diagnostics |
| `intel-opencl-icd` + `clinfo` | OpenCL on Intel iGPU (Blender, Darktable, etc.) |
| `intel-media-va-driver-non-free` | HEVC / VP9 / AV1 hardware decode through VA-API |
| `thermald` | Intel Dynamic Thermal Tuning equivalent — usually already installed |
| `fwupd` | Firmware updates (UEFI, NVMe, ME, TBT) via LVFS |
| `powertop` | Power-draw inspector and autotune |

Check the install landed:

```bash
vainfo                                    # see VA-API note below if this fails
vulkaninfo --summary                      # should list both Intel Arc + NVIDIA
clinfo -l                                 # should list "Intel(R) OpenCL Graphics"
intel_gpu_top                             # live iGPU dashboard
fwupdmgr refresh && fwupdmgr get-updates  # check for firmware updates
```

### 2. Point VA-API at the iGPU under NVIDIA PRIME

Skip this if you stayed on `on-demand`. With `prime-select nvidia` active the
default DRM device is the NVIDIA card, so a bare `vainfo` looks for a
`nvidia_drv_video.so` that does not exist. Force the Intel iHD backend onto
the iGPU's render node:

```bash
LIBVA_DRIVER_NAME=iHD vainfo --display drm --device /dev/dri/renderD128
```

Make it permanent for video applications by exporting both variables in
`~/.profile` or a desktop file's `Exec=` line:

```bash
export LIBVA_DRIVER_NAME=iHD
export LIBVA_DRM_DEVICE=/dev/dri/renderD128
```

### 3. Install the NPU userspace

The `intel_vpu` kernel module ships with Ubuntu 24.04 and loads by itself.
Running inference on the NPU also needs Intel's userspace driver, packaged as
`intel-npu-level-zero`.

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

Confirm the kernel sees the NPU and the device node exists:

```bash
sudo dmesg | grep -i vpu        # kernel sees the NPU
ls /dev/accel/                  # /dev/accel/accel0 exists
```

For OpenVINO inference, install `openvino` from Intel's repository or
`pip install openvino`, then target `device='NPU'`.

### 4. Turn the webcam on

**This SKU does not use Intel IPU6.** Early inspection suggested it did,
because of `INTC1062` ACPI nodes — but those are EC temperature sensors, not a
camera. The webcam is a plain USB UVC device:

```text
usb 3-7: Chicony USB2.0 Camera (04f2:b7e7) — UVC 1.50
```

`uvcvideo` binds it at boot and it then **disconnects about 7 seconds later**,
because the EC kills the USB device while the privacy switch is off. That is
hardware behaviour, not a driver problem, and no IPU6 build is needed here.

| Toggle | Where |
|---|---|
| Hardware shutter slider | Top bezel above the screen |
| `Fn` + `F10` | Common Clevo webcam-kill keybind — try this first |
| BIOS setting | Aptio Setup → Advanced → I/O Configuration → "Camera" / "Webcam" |

Then confirm it stays:

```bash
lsusb | grep -i chicony           # should show 04f2:b7e7
ls /dev/video*                    # /dev/video0, /dev/video1 should appear
v4l2-ctl --list-devices           # detailed camera info
cheese                            # GUI test (sudo apt install cheese)
```

### 5. Replace Sound Blaster with EasyEffects

Windows ships Creative Sound Blaster Connect. The PipeWire equivalent is
EasyEffects.

```bash
sudo apt-get install -y easyeffects
```

Community presets that work well on Clevo NL5x are at
<https://github.com/Digitalone1/EasyEffects-Presets>.

The microphone array runs through SOF DSP. Ubuntu 24.04's default UCM2 profile
handles it — check **pavucontrol → Input devices** to confirm the array shows
up.

### 6. Install color tooling

Only needed for color-critical work. See
[X-Rite panel calibration on Linux](../explanation/x-rite-panel-calibration-on-linux.md)
for what is actually achievable on this panel before spending time here.

```bash
sudo apt-get install -y colord gnome-color-manager argyll
```

```bash
flatpak install flathub net.displaycal.DisplayCAL
```

### 7. Update firmware through LVFS

```bash
fwupdmgr refresh
fwupdmgr get-updates
fwupdmgr update
```

This SKU publishes the NVIDIA dGPU vBIOS, Intel ME, Intel iGPU and NVMe SSD
firmware through LVFS. Monster does not currently push UEFI updates that way.

## Verify

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

## Roll back

Remove the extra repositories and the packages installed above:

```bash
sudo rm -f /etc/apt/sources.list.d/intel-gpu.list /usr/share/keyrings/intel-graphics.gpg
sudo apt-get update
sudo apt-get remove -y intel-level-zero-gpu level-zero intel-npu-level-zero easyeffects
```

The in-tree drivers and the firmware updates are not reversible from here, and
should not need to be.

## Troubleshooting

**`vainfo` fails while PRIME is in `nvidia` mode**

Expected. Use the explicit device form from step 2.

**The NPU package name is not found**

It has shifted between releases. Search for the current one:

```bash
apt-cache search npu | grep -i intel
```

Then pick the matching package — `intel-driver-compiler-npu`, `intel-fw-npu`
or `level-zero-npu`.

**`lsusb` shows the camera but `/dev/video*` is missing**

```bash
sudo modprobe uvcvideo
dmesg | tail
```

If the camera disappears again after a few seconds, the EC kill is still
active: the switch is in software-off rather than hardware-off.
