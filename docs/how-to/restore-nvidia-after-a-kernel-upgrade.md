# Restore NVIDIA after a kernel upgrade

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1
**Verified on:** Ubuntu 24.04 · kernel 6.17+ · 2026-08-13
**Symptom:** `nvidia-smi` fails with
`couldn't communicate with the NVIDIA driver` after upgrading to a new kernel.

Ubuntu ships NVIDIA kernel modules as per-kernel packages, so every new kernel
needs its matching one — jumping to `6.17.0-23` means installing
`linux-modules-nvidia-580-open-6.17.0-23-generic`. That
package depends on Ubuntu's `580.142` build — and the Tuxedo apt repository's
epoch-versioned `2:580.126.09` outranks it, so apt refuses the upgrade and you
are left with a driver that has no module for the running kernel. Pinning the
Ubuntu archive above that epoch restores the normal upgrade path.

## Confirm the diagnosis

```bash
nvidia-smi
# expect: couldn't communicate with the NVIDIA driver
```

```bash
# The per-kernel module package for the running kernel is missing:
dpkg -l | grep "linux-modules-nvidia.*$(uname -r)"
```

```bash
# The Tuxedo repo is winning the version race:
apt-cache policy nvidia-kernel-common-580
# expect: a 2:580.126.09 candidate from the Tuxedo repository
```

## Fix

### 1. Pin Ubuntu's NVIDIA packages above the Tuxedo repo epoch

```bash
sudo tee /etc/apt/preferences.d/nvidia-ubuntu-pin << 'EOF'
Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-updates
Pin-Priority: 1001

Package: *nvidia* libnvidia* linux-modules-nvidia* linux-objects-nvidia*
Pin: release o=Ubuntu,a=noble-security
Pin-Priority: 1001
EOF
```

> **Newer Ubuntu releases:** replace `noble` with your release's codename in
> both `Pin:` lines (26.04 = `resolute`), and adjust the version strings in the
> steps below to match `apt-cache policy`'s candidate. The pin itself — Ubuntu
> archive above the Tuxedo repo's epoch — is what matters. Verified still
> needed after the 24.04 → 26.04 upgrade.

### 2. Update the package cache

```bash
sudo apt-get update
```

### 3. Verify the correct candidate is selected

```bash
apt-cache policy nvidia-kernel-common-580 | grep Candidate
# expect: 580.142-0ubuntu0.24.04.1
```

If a different version appears, the pin from Step 1 may not have taken effect.
Double-check `/etc/apt/preferences.d/nvidia-ubuntu-pin`.

### 4. Upgrade the NVIDIA stack to 580.142

```bash
NVIDIA_VER="580.142-0ubuntu0.24.04.1"

sudo apt-get install -y --allow-downgrades \
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
```

### 5. Install the per-kernel module package

```bash
sudo apt-get install -y "linux-modules-nvidia-580-open-$(uname -r)"
```

### 6. Load the module and verify

```bash
sudo modprobe nvidia
nvidia-smi
```

If `nvidia-smi` still shows an error, a reboot is required to fully swap out the
kernel module:

```bash
sudo reboot
```

## Verify

```bash
nvidia-smi
# expect: the GPU info table without errors
```

## Roll back

Remove the pin and let the Tuxedo repository win again:

```bash
sudo rm /etc/apt/preferences.d/nvidia-ubuntu-pin
sudo apt-get update
```

The installed driver packages stay where they are until something upgrades
them. To go all the way back, reinstall the Tuxedo versions afterwards with
`apt-get install --allow-downgrades` and the `2:` epoch versions that
`apt-cache policy` now offers.

## Troubleshooting

**`apt-get install` fails due to broken dependencies**

Try adding `--fix-broken` or run:

```bash
sudo apt-get install -f
```

**Wrong candidate version after adding the pin**

Make sure there are no conflicting priority files:

```bash
apt-cache policy nvidia-kernel-common-580
grep -r nvidia /etc/apt/preferences.d/
```

**nvidia-smi still failing after reboot**

Check that the kernel module is loaded:

```bash
lsmod | grep nvidia
dmesg | grep -i nvidia
```
