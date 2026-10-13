# nproc — print the number of processing units available

## Overview

`nproc` prints how many CPUs the *current process* may actually use — not
how many the machine has. It calls `sched_getaffinity(2)` and counts the
bits in the affinity mask, so the answer automatically respects CPU
pinning (`taskset`), container configurations, and similar restrictions.
It is the canonical tool for sizing parallelism in build systems and
scripts: `make -j"$(nproc)"`, `xargs -P "$(nproc)"`, `pigz -p "$(nproc)"`.

Two twists make it more than `grep -c processor /proc/cpuinfo`: the
`OMP_NUM_THREADS` environment variable is honored (an OpenMP
compatibility carve-out that lets users override the answer), and the
`--all`/`--ignore=` flags let you deliberate between "what may I use" and
"what is installed". It ships in the Debian `coreutils` package at
`/usr/bin/nproc`. It is a pure GNU extension — no POSIX spec, no classic
Unix lineage — first added to coreutils in the 8.x era (late 2000s).

It is often confused with `lscpu` (detailed CPU inventory), `taskset`
(get/set affinity), and the raw `/proc/cpuinfo` count, which ignores
affinity entirely.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/nproc` |
| First appeared | GNU coreutils 8.x era (2009) |
| Standards | GNU extension — not POSIX |

## Synopsis

```
nproc [OPTION]...
```

Main forms:

```
nproc                     # usable CPUs for this process (affinity-aware)
nproc --all               # installed CPUs, ignore affinity
nproc --ignore=2          # usable CPUs minus 2
```

## How It Works

The kernel gives every task an affinity mask — the set of CPUs it is
allowed to be scheduled on. `nproc` asks for its own mask with
`sched_getaffinity(0, ...)` and prints the popcount. Anything that narrowed
the mask — `taskset -c 0,1`, a container runtime, `systemd` `CPUAffinity`,
`isolcpus` boot parameters — is already reflected in the answer.

```bash
# This container: affinity-limited to 2 CPUs
$ nproc
2

# Pin to one CPU: nproc follows
$ taskset -c 0 nproc
1

# But --all reports the hardware regardless
$ taskset -c 0 nproc --all
2
```

The environment override comes first, though: if `OMP_NUM_THREADS` is set
to a positive value, `nproc` prints that instead of asking the kernel.
This exists so OpenMP programs and build scripts agree on one pool size.

```bash
$ OMP_NUM_THREADS=1 nproc
1
```

Decision order, in effect:

```
  OMP_NUM_THREADS set and > 0 ?  ──yes──►  print it
        │no
        ▼
  sched_getaffinity() popcount   ──►  usable CPUs
        │
        ▼ (with --all)  installed CPU count instead
        │
        ▼ (--ignore=N)  subtract N, floor at 1
