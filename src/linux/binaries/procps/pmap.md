# pmap — report the memory map of a process

## Overview

`pmap` prints the address space of one or more processes: every memory mapping with its address range, size, permissions, and backing file. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/pmap` and is, at heart, a formatter over `/proc/<pid>/maps` and `/proc/<pid>/smaps` — there is no syscall interface to "get a memory map"; pmap reads the same text files you could read by hand.

The default output is one line per mapping: address, size, permissions, and the mapping name (`[ anon ]`, `[heap]`, `[stack]`, or a file path). The interesting work happens with the display modes: `-x` adds RSS and Dirty columns plus a total row, `-d` shows the file offset and device, and `-X`/`-XX` pass through essentially everything the kernel puts in `smaps` — Pss, Anonymous, Swap, `VmFlags` and friends.

`pmap` is often confused with `top`'s VIRT/RES columns (which are process-wide sums, not per-mapping detail) and with `free` (system-wide memory). The per-mapping breakdown is what makes pmap the tool for questions like "why does this process have 900 MB resident" or "is that heap growth or a new anonymous mapping".

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/pmap |
| First appeared | procps-ng, late 1990s (Albert Cahalan); modeled on the SunOS `pmap` |
| Standards | No standards apply; the man page notes it "looks an awful lot like a SunOS command" |

## Synopsis

```
pmap [options] pid [...]
```

Common one-line forms:

```
pmap 1234              # default: address, size, perms, mapping
pmap -x 1234           # extended: + RSS, Dirty, Mode, total row
pmap -d 1234           # device format: + offset, major:minor device
pmap -XX 1234          # every smaps field the kernel provides
pmap -x $(pgrep java)  # multiple pids, one report each
```

## How It Works

### Two source files, five output formats

pmap has exactly two data sources, selected by the display mode:

```
/proc/<pid>/maps              /proc/<pid>/smaps
 one line per mapping:         same lines + per-mapping counters:
 address, perms, offset,       Rss, Pss, Shared/Private_Clean/Dirty,
 dev, inode, path              Anonymous, Swap, THPeligible, VmFlags
        │                            │
        ▼                            ▼
 default mode, -d             -x, -X, -XX
 (size + perms + name)        (adds RSS, Dirty, and more)
        └────────────┬───────────────┘
                     ▼
          pmap formatting, total row
```

The default mode and `-d` read only `maps`; `-x`, `-X`, and `-XX` read `smaps`, which is why they cost more (the kernel walks every page in every VMA to fill in the counters). A concrete default-mode run:

```bash
$ pmap $$
11693:   /bin/bash --noprofile --norc
0000558ecaf13000    188K r---- bash
0000558ecaf42000    804K r-x-- bash
0000558ecb047000     36K rw--- bash
0000558ecb050000     44K rw---   [ anon ]
00007f1c8205b000    160K r---- libc.so.6
00007f1c82083000   1420K r-x-- libc.so.6
00007fffe3757000      8K r-x--   [ anon ]
ffffffffff600000      4K r-x--   [ anon ]
 total             4448K
