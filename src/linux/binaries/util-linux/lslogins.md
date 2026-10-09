# lslogins — per-user account and login information from local system files

## Overview

`lslogins` answers "what do we know about this system's users" in one place: it joins `/etc/passwd`, `/etc/shadow`, the login-accounting files (`wtmp`, `btmp`, `lastlog`) and live process data into either a user table or a detailed key/value report per account. Typical output covers UID/GID, home, shell, whether login is disabled (`nologin`), password state (locked/empty/denied), last successful and failed logins, and the user's current process count.

It ships in the `util-linux` package at `/usr/bin/lslogins` and follows the same table/columns/output-format conventions as `lslocks` and `lsns`. It is often confused with `last`/`lastlog` (which read only one accounting file each), with `getent passwd` (directory lookup, no login history), and with `passwd -S` (single-account password state only).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/lslogins |
| First appeared | util-linux 2.29 era (mid-2010s) |
| Standards | None — uses local files and login.defs conventions |

## Synopsis

```
lslogins [options] [username]
```

Common one-line forms:

```
lslogins                     # table of all accounts
lslogins -u                  # regular (login-capable) users only
lslogins -s                  # system accounts only
lslogins root                # detailed key/value report for one user
lslogins -o USER,UID,LAST-LOGIN -u   # selected columns
```

## How It Works

### Sources joined per account

Each row aggregates several independent system files. The tool reads them directly (not through NSS), which is both its speed and its main limitation — LDAP/SSSD users are invisible unless they also exist locally:

```
/etc/passwd ─────▶ USER, UID, GID, GECOS, HOMEDIR, SHELL
/etc/shadow ─────▶ PWD-LOCK, PWD-EMPTY, PWD-DENY, PWD-METHOD, expiration
/var/log/wtmp ───▶ LAST-LOGIN, LAST-TTY, LAST-HOSTNAME
/var/log/btmp ───▶ FAILED-LOGIN count, last failed attempt
/var/log/lastlog ▶ LAST-LOGIN per tty
/run/utmp + /proc ▶ PROC (current process count)
```

Shadow-derived columns (`PWD-*`, expiration) are only meaningful when the caller can read `/etc/shadow` — as root, or via suitable group membership; otherwise those cells stay empty rather than erroring.

### Two output shapes

- **Table mode (no username):** one row per account, columns selected with `-o`/`--output-all`. Real default output on a fresh container:

  ```
  $ lslogins
    UID USER            PROC PWD-LOCK PWD-DENY LAST-LOGIN GECOS
      0 root               6                              root
      1 daemon             0                              daemon
   1000 bun                 0
  ```

- **Detail mode (username given):** aligned key/value lines for that account, ending with its recent log entries:

  ```
  $ lslogins root
  Username:                           root
  UID:                                0
  Home directory:                     /root
  Shell:                              /bin/bash
  No login:                           no
  Running processes:                  6
  ```

### User vs system accounts

`-u` (user accounts) and `-s` (system accounts) classify by the `UID_MIN` threshold from `/etc/login.defs`, so the split follows the machine's own policy rather than a hard-coded number. With neither flag, all accounts are listed. `-g` filters by group membership and `-l` by explicit user/UID list — the two flags compose with the column selection for audit one-liners.

### The accounting files, critically assessed

The history columns are only as good as the files feeding them, and each has distinct behavior:

- `/var/log/wtmp` — appended by login programs and session leaders; rotates (so "last login" can live in `wtmp.1`); recent systemd releases write far less here than they used to.
- `/var/log/btmp` — failed-login records; on internet-facing hosts this file grows enormously under brute force (and tools like fail2ban exist partly to manage that pattern); mode 0600 because it accumulates usernames attempted by attackers.
- `/var/log/lastlog` — one sparse record per UID; can appear huge in `ls -l` while occupying almost no blocks (sparse file, a classic `du` vs `ls` surprise).
- `/run/utmp` — current sessions only; lost on every boot by design.

The `--wtmp-file`/`--btmp-file`/`--lastlog` options exist precisely because auditors point the tool at rotated or mounted-from-images copies of these files.

### Output formats for automation

Beyond the human table, three machine formats matter: `-r` (raw, unpadded), `-c` (colon-separated, passwd-file flavored), and `-e` (export format: quoted `KEY=value` pairs suitable for shell evaluation). `-y` additionally rewrites headers so column names are valid shell identifiers (`PWD-LOCK` style becomes underscore-safe), and `-z` NUL-delimits records for pipelines through `xargs -0`. The design goal is that an audit script needs no fragile whitespace parsing.

