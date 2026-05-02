#!/bin/bash
# Monster Notebook NVIDIA Driver Fix
# Fixes: nvidia-smi failure after kernel upgrade on Ubuntu 24.04 with Tuxedo repo
# Root cause: Tuxedo repo epoch 2: blocks Ubuntu's 580.142 update needed for new kernel modules

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }

[ "$(id -u)" -ne 0 ] && error "Run with sudo: sudo bash fix_nvidia.sh"

KERNEL=$(uname -r)
NVIDIA_VER="580.142-0ubuntu0.24.04.1"

echo ""
echo "Monster Notebook NVIDIA Fix"
echo "Kernel: $KERNEL"
echo "==========================="
echo ""

# ── Step 1: Pin Ubuntu NVIDIA packages above Tuxedo repo epoch ────────────────
info "Pinning Ubuntu NVIDIA packages to priority 1001..."
cat > /etc/apt/preferences.d/nvidia-ubuntu-pin << 'EOF'
Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-updates
Pin-Priority: 1001

Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-security
Pin-Priority: 1001
EOF

# ── Step 2: Update apt cache ───────────────────────────────────────────────────
info "Updating package cache..."
apt-get update -q

# ── Step 3: Verify 580.142 is now the candidate ───────────────────────────────
CANDIDATE=$(apt-cache policy nvidia-kernel-common-580 | grep Candidate | awk '{print $2}')
info "nvidia-kernel-common-580 candidate: $CANDIDATE"
echo "$CANDIDATE" | grep -q "580.142" || warn "Expected 580.142 but got $CANDIDATE — continuing anyway."

# ── Step 4: Upgrade NVIDIA stack to 580.142 ───────────────────────────────────
info "Upgrading NVIDIA packages to $NVIDIA_VER..."
apt-get install -y --allow-downgrades \
    nvidia-kernel-common-580="$NVIDIA_VER" \
    nvidia-driver-580-open="$NVIDIA_VER" \
    libnvidia-cfg1-580="$NVIDIA_VER" \
    libnvidia-compute-580:amd64="$NVIDIA_VER" \
    libnvidia-decode-580:amd64="$NVIDIA_VER" \
    libnvidia-encode-580:amd64="$NVIDIA_VER" \
    libnvidia-extra-580:amd64="$NVIDIA_VER" \
    libnvidia-fbc1-580:amd64="$NVIDIA_VER" \
    libnvidia-gl-580:amd64="$NVIDIA_VER" \
    nvidia-compute-utils-580="$NVIDIA_VER" \
    nvidia-utils-580="$NVIDIA_VER" \
    xserver-xorg-video-nvidia-580="$NVIDIA_VER"

# ── Step 5: Install per-kernel module package ─────────────────────────────────
info "Installing linux-modules-nvidia-580-open-$KERNEL..."
apt-get install -y "linux-modules-nvidia-580-open-$KERNEL"

# ── Step 6: Load module and verify ────────────────────────────────────────────
info "Loading nvidia module..."
modprobe nvidia 2>/dev/null || true

echo ""
nvidia-smi 2>&1 | head -12 || warn "nvidia-smi still failing — reboot may be required."
echo ""
echo -e "${GREEN}Done.${NC} If nvidia-smi still shows an error above, reboot and run: nvidia-smi"
