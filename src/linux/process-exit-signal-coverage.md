# Process Exit Codes, Signals, and Lifecycle — Unified Coverage Ledger

This ledger is the authoritative inventory for the [process exit and signal knowledge base](./process-exit-signal/index.md).
It seeds every identified requirement with a stable ID before documentation work begins; statuses are
updated only when the required explanation, examples (where required), and cited references actually exist.

**Status vocabulary** (same as the rest of this book):

- `not-started` — requirement identified with a stable ID and source; no documentation page yet.
- `researched` — primary sources read; brief entry exists.
- `documented` — full explanation, examples where required, and references that support the claims exist at the linked path.
- `source-limited` — documentation attempted but a named primary source was unreachable; the entry states what is missing.

**Scope statement.** The signal inventory covers the architectures documented by the Linux kernel's
`arch/` tree signal headers and cross-checked against `man 7 signal`: alpha, arc, arm, arm64, csky,
hexagon, loongarch, m68k, microblaze, mips, nios2, openrisc, parisc, powerpc, riscv, s390, sh, sparc,
x86 (i386 and x86-64), and xtensa. Per-architecture numbering is verified from the kernel source
`include/uapi/asm-generic/signal.h` and per-arch overrides; claims are stated per architecture, never
universally. Interface signatures are verified against man-pages and glibc/musl documentation; shell
claims against Bash, Dash, and Zsh manuals; service-manager claims against official project docs;
language claims against official language/library/runtime references at the versions stated in each chapter.

Requirement-ID derivation: requirements were derived from the challenge specification (sections 2–11)
plus the APIs those sections name, decomposed into individually verifiable rows. Named systems, signals,
interfaces, languages, and comparison requirements each carry IDs. Language chapters additionally carry
per-language ledger sections with canonical signatures.

