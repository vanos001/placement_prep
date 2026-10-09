# id — print user and group identities

## Overview

`id` prints the identity a process runs as — user ID, group ID, and the full
supplementary group list — either for the calling process or, given a USER
operand, as recorded in the system's user database. It is the diagnostic
that answers "who does the kernel think I am, and what can I group-wise
touch?", and the scripted form of that question (`id -u`, `id -Gn`) appears
in a large share of production shell code.

It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at
`/usr/bin/id`, maintained upstream as part of GNU coreutils. The tool has
BSD lineage and has been standardized by POSIX for decades, which makes the
core flags (`-u -g -G -n -r`) the portable subset; `-Z` (SELinux context)
and `-z` (NUL delimiting) are Linux/GNU extensions.

`id` is most often confused with `whoami` (effective user *name* only —
exactly `id -un`), with `groups` (only the group list — exactly `id -Gn`
for the current process), and with `logname` (the *login* identity from the
session record, stable across privilege switches). The distinction that
interviews probe is real versus effective identity, and `id` is the one
tool that shows both.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/id` |
| First appeared / lineage | BSD lineage; in GNU coreutils |
| Standards | POSIX.1-2018 (`id` with `-u`, `-g`, `-G`, `-n`, `-r`) |

## Synopsis

```
id [OPTION]... [USER]...
```

Common one-line forms:

```
id                    # uid, gid, supplementary groups of this process
id alice              # same, from the user database for alice
id -un                # effective user name (== whoami)
id -Gn user           # all group names for user
id -Z                 # SELinux security context of this process
```

## How It Works

### Two sources of truth: process credentials vs the user database

Without operands, `id` reads the calling process's credentials with
`getuid`/`geteuid`, `getgid`/`getegid`, and `getgroups(2)` — the live
security state the kernel enforces on every syscall. With a USER operand,
no process is involved: `id` performs a pure database lookup through NSS
(NSS: `/etc/passwd`, `/etc/group`, then LDAP/SSSD and friends), resolving
the account's recorded UID, primary GID, and the groups that list the user
as a member. The difference matters whenever privilege switching or
in-memory group changes are involved:

```
        ┌──────────────── process credentials (live) ────────────────┐
        │ real uid/gid        who started the process                 │
        │ effective uid/gid   whose permissions apply right now       │
        │ saved uid/gid       stash for setuid privilege switching    │
        │ supplementary set   getgroups(2) vector — mutable at runtime│
        └──────────────┬─────────────────────────────────────────────┘
   id (no operand)     │                    id USER
   kernel reads only   │                    database snapshot:
   via getuid/getgroups│                    passwd + group + NSS
                       ▼
        NSS: /etc/passwd, /etc/group, LDAP, SSSD, winbind…
```

A user who has run `newgrp docker` gets the group in `id`'s output but not
in `id thatuser`'s — the first reads the process, the second reads the
files. Conversely `id root` works on a machine where root has no processes
at all, because nothing but the database is consulted.

### Anatomy of the default output

```bash
$ id
uid=1001(z) gid=1001(z) groups=1001(z)
```

Three `name=value` pairs: effective UID, effective GID, and the complete
supplementary vector (which here contains only the primary group). The
parenthesized names are NSS decorations around the numbers. Two things are
conspicuously absent on a stock system: any mention of *real* IDs (omitted
when identical to effective) and any SELinux context (appended as
`context=...` only on SELinux systems). Both appear as soon as they carry
information, which is precisely why the default format is hostile to
parsing — see gotchas.

```bash
$ id nobody
uid=65534(nobody) gid=65534(nogroup) groups=65534(nogroup)
```

Querying another user needs no privileges beyond reading the user database,
and works for any account, logged in or not.

### Effective, real, and the flag combinations

The kernel maintains real and effective IDs separately so that setuid
programs and privilege switches can move the effective ID while remembering
where they came from. `id` exposes the split through `-r` (real) combined
with one of `-u/-g/-G`:

```bash
# After a privilege switch (sudo, su, setuid binary):
#   id -u     → 0        effective UID: whose permissions apply
#   id -ru    → 1001     real UID: who started the process
#   id -un    → root     effective name, exactly what whoami prints
```

Without a privilege switch the two coincide, which is why plain shells show
no difference — and why scripts must test the *effective* UID for "am I
root" (the one the kernel enforces) but may want the real UID for
"which human launched this".

The narrow output flags compose: `-u`/`-g`/`-G` pick the field, `-n`
renders names instead of numbers, `-r` selects real over effective.

```bash
$ id -u; id -un; id -g; id -gn; id -G; id -Gn
1001
z
1001
z
1001
z
```

### Contexts, NUL delimiters, and multiple users

On SELinux systems, `id -Z` prints the process's security context
(`unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023`-style) — the
subject label that SELinux policy evaluates. On kernels without SELinux
support the option is a hard error, not an empty output. For scripting,
`-z` delimits entries with NUL instead of whitespace, pairing with
`xargs -0` and surviving group names that contain spaces:

```bash
$ id -Gz | od -c | head -2
0000000   1   0   0   1  \0
```

Recent GNU coreutils releases (the 9.2 era onward) also accept multiple
USER operands, printing one report per user; older releases — including
bookworm's 9.1 — reject a second operand as an error. Scripts that must
run on bookworm should loop over users instead.

### Name resolution failure is a first-class scenario

When the numeric UID has no NSS entry — a container where the UID exists in
the kernel but not in `/etc/passwd`, an LDAP outage, a deleted account —
`id` prints the bare number without parentheses and keeps going:

```bash
# In a container with an unmapped UID:
#   uid=165536 gid=165536 groups=165536     <- no names available
```

This "naked number" output is the tell-tale of passwd-file drift in
containers, chroots, and user-namespace remaps (`/etc/passwd` on the inside
not covering the UID used on the outside), and it is why `id` is the first
diagnostic for "files owned by nobody-ish UIDs" complaints. The lookup
itself failing hard — a USER operand that matches nothing — is an error
with exit status 1.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-u, --user` | Print only the effective UID (number by default) |
| `-g, --group` | Print only the effective GID |
| `-G, --groups` | Print all group IDs — primary plus supplementary |
| `-n, --name` | Names instead of numbers; requires `-u`, `-g`, or `-G` |
| `-r, --real` | Real instead of effective; requires `-u`, `-g`, or `-G` |
| `-Z, --context` | Print only the SELinux security context of the process |
| `-z, --zero` | NUL-delimit entries; not permitted in the default format |
| `-a` | Ignored — compatibility with other `id` versions |

