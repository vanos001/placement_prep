# pwck — verify the integrity of /etc/passwd and /etc/shadow

## Overview

`pwck` is the shadow suite's consistency checker for the user-account databases. It reads `/etc/passwd` and — when it exists or is given — `/etc/shadow`, verifies that every entry has the right shape and plausible data, reports anything the normal account tools would trip over, and, when run interactively as root, prompts to delete entries that cannot be repaired any other way. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/pwck`. Its group-side twin is `grpck`, which does the same job for `/etc/group` and `/etc/gshadow`.

Nothing in the day-to-day toolset calls pwck for you: `useradd`, `usermod`, and `passwd` all lock the files and write well-formed entries. You reach for pwck after something *else* has touched these files — a hand edit gone wrong, a provisioning script that appended garbage, a merge from a config-management tool, a full disk that truncated a write. It is also the tool of record for removing an entry so corrupt that `userdel` refuses to touch it, since the ordinary tools cannot parse, and therefore cannot alter, a broken line.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/pwck |
| First appeared | System V lineage (pwck ships with SVR-era Unix); carried by the shadow suite since the Julianne F. Haugh codebase (1988+) |
| Standards | Not POSIX; specified by LSB. Behavior partly configured via /etc/login.defs |

## Synopsis

```
pwck [options] [passwd [shadow]]
```

Common one-line forms:

```
pwck -r                                   # read-only audit of the live files
pwck -s                                   # sort /etc/passwd and /etc/shadow by UID
pwck -R /mnt/rootfs                       # check the account files of a mounted image
pwck /tmp/test-passwd /tmp/test-shadow    # check an arbitrary file pair
```

The two positional arguments are optional; when only `passwd` is given, the shadow side is checked against `/etc/shadow` if that file exists. Shadow-side checks are enabled whenever a shadow file is in play, which on any modern Debian system means always.

## How It Works

### The passwd-side check list

For each line of the password file, pwck verifies:

```
1. correct number of fields          7, colon-separated      FATAL
2. unique and valid user name        no dupes, sane charset   prompted
3. valid user identifier             numeric, plausible UID   warning
4. valid primary group               GID exists in /etc/group warning
5. valid home directory              path exists on disk      warning
6. valid login shell                 program exists           warning
```

Only the first two are treated as structural failures; the man page calls them fatal. A wrong field count means the entry cannot be parsed reliably, so pwck offers to delete the entire line and, if you refuse, skips the remaining checks for that entry. A duplicated user name is also offered for deletion, but the remaining checks still run. Everything else is a warning you are expected to fix with `usermod` — pwck repairs nothing except by deletion and sorting.

The GID check is why pwck's FILES list includes `/etc/group` even though you never pass it: the primary group of every user must resolve there, which makes pwck a crude cross-file checker too.

### The shadow-side check list

Shadow checks activate whenever a shadow file is consulted (the default on modern systems, or explicitly via the second argument):

```
1. pairing          every passwd entry has a matching shadow entry, and vice versa
2. placement        the password hash lives in the shadow file, not in passwd
3. shape            shadow entries have the correct number of fields (9)
4. uniqueness       no duplicate shadow entries for one name
5. sanity           the last-change date is not in the future
```

Unpaired entries are fixable inside pwck: a passwd row without a shadow row can get one generated (seeded from `PASS_MIN_DAYS`, `PASS_MAX_DAYS`, `PASS_WARN_AGE` in `/etc/login.defs`), and an orphaned shadow row can be deleted — both after an interactive prompt.

### A real repair session

The transcript below is from this container, with a deliberately corrupted copy of the password file (`badline` has only 2 fields; `z` has no shadow row):

```
$ pwck /tmp/pwtest /tmp/shtest
invalid password file entry
delete line 'badline:x:99999'? n
no matching password file entry in shtest
add user 'z' in shtest? n
pwck: no changes
$ echo $?
2
```

