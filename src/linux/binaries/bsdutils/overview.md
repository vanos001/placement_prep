# bsdutils — Collection Overview

`bsdutils` is Debian packaging history you can hold in your hand: a small
set of utilities whose ancestry is 4BSD but whose upstream home today is
util-linux. Debian keeps them in their own binary package — installed on
essentially every system, priority "required" — because boot-critical
tooling depends on them. The collection covers the seven binaries the
package ships; each page carries its own usage depth, and this hub holds
the BSD-lineage story and the packaging logic.

## Why a BSD-named Package on Linux

Early Linux distributions borrowed working userland from wherever it
existed; the BSD-derived terminal and logging tools arrived as one bundle
and kept the name through the 1990s packaging consolidation. Upstream,
most of these tools migrated into util-linux during the 2010s
(`script`, `scriptreplay`, `renice`, `wall`, `logger`), while `write`
joined the absorbed `bsdmainutils` tools in `bsdextrautils`. The practical
takeaway for interviews: **package name, upstream project, and functional
family are three different axes** — `logger` is upstream util-linux,
Debian package bsdutils, functionally part of the syslog toolchain.

## Inventory

| Binary | One-liner | Page |
|---|---|---|
| `logger` | Write to syslog from the shell | [logger](./logger.md) |
| `wall` | Broadcast to all terminals | [wall](./wall.md) |
| `write` | Message one terminal | [write](./write.md) |
| `script` | Record a terminal session | [script](./script.md) |
| `scriptlive` | Replay typescript as live commands | [scriptlive](./scriptlive.md) |
| `scriptreplay` | Replay a recorded session | [scriptreplay](./scriptreplay.md) |
| `renice` | Renice running processes | [renice](./renice.md) |

Note on the neighbors: the old `bsdmainutils` package was retired and its
contents redistributed — `col`, `hexdump`, `look`, `ul`, `column` and
friends now live in `bsdextrautils` and are covered in the
[util-linux collection](../util-linux/overview.md). `calendar` and other
true 4BSD relics left the default sets entirely.

## Shared Concepts

- **The terminal-permission triangle**: `write` and `wall` both need the
  target's `mesg y` permission; `wall` skips closed terminals and says
  so, `write` fails per-target. The [mesg](../util-linux/mesg.md) page in
  the util-linux collection holds the permission mechanics; the
  [write](./write.md) and [wall](./wall.md) pages show the behavior.
- **The script family**: one recorder, two replay styles — timed
  playback ([scriptreplay](./scriptreplay.md)) and live re-execution
  ([scriptlive](./scriptlive.md)). The pairing matters for demos, audit
  trails, and CI flake reproduction; the [script](./script.md) page
  holds the timing-file format.
- **System messaging**: `logger` and `wall` are the two write paths into
  a system's attention — the journal/syslog for machines, terminals for
  humans. Shutdown sequences chain both (`wall` the countdown, then
  `logger` the transition; `/run/nologin` gates new logins).
- **Scheduling courtesy**: [renice](./renice.md) is the scheduler-facing
  tool here; privilege rules (you may only make processes nicer) mirror
  the coreutils [nice](../coreutils/nice.md) page and the procps
  [snice](../procps/snice.md) variant.

## Interview Questions

### Q: You need an audit trail of everything typed in a support session. What do you reach for?

`script -T timing -O typescript` (or `--log-timing/--log-io` on modern
util-linux) records the whole session with timing; `scriptreplay` plays
it back for review. The gotchas interviewers probe: it records the
terminal I/O, not the process tree (child ssh sessions are included
because their I/O flows through the pty; but separate ttys are not), and
passwords typed at prompts are captured too — audit convenience cuts
against secret hygiene. See [script](./script.md) for the file formats.

### Q: Why does logger sometimes exit 0 without your message appearing?

Classic paths: no `/dev/log` socket in the namespace (a minimal
container) and logger silently succeeds unless you ask for error
reporting; or the message went to a facility your filter ignores. Check
with `logger --socket-errors=on`, verify with `journalctl -t`, and pick
explicit `-p` facility.priority — the [logger](./logger.md) page decodes
the PRI computation.

### Q: wall says "will not read /etc/nologin" in some invocations — what is going on?

util-linux `wall` has a shutdown-aware mode: when invoked by root with
the right conditions it prints the nologin-file contents to logged-in
users as part of the shutdown sequence. The broader point is the
three-way split between broadcasting to current sessions (wall), gating
new sessions (pam_nologin + `/run/nologin`), and messaging one user
(write) — three tools, three questions. [wall](./wall.md) maps them.

## References

- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
- [Source — GitHub (util-linux upstream)](https://github.com/util-linux/util-linux)
- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/)
