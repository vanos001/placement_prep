# personality(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 135 / 136 / 92 / 136 |
| Since (kernel) | 1.2 |
| Man page | man2/personality.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | personality@@GLIBC_2.2.5 (nm -D, glibc 2.41); header `/usr/include/x86_64-linux-gnu/sys/personality.h` present on host; musl: src/linux/personality.c + include/sys/personality.h (declares `int personality(unsigned long)`) |
| Aliases covered | none |
| Ledger ID | SC-personality |

## Purpose

personality() sets or reads the caller's execution domain: a 32-bit word whose low byte selects a persona (behavioral compatibility profile with other UNIX variants) and whose top three bytes carry flags that change kernel behavior to emulate historical or architectural quirks (personality.2, DESCRIPTION).

## Synopsis

```c
#include <sys/personality.h>
int personality(unsigned long persona);
```

## Arguments and behavior

Passing `0xffffffff` reads the current persona without changing it; anything else sets it (personality.2, DESCRIPTION). Flag bits (values verified in /usr/include/linux/personality.h):

| Flag | Value | Effect (personality.2) | Since |
|---|---|---|---|
| `ADDR_NO_RANDOMIZE` | 0x0040000 | Disable address-space-layout randomization | 2.6.12 |
| `ADDR_COMPAT_LAYOUT` | 0x0200000 | Legacy virtual address space layout | 2.6.9 |
| `ADDR_LIMIT_32BIT` | 0x0800000 | Limit address space to 32 bits | 2.2 |
| `ADDR_LIMIT_3GB` | 0x8000000 | mmap base search at 0xc0000000 instead of 0xffffe000 | 2.4.0 |
| `FDPIC_FUNCPTRS` | (header) | Signal-handler function pointers point to descriptors (FDPIC arches) | 2.6.11 |
| `MMAP_PAGE_ZERO` | (header) | Map page 0 read-only (SVr4 binaries that dereference NULL) | 2.4.0 |
| `READ_IMPLIES_EXEC` | (header) | `PROT_READ` implies `PROT_EXEC` for mmap | 2.6.8 |
| `SHORT_INODE` | (header) | No effects(?) (personality.2) | 2.4.0 |
| `STICKY_TIMEOUTS` | (header) | select/pselect/ppoll do not overwrite the timeout on EINTR | 1.2.0 |
| `UNAME26` | (header) | uname reports 2.6.40+ instead of 3.x (3.1 stopgap) | 3.1 |
| `WHOLE_SECONDS` | (header) | (listed in header; see man page) | -- |

Persona constants include `PER_LINUX` (0x0000), `PER_LINUX_32BIT` (= PER_LINUX | ADDR_LIMIT_32BIT), `PER_LINUX_FDPIC`, `PER_LINUX32` (0x0008, 32-bit emulation on 64-bit kernels), `PER_SVR4` (0x0001 | STICKY_TIMEOUTS | MMAP_PAGE_ZERO), `PER_BSD` (0x0006), `PER_SUNOS`, `PER_XENIX`, `PER_IRIX32/N32/64`, `PER_RISCOS`, `PER_SOLARIS`, `PER_UW7`, `PER_OSF4`, `PER_HPUX` -- the full set is in the header (verified list above truncated to the load-bearing ones).

## Return value and errors

The call does not follow the usual 0/-1 convention: it returns the previous persona on success (so 0 means "was PER_LINUX"), or -1 with `errno` on failure: `EINVAL` (attempted persona invalid) and `EPERM` (missing capability) (personality.2, RETURN VALUE/ERRORS).

## Security and notes

Changing a persona that weakens protections requires privilege: the kernel gates personas where the caller does not already have the privileges the persona implies, and `PER_CLEAR_ON_SETID` in the header lists the flags (READ_IMPLIES_EXEC, ADDR_NO_RANDOMIZE, ADDR_COMPAT_LAYOUT, ...) that are stripped on setuid/setgid transitions so hardened binaries cannot be downgraded by pre-exec personality calls. `ADDR_NO_RANDOMIZE` is the flag setuid-safe tools wrap into helpers (setarch(8)'s -R) for debugging ASLR-sensitive code; it is also the classic example of a debug affordance doubling as an exploit mitigation bypass when inherited across exec. The call is Linux-specific and ABI-flavored: most personas other than PER_LINUX* exist to support ibcs2/abi emulation layers and are effectively unused by modern binaries. Cross-references: [execve.md](execve.md) (persona survives exec; setuid resets selected flags), [uname/sysinfo](../sched-misc/) for UNAME26's target.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/personality.2`
- Online: https://man7.org/linux/man-pages/man2/personality.2.html
- Header: /usr/include/linux/personality.h (flag values, PER_* table, PER_CLEAR_ON_SETID), /usr/include/x86_64-linux-gnu/sys/personality.h
- Kernel tables: source-cache/kernel/syscall_64.tbl (135), syscall_32.tbl (136), syscall_generic.tbl (92), syscall_arm.tbl (136)
- musl: source-cache/musl-clone/musl/src/linux/personality.c, include/sys/personality.h
- Ledger row SC-personality
