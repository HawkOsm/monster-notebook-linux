# Thermal sensor sources

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator)
**Verified on:** Ubuntu 26.04 · kernel 7.0 · 2026-08-13
**See also:** [install the thermal dashboard](../how-to/install-the-thermal-dashboard.md)

Where each temperature and fan reading on this machine actually comes from.

| Sensor | Source | Notes |
|--------|--------|-------|
| CPU package + all cores | `coretemp` hwmon | Working natively |
| Both NVMe drives | `nvme` hwmon | Working natively |
| CPU Fan RPM | ACPI hwmon (`INTC1063:00`) | Working natively |
| DGPU Fan RPM | ACPI hwmon (`INTC1063:01`) | Working natively |
| GPU temperature | `nvidia-smi` | Requires NVIDIA driver loaded |
| GPU power & clock | `nvidia-smi` | Requires NVIDIA driver loaded |
| Fan duty percent | `/dev/tuxedo_io` ioctl | Requires `tuxedo-drivers` loaded |

The ITE IT5570E embedded controller, chip ID `0x5570`, is not supported by the
standard `it87` kernel module. Fan RPM comes from ACPI hwmon instead, which is
accurate. Fan PWM control stays with the EC firmware and TUXEDO Control
Center.
