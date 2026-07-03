# Fix: TUXEDO Control Center Shows No Fan or Temperature (ABRA A5 V20.2)

**Symptom:** TUXEDO Control Center's dashboard shows nothing for fan speed or CPU temperature — both gauges are blank/zero, even though the fans are physically spinning and the CPU is clearly running hot under load.

**Tested on:** Monster ABRA A5 V20.2 · BIOS N.1.13MON07 · Ubuntu 22.04 (kernel 6.8) · `tuxedo-drivers` 4.22.2 · `tuxedo-control-center` 2.1.17

---

## Why This Happens

`tccd` (the TUXEDO Control Center daemon) reads sensors through one of three paths, in order:

1. A hwmon chip named exactly `tuxedo_tuxi_sensors`.
2. A hwmon chip named exactly `tuxedo` (plus, optionally, a platform device at `/sys/bus/platform/devices/tuxedo_fan_control` for fan-curve write access).
3. Fallback: talk directly to `/dev/tuxedo_io`, which forwards `CLEVO_CMD_GET_FANINFO*` calls over WMI to the board firmware.

On the ABRA A5, neither of the first two hwmon chips exist, so `tccd` falls back to path 3. But the ABRA A5's OEM ("MONSTER") firmware doesn't fully implement the standard Clevo WMI command set — the same way `CLEVO_CMD_GET_SPECS` fails at boot (visible in `dmesg` as `CLEVO_CMD_GET_SPECS does not exist on this device`), `CLEVO_CMD_GET_FANINFO1/2/3` also comes back empty. `TuxedoIOAPI.GetNumberFans()` then reports **0 fans**, and `tccd`'s `FanControlWorker` aborts its entire update cycle when that happens — logged once at startup as:

```
tccd[...]: Using tuxedo-io
tccd[...]: FanControlWorker: Control unavailable
```

Because fan and temperature are updated together in that same code path, the dashboard loses **both**, not just the fan reading.

This is confirmed by calling the daemon's own native binding directly (as root):

```bash
node -e '
const api = require("/opt/tuxedo-control-center/resources/app.asar/dist/tuxedo-control-center/service-app/native-lib/TuxedoIOAPI.node");
console.log("wmiAvailable:", api.wmiAvailable());   // -> false
console.log("getNumberFans:", api.getNumberFans()); // -> 0
'
```

## What the DSDT Actually Provides (and What's Dead)

The DSDT (dumped with `acpidump`, decompiled with `iasl`) declares a memory-mapped EC region `ECMG` at `0xFE410000` containing, among others:

| Field | Offset | Meaning | Status on N.1.13MON07 |
|-------|--------|---------|----------------------|
| `CPUT` | `0xE0D` | CPU temperature | **dead — always 0** |
| `PCHT` | `0xE0E` | PCH temperature | **dead — always 0** |
| `SN1T`–`SN5T` | `0xE10`–`0xE18` | extra temp sensors | **dead — always 0** |
| `F1SH`/`F1SL` | `0xE1C`/`0xE1D` | fan1 tachometer (16-bit) | **dead — always 0** |
| `F1DC`+`F1CM` | `0xE8C` | fan1 duty (0–127) + manual bit | **live, working** |
| `F2DC`+`F2CM` | `0xE9D` | fan2 duty (0–127) + manual bit | **live, working** |

Verified with a read-only probe module under full fan load (duty at 116/127): the duty registers track fan behavior in real time, while every temperature/tachometer byte stays at 0 — the EC firmware simply never populates them.

The ACPI thermal zone `ECTZ` is no help either: its `_TMP` method returns a **formula** (`0x0AAC + XHPP*0xA`), not a real sensor read. (The `acpitz` values you see in `sensors` come from this synthetic zone.)

The only trustworthy sources on this board are:

- **CPU temperature:** the CPU's own digital thermal sensor, via `MSR_IA32_PACKAGE_THERM_STATUS` / `MSR_IA32_TEMPERATURE_TARGET` — the same mechanism the `coretemp` driver uses (verified to track `coretemp` within 1–3 °C under load).
- **Fan speed:** the EC duty registers above. There is no real RPM, but duty percent is exactly what TCC displays as "fan speed" on working Clevo devices anyway (their WMI fan info is also duty, not RPM).

