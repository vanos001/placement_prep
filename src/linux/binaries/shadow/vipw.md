# vipw — safely edit /etc/passwd (and friends) under lock

## Overview

`vipw` is the lock-protected editor for `/etc/passwd`. Instead of opening the live account file with a bare editor, `vipw` takes the shadow suite's locks, hands you a private copy in `$VISUAL`/`$EDITOR`/`vi`, and on save sanity-checks the result before it is moved into place — protecting you from corrupting the file and from racing a concurrent `useradd` or `passwd`. It ships in the `passwd` package and lives in `/usr/sbin/vipw`; with `-s` it edits `/etc/shadow`, and through its `vigr` variant (the same binary, reached via a symlink) it edits `/etc/group` and `/etc/gshadow`.

The problem it solves is old enough that 4.3BSD shipped the first vipw: account files are parsed by everything (login, NSS, PAM, cron), have no schema validator of their own, and are the single most embarrassing file to truncate on a production host. On Debian, resist the habit of reaching for util-linux's version — the file belongs to shadow's `passwd` package here (verified on this container: `/usr/sbin/vipw` is a real binary from `passwd`, and `/usr/sbin/vigr` is a symlink to it).

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/vipw |
| First appeared | 4.3BSD lineage (as the BSD vipw idiom); the shadow suite ships its own implementation on Linux |
| Standards | Not POSIX; a Unix sysadmin convention implemented by BSD util-linux and shadow alike |

## Synopsis

```
vipw [options]
vigr [options]
```

One-line forms for the main modes:

```
vipw            # edit /etc/passwd under lock, re-checked on save
vipw -s         # edit /etc/shadow instead
vigr            # edit /etc/group (same binary via symlink)
vigr -s         # edit /etc/gshadow
```

There are no file operands: the target is fixed by the mode flags, which is part of the safety model.

## How It Works

### The edit cycle

```
        +------------------------------------------+
        | 1. lock the target (e.g. /etc/passwd.lock)|
        |    refuses if another account tool holds it|
        +--------------------+---------------------+
                             v
        +------------------------------------------+
        | 2. copy the file to a private temp copy   |
        +--------------------+---------------------+
                             v
        +------------------------------------------+
        | 3. $VISUAL, else $EDITOR, else vi         |
        +--------------------+---------------------+
                             v
        +------------------------------------------+
        | 4. editor exits: check the result         |
        |    (duplicate names, malformed lines...)  |
        |    problems --> offered a re-edit, not    |
        |    a silently broken file                 |
        +--------------------+---------------------+
                             v
        +------------------------------------------+
        | 5. unchanged? "vipw: /etc/passwd is       |
        |    unchanged" and no rewrite.             |
        |    changed? atomic replace, then unlock   |
        +------------------------------------------+
```