## 1. Standard signals (section 2)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| SIG-001 | SIGHUP (1): purpose, default action, catchability, arch numbering | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; kernel signal.h per-arch | Linux; all arch in scope | not-started |
| SIG-002 | SIGINT (2) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-003 | SIGQUIT (3), core-dump behavior | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-004 | SIGILL (4) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-005 | SIGTRAP (5), ptrace interplay | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; ptrace(2) | Linux; all arch | not-started |
| SIG-006 | SIGABRT (6) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; abort(3) | Linux; all arch | not-started |
| SIG-007 | SIGBUS (7), arch-dependent on some | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-008 | SIGFPE (8) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-009 | SIGKILL (9), uncatchable semantics | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-010 | SIGUSR1 (10 / 16 per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-011 | SIGSEGV (11) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-012 | SIGUSR2 (12 / 17 per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-013 | SIGPIPE (13) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-014 | SIGALRM (14) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-015 | SIGTERM (15) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-016 | SIGSTKFLT (16; not on all arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; kernel per-arch headers | Linux; x86, m68k, others; absent on alpha/sparc | not-started |
| SIG-017 | SIGCHLD (17 / 20 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-018 | SIGCONT (18 / 19 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-019 | SIGSTOP (19 / 18 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-020 | SIGTSTP (20 / 18 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-021 | SIGTTIN (21 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-022 | SIGTTOU (22 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-023 | SIGURG (23 / 16 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-024 | SIGXCPU (24 / 30 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-025 | SIGXFSZ (25 / 25 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-026 | SIGVTALRM (26 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-027 | SIGPROF (27 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-028 | SIGWINCH (28 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-029 | SIGIO/SIGPOLL (29 / 23 / others per-arch) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-030 | SIGPWR (30 / 19 / others per-arch; absent where SIGLOST) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; most arch | not-started |
| SIG-031 | SIGSYS/SIGUNUSED (31) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal | Linux; all arch | not-started |
| SIG-032 | Architecture numbering table (all 31 across the arch set) | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | kernel include/uapi/asm*/signal.h | 21 arch named in scope statement | not-started |
| SIG-033 | Signal dispositions: default/ignore/handler, catchability rules, what SIGKILL/SIGSTOP cannot do | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; POSIX.1-2017 XSH 2.4 | Linux + POSIX | not-started |
| SIG-034 | Generation vs delivery: standard signals do not queue, pending set, blocking | [signals/standard-signals.md](./process-exit-signal/signals/standard-signals.md) | man 7 signal; POSIX | Linux + POSIX | not-started |
| SIG-035 | Real-time signal range SIGRTMIN..SIGRTMAX, glibc vs kernel placement | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 7 signal; glibc manual | Linux; glibc ≥2.1 | not-started |
| SIG-036 | Real-time queuing guarantees, multiple pending instances | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 7 signal; POSIX.1-2017 | Linux + POSIX | not-started |
| SIG-037 | Real-time delivery ordering: lower numbers first, queued order within a number | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 7 signal; POSIX | Linux + POSIX | not-started |
| SIG-038 | Real-time queue limits: RLIMIT_SIGPENDING, /proc/sys/kernel/rtsig-max history, EAGAIN | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 7 signal; setrlimit(2); kernel docs | Linux | not-started |
| SIG-039 | sigqueue(3)/rt_sigqueueinfo: sending queued signals with value | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 2 rt_sigqueueinfo; man 3 sigqueue | Linux | not-started |
| SIG-040 | Real-time vs standard signal practical trade-offs and misconceptions | [signals/real-time-signals.md](./process-exit-signal/signals/real-time-signals.md) | man 7 signal | Linux | not-started |

## 2. Signal interfaces (section 3)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| IF-001 | kill(2): declaration, semantics, pid rules, errors; kill(1) utility and shell builtin differences | [interfaces/kill-raise.md](./process-exit-signal/interfaces/kill-raise.md) | man 2 kill; POSIX; coreutils; bash manual | Linux + POSIX | not-started |
| IF-002 | raise(3): declaration, thread semantics vs kill(getpid()), C11 vs POSIX | [interfaces/kill-raise.md](./process-exit-signal/interfaces/kill-raise.md) | man 3 raise; C11 7.14.2.1; glibc manual | C11 + POSIX | not-started |
| IF-003 | sigaction(2/3): struct sigaction, flags, SA_SIGINFO, sa_restorer | [interfaces/sigaction-signal.md](./process-exit-signal/interfaces/sigaction-signal.md) | man 2 sigaction; POSIX | Linux + POSIX | not-started |
| IF-004 | signal(2/3): portability hazards, BSD vs SysV semantics, glibc behavior | [interfaces/sigaction-signal.md](./process-exit-signal/interfaces/sigaction-signal.md) | man 2 signal; man 3 signal; glibc manual | Linux + POSIX | not-started |
| IF-005 | sigprocmask(2/3): how values, restrictions in threads | [interfaces/signal-masks.md](./process-exit-signal/interfaces/signal-masks.md) | man 2 sigprocmask; POSIX | Linux + POSIX | not-started |
| IF-006 | pthread_sigmask(3): thread-local masks, errors, examples | [interfaces/signal-masks.md](./process-exit-signal/interfaces/signal-masks.md) | man 3 pthread_sigmask; POSIX | POSIX threads | not-started |
| IF-007 | sigpending(2/3): pending-set semantics, thread view | [interfaces/signal-masks.md](./process-exit-signal/interfaces/signal-masks.md) | man 2 sigpending; POSIX | Linux + POSIX | not-started |
| IF-008 | sigwait(3): semantics, consuming pending signals, thread-safety | [interfaces/sigwait-sigsuspend.md](./process-exit-signal/interfaces/sigwait-sigsuspend.md) | man 3 sigwait; POSIX | POSIX | not-started |
| IF-009 | sigwaitinfo/sigtimedwait(2/3) and sigtimedwait64 variants | [interfaces/sigwait-sigsuspend.md](./process-exit-signal/interfaces/sigwait-sigsuspend.md) | man 2 sigtimedwait; POSIX | Linux + POSIX | not-started |
| IF-010 | sigsuspend(3): atomic mask swap, race-free waiting | [interfaces/sigwait-sigsuspend.md](./process-exit-signal/interfaces/sigwait-sigsuspend.md) | man 3 sigsuspend; POSIX | POSIX | not-started |
| IF-011 | signalfd(2)/signalfd4(2): fd-based signal consumption, epoll interplay | [interfaces/signalfd-pidfd.md](./process-exit-signal/interfaces/signalfd-pidfd.md) | man 2 signalfd | Linux ≥2.6.22, glibc ≥2.8 | not-started |
| IF-012 | pidfd_send_signal(2): pidfd-based signaling, race avoidance | [interfaces/signalfd-pidfd.md](./process-exit-signal/interfaces/signalfd-pidfd.md) | man 2 pidfd_send_signal; pidfd_open(2) | Linux ≥5.1 | not-started |
| IF-013 | tgkill(2) and tkill(2): thread-directed signals, library use | [interfaces/tgkill.md](./process-exit-signal/interfaces/tgkill.md) | man 2 tgkill | Linux | not-started |
| IF-014 | rt_sigaction(2): kernel ABI, struct layout, sa_restorer, glibc wrapper differences | [interfaces/rt-sig-syscalls.md](./process-exit-signal/interfaces/rt-sig-syscalls.md) | man 2 sigaction NOTES; kernel source | Linux; per-arch ABI | not-started |
| IF-015 | rt_sigprocmask(2): kernel ABI vs libc sigprocmask | [interfaces/rt-sig-syscalls.md](./process-exit-signal/interfaces/rt-sig-syscalls.md) | kernel source; man 2 sigprocmask | Linux; per-arch ABI | not-started |
| IF-016 | Related: sigqueue/sigwaitinfo family cross-links and existing per-syscall pages (rt_sigsuspend, sigaltstack, sigreturn, pause) | [interfaces/rt-sig-syscalls.md](./process-exit-signal/interfaces/rt-sig-syscalls.md) | man 7 signal; existing syscalls/ pages | Linux | not-started |
| IF-017 | Async-signal-safety: rules, safe function list, handler patterns | [interfaces/async-signal-safety.md](./process-exit-signal/interfaces/async-signal-safety.md) | man 7 signal-safety | Linux/glibc | not-started |
| IF-018 | Interface category taxonomy: kernel syscall vs libc wrapper vs shell builtin vs external utility, per interface | [interfaces/index.md](./process-exit-signal/interfaces/index.md) | man pages; glibc; bash/dash manuals | Linux | not-started |

## 3. Exit-status lifecycle and conventions (section 4)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| EX-001 | exit(3): flush, atexit handlers, C standard guarantees | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 3 exit; C11 7.22.4.4; POSIX | C11 + POSIX | not-started |
| EX-002 | _exit(2)/_Exit(3): immediate termination, no cleanup, difference from exit | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 _exit; C11; POSIX | Linux + C11 + POSIX | not-started |
| EX-003 | wait(2)/waitpid(2)/waitid(2): status retrieval, W* macros, wait3/wait4 legacy | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 wait; POSIX | Linux + POSIX | not-started |
| EX-004 | Status encoding: 16-bit wait status layout, WIFEXITED/WEXITSTATUS/WIFSIGNALED/WTERMSIG/WCOREDUMP/WIFSTOPPED/WSTOPSIG/WIFCONTINUED | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 wait; kernel include/uapi linux/wait.h | Linux + POSIX | not-started |
| EX-005 | Exit-status truncation to 8 bits: where it happens, what is lost | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 3 exit; POSIX 2.8.2 | POSIX + Linux | not-started |
| EX-006 | Normal exit vs signal termination vs core dump: what the parent observes | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 wait; man 5 core | Linux + POSIX | not-started |
| EX-007 | Stopped and continued children: WUNTRACED/WCONTINUED, waitid targets | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 wait; POSIX | Linux + POSIX | not-started |
| EX-008 | Zombies and orphans: reaping, SIGCHLD, init/systemd reaping duty | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | man 2 wait; man 7 signal | Linux | not-started |
| EX-009 | Termination vs status collection vs shell reporting: three distinct layers | [exit-status/lifecycle.md](./process-exit-signal/exit-status/lifecycle.md) | POSIX 2.8; shell manuals | POSIX + shells | not-started |
| EX-010 | Common status conventions table: 0, 1, 2, 126, 127, 128+N, 130, 137, 139, 143; guarantees vs conventions | [exit-status/conventions.md](./process-exit-signal/exit-status/conventions.md) | POSIX 2.8.2; coreutils; bash manual | POSIX + shells + coreutils | not-started |
| EX-011 | Why one integer cannot establish cause: evidence needed to confirm interpretations | [exit-status/conventions.md](./process-exit-signal/exit-status/conventions.md) | POSIX; coreutils docs | POSIX + Linux | not-started |
| EX-012 | Convention consumers: shells, coreutils, service managers, container runtimes, orchestrators | [exit-status/conventions.md](./process-exit-signal/exit-status/conventions.md) | respective official docs | Linux ecosystem | not-started |

## 4. Shell behavior (section 5)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| SH-001 | Bash pipeline status and pipefail | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual | bash ≥2.0 (pipefail ≥3.0) | not-started |
| SH-002 | Bash `$?`, PIPESTATUS, PROMPT_COMMAND tracing | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual | bash | not-started |
| SH-003 | Bash command substitution, subshell status propagation | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual | bash | not-started |
| SH-004 | Bash traps, signal delivery to shell vs children, `wait` semantics | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual; POSIX 2.11 | bash | not-started |
| SH-005 | Bash async jobs, background processes, job control, `wait -n` | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual | bash ≥4.3 for wait -n | not-started |
| SH-006 | Bash exit-status propagation rules: simple commands, lists, functions | [shells/bash.md](./process-exit-signal/shells/bash.md) | bash manual; POSIX 2.8/2.9 | bash | not-started |
| SH-007 | Dash pipeline status, `$?`, traps, no PIPESTATUS; POSIX conformance notes | [shells/dash.md](./process-exit-signal/shells/dash.md) | dash(1) manual; POSIX.1-2017 | dash 0.5.x | not-started |
| SH-008 | Dash command substitution, async jobs, signal handling differences from bash | [shells/dash.md](./process-exit-signal/shells/dash.md) | dash(1) manual; POSIX | dash 0.5.x | not-started |
| SH-009 | Zsh pipeline status, pipefail, pipestatus array (case difference vs bash) | [shells/zsh.md](./process-exit-signal/shells/zsh.md) | zsh manual | zsh ≥5.x | not-started |
| SH-010 | Zsh traps, TRAPxxx functions, signals, job control | [shells/zsh.md](./process-exit-signal/shells/zsh.md) | zsh manual | zsh ≥5.x | not-started |
| SH-011 | Zsh command substitution, background jobs, exit propagation | [shells/zsh.md](./process-exit-signal/shells/zsh.md) | zsh manual | zsh ≥5.x | not-started |
| SH-012 | Cross-shell portability matrix and documented version differences | [shells/index.md](./process-exit-signal/shells/index.md) | all three manuals; POSIX | bash/dash/zsh | not-started |

## 5. Service managers and supervisors (section 6)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| SM-001 | systemd: clean vs abnormal termination handling, MainPID | [service-managers/systemd.md](./process-exit-signal/service-managers/systemd.md) | systemd.exec(5), systemd.service(5) | systemd ≥2xx, versioned where needed | not-started |
| SM-002 | systemd: Restart= policies, StartLimitIntervalSec/Burst, restart loops | [service-managers/systemd.md](./process-exit-signal/service-managers/systemd.md) | systemd.service(5) | systemd (v230+ renames) | not-started |
| SM-003 | systemd: KillMode, KillSignal, TimeoutStopSec, escalation SIGTERM→SIGKILL | [service-managers/systemd.md](./process-exit-signal/service-managers/systemd.md) | systemd.kill(5), systemd.service(5) | systemd | not-started |
| SM-004 | systemd: SuccessExitStatus, RestartPreventExitStatus, RestartForceExitStatus | [service-managers/systemd.md](./process-exit-signal/service-managers/systemd.md) | systemd.service(5) | systemd | not-started |
| SM-005 | systemd: supervision model, cgroups, child reaping, failure reporting | [service-managers/systemd.md](./process-exit-signal/service-managers/systemd.md) | systemd docs | systemd | not-started |
| SM-006 | OpenRC: supervision options, start/stop semantics, signal handling | [service-managers/openrc.md](./process-exit-signal/service-managers/openrc.md) | OpenRC guide, openrc-run(8), man pages | OpenRC ≥0.4x | not-started |
| SM-007 | OpenRC: restart limits (if any), retry/timeout options | [service-managers/openrc.md](./process-exit-signal/service-managers/openrc.md) | OpenRC docs | OpenRC | not-started |
| SM-008 | runit: stage-based supervision, ./run ./finish, exit-status semantics | [service-managers/runit.md](./process-exit-signal/service-managers/runit.md) | runit(8), runsv(8) docs | runit 2.x | not-started |
| SM-009 | runit: restart-on-exit behavior, sv control signals | [service-managers/runit.md](./process-exit-signal/service-managers/runit.md) | runsv(8) | runit 2.x | not-started |
| SM-010 | s6: supervision tree, s6-supervise, finish scripts, exit codes | [service-managers/s6.md](./process-exit-signal/service-managers/s6.md) | s6 docs (skarnet.org) | s6 2.x | not-started |
| SM-011 | s6: s6-svscan/s6-svcdt, down files, restart behavior, notification fd | [service-managers/s6.md](./process-exit-signal/service-managers/s6.md) | s6 docs | s6 2.x | not-started |
| SM-012 | Cross-manager comparison: stop signals, timeouts, escalation, restart conditions | [service-managers/index.md](./process-exit-signal/service-managers/index.md) | all four official docs | four managers | not-started |

## 6. Containers and orchestration (section 7)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| CT-001 | PID 1 responsibilities in containers: signal dispatch, default dispositions, reaping | [containers/pid1-signals.md](./process-exit-signal/containers/pid1-signals.md) | man 7 signal; docker docs | Linux; docker | not-started |
| CT-002 | Shell entrypoints (sh -c) as PID 1: signal non-forwarding, exec workaround | [containers/pid1-signals.md](./process-exit-signal/containers/pid1-signals.md) | docker docs; shell manuals | POSIX shells | not-started |
| CT-003 | Docker: STOPSIGNAL, stop grace period, docker kill/stop, signal forwarding | [containers/docker.md](./process-exit-signal/containers/docker.md) | Docker reference docs | Docker Engine | not-started |
| CT-004 | Docker: exit codes from containerized processes, 128+N representation, `docker inspect` State | [containers/docker.md](./process-exit-signal/containers/docker.md) | Docker reference | Docker Engine | not-started |
| CT-005 | Docker: OOM killer State.OOMKilled, memory limits, what 137 does and does not prove | [containers/docker.md](./process-exit-signal/containers/docker.md) | Docker docs; kernel oom docs | Docker Engine | not-started |
| CT-006 | Kubernetes: kubelet termination flow, grace periods, terminationMessagePolicy | [containers/kubernetes.md](./process-exit-signal/containers/kubernetes.md) | k8s docs | k8s ≥1.x (versioned) | not-started |
| CT-007 | Kubernetes: exit-code and signal-based restart decisions, CrashLoopBackOff | [containers/kubernetes.md](./process-exit-signal/containers/kubernetes.md) | k8s docs | k8s | not-started |
| CT-008 | Kubernetes: OOMKilled reason vs exit code 137 evidence requirements, eviction vs OOM | [containers/kubernetes.md](./process-exit-signal/containers/kubernetes.md) | k8s docs | k8s | not-started |
| CT-009 | Zombie reaping in containers: tini/dumb-init/runtime reapers | [containers/pid1-signals.md](./process-exit-signal/containers/pid1-signals.md) | tini docs; runtime docs | Linux; docker/k8s | not-started |
| CT-010 | Nested processes, wrapper scripts, transformed or lost statuses through layers | [containers/pid1-signals.md](./process-exit-signal/containers/pid1-signals.md) | runtime docs | Linux; docker/k8s | not-started |
| CT-011 | Troubleshooting scenarios: shutdown races, ignored SIGTERM, lost exit reasons | [containers/troubleshooting-scenarios.md](./process-exit-signal/containers/troubleshooting-scenarios.md) | docker + k8s docs | Docker + k8s | not-started |

## 7. Language chapters (section 8)

Shared coverage areas per language: syntax/semantics (A), API inventory (B), lifecycle/termination (C),
signals/OS interaction (D), subprocess management (E), concurrency/resource semantics (F).

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| LG-C-001 | C: main, return from main, exit/_Exit/abort/atexit/quick_exit/at_quick_exit, C11/C23 differences | [languages/c.md](./process-exit-signal/languages/c.md) | C11/C23 standards; man pages | C11/C23 + POSIX | not-started |
| LG-C-002 | C: exit-status representation and truncation, termination vs threads vs children | [languages/c.md](./process-exit-signal/languages/c.md) | C11; POSIX | C11 + POSIX | not-started |
| LG-C-003 | C: signal(3)/sigaction(2) usage from C, UB list, async-signal-safety, handler restrictions | [languages/c.md](./process-exit-signal/languages/c.md) | C11 7.14; man 7 signal-safety | C11 + POSIX | not-started |
| LG-C-004 | C: fork/exec/wait family, posix_spawn, status macros, examples | [languages/c.md](./process-exit-signal/languages/c.md) | POSIX; man pages | POSIX | not-started |
| LG-C-005 | C: threads (pthread_kill, cancellation), buffered stdio hazards, FD ownership | [languages/c.md](./process-exit-signal/languages/c.md) | POSIX; man pages | POSIX | not-started |
| LG-C-006 | C: API inventory rows with verified signatures (see language ledger below) | [languages/c.md](./process-exit-signal/languages/c.md) | man pages; C standard | C11/C23 + POSIX | not-started |
| LG-CPP-001 | C++: main, std::exit/_Exit/quick_exit/abort, termination handlers | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard (cppreference as mirror) | C++17/20/23 | not-started |
| LG-CPP-002 | C++: which paths skip automatic-object destruction; static destruction; buffered streams | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard | C++17+ | not-started |
| LG-CPP-003 | C++: stack unwinding, exceptions, terminate/abort, noexcept | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard | C++17+ | not-started |
| LG-CPP-004 | C++: RAII cleanup guarantees across termination paths; std::system and subprocess | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard; POSIX for process APIs | C++17+ | not-started |
| LG-CPP-005 | C++: signals from C library in C++ programs; interactions with exceptions | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard; man 7 signal-safety | C++ + POSIX | not-started |
| LG-CPP-006 | C++: API inventory rows with verified signatures (see language ledger below) | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | C++ standard | C++17+ | not-started |
| LG-PY-001 | Python: sys.exit/SystemExit, os._exit, os.abort, atexit, exception propagation, interpreter shutdown | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org | Python 3.x (versioned) | not-started |
| LG-PY-002 | Python: exit status derivation from exceptions, unhandled exceptions, Py_Finalize behavior | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org; CPython source | CPython 3.x | not-started |
| LG-PY-003 | Python: signal module, handlers run in main thread, signal.signal/ITIMER, CPython restrictions | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org signal | CPython 3.x | not-started |
| LG-PY-004 | Python: subprocess.Popen/run, CompletedProcess, returncode, pipes, timeouts, process groups, start_new_session | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org subprocess | Python 3.x | not-started |
| LG-PY-005 | Python: asyncio subprocesses, multiprocessing termination semantics | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org | Python 3.x | not-started |
| LG-PY-006 | Python: CPython-specific vs language-guarantee separation; API inventory rows | [languages/python.md](./process-exit-signal/languages/python.md) | docs.python.org; CPython docs | CPython 3.x | not-started |
| LG-GO-001 | Go: os.Exit, return from main, log.Fatal, panic/recover, deferred calls per path | [languages/go.md](./process-exit-signal/languages/go.md) | go.dev/pkg docs; spec | Go 1.2x (versioned) | not-started |
| LG-GO-002 | Go: runtime shutdown, which defers run on os.Exit vs panic, exit status from panics | [languages/go.md](./process-exit-signal/languages/go.md) | go spec; runtime docs | Go 1.2x | not-started |
| LG-GO-003 | Go: os/signal.Notify, Signal type, context-based shutdown patterns, runtime restrictions in handlers | [languages/go.md](./process-exit-signal/languages/go.md) | os/signal docs | Go 1.2x | not-started |
| LG-GO-004 | Go: os/exec Cmd/Process/ProcessState/ExitCode/WaitStatus, pipes, contexts, cancellation | [languages/go.md](./process-exit-signal/languages/go.md) | os/exec, os docs | Go 1.2x | not-started |
| LG-GO-005 | Go: goroutines, threads, GOMAXPROCS interaction with signals; API inventory rows | [languages/go.md](./process-exit-signal/languages/go.md) | go docs | Go 1.2x | not-started |
| LG-JA-001 | Java: JVM startup/shutdown, return from main, System.exit/Runtime.exit/Runtime.halt | [languages/java.md](./process-exit-signal/languages/java.md) | docs.oracle.com (JDK versioned) | JDK ≥11 (versioned) | not-started |
| LG-JA-002 | Java: shutdown hooks, ordering, halt skips hooks, uncaught exception handler → exit status | [languages/java.md](./process-exit-signal/languages/java.md) | JDK API docs; JVM spec | JDK ≥11 | not-started |
| LG-JA-003 | Java: ProcessBuilder/Process/ProcessHandle, waitFor/exitValue/destroy/destroyForcibly/onExit | [languages/java.md](./process-exit-signal/languages/java.md) | JDK API docs | JDK ≥9 for ProcessHandle | not-started |
| LG-JA-004 | Java: process I/O streams, deadlocks, timeouts, descendants, interruption | [languages/java.md](./process-exit-signal/languages/java.md) | JDK API docs | JDK ≥11 | not-started |
| LG-JA-005 | Java: signals via sun.misc.Signal / jdk.internal, JVM-internal signal use; API inventory rows | [languages/java.md](./process-exit-signal/languages/java.md) | JDK docs; HotSpot docs | JDK (HotSpot) | not-started |
| LG-RU-001 | Rust: return from main, std::process::exit, abort, panic strategies (unwind/abort), destructors per path | [languages/rust.md](./process-exit-signal/languages/rust.md) | doc.rust-lang.org std; Rust reference | Rust 1.7x+ (versioned) | not-started |
| LG-RU-002 | Rust: panic hook, catch_unwind, ExitCode trait From-return from main (1.61+) | [languages/rust.md](./process-exit-signal/languages/rust.md) | std docs | Rust ≥1.61 | not-started |
| LG-RU-003 | Rust: std::process::Command/Child/ExitStatus/ExitCode/Output/Stdio, Unix ext traits | [languages/rust.md](./process-exit-signal/languages/rust.md) | std docs | Rust 1.7x+ | not-started |
| LG-RU-004 | Rust: ownership/drop on exit/abort/panic; signal crates position (no std signal API) | [languages/rust.md](./process-exit-signal/languages/rust.md) | std docs; nomicon | Rust | not-started |
| LG-RU-005 | Rust: threads, scoped threads, std::process child cleanup on drop; API inventory rows | [languages/rust.md](./process-exit-signal/languages/rust.md) | std docs | Rust | not-started |
| LG-NO-001 | Node.js: event-loop completion, process.exit/exitCode/abort, uncaught exceptions, unhandled rejections | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | nodejs.org/api | Node ≥18 LTS (versioned) | not-started |
| LG-NO-002 | Node.js: signal events, process.on(SIGxxx), default behaviors, shutdown, flushing hazards with process.exit | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | nodejs.org/api process | Node ≥18 | not-started |
| LG-NO-003 | Node.js: child_process spawn/exec/execFile/fork + sync variants, code vs signal, exit vs close | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | nodejs.org/api child_process | Node ≥18 | not-started |
| LG-NO-004 | Node.js: pipes, stdio options, stream closure, kill, cancellation (AbortSignal), cleanup | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | nodejs.org/api | Node ≥18 | not-started |
| LG-NO-005 | Node.js: event-loop state effects, libuv threadpool position; API inventory rows | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | nodejs.org docs | Node ≥18 | not-started |
| LG-OC-001 | OCaml: Stdlib exit/at_exit, exceptions, propagation, backtraces, runtime shutdown | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | ocaml.org manual | OCaml 5.x (versioned) | not-started |
| LG-OC-002 | OCaml: Sys.error_message/Sys.exit semantics, uncaught exception exit status 2 | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | OCaml manual | OCaml 5.x | not-started |
| LG-OC-003 | OCaml: Unix fork/exec/wait/kill/signal/sigprocmask, Unix.process_status constructors | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | OCaml Unix library manual | OCaml 5.x | not-started |
| LG-OC-004 | OCaml: Unix.open_process_*/close_process_*, pipes, deadlock hazards, waiting | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | OCaml Unix manual | OCaml 5.x | not-started |
| LG-OC-005 | OCaml: signal handling with runtime/threads restrictions (Sys.signal, Signal module), effects runtime deltas | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | OCaml manual; Stdlib.Signal | OCaml 5.x | not-started |
| LG-OC-006 | OCaml: API inventory with verified signatures against official docs (no invented APIs) | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | ocaml.org API docs | OCaml 5.x | not-started |

## 8. Cross-language comparison (section 8.3)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| XC-001 | Normal return vs explicit termination across 8 languages | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-002 | Cleanup/finalization guarantees across termination paths | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-003 | Exceptions/panics/fatal errors/abort mapping table | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-004 | Signal registration and handling models compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-005 | Subprocess creation/waiting/cancellation/termination compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-006 | Child-status representations and signal interpretation compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-007 | Pipe and stream behavior compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-008 | Threading and runtime restrictions compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |
| XC-009 | Portability and version dependencies compared | [languages/comparison.md](./process-exit-signal/languages/comparison.md) | per-language refs | 8 languages | not-started |

## 9. Operational troubleshooting (section 9)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| TR-001 | Status values 126, 127, 128+N, 137, 139, 143: meanings, conventions vs guarantees, confirming evidence | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | POSIX; coreutils; shells; runtimes | POSIX + Linux ecosystem | not-started |
| TR-002 | SIGTERM vs SIGKILL operational differences and shutdown races | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | man 7 signal; runtime docs | Linux | not-started |
| TR-003 | Segmentation faults and core dumps: capture, analysis, core_pattern | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | man 5 core; systemd-coredump | Linux | not-started |
| TR-004 | OOM kills and rlimit failures: oom_score, dmesg evidence, cgroup memory events | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | kernel docs; man pages | Linux | not-started |
| TR-005 | Failed exec, permission errors, missing commands: shell and runtime evidence | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | POSIX; shell manuals; man 2 execve | POSIX + Linux | not-started |
| TR-006 | Pipeline, shell-wrapper, and subprocess failure attribution | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | shell manuals | shells | not-started |
| TR-007 | Service-manager restarts and container termination diagnosis | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | systemd docs; docker/k8s docs | systemd + docker + k8s | not-started |
| TR-008 | Signal masking, ignored signals, shutdown races: detection and diagnosis | [troubleshooting/common-status-values.md](./process-exit-signal/troubleshooting/common-status-values.md) | man 7 signal | Linux | not-started |
| TR-009 | Decision tree from observed status + evidence to plausible causes (no overclaiming) | [troubleshooting/decision-tree.md](./process-exit-signal/troubleshooting/decision-tree.md) | synthesized; cited per node | Linux ecosystem | not-started |

## 10. Navigation and integration (section 12)

| ID | Requirement or API | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|
| NAV-001 | Part index page reachable from SUMMARY.md | [index.md](./process-exit-signal/index.md) | — | — | not-started |
| NAV-002 | SUMMARY.md entries for every chapter | [../../SUMMARY.md](../../SUMMARY.md) | — | — | not-started |
| NAV-003 | Cross-links: signals ↔ interfaces ↔ languages ↔ troubleshooting ↔ containers ↔ service managers | per-chapter "Related" sections | — | — | not-started |
| NAV-004 | No duplicate chapters with existing book pages; reuse/cross-link instead | per-chapter links to existing pages | — | — | not-started |
| NAV-005 | This ledger consistent with language sub-ledgers | this file | — | — | not-started |

## Category rollup

Updated at integration time; counts must match the rows above.

| Category | Total | documented | remaining | source-limited |
|---|---|---|---|---|
| Standard signals (SIG) | 40 | 0 | 40 | 0 |
| Signal interfaces (IF) | 18 | 0 | 18 | 0 |
| Exit-status lifecycle (EX) | 12 | 0 | 12 | 0 |
| Shells (SH) | 12 | 0 | 12 | 0 |
| Service managers (SM) | 12 | 0 | 12 | 0 |
| Containers (CT) | 11 | 0 | 11 | 0 |
| Languages (LG) | 46 | 0 | 46 | 0 |
| Comparison (XC) | 9 | 0 | 9 | 0 |
| Troubleshooting (TR) | 9 | 0 | 9 | 0 |
| Navigation (NAV) | 5 | 0 | 5 | 0 |
| **Total** | **174** | **0** | **174** | **0** |

## Language-specific ledger addendum (canonical signatures)

Per-language API inventory rows with verified signatures live at the end of each language chapter
(sections titled "Coverage ledger"), and are cross-referenced from here. The main ledger row for each
language (LG-*-006 etc.) is marked `documented` only when that chapter's ledger exists, signatures are
verified against the official reference named there, and the remaining/source-limited counts are reported.

| Language | Chapter | Ledger location | Signature source of truth |
|---|---|---|---|
| C | [languages/c.md](./process-exit-signal/languages/c.md) | end of chapter | C11/C23 standard text; man-pages 6.x |
| C++ | [languages/cpp.md](./process-exit-signal/languages/cpp.md) | end of chapter | ISO C++ standard (via cppreference, stated) |
| Python | [languages/python.md](./process-exit-signal/languages/python.md) | end of chapter | docs.python.org 3.x library reference |
| Go | [languages/go.md](./process-exit-signal/languages/go.md) | end of chapter | pkg.go.dev stdlib docs |
| Java | [languages/java.md](./process-exit-signal/languages/java.md) | end of chapter | docs.oracle.com JDK API docs |
| Rust | [languages/rust.md](./process-exit-signal/languages/rust.md) | end of chapter | doc.rust-lang.org/std |
| Node.js | [languages/nodejs.md](./process-exit-signal/languages/nodejs.md) | end of chapter | nodejs.org/api |
| OCaml | [languages/ocaml.md](./process-exit-signal/languages/ocaml.md) | end of chapter | ocaml.org API manual |
