# s390_pci_mmio_write(2) / s390_pci_mmio_read(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (s390 table only) |
| Since (kernel) | 3.19 (s390_pci_mmio_write.2 HISTORY: "Linux 3.19. System z EC12") |
| Man page | man2/s390_pci_mmio_write.2 (man-pages 6.19 HTML set, fetched 2026-10-17) covers both calls; man2/s390_pci_mmio_read.2 is the sibling |
| glibc wrapper | none -- "glibc provides no wrappers for these system calls, necessitating the use of syscall(2)" (s390_pci_mmio_write.2, SYNOPSIS) |
| Aliases covered | s390_pci_mmio_read (SC-s390_pci_mmio_read, grouped) |
| Ledger ID | SC-s390_pci_mmio_write |

## Purpose

s390_pci_mmio_write()/s390_pci_mmio_read() transfer `length` bytes between a userspace buffer and a PCI MMIO mapping on System z: plain loads/stores are not sufficient for s390 PCI MMIO areas, so the kernel performs the access with the special instructions/handling the platform requires (s390_pci_mmio_write.2, DESCRIPTION). The address must belong to a PCI MMIO page mapped in the caller's address space, the transfer must not cross a page boundary, and length cannot exceed the page size (s390_pci_mmio_write.2, DESCRIPTION).

## Synopsis

```c
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_s390_pci_mmio_write, unsigned long mmio_addr,
            const void user_buffer[length], size_t length);
int syscall(SYS_s390_pci_mmio_read, unsigned long mmio_addr,
            void user_buffer[length], size_t length);
```

## Arguments and behavior

`mmio_addr` must land inside a PCI MMIO mapping of the caller; `user_buffer`/`length` bound the copy (max one page, no page crossing) (s390_pci_mmio_write.2, DESCRIPTION). This is the read/write pairing used by s390 userspace drivers (the vfio-style map + syscall access pattern); generic x86-style mmap'd MMIO access just dereferences, which is why the calls are s390-only.

## Return value and errors

0 on success; -1 with errno (s390_pci_mmio_write.2, RETURN VALUE). Errors: EFAULT (invalid mmio_addr, or user_buffer outside the caller's address space), EINVAL (invalid length), ENODEV (PCI support not enabled), ENOMEM (insufficient kernel memory) (s390_pci_mmio_write.2, ERRORS).

## Flags and constants

None.

## Security and notes

The permission story is the mapping, not the syscall: the caller must already have mmap'd the device region (with the usual device-file permissions), and the syscall only executes the platform-correct access. Interview angle: why would a platform need a syscall to read memory it can map? -- because s390 PCI MMIO accesses require special instructions/error handling that plain userspace loads do not provide. Cross-reference: [mmap](../memory/mmap.md), [ioperm](ioperm.md), [pciconfig_read](pciconfig_read.md).

## References

- https://man7.org/linux/man-pages/man2/s390_pci_mmio_write.2.html
- https://man7.org/linux/man-pages/man2/s390_pci_mmio_read.2.html
- man-pages syscalls(2) (3.19, s390 only)