```

On cgroup-limited containers, note the boundary of what nproc can see:
CPU affinity is respected, but a `cpu.max` quota (say, 2.5 CPUs of
throttle without pinning) is *not* — affinity is a scheduling set, quota
is a rate limit. Scripts that must honor quotas need to read cgroup files
themselves or use taskset-pinned containers.

## Options That Matter

| Option | Effect |
|---|---|
| `--all` | Print the number of *installed* processors, ignoring affinity restrictions |
| `--ignore=N` | If possible, exclude N processing units from the count (never goes below 1) |
| `--help` / `--version` | Informational |

`--ignore` exists for reserving headroom: leave one core for I/O or the
interactive session while workers use `nproc --ignore=1`.

## Usage Patterns

```bash
# Canonical build parallelism
make -j"$(nproc)"
```

```bash
# Parallel compression with all usable cores
tar cf - dir | pigz -p "$(nproc)" > dir.tgz
```

```bash
# Cap xargs worker pool by CPU count
find . -name '*.png' | xargs -P "$(nproc)" -n1 optipng
```

```bash
# Leave headroom: N-1 workers, one core for the rest of the box
make -j"$(nproc --ignore=1)"
```

```bash
# Log hardware context in CI for reproducing benchmark numbers
echo "runner cpus: $(nproc) (installed: $(nproc --all))"
```

```bash
# Respect an operator's explicit override, else detect
JOBS=${JOBS:-$(nproc)}
make -j"$JOBS"
```

```bash
# Sanity-check container CPU limits after taskset/pinning
taskset -pc $$ && nproc
```

```bash
# Split a workload across two affinity-limited workers evenly
half=$(( $(nproc) / 2 )); taskset -c 0-$((half-1)) worker-a & taskset -c "$half"- worker-b &
```

## Nuances and Gotchas

- **`OMP_NUM_THREADS` hijacks the output.** Any environment where an
  OpenMP application set it will change `nproc`'s answer for *everything*
  in that environment — including your `make -j`. If a build suddenly
  runs single-threaded, check that variable first. Unset or `0` restores
  kernel-provided detection.
- **Cgroup CPU quotas are invisible.** `nproc` reads affinity, not
  bandwidth limits. A container promised "2.5 CPUs" via quota with a full
  affinity mask reports all host cores. Sizing `-j` by `nproc` in such a
  container oversubscribes; use quota-aware tooling or pin CPUs.
- **`--all` is not "what I should use".** It answers inventory questions
  (installed processors); scripts that use it to size worker pools defeat
  affinity-based isolation.
- **Hyper-threading is counted.** `nproc` sees logical CPUs, so an
  8-core/16-thread box reports 16. For workloads where SMT siblings
  contend (some FP-heavy codes), `lscpu -p` or core-level pinning is the
  better basis.
- **No output for "zero CPUs" exists.** Affinity masks always contain at
  least one CPU, and `--ignore` clamps at 1; there is no failure mode
  where parallelism should be zero.
- **`/proc/cpuinfo` is not a substitute.** It lists (on many platforms)
  online CPUs regardless of affinity and can hide hotplugged ones; on
  some architectures its format varies. `nproc` is the stable interface.
- **busybox has no `nproc`** on many tiny images (it does in some
  configurations); a portable fallback is `getconf _NPROCESSORS_ONLN`
  (though that ignores affinity) or reading
  `/sys/devices/system/cpu/online`.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Count printed successfully |
| `1` | Failure (e.g. `sched_getaffinity` error, invalid `--ignore` value) |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./nice.md`](./nice.md) — trade CPU priority instead of CPU count.
- [`./sleep.md`](./sleep.md) — pacing batch loops that don't need full parallelism.
- [`../../shell/bash.md`](../../shell/bash.md) — `$( )` command substitution patterns.

## Interview Questions

### Q: What does nproc actually measure, and how does it differ from counting entries in /proc/cpuinfo?

It prints the popcount of its process's `sched_getaffinity` mask — the
CPUs this process may be scheduled on. `/proc/cpuinfo` lists online CPUs
of the host regardless of affinity, so under `taskset`, cpusets, or
pinned containers the two diverge. `nproc --all` is the flag that switches
to inventory semantics (installed processors).

### Q: A make build in a Docker container with `--cpus=2` still spawns 64 jobs after `make -j$(nproc)`. Explain and fix.

The `--cpus=2` limit is a CFS *quota* (a rate limit on CPU time), while
`nproc` reports the affinity mask, which still includes every host core —
the container sees 64 "usable" CPUs and nothing about bandwidth. Fix by
pinning (`docker run --cpuset-cpus=0,1`, making affinity match the
promise) or by overriding parallelism explicitly
(`JOBS=${JOBS:-$(nproc)}` with the operator setting `JOBS=2`).

### Q: Why does nproc consult OMP_NUM_THREADS, and what's the risk?

OpenMP runtimes use that variable as the thread-pool size, and coreutils
chose compatibility with it so scripts and OpenMP programs agree on pool
size. The risk is leakage: any process in an environment where the
variable is set (CI images, HPC job scripts) gets a different `nproc`
answer than the kernel would give, silently changing `-j` sizing. Treat
it as a documented override, and unset it when you want ground truth.

### Q: When would you use nproc --ignore=1 instead of nproc?

When you want worker pools that leave headroom for latency-sensitive
work on the same box: with 8 usable CPUs, `make -j$(nproc --ignore=1)`
spawns 7 workers so an interactive session, SSH, or the build driver
itself keeps a core. It is a deliberate under-subscription idiom, also
useful beside storage or network daemons that need consistent CPU time.

### Q: Is nproc POSIX? What do you use on a minimal system?

No — it is a GNU coreutils extension with no POSIX spec and no classic
Unix history. On minimal/busybox images, portable choices are
`getconf _NPROCESSORS_ONLN` (POSIX-ish, but ignores affinity) or parsing
`/sys/devices/system/cpu/online`. For build scripts that already assume
coreutils (most Linux distros ship it), `nproc` is the right default.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/nproc.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
