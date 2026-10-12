# System Call Encyclopedia

This section documents the Linux system call interface one call per page,
organized into seven domains. The [coverage ledger](./ledger.md) is the
authoritative inventory: 535 rows generated from the per-architecture kernel
syscall tables (`arch/x86/entry/syscalls/syscall_64.tbl`,
`syscall_32.tbl`, `arch/arm/tools/syscall.tbl`, and the asm-generic
`scripts/syscall.tbl`/`unistd.h` numbering used by arm64/riscv/loongarch),
with `since` values from the man-pages `syscalls(2)` table and man-page
existence flags. Statuses are merged from per-task agent reports — a name in
a table is never treated as documented.

## Domains

| Domain | Hub | Rows | Documented |
|---|---|---|---|
| Process, thread, credential | [process](./process/overview.md) | 86 | 62 |
| Memory management | [memory](./memory/overview.md) | 34 | 31 |
| Descriptors and file I/O | [descriptors-io](./descriptors-io/overview.md) | 70 | 67 |
| Filesystem, mounts, namespaces | [fs-mounts-namespace](./fs-mounts-namespace/overview.md) | 80 | 70 |
| Signals and time | [signals-time](./signals-time/overview.md) | 50 | 32 |
| Scheduling, security, misc | [sched-misc](./sched-misc/overview.md) | 131 | 38 |
| Network, IPC, event loops | [net-ipc](./net-ipc/overview.md) | 84 | 66 |

## How pages are organized

Each domain hub lists one row per **function page**. Aliases share a page when
the man page is shared (`.so` alias pages in man-pages, e.g. `dup2`/`dup3` on
[dup](./descriptors-io/dup.md)), and the documented time64 twins (kernel 5.1,
32-bit architectures) and futex2 operations (kernel 6.7) live inside their
base entry pages — the ledger still tracks every number separately so nothing
is silently swallowed.

Every per-call page follows the same skeleton: purpose, prototype and
glibc/musl wrapper story, argument table, return and error behavior, flags and
constants (values cross-checked against installed headers), side effects and
blocking behavior, security notes (capabilities, seccomp/LSM visibility),
architecture and version notes with provenance, and a primary reference (man
page section, kernel source file, or ABI document — named explicitly).

## Counting rules

- The number of syscall *names* is not a coverage metric. Multiplexed
  interfaces (`ioctl`, `fcntl`, `prctl`, `bpf`, `perf_event_open`),
  compat/legacy layers (`*32`, `*64` LFS variants, `old*` slots), arch-specific
  calls, and obsolete entries all get rows — aliases are tracked so they
  neither inflate nor hide real coverage.
- `not-started` and `source-limited` rows stay visible with their gaps named.
- x32-only and s390-only leftovers (10 rows) are explicitly inventoried but
  outside the four tabulated architectures' per-number columns.
