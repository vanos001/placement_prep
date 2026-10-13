# setarch — run a program under a modified process personality

## Overview

`setarch` executes a program after applying a Linux *personality* — a
per-process flag set the kernel consults when laying out the virtual
address space, reporting the architecture via `uname`, or emulating old
ABI quirks. Its most famous use is disabling ASLR (`setarch -R`) to get
reproducible memory layouts under a debugger; its second is lying about
the architecture (`setarch linux32 uname -m` reports `i686` on an x86_64
kernel). It ships with the `util-linux` package (Debian bookworm) at
`/usr/bin/setarch`, plus the `linux32`, `linux64`, `i386` and `x86_64`
symlinks described in the Variants subsection below.

`setarch` is often confused with `uname` (reports the *system*'s
architecture; setarch changes what one process tree *sees*), with `chrt`
and `ionice` (scheduling attributes, orthogonal syscalls), and with
`setpriv` (privilege/credential control, also orthogonal).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/setarch (plus /usr/bin/linux32, linux64, i386, x86_64 symlinks) |
| First appeared / lineage | early-2000s Linux personality tool, bundled with util-linux |
| Standards | None — Linux `personality(2)` specific |

## Synopsis

```
setarch [<arch>] [options] [<program> [<argument>...]]
```

Common one-line forms:

```
setarch linux32 uname -m        # report a 32-bit architecture
setarch -R ./crashy             # run with ASLR disabled
setarch --show                  # print the current personality
setarch --list                  # list known architecture personas
```

## How It Works

### The personality(2) syscall

Linux keeps a per-process `personality` word, inherited by children
across `fork` and `exec`. Bits in it ask the kernel to alter behavior:

- which architecture `uname()` reports (`linux32` sets `PER_LINUX32`,
  visible as `0x8` in `/proc/self/personality`),
- whether address-space layout is randomized (`ADDR_NO_RANDOMIZE`),
- legacy ABI compatibilities (`MMAP_PAGE_ZERO`, `READ_IMPLIES_EXEC`,
  `ADDR_LIMIT_3GB`, `WHOLE_SECONDS`, `STICKY_TIMEOUTS`, ...).

`setarch` calls `personality(2)` with the requested flags, then *execs*
the program in the same process — so the flags are in effect before the
target's dynamic loader ever runs, and the target cannot easily tell it
is being wrapped. The exit status of `setarch` is therefore the exit
status of the program it exec'd.

```
shell ──fork/exec──► setarch ──personality(2)──► execve(prog)
                        (same process)                │
                                                      ▼
                              prog + all its children run with the
                              modified personality (inherited)
```

Verified behavior on an x86_64 kernel:

```bash
$ setarch linux32 uname -m
i686
$ cat /proc/self/personality            # PER_LINUX
00000000
$ setarch linux32 cat /proc/self/personality
00000008                                # PER_LINUX32
```

And the flagship ASLR demo — three runs of the same binary, then three
runs with `-R`:

```bash
$ for i in 1 2 3; do sh -c 'cut -d- -f1 /proc/self/maps | head -1'; done
55e8f25c8000
55b933b76000
564a278b4000
$ for i in 1 2 3; do setarch -R sh -c 'cut -d- -f1 /proc/self/maps | head -1'; done
555555554000
555555554000
555555554000
```

### Variants: the architecture symlink aliases

Debian installs several symlinks to `setarch` (verified with
`readlink`: all point at `setarch`). The target personality is derived
from `argv[0]`, so calling the symlink is shorthand for passing the arch
as the first argument:

| Symlink | Equivalent | Personality | Effect |
| --- | --- | --- | --- |
| `linux32` | `setarch linux32` | `PER_LINUX32` | `uname -m` reports i686-class on x86_64 |
| `i386` | `setarch i386` | `PER_LINUX32` | alias of linux32 (as are i486/i586/i686/athlon) |
| `linux64` | `setarch linux64` | `PER_LINUX` | normal 64-bit persona (undoes linux32) |
| `x86_64` | `setarch x86_64` | `PER_LINUX` | alias of linux64 |

