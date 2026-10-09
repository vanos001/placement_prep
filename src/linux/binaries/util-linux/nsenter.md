# nsenter — run a program in the namespaces of another process

## Overview

`nsenter` ("namespace enter") executes a program inside the Linux namespaces of another process, identified by PID or by namespace files. It is the standard tool for stepping *into* a running container, network namespace, or mount namespace from the host shell — the mechanism is the `setns(2)` syscall on `/proc/<pid>/ns/*` handles. It ships in the `util-linux` package at `/usr/bin/nsenter` and pairs with `unshare`, which creates new namespaces instead of entering existing ones.

You reach for it when the container runtime's own exec path is unavailable or insufficient: the container has no shell, the runtime socket is gone, you need host tooling (`tcpdump`, `strace`, `gdb`) inside the container's network or PID view, or you are debugging an initramfs/early-boot mount namespace. It is often confused with `chroot` (changes only the filesystem root view, no namespace switch), with `docker exec`/`kubectl exec` (which go through the runtime's API and its own process supervision), and with `su`/`setpriv` (credentials, not namespaces).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/nsenter |
| First appeared | util-linux 2.23 (2013) |
| Standards | Linux namespaces / `setns(2)`; not POSIX |

## Synopsis

```
nsenter [options] [<program> [<argument>...]]
```

Main one-line forms:

```
nsenter -t <pid> --all -- <cmd>            # enter every namespace of pid
nsenter -t <pid> -n -- ss -tlnp            # only the network namespace
nsenter -t <pid> -m -u -i -n -p -- bash    # the classic "enter container" set
nsenter --net=/run/netns/blue -- ip addr   # namespace file instead of a PID
```

## How It Works

### The setns dance

Every process owns namespace handles exposed at `/proc/<pid>/ns/<type>` (mnt, uts, ipc, net, pid, user, cgroup, time). Each is an atomic handle: opening one yields an fd; `setns(fd, nstype)` re-associates the calling process with it. `nsenter` opens the requested handles, orders the joins correctly, then `exec`s your program:

```
resolve -t PID (or namespace files)
open /proc/PID/ns/user        # user ns first if requested — capabilities are
  setns()                     # evaluated relative to the *owning* user ns
open ns/pid, ns/net, ns/ipc, ns/uts, ns/cgroup, ns/mnt
  setns() each
apply uid/gid (-S/-G) or --preserve-credentials
fork (unless -F), chdir (-w/-r), exec <program>
```

Joining requires `CAP_SYS_ADMIN` in the user namespace that *owns* the target namespace — being root on the host is normally sufficient; inside an unprivileged container it is not, because the container's user namespace owner is the host user.

### The PID namespace special case

`setns` into a PID namespace does not move your existing process into it — PID namespace membership is fixed at fork time. The association applies to processes you spawn *after* the join. This is why `nsenter` forks before exec by default, and why, after entering only a PID namespace, `ps` still shows the old `/proc` until you also enter (or remount) a matching mount namespace. The same mount-ns/pid-ns pairing is why the classic container-entry command lists `-m` and `-p` together.

### Credentials

Entering a user namespace normally re-executes you as uid/gid 0 *inside that mapping* (nsenter does `setuid(0)`/`setgid(0)` when permitted) — you become "root" with only the capabilities that namespace grants. `--preserve-credentials` keeps your original uid/gid and capability set instead, which is what you want when the target namespace's mapping does not map root, or when you deliberately stay a normal user. `-S`/`-G` set explicit uid/gid after joining; `--keep-caps` retains capabilities across the uid change.

### Working directory and root

Your cwd inode travels with you; if it is not meaningful in the new mount namespace (e.g., a path that only exists on the host), commands fail or resolve oddly. `-w <dir>` chdirs after entering (defaults to the new root when `-r` is given); `-r` chroots to the target's root directory. Recent util-linux releases add `-W/--wdns`, which resolves the working directory *after* the namespace switch, plus `-e/--env` (adopt the target's environment) and `-c/--join-cgroup`.

### The handles behind -t and =file

`/proc/<pid>/ns/<type>` entries are magic symlinks: `readlink` shows `net:[4026532285]`-style instance ids, and *opening* one yields the fd that `setns()` consumes. Three consequences:

- Two processes share a namespace iff their ns files have the same device+inode — `stat -c '%d:%i' /proc/PID/ns/net` is the canonical comparison, and `lsns` is a prebuilt scan of exactly that across all of /proc.
- Holding the fd open keeps the namespace alive even after its last member process exits — how `ip netns` keeps "empty" named namespaces addressable, and how leaking fds silently pins namespaces in memory.
- The instance numbers are not stable across reboots; only a runtime (dev,ino) comparison is meaningful, never a hardcoded id.

The `=[file]` forms on the namespace options take exactly these handles: `--net=/var/run/netns/blue` is the same setns() call with an explicitly named fd source, which is why `ip netns exec` and `nsenter --net=` are functionally identical — `ip netns` just manages the bind mounts for you.

```bash
# Same-network-namespace test, the kernel way
[ "$(stat -c %d:%i /proc/1/ns/net)" = "$(stat -c %d:%i /proc/$PID/ns/net)" ] \
  && echo "same net ns" || echo "different net ns"
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t`, `--target <pid>` | Take all requested namespaces from this process |
| `-m`, `--mount[=file]` | Enter mount namespace (file defaults to target's) |
| `-u`, `--uts[=file]` | Hostname/domainname namespace |
| `-i`, `--ipc[=file]` | SysV IPC / POSIX message queues |
| `-n`, `--net[=file]` | Network namespace (interfaces, sockets, routes) |
| `-p`, `--pid[=file]` | PID namespace (applies to children) |
| `-C`, `--cgroup[=file]` | cgroup namespace |
| `-U`, `--user[=file]` | User namespace — join first; enables the rest unprivileged |
| `-a`, `--all` | Enter every namespace of the target |
| `-S` / `-G` | Set uid / gid in the entered namespace |
| `--preserve-credentials` | Keep uid/gid/caps instead of becoming ns-root |
| `--keep-caps` | Retain capabilities across the uid/gid change |
| `-r`, `--root[=dir]` | chroot to the target root (default target's `/`) |
| `-w`, `--wd[=dir]` | Set working directory after entering |
| `-F`, `--no-fork` | Do not fork before exec (one fewer process) |
| `-Z`, `--follow-context` | Adopt the target's SELinux context |

Newer util-linux (2.39+) adds a time namespace (`-T`), `--user-parent`, `-N/--net-socket` (join via an open socket fd), and the `-W`/`-e`/`-c` conveniences mentioned above; do not rely on them on stable releases.

## Usage Patterns

```bash
# Enter a container by host PID with host tooling, as its "root"
PID=$(docker inspect -f '{{.State.Pid}}' web)
nsenter -t "$PID" -m -u -i -n -p -- bash
```

```bash
# Debug the container's network with host tcpdump (no tcpdump inside)
nsenter -t "$PID" -n -- tcpdump -i eth0 -nn
```

```bash
# Same for the mount view only (inspect its /etc without exec in container)
nsenter -t "$PID" -m -- cat /etc/nginx/nginx.conf
```

```bash
# Enter everything, preserving who you are
nsenter -t "$PID" -a --preserve-credentials -- bash
```

```bash
# Join a named network namespace created with ip netns
nsenter --net=/var/run/netns/blue -- ip -br addr
```

```bash
# Inspect the init system's mount namespace (host root)
nsenter -t 1 -m -- findmnt
```

```bash
# Enter as a specific uid inside the target user namespace
nsenter -t "$PID" -U -S 1000 -G 1000 -- id
```

```bash
# Keep current creds while switching mount namespace (bind-mount experiments)
nsenter -t "$PID" -m --preserve-credentials -- mount --make-rprivate /
```

```bash
# Avoid the intermediate fork (scripting; program becomes nsenter's child directly)
nsenter -F -t "$PID" -n -- python3 -c 'import socket; print(socket.gethostname())'
```

```bash
# SELinux systems: also adopt the target's security context
nsenter -t "$PID" -a -Z -- bash
```

```bash
# Runtime-agnostic entry: works for containerd, CRI-O, podman — any PID
PID=$(pgrep -f 'nginx: master' | head -1)
nsenter -t "$PID" -m -u -i -n -p -- bash

# Per-namespace diff of two processes: which namespaces do they actually share?
for ns in mnt net pid user uts ipc cgroup; do
  if [ "$(stat -c %d:%i /proc/1/ns/$ns)" = "$(stat -c %d:%i /proc/$PID/ns/$ns)" ]; then
    echo "$ns: same"; else echo "$ns: differs"; fi
done

# Snapshot a container's /etc without a shell inside the image
nsenter -t "$PID" -m -- tar -C / -cf - etc | tar -C /backup/etc-snap -xf -

# Enter the network of a veth peer by namespace file (no target PID needed)
nsenter --net=/var/run/netns/blue -- ip -br addr

# Run a one-shot command with the container's environment, not yours
nsenter -t "$PID" -m -u -i -n -p -e -- env | head -5
```

## Nuances and Gotchas

- **Capabilities are the gate, not uid.** `setns` needs `CAP_SYS_ADMIN` in the owning user namespace. A container that drops `CAP_SYS_ADMIN` from its own users cannot be entered *from inside*; from the host you act with host capabilities over the target's namespaces — different namespaces have different owning user namespaces, and each join is checked against its own owner.
- **PID namespace entry is for children.** Your `ps` does not switch. Pair `-p` with `-m` (and consider `-w /`) or you get a hybrid view that confuses shells and debugging.
- **The fork matters.** Default forking lets the intermediate process reap the child; `-F` removes one hop (useful for `$!`-style scripting) but means nsenter's own process image is replaced — anything after exec in a script must account for that.
- **`/proc` is per mount namespace.** After `-m` without remounting proc, `/proc` may show the *host* PID space even though you are in the container's PID namespace. `mount -t proc proc /proc` inside, or enter both namespaces, to line them up.
- **Stale targets.** `-t` on a dead PID fails immediately; in scripts, re-resolve PIDs (`pgrep`, runtime inspect) rather than caching them — container PID reuse is real.
- **`--preserve-credentials` vs the default.** The default "become root of the user namespace" fails when that namespace has no mapping for uid 0; if you see EPERM from the uid switch (not the setns), that is why — pass `--preserve-credentials` or explicit `-S/-G`.
- **No cgroup migration by default.** Joining mount/net/pid namespaces does not move your process into the container's cgroup — resource usage stays attributed to your original cgroup. Newer `-c/--join-cgroup` opts in.
- **Exit status is the child's.** nsenter reports the program's exit code; recent util-linux man pages document 124 when the program is killed by a signal. nsenter's own failures (bad PID, EPERM on setns) are distinct non-zero codes.
- **Not a sandbox.** Entering namespaces is a *privilege escalation into a context*, not isolation. Host root via nsenter inside a "rootless" container is exactly how privilege boundaries get audited — and broken.
- **Namespace ids look stable but are not.** `[4026531840]`-style instance numbers repeat across reboots only by allocation-order coincidence. Scripts must compare `stat -c %d:%i` pairs at runtime; nothing should hardcode ids.
- **Entering a net namespace keeps your host sockets.** Connections and listening sockets opened before the join stay bound to the *old* namespace; `ss -tlnp` inside the freshly entered ns shows no new listeners until you re-exec. nsenter's fork+exec does the re-exec for you; a long-lived agent must re-exec itself.
- **`-a/--all` follows the target's *current* set.** If the target PID is a runtime shim that has not unshared yet, `-a` enters host namespaces — verify the target is the container init (`cat /proc/$PID/cgroup`, low pid inside its pid ns) before trusting an "entered the container" result.
- **setns() requires a single-threaded caller for pid/user namespaces.** A multithreaded process gets `EINVAL` joining CLONE_NEWPID/CLONE_NEWUSER — invisible through nsenter (it forks) but a real trap for reimplementing the join inside threaded programs; the robust pattern is shelling out to nsenter.
- **`--all` plus `-S/-G` is a credentials minefield.** Entering a userns and then forcing an explicit uid that the mapping does not cover fails late and confusingly; when scripting arbitrary targets, probe the mapping (`cat /proc/$PID/uid_map`) before choosing credential flags.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0–255 | Exit status of the executed program |
| 1 | nsenter's own failure: unknown target, setns denied (EPERM), bad namespace file |
| 124 | The program was terminated by a signal (documented in recent util-linux) |

## Related Commands

- [`unshare`](https://manpages.debian.org/bookworm/util-linux/unshare.1.en.html) — the inverse operation: create and run in *new* namespaces.
- [`mount`](./mount.md) — the mount namespace is the richest one to enter; `-N`/`setns` context lives there too.
- [`pivot_root`](./pivot_root.md) — what container init typically does inside the mount namespace you just entered.
- [`chrt`](./chrt.md) — same "run a program with modified execution properties" launcher family.
- [`process-management`](../../admin/process-management.md) — PIDs, `/proc`, and process credentials underpinning `-t`.
- [`internals`](../../internals.md) — namespace primitives and how `CLONE_NEW*` maps to `setns`.
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: How does `nsenter -t <pid> -m -u -i -n -p -- bash` differ from `docker exec`?

`nsenter` runs on the host with your host credentials and joins the target process's namespaces directly via `setns`; the shell you get is a *host* process wearing container namespaces, with host-visible `/proc` handling and no runtime involvement. `docker exec` asks the containerd-shim to spawn a process inside the container (respecting its cgroups, user mappings, seccomp, and SELinux/AppArmor profiles). Consequences: nsenter works when the runtime socket or CLI is broken, bypasses runtime policy (auditors care), and its processes don't show up in container tooling; exec is the sanctioned, policy-respecting path.

### Q: Why does entering a PID namespace not change what `ps` shows, and how do you get a coherent view?

PID namespace membership is established at process creation and cannot be changed by `setns` for an existing process; it only affects subsequently forked children. To get a coherent container view you enter the mount namespace as well (so `/proc` you read is mounted inside that namespace), or explicitly remount proc: `nsenter -t PID -m -p -- bash` and then `mount -t proc proc /proc`. The PID/mount namespace pairing is the most common source of "half-entered container" confusion.

### Q: A teammate runs `nsenter -t 4242 -U -- id` inside an unprivileged container and gets EPERM. Explain.

`setns` on a user namespace requires `CAP_SYS_ADMIN` in the *owning* user namespace. Inside the container the teammate lacks it; joining is a capability-gated operation, not a uid-gated one. From the host, root holds `CAP_SYS_ADMIN` over the container's owning namespace and can enter. Fixes: run the join from the host, grant the capability deliberately (and understand the security implications), or restructure with `--preserve-credentials` after entering from a privileged context.

### Q: What does `--preserve-credentials` actually trade off?

By default, entering a user namespace makes you uid 0 there — convenient, because container tooling expects root, and the namespace mapping permits it. With `--preserve-credentials` you keep your original uid/gid and capabilities: required when the mapping has no uid 0 (some rootless setups), or when you want file writes to happen as your real uid rather than the namespace root. Trade-off: you keep no (or fewer) capabilities inside the new namespace, so privileged operations there will fail.

### Q: Why does nsenter fork before exec by default?

Two reasons: the forked child can be reaped and its exit status forwarded cleanly, and forking after the namespace joins but before exec keeps nsenter's own bookkeeping (fd closing, credential changes, chdir) isolated from the final program. `-F` skips the fork for latency and simpler process trees, at the cost of exec semantics being visible directly to nsenter's parent — which is exactly what shell scripting with `$!` and signals wants.

### Q: What do the /proc/<pid>/ns/* files actually contain, and how do tools tell namespaces apart?

They are magic symlinks whose readlink output (`net:[4026532285]`) shows the kernel instance id; the reliable equality test is comparing stat's device+inode on two of them. `lsns` walks /proc doing exactly that to enumerate all namespaces and their users. The files double as handles: opening one pins the namespace against teardown even with zero member processes — the mechanism `ip netns` uses to keep empty named networks addressable.

### Q: Why can't a Go program naively reimplement `nsenter -t PID -p` in a goroutine?

setns(2) into a PID (or user) namespace requires a single-threaded caller; the Go runtime starts multiple OS threads by default, so the call fails with EINVAL. The workarounds are what nsenter itself does — fork a single-threaded helper that performs the joins and then execs — or runtime.LockOSThread gymnastics that still cannot guarantee no other threads exist. Shelling out to nsenter is the robust pattern, which is why container tooling does exactly that.

### Q: How would you prove in CI that a "debug container" genuinely shares the host network namespace?

Compare namespace handles, not behavior: `stat -c '%d:%i' /proc/<hostpid>/ns/net` must equal the same for the container process. Behavior probes (same IP) are weak — they can pass in configurations you did not intend to test. The same technique extends across mnt/pid/user for full "entered-everything" verification, and it is exactly the comparison `lsns` and `nsenter --all` rely on.

### Q: nsenter entered the mount namespace but `ls /` still shows the host root. What did you forget?

Namespace entry changes *view resolution*, not your current working directory or root: your shell's cwd is a host inode, and `/` still resolves through your old root unless the process re-execs from a new root. Fix with `-r` (chroot to the target's `/`) plus `-w /` — or rely on the fact that nsenter's fork+exec starts the child fresh in the entered view, which is why the interactive `nsenter -t PID -m -r -- bash` pattern looks right while `exec nsenter ...` in an existing shell can look half-broken.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/nsenter.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
