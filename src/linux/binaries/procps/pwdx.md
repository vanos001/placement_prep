# pwdx — report the current working directory of a process

## Overview

`pwdx` prints the working directory of running processes: give it one or more PIDs, get back one line per PID in the form `PID: /path/to/cwd`. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/pwdx`, and it has no options that affect output — no formatting, no filtering, no verbosity — because the entire job is one `readlink()` on `/proc/<pid>/cwd`.

The question it answers comes up constantly in operations: which directory is that `java` process actually running from (which config files does it see)? Which process is holding a directory that `rmdir` refuses to remove? Is that cron job executing where the author assumed? `pwdx` is the two-character-per-PID answer, and because it is a thin wrapper over procfs it always agrees with what the kernel thinks — no libc path caching, no stale shell state.

`pwdx` is often confused with `pwd` (prints *your* shell's directory) and with `lsof`'s `cwd` rows (which require lsof and list all fds anyway). It is also mistaken for a full "process file info" tool: it does not report open files, roots, or exe paths — only cwd.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/pwdx |
| First appeared | 2004, written by Nicholas Miell for procps |
| Standards | No standards apply; the man page notes it "looks an awful lot like a SunOS command" |

## Synopsis

```
pwdx [options] pid...
```

Common one-line forms:

```
pwdx 1234              # one process
pwdx 1234 5678         # several processes, one line each
pwdx $(pgrep -x java)  # every java process
pwdx 1                 # init/systemd (root only)
```

## How It Works

### One symlink, one line

Every process directory in procfs carries a `cwd` symlink that the kernel resolves to the process's working directory at readlink time:

```bash
$ ls -l /proc/$$/cwd
lrwxrwxrwx 1 z z 0 ... /proc/12035/cwd -> /home/z/my-project
$ pwdx $$
12035: /home/z/my-project
```

`pwdx` formats `/proc/<pid>/cwd` readlink output and nothing else — the binary's only procfs path is the `cwd` symlink. What the kernel shows is the *dentry* of the process's current working directory, rendered as a path. Two consequences follow:

1. The result is authoritative and instantaneous: if the process just `chdir()`ed, the next readlink already shows the new path. There is no snapshot semantics to worry about.
2. The kernel may render paths that do not literally exist in your filesystem view. If the directory was removed, the process still holds the inode, and the kernel marks the readlink result:

```bash
$ mkdir -p /tmp/gonex2
$ (cd /tmp/gonex2 && exec sleep 90) & sleep 0.4
$ pwdx $!
12081: /tmp/gonex2
$ rmdir /tmp/gonex2
$ pwdx $!
12081: /tmp/gonex2 (deleted)
```

The ` (deleted)` suffix is the same marker the kernel uses for `/proc/<pid>/fd` links to unlinked files. That is not an error — it is the single most useful diagnostic pwdx produces: the directory no longer has a name, but a process still lives inside it, and the inode (and anything mounted/linked from it) cannot be fully reclaimed until that process dies or moves out.

### What cwd is to a process

The working directory is not a string — it is a reference to a directory inode held in the process's `fs_struct`. That explains every behavior pwdx exposes:

- **Children inherit it.** `fork()` copies the reference; a service started from a shell keeps the shell's cwd until it `chdir`s. This is why "which directory did the daemon actually start in" needs pwdx and cannot be answered from the unit file alone.
- **`execve` keeps it.** Replacing the program image does not touch the cwd, so a re-executed process stays pinned where it was.
- **Every relative path resolves against it.** A process with cwd `/srv/app` opening `config.yaml` reads `/srv/app/config.yaml` — pwdx is how you reconstruct what unqualified paths mean for a running process.
- **It pins the inode.** Until the process chdirs away or exits, the directory (and its whole subtree of live inodes) cannot be reclaimed — the `(deleted)` case below.
- **Daemons usually let it go.** The traditional double-fork daemonization does `chdir("/")` precisely to release the mount point it started on; modern systemd services set `WorkingDirectory=` instead. A service still cwd'd inside a removed deployment directory is a daemonization bug in action.

```
  shell (cwd=/home/ops) ──fork──▶ child (cwd=/home/ops)
                                     │ cd /srv/app && exec ./server
                                     ▼
                          server (cwd=/srv/app)
                                     │ rm -rf /srv/app (elsewhere)
                                     ▼
                          server (cwd=/srv/app (deleted))  ← inode pinned
