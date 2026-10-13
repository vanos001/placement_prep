# chcon — one-shot change of SELinux security context

## Overview

`chcon` sets the SELinux security context of files: the
`user:role:type:level` label stored in the `security.selinux` extended
attribute of every SELinux-labeled inode. Where `chmod` and `chown` edit
discretionary metadata (mode bits, uid/gid), `chcon` edits the
mandatory-access-control label that the SELinux policy matches rules
against. It mirrors their interface on purpose: per-part flags
(`-u`, `-r`, `-t`, `-l`), a `--reference=RFILE` mode like `chown --reference`,
and the same `-R`/`-H`/`-L`/`-P` traversal family as `chgrp`.

Debian ships it in `coreutils` at `/usr/bin/chcon` (built with SELinux
support via libselinux). It is a **one-shot, surgical** tool: the labels it
writes last until something relabels the file from policy — `restorecon`,
a package update's `fixfiles`, or a boot-time autorelabel. The persistent
way to define what a path *should* be labeled is `semanage fcontext` plus
`restorecon` (package `policycoreutils-python-utils`), which is why `chcon`
is best treated as a debugging and triage tool, not configuration
management.

Two failure modes dominate real use: partial-context changes on files that
have no current label to merge into, and "successful" changes on systems
where SELinux is disabled — see How It Works and the gotchas.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/chcon` on modern Debian/Ubuntu |
| First appeared / lineage | Merged into GNU coreutils mid-2000s with the SELinux support set (`ls -Z`, `id -Z`) |
| Standards | SELinux-specific; not in POSIX |

## Synopsis

```
chcon [OPTION]... CONTEXT FILE...
chcon [OPTION]... [-u USER] [-r ROLE] [-l RANGE] [-t TYPE] FILE...
chcon [OPTION]... --reference=RFILE FILE...
```

Main forms:

```bash
chcon system_u:object_r:httpd_sys_content_t:s0 /srv/www/index.html
chcon -t httpd_sys_content_t /srv/www/*.html     # change only the type
chcon --reference=/var/www/html/index.html ./new.html
chcon -R -t container_file_t /var/lib/mydata     # recursive relabel
```

## How It Works

### Anatomy of a context

Every labeled inode carries four colon-separated components. The **type**
(aka domain for processes) is the part the policy's `allow` rules match on
for file access; user and role matter mostly for MLS/identity semantics,
and the level/range only bites under MLS policies.

```
  unconfined_u : object_r : user_tmp_t : s0
  ──────┬─────   ───┬───   ─────┬─────   ─┬─
    SELinux    role for    the type   MCS/MLS
    user       files       policy     level or
    identity   (object_r)  checks     range
```

For day-to-day file labeling work, almost everything is `object_r` and the
interesting question is "which **type** may the serving process access?" —
hence `-t` being the flag you use 95% of the time.

### Partial vs full context

The three synopsis forms differ in what they need to read:

- **Full `CONTEXT` string** — a raw write of all four components to
  `security.selinux`. It does not require reading the file's current label.
- **`-u/-r/-t/-l` partial change** — coreutils must read the *current*
  context first and splice one component. On a file with no existing label
  (the file system has never been labeled, `ls -Z` shows `?`), there is
  nothing to splice and it fails:

```bash
$ ls -Z f1.txt
? f1.txt
$ chcon -t user_tmp_t f1.txt
chcon: can't apply partial context to unlabeled file 'f1.txt'    # exit 1
$ chcon unconfined_u:object_r:user_tmp_t:s0 f1.txt               # full form
$ ls -Z f1.txt
unconfined_u:object_r:user_tmp_t:s0 f1.txt
```

### What "success" means when SELinux is off

On a kernel without SELinux enforcement (the Debian/Ubuntu default is
SELinux disabled), the xattr write may still succeed — the label is stored
and `ls -Z` will even display it, but no policy consults it. So `chcon`
exit 0 proves the *metadata write* worked, not that any access decisions
changed. The honest checks for "is this system enforcing?" are
`getenforce` (SELinux-enabled systems) or the absence of
`/sys/fs/selinux`.

### chcon vs restorecon vs semanage fcontext

```
   policy defaults                your intent
   ┌──────────────┐   semanage    ┌─────────────────────┐
   │ file_contexts│ ─fcontext -a─►│ persistent mapping  │
   │ (rules)      │               │ path regex → type   │
   └──────┬───────┘               └──────────┬──────────┘
          │ matchpathcon (query)             │ restorecon (apply)
          ▼                                  ▼
   "what SHOULD this be?"  ───────►   relabeled file
          ▲
          │ chcon (bypasses rules; writes label directly)
   "what I want RIGHT NOW"
```

- `chcon` writes a label you choose — survives until the next relabel.
- `restorecon` resets labels to what the mapping rules say — the bulk fixer.
- `semanage fcontext -a -t TYPE '/path(/.*)?'` records the mapping
  persistently, after which `restorecon -v /path` applies it.
- A full relabel (`fixfiles onboot`, or autorelabel) rewrites the whole
  file system from the mapping rules — wiping every chcon-only change.

### Traversal and symlinks

By default chcon changes the referent of a symlink (like chmod), and
`-R` traversal follows **no** symlinks (`-P` semantics). `-h` inverts the
first behavior to label the link itself; `-H`/`-L`/`-P` (last one wins)
control what `-R` follows, identical to `chown`/`chgrp`. `--preserve-root`
is the default for recursive runs.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t`, `--type=TYPE` | Set only the type component — the workhorse flag |
| `-u`, `--user=USER` | Set only the SELinux user component |
| `-r`, `--role=ROLE` | Set only the role component (rarely `object_r` changes) |
| `-l`, `--range=RANGE` | Set the MCS/MLS level or range (MLS policies only) |
| `--reference=RFILE` | Copy RFILE's whole context to each FILE |
| `-h`, `--no-dereference` | Change the symlink itself, not its referent (default is the referent) |
| `-R`, `--recursive` | Recurse into directories |
| `-H` / `-L` / `-P` | With `-R`: traverse command-line dir symlinks / all dir symlinks / none (default `-P`) |
| `-v`, `--verbose` | Print a diagnostic for every file processed |
| `--preserve-root` | Refuse `-R` on `/` (default); `--no-preserve-root` overrides |

## Usage Patterns

```bash
# Serve a relocated docroot: give the web server's type to the tree
chcon -R -t httpd_sys_content_t /srv/web/htdocs
```

```bash
# A daemon needs write access to its state dir after a manual move
chcon -R -t var_lib_t /srv/myapp/state        # triage; see semanage below
```

```bash
# Copy the context from a known-good sibling instead of typing it
chcon --reference=/etc/ssh/sshd_config /etc/ssh/sshd_config.new
```

```bash
# Change only the type on a log dir, verbosely, one line per file
chcon -Rv -t var_log_t /var/log/myapp
```

```bash
# Label the symlink itself rather than the target
chcon -h -t httpd_sys_content_t /var/www/html/current
```

```bash
# Full context when the file is unlabeled and partial forms fail
chcon system_u:object_r:etc_t:s0 /etc/myapp/app.conf
```

```bash
# Mirror a reference tree's labeling onto your staged copy
chcon -R --reference=/etc/myapp /staging/etc/myapp
```

```bash
# Set an MLS range under a policy that enforces categories
chcon -l s0-s0:c0.c100 /srv/classified
```

```bash
# Guard recursive runs: never relabel more than the subtree
chcon -R --preserve-root -t container_file_t /var/lib/containers/volumes/appdata
```

## Nuances and Gotchas

- **chcon is not persistent configuration.** `restorecon`, `fixfiles`
  relabels, and policy updates re-derive labels from the mapping rules and
  silently revert chcon's changes. Anything that must survive goes into
  `semanage fcontext` (then `restorecon` to apply) — chcon is the
  "right now" tool, which also makes it the right tool for testing a label
  hypothesis before encoding it in policy.
- **Partial changes need an existing label.** `chcon -t`/`-u`/`-r`/`-l`
  read the current context to splice into; on an unlabeled file they abort
  with "can't apply partial context to unlabeled file" (exit 1). Use the
  full four-component form, or `--reference`, to bootstrap a label.
- **Exit 0 can be meaningless.** With SELinux disabled, the xattr write
  often still succeeds and `ls -Z` shows the new label — but no policy
  consults it. Conversely, on systems whose kernel or file system rejects
  `security.selinux`, you get `Operation not supported`. Interpret results
  against `getenforce`/`sestatus`, not against chcon's exit code alone.
- **The type is what policy checks; don't freelabel the rest.** Randomly
  changing `-u`/`-r` (e.g., inventing users the policy has no rules for)
  usually just breaks things; targeted policies expect `object_r` roles and
  standard users on files.
- **Traversal defaults are the safe ones — keep them.** `-R` without
  traversal flags follows no symlinks (`-P`), and bare paths dereference to
  the referent. `-L` on a tree with hostile symlinks can label far outside
  what you intended; if you must use it, pair it with `-v` and a tight path.
- **`--reference` copies all four components** — convenient, but it also
  copies an MLS range and user you may not want; on MLS systems that is a
  real mistake class. Prefer explicit `-t` when only the type is wrong.
- **Tooling may be absent on minimal installs.** Debian's coreutils always
  has chcon, but `restorecon`/`matchpathcon`/`semanage` live in the
  policycoreutils / libselinux-utils packages — scripts that assume they
  exist break on containers.
- **Not POSIX, not portable.** Non-SELinux systems (most hardened BSDs,
  musl images without libselinux) either lack the binary or reject the
  operation; feature-detect with `command -v chcon` plus a check for
  `/sys/fs/selinux`.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Every requested context change succeeded |
| 1 | At least one failure: unlabeled file for a partial change, unsupported operation, policy/permission denial, bad CONTEXT syntax |

## Related Commands

- [`chmod`](./chmod.md) — discretionary mode bits; chcon is the MAC-label counterpart
- [`chown`](./chown.md) — same `--reference` and `-H/-L/-P` idiom, different metadata
- [`chgrp`](./chgrp.md) — group-side ownership change; shares the traversal semantics
- [`ls`](./ls.md) — `ls -Z` is how you read contexts back before and after
- [permissions](../../admin/permissions.md) — where DAC ends and MAC begins
- [users-groups](../../admin/users-groups.md) — Unix identity model vs SELinux user/role identity
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages

## Interview Questions

### Q: What are the four components of an SELinux file context, and which one usually matters?

`user:role:type:level` — SELinux user identity, role (`object_r` for
almost all files), type, and the MCS/MLS level or range. Access decisions
in standard targeted policies match on the **type**: a process domain is
allowed `read`/`write` on specific file types, so relabeling a file with
`chcon -t httpd_sys_content_t` is what makes a relocated web root readable
by httpd. The user/role matter for identity semantics and the level only
under MLS-enabled policies.

### Q: Why is `chcon` discouraged as the permanent fix for a mislabeled path, and what is the correct sequence?

Because labels from chcon exist outside the policy's mapping rules and are
reverted by any relabel: `restorecon` runs, a package's postinst relabels,
or the system autorelabels on boot. The durable fix is
`semanage fcontext -a -t TYPE '/regex(/.*)?'` to record the mapping, then
`restorecon -v /path` to apply it; audit the result with `matchpathcon`.
chcon remains valuable precisely for verifying the hypothesis — if
`chcon -t ...` makes the service work, you have confirmed the label was
the problem and should encode that mapping persistently.

### Q: `chcon -t etc_t file` fails with "can't apply partial context to unlabeled file". What happened and what are your options?

A partial change (`-t`/`-u`/`-r`/`-l`) must read the file's current context
to splice one component in; the file has no `security.selinux` xattr at
all, so there is nothing to splice. Options: write the full four-component
context explicitly (`chcon system_u:object_r:etc_t:s0 file`), copy one
from a sibling via `chcon --reference`, or label the whole file system
(`restorecon`) if the box was never labeled. It is a missing-label error,
not a permission error.

### Q: You ran `chcon -t var_t /data` on a workstation and it exited 0, but the deny messages in the log did not stop. What is going on?

Exit 0 only means the xattr write happened. If SELinux is disabled on that
system (the default on Debian/Ubuntu), no policy consults the label, so
the original problem — whatever produced the denials you were chasing —
is unchanged; check `getenforce`/`sestatus` and whether the kernel has
SELinux enabled. The inverse also bites: on a non-labeling file system the
same command fails with `Operation not supported`. chcon's exit code
reports metadata mechanics, not security posture.

### Q: What are the default symlink semantics of chcon, and how do you relabel the link itself or recurse safely?

Bare arguments dereference: chcon labels the referent. `-h
/--no-dereference` labels the symlink inode itself — what you want for
`current`-style pointer links. Under `-R`, the default traversal is `-P`
(no symlink followed); `-H` follows directory symlinks named on the
command line and `-L` follows every directory symlink — the last flag
specified wins. Safe recursion is `-R` (or `-RH` at most) plus `-v`, and
`--preserve-root` stays on.

### Q: How does `chcon --reference=RFILE` differ in risk from `chcon -t TYPE`?

`--reference` copies all four components — including the SELinux user and
any MLS range — which on MLS-enabled systems can stamp a file with a
sensitivity it should not have, or an identity with no matching rules. It
is ideal when cloning known-good labeling (staged configs, restored
backups); if only the type is wrong, surgical `-t` avoids inheriting
unintended components.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/chcon.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