Three things to note: the deletion prompt names the exact offending line; declining a fatal repair bypasses that entry's remaining checks; and a declined session still exits 2 — "one or more bad password entries" — because the files are still bad. Answer `y` and the line is actually removed from the file (that is the only write pwck performs short of `-s`).

### Read-only vs interactive

```
terminal, root, no flags  -->  interactive: prompts, may rewrite files
-r / --read-only          -->  report only, never writes, never rewrites
stdin not a tty           -->  prompts still read from stdin (scriptable, dangerous)
```

`-r` is what you want in monitoring jobs and CI: pure audit, exit code as the signal. Without `-r`, prompts are read from stdin, so piping `yes` into pwck will happily delete every entry it asks about — the prompts are not tty-aware protection.

### Sorting

`-s` rewrites `/etc/passwd` and `/etc/shadow` sorted by UID (for shadow, by the UID of the matching passwd entry). `-r` and `-s` cannot be combined — one audits, the other rewrites. Sorting is cosmetic-to-moderately-useful: lookups in these files are done by name via NSS and are not order-sensitive, but sorted files make diffs and reviews sane after a migration.

### Alternate file pairs

The positional arguments exist so you can check candidate files *before* installing them:

```
cp /etc/passwd /tmp/p && cp /etc/shadow /tmp/s
# ...edit /tmp/p and /tmp/s or apply a script's changes...
pwck /tmp/p /tmp/s && {
    vipw        # or: install the files with correct ownership/perms
}
```

This is the safe pattern for hand edits: never validate against the live files, validate the copies, then move them in with `vipw` (which locks and re-checks).

```
                +----------------------+
   argv files?  |  /etc/passwd(+shadow)|
   ------------>+          |           |
                |    open both files    |
                +----------+------------+
                           v
                +----------------------+   bad field count ----> prompt delete
                |  per-entry checks    |--> duplicated name ----> prompt delete
                |  (passwd + shadow)   |--> other mismatch -----> warning only
                +----------+-----------+
                           v
              -s? rewrite sorted : -r? done : interactive prompts
```

### Pairing with grpck

pwck is deliberately half of a pair. `grpck` applies the same model — field counts, unique names, GID validity, gshadow pairing, interactive delete prompts, and the same `-r`/`-s` semantics — to `/etc/group` and `/etc/gshadow`, and shares pwck's exit-code table. Cleanup sessions conventionally run both: `pwck -r && grpck -r` as the audit sweep, then the interactive forms only against files you actually intend to repair. The converters share the same relationship (see the pwconv/pwunconv pages): their shared man page requires both checkers as pre-flight.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-r`, `--read-only` | Audit mode: report errors and warnings, change nothing. The flag for cron/CI. Cannot be combined with `-s`. |
| `-s`, `--sort` | Sort `/etc/passwd` and `/etc/shadow` by UID and rewrite them. Cannot be combined with `-r`. |
| `-q`, `--quiet` | Report errors only; suppress warnings that need no user action. |
| `-R`, `--root DIR` | Operate on `DIR/etc/passwd` and `DIR/etc/shadow`, using `DIR`'s login.defs. Absolute paths only. |
| `--badname` | Allow names that do not conform to standards. Deprecated in recent shadow releases (and spelled `--badnames` in some intermediates). |
| `passwd shadow` | Positional alternate files — the basis of the safe edit-and-validate workflow. |

## Usage Patterns

