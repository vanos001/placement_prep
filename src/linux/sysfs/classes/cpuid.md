# /sys/class/cpuid

| Field | Value |
|---|---|
| Subsystem | x86 platform; arch/x86/kernel/cpuid.c (cpuid_class, cpuid_devnode) |
| Config gate | CONFIG_X86_CPUID (arch/x86/kernel/Makefile: obj-$(CONFIG_X86_CPUID) += cpuid.o); x86 only |
| ABI documentation | None (no What: entries in Documentation/ABI for /sys/class/cpuid) |
| Since | Source-established; interface is the CPUID instruction marshalled through read(2)/pread(2) on the char device |
| Live (5.10.134 host) | 2 entries: cpu0, cpu1; cpu0 dev = 203:0 |
| Ledger ID | SYSC-cpuid |

## What it represents

One character device per CPU (cpu%d, minor = CPU number) whose read side
executes the x86 CPUID instruction with the requested leaf/subleaf taken
from the file offset. There are no sysfs attributes: the class directory is
purely the registry that names the per-CPU devices and lets udev/devtmpfs
create the real node /dev/cpu/<N>/cpuid. The driver pairs structurally with
the msr driver (same pattern, CPUID_MAJOR 203 vs MSR_MAJOR 202), documented
on the [msr](./msr.md) page.

## Relationship to the device model

cpuid_class is registered from cpuid_init() along with __register_chrdev of
major 203 ("cpu/cpuid" in the chdev registry). Devices are created and
destroyed from the CPU hotplug callbacks (cpuid_device_create /
cpuid_device_destroy), so the class population tracks the online CPU set:
the live host's two entries correspond to its two vCPUs. The devnode callback
formats "cpu/%u/cpuid" from the minor, which is how the /dev/cpu/N/cpuid path
is derived on devtmpfs hosts; on this container /dev is not populated with
/dev/cpu, while the class entries still exist (devnode-vs-devnode split
noted live).

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| cpu0/dev | RO | 203:0 | live check (5.10.134); cpuid.c MKDEV(CPUID_MAJOR, cpu) |
| cpu1/dev | RO | 203:1 | live check; minor = CPU number |
| uevent | RO/RW | standard uevent file | device core |

No class-level or device-level sysfs attributes exist beyond the core set:
the interface is the char device itself. Anything else found under these
directories is device-core boilerplate, not driver ABI.

## Safety and writes

The class directory has nothing to write. The risk surface is the device
node: reads expose CPUID leaves including microcode and feature information
(useful for fingerprinting), which is why hardening setups restrict
/dev/cpu/*/cpuid. Reads do not execute privileged operations and cannot
change CPU state. Keep in mind the class only exists with CONFIG_X86_CPUID
and tracks hotplug: CPU offline removes the matching directory.

## References

- arch/x86/kernel/cpuid.c, include/uapi/linux/major.h (CPUID_MAJOR 203), fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/cpuid (read-only, kernel 5.10.134)
- Documentation/ABI: confirmed absence (grep for /sys/class/cpuid returns nothing)
- Sibling pages: [msr](./msr.md), [mem](./mem.md); coverage: [ledger](../ledger.md)
