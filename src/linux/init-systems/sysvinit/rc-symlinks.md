# rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics

## Overview

The `/etc/rc0.d` through `/etc/rc6.d` directories (plus `/etc/rcS.d`) are where sysvinit's boot order actually lives. Each contains nothing but symlinks back into `/etc/init.d`, named so that a plain directory listing *is* the execution order: `S20ssh` means "start sshd at position 20 of this runlevel," `K80ssh` means "stop sshd at position 80." PID 1 never reads these directories itself — it delegates each runlevel change to `/etc/init.d/rc <N>`, a shell script that walks the relevant directory and executes the links in name order. This indirection is the mechanism that lets packages install themselves into the boot process by creating links rather than editing a master config, and it is the mechanism every later init system replaced with something declarative.

Two layers of ordering coexist, and knowing which one is authoritative matters. In the original scheme, the two-digit sequence number `NN` is the whole story, with lexicographic order on the remainder of the name as tiebreak. On dependency-mode systems (insserv, since Debian squeeze 6.0), the numbers are recomputed artifacts; the real order comes from the `.depend.boot` / `.depend.start` / `.depend.stop` files that insserv generated from LSB headers, with startpar consuming the same files for parallel batches. The links still matter — they encode runlevel membership and stop-side position — but "S20 runs before S21" is only guaranteed where no dependency edge says otherwise.

This page is the mechanical companion to the runlevel model: [Runlevels in Depth](./runlevels.md) explains what runlevels mean, [The sysvinit Boot Sequence](./boot-sequence.md) places the rc pass inside the full boot timeline, and [LSB Init Script Headers](./lsb-headers.md) explains where the dependency order comes from. Here the focus is the filesystem itself: naming grammar, the transition algorithm, update-rc.d as the supported way to maintain the links, the rcS.d/sysinit pass, and the rc.local convention.

## The Layout: /etc/rcN.d and /etc/rcS.d

Seven start-side directories plus the boot-phase directory:

```
/etc/rc0.d/    halt        (K-heavy: everything stops)
/etc/rc1.d/    single-user (S: sulogin path; daemons stopped)
/etc/rc2.d/    multi-user  (Debian default; S-heavy)
/etc/rc3.d/    multi-user + networking services (Debian: like 2)
/etc/rc4.d/    multi-user (Debian: like 2)
/etc/rc5.d/    multi-user + X display manager (elsewhere)
/etc/rc6.d/    reboot      (K-heavy mirror of 0)
/etc/rcS.d/    boot/sysinit phase (one-shot setup, run once at boot)
```

Every entry is a symlink into the init script directory — never a copy:

```
$ ls -l /etc/rc2.d/S02ssh
lrwxrwxrwx 1 root root 13 Jun  1 10:00 /etc/rc2.d/S02ssh -> ../init.d/ssh
```

The relative target `../init.d/ssh` matters for one reason: the directories are relocatable as a unit. RHEL-family distributions keep the real directories at `/etc/rc.d/rc0.d`–`/etc/rc.d/rc6.d` and preserve `/etc/rc0.d`–`/etc/rc6.d` as compatibility symlinks pointing into `rc.d/` — scripts that hardcode either path still work. The content scheme (S/K plus two digits plus name) is identical across distributions; only the parent directory differs.

## Naming Grammar and Ordering Rules

The grammar is exactly `[SK][0-9][0-9]<name>`:

- Leading `S` — the link is a *start* link; rc invokes `/etc/init.d/name start`.
- Leading `K` — the link is a *kill/stop* link; rc invokes `/etc/init.d/name stop`.
- `NN` — a two-digit sequence number. Ordering is numeric on `NN` first (`S9x` would sort before `S10x` if it existed; the two digits are zero-padded precisely so lexicographic and numeric order coincide).
- `<name>` — the service name; it must match the script basename in `/etc/init.d` for the link target to resolve.

Within the same `NN`, ordering falls back to a lexicographic comparison of the remaining name: with `S20cron` and `S20ssh` both present, `cron` runs first. Equal numbers are common in dependency mode because the number encodes graph depth rather than hand-chosen priority — a topological sort naturally assigns the same depth to independent services. The name tiebreak is stable but meaningless semantically; never build a design on "cron before ssh because c < s."

