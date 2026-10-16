# uprobe(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 336 / -- / -- / -- (x86_64 table only) |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (x86_64 number verified in arch/x86/entry/syscalls/syscall_64.tbl, fetched 2026-10-17) |
| Man page | none (no man2/uprobe.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [uretprobe](uretprobe.md) |
| Ledger ID | SC-uprobe |

## Purpose

uprobe() is the x86_64 trampoline return syscall for user-space probe handlers: when a uprobe (userspace breakpoint probe, the perf/bpftrace mechanism) fires, the kernel redirects execution to an inline trampoline that ends by issuing this syscall, which hands control back to the kernel to resume the original instruction stream -- including restoring the interrupted registers from the probe's saved state.

## Synopsis

```c
/* x86_64 syscall, invoked by the uprobe trampoline, not by applications */
long syscall(SYS_uprobe);
```

## Arguments and behavior

No userspace arguments. The syscall is part of the probe protocol: the trampoline pushes the saved register state, calls SYS_uprobe, and the kernel unwinds the probe (the x86_64 syscall_64.tbl row `336 common uprobe sys_uprobe`, verified fetched table).

## Return value and errors

For probe infrastructure: resumes the probed thread's original flow; a raw user invocation has no defined useful behavior.

## Flags and constants

None.

## Security and notes

Source-limited: the number was verified in the fetched syscall table; no man page exists and the implementation file was not fetched this round. Interview angle: uretprobe/uprobe syscalls exist because returning from a probe without them would clobber the very instructions being probed -- the same reason kretprobe trampolines exist in kernel space. Cross-reference: [uretprobe](uretprobe.md), [perf_event_open](perf_event_open.md), [restart_syscall](../signals-time/restart_syscall.md).

## References

- Kernel table: arch/x86/entry/syscalls/syscall_64.tbl line `336 common uprobe sys_uprobe` (torvalds/linux master, fetched 2026-10-17)
- Ledger row SC-uprobe