```bash
# Post-incident audit: did anything mangle the account files?
pwck -r

# CI/monitoring gate: exit 0 means files are structurally sound
pwck -r -q || echo "passwd/shadow integrity violation" | logger -t pwck-watch

# Validate a candidate file pair before installing it
cp /etc/passwd /tmp/p.new && cp /etc/shadow /tmp/s.new
$EDITOR /tmp/p.new /tmp/s.new
pwck /tmp/p.new /tmp/s.new

# Sort both files by UID after a bulk migration (root, tools idle)
pwck -s

# Remove an entry too corrupt for userdel (interactive, root)
pwck

# Check the account files of a chroot or mounted rootfs image
pwck -R /mnt/rootfs

# Quiet mode to see only findings that require action
pwck -r -q

# Pre-flight before shadow conversion (the man page's own BUGS advice)
pwck && pwconv

# Check against a group file mismatch you suspect after NIS-era cleanup
pwck -r /etc/passwd /etc/shadow && grep -F -f <(cut -d: -f4 /etc/passwd) \
    <(cut -d: -f1-3 /etc/group)

# Script the answer to prompts (know what you are doing — this deletes)
printf 'y\n' | pwck /tmp/pwtest /tmp/shtest

# Pair with the group-side checker in one sweep
pwck -r; grpck -r

# Confirm the audit passes after a repair (rc=0 is the pass signal)
pwck -r; echo "audit rc=$?"
```

## Nuances and Gotchas

- **You must be root.** `/etc/shadow` is mode `0640 root:shadow`; a non-root pwck cannot open it and exits 3:

  ```
  $ pwck -r /etc/passwd /etc/shadow
  pwck: cannot open /etc/shadow
  $ echo $?
  3
  ```

- **Exit 2 means "found problems", not "pwck crashed".** Scripts commonly treat any non-zero as infrastructure failure; for a file-integrity gate, zero-or-2 is normal operation and 3-6 is the real alert.
- **Prompts read stdin.** Piping answers (`yes | pwck`, `printf 'y\n' |`) deletes entries without review. Interactive repair is meant for a human at a terminal.
- **`-r` and `-s` are mutually exclusive.** One audits, one rewrites; combining them is a usage error (exit 1).
- **`--badname` is deprecated.** Recent shadow releases warn that nonconforming names are a legacy escape hatch; the correct fix is renaming the account with `usermod -l`.
- **pwck does not fix warnings.** Missing home directories, bad shells, unknown GIDs — all reported, none repaired. It only deletes fatal entries and sorts. The man page explicitly points you at `usermod` for everything else.
- **The home-directory check is existence only.** It will not notice wrong ownership or permissions on an existing directory; use `../../admin/permissions.md`-style audits for that. Intentionally homeless system accounts can be silenced by putting the `NONEXISTENT` keyword (configurable in `/etc/login.defs`) in the home field.
- **The shell check can false-positive under `-R`.** A chroot may not carry the shell binary; the entry is fine from inside the image, flagged from outside.
- **Sorting rewrites two of the most sensitive files on the system.** Run `pwck -s` only when no account tool is active; pwck takes the usual shadow-suite locks, but "nothing else is touching /etc/passwd" is the operator's responsibility during the rewrite.
- **Portability.** pwck is a shadow-suite tool: Linux via `passwd`/`shadow-utils` packages, not BSD (which has `pwd_mkdb` and a different world), and not in busybox-only minimal images.
- **No `--version`.** Unlike many suite members, pwck (4.17-era, as observed here) rejects `--version` with exit 1 — check the `passwd` package version instead.
- **Warning volume is a tuning problem.** Healthy systems still warn — intentionally homeless system accounts, vendor shells outside the chroot, `nologin` variants. `-q` exists for exactly this: decide which warnings matter, then let the audit script grep for the classes you page on, rather than treating every warning as an incident.

## Exit Status

Documented in the man page ("EXIT VALUES"):

| Code | Meaning |
| --- | --- |
| 0 | success — files consistent |
| 1 | invalid command syntax |
| 2 | one or more bad password entries |
| 3 | can't open password files (missing, or permissions — see the non-root example above) |
| 4 | can't lock password files |
| 5 | can't update password files |
| 6 | can't sort password files (`-s` failure) |

## Related Commands

