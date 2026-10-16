# Linux Interface Encyclopedia — Method and Coverage

This part of the book is a **reference encyclopedia** of the interfaces programs
actually touch: the Linux kernel's system calls, the libc API surface that wraps
and extends them, the sysfs class tree the kernel publishes, and the cross-layer
mappings that tie the layers together. It is built like a catalog, not like a
tutorial: every interface gets an inventory row first, and a documentation page
only after primary sources have been read.

Everything here is regenerated or written **from sources**, never from memory:

| Source | Cached at | Used for |
|---|---|---|
| torvalds/linux per-arch syscall tables | `source-cache/kernel`, `linux-sparse` | syscall numbers, `since` values, ABI flags |
| man-pages (man2 497 pages, man3 1717 pages) | `source-cache/man-pages-sparse` | per-call semantics, return values, errors |
| glibc manual (texi) + installed headers + `nm -D` | `source-cache/glibc*` | glibc API surface, symbol versions |
| musl 1.2.5 source tree + WHATSNEW | `source-cache/musl-1.2.5.tar.gz` | musl API surface and deltas |
| kernel `Documentation/ABI/**` | `source-cache/abi` | sysfs attribute contracts |
| live `/sys` enumeration (5.10.134 container) | `source-cache/live-sys` | class populations, permission bits |

## What "covered" means — the status vocabulary

Names appearing in a table **never** count as completion. Every inventory row
carries one of four statuses, and only the ledger may change it:

- `not-started` — the interface is inventoried (it exists, with a stable ID and
  a source); no documentation page exists yet.
- `researched` — primary sources were read and a brief entry exists (facts and
  references, no full template).
- `documented` — a full per-page entry exists: purpose, signature, arguments,
  return value, error conditions, side effects, blocking behavior, security
  notes, version/architecture constraints, and a primary reference.
- `source-limited` — documentation attempted but a named primary source was
  unreachable; the entry states exactly what is missing and what the claim
  rests on instead.

## Structure: one page per function

Documentation is **split per function**, not grouped into per-domain mega-chapters:

- `syscalls/<domain>/<call>.md` — one page per system call. Tight families share
  one page when the man page itself is shared: roff `.so` alias pages
  (`dup2`/`dup3` → `dup`, `openat` → `open`, 225 such aliases in the cached
  man2 tree), documented time64 twins, and the 6.7 futex2 operations, which
  their base entries document inline. Aliases never inflate page counts or
  coverage: the ledger tracks each number separately and points it at the
  family page.
- `syscalls/<domain>/overview.md` — auto-generated hub: every call of the
  domain, the calls its page covers, numbers per architecture, `since`, status.
- `libc/glibc/<family>/<function>.md` — one page per glibc function;
  `libc/ledger-glibc.md` and `libc/ledger-musl.md` track the full surface
  (1881 documented-API rows and 3470 exported symbols for glibc; 1482
  functions for musl 1.2.5). musl keeps a separate catalog because its API
  surface is mostly shared POSIX plus deltas; pages exist for families where
  behavior genuinely differs.
- `sysfs/classes/<class>.md` — one page per sysfs class, with live-vs-documented
  attribute honesty (attributes are driver-, version- and config-dependent and
  are never invented; only ABI-doc `What:` lines, subsystem `DEVICE_ATTR`
  blocks, or kernel docs qualify).
- `crossref/*.md` — the cross-layer maps (libc → syscall → kernel subsystem;
  sysfs class → driver model → tools; feature → minimum kernel → libc
  availability → runtime prerequisites). Maps stay grouped because they are
  tables of relations, not functions.

## Non-negotiable rules

1. **No invented interfaces.** If a source cannot be named for a claim, the
   claim is marked uncertain or omitted. Attributes observed only on a live
   host are stamped with the host kernel and flagged.
2. **No conflation of layers.** POSIX APIs, libc functions, Linux syscalls,
   sysfs attributes, and userspace commands are different things on different
   pages, cross-linked — never merged into one topic soup.
3. **Architecture, configuration, version honesty.** Numbers differ per arch
   (`x64 · i386 · g64 · arm` columns); availability is qualified with the
   kernel version, glibc/musl version, and config gate where known. Nothing
   here claims universal Linux support.
4. **Ledger is the source of truth** for IDs and statuses; pages link into it,
   agent status reports land in `status/<task>.status`, and a merge step
   updates the ledger — the ledger is never hand-edited per row.
5. **Modularity.** No page accumulates hundreds of entries; when a page grows
   past a family, it splits.

## Coverage snapshot

| Ledger | Rows | Statused | documented | Pages |
|---|---|---|---|---|
| [Syscalls](./syscalls/ledger.md) | 535 | 535 | 433 | 288 per-function + 7 auto hubs |
| [glibc API](./libc/ledger-glibc.md) | 1881 documented-API (+3470 exported, +1953 triage) | 1881 | 1047 | 281 function pages |
| [musl API](./libc/ledger-musl.md) | 1482 functions (110 header families) | by family | 6 family pages | 6 + catalog |
| [Sysfs classes](./sysfs/ledger.md) | 120 | 120 | 106 | 119 class pages |
| [Cross-layer maps](./crossref/ledger.md) | 38 | 38 | 37 | 3 maps |

Source-limited rows and not-started rows are **kept visible** with their gaps
named, rather than dropped to make the numbers look better.

Remaining after wave 7 (2026-10-13): syscalls 46 `researched` + 101
`source-limited`; glibc 10 `source-limited` (uabs family, getumask, mseal,
memalignment, free_sized, free_aligned_sized, pthread_gettid_np) plus 2573
`not-started` exported-symbol rows; sysfs 14 `source-limited` (thin/no-source
classes, named in-page); crossref 1 `source-limited` (XR-112 msr-tools).