```

### Permissions

`/proc/<pid>/cwd` follows the usual procfs protection model: a process may inspect itself, root may inspect everything, and unprivileged users get `Permission denied` for other users' processes:

```bash
$ pwdx 1
1: Permission denied            # as a normal user
$ echo $?
1
```

The check is not just ownership: the kernel applies the same "may I ptrace-ish-access this task" logic as for the rest of `/proc/<pid>`, so hardened setups (e.g. `hidepid` mounts, some hardened kernels) can deny even same-uid lookups of foreign sessions.

### Multiple PIDs and the exit contract

With several PIDs, pwdx emits one line per PID — good ones to stdout, failures to stderr — and exits 1 if *any* argument failed:

```bash
$ pwdx $$ 123456789
12035: /home/z/my-project
123456789: No such process
$ echo $?
1
```

So the exit code answers "did everything succeed", never "did anything succeed". Scripts that just want the successes should redirect stderr and ignore the status, or loop over PIDs one at a time.

Ordering is the argument order, not PID order: `pwdx 500 100` prints 500's line first. The output is trivially parseable (`PID: path`, single space delimiter), which is the other half of why it survives in scripts — `pwdx $(pgrep -x app) | awk -F': ' '$2 ~ /releases/'` needs no column guessing.

## Options That Matter

pwdx has exactly two options; that is the design, not an omission:

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Usage text and exit |
| `-V`, `--version` | Version and exit |

There is no `-l`, no `-a`, no output-format flag. If you need more per-process path information (exe, root, fds), go straight to procfs or lsof; pwdx deliberately stays one readlink wide.

## Usage Patterns

```bash
# Which directory is this service actually running from?
pwdx $(pgrep -x java)

# Verify a daemon started by systemd sees the WorkingDirectory you set
systemctl show -p WorkingDirectory myservice
pwdx $(systemctl show -p MainPID --value myservice)

# Find the process pinning a directory you want to remove
pwdx $(ps -eo pid=) | grep /srv/old-app

# Locate cwd markers of deleted directories (space-retention forensics)
pwdx $(ps -eo pid=) 2>/dev/null | grep '(deleted)'

# One PID at a time so one failure does not spoil the batch
for p in $(pgrep -f exporter); do pwdx "$p"; done

# Check where your shell's children landed (background jobs)
pwdx $(jobs -p)

# The no-pwdx equivalent, for minimal containers without procps
for p in /proc/[0-9]*; do printf '%s: %s\n' "${p#/proc/}" "$(readlink "$p/cwd")"; done

# Confirm an unpacked tarball's postinstall chdir actually happened
pwdx $INSTALLER_PID

# Audit every long-running python service's directory at a glance
for p in $(pgrep -x python3); do pwdx "$p"; done | sort -t: -k2

# Compare the cwd you expected vs the one systemd configured
systemctl cat myservice | grep -i workingdir
pwdx "$(systemctl show -p MainPID --value myservice)"

# Find processes still living in last week's release directory
pwdx $(ps -eo pid=) 2>/dev/null | grep -F /releases/2024-

# Guard rails: dump cwd before killing, for the postmortem
for p in $(pgrep -f flakyworker); do pwdx "$p"; kill -TERM "$p"; done

