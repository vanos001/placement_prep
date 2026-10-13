# procps — Collection Overview

procps is the /proc reader's toolkit: `ps`, `top`, `free`, `vmstat`,
`sysctl` and friends all render kernel state into human form. Every
production incident review starts with one of these binaries, and
interviews use them as a proxy for "have you actually debugged a live
system." This collection covers all 17 binaries one page each; the hub
carries the /proc mapping ideas they share.

## The /proc Contract

Everything procps shows comes from `/proc` — but from different files
with different semantics:

| Binary | Primary sources |
|---|---|
| [ps](./ps.md), [pgrep](./pgrep.md), [pkill](./pkill.md) | `/proc/<pid>/stat`, `status`, `cmdline` |
| [top](./top.md) | the above plus `/proc/stat`, `/proc/meminfo`, delta sampling |
| [free](./free.md) | `/proc/meminfo` |
| [vmstat](./vmstat.md) | `/proc/stat`, `/proc/meminfo`, `/proc/vmstat` |
| [uptime](./uptime.md), [w](./w.md) | `/proc/loadavg`, `/proc/uptime`, utmp |
| [sysctl](./sysctl.md) | `/proc/sys/**` (the tunables tree itself) |
| [pmap](./pmap.md) | `/proc/<pid>/maps`, `smaps` |
| [slabtop](./slabtop.md) | `/proc/slabinfo` |
| [pwdx](./pwdx.md) | `/proc/<pid>/cwd` readlink |

Two habits transfer everywhere: values like %CPU are **deltas between
samples**, not absolutes (why `top`'s first %CPU reading is odd), and
field meanings shift across kernel versions, so tools label rather than
assume. The free-vs-available story — "available" estimates reclaimable
cache, "free" is truly idle — is the single most-asked interview question
in this collection and lives on the [free](./free.md) page.

## Inventory

### Observe processes (6)

| Binary | One-liner | Page |
|---|---|---|
| `ps` | Snapshot process list (flagship) | [ps](./ps.md) |
| [top](./top.md) | Live process view (flagship) | [top](./top.md) |
| `pgrep` | Find PIDs by criteria (flagship) | [pgrep](./pgrep.md) |
| `pkill` | Signal PIDs by criteria | [pkill](./pkill.md) |
| `pidof` | PIDs by exact program name | [pidof](./pidof.md) |
| `pidwait` | Wait for matching processes | [pidwait](./pidwait.md) |

### Observe memory and kernel (5)

| Binary | One-liner | Page |
|---|---|---|
| `free` | Memory summary | [free](./free.md) |
| `pmap` | Per-process memory map | [pmap](./pmap.md) |
| `slabtop` | Kernel slab usage live | [slabtop](./slabtop.md) |
| `vmstat` | Virtual memory statistics | [vmstat](./vmstat.md) |
| `pwdx` | Working directory of PIDs | [pwdx](./pwdx.md) |

### Session, load, and control (6)

| Binary | One-liner | Page |
|---|---|---|
| `uptime` | Load triple + uptime | [uptime](./uptime.md) |
| `w` | Who is on and doing what | [w](./w.md) |
| `watch` | Repeat a command, diff output | [watch](./watch.md) |
| `sysctl` | Read/write kernel tunables | [sysctl](./sysctl.md) |
| `snice` | Renice by criteria | [snice](./snice.md) |
| `tload` | ASCII load graph | [tload](./tload.md) |

## Shared Concepts

- **POSIX vs BSD syntax duality** — `ps -ef` vs `ps aux` is one interface
  choice with deep history; [ps](./ps.md) is the canonical explanation
  and every other tool picks a side.
- **Selection grammar reuse** — `pgrep`/`pkill`/`pidwait`/`snice` share
  one matching engine (name vs `-f` full cmdline, `-u` user, `-P`
  parent, `-x` exact); learn it once, and know that `-x` still means
  "match the pattern exactly", not "literal string".
- **Signals as control** — `pkill` defaults to SIGTERM for a reason
  (graceful shutdown contract); the escalation ladder TERM → KILL and
  the exit-code contract are on [pkill](./pkill.md).
- **Sampling honesty** — `top -bn1` %CPU is since-boot-ish, first
  `vmstat` line is since-boot by design; batch mode for scripts needs
  warm-up iterations. The [top](./top.md) and [vmstat](./vmstat.md)
  pages quantify this.
- **Tunables are files** — `sysctl -w vm.swappiness=10` is a write to
  `/proc/sys/vm/swappiness`; persistence lives in `/etc/sysctl.d/`.
  The name→path mapping rule is on [sysctl](./sysctl.md).

## Reading Order For Interview Prep

1. [ps](./ps.md) and [top](./top.md) — the flagship pair.
2. [free](./free.md) + [vmstat](./vmstat.md) — memory truth-telling.
3. [pgrep](./pgrep.md)/[pkill](./pkill.md) — safe process targeting.
4. [sysctl](./sysctl.md) — tuning and persistence.
5. The rest for breadth: [pmap](./pmap.md), [slabtop](./slabtop.md),
   [watch](./watch.md), [w](./w.md), [uptime](./uptime.md).

Related: [Process Management](../../admin/process-management.md) (admin
track) covers cgroups/systemd context; [kill](../util-linux/kill.md) in
the util-linux collection covers the signal sender itself; load-average
semantics appear on both [uptime](./uptime.md) and
[top](./top.md).

## Interview Questions

### Q: free shows 200 MB free but 30 GB available. Is the box out of memory?

No — the opposite. "free" is memory the kernel had nothing to put in;
"available" estimates what can be reclaimed from page cache and other
reclaimable structures without hurting performance. Linux treats unused
RAM as wasted RAM, so healthy boxes have small free and large available.
The [free](./free.md) page maps every field to `/proc/meminfo`.

### Q: A process sits in D state and load average climbs. What does it mean and why does kill -9 not work?

D is uninterruptible sleep — the task is blocked in a syscall the kernel
cannot safely abort, classically NFS or other storage I/O. Signals are
delivered only when the task returns to user mode, so even SIGKILL
waits. Load average includes D-state tasks on Linux, which is why the
load climbs without CPU usage — the [uptime](./uptime.md) and
[ps](./ps.md) pages decode both halves.

### Q: Why do people say "never pkill -9 by name"?

Two reasons stack: broad name patterns match more than you think
(unanchored `-f` matches command lines, including your own monitoring
wrapper), and SIGKILL skips the process's cleanup contract — sockets
without FIN waits, lock files, data not fsynced. The professional
pattern: `pgrep` first to see targets, SIGTERM, wait, then escalate.
[pkill](./pkill.md) has the full ladder and the `-c`/`-e` guardrails.

### Q: What is steal time and where do you see it?

`st` in `top`'s %Cpu(s) line and `vmstat`'s `st` column: the fraction of
time the hypervisor ran other tenants while this vCPU wanted to run.
Sustained steal on a cloud VM means noisy-neighbor or undersizing —
a conversation about capacity, not the kernel. Both the
[top](./top.md) and [vmstat](./vmstat.md) pages decode their full
column sets.

## References

- [Source — Debian sources](https://sources.debian.org/src/procps/)
- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/procps/)
- [man7.org — Linux man-pages](https://man7.org/linux/man-pages/)