One consequence worth internalizing: the *name* part is load-bearing for the K/S decision and for tooling that parses listings, but renaming a symlink's service part while keeping its sequence number is a common hand-editing mistake — the link then points at a nonexistent script (broken symlink, silently skipped with an error) or at the wrong service. Tooling that respects `S{NN}name` uniformly (`update-rc.d`, `insserv`, chkconfig) exists precisely so humans stop writing these names.

## What /etc/init.d/rc Does on a Runlevel Transition

`/etc/init.d/rc` is a shell script shipped by `sysvinit-core` — not part of the `init` binary. init invokes it through the `wait` lines of `/etc/inittab` (for example `l2:2:wait:/etc/init.d/rc 2`), and passes context in the environment: init sets `RUNLEVEL` and `PREVLEVEL` for the rc process, with `PREVLEVEL=N` (or unset) marking a fresh boot rather than a transition. The script then performs a fixed two-pass walk of `/etc/rcN.d`:

1. **The K pass (stop links).** For each `K*` link in the new runlevel's directory, rc runs `stop` — but only if the service is actually running, which in practice means the corresponding service had a start link in the previous runlevel (`rcPREVLEVEL.d`). On a fresh boot `PREVLEVEL` is `N` and there is nothing to stop, so K links in the boot path are inert. This is why "K link" does not mean "runs at every boot" — it means "runs on transitions *into* this level from a level where the service was active."
2. **The S pass (start links).** For each `S*` link in numeric-then-name order, rc runs `start` — unless the service was already started in the previous runlevel. A service enabled in both runlevel 2 and runlevel 3 is left running across a `telinit 3`; it is not bounced. Only services newly present in the target level get a start invocation.

Ordering within each pass is the interesting part. In static mode it is the symlink sort described above. In dependency mode, rc uses the `.depend.start` / `.depend.stop` files generated from LSB headers as the ordering source, with the symlink numbers as a secondary hint — this is what makes insserv-derived boots topologically correct rather than numerically lucky. Scripts marked interactive (via `X-Interactive: true` in the header, or the `<interactive>` keyword in `/etc/insserv.conf`) are serialized: a parallel batch (see [Parallel Booting and startpar](./parallel-booting.md)) is drained before the interactive script runs alone, so it owns the console. And rc guards against the classic footgun of running a start link whose script lacks the executable bit or whose target vanished — the link is skipped with a diagnostic rather than aborting the pass.

Two environment details complete the picture. The `wait` action in inittab means init blocks until the whole rc pass finishes before respawning gettys — nothing in the runlevel pass runs concurrently with init's bookkeeping. And the rc script exports the runlevel context to the scripts it calls, which is why well-behaved scripts can consult `$RUNLEVEL` when their behavior must differ between boot and a mid-run transition.

### Serial and Parallel Modes of the rc Pass

Nothing above requires the pass to be serial — it only requires that dependencies be honored before concurrency is introduced. Debian's rc script historically exposed exactly this choice through a `CONCURRENCY` setting (values `none`/`shell` for the serial walk, `startpar` for batched parallel execution), stored in `/etc/default/rcS` on older releases. The dependency-mode design makes the parallel option safe: because the order comes from the `.depend.*` graph, startpar can start every script whose predecessors have completed and still preserve the header-declared ordering — that combination (graph plus batches) is the subject of [Parallel Booting and startpar](./parallel-booting.md). Without a valid dependency graph, parallel mode is disabled for a reason: two racing scripts are the original failure that symlink sequencing was invented to avoid.

For the reader's model, the two modes differ only in *how the order is consumed*:

- **Serial:** iterate the computed order; run each script to completion; move to the next. Output is naturally ordered; wall-clock time is the sum of every script.
- **Batched (startpar):** consume the same order as a make-style schedule; launch ready scripts together; buffer per-script output; serialize anything marked interactive. Wall-clock time approaches the critical path of the dependency graph.

Everything else — K pass first, S-skip on already-running services, `PREVLEVEL`/`RUNLEVEL` context — is identical in both modes.

## Sequence Number Conventions

There is no enforced standard for `NN` values — only strong conventions that packages historically shared. The legacy (pre-dependency-mode) layering:

| Range | Conventional meaning | Typical legacy examples |
|---|---|---|
| 00–09 | earliest system work | `S01`-style leftovers, halt/reboot helpers on K side |
| 10–19 | core infrastructure: logging, device setup | `S10sysklogd`, `S11klogd`, `S12dbus` |
| 20–29 | the default daemon band | `S20cron`, `S20samba`, `S20ntp` (legacy `update-rc.d defaults` = 20) |
| 30–69 | application services with ordering needs | `S30`-`S69` web/app tiers behind their databases |
| 70–89 | late user-facing services | `S89atd`, `S89cron` on some layouts |
| 90–99 | end-of-boot conveniences | `S99gdm3`, `S99rc.local`, `S99stop-bootlogd` |
| K side | mirror position for stopping | legacy `defaults` stop = 80 → `K80name`; disable computes `100 − NN` |

On a dependency-mode system the numbers stop looking like a hand-drawn ladder and start clustering by graph depth. A representative (abridged) modern listing:

```
$ ls /etc/rc2.d
K01nfs-common  S01dbus       S01networking   S01rpcbind
S01kmod        S01procps     S02nfs-common   S02ssh
S04cron        S04rsyslog    S99rc.local
```

The pattern to recognize: everything that only needs `$local_fs` bunches at 01; network-adjacent services follow at 02–03; things needing `$named` or `$remote_fs` land deeper; and `S99rc.local` remains pinned at the end because its header demands `$all`. The numbers were *chosen by the topological sort*, which is why dependency-mode directories read like `S01, S01, S02, S04, S99` instead of the legacy `S10, S20, S89, S99` spread. If you see the legacy spread on a modern system, someone is managing links by hand or the box predates dependency booting.

## rcS.d — The Sysinit Pass vs the Runlevels

`/etc/rcS.d` is run once per boot by the inittab `si::sysinit:/etc/init.d/rcS` action (rcS itself delegates to `/etc/init.d/rc S`), before the default runlevel's rc pass. Its scripts are *one-shot system setup*, not services, and its LSB headers conventionally use `Default-Start: S`. The canonical cast, in the order a dependency graph produces them:

| Script | Job |
|---|---|
| `hostname.sh` | set the hostname early |
| `mountkernfs.sh` | mount `/proc`, `/sys` |
| `udev` | start udev, populate `/dev` |
| `mountdevsubfs.sh` | devtmpfs/pts/shm mounts |
| `checkroot.sh` | fsck `/`, mount `/` rw; source of `$local_fs`'s first promise |
| `checkfs.sh` | fsck other local filesystems |
| `mountall.sh` + `mountall-bootclean.sh` | mount everything else, clean tmp dirs |
| `procps` | apply sysctl settings |
| `bootlogd` | capture console output to a log while boot is still scrollback-fragile |
| `ifupdown-clean` / `networking` (older layouts) | interface state cleanup / bring up the network |
| `mountnfs.sh` + `mountnfs-bootclean.sh` | mount network filesystems (completes `$remote_fs`) |

Differences from the runlevel directories are structural, not just naming. There is no meaningful K pass in rcS.d at boot (nothing is running yet, `PREVLEVEL=N`), so its K links are vestigial; runlevels 0, 1, and 6 have almost nothing but K links (they exist to *stop* things); and rcS.d ordering is anchored by the `.depend.boot` file rather than `.depend.start`. Services in rc2.d can and do `Required-Start: $remote_fs`, which resolves only because `mountnfs.sh` ran in the S pass — the two directories are coupled through the virtual facilities, which is why a wrong facility token in a rc2.d service's header manifests as an rcS.d-phase ordering bug.

## The Stop Pass and the Shutdown Runlevels

The K side of the scheme deserves its own treatment because it inverts most intuitions. Runlevels 0, 1, and 6 are *stop-dominant*: their directories are nearly all K links, and entering them via `telinit 0`, `telinit 6`, or `telinit 1` from a multi-user level triggers the largest stop pass of the system's life. The transition algorithm is the same two-pass walk — K links for services that were running in the outgoing level, then S links for anything newly started — but the populations differ: `rc0.d` and `rc6.d` contain a handful of S links only for the scripts that must *perform* the halt or reboot (`halt`, `reboot`, `sendsigs`, `umountfs`, `umountroot` on Debian), while everything else is a K link being retired.

Three details separate people who have read a shutdown from people who have watched one:

- **Stop order is dependency order, reversed.** The `.depend.stop` file encodes "do not stop the facilities I declared until after me" — so syslog stops late (other scripts want to log their own shutdown), filesystems unmount late (everything wants its files closed first), and the root remount-to-ro is last. The stop sequence numbers on the links (`K01`, `K10`, `K90`) are consistent with that reversed graph, which is why the legacy stop convention (mirror the start number: `100 − NN`) lands in roughly the right place without a graph.
- **`sendsigs` is the terminator.** Before filesystems go away, the K pass sends SIGTERM then SIGKILL to remaining processes; scripts' own `stop` actions get their chance first, which is exactly why the action contract (graceful-then-forced termination) matters at the script level.
- **Runlevel 1 is not a stop-only level.** It keeps a small S set (single-user setup, sulogin path) and K links for every daemon; the transition into 1 stops services and starts almost nothing. See [Runlevels in Depth](./runlevels.md) for the state model and [The sysvinit Boot Sequence](./boot-sequence.md) for how `shutdown(8)` hands control to init to enter these levels.

The practical corollary for tooling users: a service installed with only K links (`update-rc.d foo defaults-disabled`, or a `disable`d service) is invisible at boot by design but fully visible to the stop pass machinery — which is exactly the state you want for "installed, not started, cleanly stoppable if something starts it anyway."

## update-rc.d Mechanics

update-rc.d(8) is the supported tool for maintaining these links, and on Debian it is what package maintainer scripts call. Its bookworm grammar:

```
update-rc.d [-f] name remove
update-rc.d name defaults
update-rc.d name defaults-disabled
update-rc.d name disable|enable [S|2|3|4|5]
```

The verbs, with the resulting filesystem effect:

- `defaults` — install `[SK]NNname` links using runlevel and dependency information from the script's LSB header. With no header position hints, sequence numbers come from the dependency graph. This is the *package install* verb.
- `defaults-disabled` — install only K links (start links suppressed): "install the package but do not enable the service."
- `disable` — rename existing start links to stop links, with the sequence number transformed to `100 − NN`: `S20cron` becomes `K80cron`. Restrict to specific levels with `disable 2` etc.; the option only operates on start runlevels `S, 2, 3, 4, 5` and defaults to all of them.
- `enable` — the exact inverse: `K80cron` back to `S20cron` (positive difference of the current number minus 100 restores the original position).
- `remove` — delete all links to the script. The man page is explicit that the script must have been *deleted already*; if `/etc/init.d/name` still exists, update-rc.d aborts unless forced with `-f`.

The legacy syntax deserves a paragraph because it saturates old documentation and old muscle memory: `update-rc.d foo defaults 20 80` and the fully explicit `update-rc.d foo start 20 2 3 4 5 . stop 80 0 1 6 .` (note the mandatory trailing dots) were the pre-dependency-mode grammar for choosing numbers by hand. Bookworm's update-rc.d no longer supports them as such — the man page states the old `start` and `stop` options "are no longer supported, and are now equivalent to the defaults option." Sequence numbers now come from the LSB headers via the dependency graph; hand-picked numbers are legacy.

The most safety-critical sentence in the man page is about *not* overwriting: "If any files named `/etc/rcrunlevel.d/[SK]??name` already exist then update-rc.d does nothing... it will never change an existing configuration, which may have been customized by the system administrator." The corollary is the classic trap the same man page documents: deleting a service's links to "disable" it fails at the next package upgrade, because the postinst reruns `update-rc.d foo defaults`, finds no links, and reinstalls the factory default positions. The correct way to disable is `update-rc.d foo disable` — the S→K rename preserves the stop path (the service still stops cleanly at shutdown) and survives upgrades. See [SysVinit Service Management Tooling](./tooling.md) for the full command-by-command treatment.

### A Worked Disable/Enable Walkthrough

The arithmetic is easiest to trust after watching it once. Start from a default install (`S02ssh` in rc2–rc5, `K01`-family stop links elsewhere) and disable per-level:

```sh
$ update-rc.d ssh disable 2
$ ls -l /etc/rc2.d | grep ssh
lrwxrwxrwx 1 root root 13 Jun  1 10:00 /etc/rc2.d/K98ssh -> ../init.d/ssh
#  S02 -> K(100-02): start link became a stop link, position preserved
$ ls /etc/rc3.d | grep ssh
S02ssh                       # other levels untouched
$ update-rc.d ssh disable    # now everywhere
$ ls /etc/rc5.d | grep ssh
K98ssh
$ update-rc.d ssh enable 2   # exact inverse: K98 -> S02 again
```

