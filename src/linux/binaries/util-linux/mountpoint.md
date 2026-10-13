# mountpoint — test whether a directory (or device) is a mountpoint

## Overview

`mountpoint` answers one yes/no question: is this path a mountpoint in the current mount namespace — that is, does a filesystem attach here? It also has a device-checking mode: given a block device file, it verifies the file is a block device and prints its major:minor numbers. The tool ships in the `util-linux` package at `/usr/bin/mountpoint` and is designed for scripts and unit files, so its contract is entirely exit-code based: the printed message is for humans, `$?` is for the machine.

Historically `mountpoint` lived in the sysvinit package; util-linux adopted it (2.23-era) to sit beside `mount`, `umount`, and `findmnt` with consistent semantics. It is often confused with two look-alike techniques: comparing `st_dev` of a directory with its parent (the classic shell trick), and grepping `/etc/fstab` (which tells you what *should* be mounted, not what *is* mounted). Only reading the kernel's live mount table — what `mountpoint` and `findmnt` do — is authoritative.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mountpoint |
| First appeared | sysvinit; adopted into util-linux 2.23 (2013) |
| Standards | Not POSIX; Linux-specific (reads `/proc/self/mountinfo`) |

## Synopsis

```
mountpoint [options] <directory>
mountpoint [options] <device>     # with -x
```

Main one-line forms:

```
mountpoint /data                  # rc 0 if /data is a mountpoint, else non-zero
mountpoint -q /data || mount /data
mountpoint -d /proc               # print major:minor of the filesystem mounted there
mountpoint -x /dev/vdb1           # print major:minor of the device file itself
mountpoint -q /proc/1/root/mnt    # a path inside another process's namespace view
```

## How It Works

### What "is a mountpoint" means

The kernel keeps the namespace's mount tree in `/proc/self/mountinfo`, one line per mount, with the mountpoint path, the mounted device's major:minor, propagation, and filesystem type. `mountpoint` consults this table (through libmount) rather than guessing from `stat` metadata:

```
$ cat /proc/self/mountinfo | grep ' / '
36 1 0:36 / / rw,relatime - overlay overlay rw,...
   │ │   │   │
   │ │   │   └─ mountpoint path inside the mount
   │ │   └───── device (major:minor) of the mount
   │ └───────── mount ID of the parent
   └─────────── mount ID of this mount
```

The older st_dev trick — compare `stat -c %D /dir` with `stat -c %D /dir/..` — works for ordinary mounts but misleads on network filesystems, some bind-mount setups, and overlayfs; the mountinfo table is exact because it is the kernel's own bookkeeping.

### The detection techniques, compared

```
technique                     exact?  touches the fs?  notes
mountpoint /dir               yes     parents only     exit-code contract for scripts
grep ' /dir ' /proc/mounts    yes     never            crude quoting on odd paths
findmnt --target /dir         yes     parents only     richest filtering (-o, JSON)
stat -c %D dir vs dir/..      mostly  full stat        overlayfs/NFS false results
grep /dir /etc/fstab          no      never            intent, not state
```

The st_dev trick's failure mode is instructive: on overlayfs the mount and its content share one st_dev, and on NFS all exports can share the server's device ID — the very cases where people need the check most. `/proc/self/mountinfo` compares paths, not device numbers, so it is immune.

### What mountpoint actually does, call by call

For the directory form it (1) stats the path to establish existence — a missing path is exit 1, not "not a mountpoint"; (2) has libmount parse `/proc/self/mountinfo` into a mount table; (3) looks the canonicalized path up among mount targets. `-d` then prints the matched entry's device numbers; `-x` bypasses the table entirely and answers a pure device-node question about the argument file. Two wrinkles follow from the design: the table is *this namespace's* view (containers disagree with hosts by construction), and the initial `stat(2)` of the path is real filesystem work — enough to trigger an autofs mount or block on a dead network path.

