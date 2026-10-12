# Feature -> version -> availability matrix (XR-201..XR-210)

## Overview

This matrix tracks ten modern kernel features through the chain that decides
whether a program can actually use them: **kernel feature -> minimum kernel
version -> libc availability -> runtime prerequisites**. A feature is not
usable because a syscall number exists; it is usable when the running kernel
has it *and* is configured for it, when your libc either wraps it or leaves you
a supported way to call it raw, and when the runtime gates (capabilities,
boot parameters, cgroup versions, seccomp behavior) are satisfied. The rows are
`XR-201..XR-210` of the [coverage ledger](./ledger.md) (statuses authoritative
there: all 10 documented; XR-208/XR-209 upgraded in the 7-d pass).

How to read each row:

- The **kernel version** column carries the minimum version in which the
  feature's syscall(s) appeared; staged follow-ups are listed in the prose.
- The **glibc** and **musl** columns state what each libc gives you: a wrapper
  (with the symbol version), a raw `syscall()`/`SYS_*` macro path, or nothing.
- The **runtime prerequisites** column names the config gate, capability, boot
  parameter, or filter interaction that still stands between you and the
  feature on an otherwise-current system.

Provenance and honesty: version claims below were **tag-probe verified**
during this encyclopedia's research passes -- kernel tables and UAPI headers
were fetched at consecutive release tags on torvalds/linux and diffed; glibc
claims come from the glibc `NEWS`/`Versions` files cross-checked with `nm -D`
on the installed glibc 2.41; musl claims come from the musl 1.2.5 tree and
`WHATSNEW`. Claims that could not be double-sourced are flagged in place
instead of asserted. Every syscall cites its `SC-<name>` row in the
[syscall ledger](../syscalls/ledger.md).

One correction is recorded in place: the ledger's XR-209 note historically
said cachestat landed in **6.1**; the tag probe in the memory-syscall pass
fixed the value at **6.5** (absent at v6.4, present at v6.5; `cachestat.2`
HISTORY agrees). This page carries 6.5.

