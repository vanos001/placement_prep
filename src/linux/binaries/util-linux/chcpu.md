# chcpu — enable, disable, and configure CPUs

## Overview

`chcpu` switches CPUs on and off and drives the architecture-specific CPU
configuration interfaces. Its everyday work is logical CPU hotplug:
`-e`/`-d` take a CPU list and write to the kernel's per-CPU `online`
attribute, bringing cores in or out of the scheduler. Its mainframe work —
`-c`/`-g` (de)configure, `-p` dispatching mode, `-r` rescan — maps to
s390 sysfs attributes used by LPAR/z/VM environments to add and remove
CPUs from the running system. It ships in the `util-linux` package at
`/usr/sbin/chcpu`.

You reach for it when a workload should be pinned away from certain cores
(benchmarking, license-limited software, power saving), when simulating a
smaller machine, or on s390 when the hypervisor adds CPUs that need
configuring. It is often confused with `taskset` (which restricts a
process to CPUs via affinity, leaving all CPUs running), with `nproc`
(merely counts usable CPUs), and with `lscpu` (read-only topology and
online-state reporting — the natural companion).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/chcpu |
| First appeared | util-linux 2.22 (2012) |
| Standards | Linux sysfs CPU hotplug interface; s390 hypervisor interfaces |

## Synopsis

```
chcpu [options]
```

Main one-line forms:

```
chcpu -d 2-3            # take CPUs 2 and 3 offline
chcpu -e 2-3            # bring them back online
chcpu -p vertical       # s390: set dispatching mode
chcpu -r                # s390: rescan for newly added CPUs
```

CPU lists accept the standard range syntax: `0`, `0-3`, `0-3,8,12-15`.

## How It Works

### What enable/disable actually does

The kernel exposes one sysfs switch per logical CPU:

```
$ cat /sys/devices/system/cpu/online
0-7
$ echo 0 | sudo tee /sys/devices/system/cpu/cpu3/online
#          ^ chcpu -d 3 performs exactly this, plus error handling
$ cat /sys/devices/system/cpu/online
0-2,4-7
$ chcpu -d 2-3      # the friendly wrapper doing the same for two CPUs
CPU 2 disabled
CPU 3 disabled
```

Taking a CPU offline: the scheduler drains it, migrates its tasks to other
CPUs, stops the per-CPU kernel threads (kworkers, ksoftirqd for that CPU),
and removes it from `/proc/cpuinfo`, `/proc/stat`, and the scheduler's
domain. Bringing it back re-registers it. The state is not persistent —
a reboot re-onlines everything unless you add `maxcpus=`/`nr_cpus=` kernel
parameters.

### The s390-specific half

```
attribute                            chcpu flag    meaning
/sys/devices/system/cpu/cpuN/configure   -c/-g     (de)configure: make the
                                                   CPU (un)available to the
                                                   running LPAR at all
/sys/devices/system/cpu/dispatching      -p        polarization: horizontal
                                                   (equal share) or vertical
                                                   (low/medium/high weight)
/sys/devices/system/cpu/rescan           -r        probe the hypervisor for
                                                   newly defined CPUs
```

Configure is one level deeper than online: an unconfigured CPU is not even
a candidate for scheduling and consumes no hypervisor resources. On x86
these operations have no sysfs backing and chcpu fails them with an error
— which is the portability gotcha to know.

### What online state means elsewhere

```
$ lscpu | grep -E '^CPU\(s\)|On-line|Off-line'
CPU(s):                    8
On-line CPU(s) list:       0-2,4-7
Off-line CPU(s) list:      3
$ nproc                     # respects affinity, sees 7 now
7
```

