# newuidmap — write subordinate UID mappings into a user namespace

## Overview

`newuidmap` is the setuid-root helper that lets an *unprivileged* user install a multi-entry UID mapping into a user namespace. It writes to `/proc/<pid>/uid_map` for a namespace-creating process the caller owns, after verifying that every mapped range lies inside the caller's allocation in `/etc/subuid`. It ships in its own small Debian binary package `uidmap` (source package `shadow`), lives in `/usr/bin/newuidmap`, and is installed setuid root — the one piece of privilege that makes unprivileged user namespaces usable as containers.

It is often confused with `unshare --map-root-user`, which writes a single-UID self-map without any helper, and with the runtime-side machinery of `podman`/`runc`/`crun`/LXC, which ultimately invoke `newuidmap` (or an equivalent in-process equivalent) when they set up rootless containers. Note that minimal images frequently lack it — this container, for example, has the shadow account tools but no `uidmap` package, so the binary is absent here; everything below describes the standard Debian/uidmap behavior, and hedge accordingly on stripped-down systems.

| Field | Value |
| --- | --- |
| Package | uidmap (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 (a userland helper, not an admin sbin tool) |
| Path | /usr/bin/newuidmap (setuid root, mode 4755 on standard installs) |
| First appeared | Modern era: Linux user namespaces (kernel 2.6.23, 2008) and the shadow 4.x subuid patches built for unprivileged container tooling |
| Standards | Not POSIX; Linux-specific, defined by namespaces(7) kernel semantics plus /etc/subuid policy |

## Synopsis

```
newuidmap pid uid loweruid count [uid loweruid count [uid loweruid count ...]]
```

Mapping triplets, all on one line:

```
newuidmap 4242 0 165536 65536                     # one full-range map
newuidmap 4242 0 1001 1 1 165536 65535            # rootless-container shape
```

Each triplet reads: inside-namespace start (`uid`), outside-namespace start (`loweruid`), length (`count`). There are no options; the man page documents none beyond the usual `-h`.

## How It Works

### The kernel layer: /proc/<pid>/uid_map

Every process in a non-initial user namespace exposes its UID translation in `/proc/<pid>/uid_map`. Each line is:

```
ID-inside-ns    ID-outside-ns    length
```

An empty map means "this namespace's UIDs are unmapped": the namespace's processes run as the overflow identity (`nobody`, 65534) until someone writes the map. The kernel rules that make an unprivileged write possible at all:

- The writer is either a process with `CAP_SETUID` in the **parent** namespace (mapping only IDs it may map there), or a process inside the new namespace itself mapping only its own effective UID.
- The whole map must be delivered in a **single `write(2)`** call, and the kernel refuses conflicting rewrites of an established mapping — in practice helpers treat the map as write-once.
- Maps written from the parent side are limited in extent; the man page documents a **maximum of 5 mapping triplets** per invocation. (Richer maps must be written from inside the child namespace.)

Real root could write any map it likes. What makes the system safe is the policy layer:

### The policy layer: /etc/subuid

```
$ cat /etc/subuid
bun:100000:65536
z:165536:65536
```

Each line grants one user a contiguous range: `name:start:count`. These allocations are normally created automatically by `useradd` from `/etc/login.defs` (`SUB_UID_MIN`, `SUB_UID_MAX`, `SUB_UID_COUNT`; this container uses the defaults 100000, 600100000, 65536 per user). `newuidmap` enforces that every outside ID in every requested triplet falls inside the *calling user's* subuid ranges — the kernel would trust setuid root with anything, so the helper is where the restriction actually lives.

### Where the allocation comes from

```
$ grep -E '^SUB_UID' /etc/login.defs
SUB_UID_MIN                100000
SUB_UID_MAX             600100000
SUB_UID_COUNT               65536
```

`useradd` hands the first regular account 100000-165535, the second 165536-231071, and so on up the corridor — which is exactly what this container's `/etc/subuid` shows (`bun:100000:65536`, then `z:165536:65536`). The numbers only matter as *policy inputs*: nothing at the kernel layer knows or cares about 100000, and the helper would happily map any slice the file grants. Change the login.defs knobs and only future accounts are affected; grow an existing user's grant with `usermod -v`.

One mental-model point that separates people who have debugged rootless stacks from people who have read about them: you almost never type `newuidmap` yourself. A container engine or LXC harness invokes it as a child process while setting up the namespace — your direct contact is usually through `strace` output, runtime error logs, or an `lxc.idmap` config line that translates into one of these calls.

### What the helper checks, then does

```
caller (uid 1001, no caps)
   |
   | execve setuid-root helper
   v
newuidmap (euid 0, CAP_SETUID in parent ns)
   1. pid exists, and the caller is the owner of that process
   2. every [loweruid, loweruid+count) slice is inside the caller's
      /etc/subuid allocation
   3. single write(2) of all triplets  -->  /proc/<pid>/uid_map
   v
kernel validates + installs the map; the namespace now has real UIDs
```

Because the helper runs setuid root, the kernel-side capability check passes automatically; because the helper checks `/etc/subuid`, an unprivileged user can only spend the subordinate IDs granted to them. This combination — kernel capability plus userspace policy gate — is the entire security design.

### The rootless-container flow

A typical unprivileged runtime does, in essence:

```bash
# parent: create the child in a new user namespace (map still empty)
unshare -U sh -c 'echo $$ > /tmp/ns.pid; exec sleep 600' &
sleep 1

# parent: install the map for the child
pid=$(cat /tmp/ns.pid)
newuidmap "$pid" 0 1001 1 1 165536 65535

# kernel view from the outside
cat /proc/$pid/uid_map
```

That two-triplet shape is the standard rootless mapping: inside-namespace UID 0 (container root) maps to your *own* UID (1001 here), so files it creates appear on the host as yours; UIDs 1-65535 inside map to your subordinate range, so bulk file trees can be chowned inside the namespace without touching real system UIDs. LXC's `lxc.idmap` entries, podman's default rootless mapping, and `lxc-usernsexec` all reduce to exactly this call — the runtime just orchestrates the pid plumbing around it.

### Reading a real map

The kernel's rendering, captured on this container from a single-ID self-map (written by `unshare --map-root-user` itself — no helper needed, which is the useful contrast):

```
$ unshare -U --map-root-user sh -c 'cat /proc/self/uid_map; cat /proc/self/gid_map'
         0       1001          1
         0       1001          1
```

Columns, left to right: inside-namespace ID, outside-namespace ID, length — the same reading order as the helper's triplets. The outside value `1001` is this container's own user; inside the namespace that process is genuinely UID 0. A multi-triplet `newuidmap` call produces exactly this format with one line per triplet. Any inside ID the map does not cover resolves to the overflow identity (65534, `nobody`) from outside — the quick diagnostic for gaps or an unwritten map.

## Options That Matter

There is no flag family; the man page documents no options beyond help. The interface *is* the argument list:

| Element | Effect |
| --- | --- |
| `pid` | Target process ID, as visible to the caller; its user namespace receives the map. |
| `uid` | First ID as seen *inside* the namespace (start of the mapped block). |
| `loweruid` | First ID on the *outside* (host) side; must sit inside the caller's /etc/subuid range. |
| `count` | Number of consecutive IDs to map; every mapped ID must stay in-range. |
| triplet count | Up to 5 triplets per invocation (documented limit for parent-side map writes). |

## Usage Patterns

```bash
# Discover your allocation (or notice it is missing — root cause of many failures)
cat /etc/subuid

# Check the helper exists at all on a stripped-down image
command -v newuidmap || echo "install the uidmap package"

# Boot a process in a user namespace with an empty map, note its pid
unshare -U sh -c 'echo $$ > /tmp/ns.pid; exec sleep 600' &

# Map the whole subordinate range: container UIDs 0..65535 are your subuids
newuidmap "$(cat /tmp/ns.pid)" 0 165536 65536

# Verify the kernel received it
grep . /proc/$(cat /tmp/ns.pid)/uid_map

# Rootless-container shape: keep container-root == your own UID
newuidmap "$pid" 0 1001 1 1 165536 65535

# Two allocations (e.g. overlapping projects) as separate triplets
newuidmap "$pid" 0 165536 32768 32768 198272 32768

# Drive the pair together — a namespace is not usable until both maps exist
newuidmap "$pid" 0 1001 1 1 165536 65535 && newgidmap "$pid" 0 1001 1 1 165536 65535

# Diagnose an "operation not permitted" from your container runtime:
# the runtime logs which helper call failed — reproduce it by hand
strace -f -e trace=openat,write podman run --rm alpine true 2>&1 | grep uid_map

# The no-helper contrast: the one map every user can write unaided
unshare -U --map-root-user sh -c 'cat /proc/self/uid_map'

# Bound-check a candidate map against your allocation before invoking
awk -F: -v me="$(id -un)" '$1==me { if (165536+65536 <= $2+$3) print "fits" }' /etc/subuid

# Show that subuid policy is read per-invocation, not cached in the kernel
cat /proc/$(cat /tmp/ns.pid)/uid_map   # before and after changing /etc/subuid

# Prove the baseline: a one-ID self-map needs no helper at all
unshare -U --map-root-user sh -c 'id -u'   # prints 0
```

## Nuances and Gotchas

- **Absent on minimal systems.** `uidmap` is its own package and is not pulled in everywhere; a container without it cannot do multi-ID rootless mapping. `command -v newuidmap` is step one of any rootless-debugging session. (It is missing from this very container.)
- **Ownership, not mere existence.** The caller must *own* the target process. Pointing the helper at an unrelated pid is refused — this is the anti-abuse boundary that lets the binary stay setuid.
- **Subuid containment is checked per-ID, not per-start.** `newuidmap pid 0 165536 65537` fails if the last ID falls outside your range; off-by-one counts are the classic error.
- **Direction confuses everyone.** Kernel map lines and helper triplets both list inside-namespace first, outside second. Reading `uid_map` "backwards" is the most common debugging mistake with rootless UID issues.
- **The pid is namespace-relative.** You address the target by a PID as visible from *your* namespace. After a runtime forks into a new PID namespace, the PID you see and the PID it sees differ — scripts that pass the wrong side's PID get "no such process", not a mapping error.
- **Empty map = nobody.** Until the map is written, all files in the namespace appear as `nobody:nogroup` (65534) from outside. Symptoms: `ls -l` showing `nobody` for files you know are yours — the map (or the gid map) is missing, not permissions.
- **setuid must actually work.** On filesystems mounted `nosuid`, or in images that strip setuid bits, the helper loses its privilege and fails. Rootless runtimes on such hosts fall back or fail outright — check `stat -c '%a' /usr/bin/newuidmap` (expect `4755`).
- **One map, one write.** You cannot patch an established map incrementally from the parent side; a wrong map means tearing the namespace down and starting over. Get the triplets right before the call.
- **5-triplet ceiling.** Complex multi-range layouts hit the documented cap; runtimes that need more write the map from inside the child namespace instead, where the kernel's own limits are looser.
- **`unshare --map-root-user` needs no helper** because it maps exactly one ID (your own) — the kernel allows every unprivileged user that single self-map. The helper exists precisely for everything beyond that.
- **login.defs `SUB_UID_*` are allocation defaults, not enforcement.** They govern what `useradd` writes into `/etc/subuid`; the enforcement is the helper's range check against that file. Editing login.defs afterwards changes nothing for existing users.
- **Subuid policy is read at invocation time.** The helper opens `/etc/subuid` when it runs; already-established namespace maps are unaffected by later edits to the file, and there is no daemon to reload. Fixing an under-allocated range means fixing the file, then recreating the namespace.
- **The helper is audited, not the write.** Because the kernel would accept anything from setuid root, security review of this mechanism means auditing the helper's range logic — one small, stable code path — rather than trusting a broad kernel feature. The same review pattern applies to `sudo`/`visudo`: capability at the edge, policy in a small userspace gate.

## Exit Status

The man page documents no exit-status table. In practice:

- `0` — map written successfully.
- non-zero (1) — any refusal: bad pid, caller does not own the process, requested ranges outside `/etc/subuid`, too many triplets, kernel rejected the write (map already set, setgroups state, permissions).

Script the check as `newuidmap ... || die` — the helper does not distinguish policy failures from kernel failures on its face; the runtime log or `strace` does.

## Related Commands

- [`newgidmap`](./newgidmap.md) — the twin for `/proc/<pid>/gid_map` and `/etc/subgid`; always invoked in pairs with this one.
- [`useradd`](./useradd.md) — allocates the /etc/subuid ranges this helper spends (SUB_UID_* from login.defs).
- [`usermod`](./usermod.md) — `-v`/`-w` grow the subordinate ranges after the fact.
- [`userdel`](./userdel.md) — removes the allocation when the account goes away.
- [overview](./overview.md) — the shadow suite collection, including the uidmap helpers.
- [users-groups](../../admin/users-groups.md) — the UID model that subuid ranges extend.

## Interview Questions

### Q: Why does newuidmap need to be setuid root if user namespaces are "unprivileged"?

The kernel lets an unprivileged creator map only its own effective UID from inside the namespace — a single-ID self-map. Writing a multi-entry map from the parent side requires `CAP_SETUID` in the parent namespace, which an ordinary user lacks; the setuid-root helper contributes that capability. The security is preserved because the helper itself enforces `/etc/subuid` containment and ownership of the target process — it is a policy gate wrapped around a capability, which is the standard pattern for exposing privileged kernel operations to unprivileged users.

### Q: Explain the two-triplet invocation `newuidmap $pid 0 1001 1 1 165536 65535` and where you have seen it.

Triplet one maps inside-namespace UID 0 (container root) to the host's UID 1001 — the calling user — so files created by "root" inside land on the host owned by the real user. Triplet two maps inside UIDs 1-65535 to the user's subordinate range starting at 165536, giving the namespace a wide, safe pool for `chown` inside. This is exactly the default rootless mapping shape of podman and friends, and the same shape LXC writes from `lxc.idmap` entries. It answers the container "root without root" question in one line of argv.

### Q: Rootless podman on a server fails with 'newuidmap: uid is out of range'. Diagnose.

Read it in layers. First, does `/etc/subuid` contain an entry for the running user at all — minimal images and LDAP/NSS-based accounts often have none (subordinate allocations are written at `useradd` time). Second, is the requested count larger than the allocation (off-by-one on the range end is endemic). Third, is the helper actually setuid (`stat -c '%a' /usr/bin/newuidmap`), or has a hardened image stripped it or mounted /usr `nosuid`. Each layer — allocation, arithmetic, file mode — is independently common enough to check in that order.

### Q: Why is a freshly created user namespace's file listing full of 'nobody'?

The namespace's uid_map is still empty, so no inside UID has a host-side translation; the kernel displays the overflow identity, 65534 (`nobody`), for every such file. The fix is writing the map — with `newuidmap` for a multi-ID map — and usually `newgidmap` alongside it, since group resolution fails the same way without a gid_map. The `nobody`-everywhere symptom means "mapping problem", not "permissions problem", and treating it with chmod makes things worse.

### Q: Why is the range policy in a setuid helper instead of in the kernel reading /etc/subuid?

Because the two layers answer different questions. The kernel enforces *capability* semantics — who may write a map at all — and keeps that logic small, stable, and free of filesystem dependencies; reading `/etc/subuid`, a distribution-administered policy file with its own format history, is a userspace concern. Putting policy in the helper means distributions can evolve it (range syntax, allocation tools, audit behavior) without kernel releases, and the trusted computing base stays a few hundred lines of reviewable code rather than a filesystem-coupled kernel path. It is the sudo pattern applied to namespaces: privilege at the boundary, policy in a small audited gate.

### Q: What limits how many mappings you can install, and where does the number 5 come from?

The man page documents a maximum of 5 mapping triplets per `newuidmap` invocation, which matches the kernel's tight limit on the number of extents a map written from the parent namespace may have. It is rarely binding — standard rootless layouts use one or two triplets — but multi-tenant designs that stitch several subuid allocations into one namespace hit it, and their workarounds (writing the map from inside the child namespace, or consolidating ranges) are good design-level interview follow-ups.

### Q: Where do the ranges in /etc/subuid come from, and what happens when they run out?

`useradd` allocates them at account creation from `/etc/login.defs`: `SUB_UID_MIN` (default 100000), `SUB_UID_MAX` (600100000), and `SUB_UID_COUNT` (65536) — so the first account gets 100000-165535, the second 165536-231071, and so on upward. This container's real `/etc/subuid` (`bun:100000:65536`, `z:165536:65536`) shows exactly that arithmetic. When the corridor is exhausted — roughly 9000 users under the defaults — new accounts simply get no allocation, and rootless tooling fails for them until an admin carves ranges manually (or `SUB_UID_COUNT` is reduced). `usermod -v` can append additional ranges after the fact.

### Q: Map the failure modes: which symptom points at which broken layer?

`command not found` → the uidmap package is missing (minimal image). `operation not permitted` from the helper → setuid stripped by a `nosuid` mount or a hardened image, or the caller does not own the target pid. `uid is out of range`/range rejection → arithmetic or policy: the requested slice exceeds the caller's `/etc/subuid` allocation. `nobody`-everywhere listings → the map was never written (empty uid_map), the classic missing-or-failed-call symptom. Exit non-zero with no message nuance → check the runtime log or `strace`; the helper does not classify failures for you. Diagnosing in that order — presence, privilege, policy, map state — resolves nearly every rootless-UID incident.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/uidmap/newuidmap.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
