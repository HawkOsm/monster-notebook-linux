// SPDX-License-Identifier: GPL-2.0
// Fan/temperature integration for MONSTER ABRA A5 V20.2 via EC MMIO + ACPI thermal zone
//
// EC memory base (ECMA) = 0xFE410000 from DSDT ECMG region
// F1DC[6:0] + F1CM[7] @ offset 0xE8C  (fan1 duty + manual flag)
// F2DC[6:0] + F2CM[7] @ offset 0xE9D  (fan2 duty + manual flag)
//
// Background: TUXEDO Control Center's daemon (tccd) only populates its
// dashboard when it finds either its own "tuxedo_fan_control" platform
// device, or (failing that) a hwmon chip whose "name" file is exactly
// "tuxedo" (see FanControlWorker.getHwmonPwmPath(), which greps for
// '^tuxedo$'). On this board tccd falls back to talking to /dev/tuxedo_io
// over the clevo_wmi interface instead, and GetNumberFans() returns 0
// there (the OEM ("MONSTER") ACPI/WMI implementation doesn't answer
// CLEVO_CMD_GET_FANINFO*, the same way it doesn't answer
// CLEVO_CMD_GET_SPECS - see dmesg at boot). tccd's FanControlWorker bails
// out of its whole update cycle in that case, so it shows neither fan
// speed nor temperature, even though a real CPU temperature is available.
//
// This driver exposes a hwmon chip literally named "tuxedo" so tccd picks
// it up through its generic hwmon path instead of the broken WMI path.
//
// Temperature source: the CPU package digital thermal sensor via
// MSR_IA32_PACKAGE_THERM_STATUS (tjmax from MSR_IA32_TEMPERATURE_TARGET) -
// the same mechanism coretemp uses. The DSDT declares EC temperature bytes
// (CPUT @0xE0D, PCHT @0xE0E, SN1T-SN5T) and a fan tachometer (F1SH/F1SL
// @0xE1C/0xE1D) in the ECMG region, but on this board's firmware
// (N.1.13MON07) they all read constant 0 even under full fan load - the EC
// never populates them. The ACPI thermal zone ECTZ is synthetic too (its
// _TMP returns a formula, not a sensor read). Hence the MSR.
//
// Fan speed: a true RPM tachometer is not available (the DSDT F1SH/F1SL
// bytes are dead), so the fan channels report the current EC duty cycle
// (0-127) with fan_max=127. That is real, live data - tccd computes
// input/max*100 and displays it as fan speed percent, which is exactly
// what duty is, and matches what TCC shows on working Clevo devices
// (their WMI "fan speed" is also duty percent, not RPM). Side effect:
// lm-sensors will print the raw duty value labeled "RPM"; documented in
// fix-tuxedo-fan-temp-abra.md. PWM duty control (reverse engineered
// earlier, working) is unchanged.

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/io.h>
#include <linux/platform_device.h>
#include <linux/hwmon.h>
#include <linux/hwmon-sysfs.h>
#include <asm/msr.h>

#define EC_BASE_PHYS   0xFE410000ULL
#define EC_SIZE        0x10000
#define F1_OFFSET      0xE8C
#define F2_OFFSET      0xE9D
#define FAN_MANUAL_BIT 0x80
#define FAN_DUTY_MASK  0x7F

#define TJMAX_FALLBACK 100

static void __iomem *ec_base;
static struct platform_device *pdev;
static struct device *hwmon_dev;

static inline u8 ec_read(u32 offset)
{
	return ioread8(ec_base + offset);
}

static inline void ec_write(u32 offset, u8 val)
{
	iowrite8(val, ec_base + offset);
}

static int abra_read_system_temp(long *val)
{
	u32 lo, hi;
	int tjmax = TJMAX_FALLBACK;
	int readout;

	if (!rdmsr_safe(MSR_IA32_TEMPERATURE_TARGET, &lo, &hi) &&
	    ((lo >> 16) & 0xff))
		tjmax = (lo >> 16) & 0xff;

	if (rdmsr_safe(MSR_IA32_PACKAGE_THERM_STATUS, &lo, &hi))
		return -EIO;

	readout = (lo >> 16) & 0x7f;
	*val = (tjmax - readout) * 1000;
	return 0;
}

static umode_t abra_fan_is_visible(const void *data, enum hwmon_sensor_types type,
				   u32 attr, int channel)
{
	if (type == hwmon_temp && (attr == hwmon_temp_input || attr == hwmon_temp_label))
		return 0444;
	if (type == hwmon_fan && (attr == hwmon_fan_input || attr == hwmon_fan_label ||
				  attr == hwmon_fan_min || attr == hwmon_fan_max))
		return 0444;
	if (type == hwmon_pwm && (attr == hwmon_pwm_input || attr == hwmon_pwm_enable))
		return 0644;
	return 0;
}

static int abra_fan_read(struct device *dev, enum hwmon_sensor_types type,
			 u32 attr, int channel, long *val)
{
	u32 offset = (channel == 0) ? F1_OFFSET : F2_OFFSET;
	u8 reg;

	if (type == hwmon_temp && attr == hwmon_temp_input)
		return abra_read_system_temp(val);

	if (type == hwmon_fan) {
		switch (attr) {
		case hwmon_fan_input:
			// Live EC duty cycle (0-127), not RPM - see header comment.
			*val = ec_read(offset) & FAN_DUTY_MASK;
			return 0;
		case hwmon_fan_min:
			*val = 0;
			return 0;
		case hwmon_fan_max:
			*val = FAN_DUTY_MASK;
			return 0;
		default:
			return -EOPNOTSUPP;
		}
	}

	if (type == hwmon_pwm) {
		reg = ec_read(offset);
		if (attr == hwmon_pwm_input) {
			// duty 0-127 -> scale to 0-255
			*val = (reg & FAN_DUTY_MASK) * 2;
		} else if (attr == hwmon_pwm_enable) {
			*val = (reg & FAN_MANUAL_BIT) ? 1 : 2;
		}
		return 0;
	}
	return -EOPNOTSUPP;
}

