# login — Collection Overview

The login collection is small and packaging-shaped: Debian's `login`
binary package holds the tools that put a session on a terminal and keep
its accounting straight. Upstream it is a split bag — `login`,
`sulogin`, and `nologin` come from util-linux, while `faillog`,
`lastlog`, `newgrp`, and `sg` come from the shadow suite — but they ship
together because they belong to the same moment in a system's life: the
user's first process.

## Why This Moment Matters

Everything about a session is decided at login time: which PAM stack
runs, what utmp/wtmp records are written, which shell and group
identity you get, and what the failure path looks like when the system
is half-broken. Interviews love the failure paths — `sulogin` on a
broken boot, `nologin` as a policy shell, `newgrp`'s surprising fork —
because they separate people who have actually administered machines
from people who have only read about them.

## Inventory

| Binary | One-liner | Upstream | Page |
|---|---|---|---|
| `login` | Open a session on a tty | util-linux | [login](./login.md) |
| `sulogin` | Single-user shell entry | util-linux | [sulogin](./sulogin.md) |
| `nologin` | The polite refusal shell | util-linux | [nologin](./nologin.md) |
| `faillog` | Login-failure accounting (db + tool) | shadow | [faillog](./faillog.md) |
| `lastlog` | Last-login accounting | shadow | [lastlog](./lastlog.md) |
| `newgrp` | Re-login into a group | shadow | [newgrp](./newgrp.md) |
| `sg` | Run a command under a group | shadow | [sg](./sg.md) |

## Shared Concepts

- **utmp/wtmp/lastlog**: three databases, three questions — who is
  logged in now (utmp), who logged in historically (wtmp, read by
  `last` in the util-linux collection), and when did each account last
  log in ([lastlog](./lastlog.md)). The struct layouts and Y2038 caveat
  are on the [utmpdump](../util-linux/utmpdump.md) page.
- **PAM boundary**: `login` is the canonical PAM consumer — auth,
  account, session stacks all fire here. `pam_nologin` is what makes
  `/etc/nologin` (the FILE) block logins; [nologin](./nologin.md) covers
  the same-named binary/file distinction, a favorite trick question.
- **Group identity**: `newgrp`/`sg` change the SGID context without
  re-authenticating the user, using `/etc/gshadow` passwords when the
  user is not a member — see [newgrp](./newgrp.md) and pair with
  [gpasswd](../shadow/gpasswd.md) in the shadow collection.
- **Rescue path**: when the boot fails, systemd drops to
  `sulogin`-driven rescue/emergency targets. The [sulogin](./sulogin.md)
  page explains the root-password check and `-p` persistence that make
  that path work (or fail) safely.

## Reading Order

1. [login](./login.md) — the canonical session-entry flow.
2. [nologin](./nologin.md) + [sulogin](./sulogin.md) — the two failure
   faces of the same name.
3. [lastlog](./lastlog.md) — accounting with the sparse-file surprise.
4. [newgrp](./newgrp.md)/[sg](./sg.md) — group switching mechanics.

Related: the [shadow collection](../shadow/overview.md) owns the account
database these tools authenticate against, and
[agetty](../util-linux/agetty.md) is what invokes `login` on a serial or
virtual terminal.

## Interview Questions

### Q: /usr/sbin/nologin vs /bin/false as a user's shell — why prefer nologin?

Both refuse execution; the difference is diagnostics. `nologin` prints a
standard refusal message ("This account is currently not available.")
before exiting 1, so users and SSH clients see an intentional policy
message rather than a silent connection drop. `/bin/false` just exits 1 —
correct for service accounts where even a message invites curiosity.
The [nologin](./nologin.md) page also separates the binary from the
`/etc/nologin` file that `pam_nologin` reads.

### Q: Where does "last login: ..." come from on an SSH session?

pam_lastlog (or an equivalent in sshd) reads the account's record from
`/var/log/lastlog` and prints it before the shell starts; the record is
then updated on successful login. The file is sparse — its apparent size
scales with the highest UID, not the data written — a classic
`ls -lh` surprise covered on the [lastlog](./lastlog.md) page.

### Q: Why does newgrp fork a new shell instead of changing your group in place?

POSIX process semantics give a process its group memberships at
credential time; a running shell cannot add a supplementary group it
lacks. `newgrp` execs a fresh shell whose credentials carry the new
GID (after an optional gshadow password check), which is also why the
old shell's environment does not fully survive. See
[newgrp](./newgrp.md) for the exact flow and [sg](./sg.md) for the
one-command variant.

## References

- [Source — Debian sources (shadow)](https://sources.debian.org/src/shadow/)
- [Source — GitHub (util-linux)](https://github.com/util-linux/util-linux)
- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/login/)
