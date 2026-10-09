# sysctl — read and write kernel runtime parameters

## Overview

`sysctl` is the CLI for the kernel's runtime configuration: every tunable the kernel exposes lives as a file under `/proc/sys`, and `sysctl` reads and writes them by dotted name — `vm.swappiness` is `/proc/sys/vm/swappiness`. It ships in the `procps` package at `/usr/sbin/sysctl` (section 8: it administers the system) and is the tool behind the phrase "set `net.ipv4.ip_forward`": one-off `sysctl -w`, persistent `/etc/sysctl.d/*.conf`, bulk re-apply `sysctl --system`.

It is often confused with three neighbors: writing `/proc/sys` files directly with `echo` (same effect, no name mapping or config-file loading), `modprobe`/module parameters (per-driver knobs under `/sys/module/*/parameters`, a different tree), and `systemd-sysctl` (the boot-time loader that applies the very config files `sysctl -p` reads). The interview gravity is the mapping rule and the persistence story — sysctl writes vanish at reboot unless they also land in a config file.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 8 |
| Path | /usr/sbin/sysctl |
| First appeared | BSD lineage; Linux implementation in procps/procps-ng |
| Standards | None (parameter set is entirely kernel-specific) |

## Synopsis

```
sysctl [options] [variable[=value] ...]
```

Common one-line forms:

```
sysctl vm.swappiness                    # read one value
sysctl -a | grep ip_forward             # search everything
sysctl -w net.ipv4.ip_forward=1         # write, runtime only
sysctl -p                               # re-apply /etc/sysctl.conf
sysctl --system                         # apply every system config dir, boot-style
```

## How It Works

### The mapping rule

The whole tool is a naming convention over `/proc/sys`:

```
kernel.hostname     →  /proc/sys/kernel/hostname
vm.swappiness       →  /proc/sys/vm/swappiness
net.ipv4.ip_forward →  /proc/sys/net/ipv4/ip_forward

dotted name  ==  path with dots replaced by slashes, rooted at /proc/sys
```

The reverse works too: `sysctl` accepts `/proc/sys/net/ipv4/ip_forward` or slash form `net/ipv4/ip_forward` directly — which matters for names containing dots *inside* a component (interface names like `eth0.100` in `net/ipv4/conf/eth0.100/...`), where the dotted form is ambiguous and the slash form is exact. The tree's top-level directories (`fs`, `kernel`, `net`, `vm`, `debug`, `dev`, `abi`) are the menu of subsystems:

```
/proc/sys/
├── fs/        fs.file-max, fs.aio-max-nr, fs.inotify.max_user_watches
├── kernel/    kernel.hostname, kernel.panic, kernel.sysrq, kernel.pid_max
├── net/       net.ipv4.ip_forward, net.core.somaxconn, net.ipv4.tcp_syncookies
└── vm/        vm.swappiness, vm.overcommit_memory, vm.dirty_ratio
```

### Reading

Reading is `cat` with a friendlier name and error handling: `sysctl vm.swappiness` opens the file and prints `vm.swappiness = 60`. `-n` prints values only (script-friendly), `-N` prints names only (completion and iteration), `-b` prints the raw value without a trailing newline, and `-a` dumps everything — thousands of lines, best piped or filtered with `-r PATTERN` (extended regex):

```
$ sysctl vm.swappiness
vm.swappiness = 60
$ sysctl -n kernel.ostype
Linux
$ sysctl -N vm | head -3           # names only — feed to loops
vm.admin_reserve_kbytes
vm.block_dump
vm.compact_unevictable_allowed
$ sysctl net.ipv4.ip_forward
net.ipv4.ip_forward = 0
```

Values can be multi-word (`kernel.hostname = my box`) and tab-separated lists (`fs.dentry-state` prints six numbers on one line) — which is why `-n` plus `cut`/`awk` is the usual script idiom.

### Writing

```
sysctl -w net.ipv4.ip_forward=1     # explicit form
sysctl net.ipv4.ip_forward=1        # recent procps also infers write mode
```

The write is a plain open-for-write on the `/proc/sys` file: it requires root, it takes effect immediately, and it lives in RAM only — gone at reboot unless recorded in a config file (see Persistence). Values with spaces need the whole `variable=value` argument quoted, and per-key failures are reported individually (`sysctl: permission denied on key "vm.swappiness"` — exactly what an unprivileged user or a locked-down container produces). `--dry-run` prints what *would* be written without touching anything, and `-q` suppresses the echo of applied values.