static int abra_fan_read_string(struct device *dev, enum hwmon_sensor_types type,
				 u32 attr, int channel, const char **str)
{
	// Labels recognized by TUXEDO Control Center's
	// FanControlWorker.getLabelIndex(): "cpu0", "gpu0", "gpu1".
	if (type == hwmon_temp && attr == hwmon_temp_label) {
		*str = "cpu0";
		return 0;
	}
	if (type == hwmon_fan && attr == hwmon_fan_label) {
		*str = (channel == 0) ? "cpu0" : "gpu0";
		return 0;
	}
	return -EOPNOTSUPP;
}

static int abra_fan_write(struct device *dev, enum hwmon_sensor_types type,
			  u32 attr, int channel, long val)
{
	u32 offset = (channel == 0) ? F1_OFFSET : F2_OFFSET;
	u8 reg;

	if (type != hwmon_pwm)
		return -EOPNOTSUPP;

	reg = ec_read(offset);

	if (attr == hwmon_pwm_input) {
		if (val < 0 || val > 255)
			return -EINVAL;
		// Scale 0-255 to 0-127
		reg = (reg & FAN_MANUAL_BIT) | ((u8)(val / 2) & FAN_DUTY_MASK);
		ec_write(offset, reg);
	} else if (attr == hwmon_pwm_enable) {
		if (val == 1) {
			reg |= FAN_MANUAL_BIT;
		} else {
			reg &= ~FAN_MANUAL_BIT;
		}
		ec_write(offset, reg);
	}
	return 0;
}

static const struct hwmon_ops abra_fan_ops = {
	.is_visible  = abra_fan_is_visible,
	.read        = abra_fan_read,
	.read_string = abra_fan_read_string,
	.write       = abra_fan_write,
};

static const struct hwmon_channel_info *abra_fan_info[] = {
	HWMON_CHANNEL_INFO(temp,
		HWMON_T_INPUT | HWMON_T_LABEL),
	HWMON_CHANNEL_INFO(fan,
		HWMON_F_INPUT | HWMON_F_LABEL | HWMON_F_MIN | HWMON_F_MAX,
		HWMON_F_INPUT | HWMON_F_LABEL | HWMON_F_MIN | HWMON_F_MAX),
	HWMON_CHANNEL_INFO(pwm,
		HWMON_PWM_INPUT | HWMON_PWM_ENABLE,
		HWMON_PWM_INPUT | HWMON_PWM_ENABLE),
	NULL
};

static const struct hwmon_chip_info abra_chip_info = {
	.ops  = &abra_fan_ops,
	.info = abra_fan_info,
};

static int __init abra_fan_init(void)
{
	if (!request_mem_region(EC_BASE_PHYS, EC_SIZE, "abra_fan")) {
		pr_warn("abra_fan: cannot claim EC MMIO, trying ioremap anyway\n");
	}

	ec_base = ioremap(EC_BASE_PHYS, EC_SIZE);
	if (!ec_base) {
		pr_err("abra_fan: ioremap failed\n");
		release_mem_region(EC_BASE_PHYS, EC_SIZE);
		return -ENOMEM;
	}

	pdev = platform_device_register_simple("abra_fan", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		iounmap(ec_base);
		release_mem_region(EC_BASE_PHYS, EC_SIZE);
		return PTR_ERR(pdev);
	}

	// Registered as "tuxedo" (not "abra_fan") so that TUXEDO Control
	// Center's tccd daemon recognizes and reads this hwmon chip through
	// its generic fallback path instead of the non-functional clevo_wmi
	// FANINFO calls. See FanControlWorker.getHwmonPwmPath() in tccd.
	hwmon_dev = hwmon_device_register_with_info(&pdev->dev, "tuxedo",
						    NULL, &abra_chip_info, NULL);
	if (IS_ERR(hwmon_dev)) {
		platform_device_unregister(pdev);
		iounmap(ec_base);
		release_mem_region(EC_BASE_PHYS, EC_SIZE);
		return PTR_ERR(hwmon_dev);
	}

	pr_info("abra_fan: EC MMIO fan control + tccd-visible temp loaded (base=0x%llx)\n",
		(unsigned long long)EC_BASE_PHYS);
	return 0;
}

static void __exit abra_fan_exit(void)
{
	// Restore auto mode on exit
	ec_write(F1_OFFSET, ec_read(F1_OFFSET) & ~FAN_MANUAL_BIT);
	ec_write(F2_OFFSET, ec_read(F2_OFFSET) & ~FAN_MANUAL_BIT);

	hwmon_device_unregister(hwmon_dev);
	platform_device_unregister(pdev);
	iounmap(ec_base);
	release_mem_region(EC_BASE_PHYS, EC_SIZE);
	pr_info("abra_fan: unloaded\n");
}

module_init(abra_fan_init);
module_exit(abra_fan_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("MONSTER ABRA A5 V20.2 fan control");
MODULE_DESCRIPTION("EC MMIO fan control + tccd-visible temperature for MONSTER ABRA A5 V20.2");