```
resolve path → stat (exists?) ──── no → exit 1 (error, not a verdict)
                     │ yes
                     ▼
        parse /proc/self/mountinfo
                     │
        target in table? ── yes → print msg (unless -q), exit 0
                     │ no
                     ▼
              exit 32 (current util-linux) / 1 (old contract)
```

### Stacked mounts and the "topmost" question

A path can have several mounts stacked on it (a bind over an existing mount). `mountpoint` answers "is something mounted here" with a single bit; it cannot tell you *how many* mounts are stacked or which is on top. `/proc/self/mountinfo` orders the stack, and `findmnt --target` shows the topmost entry with its full option set — when you care about what you are *about to cover* with a new mount, that is the question to ask.

### Observed behavior

```
$ mountpoint /proc
/proc is a mountpoint
$ echo $?
0

$ mountpoint /tmp
/tmp is not a mountpoint
$ echo $?
32

$ mountpoint /definitely/not/here
mountpoint: /definitely/not/here: No such file or directory
$ echo $?
1

$ mountpoint -x /etc/hosts
mountpoint: /etc/hosts: not a block device
$ echo $?
32
```

`-q` silences the message and keeps the exit code, which is the form scripts want. `-d` on a real mountpoint prints the major:minor of the mounted filesystem — useful for correlating with `findmnt`/`mountinfo` output or for detecting that a mount changed underneath you.

### Why scripts should care

Idempotent provisioning is the canonical use: "mount unless already mounted". Because the check consults kernel state, it is race-free for practical purposes and works identically for bind mounts, tmpfs, and NFS. systemd service units use the same idea as an `ExecStartPre`; shell equivalents abound in `/etc/init.d` scripts from the sysvinit era.

### systemd equivalents

