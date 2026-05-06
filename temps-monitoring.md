# Temperature & Fan Monitoring

A thermal dashboard for the Monster TULPAR T6 V2.1 that reads CPU/GPU temperatures, NVMe drive temps, and fan RPMs from the correct hardware sources.

**Requires:** NVIDIA driver working (`nvidia-smi` functional) and `tuxedo-drivers` loaded (see [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md)).

---

## What It Shows

```
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

---

## Sensor Sources

| Sensor | Source | Notes |
|--------|--------|-------|
| CPU package + all cores | `coretemp` hwmon | Working natively |
| Both NVMe drives | `nvme` hwmon | Working natively |
| CPU Fan RPM | ACPI hwmon (`INTC1063:00`) | Working natively |
| DGPU Fan RPM | ACPI hwmon (`INTC1063:01`) | Working natively |
| GPU temperature | `nvidia-smi` | Requires NVIDIA driver loaded |
| GPU power & clock | `nvidia-smi` | Requires NVIDIA driver loaded |

> **Note:** The ITE IT5570E embedded controller (chip ID `0x5570`) is not supported by the standard `it87` kernel module. Fan RPM is read via ACPI hwmon which is accurate. Fan PWM control is handled by the EC firmware and the Tuxedo Control Center.

---

## Installation

**1. Create the script file:**

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

**2. Make it executable:**

```bash
sudo chmod +x /usr/local/bin/temps
```

**3. Run it:**

```bash
temps
```

---

## Troubleshooting

**GPU section shows `nvidia-smi N/A`**

The NVIDIA driver is not loaded. See [fix-nvidia.md](fix-nvidia.md).

**Fan RPMs missing or all showing `N/A`**

The Tuxedo modules must be loaded:

```bash
lsmod | grep tuxedo
```

If missing, see [fix-keyboard-touchpad.md](fix-keyboard-touchpad.md).
