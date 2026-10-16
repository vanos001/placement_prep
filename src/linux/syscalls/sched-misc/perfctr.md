# perfctr(2) (SPARC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (SPARC table only) |
| Since (kernel) | 2.2 (syscalls(2): "SPARC only; removed in ..." -- removed during the 2.6 series) |
| Man page | none (no man2/perfctr.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-perfctr |

## Purpose

perfctr() was the SPARC userspace interface to the processor performance counters: it started, stopped and read the hardware performance counter registers for the calling process -- SPARC's counterpart of what perf_event_open(2) (see [perf_event_open](perf_event_open.md)) does generically today. syscalls(2) records the name as SPARC-only and removed during the 2.6 series; the ledger keeps the 2.2 introduction date and no x86/asm-generic numbers.

## Synopsis

```c
/* SPARC syscall, removed in the 2.6 series */
long syscall(SYS_perfctr, int op, ...);
```

## Arguments and behavior

Operation-dependent (start/stop/read counter sets for the calling process); the interface predates the structured command/argument design of perf_event_open and was never documented in a man page -- the gap this entry names.

## Return value and errors

Operation-dependent; the call no longer exists on any current kernel.

## Flags and constants

None documented.

## Security and notes

Source-limited: no man page and the implementation is long gone from the tree; the entry rests on the syscalls(2) listing and the ledger. Interview angle: perfctr -> perfmonctl (IA-64, [perfmonctl](perfmonctl.md)) -> perf_event_open is the whole history of Linux performance-counter interfaces. Cross-reference: [perf_event_open](perf_event_open.md), [perfmonctl](perfmonctl.md), [getrusage](../process/getrusage.md).

## References

- man-pages syscalls(2) (perfctr(2), 2.2, SPARC only, removed)
- Ledger row SC-perfctr

