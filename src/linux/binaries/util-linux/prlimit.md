# prlimit — get and set per-process resource limits

## Overview

`prlimit` reads and changes the kernel's per-process resource limits (rlimits): open-file counts, CPU time, process counts, stack and core sizes, and friends. It is a command-line wrapper over the `prlimit64(2)` syscall and does two jobs: query (`prlimit --nofile --pid 1234`) and modify (`prlimit --nofile=65535 --pid 1234`), plus a launcher mode that starts a command under new limits. It ships in the `util-linux` package at `/usr/bin/prlimit`.

You reach for it when the classic levers do not apply: `ulimit` is a shell builtin that only affects children of that shell, PAM `limits.conf` only applies at login, and systemd `Limit*=` only at unit start — but a long-running daemon was already started, and it just hit *too many open files*. `prlimit` is the only standard tool that fixes limits on a live PID. It is often confused with `ulimit` (shell builtin, same kernel data), `getrlimit`/`setrlimit` (the POSIX interfaces it wraps), and cgroup limits (per-process kernel accounting vs per-process *resource ceilings* — orthogonal mechanisms).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/prlimit |
| First appeared | util-linux 2.21 era (2012), on top of kernel 2.6.36 `prlimit64` |
| Standards | `getrlimit`/`setrlimit` are POSIX; `prlimit(2)` is Linux-specific |

## Synopsis

```
prlimit [options] [--resource[=limits]] [--pid <pid>]
prlimit [options] [--resource[=limits]] <command> [<arg>...]
```

Main one-line forms:

```
prlimit                          # all limits of the calling process
prlimit --nofile --pid 1234      # one limit of a live process
prlimit --nofile=8192:65535 --pid 1234   # set soft=8192, hard=65535
prlimit --nproc=256 -- make -j8  # launch a command under new limits
```

## How It Works

### The data model

Every process carries 16 rlimit slots, each a (soft, hard) pair. The kernel enforces the soft value; the hard value is the ceiling a non-root process can raise soft to. `RLIM_INFINITY` (printed as `unlimited`) means no cap.

```
$ prlimit | head -12
RESOURCE   DESCRIPTION                        SOFT      HARD UNITS
AS         address space limit           unlimited unlimited bytes
CORE       max core file size                    0 unlimited bytes
CPU        CPU time                      unlimited unlimited seconds
FSIZE      max file size                 unlimited unlimited bytes
LOCKS      max number of file locks held unlimited unlimited locks
MEMLOCK    max locked-in-memory address space 65536    65536 bytes
NOFILE     max number of open files           1024   100000 files
NPROC      max number of processes          100000   100000 processes
...
```

### Reading and writing

