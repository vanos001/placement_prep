# renice — alter the scheduling priority of running processes

## Overview

`renice` changes the nice value of processes that are already running — the live counterpart to coreutils `nice(1)`, which sets the value at launch. Nice values span −20 (most favorable to the CPU scheduler) to 19 (most polite); higher means "runs only when nothing else wants the CPU". `renice` ships in the `bsdutils` package at `/usr/bin/renice` (upstream util-linux; it first appeared in 4.0BSD and is standardized by POSIX — with a twist, see the absolute-vs-delta trap below).

You reach for `renice` to demote a runaway compile without killing it, or to promote a latency-sensitive process on a busy box. It is often confused with `nice` (launch-time only — a running process can't `nice` itself down without privilege), with procps `snice` (the skill-family variant with its own syntax), and with `ionice`/`chrt` — which adjust I/O priority and real-time scheduling, orthogonal axes that nice does not touch.

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/renice |
| First appeared | 4.0BSD |
| Standards | POSIX.1-2018 (`renice`), with a documented local deviation on `-n` |

## Synopsis

```
renice [-n|--priority|--relative] priority [-g|--pgrp] pgid...
renice [-n|--priority|--relative] priority [-p|--pid]  pid...
renice [-n|--priority|--relative] priority [-u|--user] user...
```

Common one-line forms:

```
renice 19 -p 4242              # set PID 4242 to nice 19 (absolute — see below!)
renice --relative +5 -p 4242   # unambiguously add 5 to the current nice value
renice 10 -u buildbot          # every process owned by buildbot
sudo renice --priority -5 -p 4242   # lower nice value (needs privilege)
```

## How It Works

### The scheduling knob

On Linux, nice values live in [−20, 19] and bias the CFS scheduler's weighting of a task: 0 is the default, 19 runs only when nothing else contends, negative values demand the CPU. `renice` calls `setpriority(2)` per target and reports each transition; the output shape is part of the tool's contract and worth knowing verbatim (verified):

```
$ renice 10 -p 13795
13795 (process ID) old priority 0, new priority 10
$ renice 10 -g 13718
13718 (process group ID) old priority 0, new priority 10
```

Selection granularity is threefold: `-p` (default) targets PIDs; `-g` targets a process group and re-nices every member; `-u` targets a user and re-nices every process they own. The selectors are switches, not one-shot flags — later operands belong to the most recent switch, which is how the man page's classic example reads:

```
renice +1 987 -u daemon root -p 32
#  ↑ 987 is a PID (default), then every process of daemon and root,
#    then PID 32 again — one invocation, three target classes
```

### THE gotcha: `-n` is absolute here, relative under POSIXLY_CORRECT

POSIX says `renice -n increment` adjusts *relative* to the current value. util-linux `renice` deviates deliberately (documented in its NOTES): historically `-n` set an **absolute** priority, and that behavior is kept by default; setting `POSIXLY_CORRECT` in the environment restores POSIX relative semantics. The man page offers the unambiguous escapes `--priority` (absolute) and `--relative` (delta). Verified on this system — same PID, four calls:

```bash
$ renice -n 10 -p $PID            # -n, no POSIXLY_CORRECT → ABSOLUTE 10
13795 (process ID) old priority 0, new priority 10
$ renice --priority 5 -p $PID     # lowering 10 → 5 needs privilege
renice: failed to set priority for 13795 (process ID): Permission denied
$ renice --relative +5 -p $PID    # explicit delta: 10 + 5
13795 (process ID) old priority 10, new priority 15
$ renice -n 5 -p $PID             # absolute 5 again → denied
renice: failed to set priority for 13795 (process ID): Permission denied
```

And the POSIX flip, verified: `POSIXLY_CORRECT=1 renice -n 3 -p $PID` moved a nice-0 process to **3** (0+3 relative), not *to* 3. The portable, self-documenting habit: never write `-n N` in scripts; write `--priority` or `--relative` and mean it.

### Privilege rules

Two gates apply, enforced by the kernel's `setpriority(2)` checks:

1. **Ownership.** Unprivileged users may only alter processes they own. (Verified: `renice --priority 0 -p 1` → `failed to set priority for 1 (process ID): Operation not permitted`, exit 1.)
2. **Direction.** An unprivileged user may only *increase* the nice value (i.e., make the process *more* polite). Lowering nice — even back to where it was — requires privilege, and the increase is **irreversible** by the same user. Since Linux 2.6.12 the exception is a suitable `RLIMIT_NICE` resource limit (bash: `ulimit -e`); the default limit of 0 on stock systems means the rule is absolute in practice (verified: `ulimit -e` → 0).

The superuser may target any process and set any value in −20…19. Useful anchors from the man page: 19 (run only when idle), 0 (baseline), negative (go fast).

### Clamping

Out-of-range requests are clamped into [−20, 19] rather than rejected, and `renice` reports the clamped result (verified):

```
$ renice 100 -p 14484
14484 (process ID) old priority 0, new priority 19
$ ps -o pid,ni,comm -p 14484
  PID  NI COMMAND
14484  19 sleep
```

### Who may change what: the permission flow

Before touching a value, mentally run this check — it is exactly what the kernel does per target:

```
        renice <value> <target>
                 │
   ┌─────────────┴──────────────┐
   │ do you own the process?    │──no──► EPERM ("Operation not permitted")
   └─────────────┬──────────────┘
                 │ yes
   ┌─────────────┴──────────────┐
   │ is new nice ≥ current?     │──no──► EPERM (only root may lower nice;
   │ (or you are root / have    │        RLIMIT_NICE > 0 buys headroom)
   │  RLIMIT_NICE headroom)     │
   └─────────────┬──────────────┘
                 │ yes
                 ▼
      value clamped into [−20, 19], applied
```

### What the weight actually buys

Nice biases the CFS scheduler's time-share weighting. The effect is proportional and only visible under contention: on an idle 32-core box, a nice-19 process uses all the CPU it wants; once other runnable threads appear, its share shrinks toward a small fraction. This is why "I reniced it and nothing changed" almost always means "the box wasn't loaded" — validate under load, and treat nice as a relative politeness knob, never a capacity guarantee.

### User-granularity renice is an all-or-nothing kernel call

`renice` with `-u`/`-g` resolves to a single `setpriority(PRIO_USER/PRIO_PGRP, …)` call, and the kernel applies one value to *every* matching process. With a relative operand, the delta is derived from the current (most favorable) nice among the targets — so on an account whose processes have mixed nice values, some processes would end up *lowered*, the kernel refuses with EPERM, and the whole call fails (observed: `renice: failed to set priority for 1001 (user ID): Permission denied` on an account with processes at nice 0/3/15/19). Prefer per-PID renice, or run as root, when the target population is heterogeneous.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n NUM` | priority; **absolute by default**, relative if `POSIXLY_CORRECT` is set; must be the first argument when used |
| `--priority NUM` | unambiguous absolute set |
| `--relative NUM` | unambiguous delta (POSIX `-n` semantics) |
| `-p, --pid` | interpret following operands as PIDs (default) |
| `-g, --pgrp` | interpret following operands as process group IDs |
| `-u, --user` | interpret following operands as usernames or UIDs |
| `-h, -V` | help / version |

There are no output-format options; the `old priority X, new priority Y` lines are fixed.

## Usage Patterns

```bash
# Demote a runaway compile to run only when the box is idle
renice 19 -p $(pgrep -f 'make -j')
```

```bash
# Politely demote everything of a batch account
sudo renice 15 -u buildbot
```

```bash
# Give a latency-sensitive daemon a real boost (root required for negative)
sudo renice --priority -10 -p $(pidof mpd)
```

```bash
# The delta you almost always mean: +5 niceness, explicitly
renice --relative +5 -p 4242
```

```bash
# POSIX-compliant scripts that must behave the same everywhere
POSIXLY_CORRECT=1 renice -n 5 -p 4242     # relative +5
```

```bash
# An entire process group (e.g. a session you started under setsid)
renice 10 -g 31337
```

```bash
# Mixed targets in one call: PID, then two users, then another PID
sudo renice 5 987 -u daemon root -p 32
```

```bash
# Verify results the way the kernel sees them
ps -o pid,ni,pri,comm -p 4242
top -b -n1 | head -15           # NI column; PRI is a different scale
```

```bash
# Undo your own demotion after promoting yourself with sudo once
sudo renice --priority 0 -p 4242
```

```bash
# Check your room to maneuver before relying on RLIMIT_NICE
ulimit -e        # 0 on default Linux: no lowering without root
```

```bash
# Find the process group of a background job, then demote the whole group
PG=$(ps -o pgid= -p $PID | tr -d ' ')
renice 10 -g $PG
```

```bash
# Demote by command line when the PID changes between runs
for p in $(pgrep -f 'ffmpeg'); do renice 19 -p "$p"; done
```

```bash
# Script defensively: report which targets failed instead of guessing
renice --relative +5 -p $P1 $P2 $P3 || echo "one or more renice calls failed" >&2
```

```bash
# Launch-time vs run-time: nice sets it once, renice adjusts later
nice -n 19 ./nightly-index.sh &     # start polite
# ... later, when the batch window opens:
renice --priority 5 -p $!           # (root: lowering is privileged)
```

## Nuances and Gotchas

- **`-n` is absolute in util-linux renice.** This contradicts POSIX and muscle memory from `nice -n` (which is also absolute, to be fair) *and* from tools where `-n` means delta. Scripts that "add 5" with `renice -n 5` actually *set* nice 5. Use `--relative`/`--priority`, or export `POSIXLY_CORRECT` deliberately.
- **Increases are one-way for mortals.** Once you renice a process up, you cannot bring it back down without privilege — a regular trap when someone "tests" `renice 19` on their own editor. Since Linux 2.6.12 `RLIMIT_NICE` can relax this, but the stock limit is 0.
- **`renice +5` and `renice 5` are the same thing here.** The sign does not make the value a delta; both are absolute sets. Only `--relative +5` is a delta.
- **`-n` must be the first argument.** When used, `-n` and its value come before any selector; `renice -p 42 -n 5` is a usage error.
- **`-u`/`-g` are blast radii.** `renice 19 -u alice` re-nices every process alice owns — including her interactive shell. On accounts with mixed nice values the unprivileged user-granularity call can fail outright with EPERM (see How It Works). Scope narrowly with `-p` whenever possible.
- **nice is a per-thread attribute on Linux.** `renice -p PID` on a multithreaded process targets the thread-group leader; worker threads can retain the old value. Inspect with `ps -L -o pid,tid,ni,comm -p PID` and renice the specific TIDs (or the process early in its life) if uniformity matters.
- **nice ≠ priority you see in top.** The `PRI` column is the kernel's dynamic priority derived from nice plus scheduling class; comparing PRI numbers across classes misleads. Reason in NI, verify effects under load, not on an idle box.
- **vs procps `snice`:** same knob, different grammar. `snice` takes the priority as a positional operand, defaults to `+4`, spans `+20…-20`, and restricts negative values to administrative users — there is no `-n`, so the absolute-vs-delta ambiguity of `renice -n` doesn't transfer. Cross-tool muscle memory is the trap; read the tool's man page each time.
- **Only helps CPU contention.** A nicely-niced process still hammers disk (that's `ionice`), can starve memory, and is a different world from real-time scheduling (`chrt`). Nice influences scheduling weight, not access to resources.
- **`-n` placement is rigid.** `renice -p 42 -n 5` errors out — when used, `-n <value>` must lead the command line. The long options `--priority`/`--relative` are more forgiving, one more reason to prefer them.
- **Partial failure still exits nonzero, but earlier successes stand.** `renice 5 -p $A $B` where only `$B` is foreign leaves `$A` re-niced and exits 1; there is no rollback. Check the per-target report lines, not just `$?`.
- **Clamping, not rejecting.** `renice 100` silently means 19, and the report shows 19 — scripts checking the echo may not notice the clamp happened.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Every requested change succeeded |
| >0 | At least one change failed (verified: `failed to set priority … Permission denied` → 1) |

POSIX specifies 0 when all targets are altered and >0 otherwise; util-linux reports the first failure per target line and exits 1.

## Related Commands

- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.
- [`../util-linux/ionice.md`](../util-linux/ionice.md) — the I/O-scheduling sibling: same politeness idea, different resource.
- [`../util-linux/chrt.md`](../util-linux/chrt.md) — real-time scheduling policies; the step beyond nice that needs privilege.
- [`../../admin/process-management.md`](../../admin/process-management.md) — where renice fits in the process-lifecycle toolbox (signals, priorities, limits).
- [`../../reference/commands.md`](../../reference/commands.md) — quick reference including the nice/renice one-liners.

## Interview Questions

### Q: What can an unprivileged user do with renice, exactly?

Change only processes they own, and only in the "more polite" direction — raise the nice value. The change is irreversible without privilege because lowering nice (raising priority) is a privileged `setpriority` operation; since Linux 2.6.12 a nonzero `RLIMIT_NICE` can grant headroom, but the stock limit of 0 means none. The superuser can retarget anything within −20…19. This asymmetry is intentional: users can give up CPU, not take it.

### Q: Explain the `-n` trap in util-linux renice.

POSIX defines `renice -n increment` as a relative adjustment, but util-linux `renice` treats `-n` as an *absolute* set by default for historical reasons, and only honors relative semantics when `POSIXLY_CORRECT` is exported. The unambiguous options are `--priority` (absolute) and `--relative` (delta). Verified on a live system: `renice -n 10` on a nice-0 process yields nice 10, and `POSIXLY_CORRECT=1 renice -n 3` yields 3 added. In scripts, spell out `--priority`/`--relative` and never rely on the environment.

### Q: You renice an entire user account and get EPERM even though you're only making things politer. Why?

`-u`/`-g` become a single kernel-level `setpriority` call that applies one value to every matching process. A relative operand is computed against the current nice of the target population; if the account's processes have heterogeneous nice values, applying one new value necessarily *lowers* some of them — and lowering is a privileged operation, so the kernel rejects the whole call. Fix by renicing PIDs individually, or by running as root.

### Q: How do renice, ionice, and chrt differ in what they control?

They tune three different scheduler axes. `renice` biases CPU time-share within the normal (CFS) class — a weight, not a guarantee. `ionice` sets I/O scheduling class and priority for block-I/O contention. `chrt` moves a process into real-time policies (FIFO/RR/deadline) with explicit priorities, which preempts all normal-class work and requires privilege or proper rlimits. A "slow but important" process may need all three addressed; nice alone only fixes CPU starvation.

### Q: After `renice 19 -p X`, top shows X's PRI unchanged at first. Is renice broken?

No — top's `PRI` is the kernel's dynamic priority, recomputed under contention, while `NI` shows the nice value you set. On an idle machine a nice-19 process may still run immediately because nothing contends. Verify the knob (`ps -o ni`) and the effect under load. Also remember nice is per-thread on Linux: multithreaded programs can mix old and new values across threads until each thread is reniced.

### Q: Compare `renice -n 5 -p PID` with procps `snice 5 PID`.

Both end at nice 5 on a default system, but the semantics of the *notation* differ. util-linux `renice -n 5` is an absolute set (and would be a +5 delta under `POSIXLY_CORRECT`); procps `snice` has no `-n` — the priority is positional, defaults to `+4`, and its signed `+20…-20` range notation reserves negative values for administrators. The transferable lesson is that "renice-like" tools disagree about whether a bare number means "set to" or "add" — always check, and prefer tools' explicit long options when scripting.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/renice.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
