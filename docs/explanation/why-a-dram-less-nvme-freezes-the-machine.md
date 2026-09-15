# Why a DRAM-less NVMe freezes the machine

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (GOODRAM PX600 1TB,
`SSDPR-PX600-1K0-80`, Phison PS5021-E21)
**Verified on:** Ubuntu 26.04 · kernel 7.0 · 2026-07-05
**See also:** [stop random hard freezes from PCIe ASPM](../how-to/stop-random-hard-freezes-from-pcie-aspm.md)

## In short

The drive's controller sometimes never wakes from the PCIe ASPM L1 link state.
On any other disk that is an I/O error you can recover from; on the root disk
the kernel loses the ability to page in code or write logs, so the machine
stops dead and leaves nothing behind to explain why.

## The mechanism

ASPM is the power state of the PCIe *link*, not of the drive. When the link
has been idle, the controller is asked to bring it back up — and the Phison
E21 in this DRAM-less PX600 occasionally does not answer.

Everything the kernel would normally do at that point requires the disk it
just lost. It cannot page in the code to handle the error. It cannot write the
journal entry recording it. The display stops updating, SysRq is dead, VT
switching does nothing, and only the power button responds.

This is also why the logs are empty. The journal has no cause recorded in it
because the device needed to record the cause was the casualty. An empty
journal after a freeze is evidence, not an absence of it.

## How this was diagnosed

One panic did survive, in the EFI pstore under `/var/lib/systemd/pstore/`, and
it pointed the wrong way. It read as textbook memory corruption: a `list_del
corruption` splat with a single-nibble pointer difference — precisely the
signature of a bad DIMM. Two full passes each of memtest86+ and memtester came
back clean.

**That is the finding worth carrying away: if your freeze logs look like
memory corruption but memtest is clean, check the disk's link power management
before you buy new DIMMs.** A storage controller that dies mid-operation can
corrupt kernel structures on its way out, and the wreckage looks exactly like
failing RAM.

The confirming signal is subtler than the panic. The drive reports perfectly
healthy over SMART, because it is healthy — it hangs, it does not die. What
climbs with every freeze is the unsafe shutdown counter.

## What does not fix it

- `nvme_core.default_ps_max_latency_us=0` disables **APST**, the drive's own
  internal power states. ASPM is the *link's* power state. This parameter
  never touches it, and changing it changes nothing.
- SMART health checks. The drive passes them during and after every freeze.

## What the fix actually buys

Since `pcie_aspm=off` was applied on 2026-07-05: zero freezes.

The `I/O ... timeout, completion polled` lines still turn up occasionally, so
the controller still stalls. The difference is that with ASPM off it recovers
instead of taking the system down with it. This is mitigation, not a cure.

If the freezes ever return, the escalation path is a GOODRAM/Phison firmware
update (the updater is Windows-only; this drive is on `ELFMH0.1`), disabling
VMD in the BIOS, or moving the root filesystem to a different SSD.