Index of the ten rows (statuses are the ledger's):

| Row | Feature headline | Status |
|---|---|---|
| XR-201 | io_uring (5.1/5.5+) | documented |
| XR-202 | pidfd API (5.3+) | documented |
| XR-203 | openat2 (5.6) / landlock (5.13) | documented |
| XR-204 | clone3 (5.3+) | documented |
| XR-205 | time64 (5.1, 32-bit) | documented |
| XR-206 | statx (4.11) | documented |
| XR-207 | mount API (5.2+) | documented |
| XR-208 | memfd_secret (5.14) | documented |
| XR-209 | cachestat (6.5) | documented |
| XR-210 | fchmodat2 (6.6) | documented |

---

### XR-201 -- io_uring (5.1/5.5+) -> liburing, no glibc wrapper -> kernel config + caps

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| io_uring (`SC-io_uring_setup` 425, `SC-io_uring_enter` 426, `SC-io_uring_register` 427 -- numbers uniform across x64/i386/g64/arm) | trio since **5.1** (ledger + man pages); the row's headline "5.1/5.5+" marks the early maturation window -- the io_uring man pages carry no VERSIONS sections, so 5.1 rests on the ledger/hub | **none**: no wrapper and no symbols across glibc releases (NEWS has zero io_uring hits; `nm -D` on glibc 2.41 finds none); userspace goes through **liburing** or raw `syscall()` | musl 1.2.5: raw `syscall()` only (no wrapper) | `CONFIG_IO_URING` (present in the v5.1 Kconfig); sysctls `io_uring_disabled`/`io_uring_group` exist **since 6.6** (tag-verified absent at v6.5) |

The three-call protocol is the interface: `io_uring_setup` creates a ring, the
SQ/CQ rings are **mmap**ed (not read through syscalls), and `io_uring_enter`
submits/completes. The setup flags (`IORING_SETUP_IOPOLL`, `SQPOLL`,
`SQ_AFF`, `CQSIZE`, `CLAMP`, `ATTACH_WQ`, `R_DISABLED`, ... -- a
`1U<<0..1U<<16` block in `linux/io_uring.h`) and the 66 `IORING_OP_*`
enumerators are the real feature surface: "io_uring supports X" almost always
means "this kernel added an op or flag", which is why the row tracks versions
per-feature rather than one number. Registered buffers and files are pinned
and bounded by `RLIMIT_MEMLOCK` (`SC-io_uring_register` semantics). Because
libc never grew a wrapper, availability is decided
entirely by kernel config + liburing on the userspace side. Pages:
[io_uring_setup](../syscalls/net-ipc/io_uring_setup.md); kernel side:
[io_uring async API](../kernel/apis/io-uring-async.md),
[io_uring internals](../kernel/apis/io-uring-internals.md),
[block io_uring](../kernel/block/io-uring-block.md).

### XR-202 -- pidfd API (5.3+) -> glibc 2.30+ era wrappers -> kernel config

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| pidfd API: `SC-pidfd_send_signal` (424), `SC-pidfd_open` (434), `SC-pidfd_getfd` (438); `CLONE_PIDFD` on `SC-clone`/`SC-clone3` | **staged**: `CLONE_PIDFD` 5.1 (tag check v5.1), pidfd_send_signal 5.1, pidfd_open 5.3, pidfd_getfd 5.6; clone3 gained the pidfd field 5.3, `set_tid` 5.5, `CLONE_INTO_CGROUP` 5.7 | **2.36** for the pidfd trio (`pidfd_open`/`pidfd_getfd`/`pidfd_send_signal` `@@GLIBC_2.36`: NEWS + Versions + nm), `pidfd_getpid` 2.39; `gettid` itself 2.30; the ledger headline "glibc 2.30+" covers that era | musl 1.2.5: raw `syscall()` (no pidfd wrappers) | pidfd_getfd requires the usual **ptrace-style permission** against the target; `CLONE_INTO_CGROUP` needs a **cgroup v2 fd**; seccomp profiles that filter by syscall number must pass the new slots |

pidfds make PID races disappear by making the kernel hand you an fd instead of
a reusable number. The practical availability story is two-sided: kernel
staging (5.1..5.7) and the glibc wrapper landing at 2.36 (cached 2021 man pages
still say "no wrapper" -- stale, both sources named on the per-call pages).
Flag-level notes from the header checks: `PIDFD_NONBLOCK` is `O_NONBLOCK`, and
`PIDFD_THREAD` (`O_EXCL`) exists in the installed `linux/pidfd.h` but predates
documentation in the cached man pages -- flagged, not asserted. `waitid`
learned the `P_PIDFD` idtype so the wait family consumes pidfds directly.
Pages: [pidfd_open](../syscalls/process/pidfd_open.md),
[pidfd_getfd](../syscalls/process/pidfd_getfd.md),
[pidfd_send_signal](../syscalls/process/pidfd_send_signal.md),
[clone](../syscalls/process/clone.md).

### XR-203 -- openat2 (5.6) / landlock (5.13) -> no glibc wrapper era -> headers and raw syscall()

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-openat2` (437 uniform) + `struct open_how`/`RESOLVE_*` flags | **5.6** | **no wrapper released** (man7 wrapper note + `nm -D` 2.41); glibc 2.43 lists it as pending (NEWS + Versions) | musl 1.2.5: `syscall(SYS_openat2, ...)` via the `SYS_openat2` macro (no function) | none beyond the kernel version itself -- the gate is that *your libc has no wrapper*, so callers use `syscall()` with the UAPI header |

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| Landlock: `SC-landlock_create_ruleset` (444), `SC-landlock_add_rule` (445), `SC-landlock_restrict_self` (446) -- numbers uniform | **5.13** (ABI v1); ABI v2 5.19, v3 6.2, v4 6.7 | **none** (no landlock symbols on glibc 2.41) | musl 1.2.5: `syscall()` (numbers 444-446 present) | `CONFIG_SECURITY_LANDLOCK` (Kconfig at v5.13); the `lsm=` boot list must include landlock (landlock.7); `SC-landlock_restrict_self` needs `no_new_privs` set or `CAP_SYS_ADMIN` |

These two are the faces of the "no-wrapper era": kernel features that shipped
years before any libc blessed them, so correct use means the UAPI headers
(`linux/openat2.h`, `linux/landlock.h`) plus raw `syscall()`. For openat2 the
extension discipline is the same copy_struct_from_user pattern as clone3: the
kernel pins `OPEN_HOW_SIZE` with build-time checks, and the `RESOLVE_*` flag
block (`0x01..0x20`: NO_XDEV, NO_MAGICLINKS, NO_SYMLINKS, BENEATH, IN_ROOT,
SYMLINK_NOFOLLOW) is what makes path traversal auditable. A master-only
`OPENAT2_REGULAR` flag exists in the UAPI header but not in the 2021 man page
-- flagged on the openat2 page. For landlock, the three-call fd protocol
(create ruleset, add rules, restrict self) is deliberately libc-free. Flag
honesty: some Landlock `RESTRICT_SELF_*` constants are not yet in the installed
`linux/landlock.h` on the reference host. Pages:
[openat2](../syscalls/descriptors-io/openat2.md),
[landlock_create_ruleset](../syscalls/sched-misc/landlock_create_ruleset.md),
[seccomp](../syscalls/sched-misc/seccomp.md); kernel side:
[seccomp](../kernel/security/seccomp.md).

### XR-204 -- clone3 (5.3+) -> glibc 2.34+ posix_spawn routing -> fallback story

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-clone3` (435 uniform) + `struct clone_args` with explicit size | **5.3**; staged extras: `set_tid`/`set_tid_size` 5.5, `cgroup` field (`CLONE_INTO_CGROUP`) 5.7 | **no public wrapper ever** (man page, Versions, `nm -D` agree); **internal use since glibc 2.34**: the spawn machinery routes through clone3 with an **ENOSYS fallback** to `clone` (commit d8ea0d01 per the process-chapter research) | musl 1.2.5: raw `syscall()` | size discipline: `size < 64` -> `EINVAL`, `> PAGE_SIZE` -> `E2BIG`, zero-fill trailing bytes required (`copy_struct_from_user`); seccomp profiles that reject unknown slots shape the fallback story |

clone3 is the extensible clone: the old flat flag word becomes a versioned
struct whose size is part of the ABI, so future fields do not need a new
syscall. The size discipline is pinned by three struct-version constants
(`CLONE_ARGS_SIZE_VER0/1/2` = 64/80/88), the kernel rejects `CSIGNAL`-style
legacy bits in `clone3_args_valid`, and unknown trailing bytes must be zero --
the extension contract XR-203's openat2 shares. Its glibc story is the mirror
image of pidfd's: never a public
wrapper, but quietly load-bearing since 2.34 -- when `posix_spawn` can use
clone3 it does, and when the host kernel (or a seccomp profile) says no, glibc
falls back to the legacy clone path. That makes clone3 the rare feature whose
libc "support" is invisible from headers and visible only in behavior. Pages:
[clone](../syscalls/process/clone.md) (covers clone3),
[posix_spawn](../libc/glibc/process/posix-spawn-and-posix-spawnp.md).

### XR-205 -- time64 (5.1, 32-bit) -> glibc 2.30/2.32/2.34 stages -> runtime fallback

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| the `_time64` syscall twins (clock_, timerfd_, signal-time families; 20 slots per the 32-bit table probe) | **5.1**: the v5.0 -> v5.1 `syscall_32.tbl` diff introduces the time64 rows (tag-diff verified); `syscalls(2)` omits them -- gap recorded in the ledger | staged: **2.30** dispatches time64 wrappers first with a fallback and documents the seccomp caveat (NEWS); **2.34** makes `_TIME_BITS=64` fully supported with **kernel >= 5.1** required (NEWS verbatim); the ledger's "2.32" stage is not further detailed in the sources consulted | musl **1.2.0** switched `time_t` to 64-bit on **all** architectures (WHATSNEW; `alltypes.h.in` `TYPEDEF _Int64 time_t`) -- no twin dispatch needed | the NEWS-documented **seccomp hazard**: filters that reject unknown 32-bit slots can break the fallback chain on old kernels |

time64 is the y2038 fix for 32-bit architectures: new syscall slots whose
structs carry 64-bit time fields. The signal-time chapter tables ten such
twins (`rt_sigtimedwait_time64`, `clock_gettime_time64` and friends) alongside
the timerfd and futex twins; the syscall ledger tracks each slot separately
because the numbers only exist on the 32-bit tables (i386/arm, no g64
entries). The glibc stages matter because a 32-bit
rootfs built before 2.34 silently runs 32-bit `time_t`; musl sidestepped the
whole matrix by making `time_t` 64-bit everywhere in 1.2.0. Pages:
[clock_gettime/clock_getres](../syscalls/signals-time/clock_getres.md),
[clock_nanosleep](../syscalls/signals-time/clock_nanosleep.md); libc side:
[time, time_t and 2038](../libc/glibc/net/time-time_t-2038.md).

### XR-206 -- statx (4.11) -> glibc statx wrapper 2.28 -> header gates

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-statx` (x64 332 / i386 383 / g64 291 / arm 397) + `STATX_*`/`STATX_ATTR_*` mask protocol | **4.11** | **wrapper since 2.28** (`statx@@GLIBC_2.28`, nm-verified on the reference glibc 2.41) | not verified in the sources consulted for this matrix | fields are filesystem-dependent: `STATX_WRITE_ATOMIC` fields exist since man-pages 6.19 with block devices 6.11 and xfs+ext4 files 6.13; `stx_atomic_write_unit_max_opt` is in the 6.19 man page but **not** in the installed `linux/stat.h` |

statx is the matrix's counter-example to the no-wrapper era: a modern stat
interface that did get a glibc wrapper quickly (2.28 vs kernel 4.11), with the
usual header-gate caveat that newer `STATX_*` bits lag the installed libc
headers (`STATX_*` masks run `0x1..0x10000` in `linux/stat.h`, with
`STATX_ATTR_WRITE_ATOMIC` = 0x00400000 header-sourced). Availability of a
*field* is therefore a three-way gate: kernel, libc
header, filesystem. Pages: [statx](../syscalls/descriptors-io/statx.md),
[stat family](../syscalls/descriptors-io/stat.md).

### XR-207 -- mount API (5.2+) fsopen/fsmount/move_mount -> glibc 2.36 wrappers -> libmount

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-fsopen` (430), `SC-fsconfig` (431), `SC-fsmount` (432), `SC-fspick` (433), `SC-move_mount` (429), `SC-open_tree` (428) -- all 5.2; `SC-mount_setattr` (442) **5.12** | **5.2** suite (+ mount_setattr 5.12) | **2.36 added all seven wrappers** (NEWS "Version 2.36": fsopen, fsmount, move_mount, fsconfig, fspick, open_tree AND mount_setattr; `@@GLIBC_2.36` nm-verified; declared in `sys/mount.h`). Recorded disagreement: the cached 2021 `mount_setattr.2` still says glibc provides no wrapper -- stale; both sources named on the page | musl 1.2.5: `syscall()`; `__NR_*` macros for the family exist since musl **1.1.24** (WHATSNEW) | **`CAP_SYS_ADMIN`** for the whole family; `MOUNT_ATTR_IDMAP` additionally needs a `userns_fd`; `OPEN_TREE_NAMESPACE`/`FSMOUNT_NAMESPACE` are master-only UAPI additions (absent through v6.18 -- version pin unverified) |

The fd-based mount API replaces the flag-soup `mount(2)` path with an
object-per-step protocol: open a filesystem context, configure it, create an
attachable mount fd, move it into the tree. The UAPI surface (`FSOPEN_*`,
`FSCONFIG_*`, `FSMOUNT_*`, `MOVE_MOUNT_*`, `FSPICK_*`, `OPEN_TREE_*`,
`MOUNT_ATTR_*` plus `struct mount_attr`) is header-verified, and the
`mount_setattr` wrapper is where the two sources disagree -- the fetched 2021
man page predates the 2.36 wrapper, so the page carries both attributions.
The ledger row's "no glibc
wrapper -> libmount" headline predates glibc 2.36; the current facts (2.36
wrappers) are carried above, and libmount remains the canonical *consumer* of
the API. Pages: [fsopen](../syscalls/fs-mounts-namespace/fsopen.md),
[fsconfig](../syscalls/fs-mounts-namespace/fsconfig.md),
[fsmount](../syscalls/fs-mounts-namespace/fsmount.md),
[move_mount](../syscalls/fs-mounts-namespace/move_mount.md),
[open_tree](../syscalls/fs-mounts-namespace/open_tree.md),
[fspick](../syscalls/fs-mounts-namespace/fspick.md),
[mount_setattr](../syscalls/fs-mounts-namespace/mount_setattr.md); kernel side:
[mount API](../kernel/filesystems/mount-api.md).

