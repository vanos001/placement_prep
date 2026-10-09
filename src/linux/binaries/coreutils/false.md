# false — do nothing, unsuccessfully

## Overview

`false` does nothing at all and exits with status 1. It writes nothing to
stdout or stderr, reads nothing, and — per POSIX — ignores *all* its
arguments, including `--help` and `--version` (GNU complies: both binaries
are silent no-ops). Together with its twin `true`, it
supplies the two constant exit statuses that shell logic is built from:
success (0) and failure (1).

Debian ships it in `coreutils` at `/usr/bin/false`. Its most famous
production role is administrative: in `/etc/passwd`, system accounts that
must never log in get `/usr/bin/false` as their login shell, so even a
stolen password yields no shell. Its most famous scripting role is
placeholder and polarity-flip: stub out a command that "must fail for
now", terminate `while false` loops (rare — the opposite `while true`
idiom is common), force failure in `A || false` guards, and negate without
inverting logic by hand.

The interview-grade knowledge here is small but exact: exit status
contract, argument-ignoring semantics (deliberate, not a bug), the
difference from the `:` builtin, and why `/bin/false` as a login shell is
a policy choice with better modern alternatives (`/usr/sbin/nologin`).

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/false` on modern Debian/Ubuntu |
| First appeared / lineage | 1st/2nd Edition UNIX era; present in every Unix |
| Standards | POSIX.1-2018 (`false`) |

## Synopsis

```
false [ignored command line arguments]
```

```bash
false            # exit 1
false --help     # still exit 1, prints nothing
false -anything  # still exit 1
while false; do echo never; done   # loop body never runs
```

## How It Works

The entire program is: `exit(1)`. There is no parsing stage, no I/O, no
signal handling of note. POSIX pins the contract: `false` shall exit with a
nonzero status (1 in practice) and shall not write anything, and any
arguments — options included — are ignored. This is why
`false --version` prints no version banner: honoring `--help`/`--version`
would make the command observable, breaking the "constant failure" contract
that scripts depend on.

### Where the exit status matters

```
   ┌──────────────── shell truth model ────────────────┐
   │  exit 0  = success   (true, : , test "0")         │
   │  exit ≠0 = failure   (false, grep miss, cmd errs) │
   │                                                   │
   │  if false;   → else branch                        │
   │  false && x → x skipped                           │
   │  false || x → x runs                              │
   │  while false → body never runs                    │
   │  set -e; false → script aborts                    │
   └───────────────────────────────────────────────────┘
