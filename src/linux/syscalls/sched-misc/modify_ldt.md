# modify_ldt(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 154 / 123 / -- / -- |
| Since (kernel) | 1.0 |
| Man page | man2/modify_ldt.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none on this host: man page says "glibc provides no wrapper for modify_ldt(), necessitating the use of syscall(2)"; glibc 2.41 still exports a weak modify_ldt @GLIBC_2.2.5 (nm -D) -- treat the man page as authoritative |
| Aliases covered | none |
| Ledger ID | SC-modify_ldt |

## Purpose

modify_ldt() reads or writes the process's local descriptor table (LDT) -- the x86 segment-descriptor array user code can reference -- with Linux providing a per-process (per-mm) LDT (modify_ldt.2, DESCRIPTION). Its normal remaining use is running legacy 16-bit or segmented 32-bit code (Wine, DOSEMU-class emulators); the man page is explicit that threading libraries must not use it for TLS (modify_ldt.2, NOTES).

## Synopsis

```c
#include <asm/ldt.h>       /* struct user_desc */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_modify_ldt, int func, void ptr[bytecount],
            unsigned long bytecount);
```

## Arguments and behavior

`func` == 0 reads the LDT into `ptr`, copying min(bytecount, LDT size) bytes and returning the count (the kernel may pad with trailing zeros); `func` == 1 or 0x11 writes the entry described by the `user_desc` structure at `ptr` -- `entry_number` selects the slot (modify_ldt.2, DESCRIPTION). `func` == 2 is the legacy "read default" variant. Not all kernels permit 16-bit segments, and no kernel lets you create a 64-bit (long mode) code segment through it -- the undocumented `lm` field is explicitly a no-op trap (modify_ldt.2, NOTES). On 64-bit kernels before 3.19, setting `lm` also broke the empty-descriptor check (modify_ldt.2, BUGS).

## Return value and errors

Bytes read (func 0) or 0 (writes) on success; -1 with errno on failure (modify_ldt.2, RETURN VALUE). Errors: EFAULT (ptr outside address space), EINVAL (ptr NULL; bytecount mismatch for func 1; invalid descriptor values), ENOSYS (func not in {0, 1, 2, 0x11}) (modify_ldt.2, ERRORS).

## Flags and constants

user_desc fields from <asm/ldt.h> (entry_number, base_addr, limit, seg_32bit, contents, read_exec_only, limit_in_pages, seg_not_present, useable, lm).

## Security and notes

modify_ldt() is a recurring kernel-attack-surface story: LDT entries let userspace create unusual segment mappings, and CVEs in the LDT allocation paths (e.g. the 2015 CVE-2015-5157 class) made it a seccomp favorite to deny. Use set_thread_area(2) ([set_thread_area](set_thread_area.md)) or arch_prctl(2) ([arch_prctl](../process/arch_prctl.md)) for TLS (modify_ldt.2, NOTES). Cross-reference: [arch_prctl](../process/arch_prctl.md), [set_thread_area](set_thread_area.md), [vm86](vm86.md), [ioperm](ioperm.md).

## References

- https://man7.org/linux/man-pages/man2/modify_ldt.2.html
- man-pages syscalls(2)
- worklog: weak glibc symbol modify_ldt @GLIBC_2.2.5 noted via nm -D (2026-10-17)