### XR-208 -- memfd_secret (5.14) -> no glibc wrapper -> SECRETMEM config

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-memfd_secret` (x64 447, i386 447; no g64 slot, no arm slot) | **5.14** (x86-first: the arm32 table carries only a reservation comment; no asm-generic slot) | **none** (`nm -D` on glibc 2.41 finds no `memfd_secret` symbol; no declaration anywhere under `/usr/include` except the `SYS_memfd_secret` macro in `bits/syscall.h`, guarded by `#ifdef __NR_memfd_secret`) | musl 1.2.5: `syscall()` path noted for x86_64 | `CONFIG_SECRETMEM` (Kconfig: default y behind EXPERT, depends on `ARCH_HAS_SET_DIRECT_MAP`); **`secretmem.enable` boot/module parameter** -- off by default at v5.14, flipped to on at **v6.5** (tag bisect v6.4 off / v6.5 on; kernel-source-sourced, still no doc file states it -- flagged, not asserted); `ENOSYS` when the gate is closed |

`memfd_secret` carves memory out of the kernel's direct map so it is not
reachable by the kernel's linear mapping; creation returns an fd whose pages
are `__GFP_ZERO`-allocated and accounted against `RLIMIT_MEMLOCK`, and the
descriptor is deliberately excluded from fork/exec sharing per the man page.
The row upgraded to **documented** when the syscall encyclopedia grew the
full [memfd_secret](../syscalls/memory/memfd_secret.md) page (man page in the
cached tree plus `mm/secretmem.c`/`mm/Kconfig`), and the header sweep pinned
the libc columns: there is no `memfd_secret` declaration anywhere in the
installed headers -- `/usr/include/x86_64-linux-gnu/sys/random.h` declares
only `getrandom`/`getentropy`, and the existing
`/usr/include/linux/memfd.h` (linux-libc-dev) carries only the `MFD_*` flags
of `memfd_create` -- so the sole userspace surface is the `SYS_memfd_secret`
macro (`bits/syscall.h`, `#ifdef __NR_memfd_secret`) and raw `syscall()`.
The one flagged sub-claim is the v6.4/v6.5 `secretmem.enable` default flip,
which rests on the tag bisect (kernel-source-sourced, no doc file). Sibling:
[memfd_create](../syscalls/memory/memfd_create.md); kernel side:
[memfd](../kernel/memory/memfd.md).