## Usage Patterns

```bash
# The portable root guard — numeric, NSS-independent
[ "$(id -u)" -eq 0 ] || { echo "must run as root" >&2; exit 1; }
```

```bash
# The inverse: refuse root for builds that must not run privileged
[ "$(id -u)" -ne 0 ] || { echo "do not build as root" >&2; exit 1; }
```

```bash
# Membership check that survives group names with spaces
id -Gn | tr ' ' '\n' | grep -Fx docker >/dev/null || echo "not in docker group"
```

```bash
# Numeric group check — immune to NSS renames of the group
id -G | tr ' ' '\n' | grep -qx 999 && echo "member of gid 999"
```

```bash
# Verify an account exists and grab its UID/GID before chown
uid=$(id -u deploy) && gid=$(id -g deploy) && chown "$uid:$gid" /srv/app
```

```bash
# Audit another account's supplementary groups without logging in
id -Gn backup | grep -qw media && echo "backup can read media"
```

```bash
# NUL-safe group list for xargs pipelines
id -Gz alice | xargs -0 -n1 getent group
```

```bash
# SELinux context of the current shell (guard: not every kernel has it)
id -Z 2>/dev/null || echo "no SELinux"
```

```bash
# The whoami spelling and the id spelling, side by side
echo "running as $(id -un)"     # == $(whoami), but POSIX-blessed
```

```bash
# Docker-style UID:GID passthrough for volume ownership
docker run --user "$(id -u):$(id -g)" -v "$PWD:/work" builder
```

```bash
# Real-vs-effective pair for a setuid-era audit script
printf 'euid=%s ruid=%s\n' "$(id -u)" "$(id -ru)"
```

```bash
# Locate every file owned by a given account (database UID, not a name)
find /srv -user "$(id -u alice)" -ls | head
```

## Nuances and Gotchas

- **The default output is for humans, not parsers.** The `context=` field
  appears only on SELinux systems, names degrade to bare numbers when NSS
  fails, and the `groups=` list is whitespace-joined — extract fields with
  `id -u`, `id -G`, etc., never by cutting columns of the pretty form.
- **`id USER` is a database snapshot.** It cannot see process-level state:
  a user inside `newgrp`, a daemon that dropped supplementary groups, or a
  logged-in session with a different SELinux context all differ from what
  the database says. Conversely, database answers are available for
  accounts with no running processes at all.
- **`-Z` fails hard without SELinux.** On a plain kernel it exits 1 with
  `--context (-Z) works only on an SELinux-enabled kernel` — treat it as a
  feature probe (`id -Z 2>/dev/null`) rather than expecting empty output.
- **Naked numbers mean NSS trouble.** `uid=165536` with no parentheses is
  not cosmetic: it says the process UID has no passwd entry — the standard
  symptom of user-namespace remapped containers, a stale `/etc/passwd`, or
  an unreachable directory service. `getent passwd 165536` continues the
  diagnosis.
- **`-n` and `-r` are not standalone.** Both require `-u`, `-g`, or `-G`;
  bare `id -n` or `id -r` is a usage error (`printing only names or real
  IDs requires -u, -g, or -G`), which surprises people converting `groups`
  one-liners.
