# /sys/class/msr

| Field | Value |
|---|---|
| Subsystem | x86 platform; arch/x86/kernel/msr.c (msr_class, msr_devnode) |
| Config gate | CONFIG_X86_MSR (arch/x86/kernel/Makefile: obj-$(CONFIG_X86_MSR) += msr.o); x86 only |
| ABI documentation | None (no What: entries in Documentation/ABI for /sys/class/msr) |
| Since | Source-established; module author H. Peter Anvin, "x86 generic MSR driver" (MODULE_DESCRIPTION) |
| Live (5.10.134 host) | 2 entries: msr0, msr1; msr0 dev = 202:0 |
| Ledger ID | SYSC-msr |

## What it represents

One character device per CPU (msr%d, minor = CPU number) giving read and
write access to that CPU's model-specific registers through pread(2)/pwrite(2)
with the MSR address as the file offset. Like [cpuid](./cpuid.md) there are
no sysfs attributes: the class directory is the per-CPU registry from which
devtmpfs derives /dev/cpu/<N>/msr via the msr_devnode callback ("cpu/%u/msr").
MSRs control clocks, caches, power, debugging and more; the same physical
register index can mean different things per CPU family, so nothing about
the semantics is promised by this class.

## Relationship to the device model

msr_class is registered from msr_init() with __register_chrdev of MSR_MAJOR
202 ("cpu/msr"); devices come and go with CPU hotplug (msr_device_create /
msr_device_destroy), matching the online CPU set (live: msr0, msr1 for two
vCPUs). The driver carries one module parameter, allow_writes
(module_param_cb, mode 0600): "on" enables writes unconditionally, "off"
makes write() return -EPERM, "default" (the initial value) allows writes but
logs a warning once per driver lifetime. The parameter lives in
/sys/module/msr/parameters/allow_writes, not in the class.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| msr0/dev | RO | 202:0 | live check (5.10.134); msr.c MKDEV(MSR_MAJOR, cpu) |
| msr1/dev | RO | 202:1 | live check; minor = CPU number |
| uevent | RO/RW | standard uevent file | device core |

No sysfs attributes beyond the device core set. The functional knobs are the
char device (read/write by MSR address) and the allow_writes module
parameter named above, both source-verified; msr-tools (rdmsr/wrmsr) are the
usual userspace consumers but their documentation was not reachable in this
environment, so tool claims stay out of scope here.

## Safety and writes

Writing to the MSR device can change clocking, power and cache behavior and
can brick or hard-hang the platform; it is a root-only, x86-only, per-CPU
escape hatch, which is exactly why the driver ships a kill switch. The
default write path warns; "off" disables writes without unloading the
module. Reads are comparatively benign but leak platform details. This class
gates nothing by itself: audit /dev/cpu/*/msr node permissions and the
allow_writes parameter together. Devices vanish on CPU offline and reappear
on online, so scripts must not assume stable populations.

## References

- arch/x86/kernel/msr.c, include/uapi/linux/major.h (MSR_MAJOR 202), fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/msr (read-only, kernel 5.10.134)
- Documentation/ABI: confirmed absence (grep for /sys/class/msr returns nothing)
- Sibling pages: [cpuid](./cpuid.md), [mem](./mem.md); coverage: [ledger](../ledger.md)
