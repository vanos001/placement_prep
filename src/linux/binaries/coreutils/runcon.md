# runcon — run a program in a specified SELinux security context

## Overview

`runcon` executes COMMAND under a different SELinux security context than
the caller's: a different SELinux user, role, type, and/or MLS/MCS level
range. It is the process-side tool of the SELinux labeling family — where
`chcon`/`restorecon` change the label of *files*, `runcon` chooses the label
of the *process* that will run, and the kernel then enforces policy between
that context and everything the process touches.

The flagship use is testing policy without rebooting or re-login: fire a
binary under the type a daemon would normally run as (`runcon -t init_t ...`),
drop a helper into a sandbox type to see what it can still reach, or
exercise MCS categories (`-l s0:c1,c2`) the way container runtimes do for
multi-tenant isolation. With *neither* a CONTEXT argument nor a COMMAND,
`runcon` simply prints the current security context, making it a quick
"who am I (in SELinux terms)" probe — though plain `id -Z` is the more
idiomatic spell.

`runcon` is GNU-specific and easy to confuse with `chcon` (relabels file
context, runs nothing), with `setpriv`/`su`/`sudo` (change UNIX identity,
not SELinux context), and with `chroot` (restricts filesystem view, not
kernel object labels). On a kernel without SELinux support or a loaded
policy it is inert and fails loudly (verified message below).

| Field | Value |
|---|---|
| Package | Debian `coreutils` (bookworm; Essential package) |
| Upstream | GNU coreutils |
| Section (man) | 1 |
| Path | `/usr/bin/runcon` |
| First appeared / lineage | GNU-specific addition to coreutils in the mid-2000s, alongside Linux 2.6 SELinux support; no AT&T UNIX ancestor |
| Standards | None — not in POSIX or LSB; Linux + SELinux only |

## Synopsis

```
runcon CONTEXT COMMAND [ARG]...
runcon [ -c ] [ -u USER ] [ -r ROLE ] [ -t TYPE ] [ -l RANGE ] COMMAND [ARG]...
runcon
```

The two execution forms are mutually exclusive: either give a complete
CONTEXT as the first operand, or pick individual fields with options.
The option form inherits every field you do not override from the caller's
current context. The third form — no CONTEXT, no COMMAND — prints the
current security context.

## How It Works

### Anatomy of a security context

An SELinux context is a colon-separated 4-tuple (the last field is itself
structured for MLS/MCS):

```
┌──────────────┬───────────────┬───────────────┬───────────────────┐
│ SELinux user │ role          │ type (domain) │ level / range     │
├──────────────┼───────────────┼───────────────┼───────────────────┤
│ system_u     │ system_r      │ unconfined_t  │ s0                │
│ user_u       │ user_r        │ user_t        │ s0:c1,c2          │
└──────────────┴───────────────┴───────────────┴───────────────────┘
      │              │               │                  │
      │              │               │                  └─ MLS sensitivity
      │              │               │                    + MCS categories
      │              │               └─ THE enforcement domain: what the
      │              │                  process may do (type enforcement)
      │              └─ set of types the process may enter (RBAC layer)
      └─ identity used by policy, NOT a UNIX uid (unrelated to root)
```

The *type* is where enforcement actually happens — SELinux type enforcement
decides, per process type, which object types it may read, write, open, or
execute. Users and roles gate which types are reachable; the MLS/MCS range
adds hierarchical (sensitivity) and categorical (MCS `c0`..`c1023`)
constraints used for data isolation between tenants of the same type.

### What runcon actually does

`runcon` sets the requested context on the *next exec* (the library call
`setexeccon`, roughly "label the process this way at exec time") and then
execvp's COMMAND. Nothing is relabeled on disk; the command's files, sockets,
and children inherit whatever the kernel policy derives from the new process
context. With the option form (`-t`, `-u`, `-r`, `-l`), every unspecified
field is inherited from the calling process's context, so
`runcon -t httpd_t cmd` keeps your current SELinux user and role and changes
only the domain.

```bash
# Full-context form: every field stated explicitly
$ runcon system_u:system_r:unconfined_t:s0 id -Z

# Option form: only the type differs from the caller's context
$ runcon -t unconfined_t id -Z
```

`-c` (`--compute`) is the middle ground: instead of forcing the fields you
passed, it asks the kernel to compute the transition the policy would choose
anyway (the automatic type-transition logic used when a daemon starts a
helper), applying your flags on top of that result.

### Why a request can fail

The kernel checks the transition against the loaded policy, not against your
wishes or your uid — root gains nothing:

- the kernel lacks SELinux support or has it disabled:
  `runcon: runcon may be used only on a SELinux kernel` (exit 1 — verified
  on a plain non-SELinux container);