- **`-z` is rejected in default format.** NUL delimiting only applies to
  the narrow outputs (`-G`, `-u`, `-g`, `-Z`); `id -z` alone is an error.
- **Supplementary groups have a kernel ceiling.** `getconf NGROUPS_MAX` on
  current Linux is 65536 — the cap on the `getgroups(2)` vector that `id`
  prints, and the point past which `setgroups(2)` fails. Membership beyond
  the cap is invisible to `id -G`, a real trap on systems migrated from the
  old 16/32-group limits.
- **Root checks must be numeric.** `[ "$(whoami)" = root ]` breaks when the
  account is renamed, NSS is down, or a UID-0 account is named otherwise;
  `[ "$(id -u)" -eq 0 ]` tests the fact the kernel enforces.
- **Portability.** `-u -g -G -n -r` are POSIX and work from BusyBox to BSD;
  `-Z` is SELinux/Linux only, `-z` and multi-user operands are recent GNU
  additions. The `id` on macOS/BSD is the BSD implementation — same core
  flags, subtly different diagnostics.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Identity(ies) printed successfully |
| 1 | Unknown USER operand, `-Z` on a non-SELinux kernel, or option/operand misuse |

## Related Commands

- [`groups`](./groups.md) — the group-list-only sibling; exactly `id -Gn` for the current process.
- [`whoami`](./whoami.md) — the effective-user-name one-liner; exactly `id -un`.
- [`logname`](./logname.md) — the login identity from the session record; stable across sudo/su where id's answer moves.
- [`users`](./users.md) — who is logged in, from utmp; the session view id ignores.
- [`chown`](./chown.md) — the tool whose numeric `uid:gid` operands `id` conveniently produces.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [users and groups](../../admin/users-groups.md) — the account database that id queries.
- [permissions](../../admin/permissions.md) — how uid/gid answers translate into access decisions.

## Interview Questions

### Q: What is the difference between real and effective UID, and which id flags expose each?

The real UID records who started the process; the effective UID is the
identity the kernel enforces on permission checks right now; the saved
set-user-ID lets a program swap between them. `sudo`, `su`, and setuid
binaries change the effective ID while leaving the real ID alone, so after
`sudo` `id -u` prints 0 and `id -ru` prints the original account. Scripts
test the effective UID (`id -u -eq 0`) because that is what access checks
actually consult, and audit tooling reports the real UID to attribute the
session to a human.

### Q: Why does `id alice` work on a server where alice has never logged in, and when can its answer be wrong for alice's running processes?

Because with an operand, `id` performs a pure NSS database lookup — passwd
entry for UID/GID, group file (and directory service) for supplementary
membership — and reads no process state. It diverges from reality whenever
a process has modified its own credentials: `newgrp`/`sg` sessions, daemons
that deliberately dropped supplementary groups after binding privileged
ports, containers whose UID mappings differ from the host database, and
SELinux contexts, which are per-process and never part of a database
lookup.

### Q: Why is `[ "$(id -u)" -eq 0 ]` preferred over `[ "$(whoami)" = root ]` for root checks?

The numeric test reads the effective UID the kernel actually enforces and
never depends on NSS resolving UID 0 to the *name* root — which fails or
lies when the passwd entry is missing, the directory service is down, or
the system renames the root account (as hardened images do). `whoami` is
also not POSIX, while `id` is, so the numeric spelling is both semantically
correct and portable from GNU to BusyBox to BSD.

### Q: A script prints `uid=165536 gid=165536 groups=165536` with no names. What does that tell you, and what do you check next?

The process runs under a UID that has no entry in the NSS user database —
the number is printed bare because there is no name to parenthesize. The
usual suspects: a user-namespace-remapped container (host UID 165536 mapped
to an unprivileged range inside), a `/etc/passwd` missing from that image
or layer, a deleted account still owning running processes, or an
unreachable LDAP/SSSD backend. `getent passwd 165536` distinguishes
"missing entry" from "lookup broken", and checking `ls -ln` confirms files
really are owned by the unmapped number.

### Q: What does `id` print on an SELinux system, and what is `-Z` for?

The default output gains a `context=...` field — the process's SELinux
security context — and `-Z` prints only that context: the combination of
SELinux user, role, type, and MLS range that policy evaluates on every
access. It is the fastest way to answer "what label is this service running
as" when debugging AVC denials, and it doubles as a feature probe: on
non-SELinux kernels the option exits 1 with an explicit error rather than
printing something empty.

### Q: How do `id`, `groups`, and `whoami` overlap, and when would you pick each?

`id` is the superset: `whoami` is exactly `id -un` and `groups` is exactly
`id -Gn` for the current process. Pick the narrow tools for humans and
one-liners because the output needs no post-processing; pick `id` for
scripts because one invocation can produce any field (`-u`, `-g`, `-G`)
in either numeric or name form, supports the real-ID view via `-r`, the
SELinux context via `-Z`, and NUL-safe delimiting via `-z` — none of which
the narrower tools offer.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/id.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
