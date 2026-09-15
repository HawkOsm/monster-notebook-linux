# Hyprland picks the dGPU as primary renderer

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (Arch Linux · Hyprland 0.56 ·
nvidia-open-dkms)
**Verified on:** Arch Linux · kernel 7.2 · 2026-09-15
**See also:** [idle the dGPU on battery under Hyprland](../how-to/idle-the-dgpu-on-battery-under-hyprland.md)

## In short

Aquamarine, Hyprland's rendering backend, chooses the NVIDIA dGPU as primary
at startup. While the compositor renders through that card it can never reach
D3cold, no matter what PCI runtime power policy you set. Making the iGPU
primary fixes the power draw and breaks any external monitor wired to the
dGPU, which is why the fix has to be conditional.

## The mechanism

The documented control is `AQ_DRM_DEVICES`, an Aquamarine environment variable
listing DRM devices in priority order. First in the list becomes primary. Two
details make it easy to set and still have nothing happen:

**It must exist before Hyprland's own process starts.** `hyprland.conf`'s
`env =` directive and `hyprland.lua`'s `hl.env()` both apply to applications
Hyprland launches, not to Hyprland's own backend initialisation. In a
`uwsm`-managed session the export belongs in
`~/.config/uwsm/env-hyprland.d/*.sh`, which `env-hyprland` sources before
launch.

**Its separator collides with PCI addressing.** `AQ_DRM_DEVICES` separates
device paths with `:`, and a path like
`/dev/dri/by-path/pci-0000:00:02.0-card` is full of colons. The value
mis-parses with no error. `cardN` numbers are not a safe substitute either,
since they can renumber between boots. Colon-free udev symlinks are the only
reliable form.

## Why the obvious fix breaks things

Hyprland's own NVIDIA documentation states that the driver "doesn't support
important features for Multi-GPU which can result in a broken or slow setup"
for a monitor attached to the non-primary GPU. That is an acknowledged driver
limitation, not a configuration mistake. Make the iGPU primary
unconditionally, and any external monitor wired to the dGPU lands in exactly
that failure mode. Reports for this class of hybrid setup range from noticeable
lag to a compositor crash needing a session restart.

This machine hit it for real. A first attempt set `AQ_DRM_DEVICES`
unconditionally and made both mistakes above at once — wrong file, wrong path
syntax — so the setting never took effect. Aquamarine's own heuristic then
independently picked the iGPU as primary on a later boot; it appears to prefer
whichever GPU has a display connected at startup. With nothing plugged into
the dGPU at boot, the external monitor had no route to light up at all until
the configuration was corrected and the session restarted.

Hence the conditional: iGPU-primary only when undocked *and* on battery. When
a monitor is connected, the dGPU keeps the job it is better at.

## Why the dGPU stays in the list

The conditional export names both cards, dGPU second, rather than dropping the
dGPU entirely. Omitting it would make a mid-session dock guaranteed to fail
instead of merely best-effort. A monitor that hotplugs onto an already-open
secondary GPU worked cleanly on this hardware — no restart, no crash, no
visible lag across repeated plug and unplug cycles. Best-effort beats
guaranteed-broken.

There is no live handoff to promote the dGPU back to primary, because
`AQ_DRM_DEVICES` is read exactly once at launch. The tempting response is to
detect the dock event and restart the compositor automatically. That destroys
every open application at the precise moment the user plugged in a monitor
because they needed it, so the watcher only ever sends a notification.

## Why you cannot read the setting back from the process

Checking the running compositor's `/proc/PID/environ` does not reliably show
variables exported through `uwsm`. This was confirmed live: the dGPU was
genuinely demoted and idling at 4.3 W while `AQ_DRM_DEVICES` was absent from
`/proc/$PID/environ`. Measure the power draw, or read the marker file the
export script writes. Do not trust the process environment here.
