# Show fan and temperature in TUXEDO Control Center

**Status:** verified
**Applies to:** Monster ABRA A5 V20.2 · BIOS N.1.13MON07
**Verified on:** Ubuntu 22.04 · kernel 6.8 · `tuxedo-drivers` 4.22.2 ·
`tuxedo-control-center` 2.1.17 · 2026-08-13
**Symptom:** TUXEDO Control Center's dashboard shows nothing for fan speed or
CPU temperature. Both gauges read blank or zero while the fans are audibly
spinning and the CPU is clearly hot under load.
**See also:** [why the ABRA A5 EC never reports temperature](../explanation/the-abra-a5-ec-never-reports-temperature.md)

Install a board-specific hwmon driver that feeds `tccd` real values, so it
never falls back to the firmware's broken WMI path.

The driver registers a hwmon chip named `tuxedo`, so `tccd` logs
`Using pwm hwmon` instead of `Using tuxedo-io`. It exposes:

- `temp1` (label `cpu0`) — CPU package temperature, read from the thermal MSR.
- `fan1` and `fan2` (labels `cpu0` and `gpu0`) — live EC duty with
  `fan_max = 127`, so `tccd`'s `input/max*100` maths shows true duty percent.
- `temp2` (label `gpu0`) — fed from userspace via the driver's `gpu_temp`
  attribute, and expired after 15 s so a dead updater cannot leave a stale
  reading on screen.
- `pwm1`, `pwm2` and `pwm1_enable` — the reverse-engineered duty control,
  unchanged.

Its source lives in [`drivers/abra-a5-fan/`](../../drivers/abra-a5-fan/).

## Before you start

You need kernel headers matching your running kernel, and DKMS:

```bash
sudo apt install linux-headers-$(uname -r) dkms
```

Run every command below from the root of this repository.

## Confirm the diagnosis

```bash
journalctl -u tccd -b | grep -E "Using tuxedo-io|Control unavailable"
# expect: Using tuxedo-io
# expect: FanControlWorker: Control unavailable
```

## Fix

### 1. Place the module source

```bash
sudo mkdir -p /usr/src/tuxedo-abra-fan-1.0
sudo cp drivers/abra-a5-fan/tuxedo_abra_fan.c \
        drivers/abra-a5-fan/Makefile \
        drivers/abra-a5-fan/dkms.conf \
        /usr/src/tuxedo-abra-fan-1.0/
```

### 2. Build and install with DKMS

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

### 3. Install the GPU temperature updater

TCC hides the entire GPU fan card unless a `gpu0` temperature above 1 exists,
and the proprietary NVIDIA driver exposes no hwmon the kernel can read. This
service polls `nvidia-smi` every 5 s and writes the value into the driver. It
skips polls while the dGPU is runtime-suspended, so it never wakes the GPU,
and the driver expires the value after 15 s so a dead updater cannot leave a
stale reading on screen.

```bash
sudo cp drivers/abra-a5-fan/abra-gpu-temp-updater.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/abra-gpu-temp-updater.sh
sudo cp drivers/abra-a5-fan/abra-gpu-temp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now abra-gpu-temp.service
```

If your dGPU is not at PCI `0000:01:00.0`, adjust `GPU_PCI` in the script.
Find yours with `lspci | grep -i nvidia`.

### 4. Restart the TCC daemon

```bash
sudo systemctl restart tccd
```

## Verify

```bash
H=$(grep -xl tuxedo /sys/class/hwmon/hwmon*/name | sed 's|/name||')
cat $H/temp1_input   # CPU temp in millidegrees, should match coretemp
cat $H/fan1_input    # current fan duty, 0-127
```

```bash
journalctl -u tccd -b | grep "Using pwm hwmon"
# expect: Using pwm hwmon
```

```bash
dbus-send --system --print-reply --dest=com.tuxedocomputers.tccd \
  /com/tuxedocomputers/tccd com.tuxedocomputers.tccd.GetFanDataCPU
```

Open TUXEDO Control Center. The dashboard now shows a live CPU temperature and
fan speed percentage.

## Roll back

```bash
sudo systemctl disable --now abra-gpu-temp.service
sudo rm -f /etc/systemd/system/abra-gpu-temp.service /usr/local/bin/abra-gpu-temp-updater.sh
sudo systemctl daemon-reload
sudo rm -f /etc/modules-load.d/tuxedo-abra-fan.conf
sudo modprobe -r tuxedo_abra_fan
sudo dkms remove tuxedo-abra-fan/1.0 --all
sudo rm -rf /usr/src/tuxedo-abra-fan-1.0
sudo systemctl restart tccd
```

`tccd` goes back to its broken WMI path and the gauges go blank again.

## Trade-offs

True fan RPM cannot be shown. The EC firmware never fills the tachometer bytes
the DSDT declares, and no alternative RPM register has been found. What you
get is duty percent — which is also what TCC displays as "fan speed" on
working Clevo machines, since their WMI fan info is duty rather than RPM too.

Because hwmon's `fanN_input` is nominally RPM, `lm-sensors` prints the raw
duty value (0–127) labelled "RPM" for this chip. That is cosmetic. Keep using
`coretemp` and `nvme` in `sensors` for temperatures.

If a BIOS newer than `N.1.13MON07` starts populating `F1SH`/`F1SL`, the driver
could prefer them. Probe the registers listed in the
[EC field map](../reference/abra-a5-ec-field-map.md) before assuming.

## Troubleshooting

**`dkms build` fails with a compile error**

Your kernel headers do not match the running kernel:

```bash
sudo apt install linux-headers-$(uname -r)
```

**`tccd` still logs `Using tuxedo-io`**

The hwmon chip did not register:

```bash
lsmod | grep abra
dmesg | grep abra_fan
grep -x tuxedo /sys/class/hwmon/hwmon*/name
```

Then restart `tccd`.

**Temperature reads 0 or fails**

The module reads MSRs in kernel space, so no userspace `rdmsr` or `msr`
module is needed, and this works on stock Ubuntu kernels. On a locked-down
custom kernel, check your `CONFIG_X86_MSR` behaviour.
