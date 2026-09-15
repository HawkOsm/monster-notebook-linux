# `tccd` profiles

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 · `tuxedo-control-center-bin` 3.0.9
**Verified on:** Arch Linux · kernel 7.2 · 2026-08-13
**See also:** [switch power profiles from a custom shell](../how-to/switch-power-profiles-from-a-custom-shell.md)

The profile set defined in `/etc/tcc/profiles` on this machine, mapping four
UI modes onto `tccd`'s ODM profiles.

| id | odmProfile | fan.fanProfile | cpu.governor / EPP | notes |
|---|---|---|---|---|
| `__default_custom_profile__` | `entertainment` | `Cool` | `powersave` / `balance_performance` | Balanced, AC default |
| `performance` | `performance` | `Freezy` | `performance` / `performance`, `useMaxPerfGov: true` | |
| `quiet` | `quiet` | `Silent` | `powersave` / `balance_power` | |
| `power_saving_high` | `power_saving` | `Quiet` | `powersave` / `power`, `noTurbo: true`, capped max freq | battery default, >30% |
| `power_saving_low` | `power_saving` | `Quiet` | same, lower freq cap, `webcam.status: false`, dimmed brightness | auto-applied ≤30% |

`__default_custom_profile__` is mandatory. Delete it and `tccd` regenerates it
with generic values on the next restart, and resets `/etc/tcc/settings`'s
`stateMap` to point at it. Repurpose it rather than removing it.

## Fan preset names

`tuxedo-io` and the kernel driver resolve these names from the string alone.
The `customFanCurve` table in the JSON is consulted only when `fanProfile` is
not one of them.

`Silent` · `Quiet` · `Balanced` · `Cool` · `Freezy` · `Custom`

Confirm the stock list against the Electron app's own bundle:

```bash
grep -a -oE '"(Quiet|Balanced|Silent|Cool|Custom|Freezy)"' \
  /opt/tuxedo-control-center/resources/app.asar | sort -u
```

## D-Bus interface

Service `com.tuxedocomputers.tccd` on the system bus, object path
`/com/tuxedocomputers/tccd`.

| Method | Purpose |
|---|---|
| `SetTempProfileById(s)` | apply a profile as a temporary override |
| `GetActiveProfileJSON()` | read the profile currently in effect |
| `GetSettingsJSON()` | read `/etc/tcc/settings`, including `stateMap` |
| `GetFanDataCPU()` | current CPU fan data |

There is no D-Bus setter for `stateMap`.