```

Columns are start address, mapping size, permissions, and name. Permission letters follow the kernel's `rwx` plus `s`/`p` (shared/private): `r-x--` is a read-only executable file mapping, `rw---` is private writable, `r--s-` is a shared read-only mapping (e.g. a mapped locale archive). Note the linker's textbook layout: a read-only segment, a `r-x--` text segment, a relro `r----` segment, then `rw---` data — per library.

### Reading a real map end to end

A default `pmap` of any modern dynamically linked process tells the loader's story, top to bottom. For the bash above:

- `r---- bash` (188K) — ELF headers and read-only data (.rodata), mapped first.
- `r-x-- bash` (804K) — executable text (.text).
- two more `r---- bash` segments — RELRO (relocation read-only) and non-const data made read-only after relocation.
- `rw--- bash` (36K) — writable data (.data/.got/.bss).
- `rw--- [ anon ]` — heap overflow regions and, further down, glibc malloc arenas.
- per-library quartets (`libc.so.6`, `libtinfo.so.6.5`, `ld-linux-x-86-64.so.2`) — same four-segment shape each.
- `r--s- gconv-modules.cache` — the `s` marks a *shared* mapping; a mapped iconv cache paged in read-only for every process that uses it.
- at the top of the address space: `[stack]`, then `[vvar]`/`[vdso]`/`[vsyscall]` kernel pages.

Two details worth checking in interviews: the load base of a PIE binary lands in the `0x55..`/`0x56..` ASLR band (non-PIE executables load at the fixed `0x400000`), and every anonymous mapping between libc and `[stack]` is allocator territory — the region pmap shows "growing" when a process heap-expands.

### The special names

Mappings without a file are labeled by role:

- `[ anon ]` — anonymous memory: `mmap(MAP_ANONYMOUS)` regions, glibc malloc arenas (beyond the main heap), thread stacks, and anything else with no backing file.
- `[heap]` — the program break heap of the main arena.
- `[stack]` — the main thread stack.
- `[vdso]`, `[vvar]`, `[vsyscall]` — kernel-provided fast-syscall and clock pages present in every process.

### -x: the extended format and the total row

```bash
$ pmap -x $$ | head -4
11693:   /bin/bash --noprofile --norc
Address           Kbytes     RSS   Dirty Mode  Mapping
0000558ecaf13000     188     188       0 r---- bash
0000558ecaf42000     804     632       0 r-x-- bash
$ pmap -x $$ | tail -2
---------------- ------- ------- -------
total kB            4448    3212     276
```

- **Kbytes** is the mapping size (virtual) straight from `maps`.
- **RSS** is how much of that mapping is physically resident — 632K of the 804K text is actually paged in.
- **Dirty** is `Shared_Dirty + Private_Dirty` from smaps: pages written in RAM and thus needing swap or writeback. Read-only file mappings are always 0 there; the heap and `[ anon ]` regions are dirty almost throughout.
- The **total row** sums Kbytes, RSS, and Dirty across the whole address space.

The Kbytes-vs-RSS gap is the whole point of `-x`: a 1420K `libc.so.6` text mapping might show only a few hundred K resident, and a 64 MB `mmap`ed database file shows 64 MB of Kbytes with whatever subset is touched as RSS.

### -d: device format

```bash
$ pmap -d $$ | head -3
11706:   /bin/bash --noprofile --norc
Address           Kbytes Mode  Offset           Device    Mapping
000055ce80c4c000     188 r---- 0000000000000000 000:00029 bash
```

`Offset` is the byte offset into the backing file and `Device` is `major:minor` of the block device holding it — `000:00000` with offset 0 identifies anonymous mappings. Two mappings from the same file show different offsets (text at 0x0, data at the file's data segment). This is the mode for "which binary/library backs this mapping, and where from".

### -X and -XX: raw smaps passthrough

`-X` prints the smaps detail fields (with a header of whatever your kernel exports — the man page explicitly warns the format changes with `/proc/PID/smaps`), and `-XX` prints every field the kernel provides, including `KernelPageSize`, `MMUPageSize`, `Pss`, `Shared_Clean`, `Private_Clean`, `Anonymous`, `Swap`, `THPeligible`, and the `VmFlags` column (`rd`, `ex`, `mr`, `mw`, `ms`, `gd`, `ac`, ...). A footer sums each column with a trailing `KB` marker.

This mode is how you answer questions the aggregate numbers cannot: is this RSS shared or private (`Pss` divides shared pages by sharer count), how much of the process has been swapped (`Swap`), is transparent hugepages in play (`AnonHugePages`, `THPeligible`).

The `-c/-C/-n/-N` options save and load an rc file that pins a particular `-X`/`-XX` column layout, so scripts can depend on a stable column set across kernel versions.

### Anon vs file-backed, over time

Leak hunting is the canonical workflow: sample `pmap -x` periodically and diff.

```bash
# Which mapping grew between two samples?
$ pmap -x $(pgrep -x mydaemon) > /tmp/before
$ sleep 300
$ pmap -x $(pgrep -x mydaemon) > /tmp/after
$ diff /tmp/before /tmp/after
```

Growth in a file-backed mapping means the process mapped or paged in more of a file. Growth in `[ anon ]` / `[heap]` rows means the allocator asked the kernel for more memory — normal for a warming-up JVM, a leak signature if it never plateaus.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-x`, `--extended` | Extended format: Address, Kbytes, RSS, Dirty, Mode, Mapping + total row |
| `-d`, `--device` | Device format: Address, Kbytes, Mode, Offset, Device, Mapping |
| `-X` | More detail than `-x`; column set follows `/proc/PID/smaps` (unstable format) |
| `-XX` | Every field the kernel provides, including Pss, Swap, VmFlags |
| `-q`, `--quiet` | Suppress header and footer lines — for scripts that parse rows |
| `-p`, `--show-path` | Full path in the Mapping column (`/usr/bin/bash` instead of `bash`) |
| `-A low,high` | Restrict output to an address range; one comma-separated string |
| `-c` / `-C file` | Read the default / a named rc file for column layout |
| `-n` / `-N file` | Create the default / a named rc file (pid arguments not allowed) |
| `-h`, `-V` | Help / version |

