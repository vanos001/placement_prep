# pgrep — find processes by name or attributes

## Overview

`pgrep` answers one question efficiently: "which PIDs match these criteria?" It scans the process table, applies a pattern plus any number of attribute filters (user, parent, terminal, process group, run state, namespace, cgroup), and prints matching PIDs — one per line — with zero output decoration. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/pgrep`, together with its two siblings built from the same code: `pkill` (signals what it finds) and `pidwait` (waits for what it finds to exit).

`pgrep` exists to replace the fragile `ps aux | grep ... | awk '{print $2}'` idiom, and its exit code (`0` = something matched) makes it a natural boolean probe in scripts. It is often confused with `pidof` (exact name matching, no regex, sysvinit heritage) and with the `ps | grep` pipeline it deprecates — including that pipeline's self-match problem, which `pgrep` does not have: it never reports itself.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/pgrep |
| First appeared | procps, late 1990s (same era as Solaris 7's pgrep) |
| Standards | none; procps-ng convention (also on Solaris, AIX, busybox with caveats) |

## Synopsis

```
pgrep [options] pattern
```

Common one-line forms:

```
pgrep -x nginx              # exact process-name match
pgrep -f 'python.*worker'   # match the full command line
pgrep -u root -l sshd       # root's sshd processes, name listed
pgrep -c -x sleep           # count, no PIDs
pgrep -P 909                # children of PID 909
pgrep -n -x sleep           # the most recently started match
```

## How It Works

### What the pattern matches: comm vs cmdline

The core design decision of `pgrep` is *which string* the regex runs against. Without `-f`, the target is the process **name** — the `comm` value, i.e. field 2 of `/proc/<pid>/stat` — which the kernel caps at 15 characters. With `-f`, the target is the **full command line** from `/proc/<pid>/cmdline`, with NUL bytes joined into one string:

```
       /proc/<pid>/stat field 2        /proc/<pid>/cmdline
       ("comm", max 15 chars)          (full argv, joined with spaces)
              │                                │
   default    │                                │  -f
   target     ▼                                ▼
        pgrep nginx                     pgrep -f 'nginx: worker'
        pgrep -x nginx                  pgrep -fx '/usr/sbin/nginx'
```

Everything else follows from this. A process started as `/usr/bin/python3 /opt/app/worker.py` has comm `python3` but a long cmdline; `pgrep worker` finds nothing (too short? no — comm is just `python3`), while `pgrep -f worker` finds it. Conversely, `pgrep -f` matches *arguments* too, which is powerful (`pgrep -f '--config /etc/foo'`) and dangerous (it can match unrelated words in unrelated argvs).

### The 15-character rule

Because `comm` is capped at 15 visible characters (`TASK_COMM_LEN` is 16 including the NUL), a pattern longer than 15 characters cannot ever match without `-f` — and `pgrep` tells you so:

```
$ pgrep reallylongprocnamehere
pgrep: pattern that searches for process name longer than 15 characters
will result in zero matches
Try `pgrep -f' option to match against the complete command line.
```

Related traps: names containing characters the kernel rewrote (spaces become... actually comm can contain spaces only via prctl), and regex metacharacters in names. `-x` demands a whole-string match, but the pattern stays an extended regular expression — `pgrep -x 'a.c'` matches `abc`.

### Regex semantics and -x anchoring

The pattern is a POSIX **extended regular expression**, matched *anywhere* inside the target string by default:

```
pgrep ssh          # matches sshd, ssh-agent, sshpass, /usr/bin/ssh
pgrep -x ssh       # matches only a process literally named "ssh"
pgrep '^sshd$'     # same as -x for this case, regex spelling
pgrep 'nginx: (worker|master)'   # full ERE, alternation works
```

`-i` makes matching case-insensitive. There is no `-F`-style fixed-string option; to search for a name containing metacharacters, either escape them or use `pidof`, which matches literally.

### Selection flags: AND between flags, OR within a list

Every selection option must all match simultaneously (AND); within one option, a comma- or blank-separated list is OR:

```
$ pgrep -u root sshd           # name matches sshd AND euid is root
$ pgrep -u root,daemon ssh     # (root OR daemon) AND name matches
```

| Flag | Selects by |
| --- | --- |
| `-u ID,...` | effective UID (user) |
| `-U ID,...` | real UID (matters across sudo/setuid) |
| `-g PGID,...` | process group ID |
| `-G GID,...` | real group ID |
| `-P PPID,...` | parent PID — the cheap child-of query |
| `-s SID,...` | session ID |
| `-t TTY,...` | controlling terminal (`pgrep -t pts/2`) |
| `-r STATE,...` | run state: `D,S,Z,T,R,I` and friends |
| `--ns PID` | same namespaces as the given PID |
| `--nslist ns,...` | which namespaces `--ns` considers |
| `--cgroup grp,...` | cgroup v2 membership |
| `-A` | exclude pidwait's own ancestors |

