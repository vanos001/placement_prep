# syscall(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | none: syscall() is a C library function, not a syscall-table slot (verified from man2/syscall.2; hub row shows all dashes) |
| Since (kernel) | 1.0 (hub); the man page says syscall() "first appeared in 4BSD" as a library function |
| Man page | man2/syscall.2 (local cache, dated 2021-03-22) |
| glibc wrapper | syscall@@GLIBC_2.2.5 (nm -D on glibc 2.41); needs _DEFAULT_SOURCE (glibc 2.19+) or _BSD_SOURCE/_SVID_SOURCE before |
| Aliases covered | none |
| Ledger ID | SC-syscall (researched/BRIEF) |

## Purpose

syscall() is a small library function that invokes the system call whose ABI number is passed as number, mapping a kernel error return to errno. It is the standard way to reach a syscall without a glibc wrapper -- openat2(2), bpf(2), perf_event_open(2), the kexec and lsm calls. It occupies no syscall slot: on x86-64, syscall is the CPU instruction (number in rax, args rdi/rsi/rdx/r10/r8/r9).

## Synopsis

```c
#include <sys/syscall.h>        /* SYS_* numbers */
#include <unistd.h>
long syscall(long number, ...);
```

## Arguments and behavior

number is the SYS_* constant; variadic arguments map onto the arch's argument registers (i386: ebx..ebp via int $0x80; arm64: svc #0, number in w8).

## Return value and errors

Defined by the invoked syscall; -1 with errno set is the generic convention.

## Flags and constants

No flags. On 32-bit ABIs with aligned 64-bit register pairs (ARM EABI, MIPS O32, 32-bit PowerPC) the caller must split and align 64-bit arguments.

## Security and notes

- seccomp filters see the raw numbers syscall() produces; indirect invocation bypasses nothing.
- x32 callers OR the number with __X32_SYSCALL_BIT.

## References

- man2/syscall.2 in the cached man-pages tree (dated 2021-03-22), including both architecture tables quoted above.
- [Syscalls ledger](../ledger.md) row SC-syscall; [Domain hub](overview.md).
