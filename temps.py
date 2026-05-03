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
