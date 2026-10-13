# taskset — set or retrieve a process's CPU affinity

## Overview

`taskset` manipulates the **CPU affinity mask** of a process: the set of CPUs the kernel is allowed to schedule it on. It can launch a new command already pinned to chosen CPUs (`taskset -c 2-3 ./job`), or read/rewrite the affinity of a running PID (`taskset -pc 0-3 1234`). It is a thin, script-friendly wrapper over the Linux `sched_setaffinity(2)`/`sched_getaffinity(2)` syscalls and ships in the Debian `util-linux` package at `/usr/bin/taskset`.

You reach for `taskset` when isolating noisy workloads onto specific cores, keeping a latency-sensitive process away from interrupt-heavy CPUs, or testing NUMA-locality hypotheses in benchmarks. It is often confused with `chrt` (changes the *scheduling policy/priority*, not the CPU set), `numactl` (adds memory-binding on top of CPU binding), `nice`/`ionice` (fair-share knobs, not placement), and cgroup `cpuset` controllers (persistent, kernel-side per-cgroup affinity — `taskset` is a one-shot per-process action).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/taskset |
| First appeared | standalone tool (R. Love, mid-2000s), absorbed into util-linux in the early 2010s |
| Standards | none; Linux-specific (`sched_setaffinity(2)`) |

## Synopsis

```
taskset [options] [mask | cpu-list] [pid | command [args...]]
taskset -p [mask | cpu-list] pid
taskset -p -c [cpu-list] pid
```

Main one-line forms:

```
taskset -c 0,2-3 make -j4       # run make on CPUs 0, 2 and 3
taskset -p 1234                 # print PID 1234's mask (hex)
taskset -pc 0-7 1234            # set PID 1234's affinity to CPUs 0-7
taskset -apc 0-3 1234           # same, but for every thread of PID 1234
```

## How It Works

### Two syscalls, one bitmask

Everything `taskset` does is one of two calls:

```
sched_getaffinity(pid, size, &mask)   ->  read the allowed-CPU set
sched_setaffinity(pid, size, &mask)   ->  write the allowed-CPU set
```

The kernel represents affinity as a bitmap over CPU numbers (bit N set = CPU N allowed). `taskset` accepts that bitmap in two spellings:

```
mask format:  0x55, 03, 55h ...    hexadecimal by default, octal if it
                                   starts with 0  (bit N = CPU N)
list format:  0,3,7-11 or 0-31:2   (-c flag; ":N" is a stride, so
                                   0-10:3 means 0,3,6,9)
```

```
              list "0,3,7-11"  ==  mask 0x8a0 ==  bits 0,3,7,8,9,10
                 CPU: 0 1 2 3 4 5 6 7 8 9 10
        mask bit: x . . x . . . x x x  x
```

After a successful `sched_setaffinity`, the kernel guarantees the task will not be scheduled outside the new mask; it does **not** guarantee an immediate migration. A running task is migrated at the next scheduler decision, and some kernel threads may legitimately stay put for a while (the `taskset(1)` man page demonstrates exactly this with `kswapd`).

### Inheritance and defaults

A new process inherits its parent's affinity mask across `fork()`/`exec()`. That single fact explains most real-world uses:

```
# everything the shell starts from now on stays on CPUs 2-3:
$ taskset -pc 2-3 $$
pid 28518's current affinity list: 0,1
pid 28518's new affinity list: 2,3
```

Conversely it is a debugging trap: a daemon pinned in its unit file passes the pin to every child, and only `-a` (all threads) makes changes visible across a multithreaded server.

### The permission and validity model

- Any user may *read* the affinity of their own processes; setting another user's affinity requires `CAP_SYS_NICE`.
- Setting a CPU that exists but is outside your `cpuset` (cgroup) fails with `EINVAL` — the kernel rejects masks that are empty after intersecting with the allowed set.
- Setting a CPU that does not exist fails as well; very large CPU numbers may exceed the tool's compiled bitmap size on old builds.
- The affinity mask constrains *scheduling*, not *memory*. A task pinned to one NUMA node still allocates memory anywhere unless `numactl`/mempolicy is used.

### Observing the ground truth

`taskset` reads the same kernel state the procps tools show; knowing both spellings helps debugging:

```bash
$ grep Cpus_allowed_list /proc/1234/status
Cpus_allowed_list: 0-1
$ ps -o pid,psr,comm -p 1234     # psr = CPU the task last ran on
$ taskset -pc 1234
pid 1234's current affinity list: 0-1
```