```
$ sysctl -w net.ipv4.ip_forward=1           # typical success as root
net.ipv4.ip_forward = 1
$ sysctl -w 'kernel.domainname = example.org'   # value with a space: quote it all
$ sysctl -w vm.swappiness=10                # as non-root / locked container:
sysctl: permission denied on key "vm.swappiness"
```

### Loading config files: -p and --system

`-p [FILE]` (default `/etc/sysctl.conf`) applies `key = value` lines from one file — the runtime re-apply after an edit. `--system` applies the whole hierarchy the way boot does, in the precedence order documented by the man page:

```
1. /etc/sysctl.d/*.conf
2. /run/sysctl.d/*.conf
3. /usr/local/lib/sysctl.d/*.conf
4. /usr/lib/sysctl.d/*.conf
5. /lib/sysctl.d/*.conf
6. /etc/sysctl.conf                ← read last
```

Two rules govern conflicts: all files are sorted lexicographically by filename *regardless of which directory they live in*, and once a given filename has been loaded, same-named files in later directories are ignored (shadowed). For a key set multiple times, the last assignment wins. Config syntax is `key = value` with `#` comments; a leading `-` on a key (`-kernel.unused = 1`) suppresses the error if the key does not exist on this kernel — the standard trick for files shared across kernel versions.

### Persistence: two halves

A setting has two independent halves, and forgetting one is the classic mistake:

```
        "set vm.swappiness=10"
                 │
     ┌───────────┴─────────────┐
     ▼                         ▼
 sysctl -w                /etc/sysctl.d/99-swap.conf
 (write /proc/sys file)   (key = value line)
     │                         │
     ▼                         ▼
 NOW: kernel honors it     boot: systemd-sysctl.service
 dies at reboot            replays every sysctl.d file
                           (or sysctl --system / -p to replay now)
```

```
sysctl -w vm.swappiness=10          # half 1: NOW (RAM, dies at reboot)
echo 'vm.swappiness=10' > /etc/sysctl.d/99-swap.conf
sysctl --system                     # half 2: FOREVER (file; applied now + at boot)
```

At boot, `systemd-sysctl.service` applies the same file family (`/etc/sysctl.d`, `/run/sysctl.d`, the vendor dirs, and `/etc/sysctl.conf`) — so a correct sysctl.d entry needs no cron, no rc.local, no `sysctl -p` in a unit. `sysctl -p` is merely the manual "apply again now" for people who just edited the default file.

### Tunables worth having at your fingertips

| Key | What it controls | Interview cue |
| --- | --- | --- |
| `vm.swappiness` | Tendency to swap anonymous pages vs reclaim page cache (default 60) | A preference weight, not a swap switch |
| `net.ipv4.ip_forward` | IPv4 routing between interfaces | The Docker/router/LXC prerequisite |
| `net.ipv4.tcp_syncookies` | SYN-flood resilience | Usually already 1; checked after hardening audits |
| `net.core.somaxconn` | Max listen-queue length per socket | Bumped for high-connection services |
| `fs.file-max` | System-wide open-file cap | Distinct from `ulimit -n`, which is per-process |
| `vm.overcommit_memory` | Memory-alloc policy (0/1/2) | 2 + `vm.overcommit_ratio` = strict accounting |
| `kernel.panic` | Seconds to reboot after a panic | 0 = hang forever waiting for an operator |
| `kernel.sysrq` | Magic SysRq bitmask | 1 = everything enabled; 0 = disabled |

Names are hierarchical by subsystem, which is why `sysctl -N net.ipv4` is a quick curriculum on the IPv4 stack.

## Options That Matter

| Option | Effect |
| --- | --- |
| `variable` | Read one key (dotted, slashed, or absolute `/proc/sys` path) |
| `variable=value` | Write a key (with or without explicit `-w` on recent procps) |
| `-a` | List all parameters and values |
| `-N` | Names only — iteration and completion |
| `-n` | Values only — script-friendly |
| `-w` | Explicit write mode |
| `-p[=FILE]` | Apply a config file (default `/etc/sysctl.conf`) |
| `--system` | Apply every system config directory in precedence order |
| `-r PATTERN` | Only apply/list keys matching an ERE |
| `-e` | Ignore errors about unknown keys |
| `-q` | Quiet: do not echo values as they are set |
| `--dry-run` | Show what would be written; write nothing (recent procps) |
| `-b` | Print value without trailing newline |
| `--deprecated` | Include parameters flagged deprecated |

