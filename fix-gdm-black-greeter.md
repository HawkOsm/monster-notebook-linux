# Fix: Black / Broken GDM Login Screen (Hybrid Intel + NVIDIA, Wayland)

**Symptom:** on some reboots the GDM greeter comes up black or broken — the
wallpaper may render but the password box never appears. Intermittent: most
boots are fine, which is exactly what makes it a race.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 26.04 · GNOME/GDM on Wayland ·
`nvidia-driver-580-open` · hybrid Intel Arc (i915) + RTX 4070

---

## Why This Happens

On this hybrid setup the GDM greeter runs as a Wayland session that needs
NVIDIA KMS. `nvidia_drm modeset=1` (and `fbdev=1`) being set is necessary but
not sufficient: if the nvidia modules are **not in the initramfs**, KMS only
becomes available when the modules load from the root filesystem — and on a
fast boot the greeter can start *before* the display mode is ready. Classic
late-KMS race: lose it and you stare at a black screen.

## Recover a Live Black Greeter (no reboot)

Switch VTs and back — this forces a modeset:

```
Ctrl+Alt+F3, then Ctrl+Alt+F1 (or F2)
```

## The Fix — NVIDIA Early KMS

Load the nvidia modules from the initramfs so KMS is up before the greeter
ever starts:

```bash
sudo cp /etc/initramfs-tools/modules /etc/initramfs-tools/modules.bak
printf '%s\n' nvidia nvidia_modeset nvidia_drm | sudo tee -a /etc/initramfs-tools/modules
sudo update-initramfs -u
```

Verify the modules made it in:

```bash
lsinitramfs /boot/initrd.img-$(uname -r) | grep -E "nvidia(-drm|-modeset)?\.ko"
```

Reboot. The greeter now has a ready display mode on every boot.

## Trade-offs / Notes

- **The initramfs gets big** (161 MB here, from ~70 MB) — GRUB takes a bit
  longer to load it. Worth it for a login screen that always works.
- The tempting alternative — `WaylandEnable=false` in
  `/etc/gdm3/custom.conf` — "fixes" it by pushing the whole desktop to Xorg.
  Don't, unless you want Xorg anyway; early KMS solves the actual race and
  keeps Wayland.
- Rollback: restore the `.bak` over `/etc/initramfs-tools/modules` and run
  `sudo update-initramfs -u` again.
