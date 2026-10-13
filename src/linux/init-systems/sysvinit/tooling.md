# SysVinit Service Management Tooling

## Overview

Classic sysvinit has no service-management daemon to talk to — no API, no bus, no in-memory state. Everything an administrator or package does to a service therefore goes through one of two filesystem artifacts: the init script itself (`/etc/init.d/name`) and the runlevel links (`/etc/rc*.d/`). The tooling that grew around those artifacts is a layered stack, each layer answering a different question: *which links should exist?* (update-rc.d, insserv), *may this action run at all?* (invoke-rc.d and its policy-rc.d gate), *how do I run this action comfortably?* (service), and *in what order, in parallel?* (startpar, via the `.depend.*` files). Above all of it sit the PID 1 controls — telinit, runlevel, shutdown — that change the global state the links are evaluated against.

The layering is not academic. It explains behaviors that otherwise look arbitrary: why package installs do not start services inside a chroot (invoke-rc.d consults policy-rc.d), why `service` and `invoke-rc.d` can disagree (only one checks policy), and why "disable a service" has a right answer and a wrong answer on Debian (`update-rc.d disable` versus deleting links — the wrong answer silently reverts at the next package upgrade). It also explains the migration path: when systemd arrived, it was the middle layers that were replaced, and the compat tools (`service`, the SysV generator) were written to keep the outer layers working unchanged.

This page is command-first. [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) covers the filesystem these tools manipulate and [LSB Init Script Headers](./lsb-headers.md) covers the metadata they parse; here the focus is the tools themselves — grammar, semantics, failure modes, and the debugging recipes that make them safe to use on production systems. Where a tool belongs to another init family's world (chkconfig on RHEL), it is treated as the same job wearing different syntax.

## The Tool Stack at a Glance

| Tool | Package (Debian bookworm) | Layer | Role |
|---|---|---|---|
| `update-rc.d` | init-system-helpers | link management | install/remove/enable/disable `/etc/rc*.d` links from LSB headers |
| `insserv` | insserv | dependency engine | parse headers, resolve facilities, compute order, write `.depend.*`, reorder links |
| `invoke-rc.d` | init-system-helpers | policy-enforced action | run init script actions on behalf of maintainer scripts, honoring `policy-rc.d` |
| `service` | init-system-helpers | admin convenience | run an init script action (or a systemd unit) in a clean environment |
| `startpar` | startpar | parallel execution | run rc scripts in parallel batches from the `.depend.*` files |
| `chkconfig` | (RHEL-family; inline: chkconfig(8)) | link management | RHEL equivalent of update-rc.d + `--list` reporting |
| `rcconf`, `sysv-rc-conf`, `ntsysv` | (third-party TUIs; inline names) | admin convenience | ncurses front-ends over the same link operations |
| `telinit`, `runlevel`, `shutdown` | sysvinit-core | PID 1 control | change the runlevel, query it, schedule shutdown/reboot |

The layers in one picture:

```
        PID 1 control            state changes + queries
        telinit / runlevel / shutdown / halt
                   |
        runlevel transition       /etc/init.d/rc <N>
                   |                     |
   ordering from .depend.* + rc*.d links   startpar -M (parallel batches)
                   |
        policy + action layer     invoke-rc.d  <-- policy-rc.d gate
        convenience action layer  service
                   |
        target artifacts          /etc/init.d/<name>   /etc/rc*.d/[SK]NN*
                   |
        link maintenance          update-rc.d / insserv / chkconfig
```

Reading it bottom-up is the maintenance view (how links get created); reading it top-down is the boot view (how they get executed). The tools in the middle are the ones whose behavior differs by context — that is where the interview questions live.

## update-rc.d in Full

The bookworm synopsis is deliberately small:

```
update-rc.d [-f] name remove
update-rc.d name defaults
update-rc.d name defaults-disabled
update-rc.d name disable|enable [S|2|3|4|5]
```

Semantics that are easy to get wrong:

