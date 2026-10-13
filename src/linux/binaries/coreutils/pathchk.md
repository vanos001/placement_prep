# pathchk — check pathnames for validity and portability

## Overview

`pathchk` diagnoses whether pathnames are *valid and portable* — without
touching the filesystem. Given one or more names, it checks each against
length limits (per component and total), allowed characters, and (with
`-P`) structural rules like empty components or leading dashes. It is a
lint for path strings: the tool you reach for before a script feeds a
user-supplied name to `install`, an archive builder, or a filesystem you
don't control.

It ships in the Debian `coreutils` package at `/usr/bin/pathchk`, is
POSIX-standardized, and descends from early System V lineage. Its modern
relevance is modest — Linux `PATH_MAX` (4096) and `NAME_MAX` (255) are
generous, and most tooling fails loudly on overflow anyway — but the tool
remains a fixture of interviews and of POSIX-portable packaging scripts,
where the question is "will this name survive on every conforming
system?", not just this one.

It is often confused with `test -e` (existence), `realpath`/`readlink -f`
(canonicalization), and the shell's own length checks — none of which
check *portability*.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/pathchk` |
| First appeared | PWB/System V lineage Unix |
| Standards | POSIX 2018 utility |

## Synopsis

```
pathchk [OPTION]... NAME...
```

Main forms:

```
pathchk /srv/app/data.bin     # validate against this system's limits
pathchk -p "$user_input"      # validate against most-POSIX limits
pathchk --portability name    # -p plus -P (empty names, leading dashes)
```

## How It Works

`pathchk` performs pure string-and-limit analysis. Existence is *not*
required — that surprises people who expect a "check" to stat something:

```bash
# Nothing exists here, yet the check passes: the NAME is well-formed
$ pathchk f/b/c; echo $?
0
```

What is checked depends on the mode. Default mode validates against the
*local* system and filesystem limits (on Linux: component ≤ 255 bytes,
full path ≤ 4096 bytes, per the actual underlying filesystem), reporting
kernel-style errors:

```bash
# 5000-character component on a local ext4-like filesystem
$ pathchk "$(printf 'a%.0s' $(seq 5000))"; echo $?
pathchk: aaaa...aaa: File name too long
1
```

With `-p`, the yardstick becomes the portable POSIX minimums: each
component at most **14** bytes (`_POSIX_NAME_MAX`) and the whole name at
most **255** bytes, with the diagnostic reporting the exact limit and the
offending length:

```bash
$ pathchk -p "$(printf 'a%.0s' $(seq 16))"; echo $?
pathchk: limit 14 exceeded by length 16 of file name component 'aaaaaaaaaaaaaaaa'
1
$ pathchk -p "$(printf 'a%.0s' $(seq 300))"
pathchk: limit 255 exceeded by length 300 of file name 'aaa...aaa'
```

`-P` adds two structural checks that POSIX marks as good hygiene: no
empty name, and no component starting with `-` (which would be
indistinguishable from an option for tools that don't use `--`):

```bash
$ pathchk -P ""; echo $?
pathchk: empty file name
1
$ pathchk -P -- -dashfile; echo $?
pathchk: leading '-' in a component of file name '-dashfile'
1
```

Multiple names are checked in order; `pathchk` stops at the first problem
in a name, and any failure makes the overall exit status nonzero.

## Options That Matter

| Option | Effect |
|---|---|
| `-p` | Check against limits portable to *most* POSIX systems (14-byte components, 255-byte names) instead of local filesystem limits |
| `-P` | Additionally flag empty names and components beginning with `-` |
| `--portability` | Equivalent to `-p -P` — the strictest, "any conforming system" mode |

Mode selection is the entire design: local validation (default) for
practical scripts, `-p` when the name may land on other Unix systems or
older filesystems (ISO 9660-era media, some FAT overlays, tar on odd
platforms), `--portability` when shipping source archives.

## Usage Patterns

```bash
# Validate user-supplied output filenames before creating anything
pathchk -P -- "$out" || { echo "bad output name: $out" >&2; exit 1; }
```

```bash
# Sanity-check names destined for a portable tarball
for f in $(git ls-files); do pathchk -p "$f" || echo "not portable: $f"; done
```

```bash
# Pre-check a deep path a config file will create
pathchk "$install_root/$app/logs/archive" || exit 1
```

```bash
# Distinguish "too long for here" from "too long for anywhere"
pathchk "$name" && echo "fine locally"; pathchk -p "$name" && echo "portable too"
```

```bash
# Reject option-lookalike names from untrusted input
pathchk -P -- "$1" 2>/dev/null || { echo "unsafe name" >&2; exit 2; }
```

```bash
# Batch lint of filenames extracted from a manifest
xargs -d '\n' pathchk -p < manifest.lst
```

## Nuances and Gotchas

- **It does not check existence or permissions.** `pathchk /etc/shadow/x`
  passes if the *name* is well-formed; "No such file or directory" from
  pathchk means the name string itself was malformed (e.g. empty), not
  that the file is missing.
- **Default mode is system-relative.** A name that passes on Linux (255/4096)
  can still break on a POSIX-minimum platform; only `-p`/`--portability`
  answers the cross-platform question.
- **The 14-byte component limit of `-p` is stricter than most people
  expect.** Everyday names like `configuration.yaml` (17 bytes) fail
  `-p`. That is by design — it encodes ancient-Unix minimums — but it
  makes `-p` unsuitable for linting modern trees; know which question you
  are asking.
- **Byte counts, not characters.** Limits are in bytes; a 130-character
  Cyrillic component is ~260 bytes and fails `-p` on length. Locale does
  not change the arithmetic.
- **Diagnostics are stable, codes are binary.** Any failure → exit `1`
  (POSIX also allows `>1` for errors); success → `0`. Don't parse the
  message text; branch on the status.
- **`-P` exists because of option confusion**, not filesystem limits. A
  component named `-rf` is legal almost everywhere and catastrophic
  wherever a downstream tool forgets `--`.
- **Rarely needed on modern Linux — until it is.** The real-world triggers
  are cross-platform packaging, old filesystem targets (CDFS, some SMB
  exports), and embedded toolchains where `NAME_MAX` is genuinely small.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | All names pass the selected checks |
| `1` | At least one name failed a limit/structure check |
| `>1` | Usage or operational error (per POSIX allowance; GNU uses 1 for check failures) |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./readlink.md`](./readlink.md) — canonicalize names before validating them.
- [`./link.md`](./link.md) — another syscall-shaped primitive with strict, binary failure.
- [`../../shell/posix-shell.md`](../../shell/posix-shell.md) — the portability mindset pathchk encodes.

