#!/bin/bash
# Monster Notebook GPU PRIME Fix
# Problem: Everything renders on Intel iGPU ("CPU") instead of the RTX 4070
# Root cause: PRIME profile defaults to "on-demand" — Intel drives the display,
#             NVIDIA is idle and only activated per-app.
# Fix: Switch PRIME to "nvidia" mode so RTX 4070 drives all rendering.
# REQUIRES REBOOT to take effect.

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }

[ "$(id -u)" -ne 0 ] && error "Run with sudo: sudo bash fix_gpu_prime.sh"

echo ""
echo "Monster Notebook GPU PRIME Fix"
echo "==============================="
echo ""

CURRENT=$(prime-select query 2>/dev/null || echo "unknown")
info "Current PRIME profile: $CURRENT"

if [ "$CURRENT" = "nvidia" ]; then
    warn "Already set to nvidia mode."
    glxinfo 2>/dev/null | grep "OpenGL renderer" || true
    echo ""
    echo "If the GPU is still not active, a reboot is needed."
    exit 0
fi

# Ensure nvidia_drm modeset is enabled (required for Wayland)
if ! grep -r "modeset=1" /etc/modprobe.d/ &>/dev/null; then
    info "Enabling nvidia_drm modeset..."
    echo "options nvidia_drm modeset=1" > /etc/modprobe.d/nvidia-graphics-drivers-kms.conf
fi

info "Switching PRIME profile to nvidia..."
prime-select nvidia

echo ""
echo -e "${GREEN}Done.${NC}"
echo ""
echo "REBOOT REQUIRED. After reboot, verify with:"
echo "  glxinfo | grep 'OpenGL renderer'"
echo "  # Should show: NVIDIA GeForce RTX 4070 Laptop GPU"
echo ""
echo "To switch back to power-saving mode (Intel only):"
echo "  sudo prime-select on-demand && reboot"