## Usage Patterns

```bash
# Read with both name styles
sysctl vm.swappiness
sysctl net/ipv4/ip_forward

# Enable routing right now (and note: runtime only)
sysctl -w net.ipv4.ip_forward=1

# Find a tunable when you only half-remember the name
sysctl -a | grep -i swappiness
sysctl -a | grep '^net.ipv4.tcp_' | head -20

# Iterate names without values (completion, audits)
sysctl -N vm | head -20

# Re-apply the default config after editing it
sysctl -p

# Apply one drop-in file you just wrote
sysctl -p /etc/sysctl.d/99-tuning.conf

# Apply the entire system policy exactly as boot would
sysctl --system

# Rehearse a write before doing it
sysctl --dry-run vm.swappiness=42

# Value-only reads for scripts
sysctl -n kernel.pid_max

# One-off temp change with a self-reverting guard for tests
old=$(sysctl -n vm.swappiness); sysctl -w vm.swappiness=10
# ... run the test ...
sysctl -w vm.swappiness=$old

# Bulk check after a kernel upgrade: which keys are gone?
sysctl -p 2>&1 | grep -v ' = '

# Show what a boot-time apply would change, per file
sysctl --system --dry-run 2>/dev/null | head

# Drop-in file for one concern — the sysctl.d way
cat > /etc/sysctl.d/90-router.conf <<'EOF'
net.ipv4.ip_forward = 1
net.ipv4.conf.all.accept_redirects = 0
EOF
sysctl -p /etc/sysctl.d/90-router.conf

# Audit: which keys differ from distro defaults? (diff against a dump)
sysctl -a > /tmp/now.txt; diff /tmp/baseline.txt /tmp/now.txt
```

## Nuances and Gotchas

- **`-w` is RAM-only.** Every `sysctl -w` evaporates at reboot; if the change mattered, it also belongs in `/etc/sysctl.d/*.conf`. Postmortems love finding the `-w` that was never written down.
- **Permission denied is structural, not a bug.** `/proc/sys` is root-owned, and containers routinely mount it read-only or strip the capability — even *root* inside an unprivileged container gets `permission denied on key`. Distinguish "wrong user" from "locked-down environment" before retrying harder.
- **Keys come and go between kernels.** Scripts that assume `net.ipv4.tcp_tw_recycle` exists (removed) or that new keys exist on old kernels fail mid-deploy; guard with `-e`, the `-` prefix in config files, or `-N` probing.
- **Precedence is lexicographic, then shadowing.** Same-named files across directories shadow (first loaded wins the name slot); different-named files compete key-by-key with *last assignment wins*. The historical procps 3.x behavior differed — old advice about "which directory wins" may be stale on 4.x.
- **`/etc/sysctl.conf` is the compatibility fallback**, read last under `--system`; new drop-ins belong in `/etc/sysctl.d/NN-name.conf` where NN orders the lexicographic sort. Debian ships a README in that directory explaining the split.
- **The dotted name is a lie for dotted components.** `net.ipv4.conf.eth0.100.forwarding` cannot be parsed unambiguously; use the slash form (`net/ipv4/conf/eth0.100/forwarding`) or the `all`/`default` aggregates where possible.
- **Some keys are set by other machinery.** Docker/netfilter modules rewrite `net.*` keys as they start, and systemd units may override your value after boot — verify *after* the full boot, not immediately after `sysctl --system`.
- **`-a` output is enormous and not stable.** Thousands of keys, kernel-version-dependent order; never parse it in full — filter with `-r` or iterate with `-N`.
- **`vm.swappiness` semantics in one line:** tendency of the kernel to swap anonymous pages versus reclaim page cache (default 60 on most distros); lower keeps anonymous memory resident, higher swaps earlier. It is a preference knob, not a swap on/off switch.
- **Writing requires the right capability, not just uid 0.** Containers commonly run root without `CAP_SYS_ADMIN` or with `/proc/sys` mounted read-only, so `sysctl -w` fails even for root inside them; the same command works on the host. Kubernetes users know this as "sysctls must be allowlisted (unsafe vs safe sysctls)".

## Exit Status

