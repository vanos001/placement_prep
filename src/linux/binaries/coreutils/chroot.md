# chroot — run a command with a different root directory

## Overview

`chroot` runs a command with its filesystem root (`/`) pointed at some other
directory. Everything the command then sees — its config files, its
libraries, its device nodes — comes from that directory tree, not from the
real one. It is the oldest containment primitive in Unix: the `chroot(2)`
system call dates to Version 7 UNIX (1979), and the wrapper command here is
part of Debian's `coreutils` package, installed at `/usr/bin/chroot`
(historically `/usr/sbin/chroot`; on merged-`/usr` systems both paths work).

Setting it up is ordinary file work: a target directory populated with the
binaries, libraries, and data the contained program needs — today usually
produced by `debootstrap`, `pacman -r`, or a rootfs tarball. Running it
requires privilege: `CAP_SYS_CHROOT`, which for interactive use means root.

`chroot` is often over-credited as a security boundary and equally often
dismissed. The precise statement: it confines **filesystem visibility** and
nothing else. Processes inside share the network, the PID table, and all
mounts with the host, and a root-capable process inside can escape with
classic techniques. Modern containers (Docker, LXC, systemd-nspawn) use
namespaces plus `pivot_root(2)`, not `chroot` — but every one of them still
executes the same "relocate the root, then exec" step that this command
embodies.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 8 |
| Path | `/usr/bin/chroot` on modern Debian/Ubuntu (was `/usr/sbin/chroot`) |
| First appeared / lineage | `chroot(2)` in Version 7 UNIX (1979); the standalone command appears in BSD and GNU fileutils, merged into coreutils |
| Standards | Not POSIX-standardized; Linux Standard Base historically required it |

## Synopsis

```
chroot [OPTION]... NEWROOT [COMMAND [ARG]...]
chroot OPTION
```

Main forms:

```bash
chroot /srv/jail                        # interactive shell in the jail
chroot /srv/jail /bin/sh -c 'ls /'      # one command in the jail
chroot --userspec=1000:1000 /srv/jail app   # drop privileges inside the jail
chroot --skip-chdir /srv/jail /usr/bin/pwd  # keep the current working directory
```

With no COMMAND, coreutils chroot runs `"${SHELL}" -i` (falling back to
`/bin/sh -i`) inside NEWROOT.

## How It Works

### The syscall underneath

The `chroot(2)` system call changes the root directory of the **calling
process** and everything it subsequently spawns. After the call:

- Path resolution treats NEWROOT as `/`: a program opening `/etc/passwd`
  gets NEWROOT`/etc/passwd`.
- `..` at the new root stays at the new root **for path lookup**, but the
  kernel still tracks the underlying directory — which is exactly why the
  classic escape works (below).
- The change is inherited by all children and is irreversible for the
  process; there is no "unchroot" call.