Two things to notice. First, the transform is lossless — `enable` restores the original `NN` because both directions use the `100 − NN` arithmetic, which is precisely why `disable`/`enable` can be treated as a reversible switch rather than a destructive edit. Second, the K link created by `disable` is a real stop link with a real position: on the next transition into runlevel 2 from a level where ssh was running, rc will run `stop` on it like any other K link. The service is disabled in the sense that boot no longer starts it — not in the sense that the system has forgotten how to stop it.

## insserv Artifacts: the .depend Files

In dependency mode the authoritative order lives in three files beside the scripts — insserv(8) calls them "the make(1) like dependency files produced by insserv for booting, starting, and stopping with the help of startpar(1)":

```
/etc/init.d/.depend.boot    # rcS.d ordering
/etc/init.d/.depend.start   # rc2.d–rc5.d start ordering
/etc/init.d/.depend.stop    # rc0.d–rc6.d stop ordering
```

Each line maps a script to its predecessors (abridged, illustrative):

```
# /etc/init.d/.depend.start (abridged)
mountkernfs.sh:
hostname.sh: mountkernfs.sh
networking: mountkernfs.sh udev
ssh: networking rsyslog
cron: rsyslog
rc.local: ssh cron nfs-common
```

Reading it as make(1) would: to run `ssh`, first complete `networking` and `rsyslog`; scripts with empty predecessor lists are roots of the pass. `/etc/init.d/rc` consults these files for pass order, and `startpar -M start` consumes the same file to execute independent scripts in parallel batches — one artifact, two consumers. They are generated, never hand-edited: after any header change or link surgery, `insserv -d` (use the default runlevels from the headers, restoring an edited scheme) or a round-trip through `update-rc.d -f name remove && update-rc.d name defaults` regenerates both the links and the files. A stale `.depend.start` is indistinguishable from a correct one by eye — treat any hand-edit of headers as incomplete until these files are rebuilt.

## The rc.local Convention

`/etc/rc.local` is the administrator's escape hatch: a plain shell script run automatically at the end of the multi-user boot, exempt from writing a full init script. The mechanism is itself an init script — `/etc/init.d/rc.local`, whose LSB header declares (in spirit) `Required-Start: $all` and `Default-Start: 2 3 4 5`. The `$all` facility is insserv's "after literally everything," which is what pins the link to the tail of the pass (the familiar `S99rc.local`, or `S01`-era equivalents on dependency-mode systems where `$all` still forces last position).

The contract is small but real: the file must be executable (`chmod +x /etc/rc.local`), it runs with `sh`, and it must end with `exit 0` — the shipped skeleton says so explicitly, because a nonzero exit from the last script surfaces as a boot-time "failed" marker. Under systemd the convention survives through `rc-local.service`, a compatibility unit conditioned on `/etc/rc.local` being executable and pulled into `multi-user.target` — one of the very few pure-sysvinit customs with a first-class successor. Anything more ambitious than rc.local belongs in a real script with a real header; see [Custom Init Scripts](./custom-init-scripts.md) for that path.

## Hand-Edited Symlinks vs update-rc.d

Hand-editing is possible — `ln -s ../init.d/foo /etc/rc2.d/S20foo` is a complete, working installation on a static-mode system — and it is still the fastest way to understand what the tooling does. As a *workflow* it loses on three documented counts.

First, upgrades clobber removals. The postinst of the package calls `update-rc.d foo defaults` on every upgrade; because update-rc.d refuses to touch existing links, your hand-*placed* links survive, but your hand-*deleted* links are silently reinstalled at factory positions. An administrator who "removed" a service by `rm /etc/rc2.d/S20foo` discovers it running again after the next patch release.

Second, hand edits bypass graph maintenance. On a dependency-mode system, new links need matching `.depend.*` entries; hand-made links carry no header-derived edges, so their position is honored only insofar as the graph tolerates it, and regeneration (`insserv -d`) may rewrite or strand them. A hand link that survives regeneration is the exception, not the rule.