`-P` is the workhorse for process trees: `pgrep -P "$(pgrep -x supervisord)"` lists a supervisor's children in one pipeline-free step.

### Output modifiers

- `-l` prefixes each PID with the process name (always on for a terminal when `-a`/`-l` omitted? no — plain `pgrep` prints bare PIDs; `-l` is explicit listing).
- `-a` prints PID plus the **full command line** — the quick "what exactly is running" view.
- `-d STR` changes the output delimiter (one line: `pgrep -d, -x sleep` → `4711,4712`).
- `-c` suppresses PIDs and prints a count; the count 0 still exits 1.
- `-n` (newest) and `-o` (oldest) reduce the result set to one process by start time; `-O SECONDS` keeps only processes older than SECONDS.
- `-w` ("lightweight") widens matching to threads, listing TIDs.
- `-F pidfile` reads PIDs from a file instead of scanning; `-L` additionally requires the pidfile to be locked.

```
$ pgrep -a -x caddy
2 caddy run --config /app/Caddyfile --adapter caddyfile
```

### The scan, in order

Each invocation walks `/proc` numerically, and for every candidate task applies three gates in sequence:

```
for each pid in /proc/[0-9]*:
    1. selection gates  -u -U -g -G -P -s -t -r --ns --cgroup
       (all must pass; lists inside one flag are OR)
    2. name gate        regex vs comm  (or vs cmdline with -f)
    3. modifiers        -v invert, -n/-o newest/oldest, -O older
       -> collect pid
report: -c count | -l name | -a cmdline | bare pids
```

The cost is one pass with a handful of small file reads per candidate — microseconds on typical systems, and no `fork`/`exec` of helpers. Output comes out in ascending PID order in practice, but treat that as luck, not contract: sort explicitly if order matters.

### Self-exclusion and the ancestors question

`pgrep` never lists itself — the classic `ps aux | grep foo` self-match cannot happen. But two subtler cases remain:

- A **parent shell or script** whose own cmdline contains the pattern will match: `bash -c 'pgrep -f worker'` — the `bash -c` cmdline contains `worker`. `-A` (`--ignore-ancestors`) excludes pgrep's own ancestry, which is exactly the guard for `pgrep -f` inside wrapper scripts.
- With `-f`, the pattern is compared against other users' command lines too, which may leak information or match unintended targets — scope with `-u` whenever possible.

### The `ps aux | grep` autopsy

Why the old pipeline is worse, point by point:

```
$ ps aux | grep nginx | grep -v grep | awk '{print $2}'
```

1. **Self-match:** the `grep nginx` process matches its own pattern; the `grep -v grep` band-aid is the tell.
2. **Truncation:** `ps aux` clips CMD to terminal width (use `-ww`), so long cmdlines produce false negatives.
3. **Column drift:** field positions shift with STAT length and user names; `awk '{print $2}'` assumes the layout never changes.
4. **Two greps, a sort, and a full `ps` scan** versus one targeted `/proc` pass.
5. **No structured exit code:** you need `grep -c` gymnastics to learn whether anything matched; `pgrep` returns 0/1 natively.

`pgrep -a -f nginx` does the whole job in one process, and `pkill`/`pidwait` reuse the identical selection machinery.

## Options That Matter

### Matching

| Option | Effect |
| --- | --- |
| `-f, --full` | match against full command line, not just comm |
| `-x, --exact` | whole-string match (pattern still ERE) |
| `-i, --ignore-case` | case-insensitive matching |
| `-w, --lightweight` | include threads (TIDs) |
| `-v, --inverse` | negate the match set |
| `-A, --ignore-ancestors` | exclude pgrep's own ancestors |

### Output

| Option | Effect |
| --- | --- |
| `-l, --list-name` | print PID and process name |
| `-a, --list-full` | print PID and full command line |
| `-c, --count` | print count only (empty count still exits 1) |
| `-d, --delimiter STR` | separate PIDs with STR instead of newlines |
| `-n, --newest` | only the most recently started match |
| `-o, --oldest` | only the least recently started match |
| `-O, --older SECS` | only processes started more than SECS ago |

### Selection

| Option | Effect |
| --- | --- |
| `-u, --euid LIST` | effective user (name/UID) |
| `-U, --uid LIST` | real user |
| `-g, --pgroup LIST` | process group ID |
| `-G, --group LIST` | real group ID |
| `-P, --parent LIST` | parent PID |
| `-s, --session LIST` | session ID |
| `-t, --terminal LIST` | controlling terminal |
| `-r, --runstates LIST` | kernel run states (D,S,R,Z,T,I) |
| `-F, --pidfile FILE` | read PIDs from file |
| `-L, --logpidfile` | fail if pidfile is not locked |
| `--ns PID` / `--nslist` | namespace-based selection |
| `--cgroup LIST` | cgroup v2 membership |

