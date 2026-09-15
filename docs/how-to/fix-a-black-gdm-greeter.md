# Fix a black GDM greeter

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (hybrid Intel Arc + RTX 4070)
**Verified on:** Ubuntu 26.04 · Wayland · nvidia-driver-580-open · 2026-08-13
**Symptom:** on some reboots the GDM greeter comes up black or broken. The
wallpaper may render but the password box never appears. Most boots are fine,
which is exactly what makes it a race.

The greeter is a Wayland session that needs NVIDIA KMS. Setting `nvidia_drm
modeset=1` (and `fbdev=1`) is necessary but not sufficient: while the modules
load from the root filesystem rather than the initramfs, a fast boot can start
the greeter before the display mode exists. Putting the modules in the
initramfs closes the window.

## Before you start

If you are staring at a black greeter right now, switch to another virtual
terminal and back. That forces a modeset and gets you a usable login:

```text
Ctrl+Alt+F3, then Ctrl+Alt+F1 (or F2)
```

## Confirm the diagnosis

The modules are absent from the initramfs — this returns nothing on an
affected system:

```bash
lsinitramfs /boot/initrd.img-$(uname -r) | grep -E "nvidia(-drm|-modeset)?\.ko"
```

## Fix

### 1. Add the NVIDIA modules to the initramfs

```bash
sudo cp /etc/initramfs-tools/modules /etc/initramfs-tools/modules.bak
printf '%s\n' nvidia nvidia_modeset nvidia_drm | sudo tee -a /etc/initramfs-tools/modules
sudo update-initramfs -u
```

Reboot.

## Verify

The same command from the diagnosis step now lists the modules:

```bash
lsinitramfs /boot/initrd.img-$(uname -r) | grep -E "nvidia(-drm|-modeset)?\.ko"
```

KMS is then ready before the greeter starts, on every boot.

## Roll back

```bash
sudo mv /etc/initramfs-tools/modules.bak /etc/initramfs-tools/modules
sudo update-initramfs -u
```

## Trade-offs

The initramfs grows substantially — from roughly 70 MB to 161 MB here — and
GRUB takes correspondingly longer to load it. That is the cost of a login
screen that works every time.

Do not reach for the obvious alternative. Setting `WaylandEnable=false` in
`/etc/gdm3/custom.conf` does make the symptom go away, but only by moving the
entire desktop to Xorg. Early KMS fixes the actual race and keeps Wayland.