Third, there is no undo and no dry run. update-rc.d/insserv operations are auditable (`-n`/`-s` on insserv, the documented "never change existing configuration" rule), reversible (`disable`/`enable` are exact inverses), and package-aware. The supported disable path — `update-rc.d foo disable`, optionally scoped to specific runlevels — exists precisely so that the stop path keeps working and the change survives upgrades. Anything you can express by hand-editing symlinks, you can express more safely through [SysVinit Service Management Tooling](./tooling.md).

## Listing and Reading Recipes

Read a runlevel's execution plan, annotated:

```
$ ls -l /etc/rc2.d
lrwxrwxrwx 1 root root 17 Jun  1 10:00 S01dbus       -> ../init.d/dbus
#   ^ perms ^ link to script          ^ S=start, NN=01, service name

lrwxrwxrwx 1 root root 17 Jun  1 10:00 S02ssh        -> ../init.d/ssh
lrwxrwxrwx 1 root root 17 Jun  1 10:00 S04cron       -> ../init.d/cron
lrwxrwxrwx 1 root root 17 Jun  1 10:00 S99rc.local   -> ../init.d/rc.local
```

What will actually start in the current runlevel, cross-checked against reality:

```sh
runlevel                        # e.g. "N 2" — N = previous (N = fresh boot)
ls /etc/rc$(runlevel | awk '{print $2}').d/S*   # the S pass, in name order
```

Audit questions worth scripting, with one-liners that answer them:

```sh
# Which services would be stopped in each shutdown runlevel?
for n in 0 1 6; do echo "== rc$n.d"; ls /etc/rc$n.d/K* 2>/dev/null; done

# Any broken links (hand-edited or half-removed packages)?
find /etc/rcS.d /etc/rc[0-6].d -xtype l -print

# The full start set across boot + default level, deduplicated:
ls /etc/rcS.d/S* /etc/rc2.d/S* | sed 's|.*/||' | sort -u
```

The broken-link check is the highest-yield habit: `-xtype l` reports symlinks whose targets are gone — the residue of removed packages and hand edits, and each one is a skipped diagnostic at every boot.

Three more comparisons answer the questions that follow an audit:

```sh
# What differs between runlevels 2 and 3 (the classic Debian pairing)?
diff <(ls /etc/rc2.d) <(ls /etc/rc3.d)

# Installed-but-disabled services: K links with no S counterpart anywhere
comm -23 <(ls /etc/rc0.d/K* /etc/rc6.d/K* | sed 's|.*/||' | sort -u) \
         <(ls /etc/rcS.d/S* /etc/rc[2-5].d/S* | sed 's|.*/||' | sort -u)

# Which runlevels start sshd?
for n in 0 1 2 3 4 5 6 S; do ls /etc/rc$n.d/S*ssh* 2>/dev/null | sed "s|^|rc$n: |"; done
```

The first is the everyday question ("what extra starts at 3?"); the second finds the `defaults-disabled` and `disable`d population; the third is the enablement fingerprint of one service across the whole scheme — the same question `chkconfig --list sshd` answers verbosely on RHEL.

## Interview Questions

### Q: What is the difference between an S link and a K link, and when does each actually run?

`S{NN}name` makes rc call the script with `start`; `K{NN}name` makes it call `stop`. But neither runs "at boot" unconditionally: rc runs K links only when transitioning into a runlevel from a previous one where the service was active — on a fresh boot (`PREVLEVEL=N`) the K pass is inert. S links run in the new level unless the service was already running in the previous level (a service enabled in both 2 and 3 is not bounced by `telinit 3`). So the link type encodes the *action*; the transition algorithm decides *whether* it fires.

### Q: You boot a machine that was cleanly shut down. Do any K scripts run? Why or why not?

No. On boot, init sets `PREVLEVEL=N` for the rc process, and rc's stop pass only stops services that were running in the previous runlevel — with `N` there is no previous runlevel and nothing to stop. The K links in `/etc/rc2.d` and friends exist for *transitions* (2→1, 3→0, and so on) and for the shutdown runlevels 0, 1, and 6, whose directories are deliberately K-heavy. A corollary interview probe: deleting only a service's S links leaves its K links intact, so it would still be stopped at shutdown even though it never starts — an incoherent state that `update-rc.d disable` (S→K rename) avoids by design.

### Q: What do the .depend.boot/.depend.start/.depend.stop files change about how rc works?