## Usage Patterns

```bash
# Boolean probe: is the service running?
pgrep -x nginx >/dev/null && echo up || echo down

# List PIDs with names — the human-readable census
pgrep -l -u "$(id -un)" bash

# Full command line of every matching process
pgrep -a -f 'nginx: worker'

# Children of a supervisor process
pgrep -P "$(pgrep -x uv)"

# Count matches (exit code still reflects zero/nonzero)
pgrep -c -x sleep

# Comma-joined list for logs or xargs -d
pgrep -d, -f worker

# Newest instance only (e.g. latest editor session)
pgrep -n -x vim

# Restart-safety check: refuse to run twice
pgrep -x myjob >/dev/null && { echo "already running"; exit 1; }

# Find processes stuck in uninterruptible IO
pgrep -r D -l

# Everything in the same PID namespace as a container init
pgrep --ns 1 -l

# Feed matching PIDs into ps for a detail view (blank-separated lists work)
pgrep -f 'app/worker.py' | xargs -r ps -o pid,%cpu,rss,cmd -p

# Guard against matching your own wrapper script's cmdline
pgrep -A -f 'deploy.sh' -l

# Watch a service's worker PIDs until one disappears
watch -n 1 'pgrep -l -f "nginx: worker"'

# Existence check for a specific user's process only
pgrep -u deploy -x node >/dev/null 2>&1 || systemctl start nodeapp

# Pair pgrep with ps for the full row of an exact match
ps -o pid,user,stat,etime,cmd -p "$(pgrep -x caddy)"

# Everything whose effective user is NOT in the admin set (audit view)
pgrep -v -u root,deploy -l

# Oldest surviving instance (longest-running match)
pgrep -o -x python3
```

## Nuances and Gotchas

- **15-character comm cap.** Patterns longer than 15 chars silently match nothing without `-f`; `pgrep` warns on stderr but still exits 1. Long executable names (e.g. `containerd-shim-runc-v2` is 24 characters) require `-f` or a shortened pattern.
- **`-f` matches arguments, not just programs.** `pgrep -f tmp` matches `vim /tmp/notes` and `tail -f /tmp/x`; overbroad `-f` patterns in `pkill` are the classic footgun. Anchor patterns (`-f '^/usr/bin/app'`) and prefer `-x`.
- **`-x` is exact-length, still regex.** Metacharacters inside the pattern remain active; a literal match of `a.c` requires `pgrep -x 'a\.c'`. For literal semantics, use `pidof`.
- **Exit code 1 is data, not an error.** In scripts, guard `set -e` contexts: `pgrep -x foo || true`. But exit 2/3 (syntax/fatal) must not be swallowed by `|| true` — check `$?` explicitly when it matters.
- **The match set races with reality.** PIDs printed may exit (or be recycled) before you act on them; for act-on-match workflows use `pkill`/`pidwait`, which fuse selection with the action.
- **Threads and `-f`.** Threads share the parent's cmdline, so `-f` can "match" threads; without `-w`, pgrep reports the process level. Kernel threads (kworkers etc.) are generally not what you'll match, but name collisions with kernel threads are possible when matching by short names.
- **`-u` vs `-U` after sudo.** A sudoed process has real UID = original user, effective UID = root. `pgrep -u root` catches it, `pgrep -U root` does not. Interviewers probe this distinction precisely.
- **Quoting is on you.** The pattern is one shell word; `pgrep -f nginx: worker` splits into two arguments and treats `worker` as an operand — always quote regexes, especially those containing spaces or `|`.
- **busybox pgrep is a subset.** No `--ns`, `--cgroup`, `-r`, or `-O` there; portable scripts should stick to `-f -x -l -c -u -P` and the exit code.
- **`-F pidfile` trusts the file.** PIDs read from a pidfile are not validated against the pattern or the selection flags; a stale pidfile (reused PID for an unrelated process) makes `pgrep -F` report — and `pkill -F` signal — the wrong process. `-L` narrows it by requiring the pidfile to be locked, which live daemons typically hold.
- **`-c` changes the exit-code contract, not the selection.** `pgrep -c` prints 0 and exits 1 on no match — handy for thresholds, but scripts that do `count=$(pgrep -c ...)` under `set -e` still need `|| true`.
- **`pgrep -v` inverts the *whole* selection**, which combined with other flags can sweep in kernel-adjacent and system processes — almost never what a script wants; prefer explicit selection.

## Exit Status

