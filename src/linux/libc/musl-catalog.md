# musl catalog -- the glibc 2.41 vs musl 1.2.5 deltas that matter

## Overview

This page discusses the important deltas between the musl 1.2.5 exported
surface and the glibc 2.41 set -- the two inventories maintained in
[ledger-musl.md](./ledger-musl.md) (1,482 functions across 110 header
families, parsed from musl's public headers) and
[ledger-glibc.md](./ledger-glibc.md) (1,881 documented-API rows, 3,470
exported symbols, 1,953 triage rows). The set-level deltas computed by the
musl ledger are the starting points -- musl-only: 15 names; glibc-only:
2,367+ names -- but raw counts mislead: most of the glibc-only mass is
internal aliasing and GNU extensions, and a few of the musl-only names are
reserved-namespace spellings that glibc ships under `__`-prefixed aliases.
This catalog names the families that matter in practice and why.

## Reading the deltas correctly

A name present in both libraries can still behave differently, and a
glibc-only name often has a musl equivalent under another name or in a
non-libc library. Three rules keep citations honest:

1. **Headers, not symbols, define musl's surface.** musl does not maintain
   a documented-API list or symbol versioning: every prototype in its
   public headers is exported from `libc.so` (ledger-musl.md, Overview).
   glibc's set is bigger than its API on purpose -- the ABI includes
   versioned compat symbols and `__`-prefixed internals that are not API.
2. **A missing name is a starting point, not a verdict.** Before citing a
   function as "missing in musl", check for a differently-spelled
   equivalent (`__membarrier`-style aliases, BSD names, or the underlying
   syscall wrapper the application can inline) -- the same discipline the
   ledgers apply to their own delta lists.
3. **Namespace policy differs.** glibc historically exposed many POSIX
   functions both unprefixed and as `__` internal spellings; musl exposes
   the standard name and keeps internals in `__` land only. That is why
   some musl-header names (e.g. `posix_close`, `getdents`) do not match
   glibc's exported set at all.

## The musl-only names (15)

| Name | What it is | glibc story |
|---|---|---|
| `ElfW` | macro from link.h-era ELF accessor style | glibc provides the same macro machinery under `<link.h>`/`<elf.h>` spellings but not exported as this symbol |
| `_flush_cache` | cacheflush-adjacent alias | glibc exposes `cacheflush` only on the arches that define it (see the syscall encyclopedia's [cacheflush](../syscalls/sched-misc/cacheflush.md)) |
| `at_quick_exit` | C11 quick-exit registration | glibc has it; the ledger's glibc set (manual-documented + exported) excluded it by the snapshot's policy row -- a reconciliation item, not a real gap |
| `cachectl`, `cacheflush` | `<sys/cachectl.h>` primitives | glibc wraps `cacheflush` on MIPS/ARC/CSKY/NIOS2 only (man-pages VERSIONS), so the x86_64 host set shows neither |
| `fgetln` | BSD stream-line reader | glibc-only world uses getline(3); musl ships the BSD name for portability |
| `getdents` | raw readdir syscall wrapper | glibc keeps the syscall behind readdir(3)/[getdents64](../syscalls/descriptors-io/getdents64.md) and never exported the raw name |
| `issetugid` | BSD trusted-path query | glibc has no equivalent (use getauxval(AT_SECURE)) |
| `membarrier` | direct wrapper of [membarrier(2)](../syscalls/memory/membarrier.md) | glibc does not wrap it; call syscall(2) |
| `posix_close` | POSIX-2008 spelling | glibc treats close() as the only spelling; the reserved-namespace form is internal |
| `res_init` | resolver re-init | glibc declared it obsolete (it survives as a compat symbol) |
| `tcgetwinsize`, `tcsetwinsize` | terminal window-size ioctls as functions | glibc leaves these to TIOCGWINSZ/TIOCSWINSZ [ioctl](../syscalls/descriptors-io/ioctl.md) users |
| `unsigned`, `void` | parser artifacts of the header scan, not functions | -- carry no meaning; listed for transparency |

Two lessons worth taking away: first, several "musl-only" rows are
**policy artifacts** of the glibc set (reserved spellings, non-exported
macros), which the musl ledger itself warns about; second, the genuinely
musl-added conveniences (`fgetln`, `issetugid`, `tcgetwinsize`) are all BSD
names -- musl's compatibility strategy leans BSD-ward, glibc's leans
GNU/XSI-ward.

## The glibc-only mass (2,367+), by family

The musl ledger reproduces the full sorted list so coverage claims can be
checked mechanically; these are the families that matter in practice
(ledger-musl.md, "In the glibc 2.41 set, not in musl 1.2.5 headers"):

- **GNU extensions.** The largest everyday-impact family: `strdupa` and
  the `*a` alloca-copy family, `qsort_r`, `secure_getenv`, `asprintf`,
  `fmemopen`/`open_memstream` (POSIX 2008 later adopted some), `error()`
  and `err`/`warn` families, `ftw`-adjacent helpers, `*at` conveniences
  beyond POSIX, `argp_*`, `obstack_*`. Portable code must gate these on
  `_GNU_SOURCE` and musl builds fail at compile time -- which is the right
  failure mode.
- **stdio internals and helpers.** The `_IO_*` family (`_IO_file_init`,
  `_IO_file_jumps`, `_IO_getc`, `_IO_flush_all`, ...) is glibc's libio
  implementation surface: exported for old binaries, never API, and the
  classic example of why symbol presence is not API presence.
- **Error-reporting and XSI leftovers.** XSI-era names (`ttyslot`,
  `gethostid`, legacy `*64` file-position variants) and error/printing
  helpers glibc accumulated -- musl omits them by design.
- **Symbol-versioned compat names.** Every `@@GLIBC_2.2.5`-style dup that
  exists only to keep 1997-2020 binaries running: 16/32-bit credential
  wrappers' era markers, the removed-syscall shims ([sysctl](../syscalls/sched-misc/sysctl.md),
  [nfsservctl](../syscalls/sched-misc/nfsservctl.md), [ustat](../syscalls/sched-misc/ustat.md)
  -- each still exported while documented as removed), and the
  `_r`-suffixed reentrant forms.
- **Wide/locale machinery.** glibc's `*_l` locale-argument family is
  bigger than musl's; musl implements the C/POSIX locale spellings and a
  small `_l` subset, so heavy locale code is a real porting cost.

## Semantic differences that bite

The set deltas understate the practical gap. These behaviors differ while
the names match:

- **Symbol versioning and ABI promises.** glibc guarantees the versioned
  ABI; musl re-uses one unversioned ABI and explicitly does not promise
  compat shims (ledger-musl.md, Overview). Static-linking-heavy
  deployments prefer musl precisely for this.
- **NSS and dynamic loading.** glibc's dlopen-based NSS means getpwnam()
  can load modules at runtime; musl's is built in -- behaviors around
  LDAP/AD users differ with identical source code.
- **Resolver behavior.** musl's resolver is a fresh implementation with
  different (simpler, RFC-conformant) search-domain and parallel-query
  behavior; `res_init`-style reconfiguration does not exist, matching the
  musl-only row above.
- **Math/error rounding details.** Both aim for correct rounding, but
  error-value sets and some `errno` choices differ (e.g. glibc's extra
  EOVERFLOW paths); the glibc function pages in this encyclopedia record
  the glibc contract, so treat them as one data point, not the truth for
  both libraries.

## Cross-references

- [libc API Encyclopedia](./overview.md) -- the two-ledger structure this
  page summarizes.
- [ledger-musl.md](./ledger-musl.md) -- the musl 1.2.5 inventory and the
  full machine-checked delta lists this page discusses.
- [ledger-glibc.md](./ledger-glibc.md) -- the glibc 2.41 inventory.
- [getdtablesize](../syscalls/sched-misc/getdtablesize.md),
  [getpagesize](../syscalls/sched-misc/getpagesize.md) -- syscall-encyclopedia
  pages that note libc wrapper behavior across the two libraries.

## References

- In-repo inventories: ledger-musl.md (musl 1.2.5 headers, 1,482 functions)
  and ledger-glibc.md (glibc 2.41, 1,881 documented rows / 3,470 exported
  symbols), including their "Set deltas vs glibc 2.41" sections.
- man-pages 6.19 pages for the wrapper-availability facts cited above
  (cacheflush VERSIONS, unimplemented.2 NOTES), fetched 2026-10-17.