Tools that count CPUs fall into two camps: those reading the online map
(`lscpu`, `nproc` in most cases) and those reading the affinity mask of
the calling process (`nproc` under taskset, GNU `sort --parallel` auto
tuning, build systems like `make -j$(nproc)`). Disabling a CPU changes
both; affinity restricts only one process.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-e, --enable <cpu-list>` | Put the listed CPUs online (write `1` to cpuN/online) |
| `-d, --disable <cpu-list>` | Take the listed CPUs offline (write `0`) |
| `-c, --configure <cpu-list>` | s390: configure the CPUs (attach to the system) |
| `-g, --deconfigure <cpu-list>` | s390: deconfigure the CPUs (detach from the system) |
| `-p, --dispatch <mode>` | s390: `horizontal` or `vertical` dispatching mode |
| `-r, --rescan` | s390: trigger rescan of CPUs defined at the hypervisor |
| `-h, --help` / `-V, --version` | Usage / version |

## Usage Patterns

```bash
# Take two cores offline to simulate a 4-core machine before a demo
chcpu -d 6-7
```

```bash
# Bring them back
chcpu -e 6-7
```

```bash
# Check the result the way an interviewer would
lscpu | grep -E 'On-line|Off-line'
```

```bash
# Benchmark hygiene: offline SMT siblings to compare real cores
chcpu -d 4-7            # on a 4C/8T box, siblings of 0-3
```

```bash
# License-restricted software sees fewer CPUs via nproc/sysconf
chcpu -d 8-63 && nproc
```

```bash
# s390: pick up CPUs the z/VM administrator just added
chcpu -r && chcpu -c 8-15 && chcpu -e 8-15
```

```bash
# s390: prefer vertical polarization for better hypervisor packing
chcpu -p vertical
```

```bash
# Equivalent raw sysfs, for containers where chcpu is absent
echo 0 > /sys/devices/system/cpu/cpu3/online
```

```bash
# Watch load rebalance while disabling a busy CPU
uptime; chcpu -d 3; uptime
```

## Nuances and Gotchas

- **CPU 0 is special.** Many kernels refuse to offline CPU 0 (it hosts
  essential per-CPU infrastructure); `chcpu -d 0` fails with `EINVAL`.
- **Not persistent.** Offline state vanishes at reboot; use `maxcpus=`,
  `nr_cpus=`, or init scripts/systemd units for lasting changes.
- **Affinity vs online.** `taskset` hides CPUs from one process but leaves
  them burning power and running kernel threads; `chcpu -d` removes them
  from the system entirely. Software licensed per "visible" CPU may still
  count online CPUs through other mechanisms — verify, don't assume.
- **s390-only flags fail elsewhere.** `-c`, `-g`, `-p`, `-r` have no x86
  sysfs backing; scripts using them unconditionally break on generic
  hardware.
- **Performance side effects.** RCU, irqbalance, and per-CPU kworkers need
  a moment after a state change; benchmarks run immediately after
  toggling measure transition noise. Also, offlining can *increase* power
  use in some SMT topologies.
- **Containers can't do this.** /sys is the host's; in an unprivileged
  container the writes fail with permission errors. Do it in the VM or
  on the host.
- **The CPU must be online-capable.** Some CPUs are shown but marked
  `can_offline: 0`; firmware/hypervisor decides, not chcpu.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested CPU operations succeeded |
| 1 | Usage error, or the kernel refused (offline impossible, no such CPU, s390 attribute missing) |

## Related Commands

- [`chmem`](./chmem.md) — the sibling tool for memory hotplug via sysfs
- [`chrt`](./chrt.md) — scheduling policy/priority per process, not CPU topology
- [`choom`](./choom.md) — another small process-tuning wrapper in this collection
- [util-linux overview](./overview.md) — the rest of the system-configuration tools

## Interview Questions

### Q: What is the difference between taking a CPU offline and using taskset to pin a process away from it?

Offline (`chcpu -d`) removes the CPU from the scheduler entirely: no
user or kernel tasks run there, it disappears from /proc/cpuinfo and
sysconf counts. `taskset` changes only one process's affinity mask; the
CPU still runs other processes and all its kernel threads. License
metering, benchmarking, and power measurement care about the former;
isolation of a single workload cares about the latter.

### Q: What does chcpu -d actually write, and how would you do the same thing without the tool?

It writes `0` to `/sys/devices/system/cpu/cpuN/online` and reports the
kernel's response. The manual equivalent is
`echo 0 > /sys/devices/system/cpu/cpu3/online`. The tool's added value is
CPU-list parsing, sane error reporting, and the s390 operations.

### Q: How do you make a reduced CPU count survive a reboot?

Offline state is runtime-only. Options: kernel parameters `maxcpus=N`
(bring up N at boot) or `nr_cpus=N` (compile-time cap, saves memory on
huge machines), or a boot-time systemd unit/init script that runs
`chcpu -d`. The detail interviewers probe: `maxcpus` limits what is
onlined at boot, while `nr_cpus` limits what exists at all — NUMA
topology and hotplug behave differently under each.

### Q: Which of chcpu's flags are architecture-specific, and what happens if you use them on x86?

`-c`/`-g` (configure), `-p` (dispatching mode), and `-r` (rescan) map to
s390 sysfs attributes provided by the LPAR/z/VM hypervisor interface. On
x86 the attributes do not exist and the operations fail with an error.
Only `-e`/`-d` are generic, because they are the generic CPU-hotplug
sysfs interface.

### Q: A monitoring agent suddenly reports half the CPUs. Give two plausible causes.

Either someone ran `chcpu -d`/sysfs offline (check
`lscpu`'s Off-line list and `journalctl` for hotplug events) — or the
agent's CPU count comes from the process affinity mask (`nproc`,
sysconf(_SC_NPROCESSORS_ONLN) respects affinity on some builds), and a
cgroup cpuset or taskset change shrunk it. Distinguishing online state
from affinity is exactly the interview point.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/chcpu.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