- the target type/user/role does not exist in the loaded policy;
- the policy does not permit *this* caller's context to transition into the
  target type (the usual `avc: denied` in the audit log), or the target
  type is not an allowed entrypoint for the binary being executed;
- MLS/MCS constraints reject the requested range combination;
- in enforcing mode the denial stops the exec; in permissive mode the same
  denial is only logged and the command runs anyway — which makes permissive
  mode the comfortable setting for policy testing with runcon.

Also worth grounding the "print current context" form: on a non-SELinux
system it cannot even ask the kernel:

```bash
$ runcon
runcon: failed to get current context: Invalid argument
runcon: no command specified          # exit 1
```

## Options That Matter

| Option | Effect |
|---|---|
| `CONTEXT` | First-operand form: complete `user:role:type:range` applied verbatim |
| `-c`, `--compute` | Compute the process transition context from policy before applying modifications |
| `-t`, `--type=TYPE` | Set only the type (domain); user/role/range inherited from caller |
| `-u`, `--user=USER` | Set the SELinux user identity (not the UNIX uid) |
| `-r`, `--role=ROLE` | Set the role |
| `-l`, `--range=RANGE` | Set the MLS sensitivity / MCS category range, e.g. `s0` or `s0:c1,c2` |
| *(no operands)* | Print the current security context |

Notes: `runcon CONTEXT cmd` and `runcon -t TYPE -r ROLE cmd` cannot be
mixed — choose one form per invocation. The option form is the one scripts
usually want, because keeping the caller's identity fields avoids whole
classes of "identity not allowed into role" policy denials. And `runcon`
mirrors the classic exec-wrapper exit contract (see Exit Status): any script
using it must treat 125 as "the context change failed", distinct from "the
command failed".

## Usage Patterns

```bash
# Who am I, SELinux-wise (typical output on an SELinux host; equals `id -Z`)
$ runcon
unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023
```

```bash
# Run a one-off command as the type a daemon would have
$ runcon -t httpd_t /usr/bin/curl -s https://localhost/healthz
```

```bash
# Full-context form when user/role must also change (e.g. emulate a service)
$ runcon system_u:system_r:init_t:s0 /usr/sbin/some-service --check
```

```bash
# Sandbox test: does the target type still reach sensitive paths?
# (typical denial on an enforcing SELinux host)
$ runcon -t sandbox_t cat /etc/shadow
runcon: failed to run command 'cat': Permission denied
```

```bash
# MCS multi-tenancy smoke test: same type, different category set
$ runcon -t container_t -l s0:c1,c2 /usr/bin/app --data /srv/tenant1
$ runcon -t container_t -l s0:c3,c4 /usr/bin/app --data /srv/tenant2
```

```bash
# Combine with chroot: restrict the filesystem view AND the process label
$ sudo chroot /srv/jail /usr/bin/runcon -t jail_t /usr/local/bin/job
```

```bash
# Prove the environment lacks SELinux before debugging anything else
$ runcon -t init_t id
runcon: runcon may be used only on a SELinux kernel
$ echo $?
1
```

```bash
# Differentiate runcon's own failure from the child's, in a script
$ runcon -t unconfined_t ./build.sh
case $? in
  125) echo "runcon could not set the context" ;;
  126) echo "command found but not executable" ;;
  127) echo "command not found" ;;
esac
```

## Nuances and Gotchas

- **No SELinux, no tool.** On kernels without SELinux (or without a loaded
  policy), every invocation fails: `runcon: runcon may be used only on a
  SELinux kernel` for execution forms, and
  `failed to get current context: Invalid argument` for the print form.
  Debian defaults to AppArmor, so a stock bookworm system typically shows
  exactly this — check with `getenforce` (or the absence of
  `/sys/fs/selinux`) before blaming your flags.
- **Root does not bypass policy.** Unlike DAC checks, SELinux type
  enforcement does not bend for uid 0; a transition the policy denies is
  denied for root too. The unlock is editing/loading policy (or permissive
  mode), not `sudo`.
- **`-t` alone inherits user and role.** If your current SELinux
  user/role pair is not permitted to enter the target type, `runcon -t foo_t`
  fails even though `foo_t` exists and the type alone looks right. For
  emulating daemons you often need the full context form.
- **Permissive vs enforcing changes what you observe.** In permissive mode
  the same forbidden transition is logged (audit `avc: denied`) but the
  command runs; scripts asserting on failure will see different results per
  mode. State which mode you tested under when reporting policy bugs.