## Interview Questions

### Q: What does `pathchk name` actually check, and what doesn't it check?

It checks the *string*: length limits per component and for the whole
path (local filesystem limits by default; POSIX portable minimums with
`-p`), with `-P` adding empty-name and leading-dash rejections. It does
not stat anything — existence, type, and permissions are irrelevant to
the result, so `pathchk f/b/c` succeeds on an empty directory.

### Q: Why does `pathchk -p` reject a 16-character filename when Linux allows 255?

`-p` switches the yardstick from *this system* to *most POSIX systems*:
the POSIX minimum guarantees are 14 bytes per name component and 255
bytes per name. A name exceeding those is fine on Linux but not portable
to every conforming system (historical filesystems, old Unix variants).
That strictness is the feature — and the reason `-p` is for packaging and
archive audits, not daily linting.

### Q: A build fails on a colleague's machine with "File name too long" but works on yours. How would pathchk have helped?

Your machine likely has longer effective limits (filesystem choice,
overlay/container differences) or the long name was generated there.
Running `pathchk -p` over the file list in CI would have flagged
components/names over the portable 14/255 minimums — and plain `pathchk`
over the target filesystem's real limits — before the name ever reached
`open()`. It converts a runtime `ENAMETOOLONG` on someone else's machine
into a deterministic pre-flight check.

### Q: What is the point of the -P leading-dash check when `--` exists?

Defense in depth. Names beginning with `-` are legal and common in
attacks on scripts that interpolate variables into command lines without
`--`. Requiring `-P`-clean names at the boundary (an upload handler, a
Makefile input) eliminates a whole class of argument-injection bugs
downstream, even in tools and shell functions that forgot to use `--`.
It encodes a policy, not a filesystem constraint.

### Q: Is pathchk still relevant on modern Linux?

Marginally but genuinely: for validating names that will travel to other
systems (tarballs, ISO images, cross-platform repos), for embedded
targets with small limits, and as an interview touchstone for
understanding `NAME_MAX`/`PATH_MAX` versus POSIX minimums. Day-to-day,
Linux's 255/4096 limits make failures rare — which is exactly why the
rare failure surfaces late and far from its cause, where a cheap static
check would have caught it.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/pathchk.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — pathchk](https://pubs.opengroup.org/onlinepubs/9699919799/)
