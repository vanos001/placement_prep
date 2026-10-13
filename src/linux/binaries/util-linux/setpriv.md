# setpriv — run a program with a different Linux privilege state

## Overview

`setpriv` is the low-level, no-frills sibling of `su`: it applies
credential and capability changes to the *current* process and then execs
the requested program. It wraps `setgroups`/`setresgid`/`setresuid`,
capability set manipulation, the `no_new_privs` flag, securebits and
(directly or via LSM options) SELinux/AppArmor labels — with no PAM, no
shell, no password and no user-database ceremony beyond name lookup. It
ships with the `util-linux` package (Debian bookworm) at
`/usr/bin/setpriv`.

`setpriv` is often confused with `su`/`runuser` (PAM sessions, shells,
login semantics), with `sudo` (a policy engine), and with `chrt`/`ionice`
(scheduling attributes). The mental model: setpriv is "the execve
wrapper the kernel documentation would write".

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/setpriv |
| First appeared / lineage | util-linux addition of the mid-2010s, alongside ambient capabilities |
| Standards | None — Linux-specific (setuid family + capabilities API) |

## Synopsis

```
setpriv [options] <program> [<argument>...]
```

Common one-line forms:

```
setpriv --reuid=nobody --regid=nogroup --clear-groups id
setpriv --nnp ./untrusted-helper          # no_new_privs sandbox-ish guard
setpriv --dump                            # show current state, do not exec
```

## How It Works

### Ordered transformations, then execve

`setpriv` mutates its *own* process to match the requested state and then
calls `execve` — there is no intermediate child. The option groups are
applied in the order the man page documents (simplified here):

```
 --reset-env          rebuild HOME/SHELL/USER/LOGNAME/PATH
      │
 supplementary groups (--clear-groups / --keep-groups /
      │                --init-groups / --groups)
      ▼
 setresgid            (--rgid / --egid / --regid)
      │
      ▼
 setresuid            (--ruid / --euid / --reuid)
      │
      ▼
 securebits ──► capability bounding set ──► inheritable + ambient caps
      │
      ▼
 no_new_privs (prctl PR_SET_NO_NEW_PRIVS)
      │
      ▼
 execve(program)        [or exit after --dump]
```

Dropping GID before UID is the classic safe order: while still
privileged you can set any group; after dropping UID you generally
cannot.

### Introspection with --dump

`--dump` prints the full privilege state and exits without exec'ing —
the fastest way to answer "what would this process actually run as?":

```bash
$ setpriv --dump
uid: 1001
euid: 1001
gid: 1001
egid: 1001
Supplementary groups: 1001
no_new_privs: 0
Inheritable capabilities: [none]
Ambient capabilities: [none]
Capability bounding set: chown,dac_override,fowner,fsetid,kill,
        setgid,setuid,setpcap,net_bind_service,net_raw,sys_chroot,
        mknod,audit_write,setfcap
Securebits: [none]
```

### It can only descend

setpriv starts from the caller's privilege set and can only *narrow* it.
As an unprivileged user, attempts to take a new UID fail at the syscall:

```bash
$ setpriv --reuid=1 --regid=1 --clear-groups id -un
setpriv: setresuid failed: Operation not permitted
$ echo $?
127
```

Root, by contrast, can drop to any identity — including named users, and
with fine control over which supplementary groups survive.

### Capability syntax

Capability options take a comma-separated list with a prefix: `+cap`
adds, `-cap` removes, and the list may use names (`net_raw`) or numbers.
Ambient capabilities — the mechanism that lets a *non-root* process hold
capabilities across exec — require the capability to also be in the
inheritable and permitted sets, which is why grant examples come in
pairs.

## Options That Matter