The locking is visible in the binary's own diagnostics, which tell you exactly what it is guarding against: `Couldn't lock file`, `lock file already used (nlink: ...)`, `existing lock file ... without a PID`, `existing lock file ... with an invalid PID`, `lock ... already used by PID ...`. Locks are named after the target file (`/etc/passwd.lock` style), shared with the rest of the shadow suite, so `vipw` and `useradd` cannot interleave.

The post-edit check is the other half of the contract: when the editor exits, the program validates the edited content (its error text points you at `pwck`/`grpck` for what it finds, e.g. duplicate entries) and gives you the chance to re-edit rather than installing a broken file. A no-op session is detected too — exit the editor without changes and it reports `/etc/passwd is unchanged` and leaves the file untouched (both behaviors grounded on this container's shadow 4.17 build).

### Which file gets edited

The mode flags select among the four account databases; each pairs a public file with its shadowed twin:

| Flag | File edited | Pair used for checking |
| --- | --- | --- |
| (default) / `-p` | /etc/passwd | with /etc/shadow |
| `-s` | /etc/shadow | with /etc/passwd |
| `vigr` / `-g` | /etc/group | with /etc/gshadow |
| `vigr -s` (`-g -s`) | /etc/gshadow | with /etc/group |

Editing one half updates the consistency picture of the pair: that is why a save that breaks pairing is worth catching, and why the checkers (`pwck`, `grpck`) exist as the standalone form of the same validation.

### Editor selection

Documented in the man page: `$VISUAL` first, then `$EDITOR`, then the default `vi`. No quotes, no arguments — the value is treated as a single program name, so `EDITOR="code -w"`-style strings do not do what you hope.

### vigr: the symlink variant

On Debian, `vigr` is not a second binary but a symlink (`/usr/sbin/vigr -> vipw`, verified here). The program inspects how it was invoked (argv[0]) and defaults to the group database; everything else — locking, temp copy, editor selection, post-save checks — is identical. `vigr -s` is the everyday way to edit `/etc/gshadow` for group password or administrator changes that `gpasswd` cannot express.

### Two observable endpoints

The two behaviors you can demonstrate without even a root shell:

```
$ EDITOR=true vipw
vipw: Couldn't lock file: Permission denied
vipw: /etc/passwd is unchanged
$ echo $?
5
```

Non-root, the lock step fails (exit 5) before any editor starts. As root, the same "is unchanged" message is the no-op path — leave the editor without saving and nothing is rewritten. Between those endpoints sits the normal cycle: lock, private copy, edit, check, atomic replace, unlock.

### Stale-lock forensics

Lock files are ordinary files carrying the holder's PID, and the binary's diagnostics name the failure class precisely (grounded from this container's shadow 4.17 build):

```
existing lock file /etc/passwd.lock without a PID
existing lock file /etc/passwd.lock with an invalid PID '12345'
lock /etc/passwd.lock already used by PID 8123
```

Read them as a decision table: "without a PID" means an empty lock file, safe to remove; "invalid PID" means the holder is gone — verify with `ps`, then remove; "already used by PID" means a live writer — wait, do not touch. Recovery is just `rm` of the right file after the right check.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p`, `--passwd` | Edit the passwd database (the default; explicit for scripting clarity). |
| `-s`, `--shadow` | Edit the shadow (or gshadow, with `-g`) database. |
| `-g`, `--group` | Edit the group database (what `vigr` implies by its invocation name). |
| `-q`, `--quiet` | Quiet mode — suppress some of the chatter around locking/checking. |
| `-R`, `--root DIR` | Edit `DIR/etc/passwd` (etc.) using `DIR`'s configuration. Absolute paths only. |
| `-h`, `--help` | Display help and exit. |

## Usage Patterns

```bash
# The daily-driver: fix a typo'd shell for one account (root)
vipw

# Pick a saner editor than vi for one session
EDITOR=nano vipw
VISUAL=vim vipw -s

# Edit the shadow file directly — e.g. paste a pre-computed hash for bulk seeding
vipw -s

# Group maintenance: add members in bulk faster than repeated gpasswd -a
vigr
vigr -s          # gshadow: group admins and group password hashes

# Edit the account files of a mounted image or chroot
vipw -R /mnt/rootfs

# Validate without editing (pairs with pwck for a full sweep)
pwck -r && grpck -r

# The "who is holding the lock?" debugging step
ls -l /etc/passwd.lock /etc/shadow.lock 2>/dev/null

# Recover from a crashed session's stale lock (shadow tools store the holder PID)
cat /etc/passwd.lock 2>/dev/null && rm -f /etc/passwd.lock

# Confirm your changes landed and nothing else moved
vipw && diff <(getent passwd) <(cat /etc/passwd)

# Smoke-test lock acquisition without editing anything (root)
EDITOR=true vipw   # acquires lock, runs true, reports "is unchanged"

# Confirm what the vigr name actually resolves to on this host
readlink -f "$(command -v vigr)"

# Which implementation do I have? Flag sets differ between shadow and util-linux
dpkg -S "$(readlink -f "$(command -v vipw)")"

# Guard a scripted edit: refuse to run if the locks are already held
test ! -e /etc/passwd.lock && test ! -e /etc/shadow.lock || {
    echo "account files locked, retry later" >&2; exit 1; }
```

## Nuances and Gotchas

