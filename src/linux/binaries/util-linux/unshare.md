# unshare — run a program with new Linux namespaces

## Overview

`unshare` launches a program after detaching parts of its **kernel execution context** from the parent — the Linux namespaces for mounts, UTS (hostname), IPC, network, PIDs, users, cgroups, and time. It is the CLI over the `unshare(2)` syscall and the smallest possible container: `unshare -Urpf --mount-proc bash` gives you a fresh, root-mapped world where mounts, PIDs and networking are your own. It ships in the Debian `util-linux` package at `/usr/bin/unshare` (not setuid; user namespaces make it work unprivileged).

You reach for `unshare` when testing chroot/OCI images without a container runtime, isolating builds (private mount table, no network), demonstrating namespace behavior, or building the underlying machinery that Docker/Podman/LXC compose. It is often confused with `chroot` (only swaps the filesystem root, no isolation of mounts/PID/net), [`nsenter`](./nsenter.md) (the inverse — joins *existing* namespaces of another process), and `setpriv` (credential/capability manipulation, no namespace creation). [`lsns`](./lsns.md) lists the namespaces on the system, including ones `unshare` created.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/unshare |
| First appeared | util-linux 2.14 era (2008); matured with user namespaces (kernel 3.8, 2013) |
| Standards | none; Linux `namespaces(7)` / `unshare(2)` |

## Synopsis

```
unshare [options] [program [argument...]]
```

Main one-line forms:

```
unshare -m bash                       # private mount table
unshare -Urpf --mount-proc bash       # the "mini container": user+pid+mount
unshare -n sh -c 'ip link'            # network namespace with only a loopback
unshare -u hostname newname           # private UTS (hostname) namespace
unshare -T --boottime 1000000 date    # time namespace, shifted boot clock
```

## How It Works

### One syscall, seven flags

Each `-m/-u/-i/-n/-p/-U/-C/-T` flag maps to one bit of the `CLONE_NEW*` flag word handed to `unshare(2)`. The kernel then creates fresh copies of the requested namespace structures for the calling process; children inherit them.

```
flag     namespace   isolates
-U       user        uid/gid mappings, capability scope
-m       mount       mount table, propagation
-p       pid         process-ID numbering (no view of host PIDs)
-n       network     interfaces, routes, sockets, iptables
-i       ipc         SysV IPC, POSIX message queues
-u       uts         hostname, domainname
-C       cgroup      cgroup root view
-T       time        monotonic/boottime clock offsets
```

Two ordering rules the tool enforces for you: a **user namespace must come first** (you create it to gain `CAP_SYS_ADMIN` in the *new* user namespace, which then authorizes creating the others), and a **PID namespace requires `-f/--fork`** if you want to run a program — you cannot `unshare` a PID namespace for the *current* process, so unshare forks and the parent waits.

### Namespaces vs chroot vs containers

A common interview framing — put each tool on the isolation ladder:

```
chroot(2)      filesystem root only; no isolation of mounts/PIDs/net/users
unshare -m     + private mount table (chroot becomes reversible and layered)
unshare -Urmpf # + uid mapping, own PID space, own /proc  → mini container
runc/docker    the above + cgroups (resources), seccomp (syscalls),
               LSM labels, rootfs staging, network plumbing (veth, bridges)
```

`unshare` composes the *namespace* half of a container; it deliberately does not do resource limits or syscall filtering. Being able to say precisely which piece is missing (cgroups? seccomp? rootfs?) distinguishes candidates who understand containers from candidates who use them.

### Debugging a failed unshare

```bash
$ unshare -Ur true
unshare: unshare failed: Operation not permitted
$ sysctl kernel.unprivileged_userns_clone user.max_user_namespaces
kernel.unprivileged_userns_clone = 1
user.max_user_namespaces = 61942
```

The three usual culprits, in check order: the distro sysctl (`kernel.unprivileged_userns_clone = 0` on Debian-family hardening profiles), the namespace quota (`user.max_user_namespaces = 0` — set to 0 by default for unprivileged users on RHEL, and commonly zeroed inside containers), and seccomp filters (default Docker blocks `unshare(2)`/`setns(2)`). Root inside an unprivileged container still inherits the restriction — the check is against the *user namespace owner*, not uid 0.