### Password-state columns, decoded

`PWD-LOCK` means the password hash is locked (account present but password unusable, e.g. `passwd -l` or `!` prefix); `PWD-EMPTY` means no password at all; `PWD-DENY` means password authentication is administratively disabled. These are independent of `NOLOGIN` (login shell is `/usr/sbin/nologin`/`/bin/false`). Auditing "can this account actually log in" requires reading the four columns together — a favorite interview trap.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-u, --user-accs` | Only regular user accounts (UID ≥ UID_MIN) |
| `-s, --system-accs` | Only system accounts (UID < UID_MIN) |
| `-o, --output <list>` | Comma-separated column selection |
| `--output-all` | All available columns |
| `-p, --pwd` | Add password-related columns (change/expiration) |
| `-f, --failed` | Show failed-login data (from btmp) |
| `-a, --acc-expiration` | Show password/account expiration data |
| `-L, --last` | Show last-login session info |
| `-G, --supp-groups` | Show supplementary groups |
| `-g, --groups=<groups>` | Limit to users of these groups |
| `-l, --logins=<logins>` | Limit to these users/UIDs |
| `-n, --newline` | Detail view: one field per line |
| `-c / -e / -r` | Colon-separated / exportable / raw output formats |
| `-y, --shell` | Column names usable as shell variable identifiers |
| `-z, --print0` | NUL-delimit records |
| `--time-format=<type>` | `short`, `full` or `iso` dates |
| `--wtmp-file`, `--btmp-file`, `--lastlog` | Alternate accounting file paths (testing, rotated logs) |

## Usage Patterns

```bash
# List login-capable accounts with their password state
lslogins -u -o USER,UID,NOLOGIN,PWD-LOCK,PWD-EMPTY,PWD-DENY
```

```bash
# Audit: accounts with empty passwords (should be none on a real host)
lslogins -o USER,PWD-EMPTY | awk 'NR==1 || $2 != 0'
```

```bash
# Full detail report for one account
lslogins root
```

```bash
# Failed-login summary from btmp (brute-force indicators)
lslogins -f -o USER,FAILED-LOGIN,LAST-FAILED
```

```bash
# Who actually logged in recently, ISO timestamps
lslogins -u -L --time-format=iso -o USER,LAST-LOGIN
```

```bash
# Members of the sudo group with their shells
lslogins -g sudo -o USER,SHELL,NOLOGIN
```

```bash
# Script-friendly export format
lslogins -e -u -o USER,UID,SHELL
```

```bash
# Shell-variable-safe headers for use with eval-driven scripts
lslogins -y -u -o USER,UID
```

```bash
# Inspect a captured/rotated wtmp from a forensic copy
lslogins --wtmp-file /mnt/forensics/var/log/wtmp.1 -L
```

```bash
# System accounts that should be nologin but are not
lslogins -s -o USER,SHELL,NOLOGIN | grep -v nologin
```

```bash
# UID sanity: any login-capable account below UID_MIN that is not nologin?
lslogins -s -o USER,UID,NOLOGIN | awk 'NR>1 && $3=="no"'
```

```bash
# Evaluate-safe export for a configuration-management fact
lslogins -e -u -o USER,UID,SHELL
```

```bash
# NUL-safe handoff into xargs for follow-up actions
lslogins -u -z -o USER | xargs -0 -n1 echo "audit:"
```

```bash
# Compare brute-force pressure across hosts (btmp-based failed logins)
lslogins -f -o USER,FAILED-LOGIN | sort -k2 -rn | head
```

## Nuances and Gotchas

- **Local files only, no NSS.** `lslogins` reads `/etc/passwd` and friends directly; users provided by LDAP/SSSD/Winbind do not appear unless they are also local entries. `getent passwd` is the NSS-aware alternative — they answer different questions.
- **Shadow columns silently empty for non-root.** Without permission to read `/etc/shadow`, `PWD-*` cells are blank. Scripts auditing password state must run as root; otherwise the audit looks clean while saying nothing.
- **wtmp/lastlog are aging infrastructure.** Recent systemd releases no longer populate `wtmp`/`lastlog` by default (the `lastlog2`/`wtmpdb` successor is being adopted), so `LAST-LOGIN` can legitimately be empty on current installs. An empty column is not evidence that nobody logged in.
- **PROC counts are live.** The process count comes from scanning `/proc` at invocation time — it says nothing about sessions, and inside containers it counts only the visible PID namespace.
- **Default view includes system accounts.** People expecting "users" get daemons too; use `-u`/`-s` deliberately, since the UID threshold comes from the machine's `login.defs`.
- **Parse with -r/-e/-y, not with cut.** Column widths adapt to content; the raw/export formats and `-y` shell-identifier headers exist precisely for scripting.
- **`-g`/`-l` filter, they do not add columns.** Combine them with `-o`/`-G` when you want group *data* rather than just filtering.
- **btmp size is an incident signal.** A multi-hundred-MiB `/var/log/btmp` means sustained brute-force attempts; the FAILED-LOGIN columns read from it will be dominated by nonexistent usernames. Cap/rotate it like any log.
- **lastlog's giant apparent size.** `ls -lh /var/log/lastlog` on a high-UID system shows a gigantic file that `du` reports as tiny — records live sparsely at UID offsets. Do not panic-copy "the huge log".
- **Detail mode is one account per run.** Loop it (`for u in ...; do lslogins "$u"; done`) — there is no multi-user detail flag; the `-l` list form switches back to table output.

## Exit Status

- `0` — success.
- `1` — failure: invalid option, unreadable input file, or unknown user in detail mode.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`users and groups`](../../admin/users-groups.md) — the passwd/shadow/group model these columns decode.
- [`lslocks`](./lslocks.md) — sibling util-linux reporter with the same output conventions.

## Interview Questions

### Q: How do you tell whether an account can actually log in, using lslogins?

Read four columns together: `NOLOGIN` (shell is nologin/false), `PWD-LOCK` (hash locked), `PWD-EMPTY` (no password), and `PWD-DENY` (password auth disabled). Any single one being set blocks the classic password-login path, and combinations matter (locked shell + valid password vs unlocked shell + locked password). No single column answers "can it log in".

### Q: Why might PWD-LOCK be blank for a user when run as a regular account?

The value is derived from `/etc/shadow`, which only root (or a shadow group member) can read. Rather than failing, `lslogins` leaves the field empty — so unprivileged audits produce silently incomplete results. The fix is running the audit as root or via sudo.

### Q: lslogins shows no LAST-LOGIN for anyone on a modern server. Is that a hack?

Not necessarily. Recent systemd releases stopped writing `wtmp`/`lastlog` by default in favor of the `lastlog2`/`wtmpdb` successors, so fresh installs legitimately have empty accounting files. Check whether the files are even being written (`last -f /var/log/wtmp`) before assuming tampering; the audit trail may live in journald instead.

### Q: Why does lslogins miss an LDAP user that getent passwd shows?

lslogins reads the local files directly and does not consult NSS; getent does. Accounts resolved via directory services are invisible to lslogins unless duplicated locally. That is also why lslogins is fast and consistent on air-gapped systems — it never blocks on a network directory.

### Q: How would you produce a daily report of unused login-capable accounts?

Combine `lslogins -u -L --time-format=iso -o USER,UID,LAST-LOGIN` with `LAST-LOGIN` empty or older than policy, plus `PROC` for activity, and emit via the export format (`-e`) for ingestion. Remember the wtmp caveat: empty LAST-LOGIN on modern systemd hosts is ambiguous, so corroborate with journal/auth logs.

### Q: Why can /var/log/btmp become enormous, and what does that mean for lslogins results?

btmp records every failed login, including attacks against nonexistent usernames, so internet-exposed hosts accumulate gigabytes. The FAILED-LOGIN columns then reflect attacker traffic, not account health — most "failed logins" belong to users that do not exist. Treat btmp growth as a security signal, rotate it, and read per-account failure data with that bias in mind.

### Q: What is the practical difference between lslogins and getent/getent passwd for an audit?

getent consults NSS (so it sees LDAP/AD users) but returns only directory fields. lslogins sees local files only, but joins in password state, login history, and live process counts — the audit-relevant dimensions. A complete host audit typically needs both: directory users from getent, local risk signals from lslogins, and the awareness that the two lists may not overlap.

### Q: Explain the PWD-EMPTY versus PWD-LOCK distinction and why it matters for security triage.

PWD-EMPTY means the account has no password hash at all — depending on PAM configuration, such an account may authenticate with an empty string. PWD-LOCK means a hash exists but is prefixed into unusability (`!`, `passwd -l`) — password login is impossible but SSH keys may still work. Confusing the two produces wrong incident conclusions: locked accounts are common and intentional; empty-password accounts on a multi-user host are an emergency.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lslogins.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