## The Fix

A board-specific out-of-tree module, [`tuxedo-abra-fan-fix/tuxedo_abra_fan.c`](tuxedo-abra-fan-fix/tuxedo_abra_fan.c), which:

- Registers a hwmon chip named exactly **`tuxedo`**, so `tccd` picks it up via path 2 above and never touches the broken WMI path. After restart, `tccd` logs `Using pwm hwmon` instead of `Using tuxedo-io`.
- Exposes `temp1` (label `cpu0`) read from the CPU package thermal MSR.
- Exposes `fan1`/`fan2` (labels `cpu0`/`gpu0`) reporting the live EC duty value with `fan_max = 127`, so `tccd`'s `input/max*100` math displays the true duty percent.
- Keeps the previously reverse-engineered PWM duty **control** (write `pwm1`/`pwm2`, manual/auto via `pwm1_enable`) unchanged.

> **Note:** because hwmon's `fanN_input` is nominally RPM, `lm-sensors` will print the raw duty (0–127) with an "RPM" unit for this chip. That's cosmetic; the value is real duty. Use `coretemp`/`nvme` in `sensors` as before for temps.

### Install

**1. Place the module source at `/usr/src/tuxedo-abra-fan-1.0/`:**

```bash
sudo mkdir -p /usr/src/tuxedo-abra-fan-1.0
sudo cp tuxedo-abra-fan-fix/tuxedo_abra_fan.c \
        tuxedo-abra-fan-fix/Makefile \
        tuxedo-abra-fan-fix/dkms.conf /usr/src/tuxedo-abra-fan-1.0/
```

**2. Build and install with DKMS:**

```bash
KERNEL=$(uname -r)
sudo dkms remove tuxedo-abra-fan/1.0 -k "$KERNEL" 2>/dev/null || true
sudo dkms add /usr/src/tuxedo-abra-fan-1.0 2>/dev/null || true
sudo dkms build tuxedo-abra-fan/1.0 -k "$KERNEL"
sudo dkms install tuxedo-abra-fan/1.0 -k "$KERNEL" --force
sudo modprobe -r tuxedo_abra_fan 2>/dev/null || true
sudo modprobe tuxedo_abra_fan
echo tuxedo_abra_fan | sudo tee /etc/modules-load.d/tuxedo-abra-fan.conf
```

**3. Restart the TCC daemon:**

```bash
sudo systemctl restart tccd
```

## Verify

```bash
# hwmon chip named "tuxedo" with live values
H=$(grep -xl tuxedo /sys/class/hwmon/hwmon*/name | sed 's|/name||')
cat $H/temp1_input   # CPU temp in millidegrees, should match coretemp
cat $H/fan1_input    # current fan duty, 0-127

# tccd must select the hwmon path
journalctl -u tccd -b | grep "Using pwm hwmon"

# and publish real data on D-Bus
dbus-send --system --print-reply --dest=com.tuxedocomputers.tccd \
  /com/tuxedocomputers/tccd com.tuxedocomputers.tccd.GetFanDataCPU
```

Open TUXEDO Control Center — the dashboard now shows a live CPU temperature and fan speed percent.

## Known Limitation

True fan RPM cannot be shown: the EC firmware never fills the DSDT-declared tachometer bytes, and no alternative RPM register has been found in the `ECMG` region. If a future BIOS update (post `N.1.13MON07`) starts populating `F1SH`/`F1SL` at `0xE1C`/`0xE1D`, the driver can be extended to prefer them — probe them with the field map above before assuming.

## Troubleshooting

**`dkms build` fails with a compile error**

Make sure your kernel headers match your running kernel exactly (`sudo apt install linux-headers-$(uname -r)`).

**tccd still logs `Using tuxedo-io`**

The hwmon chip isn't registered. Check `lsmod | grep abra`, `dmesg | grep abra_fan`, and that `grep -x tuxedo /sys/class/hwmon/hwmon*/name` matches something. Then restart `tccd`.

**Temperature reads 0 or fails**

`rdmsr` may be blocked by your kernel config. The module reads MSRs in-kernel (no `msr` userspace module needed), which works on stock Ubuntu kernels; if you run a locked-down custom kernel, verify `CONFIG_X86_MSR` behavior.