### The user-namespace trick (`-r`)

Unprivileged namespace creation is the foundation of rootless containers. `unshare -r` (`--map-root-user`) maps *your* UID inside the new user namespace to root:

```
host view:   uid=1000(z)          ns view:   uid=0(root)
```

Root-in-ns holds full capabilities — but only against resources in that namespace (own mounts, own netns, own PID space). Files you touch on shared mounts still check the *host* UID, which is exactly why `unshare -Ur` + mounts work for tmpfs/bind but not for reading root-owned host files.

Grounded in this environment:

```bash
$ unshare -Ur id
uid=0(root) gid=0(root) groups=0(root)     # mapped root inside the ns
```

### Mount namespaces and propagation

When you `-m`, unshare (since util-linux 2.27) automatically sets the new namespace's propagation to **private**, so mounts you make inside do not leak to the host (and vice versa) — the kernel default would otherwise inherit `shared`. `--propagation shared|slave|private|unchanged` overrides this; `unchanged` keeps exactly what the parent had. `--mount-proc` (implies `-m`) mounts a fresh `/proc` so PID-namespace tools see only the ns's processes — without it, `ps` in a new PID ns shows garbage because `/proc` still reflects the host PID space.

### Persistence and lifecycle helpers

Namespaces normally die with the last process. unshare offers knobs around that:

```
-m=<file>            bind-mount the new namespace at <file>  (persistent ns)
-f, --fork           fork first (required-ish for -p; isolates lifetime)
--kill-child[=SIG]   when unshare dies, kill the child (no orphans)
-R, --root <dir>     chroot into <dir> inside the new ns (pivot_root semantics)
-w, --wd <dir>       set working directory after setup
-S/-G, --setuid/--setgid   drop to a uid/gid after entering
--map-user/--map-group/--map-users auto   fine-grained uid_map control
--monotonic/--boottime <s>  offset the clocks in a time namespace
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m`, `-u`, `-i`, `-n`, `-p`, `-U`, `-C`, `-T` | Create the respective namespace (mount/uts/ipc/net/pid/user/cgroup/time). |
| `-r, --map-root-user` | Map current user to root inside a new user namespace. |
| `--map-user/--map-group <id\|name>` | Explicit id mapping (implies `-U`). |
| `-f, --fork` | Fork before exec (needed to actually run a program in a new PID ns). |
| `--kill-child[=<sig>]` | Ensure the child dies with unshare (default SIGKILL). |
| `--mount-proc[=<dir>]` | Mount fresh procfs in the new ns (implies `-m`). |
| `--propagation <p>` | Set mount propagation: shared/slave/private/unchanged (default private). |
| `-R, --root <dir>` | Run with `<dir>` as the new root directory. |
| `-S, --setuid` / `-G, --setgid` | Drop privileges inside the namespace after setup. |
| `--setgroups allow\|deny` | Control `setgroups(2)` in the user ns (deny is required for unprivileged mapping). |
| `--keep-caps` | Retain capabilities across the setuid step in the ns. |
| `--monotonic/--boottime <s>` | Set time-namespace clock offsets. |

## Usage Patterns

```bash
# Scratch mount table: mount/umount freely, host unaffected
unshare -m bash -c 'mount -t tmpfs none /mnt && touch /mnt/x'
```

```bash
# Rootless mini-container: mapped root, own PIDs, own /proc
unshare -Urpf --mount-proc bash
```

```bash
# Network isolation test: only loopback inside
unshare -n sh -c 'ip link set lo up && ping -c1 127.0.0.1'
```

```bash
# Rename "the machine" without touching the host hostname
unshare -u hostname container-a && unshare -u hostname
```

```bash
# Hide SysV/POSIX IPC from a test suite (fresh empty IPC set)
unshare -i ipcs
```

