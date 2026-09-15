# Stop random hard freezes from PCIe ASPM

**Status:** mitigated
**Applies to:** Monster TULPAR T6 V2.1 with a DRAM-less NVMe root disk
(GOODRAM PX600 1TB, `SSDPR-PX600-1K0-80`, Phison PS5021-E21) behind Intel VMD
**Verified on:** Ubuntu 26.04 · kernel 7.0 · 2026-07-05
**Symptom:** the whole machine hard-freezes at random — display frozen, no
cursor, no VT switch, no SysRq, nothing in the journal. Rare, weeks apart,
usually while idle or shortly after resume. Only a power cycle recovers it.
**See also:** [why a DRAM-less NVMe freezes the machine](../explanation/why-a-dram-less-nvme-freezes-the-machine.md)

Stop the root disk's PCIe link from entering a low-power state it sometimes
fails to wake from.

## Confirm the diagnosis

Run all three. The first is the strongest signal — timeouts that *recovered*
are the same fault that eventually does not.

```bash
journalctl -k | grep -E "nvme.*timeout"
# expect: nvme nvme1: I/O tag 321 (8141) QID 2 timeout, completion polled
```

```bash
sudo lspci -vv | grep -B 30 "Non-Volatile" | grep "LnkCtl:"
# expect: LnkCtl: ASPM L1 Enabled ...
```

```bash
sudo nvme smart-log /dev/nvme1 | grep unsafe
```

The unsafe shutdown counter climbs by one with every freeze. Note it now and
compare after the next one. Replace `/dev/nvme1` with your own root device.

## Fix

### 1. Disable link power management now

This takes effect immediately and survives until reboot, so you can test the
diagnosis before committing to it.

```bash
echo performance | sudo tee /sys/module/pcie_aspm/parameters/policy
```

### 2. Make it persistent

```bash
sudo cp /etc/default/grub /etc/default/grub.bak.pre-aspm
sudo sed -i 's/^\(GRUB_CMDLINE_LINUX_DEFAULT=".*\)"/\1 pcie_aspm=off"/' /etc/default/grub
sudo update-grub
```

Reboot.

> **If Intel VMD is enabled in your BIOS**, the NVMe links sit behind the VMD
> domain and carry addresses like `10000:e2:00.0`. `pcie_aspm=off` still
> reaches them, but confirm it with `lspci -vv` rather than assuming.

## Verify

```bash
cat /proc/cmdline | tr ' ' '\n' | grep aspm
# expect: pcie_aspm=off
```

```bash
# Counts PCIe links still reporting ASPM enabled. The NVMe links must not
# appear among them; check them by address rather than trusting the total.
sudo lspci -vv | grep "LnkCtl:" | grep -c Enabled
```

## Roll back

```bash
sudo mv /etc/default/grub.bak.pre-aspm /etc/default/grub
sudo update-grub
```

Reboot. The runtime change from step 1 does not persist and needs no undoing.

## Trade-offs

`pcie_aspm=off` disables link power management on **every** PCIe device, not
just the disk, and costs some idle battery life. Once you trust the diagnosis
you can try narrowing it to `pcie_aspm.policy=performance`. The freezes were
bad enough on this machine that the blunt version stays.

This suppresses the symptom without fixing the controller. The stalls still
happen — they just stop being fatal.