### Restricting with -A

```bash
$ pmap -A 7f0000000000,7fffffffffff -p $$
```

`-A` takes a single comma-separated string and filters mappings to the range — handy for isolating a library's footprint in a huge map, or cutting everything below the mmap region.

## Usage Patterns

```bash
# Quick per-mapping footprint of a process
pmap $(pgrep -x mysqld | head -1) | tail -20

# Total RSS and Dirty for a process, header-free for scripts
pmap -q -x $(pgrep -x redis-server) | tail -1

# Which libraries dominate the resident set?
pmap -x $PID | sort -k3 -n -r | head

# Confirm a library is actually mapped from where you think
pmap -p $PID | grep libssl

# Find shared (copy-on-write) dirty pages vs private ones
pmap -XX $PID | awk '$18 > 0 || $19 > 0'

# Watch heap growth of a suspected leak, one sample per minute
while :; do pmap -x $PID | tail -1; sleep 60; done >> heap-growth.log

# Only the anon mappings: malloc arenas and thread stacks
pmap -q $PID | grep 'anon'

# Prove a process is 32-bit vs 64-bit by its address range shape
pmap $PID | head -2

# Device format to spot which filesystem backs each mapping
pmap -d $PID | awk '$5 != "000:00000"'

# Every process of a user, one summary line each
for p in $(pgrep -u deploy); do echo -n "$p "; pmap -q -x $p | tail -1; done

# Isolate the heap region only
pmap -q -x $PID | grep -w heap

# Watch thread stacks appear: one new [ anon ] block per pthread_create
pmap -q $PID | grep -c 'anon'; sleep 5; pmap -q $PID | grep -c 'anon'

# Only mappings inside the 64-bit mmap region (cut the PIE/text low range)
pmap -q -x $PID | awk '$1 ~ /^00007f/'

# Classify a binary as PIE or fixed-address by its first mapping's base
pmap -q $PID | head -1 | grep -q '^00000000004' && echo non-PIE || echo PIE

# Compare two similar workers' maps after stripping volatile columns
pmap -q $PID1 | awk '{print $2, $NF}' | sort > a.txt
pmap -q $PID2 | awk '{print $2, $NF}' | sort > b.txt
diff a.txt b.txt
```

## Nuances and Gotchas

- **Kbytes is virtual, RSS is resident.** A 1 GB `mmap` of a sparse file shows 1 GB of Kbytes and maybe 4 MB of RSS. Reporting "the process uses 1 GB" from default-mode output is wrong.
- **RSS double-counts shared pages.** The total row sums per-mapping RSS, so libc's pages are counted once per process. System-wide, use `Pss` from `-XX` (or `smaps_rollup`) — that is why 50 processes × 20 MB RSS can coexist with 200 MB of real usage.
- **Dirty includes shared dirty.** A shared writable mapping that another process wrote shows up in this process's Dirty column too. Use `-XX`'s `Private_Dirty` when you need "pages this process alone touched".
- **Permission boundary.** `/proc/PID/maps` and `smaps` are readable only by the process owner or root; poking at another user's PID yields a header with no rows (the PID title line may still print) and exit status 1 — reserve 42 for "PID does not exist".
- **Exit code 42 is a feature.** When pmap was asked for several PIDs and did not find all of them, it exits 42 ("did not find all processes asked for") — scripts must not treat nonzero as "pmap broke".
- **`-X` format is kernel-dependent.** New kernels add smaps fields (LazyFree, THPeligible...), so column positions shift. Parse `-XX` by header name, not by column number, or pin a layout with the rc options.
- **Kernel threads have no map.** A kthread has an empty address space; pmap on its PID yields a header and a tiny/zero total rather than an error.
- **ASLR moves everything.** Addresses differ per run and per boot; never compare maps across processes line-by-line, compare by Mapping name and sizes.
- **The biggest pmap is not automatically the culprit.** A huge total dominated by file-backed, shared mappings (glibc, JVM CDS archive, ICU data) is paid once across the whole system; the OOM killer's victim is decided by badness scoring, not by the top of your pmap. Compare `Pss` totals before assigning blame.
- **No BSD/macOS equivalent flag-for-flag.** macOS has `vmmap`, Solaris had `pmap` with different flags. procps `pmap` is Linux-only tooling.