| Option | Effect |
| --- | --- |
| `--dump` | Print current uid/gid/groups/caps state and exit (no exec). |
| `--ruid, --euid` | Set real / effective UID (name or number). |
| `--reuid` | Set both real and effective UID in one call. |
| `--rgid, --egid, --regid` | Same, for GIDs. |
| `--clear-groups` | Drop all supplementary groups (default for a clean drop). |
| `--keep-groups` | Keep the caller's supplementary groups across a UID change (dangerous if descending from root). |
| `--init-groups` | Recompute supplementary groups from the group database for the target user. |
| `--groups <list>` | Set an explicit supplementary group list. |
| `--inh-caps`, `--ambient-caps`, `--bounding-set` | Capability set manipulation (`+cap`, `-cap`). |
| `--nnp, --no-new-privs` | Set `PR_SET_NO_NEW_PRIVS`: exec of setuid binaries and file capabilities will not gain privileges. |
| `--securebits <bits>` | Securebits flags (e.g. keep capabilities across UID changes). |
| `--reset-env` | Clear the environment and rebuild HOME, SHELL, USER, LOGNAME, PATH. |
| `--selinux-label`, `--apparmor-profile` | LSM label transitions where compiled in. |

Newer util-linux releases add further process-attribute options (parent
death signal, ptrace restrictions, Landlock and seccomp filter loading).

## Usage Patterns

```bash
# Clean, canonical privilege drop in a root-run script (root)
setpriv --reuid=www-data --regid=www-data --clear-groups -- /usr/bin/server --port 8080
```

```bash
# Drop UID but recompute the target's own supplementary groups
setpriv --reuid=deploy --regid=deploy --init-groups -- ./start-agent
```

```bash
# Drop UID and keep the caller's groups — only when you truly need inherited access
setpriv --reuid=1000 --regid=1000 --keep-groups -- id
```

```bash
# Harden a helper that must exec setuid binaries: forbid privilege gain
setpriv --nnp -- /usr/local/bin/parse-upload "$f"
```

```bash
# Give a non-root process the ability to craft raw packets (root)
setpriv --inh-caps=+net_raw --ambient-caps=+net_raw \
        --reuid=1000 --regid=1000 --clear-groups -- /usr/bin/my-sniffer
```

```bash
# Remove a capability from the bounding set so no child can ever regain it
setpriv --bounding-set=-sys_admin -- /usr/bin/container-init
```

```bash
# Script environment hygiene: rebuild a minimal env for the target identity
setpriv --reset-env --reuid=svc --regid=svc --clear-groups -- /opt/app/run
```

```bash
# Debug what a systemd unit's User=/AmbientCapabilities= produce
setpriv --dump
```

```bash
# One-shot check whether a uid switch would succeed, without side effects
setpriv --reuid=nobody --regid=nogroup --clear-groups -- true && echo drop-ok
```

## Nuances and Gotchas