- **Root required.** Without root the lock step fails before any editor starts (observed on this container, exit 5):

  ```
  $ EDITOR=true vipw
  vipw: Couldn't lock file: Permission denied
  vipw: /etc/passwd is unchanged
  ```

- **`EDITOR` is a program name, not a command line.** `EDITOR="vim -X"` is not honored as two words; export a wrapper script if you need arguments. Order matters: `VISUAL` beats `EDITOR` beats `vi` — a `VISUAL` set for other tools silently overrides your intended vipw editor.
- **You are editing a copy.** Changes only land when the editor exits cleanly and checks pass. Killing the editor or the session leaves the live file untouched (plus, in crashes, possibly a stale lock — see below).
- **Stale locks.** A killed vipw can leave `*.lock` behind; subsequent account tools then refuse with "lock already used". The lock file conventionally holds the holder's PID, so check it before removing (`cat /etc/passwd.lock`, confirm the PID is gone, then `rm`).
- **Concurrent editing is refused, not queued.** "Cannot lock" means come back later — there is no waiting, by design: two interactive editors of `/etc/passwd` is a merge conflict nobody wants.
- **Field discipline is on you.** vipw protects structure (it catches broken/duplicated entries on save) but not semantics: a validly-formatted wrong UID still passes. The real validators are `pwck`/`grpck`; run them after substantive edits.
- **`vipw -s` skips the hash-format safety rails.** `passwd`/`chage` validate hash formats; direct shadow editing accepts whatever string you paste — including one with a colon in it, which silently splits the field. Use `passwd -e`, `chage`, or `usermod -p` when a tool exists for the change.
- **Debian location trivia that bites scripts.** It is `/usr/sbin/vipw` (root's PATH), not `/usr/bin`; and `vigr` is a symlink, so `readlink -f $(command -v vigr)` resolves to the vipw binary — relevant when hardening tools whitelist exact paths.
- **Other implementations exist.** util-linux ships its own vipw/vigr upstream; on Debian the installed one is shadow's (the `passwd` package owns the file). Flag sets differ slightly between implementations, so `--help` on the local binary beats memory when porting scripts.
- **No `--version`.** As with the rest of the suite's small tools (verified here), version questions go to the package, not the binary.
- **`-p` exists for explicitness.** The default already edits passwd; `-p` is documentation-in-argv for scripts. The full dispatch matrix is {default, `-p`} × {`-s`} and {`-g`} × {`-s`} — and `-g -s` together is how you reach gshadow explicitly without the vigr name.
- **Locks are per-database.** `/etc/passwd.lock` guards passwd edits and `/etc/shadow.lock` guards shadow edits, so `vipw` and `vipw -s` can run concurrently by design. Pair consistency, however, is your problem: a passwd edit that unbalances the pair is only caught at check time (by vipw's save check or by `pwck`).
- **The staging file lives in /etc, not /tmp.** The private copy is made alongside the target (the npasswd-style staging the converters also use), so it inherits /etc's filesystem and permissions rather than whatever is mounted on /tmp — one more reason the tool survives odd /tmp setups (noexec, tmpfs eviction) that would break a /tmp-based editor workflow.

## Exit Status

No exit-status table is documented in the man page. In practice:

- `0` — edit completed (including the unchanged-file no-op path).
- non-zero — lock acquisition failure (5, observed as non-root here), editor/abort failures, or invalid usage.

For scripts, prefer the dedicated tools (`usermod`, `chage`, `gpasswd`) over scripted vipw runs; vipw's value is the interactive loop, not automation.

## Related Commands

- [`pwck`](./pwck.md) — the standalone checker whose rules vipw applies on save; run it after substantive edits.
- [`pwconv`](./pwconv.md) — reconciles the passwd/shadow pair you may have just unbalanced by hand.
- [`pwunconv`](./pwunconv.md) — the (rare) state in which `vipw -s` has nothing left to edit.
- [`usermod`](./usermod.md) — the scriptable, validated alternative to editing passwd by hand.
- [`passwd`](./passwd.md) — the right tool for the most common shadow-field edit (the hash).
- [`gpasswd`](./gpasswd.md) — the right tool for most `/etc/group` and `/etc/gshadow` changes that `vigr` would otherwise be used for.
- [overview](./overview.md) — the shadow suite collection: editors, checkers, and converters as one family.
- [users-groups](../../admin/users-groups.md) — the four-file data model vipw edits under lock.

## Interview Questions

### Q: Why does vipw exist when any editor can open /etc/passwd?

Because the failure modes of naive editing are catastrophic and structural: the file is parsed by everything on the system, has no transactional writer of its own, and is hot — `useradd`, `passwd`, and friends rewrite it concurrently. vipw serializes against those writers via the shared shadow-suite locks, edits a copy rather than the live file, and re-checks the result before installing it, so a typo'd save is caught instead of deployed. It is the same argument as `visudo` for `/etc/sudoers`: the lock plus the validation loop is the product, not the editor.

### Q: Which editor wins if VISUAL, EDITOR, and the default are all set, and what is the classic mistake here?

The order is `VISUAL`, then `EDITOR`, then `vi` (documented in the man page). The classic mistake is a `VISUAL` inherited from the environment silently overriding the `EDITOR=nano` the admin intended — or treating the variable as a command line with arguments, which it is not; it is a single program name. Wrapper scripts are the reliable way to pass flags.

### Q: What is the relationship between vipw and vigr on a Debian system?

One binary, two names: `/usr/sbin/vigr` is a symlink to `vipw`, and the program dispatches on how it was invoked — `vigr` defaults to `/etc/group`, `vipw` to `/etc/passwd`, with `-s` selecting the shadowed twin of either (`/etc/shadow`, `/etc/gshadow`). Locking, temp-copy editing, editor selection, and post-save checks are identical. The consequence for tooling is that capabilities and file ownership apply to both names at once.

### Q: A crashed vipw session left the account tools refusing to run. What happened and how do you recover?

The kill left a stale lock file (`/etc/passwd.lock` or the shadow/group equivalent). Every shadow-suite tool that writes the same file honors the same locks, so `useradd` et al. now report "cannot lock". The lock file records the holder's PID: verify that process is really gone (`cat /etc/passwd.lock`, check with `ps`), then remove the lock file. The verification step matters — deleting the lock of a *live* writer reintroduces exactly the corruption vipw exists to prevent.

### Q: How does vipw's design compare to visudo, and where does the analogy break down?

The same three-part product: serialize writers with a lock, edit a copy instead of the live file, validate and install atomically. Both protect a root-owned file consumed by privileged parsers, and both beat a bare editor for exactly those reasons. The analogy stops at validation depth: visudo parses the sudoers grammar completely and even offers a check-only mode (`visudo -c`), while vipw's save check is structural — malformed or duplicated entries — not semantic, and the pure-checking role is delegated to the separate `pwck`/`grpck` tools. So the pairing on a Debian system is vipw-plus-pwck, where sudoers gets everything from visudo alone.

### Q: When is editing /etc/shadow with vipw -s justified over passwd or chage — and what are the risks?

Justified for bulk seed operations no tool expresses well: installing pre-computed hashes for a batch of accounts, or repairing a shadow row after a bad migration. The risks are that you bypass every safety rail — no hash-format validation (a pasted string containing a colon silently corrupts the field split), no aging-policy helper, and no audit trail like `chage`'s. The professional pattern is `vipw -s` followed immediately by `pwck -r` (and `chage -l` spot checks), keeping the edit and the validation as two deliberate steps.

### Q: Why does vipw refuse a second concurrent invocation instead of waiting for the lock?

Because the contention is between two *interactive* sessions, and there is no meaningful way to serialize a merge: whoever edited second would silently discard or clobber the first editor's work the moment they save. Fail-fast with a precise diagnostic ("cannot lock", sometimes naming the holder PID) forces a human decision, unlike the non-interactive tools — pwconv and friends print "try again later" and are safe to retry in a loop precisely because their rewrite is mechanical and lossless. Same lock, different contention model.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/vipw.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
