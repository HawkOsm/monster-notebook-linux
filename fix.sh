#!/bin/bash
# Monster Notebook (Clevo) Ubuntu Fix Script
# Tested on: Monster TULPAR T6 V2.1, Ubuntu 24.04, Kernel 6.17+
# Fixes: Keyboard backlight, touchpad lock, NVIDIA driver for new kernels

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }

[ "$(id -u)" -ne 0 ] && error "Run with sudo: sudo bash fix.sh"

KERNEL=$(uname -r)
SRC="/usr/src/tuxedo-drivers-4.22.2/tuxedo_compatibility_check/tuxedo_compatibility_check.c"

echo ""
echo "Monster Notebook Linux Driver Fix"
echo "Kernel: $KERNEL"
echo "=================================="
echo ""

# ── Step 1: Install tuxedo-drivers if missing ─────────────────────────────────
if [ ! -f "$SRC" ]; then
    warn "tuxedo-drivers-4.22.2 source not found. Installing from Tuxedo repo..."
    if ! grep -r "tuxedocomputers.com" /etc/apt/sources.list /etc/apt/sources.list.d/ &>/dev/null; then
        curl -s https://deb.tuxedocomputers.com/ubuntu/dists/noble/Release.gpg \
          | gpg --dearmor | tee /etc/apt/trusted.gpg.d/tuxedo.gpg > /dev/null
        echo "deb https://deb.tuxedocomputers.com/ubuntu noble main" \
          > /etc/apt/sources.list.d/tuxedo.list
    fi
    apt-get update -q
    apt-get install -y tuxedo-drivers-dkms
fi

[ ! -f "$SRC" ] && error "Source still missing at $SRC — cannot continue."

# ── Step 2: Patch the MONSTER DMI compatibility check ─────────────────────────
info "Patching tuxedo_compatibility_check for MONSTER DMI..."

if grep -q '"MONSTER"' "$SRC"; then
    info "Already patched — skipping."
else
    python3 - "$SRC" << 'PYEOF'
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
PYEOF
fi

# ── Step 3: Rebuild DKMS ───────────────────────────────────────────────────────
info "Rebuilding tuxedo-drivers DKMS for kernel $KERNEL..."
dkms unbuild tuxedo-drivers/4.22.2 -k "$KERNEL" 2>/dev/null || true
dkms build   tuxedo-drivers/4.22.2 -k "$KERNEL"
dkms install tuxedo-drivers/4.22.2 -k "$KERNEL" --force

# ── Step 4: Configure modules to load at boot ─────────────────────────────────
info "Configuring modules for autoload at boot..."
cat > /etc/modules-load.d/tuxedo.conf << EOF
tuxedo_compatibility_check
tuxedo_keyboard
clevo_acpi
clevo_wmi
tuxedo_io
ite_829x
EOF

# ── Step 5: Load modules now ───────────────────────────────────────────────────
info "Loading modules..."
modprobe -r tuxedo_keyboard tuxedo_compatibility_check 2>/dev/null || true
modprobe tuxedo_keyboard
modprobe clevo_acpi clevo_wmi tuxedo_io ite_829x 2>/dev/null || true

# ── Step 6: Set keyboard backlight to max ─────────────────────────────────────
info "Setting keyboard backlight to full brightness..."
BACKLIGHT="/sys/class/leds/rgb:kbd_backlight/brightness"
MAX="/sys/class/leds/rgb:kbd_backlight/max_brightness"
if [ -f "$BACKLIGHT" ] && [ -f "$MAX" ]; then
    cat "$MAX" > "$BACKLIGHT"
    echo "  Brightness set to $(cat $BACKLIGHT)/$(cat $MAX)"
else
    warn "Backlight sysfs not found yet — may appear after reboot."
fi

# ── Step 7: Unlock touchpad via EC ────────────────────────────────────────────
info "Unlocking touchpad via Embedded Controller..."
python3 - << 'PYEOF'
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
PYEOF

# ── Step 8: Install persistent touchpad-enable service ───────────────────────
info "Installing touchpad-enable systemd service..."
cat > /usr/local/bin/tuxedo-touchpad-enable.py << 'PYEOF'
#!/usr/bin/env python3
import fcntl, ctypes, struct, time, sys
def _IOC(d,t,n,s): return (d<<30)|(s<<16)|(t<<8)|n
W_TP = _IOC(1, 0xEE, 0x14, ctypes.sizeof(ctypes.c_void_p))
for _ in range(5):
    try:
        fd = open("/dev/tuxedo_io","rb+",buffering=0)
        fcntl.ioctl(fd, W_TP, ctypes.create_string_buffer(struct.pack("i",1)+b'\x00'*4))
        fd.close(); sys.exit(0)
    except: time.sleep(1)
sys.exit(1)
PYEOF
chmod +x /usr/local/bin/tuxedo-touchpad-enable.py

cat > /etc/systemd/system/tuxedo-touchpad-enable.service << 'EOF'
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
systemctl daemon-reload
systemctl enable tuxedo-touchpad-enable.service

# ── Step 9: Update initramfs ───────────────────────────────────────────────────
info "Updating initramfs..."
update-initramfs -u -k "$KERNEL" 2>&1 | grep -v "^W:" || true

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Status:"
BRIGHT=$(cat /sys/class/leds/rgb:kbd_backlight/brightness 2>/dev/null || echo "N/A")
MAX_B=$(cat /sys/class/leds/rgb:kbd_backlight/max_brightness 2>/dev/null || echo "N/A")
echo "  Keyboard backlight : $BRIGHT / $MAX_B"
echo "  Modules loaded     : $(lsmod | grep -c tuxedo)"
echo ""
echo "Reboot recommended to confirm everything loads cleanly from boot."
