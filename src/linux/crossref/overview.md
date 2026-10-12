# Cross-Layer Interface Maps

Kernel features, libc functions, syscalls, and sysfs attributes are different
layers, and the mappings between them are **not one-to-one**: one libc call may
issue zero syscalls (pure userspace), several, or a version-dependent mix; one
syscall may serve dozens of libc functions; one kernel feature may need
specific glibc versions and runtime prerequisites before it is usable. This
section keeps those mappings explicit.

## The three maps

| Page | Direction | Rows |
|---|---|---|
| [libc → syscall → kernel subsystem](./libc-syscall-kernel.md) | what a libc call actually does below libc | XR-001..XR-014 |
| [sysfs class → driver model → tools](./sysfs-driver-tools.md) | how a class reaches hardware and which tools touch it | XR-101..XR-114 |
| [feature → version → availability matrix](./feature-matrix.md) | kernel feature → minimum version → libc support → runtime prerequisites | XR-201..XR-210 |

The [coverage ledger](./ledger.md) tracks all 38 rows with the same status
vocabulary as the rest of the encyclopedia (26 documented, 12 source-limited
after the wave-2 pass; source-limited rows name the exact missing source).

## Reading rules

- Arrows are typed: `wraps` (thin libc wrapper), `implements` (userspace
  fallback -- no syscall), `consumes` (reads results of), `services` (kernel
  side serving the call), `gated-by` (config/capability/version gates).
- Every syscall in a map cites its `SC-<name>` ID from the
  [syscall ledger](../syscalls/ledger.md); every class cites its `SYSC-<class>`
  ID from the [sysfs ledger](../sysfs/ledger.md); every libc function cites
  its `GLIBC-<name>` row in the [glibc ledger](../libc/ledger-glibc.md).
- Non-1:1 cases are the point, not a footnote: stdio buffering (many `printf`
  calls, zero syscalls until flush), `malloc` arena model vs `brk`/`mmap`,
  `posix_spawn` as a composite of `clone`+`execve`, NSS resolution touching no
  syscall, the vDSO serving time without entering the kernel.