At the library level the same calls are `pthread_setaffinity_np(3)`/`pthread_getaffinity_np(3)` for threads and `sched_setaffinity(2)` for tasks — `taskset` is the CLI over exactly those. When affinity looks "wrong", check the cgroup boundary first (`cat /sys/fs/cgroup/cpuset.cpus.effective` or the cpuset controller of the unit) because the per-task mask can never exceed it.

CPU hotplug adds a wrinkle: offlining a CPU removes it from every effective mask, and onlining does not necessarily restore a previously-requested bit. Scripts that pin to specific numbers should re-assert after topology changes.

### Affinity vs the rest of the toolbox

```
placement question                     tool
------------------------------------  ----------------------------
which CPUs may run this task?          taskset / cpuset cgroup
which CPUs SHOULD run it (DCFS hint)?  sched_setaffinity + energy
how urgent is it when it runs?         chrt (policy), nice (weight)
how much I/O bandwidth?                ionice / cgroup io.latency
memory locality / binding?             numactl, mempolicy
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p, --pid` | Operate on an existing PID instead of launching a command. |
| `-c, --cpu-list` | Use list format (`0,3,7-11`, strides like `0-31:2`) instead of a hex mask. |
| `-a, --all-tasks` | Apply to all threads of the given PID (TIDs), not just the main task. |
| `-h, -V` | Help / version. |

Usage grammar notes:

- Without `-p`, the first operand is the mask/list and the rest is the command to run.
- With `-p` and no value, it prints the current affinity; with `-p <mask> <pid>` it sets it.
- List format is almost always what you want; hex masks (`0x55555555`) are error-prone and CPU-count-dependent.

## Usage Patterns

```bash
# Launch a build pinned to two specific cores
taskset -c 2,3 make -j2
```

```bash
# Show the current shell's affinity as a CPU list
taskset -pc $$
# pid 28518's current affinity list: 0,1
```

```bash
# Restrict a running daemon (all threads) to CPUs 0-7
taskset -apc 0-7 $(pidof mysqld)
```

```bash
# Print a numeric PID's mask in hexadecimal
taskset -p 700
# pid 700's current affinity mask: 3
```

```bash
# Run a benchmark twice on disjoint halves of the machine
taskset -c 0-15 ./bench --out A &
taskset -c 16-31 ./bench --out B &
```

```bash
# Stride syntax: every second CPU (0,2,4,...) for a hyperthread test
taskset -c 0-31:2 ./compute
```

```bash
# Verify what CPUs a process may actually use (cpuset-aware view)
taskset -pc $(pidof nginx)
```

```bash
# Combine with chrt: real-time FIFO policy on a dedicated core
taskset -c 4 chrt -f 50 ./sampler
```

```bash
# Pin only the current shell, then start workers that inherit it
taskset -pc 8-11 $$; ./worker; ./worker
```

```bash
# Recover a mis-pinned process back to all online CPUs
taskset -apc 0-$(($(nproc)-1)) 1234
```

```bash
# Check before/after in one shot: -p with no value just prints
taskset -p 1
# pid 1's current affinity mask: 3
```

```bash
# Cross-check what the kernel sees for every thread of a service
for t in /proc/$(pidof nginx)/task/*; do taskset -pc $(basename "$t"); done
```

```bash
# Launch a latency test on a core far from the NIC IRQs (IRQs on 0-1)
taskset -c 6-7 ./udp_echo_bench
```

```bash
# Split a database's maintenance job onto one CPU of a 16-core box
taskset -c 15 pg_dump mydb > dump.sql
```

## Nuances and Gotchas

