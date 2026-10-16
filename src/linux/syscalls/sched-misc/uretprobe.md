# uretprobe(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 335 / -- / -- / -- (x86_64 table only) |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (x86_64 number verified in arch/x86/entry/syscalls/syscall_64.tbl, fetched 2026-10-17) |
| Man page | none (no man2/uretprobe.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [uprobe](uprobe.md) |
| Ledger ID | SC-uretprobe |

## Purpose

uretprobe() is the x86_64 return-trampoline syscall for uretprobe (function-return probes): when a return probe fires, the kernel has replaced the function's return address with a trampoline; when the function returns, control lands on that trampoline, which executes SYS_uretprobe so the kernel can deliver the return-probe event and then resume the genuine return (the perf/bpftrace uretprobe mechanism on x86_64).

## Synopsis

```c
/* x86_64 syscall, invoked by the uretprobe trampoline */
long syscall(SYS_uretprobe);
```

## Arguments and behavior

No userspace arguments. The syscall_64.tbl row is `335 common uretprobe sys_uretprobe` (verified fetched table). The syscall entry carries the saved state the kernel needs to fire the return probe and resume.

## Return value and errors

For probe infrastructure: fires the return-probe event and resumes the interrupted return path; a raw user invocation has no defined useful behavior.

## Flags and constants

None.

## Security and notes

Source-limited: number verified in the fetched table; no man page; implementation file not fetched this round. Interview angle: uretprobe machinery explains why you cannot uprobe-return into a function whose first bytes you also probe -- the two trampolines share the saved-state bookkeeping. Cross-reference: [uprobe](uprobe.md), [perf_event_open](perf_event_open.md).

## References

- Kernel table: arch/x86/entry/syscalls/syscall_64.tbl line `335 common uretprobe sys_uretprobe` (torvalds/linux master, fetched 2026-10-17)
- Ledger row SC-uretprobe