Inside units, the same question is declarative: `ConditionPathIsMountPoint=/data` gates a service on mount state without spawning mountpoint, and `RequiresMountsFor=/var/lib/app` makes systemd order — and *require* — the mount before the unit starts. `mountpoint` remains the tool for shell contexts (ExecStartPre lines, initramfs, cron) where conditions and dependencies are not available; the exit-code contract is precisely what makes it drop-in there.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-q`, `--quiet` | No output, exit code only — the scripting form |
| `-d`, `--fs-devno` | Print major:minor of the filesystem mounted at the directory |
| `-x`, `--devno` | Argument is a *device file*: verify it is a block device, print its major:minor |
| `--nofollow` | Do not follow the final symlink component; check the path as given |
| `-h`, `--help` / `-V`, `--version` | Usage / version |

## Usage Patterns

```bash
# Idempotent mount in a provisioning script
mountpoint -q /data || mount /data
```

```bash
# Guard an rsync: refuse to write into a non-mounted (rootfs) directory
mountpoint -q /backup || { echo "backup disk not mounted" >&2; exit 1; }
```

```bash
# Wait for an automount to become live
until mountpoint -q /mnt/nas; do sleep 1; done
```

```bash
# List every mountpoint under /mnt (mountinfo is the source of truth)
findmnt -rno TARGET /mnt 2>/dev/null | while read -r m; do mountpoint -q "$m" && echo "$m"; done
```

```bash
# Detect that a filesystem changed underneath you (compare devno before/after)
mountpoint -d /data
```

```bash
# Verify a device node exists and is a block device before mkfs
mountpoint -x /dev/vdb1
```

```bash
# systemd-style precheck in a custom unit
ExecStartPre=/usr/bin/mountpoint -q /var/lib/app
```

```bash
# Enumerate candidate mount roots before a backup (skip nested mounts)
findmnt -rno TARGET /mnt | while read -r m; do mountpoint -q "$m" && echo "$m"; done
```

```bash
# Check a bind inside a container from the host: mountinfo is per-namespace,
# so enter the container's mount namespace first
nsenter -t "$PID" -m -- mountpoint -q /data
```

```bash
# Refuse to wipe a disk partition that is currently mounted
mountpoint -q /mnt/usb && { echo "umount first" >&2; exit 1; }
```

```bash
# Count local mounts without spawning findmnt
cat /proc/self/mountinfo | wc -l
```

```bash
# Teardown-side idempotence: unmount only if mounted
mountpoint -q /mnt/iso && umount /mnt/iso
```

```bash
# Verify the mount is the one you expect (device numbers are the identity)
[ "$(mountpoint -d /data)" = "8:2" ] || echo "unexpected fs under /data" >&2
```

```bash
# Detect that a path is a planted symlink before trusting the check
mountpoint --nofollow -q /srv/data || readlink -f /srv/data
```

## Nuances and Gotchas

- **Exit code 32 is the "no" answer on current util-linux.** Observed: mountpoint → 0, existing-but-not-mountpoint → 32, missing path → 1. Older releases (and the sysvinit original) documented simply "0 if mountpoint, 1 if not"; if you support old images, test both or use `findmnt`/`grep /proc/mounts`. Never write `if ! mountpoint /x` and assume the failure reason.
- **Namespace-relative.** The answer is true for *your* mount namespace. Inside a container, `/` is almost always a mountpoint even if the host would disagree; `nsenter`-based checks from outside see the host view.
- **Stale network mounts.** The mountinfo lookup does not touch the server, but resolving the *path* (e.g., for `-d`) may hit a dead NFS mount and hang. For liveness probes of network mounts, prefer `grep /proc/self/mounts` or `findmnt --target` over anything that stats the path.
- **fstab is not state.** `grep /data /etc/fstab` proves intent, not reality. Conversely `mountpoint /data` proves reality, not persistence across reboot. The pair together is the full answer.
- **`-x` vs `-d` are easy to mix up.** `-x` inspects the *file you name* (device side); `-d` inspects *what is mounted at* the directory (mount side). Passing a regular file to `-x` yields "not a block device".
- **Trailing slashes are canonicalized** by libmount, so `mountpoint /data/` behaves like `mountpoint /data` — but a symlinked path resolves to its target first, which can silently test the wrong location.
- **BusyBox variant is reduced.** BusyBox `mountpoint` supports `-q`/`-d` but its exit codes follow the old 0/1 convention; portable initramfs scripts must handle that.
- **The root is always a mountpoint (rc 0).** `mountpoint /` proves nothing about any disk — the root mount always exists. Checking "is my data disk mounted" means checking *its* path, never `/`.
- **Under `set -e`, 32 is a failure.** `mountpoint -q /data` as a bare statement aborts a `set -e` script when the answer is no; use it in `if`/`||` context deliberately — the "no" answer *is* a non-zero exit by design.
- **The stat can have side effects.** On autofs-managed paths, resolving the directory can trigger the automounter (your "read-only check" mounts something) or block on a broken map. For pure table reads, grepping `/proc/self/mountinfo` or `findmnt --target` never resolves through the filesystem itself.
- **Exit codes are a compat surface.** Scripts written against the old 0/1 contract break on modern util-linux's 0/1/32; scripts written against 0/32 break on BusyBox. Test only for success (`if mountpoint -q ...`) and treat every nonzero as "no, for some reason" — the reason lives on stderr, not in the code.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | The directory is a mountpoint (or, with `-x`, the file is a block device) |
| 32 | The directory exists but is not a mountpoint (or, with `-x`, not a block device) — current util-linux convention |
| 1 | Error: path does not exist, permission denied, usage error |

## Related Commands

- [`mount`](./mount.md) — performs the mounts `mountpoint` checks for; shares libmount state handling.
- [`findmnt`](./findmnt.md) — the full query language over the same mount table (filter by target, source, options, JSON output).
- [`umount`](./umount.md) — detaching; pair `mountpoint -q X && umount X` for idempotent teardown.
- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`systemd`](../../admin/systemd.md) — mount/automount units make this check declarative (`RequiresMountsFor=`).

## Interview Questions

### Q: How can a shell script reliably detect whether /data is mounted, and what are the failure modes of the naive approaches?

Authoritative options: `mountpoint -q /data`, `findmnt --target /data`, or matching the path in `/proc/self/mountinfo`. Naive approaches fail in specific ways: comparing `st_dev` of the directory and its parent misreports on overlayfs and some network filesystems; grepping `/etc/fstab` reflects configuration, not live state; checking directory writability conflates permissions with mounting. The mountinfo-based checks are exact because they read kernel bookkeeping rather than inferring.

### Q: What is the difference between a directory that "exists but is empty" and a mountpoint that "is not mounted", and why does it matter operationally?

An unmounted mountpoint is just a normal directory — usually empty so it can be shadowed cleanly. If the disk fails to mount, writes land in that directory on the *root* filesystem: logs fill `/var/lib/postgresql` on `/` instead of the data disk, and nobody notices until `/` is full. That is why provisioning scripts guard with `mountpoint -q` before starting services, and why systemd mount units + `RequiresMountsFor=` exist — they turn "must be mounted" into a dependency rather than a hope.

### Q: `mountpoint /mnt/nfs` hangs in your monitoring check. Explain and fix.

The path lookup (and `-d`'s stat) on a dead NFS mount blocks in the kernel waiting for the server. Reading `/proc/self/mountinfo` never touches the network, so replace the check with `grep -q ' /mnt/nfs ' /proc/self/mountinfo` or use `findmnt --target` with a timeout wrapper (`timeout 2 mountpoint /mnt/nfs`). The general lesson: any probe that resolves a path through a potentially dead filesystem can block, and path-based syscalls have no default timeout.

### Q: Why did `mountpoint` move from sysvinit to util-linux, and what does that history tell you?

Because it is fundamentally a libmount question — "is this path a mount in the current namespace" — and util-linux owns libmount, `/proc/self/mountinfo` parsing, and the mount/umount/findmnt family. Consolidation gave it consistent fstab/namespace semantics with the rest of the family. Interview-wise, the takeaway is that small tools often migrate toward the library that owns their data model, and exit-code contracts are the stable API that survives such moves.

### Q: Design a monitoring check for "NFS backup target is mounted and writable". What does mountpoint contribute, and what is missing?

`mountpoint -q /mnt/backup` contributes the cheap, hang-resistant part: it reads kernel mount state and reports whether the path is a mountpoint at all, without writing anything. It cannot prove the *server* is alive or that the mount is the one you expect — a stale export can still be a mountpoint, and someone could have mounted the wrong device there. A complete check adds identity (`findmnt -n -o SOURCE /mnt/backup` compared against the expected server/export), liveness with a timeout (`timeout 5 touch /mnt/backup/.probe`), and alerting that distinguishes "not mounted" (mount it) from "mounted but dead" (remount/recover). The layered answer — mount state, identity, liveness — is what interviewers listen for.

### Q: Your script branches on `[ $? -eq 1 ]` for "not mounted" and misbehaves on modern util-linux. Why, and what is the robust shape?

The negative answer is now 32 (observed: `/tmp is not a mountpoint` → exit 32), while 1 is reserved for errors such as a missing path — so an equality test on 1 misclassifies both directions. The robust shape tests only for success: `if mountpoint -q "$dir"; then ... else ...`, letting stderr carry the reason. If you must distinguish "not mounted" from "path missing", check existence separately (`[ -e "$dir" ]`) rather than decoding exit codes across implementations.

### Q: Why is a plain stat-based check not enough, given mountpoint stats the path too?

The stat establishes existence; the *verdict* comes from the kernel mount table, and that separation is the point. st_dev comparisons (dir vs dir/..) infer mounting from device numbers, which overlayfs, NFS, and bind setups falsify; writability checks conflate permissions with mounting; fstab reflects intent, not state. mountpoint's stat can trigger autofs or hang on dead network paths — but the classification it returns is always the namespace's own bookkeeping. A layered check uses mountpoint (or a mountinfo grep) for state, then adds identity (`findmnt -o SOURCE`) and liveness probes on top.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mountpoint.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
