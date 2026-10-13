# newusers — batch-create and update users from passwd-format input

## Overview

`newusers` is the shadow suite's batch tool: it reads lines in `/etc/passwd` format — `pw_name:pw_passwd:pw_uid:pw_gid:pw_gecos:pw_dir:pw_shell` — and creates or updates one account per line, writing all four databases (`/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/gshadow`) under the usual locks. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/newusers`, and its man page states its niche plainly: "intended to be used in a large system environment where many accounts are created at a single time."

It is dangerous by design in two directions. The input carries **plaintext passwords** (the tool's defining feature: it encrypts them for you), and a line whose name matches an existing account **updates** that account — shell, home, GECOS, password — rather than failing. It is often confused with `chpasswd` (passwords only, no account creation), with a `useradd` loop (explicit flags, no plaintext file, but one lock round-trip per user and no built-in password handling), and with `adduser` (interactive, one at a time). For provisioning at scale, newusers is the single-command primitive; for everything smaller, it is usually the wrong amount of gun.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/newusers |
| First appeared | shadow suite (Julianne F. Haugh, 1988+); batch updater since the early shadow releases |
| Standards | Not POSIX. Reads /etc/login.defs extensively; PAM-aware on Debian builds |

## Synopsis

```
newusers [options] [file]
```

With no `file`, it reads standard input — which makes it pipeline-friendly and history-file-unfriendly at the same time. Common forms:

```
newusers batch.txt                    # file of passwd-format lines
gen-accounts | newusers               # stdin: generated rosters
newusers -r service-accounts.txt      # system accounts (SYS_UID range)
newusers -R /mnt/rootfs batch.txt     # operate on an image's tree
```

## How It Works

### The input line, field by field

Each line is passwd(5)-shaped, but several fields have batch-specific semantics (this is where the tool's real documentation lives):

```
pw_name   new account, OR an existing one -> that account is UPDATED
pw_passwd PLAINTEXT - newusers encrypts it (crypt(3) via the configured method)
pw_uid    empty   -> next free UID from UID_MIN (SYS range with -r)
          number  -> used as-is
          username-> that user's UID (clone-by-name)
pw_gid    group name (exists)      -> its GID
          group name (missing)     -> group is created, GID auto-picked
          number                   -> used as GID; if unused, a group named
                                      after the user is created with it
          empty                    -> namesake group created (auto GID)
pw_gecos  copied verbatim
pw_dir    created if missing (owned by user+primary group) - but NOT the
          parent directories; failure is non-fatal (stderr, batch continues)
          changing it for an existing user does NOT move the old content
pw_shell  copied verbatim - NO checks (typo a shell and login breaks)
```

The `pw_gid` column is quietly powerful: it is a *group declarer*. A batch file can reference groups that do not exist yet and newusers will create them with auto-picked GIDs, which is why well-formed batches often need no preceding groupadd run at all.

### Two passes, and what is transactional

The man page describes the execution model precisely, and it matters for failure analysis:

```
        batch file
            |
      parse + validate all lines
            |
   PASS 1: create/update users in the databases
           - new users get a LOCKED password ('!')
           - existing users' password fields are not touched yet
           - db writes are transactional: an error here commits NOTHING
            |
   PASS 2: passwords, through PAM (service /etc/pam.d/newusers)
           - plaintext from the line is encrypted and installed
           - a failure here is reported but does NOT stop the batch
            |
        done (exit status reflects the aggregate)
```

So the database side is all-or-nothing, while the password side is best-effort. A batch that "succeeded" may still have left some users locked (check for `!` in shadow); a batch that failed in pass 1 changed nothing at all.

### Password encryption and its moving parts

The plaintext in `pw_passwd` is encrypted with the system's configured method — on modern Debian, yescrypt via libcrypt defaults, historically driven by `ENCRYPT_METHOD` in login.defs. Bookworm's newusers additionally exposed `-c/--crypt-method METHOD` (DES, MD5, NONE, SHA256, SHA512) and `-s/--sha-rounds`; recent shadow releases removed both options (verified on this writing container's 4.17-era build, whose help offers only `-b`, `-h`, `-r`, `-R`) — scripts that pin a method must gate on the release, and `NONE` should never leave test labs (it writes the plaintext into shadow, which is at least mode 0640 — but don't).

### Configuration knobs that matter

From login.defs: `UID_MIN/UID_MAX` and `SYS_UID_MIN/SYS_UID_MAX` for UID selection, the GID counterparts for implicit group creation, `HOME_MODE` (else `UMASK`) for the mode of created home directories, `PASS_MAX_DAYS/PASS_MIN_DAYS/PASS_WARN_AGE` for the aging fields of created users, and `SUB_UID_*/SUB_GID_*` — if `/etc/subuid` exists, each created user gets subordinate ID allocations exactly like `useradd` gives. In other words: newusers is not a simplified useradd; it is useradd's machinery driven from a file.

## Options That Matter

| Option | Effect |
| --- | --- |
| `file` | Input operand; passwd-format lines. Omitted or `-`: standard input |
| `-r` | Create *system* accounts: UIDs/GIDs from the SYS ranges, no password aging written to shadow |
| `-R DIR` | Chroot into DIR and operate on its account databases (image builds) |
| `--badname` | Allow names failing the standard checks (deprecated; going away) |
| `-c METHOD` / `-s ROUNDS` | Bookworm-era: force crypt method / SHA rounds — **removed in recent shadow** |

## Usage Patterns

```bash
# Ten accounts from a here-doc (stdin form; no file ever touches disk)
newusers <<'EOF'
u01:Init!Pass1::::/home/u01:/bin/bash
u02:Init!Pass2::::/home/u02:/bin/bash
EOF
```

```bash
# The same as a file - which must be protected (mode 600) and shredded after
umask 077 && vi batch.txt && newusers batch.txt && shred -u batch.txt
```

```bash
# Classroom batch: implicit groups (empty gid column) + explicit homes
awk -F, '{print $1":ChangeMe!"$"::::/home/"$1":/bin/bash"}' roster.csv > /tmp/b
newusers /tmp/b
```

```bash
# Service accounts in one shot: system range, no aging, nologin shells
newusers -r <<'EOF'
svc-web:*::::::/usr/sbin/nologin
svc-db:*::::::/usr/sbin/nologin
EOF
```

```bash
# Pin UIDs to match a golden host (numbers must match across NFS clients)
newusers <<'EOF'
alice:PW::1501::::/home/alice:/bin/bash
bob:PW::1502::::/home/bob:/bin/bash
EOF
```

```bash
# Reuse an existing user's UID by name (clone-uid pattern for shared access)
newusers <<'EOF'
deploy-alias:PW:deploy::::/srv/deploy:/usr/sbin/nologin
EOF
```

```bash
# Declare teams: missing groups in the gid column get created automatically
newusers <<'EOF'
carol:PW::developers::::/home/carol:/bin/bash
dave:PW::developers::::/home/dave:/bin/bash
EOF
```

```bash
# Update existing users in bulk: same file shape, names must match exactly
newusers <<'EOF'
alice:NewPw!:::Alice Anderson:/home/alice:/bin/zsh
EOF
```

```bash
# Image build: populate the staging tree's accounts, not the running system
newusers -R /mnt/rootfs -r < service-accounts.txt
```

```bash
# Verify the batch afterwards: users, primaries, locks - all in one view
getent passwd alice bob u01 | cut -d: -f1,3,4
sudo getent shadow alice u01 | cut -d: -f1,2 | cut -c1-12
```

```bash
# Rotate passwords for a whole roster (update semantics: name match = update)
genpasswords roster.txt | awk -F: '{print $1":"$2":::::"}' | newusers
```

```bash
# Failed pass-1 diagnosis: nothing committed - re-run after fixing the line
newusers batch.txt || { echo "nothing committed (transactional)"; exit 1; }
```

```bash
# Dry-run the shape of the batch: names/groups that WOULD be touched
awk -F: '{print "user=" $1, "uid=" ($3=="" ? "auto" : $3), \
          "gid=" ($4=="" ? "auto" : $4), "home=" $6}' batch.txt
```

## Nuances and Gotchas

- **The input file is a plaintext password store.** The man page's CAVEATS says it outright: "The input file must be protected since it contains unencrypted passwords." `umask 077`, create under `/root`, `shred -u` after — and never a world-readable CSV from the helpdesk. Stdin form avoids the file but puts plaintext in your process tree and possibly shell history.
- **Re-running the same batch re-sets every password.** newusers is *not* idempotent: every run re-encrypts and re-installs the `pw_passwd` of every named user. An "ensure accounts exist" runbook that loops this hourly rotates passwords hourly. For declarative convergence, generate a fresh random password per user once, or use `chpasswd`/PAM tooling deliberately.
- **A typo in `pw_name` silently edits someone else's account.** Update semantics mean `alicia` when you meant `alice` rewrites alice's shell/home/GECOS/password. Batch files deserve the same review as SQL UPDATEs without a WHERE clause.
- **Homes are created, parents are not.** `/home/u01` fails if `/home` is missing (auto-mounted, not yet created); the failure is non-fatal — stderr grumbles, the batch continues, and you ship accounts without home directories. Pre-create parents in the same script.
- **Home changes do not move data.** Updating `pw_dir` for an existing user edits the passwd field only; the old directory and its content stay put. Migration is a manual `rsync`/`chown` job afterward.
- **UID edits do not chown either.** Change an existing user's `pw_uid` through newusers and their files keep the old numeric owner — the same manual `find -uid OLD -chown` sweep usermod would need.
- **`pw_shell` is unchecked.** `:/bin/bsh` ships a broken login; validate the shell column against `/etc/shells` in the generator, since the tool will not.
- **Crypt-method options moved under your feet.** `-c`/`-s` exist on bookworm, are gone on recent shadow; `ENCRYPT_METHOD` in login.defs is the portable lever. Scripts pinning `SHA512` break noisily on new releases — gate on capability.
- **PAM second pass can fail independently.** Accounts created, passwords not installed (users stay locked `!`). If your batch must yield *loggable* accounts, verify the shadow field afterwards rather than trusting exit 0.
- **`--badname` is deprecated.** It survives for migrations; new scripts should not lean on it — fix the names instead.
- **Implicit group creation can collide with your scheme.** A `pw_gid` group name that already exists is *used*, not merged; a numeric GID that is free creates a group named after the user. Sketch the expected group table before the batch, and reconcile with `grpck -r` after.

## Exit Status

The man page documents no exit-status table. Grounded and shared-machinery behavior on recent builds:

| Code | When |
| --- | --- |
| 0 | batch processed (pass-1 committed; pass-2 password failures may still have occurred) |
| 1 | can't update password file — observed for lock/permission failure (`Permission denied.` + `cannot lock /etc/passwd; try again later.`) |
| 2/3 | invalid command syntax / invalid option argument (shared machinery) |
| 6/10/12 | codes the embedded group/home machinery can surface (missing group, group-file update, home creation) |

Because pass-2 password failures do not change the exit status, exit 0 is "accounts exist", not "accounts are usable" — verify shadow fields when it matters. A provisioning wrapper that must certify logins therefore pairs the run with a shadow-side check (`getent shadow USER | grep -v '!'` per account) rather than trusting the exit code alone.

## Related Commands

- [`useradd`](./useradd.md) — the single-account tool whose machinery newusers drives; flags vs file lines.
- [`usermod`](./usermod.md) — deliberate per-account updates; what a mistaken batch line does by accident.
- [`passwd`](./passwd.md) — the interactive password tool; its batch sibling chpasswd (same package) feeds `user:pass` pairs without creating accounts.
- [`chage`](./chage.md) — aging policy for the accounts newusers seeded from login.defs defaults.
- [`groupadd`](./groupadd.md) — pre-creating groups explicitly when you do not want implicit ones.
- [`grpck`](./grpck.md) — post-batch integrity gate for the group half of what newusers wrote.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: What happens when a batch line names a user who already exists?

That line becomes an update: shell, GECOS, home directory field, group memberships implied by `pw_gid`, and (in the PAM pass) the password are all set from the line. This is simultaneously the feature (bulk updates and password rotation use exactly this) and the sharpest edge (a mistyped name silently rewrites an unintended account). The transactional guarantee only covers *database write* errors, not "wrong user". The operational answer: generate batch files from a reviewed source of truth, and treat them like schema-changing SQL.

### Q: Explain the two-pass design. Why are passwords handled separately from account creation?

Pass 1 writes accounts with locked (`!`) passwords — transactionally, so a bad line anywhere means nothing is committed. Pass 2 runs each password through PAM (the `/etc/pam.d/newusers` stack), where policy modules may reject or transform it. Decoupling means a password-policy failure affects one user's password, not the whole batch's database state; the cost is that exit 0 does not certify passwords — pass-2 failures are reported but non-fatal. So "created, but possibly locked" is the honest post-condition of any newusers run.

### Q: Where does newusers create home directories, and what exactly fails if the parent is missing?

It creates the `pw_dir` path if it does not exist, with ownership set to the user and their primary group and mode from `HOME_MODE` (else `UMASK`) — but it does **not** create parent directories, and a failed home creation is non-fatal: a message goes to stderr and the batch continues. The classic production form: N accounts, `/home` on an automount that is not mounted at provisioning time → all accounts exist, none can log in to a shell that needs a home. Pre-creating parents (or asserting the mount) belongs in the same script, and post-verification should check for the homes, not just the users.

### Q: Compare newusers, a useradd loop, and chpasswd for creating 200 accounts. When is each right?

newusers: one lock round-trip set, plaintext passwords handled in-band, implicit group creation — right for genuine bulk provisioning where a protected input file is acceptable. A useradd loop: no plaintext file (hashes via `-p` or a later `chpasswd`), per-account flags and error handling, but two hundred lock cycles and two hundred password steps — right when accounts are few, heterogeneous, or produced by a config-management tool that already handles secrecy. chpasswd: passwords only, no creation — right for rotation against *existing* accounts. The trade to articulate is plaintext-at-rest vs complexity-at-scale.

### Q: You ran the same batch file twice by accident. What changed?

Every named user's password was re-encrypted from the plaintext in the file and re-installed — so the second run rotated every password to the same value, and any password that users had changed in between was silently reverted. Accounts themselves are idempotent-ish (same fields rewritten), groups are reused, homes untouched if they exist. Nothing "breaks", which is exactly why this failure is insidious: the damage is that authentication state was reset, discoverable only from `shadow` last-change fields (`chage -l`) showing every account's password changed at the same timestamp.

### Q: What is `-r` for, and what does a system account created by newusers lack that a normal one has?

`-r` selects UIDs (and implicitly-created GIDs) from the SYS_* ranges and, critically, writes no password-aging fields into `/etc/shadow` — so policy expiry can never disable a service account. Otherwise the machinery is identical: locked password until a real hash arrives, no shell validation, home creation attempted per the `pw_dir` column. The pairing to remember from useradd applies here too: system accounts usually want `-r` plus a nologin shell in the input, which the batch line format supplies directly.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/newusers.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