# Triage a suspected wrong-workdir container entrypoint
docker exec myapp sh -c 'pwdx $$' 2>/dev/null || pwdx $(pgrep -x myapp)
```

## Nuances and Gotchas

- **` (deleted)` is part of the path string.** Scripts comparing the output to an expected directory must strip the suffix; `pwdx $p | grep -q "^$p: /srv/app$"` fails exactly when the directory was removed under the process.
- **Exit 1 on any failure.** `pwdx 100 101 102` with one dead PID is exit 1 even though two lines are fine. Aggregating PIDs into one call is convenient interactively but poisons the exit status for scripts.
- **Permission denied is the normal case for root-owned processes.** A non-root `pwdx` across `$(ps -eo pid=)` returns a wall of "Permission denied" lines on stderr — filter with `2>/dev/null` when surveying.
- **PID races.** Between `pgrep` and `pwdx` the target may exit and its PID get recycled; "No such process" or a *wrong process* is possible. For automation, re-check identity (e.g. `/proc/<pid>/cmdline`) after reading the cwd.
- **Chroot and namespace rendering.** For a chrooted process the kernel renders `cwd` relative to the process's own root, so the printed path can be meaningless (or absent) from your vantage point. Likewise, PIDs are namespaced: inside a container you can only pwdx processes of its PID namespace.
- **cwd is not the only thing pinning a directory.** An open fd or a mmap into a directory/file keeps the inode alive even when cwd is elsewhere. pwdx answers "where is it", not "what holds it" — follow up with `/proc/<pid>/fd` when hunting unremovable trees.
- **Portability.** pwdx is procps/Linux. On BSD there is no `/proc` cwd symlink in the Linux shape (`procstat -w` or `pwdx`-alikes differ), and macOS has neither procfs nor pwdx — scripts that rely on it are Linux-only.
- **One readlink, one race window.** pwdx resolves the symlink at the instant you run it; a process in the middle of `chdir` gives you either the old or the new directory, never a mix. Snapshot sweeps of thousands of PIDs are therefore internally consistent only per line, not across the sweep.
- **The output goes to stdout, failures to stderr, always.** There is no quiet mode and no "errors only" mode; capture both streams deliberately when sweeping the full process table, or your log gets interleaved diagnostics from every kernel thread you lack rights to inspect.

## Exit Status

- `0` — every requested PID reported successfully.
- `1` — at least one PID failed (nonexistent, permission denied); the successes are still printed, failures go to stderr.

## Related Commands

- [`pidof`](./pidof.md) — exact-name PID lookup; the usual front end for pwdx.
- [`pgrep`](./pgrep.md) — attribute-based PID selection to feed pwdx.
- [`pkill`](./pkill.md) — same selection machinery, for acting on the processes you found.
- [`ps`](./ps.md) — `ps -o cwd` is not portable, but ps identifies candidates; pwdx resolves their directories.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — procfs conventions and process lifecycle context.

## Interview Questions

### Q: How do you find which process is preventing an empty directory from being removed?

Any process whose working directory (or open file descriptor) lies inside the tree keeps the inode busy. `pwdx $(ps -eo pid=) | grep /that/dir` lists every process cwd'd into it; follow up with `ls -l /proc/<pid>/fd` for fds pointing into the tree. The rmdir/`rm -rf` then succeeds once those processes exit or `chdir` away — a classic with long-lived services started from a since-replaced deployment directory.

### Q: What does the ` (deleted)` suffix in pwdx output tell you?

That the process's working directory has been unlinked but the process still holds the dentry/inode, so the directory's storage cannot be reclaimed until it dies. This is the cwd-flavored version of the "deleted but open file eats disk space" phenomenon: disk usage stays high, `df` disagrees with `du`, and the fix is restarting or chdir-ing the offending process — which you can only identify by sweeping `/proc` (pwdx makes that a one-liner).

### Q: Is pwdx just `readlink /proc/PID/cwd`? Why does the binary exist?

Functionally yes, and that is its virtue: it encodes the procfs knowledge (the `cwd` symlink, the `(deleted)` marker, the PID: prefix, the exit contract) in a stable interface that exists on every Linux with procps, including ones where your shell aliases or `/usr/bin/env` tricks make raw procfs poking awkward. It is also safer than `ls -l /proc/PID/cwd` in scripts because output does not depend on `ls` formatting or locale.

### Q: Why does `pwdx 1` fail as a normal user, and what governs that?

`/proc/1/cwd` is owned by root and the kernel restricts procfs introspection of another user's (especially a privileged) process to root — the same guard that hides `/proc/1/maps` or its fds. Hardened systems go further (hidepid mount options, Yama-style restrictions), so scripts must treat "Permission denied" as an expected outcome, not a bug, and run under the target user or root when they need complete sweeps.

### Q: A monitoring script does `pwdx $(pgrep -f worker)` and fails intermittently with exit 1. What is happening and how do you fix it?

Two overlapping causes: workers churning means a PID from `pgrep` can be gone by the time `pwdx` runs (No such process), and the workers may legitimately run with a deleted cwd during a rolling deploy. Since pwdx exits 1 if *any* argument failed, the aggregate call is wrong for monitoring. Fix by looping PID-by-PID, treating stderr-only failures as ignorable, and matching on the path after stripping ` (deleted)`.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/pwdx.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
