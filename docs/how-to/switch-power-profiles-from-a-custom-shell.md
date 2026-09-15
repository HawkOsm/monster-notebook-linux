# Switch power profiles from a custom shell

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 · Hyprland via `uwsm` · custom
Quickshell shell
**Verified on:** Arch Linux · kernel 7.2 · `tuxedo-control-center-bin` 3.0.9 ·
`tuxedo-drivers-dkms` 4.22.2 · 2026-08-13
**Symptom:** a custom panel offers Performance / Balanced / Power Saver modes,
but switching between them changes nothing. Fans, CPU clocks and platform
behaviour stay identical whichever mode is selected.
**See also:** [why `tccd` and `power-profiles-daemon` are not the same thing](../explanation/tccd-versus-power-profiles-daemon.md)

Point the panel at `tccd`, the daemon that actually owns fan curves and CPU
policy on this hardware, instead of at `power-profiles-daemon`, which owns
nothing here.

## Confirm the diagnosis

```bash
powerprofilesctl list
# expect: PlatformDriver: placeholder for balanced and power-saver
```

A placeholder platform driver means `power-profiles-daemon` has no hardware
backend. Anything bound to it is steering a daemon that cannot act.

## Fix

### 1. Define real `tccd` profiles

`tccd` exposes the ODM profiles `quiet`, `power_saving`, `entertainment` and
`performance` — a clean match for four UI modes. Add them to
`/etc/tcc/profiles`, a root-owned JSON array. Back it up first. The
[`tccd` profile reference](../reference/tccd-profiles.md) lists the exact
mapping used here.

Keep the id `__default_custom_profile__`. `tccd` requires it to exist, and
regenerates it with generic values if you remove it — taking your
`/etc/tcc/settings` `stateMap` with it. Repurpose it as your Balanced profile
rather than leaving it as an unused sixth entry.

```bash
sudo systemctl restart tccd
```

### 2. Rewire the panel to `tccd`

`tccd` exposes a system D-Bus service at `com.tuxedocomputers.tccd`, path
`/com/tuxedocomputers/tccd`, with `SetTempProfileById(id)` and
`GetActiveProfileJSON()`. Confirm both work from your normal user session with
no password prompt — polkit already permits this, exactly as it does for the
TCC tray app:

```bash
busctl --system call com.tuxedocomputers.tccd /com/tuxedocomputers/tccd \
  com.tuxedocomputers.tccd SetTempProfileById s "performance"
busctl --system call com.tuxedocomputers.tccd /com/tuxedocomputers/tccd \
  com.tuxedocomputers.tccd GetActiveProfileJSON
```

Two small wrapper scripts — one to get, one to set by id, parsing the D-Bus
JSON with `jq` — replace the `PowerProfiles.profile` binding in the panel's
QML. A generic N-way `Switch` widget already handles any number of options, so
this is a content change rather than a widget rewrite.

### 3. Drive AC and battery defaults yourself

Do not rely on `tccd`'s own `stateMap`. It does not survive a daemon restart —
the explanation document covers why.

A small polling watcher (`ac_state_watch.sh`) checks
`/sys/class/power_supply/AC*/online` every 10 s or so, remembers the last seen
state in a file under `/tmp`, and calls `SetTempProfileById` itself on each
transition: Balanced on AC, `power_saving_high` on battery.

Because `SetTempProfileById` is a *temporary* override — the same semantics the
TCC GUI uses — a profile you pick by hand stays until the next real AC
transition. No extra bookkeeping is needed to make manual choices stick.

### 4. Tier by battery percentage (optional)

A second watcher (`battery_tier_watch.sh`) reads
`/sys/class/power_supply/BAT0/capacity` and switches between
`power_saving_high` and `power_saving_low` at a threshold such as 30%. Gate it
so it only acts while the active profile is already one of those two ids —
otherwise it will override a manually chosen Performance, Balanced or Quiet
mode.

## Verify

Cycle every mode and confirm each applies distinct settings:

```bash
for id in performance __default_custom_profile__ quiet power_saving_high power_saving_low; do
  busctl --system call com.tuxedocomputers.tccd /com/tuxedocomputers/tccd \
    com.tuxedocomputers.tccd SetTempProfileById s "$id" >/dev/null
  busctl --system -j call com.tuxedocomputers.tccd /com/tuxedocomputers/tccd \
    com.tuxedocomputers.tccd GetActiveProfileJSON 2>/dev/null \
    | jq -r '.data[0]' | jq -r '"\(.id): odm=\(.odmProfile.name) fan=\(.fan.fanProfile)"'
done
```

Each id must report distinct `odm=` and `fan=` values, and you should hear the
fan curve change between Performance and Quiet.

## Roll back

Restore your backup of `/etc/tcc/profiles`, restore the panel's original
`PowerProfiles.profile` binding, and stop the watchers:

```bash
sudo cp /etc/tcc/profiles.bak /etc/tcc/profiles
sudo systemctl restart tccd
```

## Troubleshooting

**`SetTempProfileById` returns `b true` but nothing changes**

If the id is not in `/etc/tcc/profiles`, `tccd` silently falls back to a
hardcoded legacy default — `__legacy_default__`,
`__legacy_cool_and_breezy__` or `__legacy_powersave_extreme__` — instead of
returning an error. Check the `id` field of `GetActiveProfileJSON`, not the
boolean return value, to confirm which profile actually landed.

**`/etc/tcc/profiles` grew a duplicate or unused entry after editing**

You removed `__default_custom_profile__`. `tccd` regenerated it with generic
defaults (`odm=performance`, `fan=Balanced`) and reset `stateMap` to point at
it. Keep the id and repurpose its
contents.

**Fan profile names seem to do nothing distinct**

Only the exact strings `Silent`, `Quiet`, `Balanced`, `Cool`, `Freezy` and
`Custom` are recognised. Anything else falls back to whatever `tccd` treats as
Custom behaviour for that string, using the `customFanCurve` table if present
or a driver default.