- `defaults` installs `[SK]NNname` links using the runlevel and dependency information from the script's LSB header — update-rc.d requires headers and defers the sequence numbers to the dependency graph. `defaults-disabled` is the same operation with only K links: "installed but not enabled."
- `disable` renames start links to stop links, computing the stop number as `100 − NN` (`S20cron` → `K80cron`); `enable` inverts it exactly. Both accept an optional list of start runlevels (`S 2 3 4 5`) to scope the change; with no list, all start runlevels are affected.
- `remove` deletes the links — and aborts if `/etc/init.d/name` still exists, unless `-f` forces it. It is the package-postrm verb, not an admin verb.
- The safety rule: *if any `[SK]??name` links already exist, update-rc.d does nothing.* It will never reposition or overwrite an existing configuration. This is why editing a script's header changes nothing until the links are regenerated (`-f remove` then `defaults`, or `insserv -d`).

The legacy grammar still pollutes old documentation and muscle memory: `update-rc.d foo defaults 20 80` and the fully explicit `update-rc.d foo start 20 2 3 4 5 . stop 80 0 1 6 .` (trailing dots mandatory). Bookworm's man page states the old `start`/`stop` options are no longer supported and are treated as equivalent to `defaults` — sequence numbers now come from the graph, not the command line.

A working session:

```sh
update-rc.d myapp defaults          # package-install path: links per LSB header
update-rc.d myapp defaults-disabled # install pre-disabled (K links only)
update-rc.d myapp disable           # S->K everywhere: survives upgrades
update-rc.d myapp disable 2         # only runlevel 2 stays stopped
update-rc.d myapp enable 3          # re-enable in runlevel 3
update-rc.d -f myapp remove         # force-remove links (script still present)
```

Division of labor: packages call `defaults` (install) and `remove` (purge) from maintainer scripts; administrators should confine themselves to `disable`/`enable`. The reasons are on the rc-symlinks page — the short version is that `remove` while the package is installed is temporary (the next upgrade reinstalls factory links) and destroys the shutdown path.

The maintainer-script choreography, for completeness — it explains both why the tools are split and why the "never overwrite" rule exists:

| Maintainer script | Invocation | Effect |
|---|---|---|
| `postinst` (configure) | `update-rc.d foo defaults` (via `deb-systemd-invoke` on mixed systems) | install links only if none exist; never repositions existing ones |
| `postinst` (configure) | `invoke-rc.d foo start` | start now, subject to policy-rc.d and runlevel state |
| `prerm` (upgrade/remove) | `invoke-rc.d foo stop` | stop before files are replaced, policy permitting |
| `postrm` (purge) | `update-rc.d foo remove` | the one legitimate `remove` — the script is already gone |

### A Complete Session

The three layers in one continuous transcript — install like a package, inspect like an auditor, disable like an administrator:

```sh
$ sudo update-rc.d myapp defaults            # layer 1: links from the LSB header
$ ls /etc/rc2.d | grep myapp                 # membership confirmed
S02myapp
$ awk '/### BEGIN INIT INFO/{b=1} b && /^# Provides:/ {print; exit} ' \
      /etc/init.d/myapp                      # what the header claims
# Provides:          myapp
$ sudo invoke-rc.d myapp start               # layer 2: policy-aware action
$ service myapp status                       # layer 3: direct, policy-blind check
[ ok ] myapp is running.
$ sudo update-rc.d myapp disable             # boot-enablement off, S->K rename
$ ls /etc/rc2.d | grep myapp
K98myapp                                     # stop path preserved, upgrade-proof
```

Every line above maps to a section of this page — and the point of the transcript is that nothing here ever edits a symlink or a `.depend.*` file by hand. The artifacts are outputs; the tools are the interface.

## invoke-rc.d and the policy-rc.d Layer

