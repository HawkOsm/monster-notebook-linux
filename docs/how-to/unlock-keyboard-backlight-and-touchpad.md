# Unlock the keyboard backlight and touchpad

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator); any Monster SKU reporting
a `MONSTER` DMI vendor
**Verified on:** Ubuntu 24.04 · kernel 6.17+ · Arch Linux · kernel 7.1.8 ·
`tuxedo-drivers` 4.22.2 · 2026-08-13
**Symptom:** the keyboard backlight is dead or stuck off, and the touchpad is
disabled and will not toggle with `Fn`+`F1`. `modprobe tuxedo_keyboard` fails
with `No such device`.
**See also:** [why `tuxedo-drivers` reject Monster hardware](../explanation/why-tuxedo-drivers-reject-monster-hardware.md),
[keyboard backlight controls](../reference/keyboard-backlight-controls.md)

Patch the driver's vendor check so it accepts `MONSTER`, rebuild it, and load
the modules at boot. On most Monster machines this is the first thing you will
need after installing Linux.

Steps 1 to 6 are always required. Steps 7 and 8 unlock a touchpad that is
stuck at the EC level — check first, because not every board is affected.

## Before you start

Confirm the machine reports the vendor string this guide is about:

```bash
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
```

## Fix

### 1. Install the driver package

**Ubuntu** needs the Tuxedo repository first. Skip this if you already have it:

```bash
curl -s https://deb.tuxedocomputers.com/ubuntu/dists/noble/Release.gpg \
  | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/tuxedo.gpg > /dev/null

echo "deb https://deb.tuxedocomputers.com/ubuntu noble main" \
  | sudo tee /etc/apt/sources.list.d/tuxedo.list

sudo apt-get update
```

```bash
sudo apt-get install -y tuxedo-drivers-dkms
```

**Arch** has it in the AUR, and needs no extra repository. This pulls
`tuxedo-drivers-dkms 4.22.2-2` — the same 4.22.2 the patch below was written
against, so it applies verbatim:

```bash
yay -S --needed tuxedo-drivers-dkms tuxedo-control-center-bin
```

Use `tuxedo-control-center-bin` rather than the source package to avoid
compiling Electron. It ships `tccd.service` pre-enabled, so no separate
systemd setup is needed.

Either way the source lands in the same place:

```text
/usr/src/tuxedo-drivers-4.22.2/tuxedo_compatibility_check/tuxedo_compatibility_check.c
```

### 2. Patch the DMI compatibility check

Find this block in the file above:

```c
	{
		.matches = {
			DMI_MATCH(DMI_CHASSIS_VENDOR, "TUXEDO"),
		},
	},
	{ }
};
```

Replace it with this, adding the `MONSTER` match:

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

Or apply it without an editor:

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

### 3. Rebuild the DKMS module

```bash
KERNEL=$(uname -r)
sudo dkms unbuild tuxedo-drivers/4.22.2 -k "$KERNEL"
sudo dkms build   tuxedo-drivers/4.22.2 -k "$KERNEL"
sudo dkms install tuxedo-drivers/4.22.2 -k "$KERNEL" --force
```

### 4. Load the modules at boot

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

### 5. Load the modules now

```bash
sudo modprobe -r tuxedo_keyboard tuxedo_compatibility_check 2>/dev/null || true
sudo modprobe tuxedo_keyboard
for m in clevo_acpi clevo_wmi tuxedo_io ite_829x; do
  sudo modprobe "$m" 2>/dev/null || true
done
```

Load each module separately, as above. Plain `modprobe` accepts only **one**
module name — anything after it is parsed as module *parameters*, not as more
modules. A one-liner such as
`sudo modprobe clevo_acpi clevo_wmi tuxedo_io ite_829x` silently loads only
`clevo_acpi`, and the trailing `2>/dev/null || true` hides the failure.
Confirmed with `lsmod`: the other three never loaded.

### 6. Turn the backlight on

```bash
cat /sys/class/leds/rgb:kbd_backlight/max_brightness \
  | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
```

If the sysfs path does not exist yet, it appears after a reboot once the
modules load correctly.

### 7. Check whether the touchpad is actually stuck

The EC has a hardware-level touchpad enable flag that survives reboots, and it
can be stranded at `0` when the driver fails to load. Not every board routes
the touchpad through it: on the Arch install the flag read `0` while the
touchpad worked normally throughout, because `FTCS1000:01 2808:0222` is a
generic `i2c_hid` device that is not gated by `tuxedo_io` at all.

If your touchpad works, skip to step 9. If it is dead, unlock it:

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

### 8. Re-enable the touchpad on every boot

Only needed if step 7 found a stuck flag.

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

### 9. Rebuild the initramfs and reboot

**Ubuntu:**

```bash
sudo update-initramfs -u -k "$(uname -r)"
sudo reboot
```

**Arch** rebuilds the initcpio automatically through `yay`'s pacman hook on
DKMS install, so a reboot is only needed if you did not load the modules live
in step 5.

## Verify

```bash
# Keyboard backlight sysfs should exist
cat /sys/class/leds/rgb:kbd_backlight/brightness

# Tuxedo modules should be loaded
lsmod | grep tuxedo

# Touchpad service should be active
systemctl status tuxedo-touchpad-enable.service
```

## Roll back

```bash
sudo systemctl disable --now tuxedo-touchpad-enable.service
sudo rm -f /etc/systemd/system/tuxedo-touchpad-enable.service \
           /usr/local/bin/tuxedo-touchpad-enable.py
sudo rm -f /etc/modules-load.d/tuxedo.conf
sudo systemctl daemon-reload
```

Then remove the driver package — `sudo apt-get remove tuxedo-drivers-dkms` on
Ubuntu, `yay -R tuxedo-drivers-dkms` on Arch — which discards the patched
source tree along with it. Rebuild the initramfs and reboot.

## Troubleshooting

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': No such device`**

The patch was not applied, or DKMS reused a cached build. Force a clean
rebuild:

```bash
sudo dkms unbuild tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms build   tuxedo-drivers/4.22.2 -k $(uname -r)
sudo dkms install tuxedo-drivers/4.22.2 -k $(uname -r) --force
```

**`modprobe: ERROR: could not insert 'tuxedo_keyboard': Operation not permitted`**

Kernel lockdown may be active:

```bash
cat /sys/kernel/security/lockdown
# expect: [none]
```

**Touchpad still locked after reboot**

```bash
systemctl status tuxedo-touchpad-enable.service
sudo python3 /usr/local/bin/tuxedo-touchpad-enable.py
```

**The backlight is off at every boot even though control works**

TCC saves the last applied state in `/etc/tcc/settings` under
`keyboardBacklightStates`. A stored `brightness: 0` means the LED comes up
dark every time. Move the slider once in TCC and the daemon writes the new
value back. To bootstrap from the command line:

```bash
echo 200 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
# Then in TCC: Tools → Keyboard Backlight → nudge the slider so tccd saves it.
```

Then nudge the slider in **Tools → Keyboard Backlight** so `tccd` saves it.