### XR-209 -- cachestat (6.5) -> no glibc wrapper -> structs in linux/mman.h, raw syscall()

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-cachestat` (451 uniform across x64/i386/g64/arm) | **6.5** -- tag-probe verified (absent at v6.4, present at v6.5); `cachestat.2` HISTORY says 6.5. **Correction**: the ledger note historically read 6.1; 6.5 is the verified value and this page carries it | **none** (no wrapper; NEWS has no cachestat item; `nm -D` on glibc 2.41 finds no symbol; the `SYS_cachestat` macro sits in `bits/syscall.h` under `#ifdef __NR_cachestat`) | musl 1.2.5: the `SYS_cachestat` **macro only** -- no function | no `CONFIG_CACHESTAT_SYSCALL` prerequisite at the tool level; one kernel-source fact not yet in the 6.19 man page: `EPERM` can come from the kernel's cachestat permission check |

cachestat answers "which pages of this file are in the page cache" -- a query
page-cache operators previously approximated with mincore tricks. The row
upgraded to **documented** when the syscall encyclopedia grew the full
[cachestat](../syscalls/memory/cachestat.md) page and the header sweep pinned
the struct story: there is no `/usr/include/linux/cachestat.h` on the
reference host, but the structs are shipped anyway -- linux-libc-dev's
`/usr/include/linux/mman.h` defines `struct cachestat_range` (the `off`/`len`
pair) and `struct cachestat` (the five `__u64` counters), matching the UAPI
-- so the real use pattern is `#include <linux/mman.h>` plus
`syscall(SYS_cachestat, ...)` with the `SYS_cachestat` macro from
`bits/syscall.h`. (The sibling syscall page's "declare the structs locally"
note reflects a glibc-header check; the kernel UAPI header does ship them on
this host -- both attributions stand.) The `EPERM` gate stays
kernel-source-sourced per the linked page. Sibling:
[mincore](../syscalls/memory/mincore.md); kernel side:
[page cache](../kernel/memory/page-cache.md);
[performance view of cachestat](../performance/cachestat.md).

