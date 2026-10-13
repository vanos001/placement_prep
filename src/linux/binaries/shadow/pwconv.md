# pwconv — enable shadowed passwords (move hashes into /etc/shadow)

## Overview

`pwconv` converts the password database to "shadowed" form: it creates or repairs `/etc/shadow` from `/etc/passwd`, moves every password hash into the shadow file, and replaces each hash in `/etc/passwd` with the placeholder `x`. It ships in the `passwd` package and lives in `/usr/sbin/pwconv` — a root-only maintenance tool, not an interactive command. Its man page documents four commands at once: `pwconv`, `pwunconv`, `grpconv`, and `grpunconv`, the convert-to/convert-from pair for both the user and the group database.

On any Debian system built in the last two decades `/etc/shadow` already exists, so pwconv's everyday role is not initial conversion but *repair and reconciliation*: if someone hand-edited `/etc/passwd` and typed a hash into the password field, or a migration script added users without shadow rows, `pwconv` brings the shadow file back in sync. It is idempotent — running it on a consistent system changes nothing.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/pwconv |
| First appeared | System V lineage (pwconv is an SVR-era tool); part of the shadow suite since the Julianne F. Haugh codebase (1988+) |
| Standards | Not POSIX; specified by LSB. Behavior partly configured via /etc/login.defs |

## Synopsis

```
pwconv [options]
pwunconv [options]
grpconv [options]
grpunconv [options]
```

One-line forms for the modes covered by this page:

```
pwconv              # create/repair /etc/shadow, hash fields in passwd become x
pwunconv            # merge /etc/shadow back into /etc/passwd, then remove shadow
pwconv -R /mnt/img  # convert the account files of a chroot or mounted image
```

`pwconv` takes no operands. Everything it does is defined by the contents of the two files and `/etc/login.defs`.

## How It Works

### The conversion algorithm

The man page describes pwconv and grpconv with the same four steps (pwconv shown; substitute group/gshadow for grpconv):

```
step 1: entries in the shadow file with NO matching passwd entry are REMOVED
step 2: entries whose passwd password field is NOT 'x' are pushed into shadow
        (an existing shadow row for that user is UPDATED from passwd)
step 3: passwd entries with no shadow row get one ADDED
step 4: every password field in /etc/passwd is replaced with 'x'
```

Step 2 is the reconciliation case: a hash typed directly into `/etc/passwd` is authoritative for one run and gets relocated. Steps 3-4 are the initial-conversion case: every user gets a shadow row, and the passwd field becomes the universal `x` placeholder that tells NSS and PAM "the real hash is in the shadow file".

New shadow rows from step 3 are seeded from `/etc/login.defs`:

```
$ grep -E '^(PASS_)' /etc/login.defs
PASS_MAX_DAYS   99999
PASS_MIN_DAYS   0
PASS_WARN_AGE   7
```

The encrypted-password value carried over is whatever stood in `/etc/passwd`; only the aging fields (last change, min, max, warn) come from login.defs defaults.

### A worked conversion

Before — the state pwconv exists to fix: one hash pasted directly into passwd by a script, one user with no shadow row at all:

```
# /etc/passwd
root:x:0:0:root:/root:/bin/bash
svc:$y$j9T$abc...:990:990::/var/lib/svc:/usr/sbin/nologin   <- hash, not x
new:x:1001:1001::/home/new:/bin/bash                        <- no shadow row

# /etc/shadow
root:!:19900:0:99999:7:::
```

After `pwconv`:

```
# /etc/passwd — every hash field back to the x placeholder
root:x:0:0:root:/root:/bin/bash
svc:x:990:990::/var/lib/svc:/usr/sbin/nologin
new:x:1001:1001::/home/new:/bin/bash

# /etc/shadow — svc's hash relocated; new gets a row seeded from login.defs
root:!:19900:0:99999:7:::
svc:$y$j9T$abc...:19900:0:99999:7:::
new:!:19900:0:99999:7:::
```

Step 1 also ran here: any shadow row for a user absent from passwd (not shown) was deleted before any of the above. Note the precedence rule step 2 embodies — when passwd and shadow disagree about a hash, *passwd wins for that one run*; the file you hand-edited is treated as the source of truth and then neutralized.

### Temp files, locks, and the atomic swap

