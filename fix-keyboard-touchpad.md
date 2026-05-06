# Fix: Keyboard Backlight & Touchpad Locked

**Symptoms:** Keyboard backlight is dead or stuck off. Touchpad is disabled and cannot be toggled with `Fn`+`F1`.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+

---

## Why This Happens

### Keyboard Backlight

The `tuxedo-drivers` package controls the Clevo keyboard hardware. It contains a compatibility gate that only allows itself to load on systems where the DMI vendor string is exactly `"TUXEDO"`. Monster notebooks report `"MONSTER"` — so the driver refuses to initialize and exits silently with `No such device`.

On kernel 6.17+, an additional problem appears: the kernel ships a built-in `tuxedo_io` v0.3.9 while the DKMS package provides v0.3.6, causing a module version collision.

### Touchpad Locked

The Embedded Controller (EC) on Clevo boards has a hardware-level touchpad enable/disable flag. This flag survives reboots. When the Tuxedo driver fails to load, the EC register can get stuck at `0` (disabled) with no way to toggle it back — because the `/dev/tuxedo_io` device that controls the EC never loads.

---

## Step 1 — Add the Tuxedo Repository

Skip this step if you already have the Tuxedo repo configured.

```bash
curl -s https://deb.tuxedocomputers.com/ubuntu/dists/noble/Release.gpg \
  | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/tuxedo.gpg > /dev/null

echo "deb https://deb.tuxedocomputers.com/ubuntu noble main" \
  | sudo tee /etc/apt/sources.list.d/tuxedo.list

sudo apt-get update
```

## Step 2 — Install tuxedo-drivers-dkms

```bash
sudo apt-get install -y tuxedo-drivers-dkms
```

The source will be placed at:

```
/usr/src/tuxedo-drivers-4.22.2/tuxedo_compatibility_check/tuxedo_compatibility_check.c
```

## Step 3 — Patch the DMI Compatibility Check

The driver rejects non-TUXEDO vendors. Open the file above and find this block:

```c
	{
		.matches = {
			DMI_MATCH(DMI_CHASSIS_VENDOR, "TUXEDO"),
		},
	},
	{ }
};
```

Replace it with:

```c
	{
		.matches = {
			DMI_MATCH(DMI_CHASSIS_VENDOR, "TUXEDO"),
		},
	},
	{
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "MONSTER"),
		},
	},
	{ }
};
```

Or apply the patch with Python (no editor needed):

```bash
sudo python3 - /usr/src/tuxedo-drivers-4.22.2/tuxedo_compatibility_check/tuxedo_compatibility_check.c << 'EOF'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

old = ('\t{\n\t\t.matches = {\n\t\t\tDMI_MATCH(DMI_CHASSIS_VENDOR, "TUXEDO"),\n'
       '\t\t},\n\t},\n\t{ }\n};')
new = ('\t{\n\t\t.matches = {\n\t\t\tDMI_MATCH(DMI_CHASSIS_VENDOR, "TUXEDO"),\n'
       '\t\t},\n\t},\n\t{\n\t\t.matches = {\n\t\t\tDMI_MATCH(DMI_SYS_VENDOR, "MONSTER"),\n'
       '\t\t},\n\t},\n\t{ }\n};')

if old not in content:
    print("ERROR: Could not find insertion point. Source may differ from expected version.")
    sys.exit(1)

with open(path, 'w') as f:
    f.write(content.replace(old, new, 1))
print("Patch applied.")
EOF
```

## Step 4 — Rebuild the DKMS Module

```bash
KERNEL=$(uname -r)
sudo dkms unbuild tuxedo-drivers/4.22.2 -k "$KERNEL"
sudo dkms build   tuxedo-drivers/4.22.2 -k "$KERNEL"
sudo dkms install tuxedo-drivers/4.22.2 -k "$KERNEL" --force
```

## Step 5 — Configure Modules to Load at Boot

```bash
sudo tee /etc/modules-load.d/tuxedo.conf << 'EOF'
tuxedo_compatibility_check
tuxedo_keyboard
clevo_acpi
clevo_wmi
tuxedo_io
ite_829x
EOF
```

## Step 6 — Load the Modules Now

```bash
sudo modprobe -r tuxedo_keyboard tuxedo_compatibility_check 2>/dev/null || true
sudo modprobe tuxedo_keyboard
sudo modprobe clevo_acpi clevo_wmi tuxedo_io ite_829x 2>/dev/null || true
```

## Step 7 — Set Keyboard Backlight to Full Brightness