### XR-210 -- fchmodat2 (6.6) -> glibc 2.40 fchmodat routing -> runtime prereq

| feature | kernel version | glibc support | musl support | runtime prerequisites |
|---|---|---|---|---|
| `SC-fchmodat2` (452 uniform) | **6.6** -- present in `include/uapi/asm-generic/unistd.h` at v6.6, absent at v6.5 (tag probe); the syscall ledger's Since column still reads "--" and its row is source-limited (no man page in the cached tree; a fetched copy exists in the research cache) | **no exported `fchmodat2` symbol** on glibc 2.41 (`nm -D`); `SYS_fchmodat2` **is** in the installed `bits/syscall.h`; the "glibc >= 2.40 routes `fchmodat` through `fchmodat2` when flags require" claim is version-note sourced but **not observable** on the 2.41 reference host -- kept flagged, not asserted | not verified in the sources consulted for this matrix | none beyond the kernel version; the glibc routing question is the row's open verification item |

fchmodat2 is the newest row in the matrix and also the least settled at the
libc layer: the kernel-side story is tag-probe solid (6.6, slot 452 on every
tabulated arch), while the
glibc-side routing claim (2.40) cannot be confirmed on the 2.41 reference
host because there is no exported symbol to observe and no cached NEWS
section naming it. That is exactly the kind of claim this encyclopedia marks
uncertain instead of smoothing over. The syscall ledger keeps
`SC-fchmodat2` itself source-limited for the same reason (no man page in the
cached tree), so the row and the ledger agree on where the boundary of
verified knowledge sits. Page:
[chmod (covers fchmodat2 notes)](../syscalls/fs-mounts-namespace/chmod.md).