invoke-rc.d(8) is "a generic interface to execute System V style init script `/etc/init.d/name` actions, obeying runlevel constraints as well as any local policies set by the system administrator," and Debian Policy is blunt about who uses it: *all* init-script access by package maintainer scripts must go through invoke-rc.d. Two policies are built in without any helper: it refuses to start a service in a runlevel where the service is disabled, and it special-cases `status` (returning 4 instead of 0 when status is denied).

The extensible policy is `/usr/sbin/policy-rc.d`. When it exists, invoke-rc.d runs it — passing the initscript name, the requested action, and the runlevel(s) — before touching the script. Its verdict decides whether the action proceeds. The world-famous use is the chroot/container deny-all gate:

```sh
#!/bin/sh
# /usr/sbin/policy-rc.d - deny all service start/stop attempts here.
# Reason: this is a build chroot / container image; packages must not
#         start daemons while they are being installed.
echo "policy-rc.d: action denied in this chroot/container" >&2
exit 101
```

Exit status 101 is the convention every minimal container image ships: with this one file, `apt-get install openssh-server` in a chroot or docker build installs the package, updates the rc links, and *does not* attempt to start sshd — because the maintainer script's `invoke-rc.d ssh start` is vetoed before the script is touched. Without the gate, package management inside unbooted filesystems either starts daemons in the host namespace or spews errors. Variants are trivial: an allow-list policy (`case "$1" in sshd) exit 0 ;; *) exit 101 ;; esac`), a "deny only during restore" policy keyed on a flag file, or a fallback-mapping policy.

Variants are trivial and worth having in muscle memory. An allow-list policy that permits only named services; a deny-until-flag policy for restore windows:

```sh
#!/bin/sh
# /usr/sbin/policy-rc.d - allow-list: only sshd may be (re)started
case "$1" in
  sshd) exit 0 ;;
  *)    echo "policy-rc.d: denying $2 on $1 (not on allow-list)" >&2 ; exit 101 ;;
esac
```

Reading the full exit-code table (from invoke-rc.d(8)) pays for itself the first time a maintainer script misbehaves:

| Status | Meaning |
|---|---|
| 0 | success — script ran OK, or action was denied *and* `--disclose-deny` is not in effect |
| 1–99 | reserved for the init script itself (usually failure) |
| 100 | unknown init script name (not registered via update-rc.d, or missing) |
| 101 | action not allowed — runlevel or policy constraint |
| 102 | subsystem error (script or policy layer malfunction) |
| 103 | syntax error |
| 104 | `--query` mode: action *would* run |
| 105 | `--query` mode: uncertain |
| 106 | policy denied the action but supplied a fallback action |

The most-quoted line in that table is the fine print on 0: a denied action still yields exit 0 unless `--disclose-deny` is passed. That design is deliberate — maintainer scripts must not fail because a local policy chose not to start a daemon — and it is why debugging "why didn't my service start" requires looking at the policy layer, not just the exit code. Related options worth knowing: `--query` (answer without acting), `--quiet`, `--force` (bypass policy — severely discouraged in maintainer scripts), and `--skip-systemd-native`, which defers to `deb-systemd-invoke` on mixed systems where the service is really a native unit.

## service(8): The Administrative Wrapper

service(8) runs a System V init script — or a systemd unit — "in as predictable an environment as possible": it clears most environment variables (passing only `LANG`/`LC_*`, `TERM`, `PATH` and a few more) and sets the working directory to `/`. That predictability is the point: a script that works under your interactive shell but fails under `service` was depending on your environment, and `service` is how you reproduce the boot-time context.

Behavior that matters day to day:

```sh
service cron status          # runs /etc/init.d/cron status, returns its code
service ssh restart          # stop+start semantics as implemented by the script
service --status-all         # every init script with 'status', alphabetical:
                             #   [ + ]  running, [ - ] stopped, [ ? ] no status action
service cron --full-restart  # literally: run 'stop', then run 'start'
```