They replace symlink-number ordering with the topological order computed from LSB headers. In dependency mode, `/etc/init.d/rc` takes its pass order from `.depend.start`/`.depend.stop` (and `.depend.boot` for the rcS phase), with the two-digit numbers as secondary evidence; `startpar -M boot|start|stop` reads the same files to run independent scripts in parallel batches. Symlinks still encode runlevel membership and the stop-side position, but "S20 before S21" is no longer a guarantee — the graph is. Regenerating these files after header changes (`insserv -d`, or update-rc.d remove/defaults round-trip) is part of any header edit.

### Q: Why is `update-rc.d foo remove` the wrong way to disable a service?

Three reasons, straight from the man page's own warnings. First, it refuses to run while `/etc/init.d/foo` still exists (remove is the package-postrm verb), so you need `-f`, which is already a smell. Second, the removal is temporary: the next package upgrade runs postinst, which calls `update-rc.d foo defaults`, finds no links, and reinstalls factory defaults — your service re-enables itself. Third, it destroys the stop path along with the start path, so even in the window before the upgrade the service would not stop cleanly on shutdown. `update-rc.d foo disable` (optionally scoped per runlevel) renames S→K, survives upgrades, and is exactly reversible with `enable`.

### Q: How does rcS.d differ from rc2.d, mechanically?

Four differences. It is run once per boot by the `si::sysinit` inittab action (via `/etc/init.d/rcS`), not on runlevel changes. Its scripts are one-shot system setup — fsck, mounts, udev, sysctl — not resident services, and its headers use `Default-Start: S`. Its ordering comes from `.depend.boot` rather than `.depend.start`. And its K pass is meaningless at boot (nothing is running yet). The two directories are nonetheless coupled: rc2.d services depend on facilities (`$local_fs`, `$remote_fs`) whose providers complete in rcS.d, which is why a misplaced rcS.d script surfaces as a rc2.d failure.

### Q: A service is enabled in runlevels 2 and 3. What exactly happens on `telinit 3` from runlevel 2?

rc performs the transition with `RUNLEVEL=3`, `PREVLEVEL=2`. The K pass finds nothing to stop (the service has no K link in rc3.d). The S pass reaches the service's `S{NN}` link — and skips it, because the service was already started in the previous runlevel. Net effect: nothing runs, the daemon keeps its process, and no stop/start bounce occurs. This "S links in both levels are left alone" rule is the reason runlevel changes under sysvinit are cheap for services that persist across levels, and it is a favorite question for distinguishing people who have read `/etc/init.d/rc` from people who assume every runlevel change restarts everything.

## References

- [update-rc.d(8) — Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/update-rc.d.8.en.html) — link grammar, the "never change existing configuration" rule, disable/enable arithmetic, and the remove-on-upgrade trap.
- [invoke-rc.d(8) — Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/invoke-rc.d.8.en.html) — how actions reach the scripts the links point at, under policy control.
- [insserv(8) — Debian bookworm](https://manpages.debian.org/bookworm/insserv/insserv.8.en.html) — the `.depend.*` files, facility resolution, and regeneration options.
- [init(8) — sysvinit-core, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html) — the inittab actions that invoke rc, and the `RUNLEVEL`/`PREVLEVEL` environment.
- [LSB Core — Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — what the scripts behind the links must implement.
- [Debian Policy Manual, ch-opersys](https://www.debian.org/doc/debian-policy/ch-opersys.html) — the packaging rules that keep `/etc/rc*.d` coherent.

## Cross-References

- [/etc/init.d Scripts — Conventions and Patterns](./init-scripts.md) — the scripts the symlinks point into, action by action.
- [LSB Init Script Headers and Dependency Metadata](./lsb-headers.md) — where the `.depend.*` ordering originates.
- [SysVinit Service Management Tooling](./tooling.md) — update-rc.d, invoke-rc.d, and friends in command-by-command depth.
- [The sysvinit Boot Sequence](./boot-sequence.md) — where the rcS and rc passes sit in the full firmware-to-getty timeline.
- [Runlevels in Depth](./runlevels.md) — the state model these directories implement.
- [systemd — Unit Files](../systemd/unit-files.md) — the declarative replacement for symlink sequencing.
- [Init Systems Hub](../README.md) — section map and reading order for all init-system families.
- [Init System Comparison](../comparison.md) — symlink sequencing versus targets, runlevels, and dependency graphs side by side.
