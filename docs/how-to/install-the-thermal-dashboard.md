# Install the thermal dashboard

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator)
**Verified on:** Ubuntu 26.04 · kernel 7.0 · 2026-08-13
**Symptom:** no single place shows CPU, GPU and NVMe temperatures with fan
RPMs. `sensors` alone misses the GPU, and the ITE IT5570E embedded controller
is not supported by the `it87` module.
**See also:** [thermal sensor sources](../reference/thermal-sensor-sources.md)

A terminal dashboard that reads each value from the source that actually works
on this machine: `coretemp` and `nvme` hwmon for temperatures, ACPI hwmon for
fan RPM, `nvidia-smi` for the GPU, and `/dev/tuxedo_io` for EC fan duty.

```text
╔════════════════════════════════════════╗
║  Monster TULPAR T6 V2.1 - Thermals    ║
╠════════════════════════════════════════╣
║  CPU Package   : 61.0C               ║
║  CPU Max Core  : 62C                 ║
║  NVMe 0        : 28.0C               ║
║  NVMe 1        : 32.0C               ║
╠════════════════════════════════════════╣
║  GPU Temp      : 43C                 ║
║  GPU Fan (smi) : EC-controlled       ║
║  GPU Power     : 17W                 ║
║  GPU Clock     : 2370MHz             ║
╠════════════════════════════════════════╣
║  CPU Fan       : 2298 RPM            ║
║  DGPU Fan      : 2274 RPM            ║
╚════════════════════════════════════════╝
```

## Before you start

The GPU section needs a working NVIDIA driver, and the fan duty readings need
the Tuxedo modules loaded:

```bash
nvidia-smi
lsmod | grep tuxedo
```

If either fails, fix that first —
[restore NVIDIA after a kernel upgrade](restore-nvidia-after-a-kernel-upgrade.md)
and
[unlock the keyboard backlight and touchpad](unlock-keyboard-backlight-and-touchpad.md)
cover them. The dashboard degrades gracefully and prints `N/A` rather than
failing, so it is still usable without them.

## Fix

### 1. Create the script

```bash
sudo tee /usr/local/bin/temps << 'EOF'
#!/usr/bin/env python3
"""Monster TULPAR T6 V2.1 - complete thermal/fan status"""
import os, subprocess, struct, ctypes, fcntl

def read(path, default="N/A"):
    try: return open(path).read().strip()
    except: return default

def mktemp(milli):
    return f"{int(milli)/1000:.1f}C" if str(milli).lstrip("-").isdigit() else "N/A"

def mkrpm(v):
    return f"{v} RPM" if str(v).isdigit() else "N/A"

def _IOC(d, t, n, s): return (d << 30) | (s << 16) | (t << 8) | n
ps = ctypes.sizeof(ctypes.c_void_p)
R_CL_FANINFO1 = _IOC(2, 0xED, 0x10, ps)
R_CL_FANINFO2 = _IOC(2, 0xED, 0x11, ps)

def ec_fans():
    try:
        fd = open("/dev/tuxedo_io", "rb+", buffering=0)
        def rd(code):
            buf = ctypes.create_string_buffer(8)
            fcntl.ioctl(fd, code, buf)
            return struct.unpack("i", buf[:4])[0]
        v1, v2 = rd(R_CL_FANINFO1), rd(R_CL_FANINFO2)
        fd.close()
        d1 = min(100, (v1 & 0xFF) * 100 // 255)
        d2 = min(100, (v2 & 0xFF) * 100 // 255)
        return d1, d2
    except:
        return None, None

def gpu():
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,fan.speed,power.draw,clocks.current.graphics",
             "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL).strip()
        parts = [x.strip() for x in out.split(",")]
        return {"temp": parts[0], "fan": parts[1], "power": parts[2], "clock": parts[3]}
    except:
        return None

def row(label, value):
    line = f"  {label:<14}: {value}"
    print(f"║{line:<38}║")

# Detect correct coretemp hwmon index
ct_hwmon = None
for d in os.listdir("/sys/class/hwmon"):
    n = read(f"/sys/class/hwmon/{d}/name")
    if n == "coretemp":
        ct_hwmon = d
        break

pkg = mktemp(read(f"/sys/class/hwmon/{ct_hwmon}/temp1_input", "0")) if ct_hwmon else "N/A"
cores = []
if ct_hwmon:
    for i in range(2, 40):
        v = read(f"/sys/class/hwmon/{ct_hwmon}/temp{i}_input")
        if v != "N/A":
            cores.append(int(v) // 1000)

# NVMe - find by name
nv_temps = []
for d in sorted(os.listdir("/sys/class/hwmon")):
    if read(f"/sys/class/hwmon/{d}/name") == "nvme":
        nv_temps.append(mktemp(read(f"/sys/class/hwmon/{d}/temp1_input", "0")))

# Fans via ACPI hwmon
fan_devices = []
for d in sorted(os.listdir("/sys/class/hwmon")):
    if read(f"/sys/class/hwmon/{d}/name") == "acpi_fan":
        rpm = read(f"/sys/class/hwmon/{d}/fan1_input")
        fan_devices.append(rpm)

fan_labels = ["CPU Fan", "DGPU Fan"]
d1, d2 = ec_fans()
ec_duties = [d1, d2]

g = gpu()

print("╔════════════════════════════════════════╗")
print("║  Monster TULPAR T6 V2.1 - Thermals    ║")
print("╠════════════════════════════════════════╣")
row("CPU Package", pkg)
if cores:
    row("CPU Max Core", f"{max(cores)}C")
for i, t in enumerate(nv_temps):
    row(f"NVMe {i}", t)
print("╠════════════════════════════════════════╣")
if g:
    row("GPU Temp", f"{g['temp']}C")
    fan_str = f"{g['fan']}%" if g['fan'] != '[N/A]' else "EC-controlled"
    row("GPU Fan (smi)", fan_str)
    row("GPU Power", f"{g['power']}W")
    row("GPU Clock", f"{g['clock']}MHz")
else:
    row("GPU", "nvidia-smi N/A")
print("╠════════════════════════════════════════╣")
for i, rpm in enumerate(fan_devices):
    label = fan_labels[i] if i < len(fan_labels) else f"Fan {i+1}"
    duty = ec_duties[i]
    duty_str = f" ({duty}% EC)" if duty is not None else ""
    row(label, f"{rpm} RPM{duty_str}")
print("╚════════════════════════════════════════╝")
EOF
```

### 2. Make it executable

```bash
sudo chmod +x /usr/local/bin/temps
```

## Verify

```bash
temps
```

Every row should carry a number rather than `N/A`.

## Roll back

```bash
sudo rm /usr/local/bin/temps
```

## Troubleshooting

**The GPU section shows `nvidia-smi N/A`**

The NVIDIA driver is not loaded. See
[restore NVIDIA after a kernel upgrade](restore-nvidia-after-a-kernel-upgrade.md).

**Fan RPMs are missing or all read `N/A`**

The Tuxedo modules are not loaded:

```bash
lsmod | grep tuxedo
```

If nothing is listed, see
[unlock the keyboard backlight and touchpad](unlock-keyboard-backlight-and-touchpad.md).
