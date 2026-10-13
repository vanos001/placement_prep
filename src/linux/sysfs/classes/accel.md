# /sys/class/accel

| Field | Value |
|---|---|
| Subsystem | compute accelerator class; no Documentation directory for the class itself is cached (no Documentation/accel, no DRM_ACCEL mention in the cached tree); implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | none for the class itself; driver-level attributes under /sys/class/accel/accel`<n>`/device/ are documented in `Documentation/ABI/testing/sysfs-driver-habanalabs` |
| Since | not stated in cached sources for the class; habanalabs device entries carry KernelVersion 5.1 through 5.18 |
| Live (5.10.134 host) | class absent: /sys/class/accel does not exist in this container |
| Ledger ID | SYSC-accel |

## What it represents

The accel device class for compute accelerators (AI/ML style cards), as
opposed to the graphics-oriented [drm](./drm.md) class. What the cached
sources establish is narrow: the class name appears as the path prefix of
the habanalabs driver's sysfs attributes, and sysfs-attrs.json lists 34
attribute paths of the form /sys/class/accel/accel`<n>`/device/`<attr>`, all
matching the cached habanalabs ABI file. The class-level story (which
subsystem creates /sys/class/accel, when it appeared, under which Kconfig
symbol) is not documented anywhere in the cached tree, so this page is
source-limited and reports only what is citable.

## Relationship to the device model

Per the habanalabs ABI, the device directory sits one level below the class
device: /sys/class/accel/accel`<n>`/device/`<attr>`. The habanalabs entries
group identity (device_type, module_id, pci_addr, parent_device, versions of
on-card firmware and EEPROM), clocks (mme_clk, tpc_clk, ic_clk and *_curr),
power (max_power, pm_mng_profile), reset controls (hard_reset, soft_reset and
their _cnt counters), and security (security_enabled, status). No bus,
parent-link, or uevent behavior is described in the cached text.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| device/device_type | RO | code name of the device according to its type | habanalabs devices | ABI testing sysfs-driver-habanalabs, 5.1 |
| device/armcp_kernel_ver, device/armcp_ver | RO | kernel and application versions of the device's CPU | habanalabs devices | ABI, 5.1 |
| device/clk_max_freq_mhz, device/clk_cur_freq_mhz | RW/RO | maximum (settable) and current clock frequency, MHz | habanalabs devices | ABI, 5.7 |
| device/mme_clk, device/tpc_clk, device/ic_clk | RW | max clock frequency in Hz of MME/TPC/interconnect | habanalabs devices | ABI, 5.1 |
| device/max_power | RW | maximum power consumption of the device | habanalabs devices | ABI, 5.1 |
| device/hard_reset, device/soft_reset | WO | trigger hard/soft reset of the device | habanalabs devices | ABI, 5.1 |
| device/hard_reset_cnt, device/soft_reset_cnt | RO | how many times each reset occurred | habanalabs devices | ABI, 5.1 |
| device/security_enabled | RO | security enabled flag | habanalabs devices | ABI, 5.1 |
| device/eeprom | RO | binary attribute with EEPROM contents | habanalabs devices | ABI, 5.1 |
| device/status | RO | device status | habanalabs devices | ABI, 5.1 |

All 34 JSON-listed paths resolve to this ABI file; remaining rows (fuse_ver,
cpld_ver, infineon_ver, cpucp_*, fw_os_ver, preboot_btl_ver, uboot_ver,
thermal_ver, vrm_ver, high_pll, ic_clk_curr, mme_clk_curr, tpc_clk_curr,
clk_*, module_id, parent_device, pci_addr, pm_mng_profile) follow the same
identity/version/clock pattern.

## Safety and writes

Writes exist in the habanalabs set (clock ceilings, max_power, reset
triggers) and act on accelerator hardware. No class-level ABI entry exists,
so no class-level write behavior can be claimed. The class is absent on the
5.10.134 host; nothing was read live.

## References

- `Documentation/ABI/testing/sysfs-driver-habanalabs` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-habanalabs
- sysfs-attrs.json entry `accel` (34 paths); live enumeration: class absent, kernel 5.10.134
- Related page: [drm](./drm.md); coverage: [ledger](../ledger.md)
