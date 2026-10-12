# arch_prctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 158 / 384 / - / - |
| Since (kernel) | 2.6 |
| Man page | man2/arch_prctl.2 (cached roff, dated 2021-08-27) |
| glibc wrapper | cached man page: "glibc provides no wrapper for arch_prctl(), necessitating the use of syscall(2)"; nm -D on glibc 2.41 does export arch_prctl @@GLIBC_2.2.5 (undocumented, used internally for TLS); musl 1.2.5 exposes arch_prctl() when SYS_arch_prctl exists (src/linux/arch_prctl.c) |
| Aliases covered | none; x86-only: no arm64-generic or arm32 row in the hub (i386 entry 384 verified in source-cache/kernel/syscall_32.tbl) |
| Ledger ID | SC-arch_prctl |

## Purpose

arch_prctl() sets or gets architecture-specific thread state on x86: the 64-bit FS and GS segment bases -- the TLS mechanism on x86-64 -- and, since Linux 4.12, CPUID faulting control. Brief entry.

## Synopsis

```c
#include <asm/prctl.h>      /* on this host: /usr/include/x86_64-linux-gnu/asm/prctl.h */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_arch_prctl, int code, unsigned long addr);        /* set */
int syscall(SYS_arch_prctl, int code, unsigned long *addr);       /* get */
```

## Arguments and behavior

code selects the subfunction; addr is a value for set operations or a pointer for get operations (arch_prctl.2, DESCRIPTION). x86-64-only: ARCH_SET_FS (0x1002) / ARCH_SET_GS (0x1001) set the 64-bit FS/GS base; ARCH_GET_FS (0x1003) / ARCH_GET_GS (0x1004) read it back (asm/prctl.h). The CPUID subfunctions (ARCH_SET_CPUID/ARCH_GET_CPUID, since 4.12) toggle per-thread CPUID and report the flag -- a disabled CPUID raises SIGSEGV, and the setting survives fork(2)/clone(2) but resets on execve(2) (arch_prctl.2).

## Return value and errors

0 on success, -1 with errno; ARCH_GET_CPUID returns 1/0 as the result. Errors: EFAULT, EINVAL, ENODEV (no CPUID-faulting hardware), EPERM (arch_prctl.2, RETURN VALUE and ERRORS).

## Flags and constants

ARCH_SET_GS 0x1001, ARCH_SET_FS 0x1002, ARCH_GET_FS 0x1003, ARCH_GET_GS 0x1004, ARCH_GET_CPUID 0x1011, ARCH_SET_CPUID 0x1012 (asm/prctl.h); the header also defines newer xcomp/vdso/shstk codes absent from the cached page.

## Security and notes

arch_prctl() is a Linux/x86-64 extension (CONFORMING TO); the cached page says 64-bit programs only, while the i386 table carries entry 384 -- availability qualified per arch. FS is owned by the threading library: direct ARCH_SET_FS callers are very likely to crash (NOTES) -- the glibc TLS use, since glibc sets FS internally via this call; musl's x86-64 __set_thread_area.s does the same. ARCH_SET_GS is disabled in some kernels; mixing with set_thread_area(2) is dangerous (NOTES). Cross-reference: [prctl](prctl.md) for the non-arch option space.

## References

- https://man7.org/linux/man-pages/man2/arch_prctl.2.html
- /usr/include/x86_64-linux-gnu/asm/prctl.h (ARCH_* values)
- /home/z/my-project/source-cache/kernel/syscall_32.tbl (i386 384)
- /home/z/my-project/source-cache/musl-clone/musl/src/linux/arch_prctl.c, src/thread/x86_64/__set_thread_area.s