- **`EINVAL` from the cpuset, not the CPU count.** `taskset -c 5 1234` fails with *Invalid argument* if CPU 5 is not in your cgroup's `cpuset.cpus.effective`, even though `nproc`-style tools elsewhere show 64 CPUs. The failure is the kernel rejecting an empty intersection.
- **Setting affinity succeeds but nothing migrates.** The man page's own example: you can set `kswapd`'s mask and it stays on the old CPU. `sched_setaffinity` is a *constraint*, not a migration command.
- **Threads, not just processes.** Without `-a` you change only one thread (the PID you name is the main thread's TID). On a 64-thread server that means 63 threads keep the old mask — a classic half-applied tuning.
- **Hex mask portability.** `taskset 03 cmd` is *octal* (leading zero), and mask widths follow the machine's CPU count — list format (`-c`) is the portable spelling in scripts and CI.
- **Not POSIX, not portable.** `taskset` is Linux-only; on BSD/macOS use `taskpolicy`/`taskset` equivalents (`psrset`, `taskpolicy`, `pthread_setaffinity_np`). BusyBox ships its own `taskset` with fewer options.
- **Affinity is not isolation.** Other processes can still land on "your" CPUs; for real isolation you combine cpuset cgroups, `isolcpus`/`nohz_full` boot parameters, and IRQ affinity.
- **Memory is not pinned.** On NUMA hardware a task pinned to node 1's CPUs can still allocate on node 0; check with `numactl -s`/`numastat` before blaming the pin for slow benchmarks.
- **Exit-status subtlety.** Success only means the syscall succeeded. When running a command, `taskset`'s exit status is the command's; in affinity mode it is 0 if the PID exists and the syscall worked, 1 on rejection.
- **Hotplug invalidates pins.** Offline a CPU and every mask containing it is silently intersected; onlining later does not resurrect the old request. Long-lived pinned daemons need re-assertion hooks on topology change events.
- **Root-less containers.** In containers you may set affinity among *allowed* CPUs only; pinning "CPU 0" can mean a different physical core than on the host. NUMA benchmarks run in containers are suspect until you map the cpuset to physical topology.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Affinity read or set successfully (`sched_getaffinity`/`sched_setaffinity` succeeded). |
| 1 | Usage error, nonexistent CPU/illegal mask, or the kernel rejected the call (`EINVAL`, `EPERM`, `ESRCH`). |
| child's status | In command mode, the exit status of the executed program. |

The man page stresses: a 0 from *setting* mode does not guarantee the thread has migrated, only that it never will run outside the mask.

## Related Commands

- [`chrt`](./chrt.md) — scheduling policy/real-time priority; the other half of "where + how urgent".
- [`uclampset`](./uclampset.md) — utilization clamping: biases frequency/placement without pinning.
- [`ionice`](./ionice.md) — the I/O-scheduler analogue of fairness control.
- [`nsenter`](./nsenter.md) — enter another process's namespaces; both tools act on a live PID's kernel attributes.
- [`../../admin/process-management.md`](../../admin/process-management.md) — signals, priorities and process state context.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What does `taskset -c 2-3 command` actually change, and for whom?

It calls `sched_setaffinity(2)` on the child *before* `exec()`, restricting the kernel's scheduling of that (and all subsequently inherited) process to CPUs 2 and 3. Only that process tree is affected — the CPUs remain fully available to other tasks unless you also isolate them via cgroups or IRQ affinity.

### Q: A colleague ran `taskset -p 0x1 <pid>` on a 64-thread box and the process still shows high load on other CPUs. Diagnose.

Three likely causes, in order of probability: the PID named the main thread only and the busy work lives in other threads (fix with `-a`); the mask was applied but threads simply haven't been migrated yet (constraint, not migration — check `/proc/<tid>/status` Cpus_allowed); or the reported load is on CPUs *inside* the mask and the expectation was misread. Verify per-thread with `taskset -pc <tid>` for each TID from `/proc/<pid>/task/`.

### Q: Why does `taskset -c 5 cmd` fail with "Invalid argument" on a 2-CPU cgroup container?

`sched_setaffinity` requires the requested mask to intersect your `cpuset`'s allowed CPUs; CPU 5 does not exist in the container's effective set, so the kernel rejects the mask as empty. `nproc` reports the *allowed* CPU count (here 2), which is why it disagrees with a host-side view.

### Q: When would you choose cpuset cgroups over `taskset`?

When the restriction must be persistent, inherited administratively, and enforced for every task ever created in a workload — containers and systemd services. `taskset` is a one-shot syscall wrapper ideal for ad-hoc commands and debugging; cgroup `cpuset` is declarative state managed by the init system.

### Q: Difference between `taskset`, `chrt` and `uclampset` in one sentence each?

`taskset` constrains *which* CPUs a task may run on; `chrt` changes *how* it competes once scheduled (policy and real-time priority); `uclampset` biases the utilization signal that drives frequency and energy-aware placement decisions. They compose: a real-time task can be pinned (`taskset`), made FIFO (`chrt`) and boosted (`uclampset -m`) at once.

### Q: Why does the man page warn that a successful set "does not guarantee the thread has migrated"?

Because affinity is a scheduling constraint evaluated at future scheduling points. Kernel threads like `kswapd` may stay on their current CPU until internal conditions change; the syscall returning 0 only certifies the *mask*, not instantaneous placement. To force migration you would need to wake the task or rely on load balancing.

### Q: How do you pin a process and verify the pin survived exec and threading?

Set the mask on the parent before exec (`taskset -c 2-3 ./daemon`) so inheritance carries it across exec, then enumerate `/proc/<pid>/task/*` and check each thread's `Cpus_allowed_list` (or `taskset -apc 2-3` per TID). Verification is per-thread because a multithreaded process can legally have per-thread masks; the parent's mask is only the default children inherit.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/taskset.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
