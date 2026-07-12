# Fix: Random Hard Freezes — DRAM-less NVMe + PCIe ASPM

**Symptom:** the whole machine hard-freezes at random — display frozen, no
cursor, no VT switch, no SysRq, nothing in the journal (it just stops
mid-line). Rare (weeks apart), tends to happen while the machine sits idle
or shortly after a resume from suspend. Power-cycle is the only way out.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 26.04 · Kernel 7.0 · root disk
GOODRAM PX600 1TB (`SSDPR-PX600-1K0-80`, Phison PS5021-E21, DRAM-less) behind
Intel VMD

---

## Why This Happens

The PX600's Phison E21 controller is **DRAM-less**, and its links negotiate
**PCIe ASPM L1** (low-power link state). When the link has been idle and the
kernel asks the drive to wake from L1, the controller sometimes doesn't come
back. On any other device that's an I/O error; on the **root disk** it means
the kernel can't page in code, can't write logs, can't do anything — a total
silent freeze. That's why the journal never shows a cause: the disk needed to
record the cause was the casualty.

The trap in diagnosing it: the one panic that did survive (in EFI pstore —
`/var/lib/systemd/pstore/`) looked exactly like RAM corruption (`list_del
corruption`, a single-nibble pointer difference). Two full memtest86+ /
memtester passes said the RAM was fine. If your freeze logs look like memory
corruption but memtest is clean, check the disk's link power management before
buying new DIMMs.

Two things that do NOT fix it, in case you've already tried:

- `nvme_core.default_ps_max_latency_us=0` — disables **APST** (the drive's
  internal power states). ASPM is the *link's* power state; this parameter
  doesn't touch it.
- SMART checks — the drive reports perfectly healthy (it is; it hangs, it
  doesn't die). The tell is the **unsafe shutdown counter** climbing with each
  freeze.

## Confirming You Have This Problem

```bash
# 1. NVMe timeouts that recover — the smoking gun, often minutes after boot:
journalctl -k | grep -E "nvme.*timeout"
# nvme nvme1: I/O tag 321 (8141) QID 2 timeout, completion polled

# 2. ASPM L1 enabled on the NVMe link:
sudo lspci -vv | grep -B 30 "Non-Volatile" | grep "LnkCtl:"
# LnkCtl: ASPM L1 Enabled ...

# 3. Unsafe shutdown counter (compare after each freeze):
sudo nvme smart-log /dev/nvme1 | grep unsafe
```

## The Fix

**Runtime (immediate, no reboot):**

```bash
echo performance | sudo tee /sys/module/pcie_aspm/parameters/policy
```

**Persistent:** add `pcie_aspm=off` to the kernel command line:

```bash
sudo cp /etc/default/grub /etc/default/grub.bak.pre-aspm
sudo sed -i 's/^\(GRUB_CMDLINE_LINUX_DEFAULT=".*\)"/\1 pcie_aspm=off"/' /etc/default/grub
sudo update-grub
```

Verify after reboot:

```bash
cat /proc/cmdline | tr ' ' '\n' | grep aspm       # pcie_aspm=off
sudo lspci -vv | grep "LnkCtl:" | grep -c Enabled  # NVMe links: ASPM Disabled
```

> **Note (VMD):** if your BIOS has Intel VMD enabled, the NVMe links live
> behind the VMD domain (`10000:e2:00.0`-style addresses). `pcie_aspm=off`
> still reaches them — verify with `lspci -vv` as above rather than assuming.

**Trade-off:** `pcie_aspm=off` disables link power management on *every* PCIe
device, costing some idle battery. Once you trust the diagnosis you can try
narrowing to `pcie_aspm.policy=performance` instead. The freezes were bad
enough here that the sledgehammer stays for now.

## Results (this machine)

- Since applying (2026-07-05): **zero freezes**.
- The `I/O ... timeout, completion polled` lines still appear occasionally —
  the controller still stalls, but with ASPM off it *recovers* instead of
  taking the system down. Mitigation, not cure.
- If the freezes ever return, the escalation path: GOODRAM/Phison firmware
  update (updater is Windows-only, currently on `ELFMH0.1`), disabling VMD in
  BIOS, or moving the root filesystem to a different SSD.

## Bonus Fixes From the Same Investigation

**Boots got ~10 s slower after every freeze.** GRUB sets a "recordfail" flag
when the previous boot didn't complete cleanly, and then shows the menu for
`GRUB_RECORDFAIL_TIMEOUT` (default 10 s on Ubuntu, even with a hidden menu).
Every hard freeze = one slow boot. Trim it in `/etc/default/grub`:

```
GRUB_RECORDFAIL_TIMEOUT=2
```

then `sudo update-grub`.

**`pcieport ... Unable to change power state from D3cold to D0, device
inaccessible` spam** in the journal: on this machine that's the Thunderbolt 4
dock's Goshen Ridge bridges failing to wake from D3cold — annoying but
harmless, and unrelated to the NVMe problem. Silenced by blocking D3cold on
those bridges via udev rule (`/etc/udev/rules.d/99-tb-bridge-no-d3cold.rules`):

```
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x8086", ATTR{device}=="0x0b26", ATTR{d3cold_allowed}="0"
```
