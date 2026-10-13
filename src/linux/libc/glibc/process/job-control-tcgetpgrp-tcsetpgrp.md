# `tcgetpgrp`, `tcsetpgrp` (foreground process group of a terminal) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-tcgetpgrp, GLIBC-tcsetpgrp (grouped with GLIBC-tcgetsid) |
| Header | `unistd.h` (with `sys/types.h` per manual; `tcgetsid` lives in `termios.h`, Unix98) |
| Provenance | POSIX.1 (manual *Terminal Access Functions*) |
| Exported | both `@@GLIBC_2.2.5` (nm, libc.so.6 2.41 x86_64) |
| Thread-safety | MT-Safe / AS-safe (manual safety notes) |
| Wraps | `ioctl(fd, TIOCGPGRP/TIOCSPGRP)` (manual comment "ioctl on BSD and GNU/Linux"; musl `src/unistd/tcgetpgrp.c`) |
| Status | documented |

**Semantics** -- `tcgetpgrp(fd)` returns the process group ID of the
foreground job on the terminal open on `fd`; the association is with the
terminal file, not a particular descriptor (manual). With no foreground
group (the old job died and none replaced it) it returns a value greater
than 1 that matches no existing process group. `tcsetpgrp(fd, pgid)`
installs `pgid` as foreground; the caller must share a session and
controlling terminal with `pgid`. For terminal-access purposes
`tcsetpgrp` counts as output: from a background group on the controlling
terminal it sends `SIGTTOU` to that group, unless the caller ignores or
blocks `SIGTTOU`, in which case the operation proceeds silently (manual;
tcgetpgrp.3).

**Return and errors** -- `tcgetpgrp`: pid or -1 with `EBADF`, `ENOSYS`
(no job control), `ENOTTY`; `tcsetpgrp`: 0 or -1 with `EBADF`, `EINVAL`,
`ENOSYS`, `ENOTTY`, `EPERM` (`pgid` not in the caller's session) (manual).

**Job-control context** -- foreground/background enforcement is
signal-driven: background readers get `SIGTTIN` (or `EIO` if they ignore
or block it), background writers `SIGTTOU` gated by `TOSTOP` (manual
*Access to the Controlling Terminal*). Shell plumbing: `setpgid(2)`,
`setsid(2)`.

**References** -- `tcgetpgrp(3)`; manual *Terminal Access Functions* and
*Access to the Controlling Terminal* nodes; process view:
[process overview](../../../syscalls/process/overview.md); context:
[process-control](../../../sysprog/process-control.md).
