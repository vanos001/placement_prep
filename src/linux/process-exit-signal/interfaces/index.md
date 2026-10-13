# Signal Interfaces — Taxonomy and Index

Every named interface in the process/signals part of this book belongs to one of four layers
(IF-018). Knowing the layer tells you what guarantees you get, what portability to expect, and
which man page documents the actual contract:

| Layer | What it is | Examples in this section |
|-------|------------|--------------------------|
| **Kernel system call** | The primitive the kernel implements; documented in man-pages section 2; raw ABI, per-arch details | `kill(2)`, `sigaction(2)`/`rt_sigaction(2)`, `sigprocmask(2)`/`rt_sigprocmask(2)`, `sigpending(2)`, `sigsuspend(2)`, `sigwaitinfo(2)`/`sigtimedwait(2)`, `signalfd(2)`/`signalfd4(2)`, `pidfd_send_signal(2)`, `pidfd_open(2)`, `tgkill(2)`, `tkill(2)`, `rt_sigqueueinfo(2)`, `rt_tgsigqueueinfo(2)` |
| **libc wrapper / POSIX function** | User-space library function; may be a 1:1 wrapper or add behavior (threading, errno translation, reserved-signal filtering); man-pages section 3 or POSIX | `raise(3)`, `pthread_sigmask(3)`, `sigwait(3)`, `sigqueue(3)`, `pthread_kill(3)`, the glibc `signal(3)`/`sigaction(3)` wrappers |
| **Shell builtin** | Implemented inside the shell process; obeys shell rules (job specs, `jobspec` operands, exit-status conventions); documented by the shell | `kill` in bash/dash/zsh (`kill -n`, `kill -s`, `kill -SIGTERM %1`) |
| **External utility** | A separate program that calls the syscall family; documented by its own project | `/bin/kill` from procps-ng or GNU coreutils (`kill -s SIGNAL`, `kill -SIGNAL`, `kill -l`, `kill -t`) |

## Pages in this section

| Page | Interfaces covered | Layer (syscall underneath) | IDs |
|------|--------------------|----------------------------|-----|
| [kill, raise, and the kill utility](./kill-raise.md) | `kill(2)`, `raise(3)`, `kill(1)` utility and shell builtins | syscall `kill(2)`; `raise(3)` → glibc `pthread_kill` → `tgkill(2)` | IF-001, IF-002 |
| [sigaction and signal](./sigaction-signal.md) | `sigaction(2/3)`, `struct sigaction`, `sa_flags`, `siginfo_t`/`si_code`, `signal(2/3)` hazards | glibc `sigaction` → `rt_sigaction(2)`; glibc `signal` → `sigaction(2)` | IF-003, IF-004 |
| [Signal masks and pending signals](./signal-masks.md) | `sigprocmask(2/3)`, `pthread_sigmask(3)`, `sigpending(2/3)` | `rt_sigprocmask(2)`, `rt_sigpending(2)` | IF-005 – IF-007 |
| [Sigwait and sigsuspend](./sigwait-sigsuspend.md) | `sigwait(3)`, `sigwaitinfo(2)`/`sigtimedwait(2)`, `sigsuspend(3)` | `rt_sigtimedwait(2)`, `rt_sigsuspend(2)` | IF-008 – IF-010 |
| [signalfd and pidfd](./signalfd-pidfd.md) | `signalfd(2)`/`signalfd4(2)`, `pidfd_open(2)`, `pidfd_send_signal(2)`, `PIDFD_*` constants | `signalfd4(2)`, `pidfd_send_signal(2)` | IF-011, IF-012 |
| [tgkill](./tgkill.md) | `tgkill(2)`, `tkill(2)`, `pthread_kill(3)` | `tgkill(2)` (raw) | IF-013 |
| [rt_sig* kernel ABI](./rt-sig-syscalls.md) | `rt_sigaction(2)`, `rt_sigprocmask(2)`, `sa_restorer`, sigsetsize; cross-links to the per-syscall pages | raw syscalls | IF-014 – IF-016 |
| [Async-signal safety](./async-signal-safety.md) | The handler-programming rules: safe list, `errno`, `volatile sig_atomic_t`, self-pipe vs `signalfd`/`eventfd` | (programming rules, not a syscall) | IF-017 |

## Portability classification at a glance

| Interface | POSIX | C standard | Linux-specific? |
|-----------|-------|------------|-----------------|
| `kill(2)`, `raise(3)` | POSIX.1 | `raise` in C11 | `raise()` thread semantics are libc-specific |
| `sigaction(2)`, `sigprocmask(2)`, `sigpending(2)`, `sigsuspend(2)` | POSIX.1 | — (POSIX only) | `rt_*` syscalls, `sa_restorer` are Linux ABI |
| `signal(2)` | POSIX (semantics deliberately unspecified) | C11 (semantics vary) | glibc picks BSD semantics by default |
| `pthread_sigmask(3)`, `sigwait(3)`, `sigwaitinfo/sigtimedwait`, `sigqueue(3)` | POSIX.1-1995+ | — | time64 `*64` syscall variants on 32-bit arches |
| `signalfd(2)`, `pidfd_*(2)`, `tgkill(2)`, `tkill(2)`, `rt_sigqueueinfo(2)` | — | — | Linux-only |
| `kill` builtin/utility | POSIX utility | — | bash `-n`, coreutils `-t` are extensions |

The per-syscall pages under [syscalls/signals-time/](../../syscalls/signals-time/overview.md)
document syscall numbers, kernel introduction versions, and per-arch entry points; the glibc
catalog rows live in the libc ledger ([ledger-glibc.md](../../libc/ledger-glibc.md)). This
section adds the application-level view: semantics, races, examples, and portability.

## Related Topics

- [Standard signals](../signals/standard-signals.md) and [Real-time signals](../signals/real-time-signals.md) — the signal set these interfaces manipulate
- [Signals overview](../../sysprog/signals.md) — the survey chapter
- [Per-syscall pages: signals and time](../../syscalls/signals-time/overview.md)
- [glibc ledger](../../libc/ledger-glibc.md) — catalog rows for the libc functions referenced here

## References

- *signal(7)*, *signal-safety(7)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man7/signal.7.html>, <https://man7.org/linux/man-pages/man7/signal-safety.7.html>
- *POSIX.1-2017*, The Open Group, <https://pubs.opengroup.org/onlinepubs/9699919799/> (System Interfaces; `kill` utility in Shell & Utilities)
- *GNU Bash Reference Manual*, <https://www.gnu.org/software/bash/manual/> (kill builtin; verified against `bash(1)` as packaged in Debian)
- *GNU Coreutils manual*, <https://www.gnu.org/software/coreutils/manual/> (kill invocation; verified against `src/kill.c` in the coreutils repository)