Without `--pid`, the tool acts on itself (useful as the launcher). With `--pid`, it uses `prlimit64(2)`, which — unlike `setrlimit` — can target *another* process, subject to permissions: you may modify your own limits, and root (or `CAP_SYS_RESOURCE` in the target's user namespace) may modify anyone's hard limits upward.

The value grammar per resource is `soft:hard`, with shortcuts that are worth memorizing:

```
--nofile=8192          BOTH soft and hard become 8192   (verified locally)
--nofile=8192:65535    soft 8192, hard 65535
--nofile=8192:         soft 8192, hard unchanged
--nofile=:65535        hard 65535, soft unchanged
--nofile=unlimited     RLIM_INFINITY
```

The bare `=N` form setting *both* values is the top operational surprise — done by a non-root user it permanently lowers the hard ceiling for that process and all descendants, because a non-privileged hard-limit decrease is irreversible.

### Inheritance and the other limit systems

Limits are inherited across `fork`/`exec`, so the process tree carries them: login session (PAM `limits.conf`) → shell (`ulimit` reads/sets the same slots) → daemons. systemd units set them with `LimitNOFILE=` etc. before exec; `prlimit` closes the loop by adjusting a process that is already running. Container runtimes set per-container rlimits at exec; cgroups then bound aggregate usage — a process can be within its rlimits and still be OOM-killed by its cgroup, and vice versa.

### The syscall, precisely

`prlimit64(pid, resource, new_limit, old_limit)` is one call that reads and/or writes: pass NULL for the side you do not want. The kernel's permission check: you may always modify yourself; you may modify another process when your real/effective/saved-set UID matches the target's, or when you hold `CAP_SYS_RESOURCE` in the user namespace owning the target — which is why "root on the host" does not automatically mean "can raise limits inside a userns container". The in-kernel slot is `struct rlimit64 { __u64 rlim_cur; __u64 rlim_max; }` per resource; `prlimit(1)` is a thin CLI over it.

Enforcement points differ per resource, which is the practical part of the design: `open()` fails with `EMFILE` beyond NOFILE; `fork()` fails with `EAGAIN` beyond NPROC; writes past FSIZE raise `SIGXFSZ` and fail with `EFBIG`; CPU overshoot raises `SIGXCPU` at soft and `SIGKILL` at hard. Knowing which syscall returns which errno turns "app misbehaving" into "limit hit" in one log line.

### The read-only mirror: /proc/<pid>/limits

`cat /proc/<pid>/limits` renders the same 16 slots — it is how monitoring collects limits without syscalls and how you cross-check what prlimit reports. There is no procfs *write* path; changes go through `prlimit64(2)` only, so scripts that try to echo into procfs fail by design.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p`, `--pid <pid>` | Target an existing process instead of launching one |
| `--nofile[=v]` | Open file descriptors (the classic *too many open files* knob) |
| `--nproc[=v]` | Processes for this real UID (see gotcha: per-uid, not per-process) |
| `--cpu[=v]` | CPU seconds; soft exceeded → `SIGXCPU`, hard → `SIGKILL` |
| `--fsize[=v]` | Max file size one process may create/extend (`SIGXFSZ` beyond) |
| `--core[=v]` | Core dump size cap (0 disables cores; `unlimited` enables) |
| `--stack[=v]` | Stack size (default 8 MiB; raise for deep recursion) |
| `--as[=v]` | Address-space cap (mostly useless under overcommit; see gotchas) |
| `--memlock[=v]` | Non-pageable RAM (DPDK, realtime, mlock users) |
| `--msgqueue[=v]` | POSIX message queue bytes |
| `--nice[=v]` | Nice ceiling a process may raise *to* |
| `--rtprio[=v]` | Realtime priority ceiling (`SCHED_RR`/`SCHED_FIFO`) |
| `--sigpending[=v]` | Queued signals cap |
| `--locks[=v]` | File-lock count |
| `--rttime[=v]` | Max realtime CPU without blocking (RT throttling companion) |
| `--rss[=v]` | Historic no-op since Linux 2.4.30 — accepted but ignored |

## Usage Patterns

```bash
# Check what the shell inherited
prlimit --nofile --nproc
```

```bash
# Fix a running nginx that is out of file descriptors (then reload config gracefully)
prlimit --nofile=16384:16384 --pid "$(pidof nginx | cut -d' ' -f1)"
```

```bash
# Launch a build with a process cap so a runaway -j cannot fork-bomb
prlimit --nproc=512 -- make -j32
```

```bash
# Enable core dumps for one debugging run only
prlimit --core=unlimited -- ./crasher
```

```bash
# Deep-recursion program needs more stack
prlimit --stack=64M -- ./interpreter
```

```bash
# Cap CPU: SIGXCPU at 300s, SIGKILL at 360s
prlimit --cpu=300:360 -- ./train_model
```

```bash
# Compare a daemon's live limits against systemd's LimitNOFILE=
prlimit --nofile --pid "$(systemctl show -p MainPID --value nginx)"
```

```bash
# DPDK / realtime prep: lock memory, allow RT priority
sudo prlimit --memlock=unlimited --rtprio=80 --pid "$DPDK_PID"
```

```bash
# See the numeric view your monitoring should alert on
prlimit --noheadings --pid 1 2>/dev/null | grep NOFILE || prlimit --nofile --pid 1
```

```bash
# Safe soft-only raise: hard ceiling untouched
prlimit --nofile=4096: --pid "$$"
```

```bash
# The two views of the same kernel data: procfs vs prlimit
grep -E 'open files|processes' /proc/$$/limits
prlimit --nofile --nproc

# The safe live fix for a service: soft-only, hard ceiling preserved
sudo prlimit --nofile=8192: --pid "$(pgrep -x mysqld | head -1)"

# One-off memory leash for an untrusted repro (with the AS caveat in mind)
prlimit --as=8G -- ./repro

# Fork-bomb containment drill in a throwaway shell
prlimit --nproc=64 --cpu=60 -- bash --noprofile --norc

# Audit a whole service tree's live ceilings (post-incident sweep)
for p in $(pgrep -f nginx); do echo "pid $p: $(prlimit --nofile --noheadings -p $p)"; done
```

```bash
# Transient systemd run with explicit limits, then verify what landed
systemd-run --scope -p LimitNOFILE=16384 redis-server
prlimit --nofile --pid "$(pgrep -x redis-server | head -1)"
```

## Nuances and Gotchas

- **`--nofile=N` sets hard too.** If you only meant to raise the soft limit, use the `soft:` form. Non-root hard-limit *decreases are permanent* — a mis-typed prlimit can lock a daemon out of its previous ceiling forever (until restart).
- **`RLIMIT_NPROC` is per real UID, not per process.** A process at `nproc=100` can still be unable to fork because *other* processes of the same user used the budget — and root's service accounts share the surprise. (Kernel ≥ 4.x honors it per-uid unless `RLIMIT_NPROC` semantics were patched in containers.)
- **`RLIMIT_AS` is a trap under overcommit.** Modern malloc reserves address space it never touches; a 48-bit VA space plus overcommit makes `AS` fire spuriously (golang, JVM, asan). Cap memory with cgroups, not `AS`.
- **`RLIMIT_RSS` is dead.** Accepted for compatibility, ignored by the kernel — knowing this is a standing interview gotcha.
- **`NOFILE` has system-level neighbors.** The per-process hard ceiling is bounded by `/proc/sys/fs/nr_open`, and the system total by `fs.file-max`. Raising `NOFILE` past `nr_open` fails with EINVAL; raising it only in one process does not relieve the system-wide cap.
- **Core dumps need more than `--core`.** `kernel.core_pattern`, `/proc/sys/fs/suid_dumpable`, and the crashing process's rlimit must all agree; `core=unlimited` on one process is necessary but not sufficient.
- **`CPU` fires signals, not a scheduler cap.** Soft `CPU` sends `SIGXCPU` (catchable — databases use it for graceful abort), hard sends `SIGKILL`. Wall-clock limits are `timeout`/systemd `RuntimeMaxSec`, not rlimits.
- **systemd defaults are huge.** Modern `LimitNOFILE=` defaults are 1024 soft / 524288 hard (journald-era change); legacy advice of "1024 everywhere" misreads contemporary systems — check with `prlimit` instead of assuming.
- **Permissions model.** Unprivileged: lower both, raise soft up to hard, never raise hard. Root/CAP_SYS_RESOURCE: anything. Failing modifications exit non-zero with the errno mapped to a message (EPERM, EINVAL).
- **setrlimit(2) cannot target other processes; prlimit64(2) can.** That PID argument (kernel 2.6.36) is the whole reason the CLI exists — older paths (and Python's `resource` module, which wraps setrlimit) are strictly self-targeted.
- **Children never see changes made after their fork.** `prlimit` against PID 1 fixes nothing already running; each long-lived process needs its own adjustment (loop with `pgrep`), and the unit file/PAM config must change for permanence.
- **Stack rlimit and ARG_MAX are coupled.** Since Linux 2.6.23 the execve argument-space limit is a quarter of RLIMIT_STACK — aggressively *lowering* stack shrinks usable argv+envp and breaks commands with huge argument lists.
- **ENFILE is not EMFILE.** A process under its NOFILE can still fail `open()` with ENFILE when the system-wide table (`fs.file-max`) is exhausted — a per-process raise cannot fix a system-wide ceiling, and triage must check both.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Query printed or limits applied successfully |
| 1 | Failure: bad resource/value, EPERM (not allowed to change that), EINVAL (value out of range), target PID missing |

## Related Commands

- [`ulimit`](https://manpages.debian.org/bookworm/bash/builtin.en.html) — shell builtin over the same data (affects children only).
- [`systemd`](../../admin/systemd.md) — `Limit*=` directives are the declarative form for services.
- [`process-management`](../../admin/process-management.md) — PIDs, credentials, and who may touch whom.
- [`nice`](./ionice.md) — sibling launchers (`nice`, `ionice`, `chrt`) that shape scheduling rather than limits.
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: A daemon is running and hit "too many open files". Walk through fixing it without restarting.

Confirm with `prlimit --nofile --pid <pid>` (or `/proc/<pid>/limits`), then raise it live: `prlimit --nofile=16384:16384 --pid <pid>` as root. The change is immediate — the process's kernel slot is updated — but the *application* may also cap itself internally (nginx `worker_rlimit_nofile`, Java `ulimit` checks), so a graceful reload is often needed after. Then make it permanent (systemd `LimitNOFILE=`, `limits.conf`, or container runtime config) and verify `fs.nr_open`/`fs.file-max` are not the real ceiling. Interviewers look for the rlimit-vs-app-config-vs-sysctl distinction.

### Q: What is the difference between soft and hard limits, and who can change which?

The soft limit is what the kernel enforces; the hard limit bounds soft-limit changes. Unprivileged processes may lower either and raise soft up to hard, but can never raise hard — and a lowered hard limit is unrecoverable without root. Root (or `CAP_SYS_RESOURCE` in the owning user namespace) can set anything, including raising hard. Design intent: hard limits are an administratively set safety ceiling; soft is the working value the process may adjust itself (e.g., a daemon raising NOFILE at startup).

### Q: Why can RLIMIT_NPROC mislead you when debugging fork failures?

It is enforced per real UID: the kernel counts all processes of that uid against the limit, not the process tree's. A service account running several daemons hits the ceiling collectively; the failing process may itself be tiny. Also, on many systems root is exempt, which hides the issue in tests. Debug with per-uid process counts (`ps -o uid= | sort | uniq -c`) rather than assuming the limit applies per-process.

### Q: When would you use prlimit instead of systemd Limit*= or limits.conf?

When the process already exists. PAM limits and systemd directives only take effect at session/unit start; prlimit adjusts a live PID via `prlimit64`. Typical split: `LimitNOFILE=`/`limits.conf` for persistence, `ulimit` in wrappers for child processes, `prlimit` for incident response and for launching one-off commands under different limits (`prlimit --core=unlimited -- ./repro`). Also `prlimit` is the *verification* tool for all of the above since it reads the kernel's live values.

### Q: Explain why RLIMIT_AS is usually the wrong way to limit memory on modern Linux.

Address-space reservations are not resident memory: malloc/overcommit, huge thread stacks, and reserved mappings (JVM, Go runtime, ASan) reserve VA far beyond RSS. Under overcommit, `AS` trips on reservations, not usage, producing mysterious allocation failures with plenty of free RAM. The correct tools are cgroup memory limits (what containers use), `RLIMIT_DATA` for the heap on modern kernels, or `RSS`-aware OOM handling — `AS` remains useful only for tightly controlled native workloads.

### Q: What changed at kernel 2.6.36 that made prlimit possible, and what can it do that setrlimit cannot?

prlimit64(2) added a PID argument to the rlimit interface: read *and* write another process's limits in one call, with proper credential checks. setrlimit/getrlimit are strictly self-targeted — and the 64 suffix exists because the 32-bit getrlimit's rlim_t could not represent large values. Before 2.6.36 the only ways to touch a running process's limits were ptrace tricks or gdb; prlimit(1) is the supported CLI over the syscall.

### Q: Design the limit stack for a multi-tenant host: where do limits.conf, systemd, ulimit, and prlimit each belong?

PAM limits.conf sets interactive-session baselines; systemd `Limit*=` is the declarative equivalent for services; `ulimit` in wrapper scripts adjusts children ad hoc; prlimit is for live incident response and for *verifying* what actually landed. Enforce hard ceilings at the outermost layer, leave soft limits for processes to self-tune, and audit live state with prlimit — the config file everyone reads is not the state the kernel enforces.

### Q: Why do "too many open files" incidents recur in Java and Node stacks specifically?

Both runtimes size internal thread/selector pools from the *soft* NOFILE at startup, so a live prlimit raise is not fully honored without a restart; and their per-connection fd accounting (thread per connection, mmap'ed jars, event-loop descriptors) multiplies usage. The durable fix sets the limit before exec — systemd `LimitNOFILE=` or container runtime ulimits — plus app-level awareness (nginx `worker_rlimit_nofile`, Netty fd accounting). prlimit's role is triage and proof: show live soft/hard against the incident, then fix the launch configuration.

### Q: What does the `soft:hard` grammar's bare `=N` shortcut really do, and why is it the top footgun?

`--nofile=8192` sets *both* soft and hard to 8192 — one keystroke away from permanently dropping the hard ceiling, since unprivileged hard-limit decreases can never be undone. The safe forms are explicit: `soft:` raises soft only, `:hard` raises hard only. The mental model to answer with: hard limits are administrative ceilings meant to move rarely and only downward-by-design for unprivileged callers; the bare form treats them as the working value, which they are not.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/prlimit.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