The conversion is transactional rather than in-place. The tool takes the standard shadow-suite locks (`/etc/passwd.lock`-style lock files, the same mechanism `vipw` uses), builds the new password and shadow files under temporary names in `/etc` — historically documented as `/etc/npasswd` and `/etc/nshadow` — validates them, and renames them into place. A pre-conversion backup of the password file is kept as `/etc/passwd-` (the dash-suffix convention you see after any shadow-suite rewrite; the binary manages it directly). If the tool dies mid-flight, the worst case is leftover temp/lock files, not a half-merged password file.

```
   /etc/passwd ----+                        +--> /etc/passwd-   (backup)
   /etc/shadow ----+--> [locks] --> temp    |
        |                  npasswd ------+--> /etc/passwd    (fields = x)
        |                  nshadow ------+--> /etc/shadow    (hashes)
   login.defs ---------------------------+    (PASS_* seeds for new rows)
```

### Idempotency

Run pwconv twice and the second run is a no-op: after step 4 no passwd field differs from `x`, every user has a shadow row, and steps 1-2 find nothing to do. This makes it safe to sprinkle into provisioning scripts as "make sure shadow is on and consistent" without idempotence wrappers.

### The four-way family

| Command | Direction | Files |
| --- | --- | --- |
| `pwconv` | passwd → shadow | /etc/passwd, /etc/shadow |
| `pwunconv` | shadow → passwd (then removes shadow) | /etc/passwd, /etc/shadow |
| `grpconv` | group → gshadow | /etc/group, /etc/gshadow |
| `grpunconv` | gshadow → group (then removes gshadow) | /etc/group, /etc/gshadow |

Systems conventionally run both conv commands: `pwconv && grpconv`. The group pair exists for the same reason as the user pair — `/etc/group` is world-readable, so group password hashes and (via gshadow) group administrator lists must be hidden too.

### Run it clean: the BUGS section

The man page's BUGS note is unusually blunt: errors in the password file (invalid or duplicate entries) "may cause these programs to loop forever or fail in other strange ways". The prescribed remedy is to run `pwck` and `grpck` before converting. A conversion over a corrupt input is the one scenario where this simple tool can make a mess, because it rewrites both files wholesale.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Display help and exit. |
| `-R`, `--root DIR` | Convert `DIR/etc/passwd` and `DIR/etc/shadow` using `DIR`'s configuration. Absolute paths only. |

That is the entire flag surface. There is no dry-run option: to preview, work on copies (`pwconv -R` against a prepared directory, or copy the file pair elsewhere and convert there).

## Usage Patterns

```bash
# Reconcile after a hand edit put a hash in /etc/passwd (root)
pwconv && grep -c ':x:' /etc/passwd

# Make sure a provisioned image has shadow enabled and consistent
pwconv && grpconv

# Sanity-gate the conversion, per the man page's BUGS advice
pwck -r && grpck -r && pwconv && grpconv

# Preview the conversion on copies before touching the live system
mkdir -p /tmp/conv/etc && cp /etc/passwd /etc/shadow /tmp/conv/etc/
cp /etc/login.defs /tmp/conv/etc/
pwconv -R /tmp/conv

# Verify the placeholder landed everywhere (only 'x' or special fields remain)
pwconv
awk -F: '$2 != "x" && $2 != "*" && $2 != "!" {print $1}' /etc/passwd

# Confirm the hash really moved (root view)
getent shadow z | cut -d: -f1-2

# Check the dash-suffix backup that the rewrite leaves behind
ls -l /etc/passwd /etc/passwd-

# Convert the account files of a mounted container image
pwconv -R /mnt/rootfs && grpconv -R /mnt/rootfs

# Confirm idempotency: second run must change nothing
md5sum /etc/passwd /etc/shadow; pwconv; md5sum /etc/passwd /etc/shadow

# Backup posture before a bulk reconcile — pwconv keeps dash-suffix backups,
# but an explicit dated copy beats reconstructing intent later
cp -a /etc/passwd /etc/shadow /root/pre-pwconv-$(date +%F)/

# The 'is shadow actually on' property that pwconv guarantees
awk -F: '$2 != "x" {print "not shadowed: " $1}' /etc/passwd

# Check what the tool preserved from before its rewrite
ls -l /etc/passwd /etc/passwd- && diff /etc/passwd- /etc/passwd
```

The `getent shadow` pattern is the everyday post-conversion check: user `z`'s second field should now hold the real hash (this container's shadow file is root-only, hence the root shell requirement), while `getent passwd z` shows `z:x:...`.