- **No PAM.** No `pam_limits` (your `ulimit`s are the caller's), no
  session keyring setup, no auth logging. If a service needs
  `limits.conf` semantics, that is what `su`/`runuser`/PAM are for.
- **No shell, no `-c`.** The program is exec'd directly; quoting is
  single-layer (the caller's shell only). A command string that worked
  with `su user -c '...'` must be re-expressed as arguments.
- **Exit code 127 covers more than "command not found".** Privilege
  setup failures also exit 127 on recent util-linux (`setresuid failed` →
  127), so `&& echo ok` guards are safe but specific error routing is
  not; read stderr.
- **`--keep-groups` is a footgun when descending from root.** It preserves
  caller groups like `root`/`adm`/`disk` across the UID change — exactly
  what you usually do *not* want in a drop. Default to `--clear-groups`
  or `--init-groups`.
- **Ambient capabilities have prerequisites.** `--ambient-caps=+cap`
  fails unless the capability is also inheritable (and permitted), which
  is why grant recipes pair `--inh-caps` and `--ambient-caps`, and why
  they must run before the UID drop in the same invocation.
- **`--nnp` is not a sandbox.** It stops *privilege gain* via exec
  (setuid bits, file capabilities) but grants no isolation; combine with
  namespaces/LSM/seccomp for real sandboxing.
- **Name lookups happen at setpriv time.** Resolving `www-data` uses the
  host's NSS; in chroots or minimal containers the name may not resolve —
  numeric IDs are the robust form.
- **BusyBox has no setpriv.** Minimal initramfs images approximate drops
  with `su -s /bin/sh -c ... user` (as root) or explicit C code.

## Exit Status

| Code | Meaning |
| --- | --- |
| exit status of the program | Normal case after a successful exec. |
| 0 | `--dump` and other query-style successes. |
| 126 | Program found but not executable. |
| 127 | Program not found — and, observed on recent util-linux, failed privilege setup (`setresuid failed`, bounding-set rejection). |

## Related Commands

- [`su`](./su.md) — interactive identity switch with PAM authentication and a shell.
- [`runuser`](./runuser.md) — root-only, password-free su variant for scripts (PAM session still runs).
- [`chrt`](./chrt.md) — same wrap-and-exec design for scheduling policy.
- [`ionice`](./ionice.md) — I/O priority wrapper.
- [`prlimit`](./prlimit.md) — resource-limit wrapper.
- [`nsenter`](./nsenter.md) — enter another namespace's context; composes with setpriv for sandboxing.
- [Permissions](../../admin/permissions.md) — UID/GID and capability fundamentals behind these options.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why choose setpriv over su or runuser for dropping privileges in a script?

setpriv has no interactive contract to break: no PAM auth, no shell, no
tty assumptions — just ordered syscalls and an exec. It also exposes
things su cannot express: capability set edits, `no_new_privs`, explicit
supplementary group control. The trade-off is the missing PAM session
(no limits.conf application, no keyring), so use su/runuser when PAM
semantics matter and setpriv when you want exactly the syscalls you
name.

### Q: What does --no-new-privs do at the kernel level, and what does it not do?

It sets `PR_SET_NO_NEW_PRIVS` on the process: from then on, neither the
process nor its descendants can gain privileges through exec — setuid
bits are ignored, file capabilities are ignored. It does *not* provide
isolation (filesystem, network, signals are untouched) and it is
irreversible for the process. It is the same flag systemd's
`NoNewPrivileges=` sets and a prerequisite for unprivileged seccomp
filters.

### Q: Explain the difference between --clear-groups, --keep-groups and --init-groups.

`--clear-groups` empties the supplementary group list — the safe default
for a drop. `--keep-groups` preserves the caller's list, which is useful
when a root process drops UID but must retain e.g. `disk` group access —
and dangerous for the same reason. `--init-groups` ignores both and
recomputes the target user's groups from `/etc/group` via the NSS,
matching what a real login would set up.

### Q: How do you give a non-root process CAP_NET_RAW without setuid?

As root: `setpriv --inh-caps=+net_raw --ambient-caps=+net_raw
--reuid=... --regid=... --clear-groups -- prog`. The capability must be
in the inheritable set before it can be ambient, and ambient
capabilities survive exec for non-root processes — that is the whole
point of the ambient set. File capabilities on the binary (setcap) are
the static alternative; setpriv is the per-invocation one.

### Q: A root-run wrapper does `setpriv --reuid=svc --regid=svc id` and the process still reads a root-only file. What happened?

The wrapper almost certainly used `--keep-groups` (or omitted group
handling in a way that preserved membership): the UID dropped, but the
supplementary groups still include `root`/`wheel`, and DAC checks use
the full credential set. Audit with `id` or `setpriv --dump` inside the
target context and switch to `--clear-groups`/`--init-groups`.

### Q: Why does setpriv exit 127 when setresuid fails? Isn't 127 for "command not found"?

That is recent util-linux behavior worth knowing: pre-exec failures
(privilege setup) and exec-not-found both funnel to 127, so exit codes
alone cannot distinguish "could not become nobody" from "nobody has no
such binary". Scripts must parse stderr or preflight with `--dump`;
assuming 126/127 carry the classic shell semantics will bite.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/setpriv.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