```
$ readlink /usr/bin/linux32 /usr/bin/x86_64
setarch
setarch
$ setarch --list
uname26
linux32
linux64
i386
...
x86_64
```

Note what `linux32` does *not* do: it does not make 32-bit binaries run.
Execution of i386 code needs kernel compat support and 32-bit libraries;
the personality only changes what the process is *told* about itself and
how its address space is shaped.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-R, --addr-no-randomize` | Disable ASLR for the child (deterministic mmap/stack bases). |
| `-v, --verbose` | Print the personality flags being switched on. |
| `--list` | List settable architecture personas and exit. |
| `--show[=personality]` | Print the current (or a named) personality and exit. |
| `linux32` / `linux64` / `i386` / `x86_64` | Architecture personas (see Variants). |
| `--uname-2.6` | Turn on `UNAME26` (report `2.6.<x>`-style kernel version strings). |
| `-3, --3gb` | Limit the address space to 3 GiB (`ADDR_LIMIT_3GB`). |
| `-B, --32bit` | `ADDR_LIMIT_32BIT` persona. |
| `-X, --read-implies-exec` | `READ_IMPLIES_EXEC`: readable pages are executable (for old interpreters/JITs). |
| `-Z, --mmap-page-zero` | Map page 0 (`MMAP_PAGE_ZERO`) — legacy ABI emulation. |
| `-L, --addr-compat-layout` | Legacy virtual-memory allocation layout. |
| `-S, --whole-seconds` / `-T, --sticky-timeouts` | Old ABI time/timeout behaviors. |
| `-F, --fdpic-funcptrs` | FDPIC function-pointer descriptors (embedded ABIs). |
| `-I, --short-inode` | `SHORT_INODE` legacy persona. |
| `--4gb` | Ignored; kept for backward compatibility. |

## Usage Patterns

```bash
# Reproduce a memory-layout bug deterministically under gdb
setarch -R gdb ./vulnerable
# (gdb also disables randomization for its inferiors by default)
```

```bash
# Pretend to be 32-bit for a build system that keys off uname -m
setarch linux32 ./configure && make
```

```bash
# Check what a persona reports before running anything heavy
setarch i686 uname -a
```

```bash
# Inspect the raw personality value of a process tree
setarch linux32 sh -c 'cat /proc/self/personality; sleep 30' &
grep -r . /proc/$!/personality 2>/dev/null; cat /proc/$!/personality
```

```bash
# Readable-implies-executable: run old bytecode interpreters
setarch -X ./legacy-vm program.bin
```

```bash
# Undo a 32-bit persona inherited from a wrapper script
setarch linux64 uname -m
```

```bash
# Show the personality of the current shell's process (no persona)
setarch --show
```

```bash
# Trace what setarch actually switched on before exec
setarch -v -R linux64 true
# Switching on ADDR_NO_RANDOMIZE.
# Execute command `linux64'.
```

```bash
# Cap the address space at 3 GiB to emulate a 32-bit memory environment
setarch -3 ./memory-hog --limit 2.5G
```

```bash
# Same idea as a systemd service property
# [Service]
# Personality=drop-ASLR   # or: personality=linux32
```

## Nuances and Gotchas

- **The personality is inherited by everything the child spawns.** A
  `setarch -R make` disables ASLR for every compiler and test binary the
  build launches. Scope it deliberately.
- **`-R` is a debugging aid, not a hardening feature.** Long-running
  services run under `setarch -R` lose address-space randomization for
  the whole tree — the opposite of what you want in production. systemd
  exposes `Personality=` for the rare legitimate case.
- **`linux32` changes the story, not the CPU.** `uname -m` says `i686`,
  but actual i386 execution still needs compat loading and 32-bit libs;
  `setarch linux32 /bin/ls` on a 64-bit system runs the *64-bit* `/bin/ls`
  unless the loader picks a 32-bit one.
- **Unknown persona names fail before exec** with
  `setarch: <name>: Unrecognized architecture` and exit status 1 — the
  persona list is compile-time (`--list`).
- **`--4gb` is a no-op** kept for ancient scripts; don't rely on it.
- **Exit status is the program's** (`setarch -R false` yields 1); exec
  failures surface as setarch's own error with status 1 (for a bad
  architecture) — different from the 126/127 shell conventions.
- **`/proc/<pid>/personality`** shows the live value in hex
  (`00000008` = `PER_LINUX32`); it is the ground truth when debugging
  what a wrapper actually applied.
- **setarch cannot change credentials or scheduling** — pair it with
  `setpriv` (uid/gid/caps) or `chrt`/`ionice` (scheduling) when a test
  needs more than one attribute changed.

## Exit Status

| Code | Meaning |
| --- | --- |
| exit status of the program | setarch replaces itself with the program; its status is what you see. |
| 1 | setarch's own failure: unrecognized architecture, bad option, `personality(2)` rejected. |

## Related Commands

- [`setpriv`](./setpriv.md) — change credentials, groups and capabilities instead of the personality.
- [`chrt`](./chrt.md) — scheduling policy/priority wrapper, the same "wrap and exec" design.
- [`ionice`](./ionice.md) — I/O scheduling class wrapper.
- [`prlimit`](./prlimit.md) — resource-limit wrapper for the same process tree.
- [`lscpu`](./lscpu.md) — reports the real system architecture; contrast with what `linux32` fakes.
- [Process management](../../admin/process-management.md) — how processes inherit attributes across fork/exec.
- [systemd](../../admin/systemd.md) — `Personality=` unit setting applies the same flags per service.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: What does setarch -R actually do, and when would you use it?

It sets the `ADDR_NO_RANDOMIZE` personality bit before exec'ing the
program, so the kernel places the stack, mmap area and (with matching
loader behavior) shared libraries at deterministic addresses — ASLR is
off for that process tree. Use it to reproduce address-dependent bugs,
compare memory layouts across runs, or teach/analyze exploitation
defense mechanisms. It is per-invocation and inherited by children.

### Q: How can uname report i686 on an x86_64 kernel?

`uname` reports the personality-adjusted architecture. `setarch linux32`
(or the `linux32`/`i386` symlink) sets `PER_LINUX32`, which the kernel
uses when answering `uname` for that process tree — `/proc/self/
personality` shows `0x8`. The CPU still runs 64-bit code; running actual
32-bit binaries is a loader/libc matter, not a personality matter.

### Q: Where do setarch, setpriv, chrt and ionice overlap and where not?

All four wrap a program, change one Linux per-process attribute family,
then exec: setarch — `personality(2)` (address space, uname view);
setpriv — credentials, groups, capabilities, `no_new_privs`; chrt —
scheduling policy/priority (`sched_setscheduler`); ionice — I/O
priority (`ioprio_set`). They compose: `setarch -R setpriv --reuid=1000
...` changes both layout and identity in one tree.

### Q: A build script behaves differently inside one CI job only, and memory addresses in core dumps repeat exactly across runs. Hypothesis?

Someone wrapped the build (or its container runtime inherited) a
`ADDR_NO_RANDOMIZE` personality — e.g. `setarch -R`, a `Personality=`
unit setting, or a debugger-style launcher. Check with `cat
/proc/<pid>/personality` (nonzero bits) and audit the launcher chain.
Reproducible addresses are convenient for debugging and a security smell
in production.

### Q: Why does setarch exec the program instead of forking it?

Because the personality must be in effect before the program's dynamic
loader runs and because exec preserves the process: after `personality(2)`
succeeds, `execve` swaps the image while keeping the flag. Forking would
add a pointless intermediate process, complicate signal and exit-status
semantics, and still leave the original unmodified. Same design you see
in `chrt`, `ionice`, `nice` and `setpriv`.

### Q: What is `READ_IMPLIES_EXEC` and why might an old interpreter need it?

Old ABIs assumed any readable memory mapping was executable. Modern
kernels separate the two, breaking ancient JITs and bytecode VMs that
never called `mprotect`. The `READ_IMPLIES_EXEC` persona (-X) restores
the old mapping behavior for that process tree, at the obvious cost of
making W^X protections moot within it.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/setarch.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