## Nuances and Gotchas

- **Non-root failure looks like lock contention.** Without root you get a permission error and a lock complaint, exit 5 (observed on this container):

  ```
  $ pwconv
  pwconv: Permission denied.
  pwconv: cannot lock /etc/passwd; try again later.
  $ echo $?
  5
  ```

- **Run pwck first.** The BUGS note is not decoration: duplicate or malformed entries can send the converter into a loop or produce strange failures. `pwck -r && pwconv` is the professional form.
- **Step 1 deletes.** Shadow rows for users that no longer exist in `/etc/passwd` are silently removed during conversion. If you keep shadow-only archives of deleted accounts in `/etc/shadow`, pwconv will clean them out — back the file up first.
- **Aging fields are re-seeded, not preserved, for newly created rows.** A user getting a fresh shadow row from pwconv inherits `PASS_MIN_DAYS`/`PASS_MAX_DAYS`/`PASS_WARN_AGE` defaults, not any per-user policy that previously lived only in someone's notes. Check with `chage -l` after bulk conversions.
- **`x` is a convention enforced by NSS/PAM, not by file format.** If you remove the placeholder and put a hash back into `/etc/passwd` (the pwunconv state), authentication still works — which is exactly why `pwunconv` exists. The files never validate field 2 against a schema.
- **No dry run.** There is no `--dry-run`/`--diff`; preview via `cp` + `-R` as shown above.
- **Orphan handling is asymmetric.** pwconv removes passwd-less shadow rows, but passwd rows always survive. If a user appears in passwd with no shadow row *and* no password intended, the new row is created locked-empty per the hash carried over — verify special accounts (`*`, `!`) afterwards rather than assuming.
- **Conversion is system-wide and instantaneous.** There is no per-user shadow enablement. Scripts that "convert one user" with pwconv are really just relying on its reconcile step.
- **NIS-era `+`/`-` lines.** Historical `/etc/passwd` files with NIS inclusion markers (`+:*::...`) confuse the field-based rewrite; systems still using compat-NIS should convert after removing those lines.
- **The dash-suffix backup is per rewrite, not a history.** `/etc/passwd-` holds the pre-conversion state of the *most recent* shadow-suite rewrite, whatever tool did it. It is an undo aid, not an archive.
- **File modes are the tool's business.** After conversion, `/etc/shadow` must be `0640 root:shadow` (this container's actual mode). If your converter run produced anything else on a non-Debian layout, fix the mode before PAM touches the file — but never loosen it by hand out of convenience.
- **grpconv has one extra knob.** `MAX_MEMBERS_PER_GROUP` in login.defs controls the split-group line-splitting behavior shared by the group pair; the user pair has no equivalent because passwd lines are short by construction.

## Exit Status

The man page documents no exit-status table for the converter family (unlike `pwck`). In practice, on shadow 4.13-4.17 as shipped in Debian:

- `0` — success (including the successful no-op case).
- non-zero — any failure to open, lock, read, or write the files. A non-root invocation that cannot lock `/etc/passwd` exits **5** (observed here).

Treat anything non-zero as "conversion did not happen" and check `ls -l /etc/passwd*` plus the lock files before retrying.

## Related Commands

- [`pwunconv`](./pwunconv.md) — the exact inverse: merge shadow back into passwd and remove the shadow file.
- [`pwck`](./pwck.md) — the pre-flight validator the man page requires before any conversion.
- [`vipw`](./vipw.md) — the locked editor; the hand edits that make pwconv's reconcile step necessary usually start here.
- [`useradd`](./useradd.md) — writes shadow rows directly with the same login.defs seeds pwconv uses.
- [`chage`](./chage.md) — inspect the aging fields pwconv seeded on newly created shadow rows.
- [`passwd`](./passwd.md) — the everyday writer of the hashes pwconv relocates.
- [overview](./overview.md) — the shadow suite collection: the conv quartet in context.
- [users-groups](../../admin/users-groups.md) — why hashes belong in a root-only file: the data-model view.

## Interview Questions

### Q: What does the `x` in /etc/passwd's password field actually mean?

It is a placeholder meaning "the hash lives in the shadow database" — a convention implemented by glibc's NSS and PAM's pam_unix, not a magic value parsed by the file format. Anything not `x` in that field is treated as a literal password hash (which is how pre-shadow Unix and pwunconv-converted systems work). Special values like `*` or `!` mean locked. That dual reading is why pwconv can move hashes around without any daemon restart.

