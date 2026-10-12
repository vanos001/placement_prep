# Process Exit Codes, Signals, and Process Lifecycle

This part is a source-backed, cross-referenced reference covering how Linux processes terminate,
how statuses are reported, and how signals behave across shells, service managers, containers,
and eight programming-language runtimes. Every chapter separates **standards guarantees**
(POSIX.1-2017, ISO C/C++) from **Linux implementation behavior** (kernel, glibc), **runtime
implementation behavior**, and **mere conventions** — and cites the primary source that supports
each claim. Coverage is tracked requirement-by-requirement in the
[unified coverage ledger](../process-exit-signal-coverage.md), which assigns stable IDs to
every signal, interface, shell, service manager, container topic, and language requirement in
scope.

## Chapter map

| Section | Chapters | Ledger IDs |
|---------|----------|------------|
| [Signals — Deep Reference](./signals/index.md) | [Standard signals](./signals/standard-signals.md) (all 31, per-architecture numbering) · [Real-time signals](./signals/real-time-signals.md) (queuing, ordering, limits) | SIG-001 – SIG-040 |
| [Signal interfaces](./interfaces/index.md) | `kill`/`raise` · `sigaction`/`signal` · masks (`sigprocmask`/`pthread_sigmask`/`sigpending`) · `sigwait`/`sigsuspend` · `signalfd`/`pidfd_send_signal` · `tgkill` · `rt_sig*` ABI · async-signal-safety | IF-001 – IF-018 |
| [Exit-status lifecycle](./exit-status/index.md) | [Lifecycle](./exit-status/lifecycle.md) (`exit`/`_exit`/`wait` family, status encoding, zombies) · [Conventions](./exit-status/conventions.md) (common values, guarantees vs conventions) | EX-001 – EX-012 |
| [Shell behavior](./shells/index.md) | [Bash](./shells/bash.md) · [Dash](./shells/dash.md) · [Zsh](./shells/zsh.md) · [Portability matrix](./shells/index.md) | SH-001 – SH-012 |
| [Service managers](./service-managers/index.md) | [systemd](./service-managers/systemd.md) · [OpenRC](./service-managers/openrc.md) · [runit](./service-managers/runit.md) · [s6](./service-managers/s6.md) · [comparison](./service-managers/index.md) | SM-001 – SM-012 |
| [Containers & orchestration](./containers/index.md) | [PID 1 & entrypoints](./containers/pid1-signals.md) · [Docker](./containers/docker.md) · [Kubernetes](./containers/kubernetes.md) · [scenarios](./containers/troubleshooting-scenarios.md) | CT-001 – CT-011 |
| [Language chapters](./languages/comparison.md) | [C](./languages/c.md) · [C++](./languages/cpp.md) · [Python](./languages/python.md) · [Go](./languages/go.md) · [Java](./languages/java.md) · [Rust](./languages/rust.md) · [Node.js](./languages/nodejs.md) · [OCaml](./languages/ocaml.md) · [Cross-language comparison](./languages/comparison.md) | LG-* · XC-001 – XC-009 |
| [Operational troubleshooting](./troubleshooting/index.md) | [Common status values](./troubleshooting/common-status-values.md) · [Decision tree](./troubleshooting/decision-tree.md) | TR-001 – TR-009 |

## Scope statement

- **Signal numbering** is verified per architecture from the Linux kernel UAPI headers
  (`include/uapi/asm-generic/signal.h` plus per-arch overrides) and [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html);
  the inventory names the architectures it covers and claims no completeness beyond them.
- **Interfaces** are documented from Linux man-pages, POSIX.1-2017, and the glibc documentation,
  with kernel-syscall / libc-wrapper / shell-builtin / utility layering kept explicit.
- **Shells** covered: Bash, Dash, Zsh (version claims stated per manual).
- **Service managers** covered: systemd, OpenRC, runit, s6 — from official project documentation.
- **Containers**: Docker-compatible runtimes and Kubernetes, from official runtime/orchestrator docs.
- **Languages** covered: C, C++, Python, Go, Java, Rust, Node.js, OCaml — each chapter declares its
  documentation version scope and carries its own end-of-chapter coverage ledger with per-API statuses,
  including honestly marked `source-limited` rows.

## Related Topics

- [Signals (existing survey chapter)](../sysprog/signals.md) — the book's earlier programming-model introduction; this part deepens it with source-backed per-requirement coverage
- [Process control (existing chapter)](../sysprog/process-control.md) — `fork`/`exec`/`wait` survey material
- [Init systems (existing part)](../init-systems/README.md) — broader init-system architecture beyond termination semantics
- [Containers (existing part)](../containers/overview.md) — container internals beyond exit/signal propagation
