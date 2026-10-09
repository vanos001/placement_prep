# whoami — print the effective user name

## Overview

`whoami` prints the user name that owns the process's *effective* user ID —
one line, nothing else. It is exactly equivalent to `id -un`, and its entire
reason to exist is that this question predates `id` and refuses to die
because the name is memorable and the output needs no parsing.

It ships in the Debian `coreutils` package at `/usr/bin/whoami` (modern
coreutils builds it as a small frontend around the same lookup `id`
performs). It descends from BSD and is not POSIX-standardized — POSIX
considers it obsolescent in favour of `id -un`, which is the spelling
portable scripts should prefer.

The word "effective" carries all the interesting semantics: after `sudo`,
`su`, or a setuid execution, the effective identity changes while the real
identity stays, and `whoami` reports the effective one. That is the classic
contrast with `logname`, which reports the *login* name from the terminal
session's utmp record regardless of how many identity changes happened
since.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/whoami` |
| First appeared / lineage | BSD lineage; in GNU coreutils |
| Standards | none — obsolescent; POSIX answers this with `id -un` |

## Synopsis

```text
whoami [OPTION]...
```

```bash
whoami             # effective user name
id -un             # the identical, POSIX-preferred spelling
whoami && id -u    # name plus numeric effective UID
```

## How It Works

The kernel tracks two user IDs per process: the *real* UID (who started the
process) and the *effective* UID (whose permissions apply right now), plus
the saved set-user-ID used by privilege-switching code. `whoami` calls
`geteuid(2)` and resolves the number to a name via the passwd database
(`getpwuid(3)`), printing the account name:

```bash
$ whoami
z
$ id -un
z
$ sudo whoami        # effective UID changed to 0
root
$ sudo logname       # login identity did not change
z
```

That four-line sequence is the whole education: `whoami` follows
privilege, `logname` follows the session. A setuid binary, a `su otheruser`
shell, or a sudo invocation each flip `whoami`'s answer while `logname`
keeps reporting the original login.

GNU `whoami` takes no operands — an extra argument is a usage error, exit
1 — and offers only the standard `--help`/`--version`. The builtin question
"is this root?" has a cheaper spelling that avoids name resolution
entirely: compare the numeric effective UID.

```bash
$ whoami extra
whoami: extra operand 'extra'
Try 'whoami --help' for more information.
$ echo $?
1
```

## Options That Matter

| Option | Effect |
|---|---|
| `--help` / `--version` | Standard coreutils informational options |
| (no operands accepted) | Any positional argument is a usage error |

There is no option surface to speak of — not even an "output numeric ID"
variant; that job belongs to `id -u`.

## Usage Patterns

```bash
# Quick identity echo in interactive shells and logs
echo "deploy started as $(whoami) at $(date -Is)"
```

```bash
# Refuse to run as root (name-based, human-oriented)
[ "$(whoami)" = root ] && { echo "do not run me as root" >&2; exit 1; }
```

```bash
# The numeric, locale-proof spelling of the same guard
[ "$(id -u)" -eq 0 ] && { echo "do not run me as root" >&2; exit 1; }
```

```bash
# Verify a sudo wrapper actually elevated before doing damage
sudo sh -c 'whoami' | grep -qx root || echo "elevation failed" >&2
```

```bash
# Stamp artifacts with the builder identity
tar czf "build-$(whoami)-$(date +%s).tgz" dist/
```

```bash
# Audit trail line pairing effective and login identity
echo "$(logname 2>/dev/null || echo '?') became $(whoami) via $0" >> audit.log
```

```bash
# Per-user cache directory without $HOME assumptions
CACHE="/tmp/cache-$(whoami)"
```

## Nuances and Gotchas

- **Effective, not real, not login.** `sudo whoami` → `root`; `logname` →
  the original account. Scripts that meant "who is at the keyboard" and
  used `whoami` misreport under every privilege switch. Conversely, scripts
  that meant "who will this file belong to" must use `whoami`/`id -u`.
- **Prefer `id -un` in portable code.** `whoami` is not in POSIX and is
  documented as obsolescent; `id` is standardized and can also produce the
  UID (`id -u`), groups (`id -Gn`), and everything else in one process.
- **Prefer numeric checks for root.** `[ "$(id -u)" -eq 0 ]` is immune to
  NSS/name-resolution weirdness (LDAP down, passwd entry missing) where
  name comparison `[ "$(whoami)" = root ]` could fail or error out.
- **`who am i` is a different tool's syntax.** It belongs to `who` (the
  session-lister) and reports your *login* session, not your effective
  identity — the naming collision is a classic interview trap.
- **Name resolution dependency.** The UID→name lookup consults NSS; in
  minimal containers or broken LDAP environments the numeric `id -u` still
  works while `whoami` may print the raw number or fail. Diagnose identity
  problems with `id`, not `whoami`.
- **busybox whoami** exists and matches the trivial contract, so embedded
  and rescue environments are covered.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Name printed successfully |
| 1 | Usage error (operands given) or the effective UID could not be resolved to a name |

In practice status 1 almost always means "you passed arguments" — the
lookup itself failing is a sign of deeper NSS breakage that `id` will
diagnose.

## Related Commands

- [`users`](./users.md) — utmp-based login lists; the session view whoami ignores.
- [`who`](./who.md) — the owner of the `who am i` syntax people confuse with this tool.
- [`tty`](./tty.md) — another one-fact environment probe, for the terminal rather than the user.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: What exactly does whoami report, and how do sudo, su, and setuid change its answer?

The name associated with the process's *effective* UID: `geteuid(2)` plus a
passwd lookup. `sudo` and `su` replace the effective UID (root or the target
user), so `whoami` reports the new identity; a setuid binary runs with the
file owner's effective UID and `whoami` reflects that too. The real UID and
the login-session identity (what `logname` reports) stay unchanged through
all of those switches — that contrast is the point of the tool.

### Q: Why do style guides recommend `id -u` over `whoami` for root checks?

Two reasons. Numeric comparison `[ "$(id -u)" -eq 0 ]` does not depend on
NSS resolving UID 0 to the name "root" — which can fail or be renamed on
hardened or directory-backed systems — and it cannot be fooled by an
account merely *named* root with a non-zero UID. `whoami` also is not
POSIX, while `id` is, so the numeric spelling is both more correct and more
portable.

### Q: What is the difference between whoami, logname, and `who am i`?

`whoami`: effective UID resolved to a name — changes with sudo/su/setuid.
`logname`: the login name attached to the session's controlling terminal
(utmp) — stable across privilege switches, but only defined when a login
session exists (empty in cron/CI). `who am i` is `who`'s legacy two-word
form: it prints your full login session line (user, terminal, host, time)
and likewise requires a real terminal. Three answers to three different
questions: current privilege, original login, session record.

### Q: When would whoami fail with status 1 in a real environment?

Most commonly because operands were passed — GNU whoami rejects any
positional argument. Beyond that, the effective-UID-to-name resolution
depends on NSS: with a broken `/etc/nsswitch.conf`, unreachable LDAP, or a
removed passwd entry, the lookup fails even though the process runs fine,
which is why diagnostic scripts fall back to `id -u` for a numeric answer.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/whoami.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