### Q: Why would you run pwconv on a system where /etc/shadow has existed for years?

For reconciliation. Step 2 of its algorithm finds passwd entries whose password field is not `x` — for example after a hand edit or a script that wrote a hash directly into `/etc/passwd` — and relocates those hashes into shadow, then re-establishes the placeholder. Step 1 removes orphaned shadow rows, and step 3 adds missing ones. It is the idempotent "make the pair consistent again" tool.

### Q: The man page says corrupt files can make pwconv loop forever. How do you defend against that?

Gate every conversion with `pwck -r` (and `grpck -r` for the group pair) and require exit 0 first. pwck's whole job is enumerating exactly the malformed or duplicate entries that break the converter's paired-file scan. The belt-and-braces version converts a copy of the file pair via `pwconv -R` on a prepared directory before touching the live files.

### Q: What is lost or changed when pwconv creates a brand-new shadow row for an existing user?

The hash carries over unchanged from the passwd field, but the aging fields are seeded from `/etc/login.defs` — `PASS_MIN_DAYS`, `PASS_MAX_DAYS`, `PASS_WARN_AGE` — rather than recovered from anywhere, because there was nowhere to recover them from. So a user who previously had no shadow entry gets default aging policy in one stroke, which may suddenly make a long-ignored password subject to `PASS_MAX_DAYS`. Auditing with `chage -l` after a bulk conversion is standard practice.

### Q: When passwd and shadow disagree about a user's hash, which one does pwconv believe, and why?

The passwd file, for that one run. Step 2 of the algorithm updates the shadow entry from any passwd row whose password field is not `x` — the reasoning is that the shadowed state is defined by the placeholder, so a non-`x` passwd field is by definition a fresh edit that has not yet been reconciled, and the only safe reading is that it supersedes the stale shadow row. Once absorbed, the passwd field is reset to `x`, and the disagreement window closes. This is also why hand-editing hashes into passwd is both dangerous and effective: pwconv will faithfully relocate whatever you typed.

### Q: Which of the four commands sharing pwconv's man page are idempotent, which are destructive, and how does that split affect scripting?

The conv pair (pwconv, grpconv) is idempotent: run twice, the second run is a no-op, so scripts can invoke them unconditionally as "ensure shadow is on". The unconv pair (pwunconv, grpunconv) is destructive and lossy: it removes the shadow/gshadow file outright and drops the aging fields that have no home in the public files — running it twice just fails the second time (nothing left to merge), and running it once is already a policy decision. That asymmetry is why hardening scripts call the conv pair freely but the unconv pair is essentially always a manual, backed-up, scheduled-maintenance action.

### Q: Walk through what happens on disk when pwconv runs on an already-consistent system.

It takes the locks, builds the temp files (the npasswd/nshadow-style staging names), and during staging discovers that every passwd password field is already `x`, every user already has a shadow row, and no orphan rows exist. The staged files are therefore identical to the live ones; they are renamed into place — same content, and the dash-suffix backups are refreshed to the pre-run state. The observable result is exit 0 with unchanged checksums (the md5sum-before/after check in the patterns above), which is precisely what makes the tool safe to call from provisioning code.

### Q: Why does pwconv seed new shadow rows from login.defs instead of leaving those fields empty?

Because the shadow format's aging fields are positional — a row must have all nine fields to parse consistently — and policy defaults have to come from somewhere. `PASS_MIN_DAYS`, `PASS_MAX_DAYS`, and `PASS_WARN_AGE` are the same seeds `useradd` uses, so a row created by pwconv is indistinguishable from one created by normal provisioning. Empty fields would technically parse, but they would mean "no policy recorded", silently disabling expiry accounting — seeding is the safer default, at the cost of applying today's defaults to accounts that never asked for them.

### Q: Compare pwconv's temp-file-and-rename approach with just running sed on /etc/passwd.

pwconv locks both files, builds new ones under temporary names, validates, and renames atomically, leaving a dash-suffix backup — so a crash mid-operation cannot leave a half-rewritten password file, and concurrent account tools are blocked for the duration. An in-place sed has no lock, no backup, no validation, and no atomicity: a concurrent `useradd` can interleave and lose entries, and a bad expression truncates the live file. The conversion tools are also the only writers that understand shadow semantics (the four-step reconcile), which no sed one-liner reimplements correctly.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/pwconv.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