Two footnotes from the man page are interview-grade. First, on a systemd machine, a *unit* with the same name as an init script takes precedence — `service ssh restart` becomes a systemctl call for `ssh.service`, while `--status-all` still only reports on sysvinit jobs. Second, unlike invoke-rc.d, `service` does **not** consult `policy-rc.d`: it is the administrator's direct path, and the policy layer exists for the *automation* path. That asymmetry is the whole answer to "what's the difference between service and invoke-rc.d?"

## insserv: The Dependency Engine

insserv(8) calls itself "a low level tool used by update-rc.d" and warns that running it directly "unless you know exactly what you're doing... may render your boot system inoperable" — update-rc.d is the recommended interface for managing scripts. Its job: parse every LSB header, resolve facilities against `/etc/insserv.conf` (+ `/etc/insserv.conf.d/`), apply any header overrides from `/etc/insserv/overrides/`, topologically sort the graph, rewrite the rc*.d links consistently, and write the `.depend.boot`/`.depend.start`/`.depend.stop` files that rc and startpar consume.

Direct invocations you will actually see:

```sh
insserv -n          # dry run: parse and resolve, touch nothing (no symlinks, no .depend.*)
insserv -s          # show-all: print runlevel + sequence info, update nothing
insserv -d          # default: use Default-Start/Default-Stop from headers; restores an edited scheme
insserv -r myapp    # remove myapp from all runlevels
insserv myapp,start=2,3,4,5,stop=0,1,6   # add with explicit level override
```

The operational rhythm: `insserv -n` to validate a header edit, `insserv -d` to make it take effect, `insserv -s` to confirm placement. Exit code 0 means the service was installed/removed successfully; 1 means it was not — which is how an unsatisfiable `Required-Start` surfaces at tooling time rather than boot time.

## startpar: Parallel Batches (Pointer)

startpar(1) is the reason the `.depend.*` files are make-shaped: given `startpar -M boot|start|stop`, it reads the corresponding file from `/etc/init.d/` and executes scripts "in parallel," make-style — starting every script whose predecessors have finished, throttling by I/O-blocked weight, and buffering each script's output so lines from different scripts do not interleave. It is how dependency-mode sysvinit systems get most of the wall-clock win of parallelism while keeping the graph's ordering guarantees, and `X-Interactive`/`<interactive>` markers are how console-bound scripts get serialized safely. The mechanics and tuning live in [Parallel Booting and startpar](./parallel-booting.md); for this page, remember only that disabling a service and deleting `.depend.*` entries by hand do not compose — regenerate, never edit.

## chkconfig on RHEL

chkconfig(8) is the RHEL-family answer to update-rc.d, reading the `# chkconfig:` line described on the headers page:

```sh
chkconfig --add sshd        # create S20sshd in 2345, K80sshd elsewhere (from the chkconfig: line)
chkconfig --del sshd        # remove all its links
chkconfig --list            # table: service, each runlevel, on/off
chkconfig --list sshd       # single service
chkconfig --level 35 sshd on    # enable in runlevels 3 and 5 only
chkconfig sshd off          # disable in default levels
```

| Task | Debian (update-rc.d) | RHEL (chkconfig) |
|---|---|---|
| install links per package metadata | `update-rc.d foo defaults` | `chkconfig --add foo` |
| remove links | `update-rc.d -f foo remove` | `chkconfig --del foo` |
| disable / enable everywhere | `update-rc.d foo disable` / `enable` | `chkconfig foo off` / `on` |
| scope to specific levels | `update-rc.d foo disable 2` | `chkconfig --level 35 foo on` |
| report what is enabled | read `/etc/rc*.d` | `chkconfig --list` |
| ordering source | LSB headers + dependency graph | fixed numbers in the `chkconfig:` line |

The reporting asymmetry is cultural: RHEL ships a query verb, Debian's answer has always been "the filesystem is the report" — `ls /etc/rc2.d`. The TUI front-ends (`ntsysv` on RHEL; `rcconf` and `sysv-rc-conf` on Debian) are thin paint over the same operations and change nothing semantically.