The coreutils wrapper does the small amount of glue around this that a bare
syscall cannot: parse `--userspec`/`--groups`, resolve names to IDs
*before* entering the jail (the jail's `/etc/passwd` might not exist), call
`chroot(2)`, `chdir("/")`, set up supplementary groups, set the IDs, and
finally `execvp` the command.

```
                chroot NEWROOT /bin/sh
   ┌────────────────────────────────────────────────────┐
   │  fork/exec chroot(8) as root                       │
   │     1. resolve --userspec / --groups (host DB)     │
   │     2. chroot(2)  → process root = NEWROOT         │
   │     3. chdir("/") → cwd inside jail                │
   │     4. setgroups/setgid/setuid (--userspec)        │
   │     5. execvp(COMMAND)                             │
   └────────────────────────────────────────────────────┘
   What was NOT changed: network stack, PID/mount/IPC/UTS
   namespaces, capabilities (until dropped), open fds,
   cgroup membership, /proc view of the host.
```

### What chroot does NOT isolate

This is the interview-critical list. A `chroot` jail shares everything below
with the host:

- **Network**: same interfaces, same sockets, same listening ports. A jail
  process can connect anywhere the host can.
- **Process table**: it sees host PIDs via `/proc` (if mounted) and can
  signal host processes of the same user. PIDs are not remapped.
- **Mounts**: a chroot does not unmount or hide anything; host bind mounts
  remain visible inside if they intersect the new root's view.
- **Users are numbers**: UIDs/GIDs are not namespaced. UID 0 inside the jail
  *is* root on the host. `--userspec` changes the *credentials*, not the
  ID mapping.
- **Kernel state**: sysctls, module state, cgroups, IPC objects, `dmesg` —
  all shared.
- **Open file descriptors**: any fd held before entering (logs, sockets,
  database files) remains valid and points outside the jail. This is the
  "chroot doesn't close fds" footgun.

### The root escape

Because `chroot(2)` does not move the process to a new mount, a process that
still has `CAP_SYS_CHROOT` (typically: UID 0) can walk back out:

```c
mkdir("hole"); chroot("hole");          /* deepen the root */
for (i = 0; i < 255; i++) chdir("..");  /* climb to the real root */
chroot(".");                            /* re-root at the real / */
```

The `..` climb works because the kernel resolves `..` against the *dentry*
tree, not the logical root. Linux deliberately did not "fix" this: the
defense is to drop the capability — which is precisely what
`--userspec=UID:GID` is for. A non-root process inside the jail cannot call
`chroot(2)` at all, and therefore cannot escape this way. (Modern kernels
have `CAP_SYS_CHROOT` namespaced by user namespaces, which shrinks the blast
radius further.)

### chroot vs pivot_root vs unshare vs mount --bind

| Mechanism | Changes | Old root remains | Needs | Typical user |
| --- | --- | --- | --- | --- |
| `chroot(2)`/`chroot(8)` | process root dir | yes, still mounted | `CAP_SYS_CHROOT` | build chroots, package builders |
| `pivot_root(2)` | whole mount namespace root | unmountable | new mount ns (`CAP_SYS_ADMIN`) | initramfs → real root, container runtimes |
| `unshare -m` + `pivot_root` | private mount ns *and* root | discardable, invisible after | `CAP_SYS_ADMIN` in ns | `unshare --mount --root`, sandboxes |
| `mount --bind` + chroot | grafts host dirs into jail | n/a (adds visibility) | `CAP_SYS_ADMIN` | giving jails /proc, /dev, /sys |

`pivot_root` is the "real" root swap: performed inside a fresh mount
namespace it lets you `umount -l` the old root so it is not merely hidden but
gone — no escape-by-`..`, no leftover host mounts. Container runtimes
(runc, and therefore Docker/Podman) do exactly this after setting up
namespaces; `chroot` survives in their codebase only as a fallback.

`mount --bind` is the complement, not the alternative: it injects host
directories (device nodes, `/proc`) into a jail so the jailed software
works at all:

```bash
mount --bind /proc  /srv/jail/proc     # jailed ps/top need this
mount --bind /dev   /srv/jail/dev      # jailed services need /dev/null etc.
mount --bind /sys   /srv/jail/sys      # many modern tools require it
```

### Container lineage

Version 7 UNIX (1979) gained `chroot(2)` during development of the FTP
daemon; FreeBSD 4.0 (2000) added `jail()` (chroot + per-jail IPs + process
visibility); Linux gained namespaces (2002+) and `pivot_root` (2000s) which
together with cgroups (2007) produced LXC (2008) and Docker (2013). Each
generation kept the core gesture — relocate the root, then exec — while
adding isolation for the things chroot never covered.

## Options That Matter

| Option | Effect |
| --- | --- |
| `--userspec=USER:GROUP` | Run COMMAND as this user/group (names or numeric IDs), resolved against the **host** database before entering |
| `--groups=G1,G2,...` | Set supplementary groups inside the jail |
| `--skip-chdir` | Do not `chdir("/")` after chrooting; keep the current working directory (host path, now interpreted inside the jail). Only accepted when NEWROOT is a different root than `/` |
| `--help`, `--version` | As usual |

`--userspec` is the security-relevant one: with it, the jailed process runs
as an unprivileged user, which closes the `..` escape and prevents tampering
with the jail's own files.

## Usage Patterns

```bash
# Enter a debootstrap'ed Debian root interactively
sudo debootstrap bookworm /srv/jail http://deb.debian.org/debian
sudo chroot /srv/jail
```

```bash
# Give the jail the minimum virtual filesystems it needs
for fs in proc sys dev; do sudo mount --bind /$fs /srv/jail/$fs; done
```

```bash
# Run one command non-interactively inside the jail
sudo chroot /srv/jail /usr/bin/apt-get -y update
```

```bash
# Build a package with a jailed, dependency-pinned environment
sudo chroot /srv/build-root make -C /src all test
```

```bash
# Drop privileges inside the jail: the service runs as nobody
sudo chroot --userspec=65534:65534 /srv/jail /usr/local/bin/worker
```

```bash
# Keep the host cwd across chroot (top of a build tree inside the jail)
sudo chroot --skip-chdir /srv/jail make
```

```bash
# Verify what the jailed environment actually sees
sudo chroot /srv/jail /bin/sh -c 'cat /etc/os-release; ls /proc | head -3'
```

```bash
# Repair a broken bootloader from live media: classic rescue use
sudo mount /dev/nvme0n1p2 /mnt && sudo chroot /mnt update-grub
```

```bash
# Test that a program runs with ONLY its declared dependencies
sudo chroot /srv/minimal-jail /usr/bin/myapp --version || echo "missing dep"
```

## Nuances and Gotchas

- **Binaries inside must match.** A chroot of a different architecture (or
  a dynamically linked binary with libraries missing from the jail) fails
  with "No such file or directory" even though the file exists — the
  *dynamic loader* `/lib64/ld-linux-x86-64.so.2` is what is missing.
- **Name resolution happens outside.** `--userspec=www-data` is resolved
  against the host's `/etc/passwd`; inside the jail the numeric UID is what
  matters. Jails with divergent passwd files produce confusing ownership.
- **No fd hygiene.** Anything the jail-entrant keeps open (listening
  sockets, log files) points outside the jail. Privilege-dropping daemons
  must close or sanitize fds before dropping root.
- **`--skip-chdir` is niche.** Its legitimate use is build systems that want
  the jailed make to operate on the current tree; misused, it leaves the
  cwd on a host path that may not exist inside the jail, and subsequent
  relative-path resolution fails.
- **Mount points inside the jail leak host state.** A bind-mounted `/proc`
  is a full view of the *host* process table; combined with root in the
  jail, it is a lateral-movement channel. This is why runtimes mount a
  *fresh* procfs in a new PID namespace instead.
- **chroot is not a sandbox.** Shared network, shared PIDs, shared mounts,
  shared kernel, escape-as-root. If the threat model includes untrusted
  code, you need namespaces/seccomp at minimum.
- **Historical footgun:** the standalone `chroot` used to live in `/usr/sbin`
  and scripts hardcoding that path broke on merged-`/usr` systems; PATH
  lookup (or `/usr/bin/chroot`) is the portable spelling now.
- **Exit status convention (125/126/127)** is the wrapper's, not the
  jailed program's — parse with care in automation.

## Exit Status

| Status | Meaning |
| --- | --- |
| 125 | `chroot` itself failed (bad option, chroot(2) rejected, cannot drop privileges) |
| 126 | COMMAND found but not executable |
| 127 | COMMAND not found |
| other | The exit status of COMMAND |

Without `--userspec` the whole chain runs as root, so COMMAND's own exit
code is all a script normally observes.

## Related Commands

- [`env`](./env.md) — the other "modified-context launcher" in coreutils: changes the environment block instead of the filesystem root
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- `unshare(1)`, `pivot_root(2)`, `mount(8)` — the modern containment stack that supersedes bare chroot (util-linux / kernel; outside this collection)

## Interview Questions

### Q: chroot is often called "the first container". What did Version 7 UNIX actually add, and what do today's containers add on top?

Version 7 (1979) added the `chroot(2)` syscall: per-process filesystem-root
relocation, used to quarantine the FTP daemon. Modern containers keep that
final "exec in the new root" step but add namespaces (pid, net, mnt, uts,
ipc, user) so processes, networks, and mounts are no longer shared; cgroups
for resource limits; and `pivot_root` inside a private mount namespace so
the old root can be unmounted rather than merely hidden. `chroot` alone
provides only the filesystem-visibility slice.

### Q: A process running as root inside a chroot can escape it. Explain the mechanism and the two standard mitigations.

The escape exploits that `chroot(2)` changes logical path resolution but not
the kernel's dentry ancestry: the process makes a deeper chroot
(`mkdir x; chroot x`), then executes `chdir("..")` repeatedly — each `..`
climbs the real dentry tree even though logically it should stay at the new
root — and finally `chroot(".")` from the real root. Mitigations: (1) drop
privileges after entering (`chroot --userspec=...`), since `chroot(2)`
requires `CAP_SYS_CHROOT`; (2) use `pivot_root` in a new mount namespace so
the old root is actually unmounted and has no dentry to climb back into.

### Q: You chroot into a prepared rootfs and get `/bin/sh: No such file or directory` even though `/bin/sh` exists there. What is the likely cause?

The error is about the ELF interpreter, not the shell: dynamically linked
binaries need `/lib64/ld-linux-x86-64.so.2` (and then libc) inside the jail,
and the loader path is resolved relative to the new root. Either the
libraries were not copied, or the rootfs is for a different architecture
than the host kernel. Running `file` on the binary from outside, and
inspecting its `INTERP` section, confirms which.

### Q: Why does `chroot --userspec=1000:1000` resolve the names before entering the jail?

Because after `chroot(2)` the process can only see the jail's copy of
`/etc/passwd` and `/etc/group`, which may be missing, stale, or absent
entirely — the jail was prepared for the application, not for identity
lookups. The wrapper reads the host NSS database while it still can,
converts names to numeric IDs, and applies them with `setgroups`/`setgid`/
`setuid` from inside. Numeric IDs keep working because UIDs are not
namespaced.

### Q: Given the table chroot vs pivot_root, why did container runtimes settle on pivot_root?

Because `pivot_root` operates on the mount namespace: the old root can be
unmounted (and its submounts moved aside first), so host paths are not just
hidden from path resolution but genuinely absent — no `..` escape, no leaked
host mounts, and the runtime can lay out the container's own /proc, /dev and
tmpfs mounts cleanly. chroot leaves every host mount reachable through the
still-mounted old root, which is unacceptable for an isolation boundary.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/chroot.8.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