```bash
# Persistent mount namespace another shell can enter later
unshare --mount=/root/ns-mnt sleep infinity   # then: nsenter --mount=/root/ns-mnt
```

```bash
# Clean-room chroot with its own mount and PID space
unshare -mpf --mount-proc -R /srv/rootfs /bin/sh
```

```bash
# Sandbox a build with no network and capped clock skew
unshare -nT --boottime 31536000 bash -c 'uptime; make'
```

```bash
# Drop to a uid inside the namespace after preparing it
unshare -Ur --setuid 1000 --setgid 1000 id
```

```bash
# Time-namespace demo: shift the boot clock forward a year
unshare -T --boottime 31556952 uptime
```

```bash
# Guard against orphaned namespaces in scripts
unshare -pf --kill-child --mount-proc bash -c 'ps -p 1 -o comm,pid'
```

```bash
# IPC namespace for a shmem test: fresh, empty IPC objects
unshare -i sh -c 'ipcmk -S 1048576 && ipcs'
```

```bash
# Reproduce a hostname-dependent bug without touching the host
unshare -u hostname ci-node-7
```

```bash
# Verify a binary's network reachability assumptions with zero interfaces
unshare -n curl --max-time 3 http://example.test || echo isolated
```

```bash
# Combine cgroup ns (fresh root view of controllers) with pid ns
unshare -Cpf --mount-proc bash -c 'cat /proc/self/cgroup'
```

## Nuances and Gotchas

- **`Operation not permitted` is usually not unshare's fault.** Unprivileged user namespaces may be disabled: `sysctl kernel.unprivileged_userns_clone` (Debian) or `user.max_user_namespaces=0` (containers often set this), and seccomp profiles (default Docker) block `unshare(2)`. Inside an unprivileged container, even root cannot create user namespaces — this exact environment is a common demo failure.
- **PID ns without `--mount-proc` lies to you.** `ps` reads `/proc`, which still shows the host's process table; only a fresh procfs mount (`--mount-proc`, implies `-m`) makes the PID ns visible. Conversely PID 1 exiting kills everything in the ns.
- **Order of flags is semantics.** `unshare -Ur` and `unshare -rU` are equivalent because the tool orders user-ns creation first, but hand-written code that calls `unshare(CLONE_NEWNET)` without `CLONE_NEWUSER` as non-root simply fails with EPERM.
- **Propagation default is private since 2.27.** Mounts made in the new ns do not propagate back — a security fix, but it surprises people who *want* shared semantics; use `--propagation shared` deliberately (and mind that shared + untrusted = mounts leaking out).
- **`-f` and PID ns lifetime.** The first process in a PID namespace becomes its PID 1; if it dies, the kernel kills the namespace. `--kill-child` exists for the reverse direction: parent gone ⇒ child gone, avoiding immortal sleeps holding namespaces open.
- **`setgroups` must be denied** before writing an unprivileged `gid_map`; unshare handles it, but hand-rolled mapping in C/Go must do `setgroups` deny first or the write fails.
- **Time ns is one-way.** Once in a time namespace you cannot see or change the host clocks; offsets (`--monotonic`, `--boottime`) apply to *new* namespaces only.
- **Not a security boundary by itself.** A user namespace gives capabilities *in that namespace*; combined with file access on shared mounts the host uid still applies. Container-grade isolation adds seccomp, cgroups, and rootfs staging — unshare is the primitive, not the fortress.
- **Nested user namespaces have limits.** Each nesting level consumes namespace quota and uid_map entries; deeply nested sandboxing tools can hit `user.max_user_namespaces` or an empty mapping range, producing EPERM far from the real cause.
- **`-R` is pivot-root-flavored, not plain chroot.** The `--root` switch sets up the new root within the (fresh) mount namespace, so the old root is not left dangling the way raw `chroot(2)` does — but it still requires the directory to be populated. Container images minus the runtime plumbing is exactly what `-R` gives you.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Namespace(s) created and (if requested) program ran and exited 0. |
| 1 | `unshare(2)`/`setns`-style failure: EPERM (no privilege / blocked), EINVAL (bad flag combination), ENOSPC (namespace limit), or usage error. |
| child status | When a program is executed, unshare propagates the program's exit status. |

