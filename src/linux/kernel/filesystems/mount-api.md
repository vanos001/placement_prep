# The New Mount API: fsopen, fsmount, move_mount and the fs_context Lifecycle

The companion page [Mounting](mounting.md) covers the operator's view — `mount(8)`, bind mounts, propagation, `/proc/self/mountinfo`, fstab. This page goes one level down into the *syscall* layer: Linux 5.2 added a family of syscalls (`fsopen`, `fsconfig`, `fsmount`, `move_mount`, `open_tree`) and Linux 5.12 added `mount_setattr`, together called the new mount API. They exist because `mount(2)` — one monolithic call with a string blob for options — had been stretched far past its design point by containers, per-service namespaces, and idmapped mounts. The kernel documents the internal object behind them, the `fs_context`, in [the mount_api design document](https://docs.kernel.org/filesystems/mount_api.html), which this page follows.

## Why mount(2) ran out of road

Four structural problems with the old interface kept generating kernel patches for two decades:

1. **One syscall, one shot.** Source, target, type, flags, and options arrive together; a bad option string fails the whole mount with a bare `EINVAL`, and the kernel's parsing diagnostics go nowhere userspace can read. There is no channel that says *which* option was rejected or why.
2. **String-only configuration.** `data` is a NUL-terminated blob the filesystem parses itself. Options that are naturally structured — an fd, a path, binary data, a "flag with no value" — all get flattened into text and re-parsed.
3. **Attach is mandatory.** `mount(2)` cannot create a superblock *without* simultaneously attaching it somewhere. Everything that wants a prepared filesystem as a first-class object — a runtime setting up a container root, a supervisor pre-mounting before pivot_root, a user namespace creating its own view — had to fork a helper, call `mount()` inside the child, and parse stderr for errors.
4. **Flag soup on remount.** `MS_REMOUNT | MS_BIND` changes mount flags, plain `MS_REMOUNT` changes superblock flags, propagation changes need `MS_SHARED`/`MS_SLAVE`/`MS_PRIVATE`/`MS_UNBINDABLE` as separate flag bits, and applying any of it recursively (`MS_REC`) has subtly different semantics per combination. `mount(2)`'s flags column became a mini-language with dialects.

The new API answers each point: discrete steps with typed commands, a per-context **log ring** for diagnostics, filesystem objects held as **file descriptors** that can live detached and be passed across processes, and `mount_setattr()` with explicit recursive semantics.

## Six syscalls, one object

| Syscall | Since | Role |
|---|---|---|
| `fsopen(fs_type, flags)` | 5.2 | Create an fs_context for a filesystem type; returns a managed fd |
| `fsconfig(fd, cmd, key, val, aux)` | 5.2 | Set parameters / issue commands on that context |
| `fsmount(fd, flags, attr_flags)` | 5.2 | Turn a context with a tree attached into a **detached mount fd** |
| `move_mount(fd, from_path, to_fd, to_path, flags)` | 5.2 | Attach (or re-attach) a mount into the namespace tree |
| `open_tree(dfd, path, flags)` | 5.2 | Grab an existing mount as an fd; `OPEN_TREE_CLONE` clones it |
| `mount_setattr(dfds, path, flags, attr, size)` | 5.12 | Change mount attributes (read-only, nosuid, idmapping) atomically |

