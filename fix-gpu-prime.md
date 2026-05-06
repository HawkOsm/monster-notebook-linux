# Fix: GPU PRIME — All Rendering on Intel Instead of NVIDIA

**Symptom:** `glxinfo | grep "OpenGL renderer"` shows the Intel iGPU or reports "llvmpipe (CPU)". The RTX 4070 appears idle.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+

---

## Why This Happens

On Ubuntu, hybrid graphics defaults to `on-demand` PRIME mode. In this mode, Intel drives the display and all rendering by default. The NVIDIA GPU is only activated per-application (e.g. by prefixing a command with `__NV_PRIME_RENDER_OFFLOAD=1`). This is by design for power saving — but if you want the RTX 4070 to drive all rendering, you need to switch to NVIDIA PRIME mode.

---

## Step 1 — Check Current PRIME Profile

```bash
prime-select query
```

If the output is `nvidia`, you are already in NVIDIA mode and a reboot may be all that is needed.

## Step 2 — Enable nvidia_drm Modeset (Required for Wayland)

Check if it is already set:

```bash
grep -r "modeset" /etc/modprobe.d/
```

If nothing is returned, create the config:

```bash
echo "options nvidia_drm modeset=1" \
  | sudo tee /etc/modprobe.d/nvidia-graphics-drivers-kms.conf
```

## Step 3 — Switch PRIME to NVIDIA Mode

```bash
sudo prime-select nvidia
```

## Step 4 — Reboot

```bash
sudo reboot
```

---

## Verify After Reboot

```bash
glxinfo | grep "OpenGL renderer"
# Expected: NVIDIA GeForce RTX 4070 Laptop GPU
```

---

## Switching Back to Power-Saving Mode

If you want to return to Intel-only rendering for better battery life:

```bash
sudo prime-select on-demand
sudo reboot
```

---

## Troubleshooting

**`prime-select` not found**

Install the NVIDIA prime utilities:

```bash
sudo apt-get install nvidia-prime
```

**Blank screen or display issues after reboot**

Boot into recovery mode, open a root shell, and switch back:

```bash
prime-select on-demand
reboot
```

**`glxinfo` not available**

```bash
sudo apt-get install mesa-utils
```