## The PID 1 Control Layer: telinit, runlevel, shutdown

Above the service tooling sits the layer that moves the whole machine between states. `telinit N` asks init to switch runlevels — which triggers exactly the rc transition mechanics of the previous pages — and `telinit q` re-examines `/etc/inittab` without changing state (the safe way to apply inittab edits; `telinit S` or `telinit 1` descends to single-user, where the console hands you sulogin). `runlevel` prints the previous and current level from utmp (`N` as the previous field means "fresh boot, no previous level"); it is the scriptable form of `who -r`. `shutdown` is telinit with a schedule and courtesy: `-h`/`-r` choose halt versus reboot, `+m` or `now` schedule it, logged-in users get wall messages, and the final step is a runlevel change into 0 or 6 — meaning the full K-pass machinery of the rc-symlinks page is what actually stops your services. The halting side of that story (final scripts, SIGKILL sweep, unmount ordering) is treated in [Shutdown and Halt](./shutdown-halt.md).

```sh
telinit q                # re-read inittab, change nothing
runlevel                 # "N 2" -> no previous level, currently 2
shutdown -h +10 "Maintenance"   # schedule halt in 10 minutes, warn users
shutdown -r now          # reboot: init -> runlevel 6 -> K pass -> reboot
```

The design point worth internalizing: none of these commands touch a service directly. They change the global runlevel state, and the per-service consequences fall out of the link layout — the same principle as every other tool on this page.

## Read-Only Inspection

Fast answers to the four questions you actually get asked:

```sh
# 1. What runlevel am I in, and where did I come from?
runlevel                    # "N 2" = fresh boot, now at 2; "3 2" = was 3, now 2
who -r                      # same answer, utmp-sourced, with a timestamp

# 2. What happened across recent runlevel changes?
last -x | head              # shutdown/level entries from wtmp

# 3. What is enabled here?
ls /etc/rc2.d/S*            # start set of the current level
ls /etc/rcS.d/S*            # the boot phase's one-shot set

# 4. What does every script claim to provide? (awk over the header blocks)
awk '/### BEGIN INIT INFO/{b=1}
     b && /^# Provides:/{print FILENAME": "substr($0,15)}
     /^### END INIT INFO/{b=0}' /etc/init.d/* 2>/dev/null
```

The awk one-liner is the dependency-mode equivalent of "list the units": it extracts only in-block `Provides:` lines, which is the input facility resolution starts from. Pair it with `grep -l 'Required-Start.*\$remote_fs' /etc/init.d/*` when auditing for the classic `$local_fs`-instead-of-`$remote_fs` bug before an NFS rollout.

## Debugging Recipes

**Trace a script's execution.** Init scripts are shell; run them with the shell's own tracer, in the sanitized environment `service` provides:

```sh
sh -x /etc/init.d/myapp start        # every expansion, visible
service myapp start                  # then compare under the clean environment
```

The difference between the two runs is almost always an environment variable or a working-directory assumption — exactly the things service(8) normalizes.

**Preview package behavior in a chroot.** The honest simulation of "what will installing this package do to my boot config":

```sh
mount --bind /proc     /target/proc   # plus /sys, /dev for realistic tooling
mount --bind /dev      /target/dev
cat > /target/usr/sbin/policy-rc.d <<'EOF'
#!/bin/sh
exit 101
EOF
chmod +x /target/usr/sbin/policy-rc.d
chroot /target apt-get install myapp-daemon      # links installed, nothing started
ls -l /target/etc/rc2.d | grep myapp             # inspect the result safely
```

Bookworm's update-rc.d has no `--dry-run` flag, so containment *is* the dry run: a throwaway chroot (or VM snapshot) plus the deny-all policy gives you the same link changes with none of the side effects.

**Regenerate rather than hand-patch.** When the `.depend.*` files and the links disagree with the headers — after a botched manual edit or a half-removed package — the fix is a round trip, not surgery: `insserv -d` for the whole scheme, or `update-rc.d -f foo remove && update-rc.d foo defaults` for one service. Then `insserv -s` to verify placement.