`fsopen()` requires `CAP_SYS_ADMIN` in the relevant user namespace ([fsopen(2)](https://man7.org/linux/man-pages/man2/fsopen.2.html)); these are privileged calls by design. glibc gained wrappers in 2.36 — before that, userland called them through `syscall(2)` with the `__NR_*` numbers, which is what [Mounting](mounting.md)'s example does.

## The fs_context state machine

Internally every mount begins as an `fs_context` with a `purpose` and a set of operations (`parse_param`, `validate`, `get_tree`, `reconfigure` — the filesystem's implementation of each). The kernel document enumerates the purposes; the observable lifecycle from userspace is:

```text
   fsopen("ext4")
       |  creates context, purpose = FS_CONTEXT_FOR_MOUNT
       v
   fsconfig(FSCONFIG_SET_STRING/SET_FLAG/SET_PATH/SET_FD, ...)
       |  parameters accumulate; parse errors are LOGGED, not fatal
       v
   fsconfig(FSCONFIG_CMD_CREATE)  ---- failed parse/validate ----> FAILED
       |  ->get_tree(): find existing superblock matching the       (context fd
       |     key, or build a new one; sb now referenced             stays alive)
       v
   fsmount(fd, MOUNT_ATTR_*)  ==> detached mount fd
       |
       v
   move_mount(mnt_fd, "", dir_fd, "/mnt/data", MOVE_MOUNT_F_EMPTY_PATH)
       |
       v
   mount is live in the target namespace; close(mnt_fd) keeps it mounted
```

Two properties of this machine are the point of the whole design. **Detachment**: between `fsmount()` and `move_mount()` the mount exists but is in no namespace — you can inspect it, pass it over a unix socket, and attach it inside a *different* mount namespace than the one you created it in (with credentials checked there). **Reconfiguration as a purpose**: a context created for an existing superblock (`FS_CONTEXT_FOR_RECONFIGURE`) runs `fsconfig(FSCONFIG_CMD_RECONFIGURE)` against that superblock's `->reconfigure()` op instead of `->get_tree()`.

## FSCONFIG_*: the configuration grammar

[fsconfig(2)](https://man7.org/linux/man-pages/man2/fsconfig.2.html) defines eight commands; typed payloads replace the old string blob:

| Command | Payload | Maps to |
|---|---|---|
| `FSCONFIG_SET_FLAG` | key only | flag-style option (`noatime`) |
| `FSCONFIG_SET_STRING` | key + string | `source=...`, `errors=remount-ro` |
| `FSCONFIG_SET_BINARY` | key + blob + size | binary parameter |
| `FSCONFIG_SET_PATH` | key + dirfd + path | path-valued option, resolved with dirfd |
| `FSCONFIG_SET_PATH_EMPTY` | key + dirfd + path | same, but empty path = dirfd itself |
| `FSCONFIG_SET_FD` | key + fd | fd-valued option |
| `FSCONFIG_CMD_CREATE` | none | run `->get_tree()`, materialize the superblock |
| `FSCONFIG_CMD_RECONFIGURE` | none | apply accumulated params to an existing sb |

`FSCONFIG_SET_PATH` with a dirfd is worth noticing: source devices are resolved *at configuration time* under the caller's control, not re-resolved inside a kernel string parser at attach time.

## The log ring: error messages with a delivery address

The fs_context fd doubles as a **log device**: while the kernel parses parameters and builds the tree, it appends timestamped diagnostic messages — usually prefixed with the filesystem name — which `read()` on the fsopen fd drains, oldest first. The buffer is a fixed-size ring: if the filesystem logs faster than you read, the oldest messages are overwritten. This is the feature the old API could never retrofit: a failed mount is no longer "errno 22, good luck," it is a transcript — try `read()`ing the context fd after any failing `fsconfig` sequence (the demo below shows the shape of it).

## Superblock re-use and reconfiguration

`->get_tree()` is where the old and new worlds meet. Given the accumulated parameters, the filesystem locates an existing superblock with the same key (device + identity options) — the classic re-use semantics `mount(2)` relied on implicitly — or allocates a new one, via the `sget_fc()` machinery described in [the kernel mount_api document](https://docs.kernel.org/filesystems/mount_api.html) and, from the superblock side, in [superblock internals](superblock.md). Consequences worth stating precisely:

- Multiple contexts configured identically conclude with *one* superblock and *several* mount objects. The mounts are independent (separate flags, separate namespaces) while the filesystem state is shared.
- A context whose `CMD_CREATE` fails leaves nothing attached anywhere; failures die inside the context, with the log ring recording why.
- Reconfiguration of a *live* superblock goes through `FSCONFIG_CMD_RECONFIGURE` and the `->reconfigure()` op, which receives the already-parsed parameters — a far stricter path than `MS_REMOUNT`'s flag arithmetic. For mount-level flags only (read-only, nosuid, atime policy), `mount_setattr()` is the lighter tool and does not touch the superblock at all.

## open_tree and move_mount: detached mounts and namespace crossing

`open_tree(path, OPEN_TREE_CLONE)` produces an fd for an existing mount (optionally a recursive clone with `AT_RECURSIVE`), and `move_mount()` attaches any mount fd anywhere — including across mount namespaces, because the fd *is* the mount. This decomposes operations that used to need contortions:

- **bind mount** = `open_tree(AT_FDCWD, "/src", OPEN_TREE_CLONE)` + `move_mount(fd, "", dirfd, "/dst", MOVE_MOUNT_F_EMPTY_PATH)`;
- **cross-namespace attach** = create the mount in a supervisor namespace, `fsmount()`, pass the fd to a container process (SCM_RIGHTS), let it `move_mount()` into its own tree;
- **re-parenting an existing mount** = `open_tree()` (no clone) + `move_mount()`, which is `MS_MOVE` without the flags ambiguity.

## mount_setattr and idmapped mounts (brief)

[mount_setattr(2)](https://man7.org/linux/man-pages/man2/mount_setattr.2.html) (Linux 5.12) applies a `mount_attr` structure — `attr_set`/`attr_clr` masks over `MOUNT_ATTR_RDONLY`, `MOUNT_ATTR_NOSUID`, `MOUNT_ATTR_NODEV`, `MOUNT_ATTR_NOEXEC`, the atime family, and `MOUNT_ATTR_IDMAP` — with `AT_RECURSIVE` as the explicit "whole tree" switch. It replaces the remount dialect: one call, one semantic, no `MS_BIND|MS_REMOUNT` folklore.

`MOUNT_ATTR_IDMAP` is the hook for **idmapped mounts**: pass a `userns_fd`, and the kernel records a translation so a mount owned by root on the host presents uids/gids as a container user — without chown-ing anything and without touching the superblock; the mapping lives on the mount. The mapping algebra is specified in [the kernel idmappings document](https://www.kernel.org/doc/html/latest/filesystems/idmappings.html); the privilege model interacts with [capabilities](../../security/capabilities.md) (the caller needs `CAP_SYS_ADMIN` in the owning user namespace) and [user namespace](../processes/namespaces.md) setup.

## systemd as the production consumer

The biggest user of mount machinery on a modern machine is the init system: every `.mount`/`.automount` unit, every `PrivateTmp=`, `ReadOnlyPaths=`, or `ProtectHome=` directive materializes as mount-namespace work done by [systemd internals](../../admin/systemd-internals.md) — namespace clones, bind mounts, propagation changes, remounts — at service start. Each of those operations is exactly the sequence the new API decomposes (configure, create, attach), which is why the API's error logging and fd-based mounts matter in practice: a unit that fails to mount can be debugged from an error transcript instead of from journal guesswork, and runtime tooling can pass prepared mount fds instead of shelling out to `mount(8)`. Watch it happen on any current distribution with `strace -f -e trace=fsopen,fsconfig,fsmount,move_mount,open_tree,mount_setattr,mount systemctl start tmp.mount`.

## Old API vs new API

| Dimension | mount(2) / umount(2) | fsopen/fsconfig/fsmount/move_mount |
|---|---|---|
| Call shape | one monolithic call | five small steps on an fd |
| Options | string blob parsed by the fs | typed FSCONFIG_* commands |
| Error detail | errno only | per-step errno + readable log ring |
| Superblock without attach | impossible | fsmount() → detached mount fd |
| Mount as a handle | none (path-based) | fd: passable, clonable, re-attachable |
| Recursive flag changes | MS_REC with per-case semantics | explicit AT_RECURSIVE in mount_setattr/open_tree |
| Namespace crossing | flags + helper processes | move_mount() across namespaces directly |
| Privilege | CAP_SYS_ADMIN | CAP_SYS_ADMIN (fsopen) |
| Introduced | 1990s | 5.2 (2019); mount_setattr 5.12 |

The two APIs coexist: `mount(2)` remains for simple, interactive, and legacy code, and userland helpers still accept option strings; but everything that mounts *programmatically and often* — init systems, runtimes, test harnesses — gets strictly better behavior from the new path. LWN's coverage of the patch series, [Six (or seven) new system calls for filesystem mounting](https://lwn.net/Articles/759499/), records the design debate, including why `fsopen()`'s context lives behind an fd rather than a handle in a new table.

## Security notes

The API keeps the old privilege model and adds fd-specific hazards. `fsopen()` and `fsconfig()` require `CAP_SYS_ADMIN` (in the governing user namespace); unprivileged callers get `EPERM` at `fsopen()`, not at attach time — fail fast by design. Mount fds are ordinary file descriptors: they cross `execve()` (unless `FSMOUNT_CLOEXEC`/`O_CLOEXEC` is used) and can be *sent* to other processes, so a privileged helper that hands out mount fds is handing out attach capability — close them or pass them deliberately. `mount_setattr()` requires `CAP_SYS_ADMIN` in the mount's owning user namespace ([mount_setattr(2)](https://man7.org/linux/man-pages/man2/mount_setattr.2.html)), which is what lets an idmapped-mount owner re-attribute their own mount without getting the host's. Finally, note what the API does *not* change: mount propagation semantics ([namespaces](namespaces.md)) are unchanged — a mount attached into a `shared` peer group still leaks to peers unless you made it private first, the same [container footgun](../../containers/overlay-mount-options.md) as before.

## Demo: simulating the fs_context lifecycle

```python
#!/usr/bin/env python3
"""Mount-API state machine simulator. Models the fs_context lifecycle of the
new mount API (fsopen -> fsconfig -> CMD_CREATE -> fsmount -> move_mount),
including the per-context kernel log ring that survives failed attempts.
Pure stdlib, deterministic."""

LOG_RING = 8   # fsopen(2): log buffer holds a bounded number of messages

class FsContext:
    def __init__(self, fstype):
        self.fstype = fstype
        self.state = "FS_CONTEXT_FOR_MOUNT (fresh)"
        self.params = {}
        self.log = []          # ring buffer, oldest overwritten
        self.truncated = 0

    def _log(self, msg):
        if len(self.log) == LOG_RING:
            self.log.pop(0); self.truncated += 1
        self.log.append(f"[{self.fstype}] {msg}")

    def fsconfig(self, cmd, key=None, value=None):
        if self.state == "FAILED":
            return "EBADF: context is dead"
        if cmd == "FSCONFIG_SET_STRING":
            self.params[key] = value; self._log(f"{key}={value!r}"); return "0"
        if cmd == "FSCONFIG_SET_FLAG":
            self.params[key] = True; self._log(key); return "0"
        if cmd == "FSCONFIG_CMD_CREATE":
            if self.state == "FS_CONTEXT_FOR_MOUNT (fresh)" and "source" not in self.params:
                self.state = "FAILED"; self._log("get_tree: no source specified")
                return "EINVAL"
            # superblock re-use: same fs+params share one superblock
            self.state = "GOT_TREE"; self._log("get_tree: superblock ready")
            return "0"
        return "EINVAL"

    def fsmount(self, attr_flags=""):
        if self.state != "GOT_TREE":
            return "EBADF/EINVAL: no tree attached"
        self.state = "FSMOUNTED"; self._log(f"mount object (flags={attr_flags})")
        return "mnt_fd"

    def move_mount(self, to):
        if self.state != "FSMOUNTED":
            return "EINVAL: fsmount() first"
        self.state = "MOVED"; self._log(f"attached at {to}")
        return "0"

    def dump_log(self):
        out = list(self.log); self.log.clear()
        return out, self.truncated

print("=== attempt 1: ext4 mount that fails on a typo'd option ===")
fc = FsContext("ext4")
print("fsconfig(SET_STRING, 'errors', 'remount-ro') ->", fc.fsconfig("FSCONFIG_SET_STRING", "errors", "remount-ro"))
print("fsconfig(SET_FLAG, 'nosuid')               ->", fc.fsconfig("FSCONFIG_SET_FLAG", "nosuid"))
print("fsconfig(SET_STRING, 'soucre', '/dev/vdb') ->", fc.fsconfig("FSCONFIG_SET_STRING", "soucre", "/dev/vdb"))
print("fsconfig(CMD_CREATE)                       ->", fc.fsconfig("FSCONFIG_CMD_CREATE"))
msgs, trunc = fc.dump_log()
for m in msgs:
    print("   read():", m)
print("state:", fc.state)

print("\n=== attempt 2: same context reused? no - new fsopen, valid source ===")
fc2 = FsContext("ext4")
print("fsconfig(SET_STRING, 'source', '/dev/vdb') ->", fc2.fsconfig("FSCONFIG_SET_STRING", "source", "/dev/vdb"))
print("fsconfig(CMD_CREATE)                       ->", fc2.fsconfig("FSCONFIG_CMD_CREATE"))
print("fsmount(MOUNT_ATTR_RDONLY)                 ->", fc2.fsmount("MOUNT_ATTR_RDONLY"))
print("move_mount('/srv/data')                    ->", fc2.move_mount("/srv/data"))
msgs, trunc = fc2.dump_log()
for m in msgs:
    print("   read():", m)
print("state:", fc2.state, "| log ring truncated messages:", trunc)
```

Real output:

```text
=== attempt 1: ext4 mount that fails on a typo'd option ===
fsconfig(SET_STRING, 'errors', 'remount-ro') -> 0
fsconfig(SET_FLAG, 'nosuid')               -> 0
fsconfig(SET_STRING, 'soucre', '/dev/vdb') -> 0
fsconfig(CMD_CREATE)                       -> EINVAL
   read(): [ext4] errors='remount-ro'
   read(): [ext4] nosuid
   read(): [ext4] soucre='/dev/vdb'
   read(): [ext4] get_tree: no source specified
state: FAILED

=== attempt 2: same context reused? no - new fsopen, valid source ===
fsconfig(SET_STRING, 'source', '/dev/vdb') -> 0
fsconfig(CMD_CREATE)                       -> 0
fsmount(MOUNT_ATTR_RDONLY)                 -> mnt_fd
move_mount('/srv/data')                    -> 0
   read(): [ext4] source='/dev/vdb'
   read(): [ext4] get_tree: superblock ready
   read(): [ext4] mount object (flags=MOUNT_ATTR_RDONLY)
   read(): [ext4] attached at /srv/data
state: MOVED | log ring truncated messages: 0
```

The instructive detail is attempt 1: the typo'd `soucre` key is accepted at `fsconfig()` time (the kernel cannot know a filesystem does not use that key until the fs's `parse_param` runs), and the failure only surfaces at `CMD_CREATE` — but the log ring then tells you exactly what the parser saw. That two-phase behavior — accumulate anything, validate at the command — is the API's error-handling contract, and reading the context fd is how you get the diagnostics `mount(2)` never had.

## References

- [Kernel mount_api documentation — fs_context design, purposes, ops](https://docs.kernel.org/filesystems/mount_api.html)
- [fsopen(2) — context creation, log ring, CAP_SYS_ADMIN requirement](https://man7.org/linux/man-pages/man2/fsopen.2.html)
- [fsconfig(2) — the FSCONFIG_* command set](https://man7.org/linux/man-pages/man2/fsconfig.2.html)
- [mount_setattr(2) — mount attributes, AT_RECURSIVE, MOUNT_ATTR_IDMAP](https://man7.org/linux/man-pages/man2/mount_setattr.2.html)
- [open_tree(2) — grabbing and cloning mounts as fds](https://man7.org/linux/man-pages/man2/open_tree.2.html)
- [LWN: Six (or seven) new system calls for filesystem mounting](https://lwn.net/Articles/759499/)
- [Kernel idmappings documentation — idmapped mount algebra](https://www.kernel.org/doc/html/latest/filesystems/idmappings.html)

## Related Topics

- [Mounting](mounting.md) — mount(2), bind mounts, propagation, fstab, troubleshooting
- [Superblock internals](superblock.md) — what get_tree()/sget_fc() find or build
- [Mount namespaces](namespaces.md) — where move_mount() attaches, propagation rules
- [User namespaces](../processes/namespaces.md) — the privilege domain for unprivileged mounts
- [Capabilities](../../security/capabilities.md) — CAP_SYS_ADMIN scope checks on each step
- [systemd internals](../../admin/systemd-internals.md) — the heaviest production consumer
- [overlayfs](overlayfs.md) — a filesystem whose container mounts the new API serves
