# Idle the dGPU on battery under Hyprland

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (Arch Linux · Hyprland 0.56 ·
nvidia-open-dkms · `uwsm`-managed session)
**Verified on:** Arch Linux · kernel 7.2 · 2026-09-15
**Symptom:** the RTX 4070 draws ~9 W at an idle desktop. `nvidia-smi` lists
`Hyprland` itself as an active GPU process at all times, and the dGPU never
runtime-suspends whatever the battery or idle state.
**See also:** [why Hyprland picks the dGPU as primary renderer](../explanation/hyprland-picks-the-dgpu-as-primary-renderer.md)

Make the iGPU the primary renderer, but only when you are undocked and on
battery. Doing it unconditionally breaks external monitors wired to the dGPU —
read the explanation before deciding this is what you want.

Measured result on this machine: ~9 W at P0 as primary renderer, ~4.3 W at P8
once demoted to secondary and idle.

## Before you start

Find your two GPUs' PCI addresses. Everything below assumes the iGPU at
`0000:00:02.0` and the dGPU at `0000:01:00.0`; substitute your own.

```bash
lspci -d ::03xx
```

## Fix

### 1. Give each GPU a stable symlink

`AQ_DRM_DEVICES` separates device paths with `:`, and PCI addresses contain
colons, so `/dev/dri/by-path/...` values mis-parse silently. `cardN` numbers
can renumber across boots. Colon-free symlinks avoid both traps.

Create `/etc/udev/rules.d/90-gpu-symlinks.rules`:

```text
KERNEL=="card*", KERNELS=="0000:00:02.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/igpu"
KERNEL=="card*", KERNELS=="0000:01:00.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/dgpu"
```

```bash
sudo udevadm control --reload && sudo udevadm trigger
readlink -f /dev/dri/igpu /dev/dri/dgpu
```

### 2. Export the device order conditionally at login

The export must happen before Hyprland's own process starts, so it goes in the
`uwsm` environment directory — not in `hyprland.conf`'s `env =`, which only
reaches applications Hyprland launches.

Create `~/.config/uwsm/env-hyprland.d/10-gpu-power.sh`:

```bash
_gpu_power_ac_online() {
    for ac in /sys/class/power_supply/AC*/online /sys/class/power_supply/ADP*/online; do
        [ -f "$ac" ] || continue
        [ "$(cat "$ac" 2>/dev/null)" = "1" ] && return 0
    done
    return 1
}

_gpu_power_dgpu_has_monitor() {
    dgpu_card="$(basename "$(readlink -f /dev/dri/dgpu)")"
    for status in /sys/class/drm/"$dgpu_card"-*/status; do
        [ -f "$status" ] || continue
        [ "$(cat "$status" 2>/dev/null)" = "connected" ] && return 0
    done
    return 1
}

if [ -e /dev/dri/igpu ] && [ -e /dev/dri/dgpu ] && ! _gpu_power_ac_online && ! _gpu_power_dgpu_has_monitor; then
    export AQ_DRM_DEVICES="/dev/dri/igpu:/dev/dri/dgpu"
    export AQ_FORCE_LINEAR_BLIT=0   # Hyprland's own recommended mitigation for Nvidia multi-GPU buffers
    echo "igpu" > /tmp/serpantinum_gpu_mode
else
    echo "default" > /tmp/serpantinum_gpu_mode
fi

unset -f _gpu_power_ac_online _gpu_power_dgpu_has_monitor
```

Two things this does deliberately:

- The connector scan globs every `/sys/class/drm/<dgpu-card>-*/status` file, so
  HDMI, DisplayPort and USB-C DP-Alt-Mode are all covered whichever port the
  cable is in.
- The dGPU stays *listed* in `AQ_DRM_DEVICES`, just second. Omitting it
  entirely would guarantee a dead external monitor if you dock mid-session.

The file also writes `/tmp/serpantinum_gpu_mode`. Use that marker, not the
compositor's environment, to tell which mode is active — see Troubleshooting.

Log out and back in to apply.

### 3. Notify on live docking, never auto-restart

`AQ_DRM_DEVICES` is read once at Hyprland's launch, so there is no way to
promote the dGPU mid-session. Do not wire a dock event to a compositor
restart: that kills every open application at the exact moment you plugged in
a monitor because you needed it.

A watcher (`gpu_dock_watch.sh`, polled every 5 s from a Quickshell `Timer`)
reads the `/tmp/serpantinum_gpu_mode` marker, waits for the dGPU's connector
to report `connected` while in `igpu` mode, requires two consecutive positive
polls so a cable bounce cannot false-trigger, and then sends one notification:
log out and back in whenever convenient for full performance, nothing restarts
automatically. It stays quiet until the next dock event, and does nothing at
all on unplug — that direction is a battery-life nicety, not an emergency.

## Verify

```bash
cat /tmp/serpantinum_gpu_mode
# expect: igpu when undocked on battery, otherwise default
```

```bash
nvidia-smi --query-gpu=power.draw,pstate --format=csv,noheader
# expect: ~9 W / P0 as primary, ~4.3 W / P8 once demoted and idle
```

To exercise the live-dock path: undock, unplug AC, log out and in, confirm the
marker reads `igpu`. Plug the monitor back in and confirm it lights up in
`hyprctl monitors` within a few seconds and the notification arrives about 10 s
later. Unplug again and confirm it disappears cleanly and the dGPU idles back
down.

## Roll back

```bash
rm ~/.config/uwsm/env-hyprland.d/10-gpu-power.sh
sudo rm /etc/udev/rules.d/90-gpu-symlinks.rules
sudo udevadm control --reload && sudo udevadm trigger
```

Log out and back in. Aquamarine returns to picking the primary GPU itself, and
the dGPU goes back to rendering everything.

## Trade-offs

- There is no live primary-GPU handoff in Hyprland or Aquamarine today. Every
  transition needs a fresh compositor launch, which is why this only decides
  at login.
- Booting on battery with the monitor already plugged in correctly stays
  dGPU-primary — the monitor wins. Booting undocked and plugging in later goes
  through the live-hotplug path instead, which worked on this hardware but is
  best-effort on NVIDIA by the compositor's own documentation.
- The dGPU's PCI `power/control` was never observed reaching `auto`/D3cold
  during normal desktop use. The ~9 W → ~4.3 W drop comes from the driver's
  own P-state management and is measured; full runtime suspend may need longer
  idle windows than were tested and could save a few watts more.

## Troubleshooting

**The external monitor stays blank after enabling this**

Find which card the connector actually belongs to:

```bash
ls -l /dev/dri/by-path
for f in /sys/class/drm/card*-*/status; do echo "$f: $(cat "$f")"; done
```

If the monitor is on the *iGPU* card, `_gpu_power_dgpu_has_monitor` cannot see
it and will switch to iGPU-primary while you are plugged in. Add that
connector's card to the check, or invert which symlink it scans.

**The marker says `igpu` but `nvidia-smi` still shows high power draw**

Confirm both symlinks resolve:

```bash
readlink -f /dev/dri/igpu /dev/dri/dgpu
```

If the udev rule did not apply, the existence check in the script silently
falls through to default behaviour.

**`AQ_DRM_DEVICES` is missing from the Hyprland process environment**

Expected, and not a fault. Reading the running compositor's
`/proc/PID/environ` does not reliably reflect variables exported through
`uwsm` — confirmed live on this machine, with the dGPU genuinely idling at
4.3 W while the variable was absent from `/proc/$PID/environ`. Trust
`/tmp/serpantinum_gpu_mode` and the measured power draw instead.
