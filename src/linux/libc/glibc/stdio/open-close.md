# `open` / `close` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

## Family B -- Low-Level Input/Output (libc wrappers)

These `unistd.h` functions are one-to-one wrappers over the syscalls
fully documented in
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md); entries here
cover only the libc-side deltas. Three facts recur:

- **Return translation.** Syscall success is a nonnegative value;
 failures surface as `-1` with `errno` set -- the wrapper is where the
 kernel's negative-error convention becomes the C convention. No
 mapping or masking happens beyond that.
- **EINTR is not retried.** glibc returns `EINTR` to the caller; the
 manual (*Interrupted Primitives*) documents that interrupted primitives
 fail with `EINTR` unless the handler was installed with `SA_RESTART`,
 and offers the `TEMP_FAILURE_RETRY` macro in `unistd.h` as the caller
 side retry loop. Nothing in the wrapper layer retries for you.
- **Close-on-exec plumbing.** Flagless wrappers (`pipe`, `dup2`) cannot
 set `FD_CLOEXEC`; glibc's answer is the GNU flag-taking variants
 `pipe2`/`dup3` (`unistd.h` gates them on `_GNU_SOURCE`), while
 `open`-style calls take `O_CLOEXEC` directly and `fopen`/`popen`
 expose the `e` mode character.

**Signature** -- `int open(const char *path, int flags, ... /* mode_t */);`
`int close(int fd);` -- `unistd.h`/`fcntl.h`.

**Libc side** -- variadic third argument for `O_CREAT`/`O_TMPFILE`;
`open64`/`openat`/`openat64` in the same ledger section. On arm64 glibc's
`open()` issues `openat(AT_FDCWD, ...)` because no `open` slot exists
(see the `open` entry in
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md)). `close`
returns `0`/`-1`+`errno`; the kernel releases the descriptor even on
`EINTR`-in-doubt paths, so retrying `close` is wrong (syscall chapter,
`close` entry). Both are raw translation wrappers; no retries, no
fallbacks.
