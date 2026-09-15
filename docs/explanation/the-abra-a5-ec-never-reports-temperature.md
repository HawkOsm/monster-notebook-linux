# The ABRA A5 EC never reports temperature

**Status:** verified
**Applies to:** Monster ABRA A5 V20.2 · BIOS N.1.13MON07
**Verified on:** Ubuntu 22.04 · kernel 6.8 · `tuxedo-control-center` 2.1.17 ·
2026-08-13
**See also:** [show fan and temperature in TUXEDO Control Center](../how-to/show-fan-and-temperature-in-tuxedo-control-center.md)

## In short

The board's OEM firmware implements only part of the Clevo WMI command set.
`tccd` asks it how many fans exist, gets zero, and abandons its whole update
cycle — which is why the dashboard loses the temperature reading as well as
the fan reading. The EC's temperature and tachometer registers are declared in
the DSDT but never populated.

## How `tccd` chooses a sensor source

`tccd` tries three paths in order:

1. A hwmon chip named exactly `tuxedo_tuxi_sensors`.
2. A hwmon chip named exactly `tuxedo`, optionally with a platform device at
   `/sys/bus/platform/devices/tuxedo_fan_control` for fan-curve writes.
3. `/dev/tuxedo_io`, which forwards `CLEVO_CMD_GET_FANINFO*` calls over WMI to
   the board firmware.

Neither hwmon chip exists on the ABRA A5, so `tccd` falls through to the WMI
path. That is where it breaks.

## Why one missing value costs two gauges

The MONSTER firmware does not fully implement the Clevo command set.
`CLEVO_CMD_GET_SPECS` already fails at boot — visible in `dmesg` as
`CLEVO_CMD_GET_SPECS does not exist on this device` — and
`CLEVO_CMD_GET_FANINFO1/2/3` comes back empty in the same way.
`TuxedoIOAPI.GetNumberFans()` therefore reports **0 fans**, and `tccd`'s
`FanControlWorker` aborts its entire update cycle rather than continuing
without a fan count:

```text
tccd[...]: Using tuxedo-io
tccd[...]: FanControlWorker: Control unavailable
```

Fan speed and temperature are refreshed together in that one code path. Losing
the fan count takes the temperature down with it.

You can confirm it by calling the daemon's own native binding directly, as
root:

```bash
node -e '
const api = require("/opt/tuxedo-control-center/resources/app.asar/dist/tuxedo-control-center/service-app/native-lib/TuxedoIOAPI.node");
console.log("wmiAvailable:", api.wmiAvailable());   // -> false
console.log("getNumberFans:", api.getNumberFans()); // -> 0
'
```

## What the hardware actually exposes

Dumping the DSDT with `acpidump` and decompiling it with `iasl` shows a
memory-mapped EC region `ECMG` at `0xFE410000` that declares CPU temperature,
PCH temperature, five spare temperature sensors, and 16-bit fan tachometers —
alongside the fan duty registers. The
[EC field map](../reference/abra-a5-ec-field-map.md) lists every field and its
real state.

A read-only probe module under full fan load, with duty at 116/127, settled
which of them are real: the duty registers track fan behaviour live, while
every temperature and tachometer byte stays at 0. The firmware simply never
writes them.

The ACPI thermal zone `ECTZ` is no help either. Its `_TMP` method returns a
formula, `0x0AAC + XHPP*0xA`, rather than reading a sensor. The `acpitz`
values that show up in `sensors` come from that synthetic zone and mean
nothing.

That leaves two trustworthy sources on this board:

- **CPU temperature** from the CPU's own digital thermal sensor, via
  `MSR_IA32_PACKAGE_THERM_STATUS` and `MSR_IA32_TEMPERATURE_TARGET` — the same
  mechanism `coretemp` uses, and verified to track `coretemp` within 1–3 °C
  under load.
- **Fan speed** from the EC duty registers. There is no real RPM available,
  but duty percent is what TCC displays as "fan speed" on working Clevo
  machines anyway, since their WMI fan info is duty rather than RPM.

The fix follows directly: register a hwmon chip named `tuxedo` so `tccd` takes
path 2 and never reaches the broken WMI path at all.
