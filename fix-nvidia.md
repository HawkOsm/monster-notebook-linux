# Fix: NVIDIA Driver After Kernel Upgrade

**Symptom:** `nvidia-smi` fails with `couldn't communicate with the NVIDIA driver` after upgrading to a new kernel.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+

---

## Why This Happens

Ubuntu ships pre-built NVIDIA kernel module packages keyed per kernel version. When you jump to a new kernel (e.g. `6.17.0-23`), the matching package (`linux-modules-nvidia-580-open-6.17.0-23-generic`) must be installed.

If you have the Tuxedo apt repository enabled, its epoch-versioned NVIDIA packages (`2:580.126.09`) block apt from upgrading to Ubuntu's newer `580.142` build — which is what the per-kernel package depends on.

---

## Step 1 — Pin Ubuntu's NVIDIA Packages Above the Tuxedo Repo Epoch

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

## Step 2 — Update the Package Cache

```bash
sudo apt-get update
```

## Step 3 — Verify the Correct Candidate is Selected

```bash
apt-cache policy nvidia-kernel-common-580 | grep Candidate
# Expected: 580.142-0ubuntu0.24.04.1
```

If a different version appears, the pin from Step 1 may not have taken effect. Double-check `/etc/apt/preferences.d/nvidia-ubuntu-pin`.

## Step 4 — Upgrade the NVIDIA Stack to 580.142

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

## Step 5 — Install the Per-Kernel Module Package

```bash
sudo apt-get install -y "linux-modules-nvidia-580-open-$(uname -r)"
```

## Step 6 — Load the Module and Verify

```bash
sudo modprobe nvidia
nvidia-smi
```

If `nvidia-smi` still shows an error, a reboot is required to fully swap out the kernel module:

```bash
sudo reboot
```

---

## Verify After Reboot

```bash
nvidia-smi
# Should display the GPU info table without errors
```

---

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