| Code | When |
| --- | --- |
| 0 | All requested reads/writes/loads succeeded |
| 1 | At least one key failed (missing, no permission, bad value) — unless `-e` suppressed unknown-key errors, or `-q`/batching semantics apply |

Because a single failed key fails the whole invocation, hardened scripts read exit status per key (`sysctl -n KEY || echo missing`) rather than in one bulk `-a`-style call.

## Related Commands

- [`top`](./top.md) — how you *observe* the effects of the tunables you set.
- [`free`](./free.md) — the memory picture that `vm.*` keys reshape.
- [`uptime`](./uptime.md) — verify a reboot actually happened after persistent changes.
- [`vmstat`](./vmstat.md) — watch `si`/`so` respond live to a swappiness change.
- [`ps`](./ps.md) — confirm the daemon that consumes a new setting actually restarted with it.
- [Process management](../../admin/process-management.md) — the kernel-side context for `kernel.*` and scheduler keys.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: What is sysctl actually doing when you type `sysctl -w vm.swappiness=10`?

Opening `/proc/sys/vm/swappiness` for writing and putting `10` in it — the dotted name is a path in disguise. Everything else is ergonomics: name mapping, error reporting, and the config-file loaders. This framing matters because it explains the tool's properties at a stroke: writes need permission on the file (root), they take effect immediately (the kernel handler runs on write), and they persist only as long as the kernel's copy of the value does — i.e. not across a reboot unless the same write is replayed from a config file.

### Q: Make net.ipv4.ip_forward=1 survive a reboot. What exactly do you do and why both halves?

One write and one file: `sysctl -w net.ipv4.ip_forward=1` makes routing work *now* (a running service may need it immediately), and `echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-forwarding.conf` plus `sysctl --system` (or a reboot test) makes it *permanent*, because at boot `systemd-sysctl.service` replays every file in the sysctl.d hierarchy. Doing only the `-w` loses the setting on the next reboot; doing only the file leaves the box unforwarded until then. The `sysctl --system` immediately after the file write doubles as a syntax check of what you just created.

### Q: How does `sysctl --system` order and de-conflict config files?

It reads the sysctl.d directories — `/etc`, `/run`, `/usr/local/lib`, `/usr/lib`, `/lib` — followed by `/etc/sysctl.conf` last. Within that hierarchy all files are sorted lexicographically by filename regardless of directory, and a filename loaded from an earlier directory shadows same-named files later in the chain. When the same key appears in multiple files, the last assignment encountered wins. So name collisions across directories are resolved by shadowing, and key collisions across differently-named files are resolved by assignment order — two different mechanisms worth distinguishing in an answer.

### Q: Your provisioning script does `sysctl -p app.conf` and fails on one key on older kernels. Fix it properly.

Three escalating fixes: prefix the fragile key with `-` in the file (`-net.ipv4.tcp_tw_recycle = 1`) so a missing key is skipped silently; run with `-e` so unknown-key errors do not fail the invocation; or pre-probe with `sysctl -N KEY` and write the key conditionally from the script. The underlying fact is that the sysctl surface is kernel-version-dependent — keys are added and removed (tcp_tw_recycle was removed outright) — so portable config files must tolerate absence, which is precisely what the `-` syntax exists for.

### Q: What does vm.swappiness control, and what would you set it to?

It weights the kernel's choice between reclaiming page cache and swapping out anonymous pages: low values (1–10) keep anonymous memory resident and prefer dropping cache; high values swap earlier to preserve cache; the distro default is 60. There is no universal right answer — databases on dedicated boxes often run low values because their buffer pools are their cache, while memory-constrained generalists may prefer the default — but the interview point is knowing it is a *tendency* knob, that changes apply immediately via `sysctl -w`, and that swappiness cannot stop swapping outright.

### Q: How do sysctl keys differ from module parameters and kernel command line?

Three different lifetimes and locations. Sysctl keys live under `/proc/sys`, are runtime-readable/writable, and are config-file-persistent via sysctl.d. Module parameters live under `/sys/module/<name>/parameters`, are usually set at module load time (`modprobe name.param=x` or modprobe.d), and many are read-only at runtime. Kernel command-line parameters (`/proc/cmdline`) are fixed at boot and often control earlier boot behavior — `sysctl` cannot change those at all. Knowing which knob lives where is half the answer in any "tune the kernel" question.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/sysctl.8.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