**Never run `/etc/init.d/rc N` by hand on a live system.** It re-executes a full K-then-S pass against real services — stopping and starting whatever the transition math says, including things you did not intend to bounce. If you need to test a runlevel transition, do it in a VM against a snapshot: snapshot, `telinit 3`, observe, restore. The rc script is idempotent for already-running services, but the K pass is not forgiving, and one mis-sequenced stop is all it takes to lose a remote session on a headless box.

## The systemctl Mapping

The bridge table — what the sysvinit tool did, and what its systemd-era equivalent is:

| Task | sysvinit-era tooling | systemd equivalent |
|---|---|---|
| run a service action | `service foo start` / `invoke-rc.d foo start` | `systemctl start foo.service` |
| enable at boot | `update-rc.d foo defaults` / `enable` | `systemctl enable foo.service` |
| disable at boot | `update-rc.d foo disable` | `systemctl disable foo.service` |
| prevent even manual start | `chmod -x /etc/init.d/foo` (crude, breaks the script) | `systemctl mask foo.service` |
| install-time enable, policy-aware | `invoke-rc.d` + `policy-rc.d` | `deb-systemd-invoke` / presets |
| list what is enabled | `ls /etc/rc*.d` | `systemctl list-unit-files` |
| query state | `service foo status` | `systemctl status foo.service` |
| change "runlevel" | `telinit 3` | `systemctl isolate multi-user.target` |

Two lines of that table deserve unpacking. The mask row: sysvinit has no true mask — the nearest approximation is removing the executable bit, which also breaks manual starts and error messages clearly (that crudeness is exactly what `mask` fixed). And the last row: `telinit` still *works* on systemd systems because it is reimplemented as an alias for `systemctl isolate` against the runlevel-target mapping — one of many places where the old vocabulary is the compat layer. The generator that lets native systemd honor LSB headers at boot is covered from the systemd side in [systemd — systemctl and the CLI](../systemd/systemctl-cli.md); the legacy-script side is [Custom Init Scripts](./custom-init-scripts.md).

## Interview Questions

### Q: What is policy-rc.d for, and what does exit 101 mean?

`/usr/sbin/policy-rc.d` is the hook invoke-rc.d consults before running any init script action: it receives the script name, action, and runlevel(s), and its exit status decides. Exit 101 means "action denied by policy" — the canonical value shipped by container images and chroots so that package installs update the rc links without attempting to start daemons in an unbooted or foreign filesystem. It is also the mechanism for local rules ("never start this service during restore"). Note the counterpart: `service` bypasses policy entirely, and a denied action still returns 0 to the caller unless `--disclose-deny` is used — maintainer scripts must not fail because a local policy said no.

### Q: Explain the layering: update-rc.d vs invoke-rc.d vs service.

Different questions, different layers. update-rc.d answers "which links should exist" — it manipulates `/etc/rc*.d` and never starts anything. invoke-rc.d answers "may this action run, and does the local policy allow it" — it executes actions for maintainer scripts under runlevel constraints and the policy-rc.d gate. service answers "run this action the way the boot would" — a thin, policy-blind wrapper that normalizes the environment (clean env, cwd `/`) and, on systemd systems, redirects to the native unit when one exists. Roughly: configuration, automation, and interaction — in that order.

### Q: How do you disable a service across all runlevels on Debian, and why not just delete its links?

`update-rc.d foo disable` — which renames every start link to a stop link (`S20foo` → `K80foo`), optionally scoped per runlevel with `disable 2 3`. Deleting links fails three ways: `update-rc.d remove` aborts while the script still exists (needs `-f`, which is the package-postrm verb); the removal does not survive upgrades (postinst reruns `update-rc.d foo defaults` and reinstalls factory links); and deleting the S links alone breaks the stop path's coherence — the supported S→K rename keeps shutdown working and is exactly reversible with `enable`.

