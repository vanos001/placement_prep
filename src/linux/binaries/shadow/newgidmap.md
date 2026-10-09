# newgidmap — write subordinate GID mappings into a user namespace

## Overview

`newgidmap` is the setuid-root helper for the group half of user-namespace mapping: it writes `/proc/<pid>/gid_map` for a process whose user namespace the caller owns, after verifying that every requested range lies inside the caller's allocation in `/etc/subgid`. It ships in the Debian binary package `uidmap` alongside `newuidmap`, lives in `/usr/bin/newgidmap` (setuid root), and is invoked in lockstep with its UID twin — a namespace is not properly usable until both maps are installed.

The GID side is the one people forget, and the failure mode is distinctive: containers whose files all resolve to `nobody`/`nogroup`, processes that cannot belong to supplementary groups, and runtimes that half-work because `uid_map` succeeded and `gid_map` did not. Note that the binary is part of the separate `uidmap` package and is absent from minimal images — it is not installed in this container, so the behavior described here is the standard Debian/uidmap contract, to be verified on stripped-down hosts.

| Field | Value |
| --- | --- |
| Package | uidmap (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 (a userland helper, not an admin sbin tool) |
| Path | /usr/bin/newgidmap (setuid root, mode 4755 on standard installs) |
| First appeared | Modern era: Linux user namespaces (kernel 2.6.23, 2008) and the shadow 4.x subgid support for unprivileged container tooling |
| Standards | Not POSIX; Linux-specific, defined by namespaces(7) kernel semantics plus /etc/subgid policy |

## Synopsis

```
newgidmap pid gid lowergid count [gid lowergid count [gid lowergid count ...]]
```

Mapping triplets, all on one line:

```
newgidmap 4242 0 165536 65536                     # one full-range map
newgidmap 4242 0 1001 1 1 165536 65535            # rootless-container shape
```

Each triplet reads: inside-namespace start (`gid`), outside-namespace start (`lowergid`), length (`count`). No options; the interface is the argument list, mirroring `newuidmap` exactly.

## How It Works

### The kernel layer: /proc/<pid>/gid_map

Each line of `gid_map` is `ID-inside-ns ID-outside-ns length`, translating GIDs exactly the way `uid_map` translates UIDs. An empty map leaves every group ID unmapped — all files show `nogroup` (65534) from outside, and group-based access checks inside the namespace cannot resolve. The kernel-side rules parallel the UID case:

- The writer must have `CAP_SETGID` in the **parent** namespace (mapping IDs it may map), or be inside the new namespace mapping only its own GIDs.
- The whole map is delivered in a **single `write(2)`**; established mappings are not incrementally re-writable, and the man page documents a maximum of **5 triplets** per invocation for parent-side writes.

### The GID-specific gate: setgroups must be denied first

The one rule with no UID-side counterpart: a process that writes `gid_map` without `CAP_SETGID` in the parent namespace must first have `deny` recorded in `/proc/<pid>/setgroups` — otherwise the kernel rejects the write with `EPERM`. The ordering exists because setgroups(2) with an unmapped GID table would let a process hold supplementary-group credentials the map cannot represent:

```
unprivileged self-mapping:   setgroups must read "deny" before the gid_map write
newgidmap (setuid root):     holds CAP_SETGID in the parent ns,
                             so the deny step is not required
```

One modern refinement: since kernel 3.19, a namespace created by an unprivileged process has setgroups denied *automatically*. Verified on this container:

```
$ unshare -U --map-root-user sh -c 'cat /proc/self/setgroups'
deny
```

So the classic "forgot to deny setgroups" `EPERM` mostly bites on older kernels, on namespaces created by privileged code (where setgroups reads `allow`), and in scripts that assume the pre-3.19 order. Checking `/proc/<pid>/setgroups` before a hand-written gid_map write is the cheap diagnostic.

### The policy layer: /etc/subgid

```
$ cat /etc/subgid
bun:100000:65536
z:165536:65536
```

Same shape as `/etc/subuid`: `name:start:count` per user, normally auto-allocated by `useradd` from `/etc/login.defs` (`SUB_GID_MIN`, `SUB_GID_MAX`, `SUB_GID_COUNT`; 100000 / 600100000 / 65536 by default). `newgidmap` — running with full root privilege, where the kernel would let it map anything — is the component that enforces that every outside GID in every triplet belongs to the *caller's* subgid allocation.

```
$ grep -E '^SUB_GID' /etc/login.defs
SUB_GID_MIN                100000
SUB_GID_MAX             600100000
SUB_GID_COUNT               65536
```

The GID allocation normally mirrors the UID one account-for-account (this container's `/etc/subgid` matches its `/etc/subuid` line for line), but the two are independent files that can drift — different knobs (`usermod -W` for GIDs, `-v` for UIDs), different provisioning. Symmetry is hygiene, not law.

### gshadow and gid_map are different worlds

A common interview confusion: `/etc/gshadow` and `/proc/<pid>/gid_map` both sound like "the hidden group data". They are unrelated layers:

```
/etc/gshadow     per-group secrets: group password hashes, administrator
                 lists — a FILE in the account database, guarded by grpconv/grpck
/proc/<pid>/gid_map   per-namespace ID translation table — KERNEL state,
                 installed by newgidmap, visible to anyone who can read procfs
```

`newgidmap` never touches the account database; `grpconv` never touches procfs. The only thing they share is the word "group" and the shadow suite's custody of the first one.

### What the helper checks, then does

```
caller (uid/gid 1001, no caps)
   |
   | execve setuid-root helper
   v
newgidmap (euid 0, CAP_SETGID in parent ns)
   1. pid exists, and the caller owns that process
   2. every [lowergid, lowergid+count) slice lies inside the caller's
      /etc/subgid allocation
   3. single write(2) of all triplets  -->  /proc/<pid>/gid_map
   v
kernel installs the map; group IDs inside the namespace now resolve
```

### Always a pair

Rootless runtimes install both maps back-to-back, because the two halves fail independently and the symptoms differ:

```
newuidmap "$pid" 0 1001 1 1 165536 65535   # files owned by you on the host
newgidmap "$pid" 0 1001 1 1 165536 65535   # groups resolve inside the ns
```

Miss the GID call and the container boots, UIDs work, but every group lookup and every supplementary-group check misfires — the maddening half-broken state. LXC's unprivileged containers, podman's rootless mode, and `lxc-usernsexec` all issue the pair, with `lxc.idmap` lines (uid and gid separately) driving each.

## Options That Matter

| Element | Effect |
| --- | --- |
| `pid` | Target process ID, as visible to the caller; its user namespace receives the map. |
| `gid` | First GID as seen *inside* the namespace (start of the mapped block). |
| `lowergid` | First GID on the *outside* (host) side; must sit inside the caller's /etc/subgid range. |
| `count` | Number of consecutive GIDs to map; every mapped ID must stay in-range. |
| triplet count | Up to 5 triplets per invocation (documented limit for parent-side map writes). |

No options otherwise — unlike many suite tools there is not even a `-R` chroot flag here; the helper's only filesystem interactions are `/etc/subgid` and the procfs target.

## Usage Patterns

```bash
# Discover your group allocation (empty file = root cause of many failures)
cat /etc/subgid

# Confirm the helper exists on this image at all
command -v newgidmap || echo "install the uidmap package"

# Create a namespace with an empty map and note the pid
unshare -U sh -c 'echo $$ > /tmp/ns.pid; exec sleep 600' &

# Install the full subordinate range on the GID side
newgidmap "$(cat /tmp/ns.pid)" 0 165536 65536

# Verify both halves of the pair (the two must always match in shape)
cat /proc/$(cat /tmp/ns.pid)/uid_map /proc/$(cat /tmp/ns.pid)/gid_map

# Rootless-container shape on both maps
newuidmap "$pid" 0 1001 1 1 165536 65535
newgidmap "$pid" 0 1001 1 1 165536 65535

# The manual deny step: idempotent today (auto-denied on 3.19+), required on old
# kernels and for privileged-created namespaces where setgroups reads "allow"
unshare -U --map-root-user sleep 300 &
echo deny > /proc/$!/setgroups

# Debug a runtime that mapped UIDs but not GIDs: half-broken containers
podman run --rm alpine stat -c '%U:%G' /etc/hostname   # nobody in = gid_map issue

# Check the setgroups gate state before any hand-written gid_map attempt
cat /proc/$(cat /tmp/ns.pid)/setgroups

# The no-helper contrast, GID edition: the single self-map any user can write
unshare -U --map-root-user sh -c 'cat /proc/self/gid_map; cat /proc/self/setgroups'

# Confirm both maps have the same shape once the pair is installed
diff <(cat /proc/$(cat /tmp/ns.pid)/uid_map) <(cat /proc/$(cat /tmp/ns.pid)/gid_map)

# Baseline: the one-ID self-map needs no helper (setgroups auto-denied)
unshare -U --map-root-user sh -c 'id -g; cat /proc/self/setgroups'

# Confirm the GID grant actually covers a group your container needs
awk -F: -v me="$(id -un)" -v want=165540 '$1==me { if (want >= $2 && want < $2+$3) print "granted" }' /etc/subgid
```

As with its UID twin, you rarely type `newgidmap` by hand in production: container engines and LXC harnesses invoke it while assembling the namespace, and your contact points are `strace` traces, runtime logs, and `lxc.idmap` gid lines.

## Nuances and Gotchas

- **Paired or broken.** A namespace with uid_map but no gid_map is the most confusing state in rootless land: ownership works, groups do not. Always issue the pair and diff the two maps — they should be structurally identical.
- **The setgroups ordering rule.** For map writes without parent-namespace `CAP_SETGID`, setgroups must read `deny` first or the kernel returns EPERM on the gid_map write. Modern kernels (3.19+) auto-deny for unprivileged-created namespaces; the manual step matters for privileged-created namespaces and old kernels. The setuid helper sidesteps the whole rule via its parent-namespace capability.
- **Supplementary groups are fully governed by gid_map.** A process inside the namespace can only `setgroups`/`setgid` to GIDs that resolve through the map. If your container needs to run as an arbitrary group, that group's GID must be inside a mapped range — not merely present in `/etc/group`.
- **'deny' is forever, per namespace.** Once setgroups reads `deny`, it cannot be flipped back to `allow` for that namespace — by design. Scripts that deny setgroups and later try to restore supplementary groups must recreate the namespace.
- **Subgid containment is per-ID.** `newgidmap pid 0 165536 65537` fails when the last GID lands one past your allocation. Same off-by-one disease as the UID side.
- **Absent on minimal images.** `uidmap` is a separate package; this container lacks it. `command -v newgidmap` before anything else on a stripped-down host.
- **setuid stripped = helper dead.** `nosuid` mounts or hardened images that clear the bit leave the helper powerless; `stat -c '%a' /usr/bin/newgidmap` should read `4755`.
- **Direction discipline.** Inside first, outside second — the same reading order as uid_map lines. Backwards reading is the perennial review comment on userns patches.
- **Group databases do not translate themselves.** A gid_map makes IDs resolvable, but names still come from `/etc/group` inside the namespace. A container image with an empty group file shows numeric GIDs even with a perfect map — map problems and name-resolution problems are separate layers.
- **One-shot map.** Established maps are not patchable from the parent side; wrong map means tear down and recreate the namespace.
- **5-triplet ceiling** for parent-side writes, as documented — same workaround as the UID side (write from inside the child namespace when you need more extents).
- **`SUB_GID_*` in login.defs allocate; they do not enforce.** Enforcement lives in the helper's check against `/etc/subgid` at invocation time.

## Exit Status

The man page documents no exit-status table. In practice:

- `0` — gid_map written successfully.
- non-zero (1) — any refusal: bad pid, caller does not own the process, ranges outside `/etc/subgid`, too many triplets, kernel rejected the write (map already set, setgroups state, capability shortfall).

As with `newuidmap`, the helper does not label the failure class; reproduce with `strace` or read the runtime log when the exit code alone is ambiguous.

## Related Commands

- [`newuidmap`](./newuidmap.md) — the UID twin; the two are always invoked as a pair for one namespace.
- [`useradd`](./useradd.md) — allocates the /etc/subgid ranges (SUB_GID_* defaults from login.defs).
- [`usermod`](./usermod.md) — `-V`/`-W` grow the subordinate group ranges after the fact.
- [`gpasswd`](./gpasswd.md) — ordinary (non-subordinate) group administration, for contrast with the subgid world.
- [overview](./overview.md) — the shadow suite collection, including the uidmap helpers.
- [users-groups](../../admin/users-groups.md) — the GID model that subgid ranges extend.

## Interview Questions

### Q: What does the setgroups deny requirement do, and when does it apply?

It applies to writing `/proc/<pid>/gid_map` without `CAP_SETGID` in the parent namespace — i.e., exactly the unprivileged self-mapping case. The writer must first record `deny` in `/proc/<pid>/setgroups`, which permanently forbids setgroups(2) in that namespace; the kernel's order enforcement prevents a process from acquiring supplementary groups that its (empty or partial) GID map cannot legitimately represent. `newgidmap` sidesteps the requirement because setuid root gives it `CAP_SETGID` in the parent — one of the two concrete privileges the helper contributes (the other being the multi-ID map write itself).

### Q: Why do rootless runtimes treat newuidmap and newgidmap as one operation?

Because the kernel's UID and GID translations are independent maps that both start empty, and the container is only coherent when both are populated with matching shapes. UIDs alone give you correct file ownership but broken group resolution and supplementary-group checks; GIDs alone, the reverse. Every rootless stack therefore issues the pair with identical triplet structure, and the classic half-configured container — files owned correctly but groups showing `nogroup` — is what happens when one call succeeds and the other fails silently.

### Q: A container's files all show 'nogroup' from the host, though UIDs look right. What happened and what do you check?

The gid_map is missing or malformed while uid_map is fine. Check in order: `/etc/subgid` has an entry for the calling user; the `newgidmap` invocation (or the runtime log of it) succeeded — the count and ranges must mirror the uid_map exactly; the helper is present and still setuid (`4755`); and, for hand-written maps, that `deny` was written to setgroups before the gid_map write. The host-side reading of `/proc/<pid>/gid_map` versus the intended triplets settles it in one step.

### Q: Why does the kernel demand the setgroups deny before accepting a gid_map, and when does that requirement actually bite?

Because setgroups(2) would otherwise let a process adopt supplementary GIDs that its (empty or partial) gid_map cannot represent, breaking the translation invariant the map exists to provide. The requirement applies to writes made without `CAP_SETGID` in the parent namespace — the unprivileged self-mapping case. Since kernel 3.19 an unprivileged-created namespace auto-denies setgroups, so today the rule bites mainly on namespaces created by privileged code (setgroups reads `allow` there) and on older kernels; `newgidmap` itself is exempt because setuid root supplies the parent-namespace capability.

### Q: How does /etc/subgid policy interact with the kernel's capability model?

The kernel, given `CAP_SETGID` in the parent namespace (which setuid root has), would write any gid_map whatsoever. The helper is therefore the *only* place the subordinate-range policy can be enforced, and that is its core job: after confirming the caller owns the target process, it verifies every requested outside GID against the caller's `/etc/subgid` allocations before issuing the write. The result is a system where an unprivileged user can exercise a privileged kernel operation, but only within a resource grant an administrator (or `useradd` defaults) has already recorded — capability at the kernel boundary, policy at the helper.

### Q: What is the mapping direction in gid_map lines and helper arguments, and why does it matter?

Both list inside-namespace IDs first, outside-namespace (host) IDs second, followed by the length. The direction matters because every rootless debugging story — `nobody` listings, wrong file ownership, chown failures — starts with someone reading a map backwards and "fixing" the wrong side. It also matters for the helper's checks: only the outside range must sit inside `/etc/subgid`, while the inside range is arbitrary as long as the extents do not collide.

### Q: Where do the ranges in /etc/subgid come from, and can they differ from the uid side?

Same allocator, same defaults: `useradd` takes `SUB_GID_MIN` (100000), `SUB_GID_MAX` (600100000), and `SUB_GID_COUNT` (65536) from login.defs, so an account normally gets a GID allocation mirroring its UID one — this container's `/etc/subgid` (`bun:100000:65536`, `z:165536:65536`) matches `/etc/subuid` line for line. They are, however, independent files and can drift apart: `usermod -v` grows subuid ranges while `-W` grows subgid ones, and custom provisioning may allocate only one side. Rootless runtimes then map unequal shapes — legal at the kernel level, but confusing in `ls -l` output, so keeping the two symmetric is operational hygiene.

### Q: Map the failure modes: which symptom points at which broken layer?

`command not found` → the uidmap package is absent (minimal image). `operation not permitted` on the helper call → setuid stripped, or the caller does not own the target pid. Range rejection → the requested slice exceeds the caller's `/etc/subgid` allocation, usually an off-by-one on `count`. `nogroup`-everywhere listings with correct owners → gid_map missing or malformed while uid_map is fine — the half-configured container. Hand-written map rejected despite correct ranges → the setgroups gate: check `/proc/<pid>/setgroups` reads `deny` (automatic on kernels 3.19+ for unprivileged-created namespaces, manual for privileged-created ones). Read in that order and nearly every rootless-GID incident resolves.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/uidmap/newgidmap.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
