# mount — attach filesystems to the directory tree

## Overview

`mount` grafts a filesystem onto a directory of the existing tree: after `mount /dev/sdb1 /data`, the contents of the filesystem on `/dev/sdb1` are reachable at `/data`, and whatever lived there before is hidden until unmount. The same binary performs bind mounts (re-grafting an existing subtree), recursive bind mounts, mount moves, propagation changes, remounts, and mounts from loop devices. It ships in the Debian `mount` package (upstream util-linux) at `/usr/bin/mount`, installed **setuid root** (mode 4755) because mounting requires `CAP_SYS_ADMIN` — the setuid bit is what lets a non-root user mount entries that `/etc/fstab` explicitly delegates to users.

You reach for `mount` when attaching disks and ISO images, mounting over a path to hide it, making a directory visible in two places, flipping a live filesystem read-only, or testing fstab changes. It is often confused with `umount` (its inverse, which only detaches), `losetup` (kernel-side loop device plumbing that `mount -o loop` drives for you), `findmnt` (a *query* tool over the same state), `blkid`/`findfs` (label and UUID lookup used for the source side), and systemd's `.mount`/`.automount` units, which are the declarative way to express fstab entries today.

| Field | Value |
| --- | --- |
| Package | mount (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/mount (setuid root, 4755) |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | Not POSIX; Linux `mount(2)`/`fstab(5)` semantics, LSB historical |

## Synopsis

```
mount [-lhV]
mount -a [-fFnrvw] [-t fstypes] [-O optlist]
mount [-fnrsvw] [-o options] [--source] <source> | [--target] <directory>
mount <operation> <mountpoint> [<target>]
```

Main one-line forms:

```
mount /dev/sdb1 /mnt/data          # device onto directory (fstab consulted for options)
mount -t xfs -o noatime /dev/sdc2 /srv
mount -o loop,ro ubuntu.iso /mnt/iso
mount --bind /var/log /mnt/logs    # same subtree, second location
mount -o remount,rw /              # flip a mounted filesystem read-write
mount /srv/backups                 # by mountpoint: rest of the line comes from fstab
```

## How It Works

### One syscall underneath

Everything the CLI does resolves to the `mount(2)` syscall:

```
mount(source, target, filesystemtype, mountflags, data)
  source          /dev/sdb1, bind source, or NULL
  target          mountpoint directory
  filesystemtype  "ext4", "xfs", "tmpfs", "nfs4", ...
  mountflags      MS_RDONLY, MS_BIND, MS_REMOUNT, MS_NOSUID, MS_MOVE, ...
  data            filesystem-specific options string (fs accepts/rejects it)
```

`libmount` (inside util-linux) parses your command line and fstab, probes the source with libblkid when the type is unknown, filters *known generic* options out of the string, and passes the remaining filesystem-specific ones verbatim in `data`. Kernel-side, a successful mount inserts a new `vfsmount` object into the namespace's mount tree: the kernel then resolves any path that goes through the mountpoint *into* the new filesystem. Files under the mountpoint are not deleted — they are merely shadowed.

```
before:  /data (dir on rootfs)          after mount /dev/sdb1 /data:
         ├── a.txt                       /data  ──> [fs on /dev/sdb1]
         └── b.txt                       (a.txt and b.txt invisible until umount)
```

### Permission model and the setuid mount era

Only processes with `CAP_SYS_ADMIN` may call `mount(2)`. Three eras coexist in any interview answer:

1. **Setuid mount + fstab delegation.** `/usr/bin/mount` is installed setuid root. A non-root user running `mount /srv/backups` gets nowhere *unless* an fstab line for that mountpoint carries `user`, `users`, `owner`, or `group`. libmount enforces this inside the binary — the setuid bit is a gate, not a bypass; any other attempt fails with *only root can do that*.
2. **Desktop/user mounts moved out of band.** FUSE (`fusermount`, setuid) and D-Bus services (udisks2) perform privileged mounting on behalf of users without weakening `mount` itself; this is why USB sticks mount without fstab lines on a desktop.
3. **User namespaces.** Since kernel 3.8, an unprivileged user can create a user+mount namespace with `CLONE_NEWUSER|CLONE_NEWNS` and mount filesystems (tmpfs, bind, overlay) *inside it* — the basis of rootless containers and `unshare -Um`.

For user fstab mounts, remember the implied options: `user` implies `noexec,nosuid,nodev` **unless you list the enabling option after it** (`user,exec`). Option order in fstab is meaningful, which is a favorite interview trap.

### The `-o` option grammar

Options are a comma-separated list with two namespaces merged:

```
generic VFS flags     ro, rw, suid, nosuid, dev, nodev, exec, noexec,
                      sync, async, dirsync, atime, noatime, relatime,
                      strictatime, auto, noauto, defaults
mount-owner flags     user, users, owner, group, nouser
libmount-internal     _netdev, nofail, x-* and comment= (userspace-only,
                      never passed to the kernel), X-mount.mkdir[=mode]
loop handling         loop[=device], offset=N, sizelimit=N, encryption gone
fs-specific           ext4: data=journal, usrquota; nfs4: hard, intr;
                      tmpfs: size=; cifs: vers=; passed verbatim via data
```

Rules that bite:

- A leading `no` negates a boolean flag (`noatime`).
- The same list serves fstab and `-o`; on remount the lists merge, with command-line options winning.
- `x-*`/`comment=` options are for tooling (e.g., `x-systemd.automount`, `x-systemd.device-timeout=5`); libmount stores them in `/run/mount/utab`, never sends them to the kernel, and systemd's fstab generator reads them.
- `loop` is not a kernel option: seeing it, libmount sets up a loop device via `losetup` first, then mounts the device.

### /etc/fstab parsing

fstab lines have six fields; `mount` cares about five of them:

```
# <spec>          <file>        <type>   <opts>            <freq> <passno>
UUID=...          /data         ext4     defaults,noatime  0      2
//nas/share       /mnt/nas      cifs     credentials=...,nofail,_netdev  0 0
```

- `mount -a` mounts everything not marked `noauto` and not already mounted; `-t` filters by type list (`-t nfs4,cifs`, `-t noxfs` = everything except), `-O` filters by option presence (`mount -a -O noatime`).
- `nofail` stops boot from hanging when the device is absent; `_netdev` orders the mount after the network (systemd also infers this for network filesystem types).
- The spec may be `LABEL=`, `UUID=`, `PARTUUID=`/`PARTLABEL=`, resolved via libblkid — that is the same database `blkid` and `findfs` show you.
- `mount --fake -v` prints what would happen without touching the kernel; handy for fstab debugging.
- Frequency/passno are for legacy `dump`/fsck ordering, not consulted by `mount` at runtime.

### Remount semantics

`mount -o remount[,...] <target>` changes flags of an existing mount without detaching. `mount -o remount,rw /` is the classic recovery step. Details worth knowing:

- On remount, unspecified options are filled in from fstab for that mountpoint, so `remount,rw` keeps your `noatime`.
- Flipping to read-only fails with `EBUSY` if any file is open for writing; remounting read-only is therefore not a guaranteed pre-fsck step on busy systems — it is, however, enough on a quiesced database server after checkpoints.
- `ro` + `remount` on the *root* filesystem at boot is special-cased by initramfs before switching root.

### Bind, rbind, move, propagation — and namespaces

```
mount --bind  /var/log /mnt/logs      one subtree visible twice
mount --rbind /data     /mnt/data     bind + subtree's child mounts travel too
mount --move  /mnt/newroot /        reparent a mount (same namespace)
mount --make-private  /                kill shared propagation
mount --make-shared   /                new mounts under / propagate both ways
mount --make-slave    /mnt/chroot      receive, don't send
mount --make-unbindable /secret         forbid future binds of this tree
```

Every process lives in a **mount namespace** (`/proc/PID/ns/mnt`) whose root is a tree of mounts. `clone(CLONE_NEWNS)` copies it; `setns(2)` enters another one (see `nsenter`). Propagation types decide whether mounts made in one tree appear in another: containers start with `make-rprivate` to isolate themselves, while host setups that want per-view mounts (e.g., autofs) use `shared`. Bind mounts of a *single file* are legal and are the standard way to inject one config file into a container. A bind mount keeps the original's read-only state unless you apply a second step — `mount --bind` then `mount -o remount,bind,ro /mnt/logs` — because per-mount flags are set per mount object, and the bind creates a new one.

### Loop devices

`mount -o loop image.iso /mnt` asks libmount to pick a free loop device, associate it with the file (`losetup` semantics, honoring `offset=` and `sizelimit=`), and mount the device. Partitioned images need `-P`-style handling at the losetup layer or an explicit `mount -o loop,offset=...` arithmetic on the inner partition's start sector. The number of loop devices is a kernel parameter (`max_loop`), and on modern kernels loop devices are allocated on demand.

### Where the state lives

`/etc/mtab` is a symlink to `/proc/self/mounts` — the kernel is the source of truth (userspace-only options live in `/run/mount/utab`). Richer per-mount detail (mount IDs, parents, propagation, peer groups, subtype) is in `/proc/self/mountinfo`; `findmnt` and `mountpoint` read these rather than guessing. `mount` with no arguments prints this table.

```
$ mount | head -3
proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)
tmpfs on /dev type tmpfs (rw,nosuid,size=65536k,nr_inodes=517320,mode=755)
```

### Ordering and boot-time behavior

`mount -a` processes fstab entries top to bottom and stops at the first hard failure — fine for a rescue shell, too fragile for boot. Systemd therefore does not run `mount -a` naively: its **fstab generator** converts each entry into `.mount` units with dependency edges. `_netdev` (and the type itself, for nfs/cifs) adds a network dependency; `nofail` downgrades failure from fatal to warning; `x-systemd.automount` turns the mount into an on-demand automount triggered by first access; `x-systemd.device-timeout=10s` bounds how long boot waits for the device. Two consequences worth knowing:

```
# fstab entry                    → systemd unit behavior
/data  ...  defaults             → local-fs.target Requires, boot fails if missing
/nas   ...  _netdev,nofail       → remote-fs.target, network-ordered, warns only
/proj  ...  x-systemd.automount  → /proj auto-mounted on first lookup
```

For hand-written boot scripts the ordering tool is `/etc/fstab` position plus explicit `mount` calls — which is exactly why initramfs and rescue environments still drive `mount` directly.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a`, `--all` | Mount all suitable fstab entries (skips `noauto`, already-mounted) |
| `-t <list>`, `--types` | Type filter; comma list, `no` prefix for exclusion |
| `-O <list>`, `--test-opts` | fstab option filter for `-a` (like `-t`, but for options) |
| `-o <list>`, `--options` | The option grammar above; `remount` merges with fstab |
| `--bind` / `--rbind` | Subtree / recursive-subtree regraft |
| `--move`, `-M` | Move a mount to a new mountpoint (same namespace) |
| `--make-{shared,private,slave,unbindable}` | Set propagation type (`-r` suffixed variants recurse) |
| `-r` / `-w` | Read-only / read-write (short for `ro`/`rw`) |
| `-f`, `--fake` | Dry run — do everything except the syscall |
| `-n`, `--no-mtab` | Skip utab/mtab bookkeeping (now mostly historical) |
| `-l`, `--show-labels` | Show fs labels in listing output |
| `-i`, `--internal-only` | Never exec `/sbin/mount.<type>` helpers (NFS/SMB helpers) |
| `-T <file>`, `--fstab` | Alternative fstab for testing |
| `-N <ns>`, `--namespace` | Perform the mount in another process's mount namespace |
| `-L` / `-U`, `LABEL=` / `UUID=` | Source by filesystem label/UUID |
| `-v` | Verbose: show what is being done |
| `--source` / `--target` | Unambiguous argument passing for scripted use |

## Usage Patterns

```bash
# Mount a data disk with sane generic options
mount -t xfs -o noatime,nodiratime /dev/vdb1 /data
```

```bash
# By UUID — survives device renumbering
mount UUID=2f0b4a2e-... /backup
```

```bash
# Mount everything fstab promises that is not mounted yet (post-reboot repair)
mount -a -v
```

```bash
# Read-only ISO via loop
mount -o loop,ro ubuntu-24.04.iso /mnt/iso
```

```bash
# A filesystem image with a partition table: skip to the inner partition (start sector 2048 * 512)
mount -o loop,offset=1048576 disk.img /mnt/img
```

```bash
# RAM-backed scratch space with a hard cap
mount -t tmpfs -o size=512m,mode=1777 tmpfs /tmp/fast
```

```bash
# Same logs in two places (bind of a directory)
mount --bind /var/log/nginx /mnt/debug
```

```bash
# Inject one file into a chroot/container root (bind of a single file)
mount --bind /etc/resolv.conf /chroot/etc/resolv.conf
```

```bash
# Read-only bind = bind first, then remount the NEW mount read-only
mount --bind /srv /mnt/srv && mount -o remount,bind,ro /mnt/srv
```

```bash
# Recover a read-only root after fs errors
mount -o remount,rw /
```

```bash
# Reparent a prepared root (init-style switch), then clean up the old root
mount --move /mnt/newroot / && umount -l /oldroot
```

```bash
# Container prep: private propagation so container mounts don't leak out
mount --make-rprivate /
```

```bash
# Mount inside a running container's mount namespace (with its PID)
mount -N $(pgrep -f 'nginx: master') -t proc proc /mnt/host-proc
```

```bash
# Only the network filesystems (post-VPN reconnect repair)
mount -a -t nfs4,cifs -v
```

```bash
# Validate fstab before a maintenance reboot
findmnt --verify --verbose
```

fstab delegation for users:

```
# /etc/fstab
/dev/sr0   /media/cdrom  iso9660 ro,user,noauto  0  0
```

```bash
# as a normal user — succeeds only because of the `user` option above
mount /media/cdrom
```

## Nuances and Gotchas

- **`user` implies `noexec,nosuid,nodev`.** Order matters: `user,exec` allows execution; `exec,user` does too (later option wins per pair), but `user` alone silently breaks binaries on the mount. Interviews probe exactly this.
- **Bind mounts need two steps to be read-only.** `mount --bind` copies the tree reference, not the flags; the remount applies to the new mount object. Doing `mount -o remount,ro /srv` instead flips the *original*, affecting everyone.
- **Mounting shadows, never merges.** Everything under the mountpoint becomes invisible (and stat-able only via its former parents' bind mounts). Packages updated under a shadowed `/usr` are a classic broken-upgrade cause.
- **`mount -a` is not idempotent-by-luck.** It skips already-mounted fstab entries by comparing sources/targets, so it is safe to re-run — but entries that fail once keep failing, and with `nofail` absent, boot or `mount -a` aborts early.
- **`/etc/mtab` must stay a symlink.** A real `/etc/mtab` file (pre-2011 style) desynchronizes from kernel state and confuses `findmnt`/`mountpoint`; if you find a regular file there, something is very wrong.
- **Propagate types bite container code.** Under a `shared` parent, a bind you make for a container also appears in the host's tree; systemd makes `/` private at boot for exactly this reason, and container runtimes re-assert `make-rprivate`.
- **`EBUSY` means "in use" on both remount-ro and umount.** Open files, cwd inside the tree, subprocesses, and loop backing files all hold a mount busy; `lsof +f -- /mnt` or `fuser -vm /mnt` finds them.
- **`x-*` options are invisible to the kernel.** Tools that parse `/proc/mounts` will not see `x-systemd.*` options — they live in `/run/mount/utab`; systemd's generator consumes them at boot.
- **Fstab cannot contain raw spaces in the spec or mountpoint.** A space separates fields; encode a literal space as `\040` (`/mnt/my\040dir`). Forgetting this yields two-field lines and confusing "can't find in fstab" errors.
- **exit code 32 vs 64 with `-a`.** When `mount -a` partially succeeds, some mounts may have happened while the command still fails; scripts must not retry blindly (see Exit Status).
- **`--move` requires no busy descendants and the target to be a mountpoint-capable directory in the *same* namespace; cross-namespace moves are impossible — that is what unshare + move combos are for.**
- **setuid is not a hole, but it is a promise.** Anything that mounts on behalf of users (fstab `user`) inherits the implied noexec/nosuid/nodev and per-user unmount rights; do not "fix" a permission problem by adding setuid elsewhere.

## Exit Status

`mount(8)` documents distinct codes:

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Incorrect invocation or insufficient permissions |
| 2 | System error (out of memory, cannot fork, no more loop devices) |
| 4 | Internal mount bug or missing library support (e.g., NFS without helper) |
| 8 | User interrupt |
| 16 | Problems writing or locking `/etc/mtab`/utab |
| 32 | Mount failure (the syscall failed) |
| 64 | Some mounts succeeded, some failed (with `-a`) |

## Related Commands

- [`umount`](./umount.md) — detach mounts; shares the busy/EBUSY semantics and fstab user rules.
- [`findmnt`](./findmnt.md) — query the live mount table in tree, JSON, or filtered form; the read-side of everything here.
- [`losetup`](./losetup.md) — explicit loop-device control for images with partition tables.
- [`pivot_root`](./pivot_root.md) — swap the namespace root entirely (initramfs, containers).
- [`mountpoint`](./mountpoint.md) — test whether a path is a mountpoint.
- [`nsenter`](./nsenter.md) — enter another process's mount namespace before mounting.
- [`blkid`](./blkid.md) — the LABEL/UUID database behind `UUID=` and `LABEL=` sources.
- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`systemd`](../../admin/systemd.md) — `.mount`/`.automount` units and the fstab generator.
- [`internals`](../../internals.md) — VFS, dentries, and how mounting plugs into the kernel.

## Interview Questions

### Q: What is the difference between `mount --bind` and a symlink?

A bind mount is a kernel-level second view of the same subtree: it crosses filesystem boundaries transparently, works for files held by processes that resolve real paths, follows chroots and containers correctly, and survives the target being remounted. A symlink is a directory entry that some syscalls resolve and others don't (e.g., `open` follows it, `lstat` doesn't), breaks when the target moves, and is invisible to namespace operations. Bind mounts also let you apply different mount flags (read-only) to the second view, which symlinks cannot.

### Q: How do you make a bind mount read-only, and why is one step not enough?

You bind first, then remount the *new* mount: `mount --bind /srv /mnt/srv; mount -o remount,bind,ro /mnt/srv`. The first command creates a new mount object; flags like `MS_RDONLY` belong to a mount object, and the bind copies the tree reference with the original's flags. Remounting `/srv` directly would flip the original for all users. (Kernels ≥ 2.27-era can do `mount -o bind,ro` in one go by applying the flag to the new mount; knowing *why* the two-step exists is the point.)

### Q: A non-root user runs `mount /media/usb` and gets "only root can do that". What actually happened, and name two clean ways to allow it.

`mount` is setuid root, so the privilege is available, but libmount refused because no fstab entry grants this user the mountpoint. Clean fixes: add the fstab line with `user` (implying noexec,nosuid,nodev) or `users` (also allows others to unmount); or use udisks2/FUSE tooling that mounts on the user's behalf (`udisksctl mount -b /dev/sdb1`); on modern kernels, a user namespace (`unshare -Um`) gives unprivileged tmpfs/bind mounts inside that namespace only.

### Q: What do the shared/private/slave/unbindable propagation types control, and why do container runtimes care?

They control how mount/unmount events propagate between mounts that were copied by bind or namespace creation: `shared` (peer group) propagates both ways, `slave` receives only, `private` isolates, `unbindable` forbids future binds. Runtimes set `make-rprivate` on the container's root so that mounts the container creates (or an attacker creates) never appear in the host namespace and vice versa. Without this, per-namespace isolation of mounts would silently leak across views.

### Q: `mount -o remount,ro /data` fails with EBUSY on a production server. What is happening and what are your options?

Some process holds the filesystem in a writable state — an open file for writing, a cwd inside the tree, a memory-mapped file, or a loop device backed by it. Options: find and stop the holder (`lsof +f -- /data`, `fuser -vm /data`), quiesce the service (database checkpoint), use `umount -l` (lazy detach: new lookups fail, existing fds keep working — a last resort), or accept that remount-ro is advisory and schedule downtime. The key insight is that read-only transition is transactional: it succeeds only if no writer exists.

### Q: What actually happens when you run `mount /srv/data` with no other arguments?

With a single operand, mount treats it as a mountpoint and looks up the rest — source, type, options — in `/etc/fstab` (or the file from `-T`). It then performs the same privileged mount as a full line would, *provided the caller is root or the entry grants `user`*. If no fstab entry matches, it fails with *can't find in /etc/fstab*. This two-form design (full line vs fstab shorthand) is why `mount /media/cdrom` works for users and why fstab remains the canonical mount configuration even on systemd systems, which merely translate it.

### Q: `mount -a` exits 64 on boot. What does that tell you, and what do you check first?

Exit 64 means *some* mounts succeeded and some failed — partial state, not total failure. First check `findmnt` to see which fstab entries actually mounted, then run `mount -a -v` to watch the failures in order: usually a missing device (no `nofail`), a bad option (kernel rejects a fs-specific option — check the exact type's man page), or an ordering problem (network mounts attempted before the link was up because `_netdev` was forgotten). The exit-code discipline matters because retrying `mount -a` blindly re-attempts the good mounts too — harmless, but the log spam hides the real culprit.

### Q: Why does `mount` sometimes exec helper programs, and when would you prevent that?

For network filesystems and some exotic types, `mount` runs `/sbin/mount.<type>` helpers (e.g., `mount.cifs`, `mount.nfs`) that handle protocol negotiation, credential setup, and daemon interaction before the actual syscall. `-i` (`--internal-only`) forbids helpers so libmount attempts the kernel mount directly — useful in initramfs/rescue contexts where helpers (and their SUID bits and dependencies) may be missing, or when testing whether the kernel itself would accept the mount.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/mount/mount.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
