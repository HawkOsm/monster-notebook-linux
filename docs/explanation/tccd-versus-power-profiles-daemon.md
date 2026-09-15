# Why `tccd` and `power-profiles-daemon` are not the same thing

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 · `tuxedo-control-center-bin` 3.0.9
**Verified on:** Arch Linux · kernel 7.2 · 2026-08-13
**See also:** [switch power profiles from a custom shell](../how-to/switch-power-profiles-from-a-custom-shell.md)

## In short

Two power daemons can run side by side on this hardware, and only one of them
controls anything. `power-profiles-daemon` is the generic freedesktop
abstraction, and here it has no platform driver behind it. `tccd` owns the fan
curves, the CPU governor and EPP, and the ODM platform mode. A UI bound to the
first one is steering a daemon with nothing attached to the far end.

## Why the switch does nothing

Desktop shells reach for `power-profiles-daemon` (`net.hadess.PowerProfiles`)
because it is the portable choice — Quickshell exposes it through
`Quickshell.Services.UPower`, and every other desktop has a widget for it. On
this machine it runs standalone with no real backend:

```bash
powerprofilesctl list
# PlatformDriver: placeholder   (for balanced and power-saver)
```

`placeholder` is the daemon saying it has nothing to drive. Meanwhile `tccd`
holds the actual controls: fan curves, CPU governor and energy-performance
preference, and the ODM platform mode — `quiet`, `power_saving`,
`entertainment` or `performance`. The two never talk to each other. Flipping
the UI switch changes a value inside a daemon that cannot act on it.

There is often a second problem underneath. A fresh `tccd` may have only one
profile defined, the mandatory `__default_custom_profile__` ("TUXEDO
Defaults"), applied identically on AC and on battery. Even the daemon that
*can* act has nothing to switch between until you define real profiles.

## The `stateMap` reset, and how it was isolated

`/etc/tcc/settings` contains a `stateMap` that maps `power_ac` and `power_bat`
to profile ids. It is supposed to apply a default profile per power source.
It does not survive a restart.

There is no D-Bus setter for it — only `GetSettingsJSON`. Editing the file
directly and restarting `tccd` appears to work, right up until the next
restart, when `tccd`'s own startup routine silently resets **both**
`power_ac` and `power_bat` back to `__default_custom_profile__` and discards
whatever was configured.

Isolating the variable is what made this legible. Writing the file *without*
restarting `tccd` persists fine — a live `GetSettingsJSON` query just serves
the stale in-memory copy, which is misleading but harmless. The reset happens
specifically in the daemon's boot-time initialisation, not in any live
file-watch reconciliation. That distinction matters: it rules out a permissions
or file-format problem and rules in "do not use this mechanism".

The consequence for anyone wiring a panel: do not rely on `stateMap`. Poll the
AC state yourself and call `SetTempProfileById` on each transition. Since that
method applies a *temporary* override — the same semantics the TCC GUI itself
uses — a manual pick naturally survives until the next real AC transition,
with no extra bookkeeping.

## The other trap: deleting the mandatory profile

`tccd` requires the id `__default_custom_profile__` to exist. Remove it and the
daemon regenerates it with generic values on the next restart, then points
`stateMap` at the thing it just invented. The fix is to repurpose that id as
your Balanced profile rather than leaving it as an unused extra entry and
defining Balanced somewhere else.