## Related Commands

- [`nsenter`](./nsenter.md) — the inverse operation: enter the existing namespaces of a running process.
- [`lsns`](./lsns.md) — enumerate all namespaces on the system and who holds them.
- [`mount`](./mount.md) — mount-namespace content: what `-m` isolates and how propagation works.
- [`chrt`](./chrt.md) — sibling "modify child's kernel context then exec" tool for scheduling attributes.
- [`../../internals.md`](../../internals.md) — kernel-side context for processes and isolation.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: Why does creating a user namespace first (`-U`) unlock all other namespaces for an unprivileged user?

Namespaces other than `user` require `CAP_SYS_ADMIN`, but capabilities are namespaced. Inside a *new user namespace* the mapping owner gets full capabilities scoped to that namespace, and the kernel accepts namespace-creation syscalls from someone holding `CAP_SYS_ADMIN` in the user namespace that owns the target scope. That is why `unshare -Ur -n ...` works as uid 1000 while `unshare -n` alone fails with EPERM.

### Q: `unshare -p bash` fails, and `unshare -pf bash` shows host processes in `ps`. Explain both.

`unshare(2)` cannot new-ify the PID namespace of the calling process — PID numbering is bound to existing threads, so you must fork (`-f`); the child lands in the ns and the parent waits. The `ps` lie is a different layer: `ps` reads `/proc`, which without `--mount-proc` is still the host's procfs showing host PIDs; a fresh procfs mount inside the ns (implied by `--mount-proc`, which also implies `-m`) fixes the view.

### Q: What does unshare's automatic propagation switch to private protect against?

Before util-linux 2.27, a new mount namespace inherited `shared` propagation, meaning mounts created inside it propagated back to the parent — a real escape vector (e.g. a container escape or prank bind-mount onto `/etc/shadow` targets). Setting the new ns to private keeps mount events local; `--propagation unchanged` restores the old behavior when you actually want the sharing.

### Q: How would you use `unshare` + a bind mount to give another shell a persistent private /tmp?

`unshare --mount=/run/ns-tmp sleep infinity` creates the namespace and pins it to a bind-mount file so it survives the creating process; inside, `mount -t tmpfs tmpfs /tmp` stays private. Any process joins later with `nsenter --mount=/run/ns-tmp`. This is the manual version of what container runtimes and systemd's `PrivateTmp=` automate.

### Q: A build script must not see the network but needs to run as root for chroot. Sketch the unshare line and justify each flag.

`unshare -Urnmf --mount-proc --kill-child bash`. `-U -r` creates a user ns with mapped root (unprivileged chroot/mount rights inside), `-n` removes all interfaces (no network), `-m` allows the chroot's mounts without touching the host, `-f` forks because a program must run to do the chroot, `--mount-proc` gives a sane `/proc`, and `--kill-child` prevents the build's children from outliving the driver script.

### Q: What does `--kill-child` solve that `--fork` alone does not?

`--fork` only creates the child in the new namespaces. If the `unshare` supervisor (or its script) is killed, the child would keep the namespaces alive indefinitely — daemon-like leftovers. `--kill-child[=SIG]` makes the parent send the signal when it dies (default SIGKILL), tying child lifetime to supervisor lifetime; it's the CLI equivalent of `PR_SET_PDEATHSIG`.

### Q: A colleague says "unshare is insecure because you become root in it". Refute precisely.

Mapping to root inside a *user namespace* grants capabilities that the kernel applies only against resources owned by that user namespace — other namespaces (mount, net, pid) created within it, not the host. Files on shared mounts still enforce the real uid; host devices, other users' processes, and system mounts remain out of reach. That said, user namespaces enlarge the kernel attack surface exposed to unprivileged users (kernel bugs reachable via namespace syscalls), which is why some distributions ship them disabled — a nuance about *risk*, not a correctness flaw in the mapping model.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/unshare.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
