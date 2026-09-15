# ABRA A5 EC field map

**Status:** verified
**Applies to:** Monster ABRA A5 V20.2 · BIOS N.1.13MON07
**Verified on:** Ubuntu 22.04 · kernel 6.8 · 2026-08-13
**See also:** [why the ABRA A5 EC never reports temperature](../explanation/the-abra-a5-ec-never-reports-temperature.md)

Fields of the memory-mapped EC region `ECMG` at `0xFE410000`, as declared by
the DSDT (dumped with `acpidump`, decompiled with `iasl`). The status column
records what a read-only probe module actually observed under full fan load,
with duty at 116/127 — not what the firmware claims.

| Field | Offset | Meaning | Status on N.1.13MON07 |
|-------|--------|---------|----------------------|
| `CPUT` | `0xE0D` | CPU temperature | **dead — always 0** |
| `PCHT` | `0xE0E` | PCH temperature | **dead — always 0** |
| `SN1T`–`SN5T` | `0xE10`–`0xE18` | extra temp sensors | **dead — always 0** |
| `F1SH`/`F1SL` | `0xE1C`/`0xE1D` | fan1 tachometer (16-bit) | **dead — always 0** |
| `F1DC`+`F1CM` | `0xE8C` | fan1 duty (0–127) + manual bit | **live, working** |
| `F2DC`+`F2CM` | `0xE9D` | fan2 duty (0–127) + manual bit | **live, working** |

## Usable sensor sources on this board

| Reading | Source | Notes |
|---|---|---|
| CPU temperature | `MSR_IA32_PACKAGE_THERM_STATUS`, `MSR_IA32_TEMPERATURE_TARGET` | tracks `coretemp` within 1–3 °C under load |
| Fan speed | EC duty registers above | duty percent, not RPM |
| GPU temperature | `nvidia-smi`, fed in from userspace | no kernel-visible hwmon on the proprietary driver |

The ACPI thermal zone `ECTZ` is not a sensor. Its `_TMP` method returns the
formula `0x0AAC + XHPP*0xA`, which is where the meaningless `acpitz` values in
`sensors` come from.

If a BIOS later than `N.1.13MON07` begins populating `F1SH`/`F1SL`, probe
those offsets before trusting them.