- [`vipw`](./vipw.md) — the lock-protected editor for these files; its post-save sanity checks are the everyday version of pwck's rules.
- [`pwconv`](./pwconv.md) — conversion to shadowed passwords; its man-page BUGS section requires a clean `pwck` first.
- [`pwunconv`](./pwunconv.md) — the reverse conversion, equally dependent on intact input files.
- [`usermod`](./usermod.md) — the tool pwck itself recommends for fixing warning-level findings.
- [`useradd`](./useradd.md) — the normal writer of the entries pwck audits; its `-K` UID ranges mirror pwck's plausibility checks.
- [`chage`](./chage.md) — manages the shadow aging fields whose values pwck sanity-checks.
- [overview](./overview.md) — the shadow suite collection: where the checkers sit in the toolset.
- [users-groups](../../admin/users-groups.md) — the `/etc/passwd`, `/etc/shadow`, `/etc/group` data model behind these checks.

## Interview Questions

### Q: Which pwck findings are fatal, and what does "fatal" mean here?

Field count and user-name uniqueness. "Fatal" means the entry cannot be processed safely, so pwck prompts to delete the whole line — and if you decline, it bypasses the remaining checks for that entry. Everything else (bad UID, unknown GID, missing home, missing shell, unpaired shadow rows) is a warning: reported, counted in the exit status, but never auto-repaired.

### Q: You want a nightly integrity gate on /etc/passwd. Which flags and exit codes do you build on?

`pwck -r -q`: read-only so the job can never mutate the files, quiet so warnings that need no action do not page you. Exit 0 is healthy; exit 2 means findings — worth alerting on; 3-6 mean pwck itself could not run (open/lock/update/sort failure), which is a different, more urgent alert class. Never run the interactive mode unattended: prompts consume stdin, and a `yes |` accident deletes entries.

### Q: A coworker's sed script inserted a stray blank line into /etc/passwd. Walk through the recovery.

Do not edit the live file in place. Copy `/etc/passwd` and `/etc/shadow` to temp files, run `pwck /tmp/p /tmp/s` to enumerate the damage (a blank or short line is an "invalid password file entry" with a delete prompt), fix the copies, then install them via `vipw` — which takes the locks, re-checks, and writes atomically. Editing live files with arbitrary editors risks a concurrent `useradd` interleave and skips all validation.

### Q: Why does pwck need to read /etc/group when it only takes passwd and shadow arguments?

Because one of its checks is "valid primary group": the fourth passwd field must be a GID that resolves in `/etc/group`. After group cleanups or NIS decommissions, users with dangling primary GIDs are common, and every shadow-suite tool would misbehave for them. This makes pwck a de-facto cross-file checker between the user and group databases.

### Q: What does `pwck -s` actually do, and why is it rarely needed?

It rewrites `/etc/passwd` and `/etc/shadow` sorted by UID. NSS lookups and the shadow tools themselves are not order-sensitive, so sorting changes nothing functionally — it is hygiene for diffs, reviews, and legacy tooling that assumes order. It is rarely needed because entries are naturally appended in UID order on well-run systems, and it is occasionally unwanted because sorted-by-UID files reorder `system` accounts against local conventions.

### Q: What breaks if you run `pwck -s` at the same moment a package's configure script is calling useradd?

Nothing corrupt, but one of them waits or fails: pwck takes the same file locks as the rest of the suite before rewriting, so useradd gets a "cannot lock" failure (or vice versa — pwck exits 4, "can't lock password files"). The operation to reschedule is the *sort*, because it rewrites both files; a read-only `pwck -r` is safe to run at any time since it never takes an exclusive rewrite or blocks anyone. That asymmetry — audits anytime, rewrites only in maintenance windows — is the operational rule.

### Q: How does pwck treat shadow entries whose last-change date is in the future, and why does this happen?

It is a warning-level shadow check ("the last password changes are not in the future"). It typically happens after clock jumps, restored VMs/snapshots, or copy-pasting shadow rows between systems with different epoch assumptions. The data still parses, so no deletion is offered — but `chage -d` (or `passwd`) should reset the field, because aging logic computing "days until expiry" against a future date produces nonsense windows.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/pwck.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
