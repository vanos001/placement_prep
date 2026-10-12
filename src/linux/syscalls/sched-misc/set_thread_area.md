# set_thread_area(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | set_thread_area 205 / 243 / - / -; get_thread_area 211 / 244 / - / - (cached kernel tables; hub agrees) |
| Since (kernel) | 2.6 (hub); man VERSIONS says set_thread_area 2.5.29 and get_thread_area 2.5.32 -- man-page values noted here |
| Man page | man2/set_thread_area.2 (get_thread_area.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | None in glibc (threading libraries use it internally); no set_thread_area symbol in libc (nm -D on glibc 2.41) |
| Aliases covered | get_thread_area |
| Ledger ID | SC-set_thread_area, SC-get_thread_area (researched/BRIEF) |

## Purpose

set_thread_area() writes a TLS descriptor into one of the x86 GDT entries dedicated for thread-local storage; get_thread_area() reads one back. Both take struct user_desc; entry_number selects the GDT TLS entry; the rest define the descriptor. entry_number -1 makes the kernel find a free entry and report the index back; a descriptor with read_exec_only and seg_not_present set and the rest 0 is "empty" and clears the entry. Available on x86 (32- and 64-bit), m68k, and MIPS (which stores an arbitrary thread pointer); it is the 32-bit x86 TLS mechanism threading libraries use.

## Synopsis

```c
#include <asm/ldt.h>            /* struct user_desc */
int syscall(SYS_set_thread_area, struct user_desc *u_info);
int syscall(SYS_get_thread_area, struct user_desc *u_info);
```

## Return value and errors

Returns 0 on success on x86; -1 with errno: EFAULT, EINVAL (entry_number out of bounds), ENOSYS (64-bit invocation), ESRCH (no free TLS entry).

## Security and notes

- Since 3.19 the call cannot install non-present, 16-bit, or code segments (clearing still works).
- arch_prctl(2) can interfere with it on x86 (see also modify_ldt(2)); on MIPS the thread pointer is readable via rdhwr $29.

## References

- man2/set_thread_area.2 in the cached man-pages tree; .so alias get_thread_area.2.
- [Syscalls ledger](../ledger.md) rows SC-set_thread_area, SC-get_thread_area; [Domain hub](overview.md).