---

## Status summary

| Rows | Status | Note |
|---|---|---|
| XR-201 .. XR-210 | documented (10) | versions tag-probe or NEWS/nm double-sourced; open sub-claims flagged in place (XR-208's boot-param default flip remains tag-bisect sourced; XR-209's `EPERM` gate kernel-source sourced) |

## Interview Questions

1. **Why can't you `#include <linux/io_uring.h>` and call io_uring from plain
   libc code?** You can -- but only via raw `syscall()`: glibc never grew
   wrappers (XR-201), so liburing exists precisely to own the ring mmap and
   submission plumbing.
2. **Your seccomp profile rejects unknown syscalls. Which matrix rows break?**
   The fallback-dependent ones: glibc's clone3-internal posix_spawn (XR-204)
   and the time64 fallback chain on 32-bit (XR-205) both assume a conventional
   ENOSYS-style rejection.
3. **Which row changed version during this encyclopedia's research, and why?**
   XR-209: cachestat was noted as 6.1 in the ledger, but the v6.4/v6.5 tag
   probe and `cachestat.2` HISTORY fix it at 6.5 (correction recorded above).

## Cross-References

- [Method and coverage](../interface-encyclopedia.md) -- status vocabulary.
- [Cross-layer maps overview](./overview.md) and [coverage ledger](./ledger.md).
- [Syscall ledger](../syscalls/ledger.md) -- `SC-` IDs and per-arch numbers.
- [libc -> syscall -> kernel](./libc-syscall-kernel.md) and
  [sysfs -> driver model -> tools](./sysfs-driver-tools.md) -- sibling maps.
- [cgroups v2](../containers/cgroups-v2.md) -- cgroup fd prerequisite context for XR-202.