## Exit Status

Documented in the man page:

- `0` — success.
- `1` — failure (bad option, unreadable process).
- `42` — did not find all processes asked for (any missing PID in the argument list).

## Related Commands

- [`ps`](./ps.md) — the aggregate view; `ps -o rss,vsz` for one-line numbers, pmap for per-mapping detail.
- [`top`](./top.md) — live per-process memory columns; pmap is the drill-down tool behind them.
- [`free`](./free.md) — system-wide memory totals that per-process RSS sums refuse to match.
- [`pgrep`](./pgrep.md) — reliable PID lookup to feed pmap.
- [`watch`](./watch.md) — wrap `pmap -x PID | tail -1` for a live growth meter.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — where process address spaces fit into the bigger picture.

## Interview Questions

### Q: In `pmap -x`, what is the difference between the Kbytes and RSS columns?

Kbytes is the size of the virtual mapping; RSS is how many of those pages are currently resident in RAM. For file-backed mappings like shared libraries the two diverge wildly (only the touched pages are faulted in); for the heap and anonymous regions they are usually close because written pages cannot be evicted without swap. Reading Kbytes as "memory used" is the classic error — it is address-space reservation.

### Q: What is pmap's exit status 42, and why would the authors do that?

The man page documents `42` as "did not find all processes asked for". It distinguishes "pmap ran but some PIDs vanished/never existed" from a hard failure (`1`) — useful when you feed it a list of PIDs captured earlier, since PIDs are recycled constantly. A wrapper script can decide that partial results are acceptable while still detecting the race.

### Q: A process leaks memory. How do you tell whether it is the heap or something else?

Sample `pmap -x PID` on an interval and diff. Growth in `[heap]` or `[ anon ]` rows points at malloc/free imbalance or `mmap`-heavy allocation (glibc moves large allocations to anonymous arenas, which appear as separate `[ anon ]` rows). Growth in a named file mapping points at mapped-file buffering, not a heap leak. `-XX` adds the `Anonymous` and `Private_Dirty` columns, which cleanly separate "memory the process dirtied" from shared or file-backed residency.

### Q: Why can the sum of RSS over all processes exceed the machine's physical memory usage?

Every process counts the pages of shared libraries (and any other shared mapping) fully in its own RSS. With hundreds of processes mapping the same libc, those pages are counted hundreds of times in a sum. The proportional set size (`Pss`, visible via `pmap -XX`) splits shared pages among their sharers, so Pss sums agree much better with `free`'s "used" — a standard follow-up question in interviews about memory accounting.

### Q: What is in the `[vdso]`, `[vvar]`, and `[vsyscall]` mappings, and why are they in every process?

They are kernel-created pages that accelerate common operations: `[vdso]` holds user-space-executable code for syscalls like `gettimeofday` (no context switch), `[vvar]` holds the clock data that code reads, and legacy `[vsyscall]` is the pre-vDSO mechanism. They show up at fixed high addresses in every address space; interviewers use them to check whether a candidate has actually looked at a memory map.

### Q: How does pmap relate to `/proc/PID/smaps_rollup`?

`smaps_rollup` (kernel 4.14+) gives the aggregated Rss/Pss/Dirty/Swap totals in one file, which the kernel computes far faster than a tool summing thousands of per-mapping lines from `smaps`. pmap's `-x` total row is essentially a user-space rollup, but for big processes a script reading `smaps_rollup` is cheaper; pmap remains the tool when you need per-mapping attribution, not just totals.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/pmap.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