```

### false as a login shell

In `/etc/passwd`, the final field is the login shell. Accounts like
`daemon`, `mail`, and service users historically get `/usr/bin/false`
(sometimes `/bin/false`) so that password authentication — even if it
succeeds — immediately terminates the session:

```
daemon:x:1:1:daemon:/usr/sbin:/usr/bin/false
```

The shell field is honored by `login`, `sshd`, and friends: sshd checks the
account's shell against `/etc/shells` and denies the session when the shell
is absent from it, giving two independent layers. Modern Debian prefers
`/usr/sbin/nologin` for these accounts because it prints a diagnostic
("This account is currently not available.") before exiting, which is
friendlier than false's silence — same denial, better UX. `false` remains
the minimal, dependency-free choice in minimal containers.

### The `:` builtin comparison

| Aspect | `false` | `:` (colon builtin) |
| --- | --- | --- |
| Exit status | 1 | 0 |
| Process | external binary (unless aliased) | shell builtin, no fork |
| Args | ignored by contract | expanded but ignored |
| Speed in a hot loop | fork + exec per call | free |
| Use | real failure semantics | success placeholder, `: ${VAR:=default}` tricks |

Scripts that need a *failing* no-op in a loop pay a fork per iteration for
`false`; that is usually a signal the loop structure is wrong.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(any arguments)* | Ignored entirely, per POSIX — including `--help` and `--version` |

This is the whole table. Note the deliberate difference from nearly every
other coreutils tool: `false --help` is not a help command.

## Usage Patterns

```bash
# Guard clause: make an optional step's failure non-fatal, explicitly
optional_check || false   # documented always-fail marker in a pipeline
```

```bash
# Stub out a not-yet-implemented command so the caller sees failure
deploy_canary() { false; }   # TODO: implement
```

```bash
# Force a `set -e` script to stop right here
some_setup && false   # deliberate abort marker during bring-up
```

```bash
# Ensure a function returns failure without printing anything
is_root() { [ "$(id -u)" = 0 ] || false; }
```

```bash
# Testing failure paths of a wrapper script
PATH=/usr/bin:/bin my_wrapper should_fail && echo "wrapper bug: expected failure"
```

```bash
# Placeholder body for a disabled cron job (keeps cron mail quiet, exits clean-ish)
0 2 * * * /usr/bin/false   # disabled 2026-08-01, keep line for audit
```

```bash
# shellcheck-silenced unconditional failure for branch coverage tests
if false; then echo unreachable; else echo taken; fi
```

```bash
# Login-shell denial (see /etc/passwd)
usermod -s /usr/bin/false backupbot
```

## Nuances and Gotchas

- **Arguments are ignored by specification.** `false --help` giving no
  help is correct behavior; wrapping tools that inspect exit codes should
  not "fix" this. `true` behaves symmetrically (silent success).
- **`false` in a pipeline:** the pipeline's status is false's *unless* the
  last element changes it — `false | echo hi` succeeds (echo is last).
  `set -o pipefail` exposes the embedded failure.
- **`set -e` interaction:** a bare `false` aborts the script; `false || true`
  is the canonical "continue anyway" idiom, and `! false` is a success.
  Being fluent in these three is shell-literacy.
- **Exit status is exactly 1, not random:** POSIX-specified nonzero, GNU
  uses 1; scripts distinguishing 1 from 2/3 of real commands must not use
  false to *simulate* those specific failures.
- **nologin vs false:** `false` is silent; `nologin` explains. In
  diagnostics-hungry environments, silent denial generates
  "connection closed" mystery tickets.
- **`! false` double negation** is a success, but `set -e` + `!` has
  subtle rules (the `!` prefix exempts the command from errexit handling).
- **Portability:** `false` is POSIX and universal — one of the few commands
  with zero portability concerns, including busybox.
- **Not a test replacement:** `false` cannot evaluate anything; scripts
  using `false` where `test`/`[ ]` is meant have a logic bug that always
  fails.

## Exit Status

| Status | Meaning |
| --- | --- |
| 1 | Always. Unconditionally. Regardless of arguments or environment. |

(POSIX requires nonzero; every implementation in living memory uses 1.)

## Related Commands

- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- `true` — the mirror twin: silent success, same argument-ignoring contract (no separate page in this batch)
- [`expr`](./expr.md) — a *real* command whose exit status also encodes falseness (value 0/null) — the contrast between designed and incidental failure semantics
- [`echo`](./echo.md) — the other "trivial" coreutils tool whose builtin-vs-binary duality matters

## Interview Questions

### Q: Why does `false --version` print nothing, and is that a bug or a feature?

A feature, and a POSIX requirement: `false` must be a constant-failure
command that writes nothing and ignores all operands, because scripts use
it as an unconditional failure value — a `--version` banner would make its
output observable and its exit status effectively conditional. GNU honors
this (`false --help` prints nothing, exits 1), and `true` is the symmetric
silent success. Interviewers use it to check whether you know the contract
or just pattern-match other coreutils tools.

### Q: Explain the differences between `false`, `: `, and `true` in a shell script, including performance.

`false` exits 1; `:` exits 0; `true` exits 0. `:` and `true` as *builtins*
cost no fork; `/usr/bin/false` (and `/usr/bin/true` when invoked by path)
cost fork+exec per call. `:` additionally participates in shell idioms
(`: ${VAR:=default}`, `:>file` truncation), while `true` is the
self-documenting spelling for infinite loops (`while true`). `false`'s
role is semantic failure — placeholders, guards, test fixtures — where
returning 1 is the payload.

### Q: How does `/usr/bin/false` as a login shell deny access, and what are its limitations versus `/usr/sbin/nologin`?

The login shell is executed after successful authentication; `false`
immediately exits 1, terminating the session with no shell. sshd adds an
independent check: shells not listed in `/etc/shells` are refused for
password/key sessions targeting restricted contexts. Limitations: silence
— users see an abrupt disconnect with no explanation — and it still allows
non-shell access paths (ftp, mail delivery, su -s) unless separately
locked. `nologin` prints "This account is currently not available."
before failing, and account-level locking (`usermod -L`, `passwd -l`) is
the stronger modern control.

### Q: In a `set -e` script, what do `false`, `false || true`, `! false`, and `false && echo x` each do?

Bare `false` aborts the script (errexit). `false || true` continues — the
compound's overall status is 0 — the canonical "I know this can fail, keep
going" idiom. `! false` yields status 0 (negation of failure) and is
exempt from errexit per POSIX, so the script continues. `false && echo x`
short-circuits: echo never runs and the *list* has status 1 — under
errexit this aborts unless it is the final command of an if/while
condition context. These four lines are the standard errexit literacy
quiz.

### Q: Name two legitimate production uses of `false` and one anti-pattern.

Legitimate: (1) login shell for service accounts in minimal
containers/images where nologin may not exist; (2) as a stub/fixture in
tests — "this code path must report failure" — including CI checks that a
wrapper propagates non-zero statuses. Anti-pattern: using `false` inside
hot loops as a "do nothing" (each call forks; use `:` or restructure), or
using `false` to simulate specific exit codes (1 only) in test suites that
later branch on 2/3 — the simulation silently diverges from the real
command's contract.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/false.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