```bash
cat /sys/class/leds/rgb:kbd_backlight/max_brightness \
  | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
```

If the sysfs path is missing, it will appear after reboot once the modules load correctly.

## Step 8 — Unlock the Touchpad via EC

```bash
sudo python3 << 'EOF'
import fcntl, ctypes, struct, time, sys

def _IOC(d, t, n, s): return (d << 30) | (s << 16) | (t << 8) | n
ptr = ctypes.sizeof(ctypes.c_void_p)
R_TP = _IOC(2, 0xED, 0x15, ptr)
W_TP = _IOC(1, 0xEE, 0x14, ptr)

for _ in range(5):
    try:
        fd = open("/dev/tuxedo_io", "rb+", buffering=0)
        buf = ctypes.create_string_buffer(8)
        fcntl.ioctl(fd, R_TP, buf)
        state = struct.unpack("i", buf[:4])[0]
        if state == 0:
            print(f"  EC touchpad state was: {state} (disabled) — enabling...")
            wb = ctypes.create_string_buffer(struct.pack("i", 1) + b'\x00'*4)
            fcntl.ioctl(fd, W_TP, wb)
            fcntl.ioctl(fd, R_TP, buf)
            print(f"  EC touchpad state now: {struct.unpack('i', buf[:4])[0]} (1=enabled)")
        else:
            print(f"  Touchpad EC state: {state} (already enabled)")
        fd.close()
        sys.exit(0)
    except Exception as e:
        time.sleep(1)
print("  Could not reach tuxedo_io — touchpad state unchanged.")
EOF
```

## Step 9 — Install a Persistent Touchpad-Enable Service

This service re-enables the touchpad automatically on every boot.

**Create the helper script:**

```bash
sudo tee /usr/local/bin/tuxedo-touchpad-enable.py << 'EOF'
#!/usr/bin/env python3
import fcntl, ctypes, struct, time, sys

def _IOC(d, t, n, s): return (d << 30) | (s << 16) | (t << 8) | n
W_TP = _IOC(1, 0xEE, 0x14, ctypes.sizeof(ctypes.c_void_p))

for _ in range(5):
    try:
        fd = open("/dev/tuxedo_io", "rb+", buffering=0)
        fcntl.ioctl(fd, W_TP, ctypes.create_string_buffer(struct.pack("i", 1) + b'\x00'*4))
        fd.close()
        sys.exit(0)
    except:
        time.sleep(1)
sys.exit(1)
EOF
sudo chmod +x /usr/local/bin/tuxedo-touchpad-enable.py
```

**Create the systemd service:**

```bash
sudo tee /etc/systemd/system/tuxedo-touchpad-enable.service << 'EOF'
[Unit]
Description=Enable Clevo/MONSTER touchpad via EC
After=systemd-modules-load.service
Requires=systemd-modules-load.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/tuxedo-touchpad-enable.py
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tuxedo-touchpad-enable.service
```

## Step 10 — Update initramfs and Reboot

```bash
sudo update-initramfs -u -k "$(uname -r)"
sudo reboot
```

---

## Verify After Reboot

```bash
# Keyboard backlight sysfs should exist
cat /sys/class/leds/rgb:kbd_backlight/brightness

# Tuxedo modules should be loaded
lsmod | grep tuxedo

# Touchpad service should be active
systemctl status tuxedo-touchpad-enable.service
```

---

## Manual Keyboard Backlight Controls

```bash
# Check current brightness (0–255)
cat /sys/class/leds/rgb:kbd_backlight/brightness

# Set brightness (replace 200 with any value 0–255)
echo 200 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness

# Turn off
echo 0 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
```

Keyboard shortcuts (hold `Fn`):

| Keys | Action |
|------|--------|
| `Fn` + `/` | Toggle backlight on/off |
| `Fn` + `*` | Cycle colors |
| `Fn` + `+` | Brightness up |
| `Fn` + `-` | Brightness down |

---

## Troubleshooting

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': No such device`**

The compatibility patch wasn't applied or the DKMS rebuild used a cached build. Force a clean rebuild:

```bash
sudo dkms unbuild tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms build   tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms install tuxedo-drivers/4.22.2 -k $(uname -r) --force
```

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': Operation not permitted`**

Kernel lockdown may be active. Check:

```bash
cat /sys/kernel/security/lockdown
# Should read [none]
```

**Touchpad still locked after reboot**

Check the service status and re-run manually:

```bash
systemctl status tuxedo-touchpad-enable.service
sudo python3 /usr/local/bin/tuxedo-touchpad-enable.py
```
