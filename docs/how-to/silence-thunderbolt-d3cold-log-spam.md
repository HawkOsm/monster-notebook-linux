# Silence Thunderbolt D3cold log spam

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 with a Thunderbolt 4 dock (Intel Goshen
Ridge bridges, PCI ID `8086:0b26`)
**Verified on:** Ubuntu 26.04 · kernel 7.0 · 2026-07-05
**Symptom:** the journal repeats `pcieport ... Unable to change power state
from D3cold to D0, device inaccessible`.
**See also:** [stop random hard freezes from PCIe ASPM](stop-random-hard-freezes-from-pcie-aspm.md)

These messages are the dock's Goshen Ridge bridges failing to wake from
D3cold. They are noisy and harmless. This was found while chasing the NVMe
freezes and is unrelated to them — silencing it fixes the log, not a fault.

## Confirm the diagnosis

Check that the complaining devices really are the dock's bridges:

```bash
journalctl -k | grep "D3cold to D0"
lspci -nn | grep 0b26
```

## Fix

### 1. Stop the bridges entering D3cold

```bash
sudo tee /etc/udev/rules.d/99-tb-bridge-no-d3cold.rules <<'RULE'
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x8086", ATTR{device}=="0x0b26", ATTR{d3cold_allowed}="0"
RULE
```

Reboot.

## Verify

```bash
journalctl -k -b | grep -c "D3cold to D0"
# expect: 0
```

## Roll back

```bash
sudo rm /etc/udev/rules.d/99-tb-bridge-no-d3cold.rules
```

Reboot.

## Trade-offs

The bridges no longer reach their deepest power state, which costs a little
idle power while the dock is attached.
