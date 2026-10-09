# true — return a successful exit status, do nothing

## Overview

`true` does nothing and succeeds. It accepts any arguments, performs no
operation, and always exits with status 0. That single contract makes it one
of the most load-bearing binaries on the system: the unconditional-true
value in `while true` loops, the "ignore this failure" guard in
`command || true` under `set -e`, and the placeholder body in unfinished
conditionals.

It ships in the Debian `coreutils` package. On merged-`/usr` systems
`/usr/bin/true` and `/bin/true` are the same file through the `/bin →
/usr/bin` symlink, and historically both paths existed independently because
early-boot environments (initramfs, single-user shell) run before `/usr` is
mounted. Scripts, boot hooks, and package maintainer code call `/bin/true`
by absolute path, which is why the initramfs must contain it: if boot-time
shell code invokes `/bin/true` and the file is missing, an early-boot step
fails for the most absurd possible reason.

Its twin is `false` (exit 1, identical everything else). The pair, plus the
shell no-op `:`, form the boolean constants of the Unix command set.
`true` is POSIX-standardized; its behaviour is deliberately frozen.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/true` (= `/bin/true` on merged-`/usr`) |
| First appeared / lineage | Earliest Unix (v1-era shell builtin heritage) |
| Standards | POSIX.1-2017 |

## Synopsis

```text
true [ignored command line arguments]
```

```bash
true                    # exit 0
true --anything 42      # still exit 0 — all arguments are ignored
while true; do ...; done
command_may_fail || true
```

## How It Works

There is nothing to it: `main` returns 0 immediately, before even looking at
`argv`. The GNU implementation deliberately skips option parsing —
`true --help` prints nothing and exits 0, because honouring `--help` would
mean *some* argument changes behaviour, and the standard forbids that.
`false` is the mirror image: same code path, exit 1.

```bash
$ true a b c --bogus; echo $?
0
$ true --help; echo $?      # no help text: args are ignored by design
0
```

Three roles in practice:

```text
1. control flow      while true; do poll; sleep 1; done
2. failure swallowing    set -e; flaky_check || true
3. absolute-path boot dependency   /bin/true as a no-op hook target
```

The third one is easy to underestimate. Boot scripts and maintainer scripts
are full of patterns like `[ -x /bin/true ]` sanity checks, no-op command
stubs, and `ExecStart=/bin/true`-style placeholders; initramfs generators
therefore treat `/bin/true` as required content. Because `/bin` is a symlink
to `/usr/bin` on modern Debian/Ubuntu, one file serves both worlds — but a
hand-rolled initramfs that copies `/usr/bin/true` without recreating `/bin`
will still break path-hardcoded callers.

The shell builtin is what you execute in hot loops: bash and dash resolve
`true` to a builtin, so `while true` costs no `exec`. The external binary
matters only when something execs it directly (shebang-less stubs, `exec
true` at the end of a script, or `chsh -s /bin/true`-style login shells that
permit no commands).

## Options That Matter

| Option | Effect |
|---|---|
| (any arguments) | Ignored entirely — including `--help` and `--version` |

That is the complete option surface, and it is the interview answer: `true`
is one of the rare Unix commands whose arguments are *specified* to be
ignored. (`--help` and `--version` work on `false`'s man page the same way.)

## Usage Patterns

```bash
# Infinite polling loop — the canonical `while true`
while true; do
    check_queue && break
    sleep 5
done
```

```bash
# set -e survival: run a command whose failure is expected or irrelevant
set -e
grep -q '^PermitRootLogin' /etc/ssh/sshd_config || true
```

```bash
# Placeholder body while prototyping a conditional
if [ -n "$DRY_RUN" ]; then true; else deploy; fi
```

```bash
# Exec-into-nothing at the end of a wrapper script
exec true
```

```bash
# Disable interactive login for a service account (shell = /bin/true)
usermod -s /bin/true backupbot
```

```bash
# Probe the exit-status plumbing in tests
true && echo "then branch runs"
```

```bash
# Keep a pipeline alive where a command may legitimately fail
flock -n /var/lock/job /usr/local/bin/job || true
```

```bash
# initramfs/boot sanity: the file must exist under BOTH historical paths
[ -x /bin/true ] || echo "broken userland" >&2
```

## Nuances and Gotchas

- **`true --help` prints nothing.** Arguments are ignored by specification.
  Scripts that "verify a flag exists" by running `true --version` are testing
  nothing; there is no output to check.
- **`true` vs `:`**: both are builtins in bash and dash and both exit 0.
  `:` accepts arguments like `: ${VAR:=default}` (parameter expansion side
  effects), `true` ignores them. `:` is marginally cheaper in some shells;
  `true` is clearer about intent and works where a real command is expected.
- **The binary and the builtin differ in one invisible way**: the builtin
  costs no fork/exec. Benchmarks of `while true` loops measure the builtin;
  `command true` or `/bin/true` forces the external file.
- **Don't confuse `/bin/true` as a login shell with security.** It prevents
  interactive shells but not all access (SSH port forwarding, `scp` fallback
  tricks may still apply depending on configuration); `nologin` is the
  intended tool and prints a message.
- **Under `set -e`, `cmd || true` is the documented escape hatch**, but it
  also swallows *unexpected* failures — overusing it converts silent
  breakage into a design flaw. Prefer `|| { handle; }` when the failure
  mode is known but ignorable.
- **`false` is its mirror, not its negation operator.** There is no
  `!`-command in POSIX sh besides the shell's own `!` pipeline negation;
  `if ! cmd` is shell syntax, not `false`'s job.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Always — the command's entire specification |

## Related Commands

- [`test`](./test.md) — the conditional producer whose 0/1 statuses `true` and `false` exemplify.
- [`yes`](./yes.md) — the other "does one trivial thing forever" coreutils utility.
- [`timeout`](./timeout.md) — bounds the `while true`-style loops `true` enables.
- [bash](../../shell/bash.md) — builtins, `set -e`, and `|| true` semantics.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: What does `true --help` print, and why?

Nothing. POSIX specifies that `true` (and `false`) ignore all command-line
arguments, so the GNU implementation deliberately does not implement the
usual `--help`/`--version` handling — honouring them would make behaviour
argument-dependent. It is the textbook example of a command whose interface
is a single contract: exit 0.

### Q: Why do initramfs and early-boot contexts care about /bin/true specifically?

Boot hooks, maintainer scripts, and no-op stubs invoke `/bin/true` by
absolute path, and initramfs images must therefore ship it or those steps
fail during early boot before `/usr` is mounted. On merged-`/usr` systems
`/bin` is a symlink to `/usr/bin`, so both paths resolve to one file — but
hand-built minimal environments that copy only one path break the other.
It is a small binary with outsized boot-criticality.

### Q: When would you choose `:` over `true`, and vice versa?

`:` when you want parameter-expansion side effects (`: "${VAR:=default}"`)
or a no-op branch in pure POSIX code; `true` when the intent is a command —
`exec true`, `cmd || true`, or any place a script reader should see "this
command succeeds". Both are builtins in bash/dash so the performance
difference is negligible; readability argues for `true` in command position.

### Q: Is `usermod -s /bin/true` a secure way to disable an account?

It blocks interactive login shells, which is its common use for service
accounts, but it is not an access-control boundary: SSH may still grant
port forwarding or command execution depending on configuration, and the
account is not locked (`passwd -l` / `usermod -L`) or expired. The thorough
answer combines a disabled password, `nologin` (which also logs the
attempt), and possibly `usermod -L`. `/bin/true` as shell is a compatibility
idiom, not a security control.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/true.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
