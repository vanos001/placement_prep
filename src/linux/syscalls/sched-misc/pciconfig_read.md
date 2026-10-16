# pciconfig_read(2) / pciconfig_write(2) / pciconfig_iobase(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | read/write -- / -- / -- / 272-273; iobase -- / -- / -- / 271 (arm32 EABI columns; the man page notes 2.0.26/2.2.15-era introduction) |
| Since (kernel) | pciconfig_read/write 2.0.26; pciconfig_iobase 2.2.15 (syscalls(2): "Not on x86") |
| Man page | man2/pciconfig_read.2 (man-pages 6.19 HTML set, fetched 2026-10-17) covers all three calls; man2/pciconfig_write.2 and man2/pciconfig_iobase.2 are .so aliases |
| glibc wrapper | none -- the calls are arch-gated (arm, alpha, ppc, sparc tables) and glibc provides no wrappers |
| Aliases covered | pciconfig_iobase (SC-pciconfig_iobase), pciconfig_write (SC-pciconfig_write); pciconfig_read is the primary (SC-pciconfig_read) |
| Ledger ID | SC-pciconfig_read |

## Purpose

The pciconfig family lets userspace touch PCI configuration space and platform I/O-region bases on architectures where the kernel PCI layer does not already mediate everything: pciconfig_read()/pciconfig_write() move bytes between a caller buffer and a device's config space at (bus, dfn, off), and pciconfig_iobase() maps a bus/devfn pair to the physical address of the memory offset, PIO base, or ISA hole (pciconfig_read.2, DESCRIPTION). The man page's own framing: "Most of the interaction with PCI devices is already handled by the kernel PCI layer, and thus these calls should not normally need to be accessed from user space" (pciconfig_read.2, DESCRIPTION).

## Synopsis

```c
#include <pci.h>
int pciconfig_read(unsigned long bus, unsigned long dfn,
                   unsigned long off, unsigned long size,
                   unsigned char *buf);
int pciconfig_write(unsigned long bus, unsigned long dfn,
                    unsigned long off, unsigned long size,
                    unsigned char *buf);
int pciconfig_iobase(int which, unsigned long bus, unsigned long devfn);
```

## Arguments and behavior

`bus`/`dfn` (device-function number)/`off` address the device; `size` selects the read/write width (EINVAL when invalid) (pciconfig_read.2, DESCRIPTION/ERRORS). pciconfig_iobase()'s `which` selects the region: IOBASE_BRIDGE_NUMBER, IOBASE_MEMORY, IOBASE_IO, IOBASE_ISA_IO, IOBASE_ISA_MEM (pciconfig_read.2, RETURN VALUE). On x86 the /sys/bus/pci/devices/*/config binary attribute replaced the read/write pair (the kernel routes it through the same access layer), and I/O-region discovery goes through /proc/iomem and libpci.

## Return value and errors

0 on success for read/write; pciconfig_iobase() returns the requested region address (pciconfig_read.2, RETURN VALUE). Errors: EINVAL (invalid size), EIO (I/O error), ENODEV (slot not found; hose NULL for iobase), ENOSYS (CONFIG_PCI off), EOPNOTSUPP (invalid `which`, iobase only), EPERM (missing CAP_SYS_ADMIN for read/write) (pciconfig_read.2, ERRORS).

## Flags and constants

IOBASE_* selectors for pciconfig_iobase (pciconfig_read.2, RETURN VALUE).

## Security and notes

EPERM + CAP_SYS_ADMIN on read/write is the whole security model -- raw config space includes the ability to flip bus-master and interrupt-disable bits, so it is privileged everywhere it exists. The calls survive only in arm32/legacy tables (hence the `--` x64 columns); modern equivalents are /sys/bus/pci + libpci + the VFIO framework for real userspace device control. Cross-reference: [ioperm](ioperm.md), [iopl](iopl.md), [reboot](reboot.md).

## References

- https://man7.org/linux/man-pages/man2/pciconfig_read.2.html
- https://man7.org/linux/man-pages/man2/pciconfig_iobase.2.html
- man-pages syscalls(2) ("Not on x86")