- **runcon never relabels files.** A process started with `-t container_t`
  still reads files labeled for other types only if policy allows; creating
  files under the new context does not necessarily label them that way
  (type transition rules govern that). Use `chcon`/`restorecon` for on-disk
  labels.
- **125 is runcon's own failure.** Because 125/126/127/child-status all
  surface through `$?`, a naive `runcon ... || alert` cannot distinguish "no
  such command" from "context denied"; branch on the code explicitly.
- **Portability is nil.** GNU coreutils on Linux+SELinux only — not in
  POSIX, not in BusyBox, not on macOS/BSD. Scripts using runcon need a
  guard (`command -v runcon`) and an SELinux detection step.
- **MCS ranges are what containers use.** Docker/container runtimes isolate
  same-type containers via MCS categories (`s0:c1,c2`); experimenting with
  `-l` against a real policy is the fastest way to understand why two
  containers of the same type still cannot read each other's labeled files.

## Exit Status

| Status | When |
|---|---|
| 125 | `runcon` itself failed (bad context, SELinux unavailable, transition denied) |
| 126 | COMMAND was found but could not be invoked (permissions, format) |
| 127 | COMMAND could not be found |
| otherwise | The exit status of COMMAND itself |
| 1 | Also seen for the no-operand print form on a non-SELinux kernel (context query fails) |

## Related Commands

- [`chroot`](./chroot.md) — confines the filesystem view; `runcon` confines the kernel-visible label; combined they approximate a poor-man's sandbox.
- [`env`](./env.md) — the other "start a program with a modified something" wrapper (environment vs security context).
- [`nice`](./nice.md) — modifies scheduling priority at exec, the same wrapper shape with a different kernel knob.
- [`timeout`](./timeout.md) — time-bounds the child; composes with runcon for bounded, labeled test runs.
- [`chmod`](./chmod.md) — DAC permissions vs SELinux type enforcement: two orthogonal gates a process must both pass.
- [Overview — GNU Coreutils collection](./overview.md) — hub page for the collection.
- [Permissions](../../admin/permissions.md) — where DAC ends and MAC (SELinux) begins.
- [Process management](../../admin/process-management.md) — how exec-time attributes (contexts, limits, priorities) attach to processes.

## Interview Questions

### Q: What does `runcon` change, and what does it deliberately not change?

It sets the SELinux security context — user, role, type, and MLS/MCS range —
of the process created for COMMAND, at exec time, and leaves the on-disk
labels of every file untouched. The kernel then enforces the loaded policy
between that new process context and all objects it touches. File relabeling
is `chcon`/`restorecon` territory; UNIX identity is `su`/`sudo`/`setpriv`
territory; runcon is only the process label.

### Q: Why does `runcon -t foo_t cmd` fail as root on a machine where `foo_t` clearly exists?

Because SELinux decisions come from the loaded policy, not from uid. Two
common causes: the caller's *inherited* SELinux user/role (remember `-t`
changes only the type) is not authorized to enter `foo_t`, or the policy
does not designate the executed binary as a valid entrypoint for that type.
Root only bypasses DAC; type enforcement applies to root equally, so the fix
is a correct full context, a policy rule, or permissive mode for testing.

### Q: Interpret the exit codes `125`, `126`, `127` from a `runcon` invocation.

125 means runcon itself failed — bad syntax, no SELinux, or a denied
transition — so the child never ran. 126 means the command was located but
could not be executed (permissions, bad binary format). 127 means the
command was not found at all. Any other value is simply the child's own exit
status. Distinguishing 125 from the child's failures is what lets a script
report "the sandbox denied you" instead of "your program crashed".

### Q: What is the difference between `-t`, `-u`, `-r`, and `-l`, and which field does most enforcement?

`-t` sets the *type* (domain), `-u` the SELinux user identity, `-r` the
role, `-l` the MLS/MCS level range. Type enforcement — the per-type allow
rules — is where nearly all practical authorization happens, so `-t` is the
workhorse flag. User and role form the RBAC layer deciding which types are
reachable, and the range field adds MLS/MCS constraints, which is the
mechanism container runtimes use to isolate same-type tenants by category.

### Q: How would you use runcon to validate a new SELinux policy before rollout?

Run the target binary under the type the policy assigns it
(`runcon -t newtype_t ./binary`) in permissive mode, where denials are
logged but not enforced, then inspect the audit log for `avc: denied` lines
to find missing allow rules; repeat with real workloads, including MCS-range
variants (`-l s0:c1,c2`) for multi-tenant cases. The verified failure mode
on a non-SELinux machine (`runcon may be used only on a SELinux kernel`)
means the harness should first assert SELinux is active, and exit-status
discipline (125 vs child status) keeps "policy denied" distinct from
"program failed".

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/runcon.1.en.html)