### Q: What does `service foo restart` do on a systemd machine?

It runs the *unit*, not the script: service(8) prefers a systemd unit with the same name over the `/etc/init.d` script, so the call maps to systemctl's restart for `foo.service`, and `start/stop/status/reload` pass through to systemctl. If no native unit exists, the SysV script is executed directly in a sanitized environment. The subtle part: init scripts that have been "converted" by systemd's SysV generator still work through both paths, which is why the same command succeeds across the migration boundary — and why `service --status-all` only reports on sysvinit jobs even on a systemd host.

### Q: How do you preview what update-rc.d will change, given that bookworm's version has no --dry-run?

Containment instead of a flag: copy the script into a throwaway chroot or VM snapshot, run the exact `update-rc.d` invocation there, and inspect `/etc/rc*.d`. For the ordering side (which the links only hint at), insserv still has real dry modes: `insserv -n` parses and resolves every header without touching symlinks or the `.depend` files, and `insserv -s` prints the runlevel/sequence placement without updating. Between a snapshot and those two flags, no header or link change needs to be discovered on a production boot.

### Q: A maintainer script's postinst logs "invoke-rc.d: denied" but the package install succeeds. Why is that correct behavior?

Because invoke-rc.d's contract with maintainer scripts is that policy vetoes are non-fatal: a denied action returns exit 0 to the caller (unless `--disclose-deny` is requested), so the package completes installation while the service simply is not started. The system administrator's policy (or the container's deny-all gate) outranks the package's desire to start its daemon; the rc links are still installed, so the service appears at the next boot in its configured runlevels. Debugging the *non-start* means inspecting the policy layer and runlevel state — the exit code was designed not to tell you, which is why `--disclose-deny` and `--query` exist.

## References

- [update-rc.d(8) — Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/update-rc.d.8.en.html) — link grammar, the never-overwrite rule, disable/enable arithmetic, and the remove-on-upgrade warning.
- [invoke-rc.d(8) — Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/invoke-rc.d.8.en.html) — the policy layer, full status-code table, and query/disclose-deny semantics.
- [service(8) — Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/service.8.en.html) — sanitized environment, unit precedence, and `--status-all` behavior.
- [insserv(8) — Debian bookworm](https://manpages.debian.org/bookworm/insserv/insserv.8.en.html) — dependency engine options, overrides, and the `.depend.*` artifacts.
- [startpar(1) — Debian bookworm](https://manpages.debian.org/bookworm/startpar/startpar.1.en.html) — the `-M boot|start|stop` make-style batch execution over the `.depend.*` files.
- [telinit(8) — sysvinit-core, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/telinit.8.en.html) — the PID 1 control layer: changing runlevels, re-reading inittab.
- [shutdown(8) — sysvinit-core, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/shutdown.8.en.html) — scheduling halts and reboots, which terminate in a runlevel change into 0 or 6.
- [runlevel(8) — sysvinit-core, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/runlevel.8.en.html) — reading the current and previous runlevel from utmp.
- [last(1) — util-linux, Debian bookworm](https://manpages.debian.org/bookworm/util-linux/last.1.en.html) — `last -x` shutdown and runlevel-change history.

## Cross-References

- [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) — the filesystem artifacts every tool on this page creates or consumes.
- [/etc/init.d Scripts — Conventions and Patterns](./init-scripts.md) — the scripts these tools execute and the action contract they rely on.
- [Parallel Booting and startpar](./parallel-booting.md) — the execution engine behind the `.depend.*` ordering.
- [Custom Init Scripts](./custom-init-scripts.md) — writing your own service the tooling can manage cleanly.
- [systemd — systemctl and the CLI](../systemd/systemctl-cli.md) — the modern command surface, including its SysV compatibility paths.
- [Init Systems Hub](../README.md) — section map and reading order for all init-system families.
- [Init System Comparison](../comparison.md) — tooling stacks across init families, mapped feature to feature.