| Code | Meaning |
| --- | --- |
| `0` | one or more processes matched the criteria |
| `1` | no processes matched |
| `2` | syntax error in the command line |
| `3` | fatal error (out of memory, etc.) |

The 0/1 pair is the API: `if pgrep -x foo; then ...` is an existence test with no output suppression needed (redirect stdout yourself).

## Related Commands

- [`pkill`](./pkill.md) — same selection machinery, but signals instead of listing.
- [`pidwait`](./pidwait.md) — same selection machinery, but blocks until matches exit.
- [`pidof`](./pidof.md) — literal exact-name lookup, no regex; sysvinit heritage.
- [`ps`](./ps.md) — the full snapshot view; pgrep is its surgical subset.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — where PID selection fits into signals and process trees.

## Interview Questions

### Q: Why is `pgrep` preferred over `ps aux | grep ... | awk '{print $2}'`?

Three concrete failure modes: the grep process matches its own pattern (the `grep -v grep` band-aid), `ps aux` truncates long command lines to terminal width causing false negatives, and awk column positions drift with STAT/user-name width. `pgrep` never matches itself, reads `/proc` directly with no width constraints, returns a clean 0/1 exit status, and composes with `pkill`/`pidwait` sharing the same selection flags. It is also one process instead of four.

### Q: A pattern of 20 characters returns nothing and pgrep warns about 15 characters. What is happening and what are the fixes?

Without `-f`, pgrep matches the process name from `/proc/<pid>/stat`, which the kernel caps at 15 visible characters, so any longer pattern is unmatchable by construction. Fixes: use `-f` to match the full command line from `/proc/<pid>/cmdline` (`pgrep -f pattern`), or shorten the pattern to fit within 15 characters. The same cap explains why `ps -o comm` truncates names and why `/proc/<pid>/comm` shows at most 15 characters.

### Q: Explain the difference between `-u` and `-U` in pgrep.

`-u` matches the effective UID, `-U` the real UID. They diverge across setuid and sudo: a process started via `sudo service` runs with real UID = the invoking user and effective UID = root. So `pgrep -u root` lists it while `pgrep -U root` does not. The same duality applies to `-g` (effective group/session depending on form) versus `-G` (real group). Knowing which identity a security policy or audit should target is the point of the question.

### Q: How do you write a script that refuses to start if an instance is already running — and what are the edge cases?

`pgrep -x myjob >/dev/null && exit 1` or, to exclude wrapper-script ancestors that carry the name in their own cmdline, `pgrep -A -x`. Edge cases: pattern breadth (`-f` matching the script's own arguments), PID reuse races between check and start (a lockfile with `flock` is stronger), and exit-code discipline — under `set -e`, a no-match exit 1 kills the script unless guarded with `|| true`.

### Q: What does `pgrep -r D -l` show and why is it operationally useful?

It lists processes currently in the D (uninterruptible sleep) run state. A pile of D-state tasks is the signature of blocked storage — dead NFS server, wedged FUSE, failing disk — and those processes ignore all signals, including SIGKILL. Watching that set (or its growth) distinguishes "storage is stuck" from "CPU is busy", which changes the entire incident response.

### Q: How does pgrep avoid the self-match problem, and why does `-A` exist if it already excludes itself?

`pgrep` filters its own PID out of the result set, so the `grep`-matching-itself artifact cannot happen. But the *ancestors* are not excluded: a wrapper script whose own cmdline contains the pattern (`bash /usr/local/bin/deploy.sh worker`) matches `pgrep -f worker` and reports the wrapper instead of — or in addition to — the target. `-A`/`--ignore-ancestors` walks up pgrep's parent chain and excludes it, which is the correct default posture for `pgrep -f` inside scripts.

### Q: How do pgrep, pkill, and pidwait relate, and when would you use each?

They are one program with three personalities sharing identical selection flags: pgrep prints matches, pkill signals them, pidwait blocks until they exit. Use pgrep for inspection and boolean tests, pkill for signal delivery (its default is SIGTERM, not SIGKILL), and pidwait when a script must synchronize on the *end* of processes it did not spawn — a common shape in container supervisors and CI teardown.

### Q: When would you choose pidof over pgrep, or pgrep over pidof?

`pidof` for the sysvinit-shaped job: literal exact-name lookup, space-separated single-line output (`kill $(pidof foo)`), script matching with `-x`, zero regex surprises. `pgrep` when the query is an expression rather than a name — attribute filters (`-u`, `-P`, `-r`, `--ns`), counting, newest/oldest, full-cmdline matching with `-f`, and a machine-checkable exit code. pidof is also not a procps binary: on Debian it lives in sysvinit-utils, so minimal procps-only images may not have it.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/pgrep.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
