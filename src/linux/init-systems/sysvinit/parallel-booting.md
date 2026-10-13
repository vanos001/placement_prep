# Parallel and Dependency-Based Boot (insserv, startpar)

## Overview

The classic SysV boot walks `/etc/rc?.d/S??*` in strict ascending sequence-number order and runs each script to completion before starting the next. That design is simple and robust, but it pays the full sum of every script's runtime, and the sequence numbers themselves carry no dependency information — they are a total order imposed by hand. Two cooperating tools fix this without abandoning the init.d model: `insserv(8)` compiles the LSB headers of every installed script into a dependency graph, and `startpar(1)` executes the scripts in that graph concurrently instead of one at a time.

The two tools are complementary, not alternatives. insserv supplies *correctness*: a minimal ordering that satisfies every declared `Required-Start` and `Should-Start` edge and nothing more. startpar supplies *throughput*: it runs whatever the graph proves independent at the same moment, multiplexing their console output so the screen stays readable. Dependency information without parallelism merely reorders the serial walk; parallelism without dependency information is a race generator. Together they turn boot time from "the sum of all scripts" into "the length of the critical path through the dependency graph."

This page covers both tools in depth — the graph files insserv writes, the batch execution model startpar implements, how to author headers that are safe under parallelism, the failure modes parallel boot introduces, and how to measure the result. It also frames the design honestly: this is a compile-once, batch-execute architecture, and comparing it with systemd's continuous graph and OpenRC's `rc_parallel` is the fastest way to understand what each generation of init systems actually changed.

## Why the Serial Walk Was Slow

Under serial boot, `/etc/init.d/rc` reads the runlevel directory, sorts the `S??` symlinks lexically, and invokes each target script with the argument `start` in the foreground. There is no concurrency of any kind: rc waits for each script to exit before the next runs, and each script's duration — disk waits, daemon startup sleeps, network timeouts — is added to boot time:

```console
serial:    [network 3.2s][rsyslog 0.8s][apache 2.4s][cron 0.1s]   total = sum
parallel:  [network 3.2s]
           [rsyslog 0.8s]                                          total = critical path
           [apache 2.4s]
           [cron 0.1s]
```

### The rc walk, mechanically

Two details of the walk matter for everything that follows. First, the ordering input is purely lexical: rc parses no metadata and knows nothing about any script — it sees filenames like `S20apache2` and runs them in sort order, full stop. Second, the cost centers on *process exits*: an init script that sleeps two seconds "for the network" adds exactly two seconds to every boot, because nothing downstream can begin until the process is gone. rc does check exit status and continues on failure — boot does not abort because one script failed — but it cannot reorder or skip ahead, so the sequence number is a hard barrier between neighbors.

One operational footnote: this is also the phase that starts `bootlogd` so the console gets recorded to `/var/log/boot` (which is what makes the measurement section below possible). It does not change the arithmetic: one script at a time, and the total is the sum.

The deeper problem is semantic. A sequence number is an *ordering*, not a *dependency*: `S20apache2` claims apache must come after everything numbered below 20 and before everything above, including services it has no relationship with. The numbers were assigned by packagers guessing at a total order for the whole system, so they drift: scripts get renumbered across releases, local admins wedge their own scripts into gaps, and the artificial constraints accumulate. Inserting one service "between" two others means choosing a fresh number that nobody else will also choose — a classic manual-global-ordering problem.

What rc cannot know from `S20` alone is what *may* run concurrently. That is exactly the information the LSB header encodes (`Provides`, `Required-Start`, `Should-Start` — field by field in [lsb-headers.md](./lsb-headers.md)), and exactly the information insserv was written to exploit.

### How the numbers drifted in practice

The drift was not hypothetical. Numbers were chosen by individual package maintainers — network at 10, syslog at 11 or 12, display managers around 20, mail servers wherever a maintainer guessed — and local admins wedged their own scripts into the gaps with numbers like `S91` that quietly fought the next package's `S90`. Renumbering a script across a release changed boot semantics on every machine that installed it, and two packages could claim overlapping ranges with no tool able to notice, because nothing about a number is verifiable. The result, on a mature system, was an ordering that was simultaneously too strict (hundreds of artificial pairwise constraints) and unverifiable (no machine-readable statement of what actually must precede what) — exactly the pathology a dependency graph fixes.

## The Two Accelerators and How They Interlock

The division of labor is worth stating precisely because interview questions probe the split:

- **insserv — dependency sequencing.** Reads every init script's LSB header, resolves virtual facilities through `/etc/insserv.conf`, builds a directed dependency graph, and writes the compiled order into `/etc/init.d/.depend.boot`, `.depend.start`, and `.depend.stop`. It changes *what order is correct*, not how scripts are executed.
- **startpar — parallel execution.** A batch executor from the same sysvinit suite (see the project tree at [git.savannah.nongnu.org/cgit/sysvinit.git/](https://git.savannah.nongnu.org/cgit/sysvinit.git/)). Given a set of scripts and their dependency rules, it runs independent scripts concurrently like `make` runs independent targets, and multiplexes their stdout/stderr onto the console.

The pipeline, end to end:

```console
   LSB headers in /etc/init.d/*          /etc/insserv.conf (facility map)
          |                                        |
          +------------- insserv ------------------+
                            |
     /etc/init.d/.depend.boot / .depend.start / .depend.stop
                            |
        /etc/init.d/rc  (dependency mode reads the graph)
                            |
                 startpar  (batch executor)
                            |
          independent scripts run concurrently
```

Once dependency mode is active, the sequence numbers in the symlink names stop carrying ordering information. The *presence* of an `S??myapp` link still decides **whether** the script runs in that runlevel (the symlink walk of [rc-symlinks.md](./rc-symlinks.md) selects the set); the compiled graph decides **when**. Numbers become metadata for humans, not instructions for rc.

## insserv: Compiling Headers into a Boot Graph

insserv is the compile step of dependency-based booting: it takes the declarations every script carries in its header plus the system's facility map, and produces the ordered graph the rest of the boot machinery executes. Its inputs, its cycle rules, its output files, and its regeneration workflow each matter operationally.

### Inputs: LSB headers and the facility map

insserv scans `/etc/init.d/*` for `### BEGIN INIT INFO` blocks and extracts, per script, what it provides and what it requires. Its second input is `/etc/insserv.conf`, the facility map that anchors the virtual facilities: `$local_fs` maps to the local-filesystem mount scripts, `$remote_fs` to `$local_fs` plus the NFS mount/umount scripts, `$network` to the network setup script, and so on. A `Required-Start: $remote_fs` in your header therefore becomes an edge to concrete mount scripts at generation time. Scripts that declare no `Provides` implicitly provide their own basename; scripts providing a facility become targets any requirer can depend on.

### The graph, the sort, and cycle handling

insserv builds a directed graph: an edge from A to B means "B must complete before A starts". `Required-Start` edges are hard constraints; `Should-Start` edges are advisory. The output order is a topological sort — every script appears after all its required providers. Two properties matter:

- A cycle among hard (`Required-Start`) edges makes regeneration fail with an error, because no topological order exists. This is a boot-blocker you find at package-install time, which is the right place to find it.
- `Should-Start` edges exist precisely so that cycles can be broken: where a should-edge would close a cycle, it is dropped rather than fatal. That is the designed use of the Required/Should split — hard facts go in `Required-Start`, preferences that must never deadlock the boot go in `Should-Start`.

The resulting order is *minimal*: two scripts unrelated by the graph get no relative ordering imposed, which is exactly the freedom startpar exploits.

### Outputs: the .depend.* files

insserv writes three machine-generated files in `/etc/init.d/`:

| File | Contents | Consumed for |
|---|---|---|
| `.depend.boot` | ordering of `rcS.d` boot scripts | the single-user-to-multiuser transition |
| `.depend.start` | ordering of start scripts per runlevel | entering runlevels 2–5 |
| `.depend.stop` | stop ordering (edges reversed: a service stops before its dependents) | leaving runlevels, shutdown |

Each file is a list of make-rule-like lines: target script on the left, its resolved prerequisites on the right. An abridged, representative `.depend.start`:

```text
### Dependencies:
#
# Machine-generated by insserv from the LSB headers - do not edit.
apache2: $local_fs $remote_fs $network $syslog $time
cron: $local_fs $remote_fs $syslog
ntp: $local_fs $remote_fs $network $syslog $named
rsyslog: $local_fs $remote_fs
sshd: $local_fs $remote_fs $network $syslog $time ntp
```

Real files are far longer and fully generated; the point to retain is the shape — `target: prerequisites` — because that is the shape startpar's makefile mode consumes, and the reason a hand-edited line (or a hand-deleted file) silently changes boot behavior. The `$`-prefixed tokens are the virtual facilities, anchored by `/etc/insserv.conf`.

### The stop graph

`.depend.stop` reverses the arrows: a service must stop *before* the services that depend on it. The stop graph encodes the shutdown half of the same contract — rsyslog stops late so other services can still log their own shutdown, network teardown comes after the daemons that hold sockets, and filesystem umounts come last. `Default-Stop` K links feed this graph exactly as S links feed the start graph, and the same cycle rules apply. Shutdown pathologies — stalled reboots, "filesystem busy" at umount — are usually stop-graph problems: a service that never declared what must outlive it, or a stop script without a bounded `--retry` schedule (the mechanics are in [init-scripts.md](./init-scripts.md)).

### History: SUSE origins, Debian squeeze, RHEL static numbers

insserv originated in the SUSE distribution (written by Werner Fink) and was adopted by Debian, where dependency-based booting became the default with Debian 6.0 "squeeze" (2011) — a milestone worth remembering, because squeeze-era and later systems order their boot from compiled graphs, not from the numbers packagers typed. Red Hat never adopted insserv: RHEL 5/6 kept static sequence numbers assigned per package through `chkconfig` priorities (the `# chkconfig: 2345 20 80` comment line). On those systems the total order really is the hand-written one, which is why RHEL-era scripts carry carefully chosen numbers and Debian-era scripts do not.

### Regeneration and dry runs

The graph is a *build artifact*. Editing a header in `/etc/init.d/foo` changes nothing until the graph is regenerated: run `insserv` (or `insserv -n` for a dry run that reports what would change and any cycle errors without touching files). When dependency-based booting is enabled, `update-rc.d(8)` delegates to insserv under the hood, so package installs regenerate the graph automatically — the failure mode is manual header edits followed by no regeneration, leaving a stale `.depend.start` that quietly ignores your new dependency. Treat the three `.depend.*` files exactly like object files: owned by the build tool, regenerated on every source change, never edited.

The day-to-day workflow is deliberately small:

```console
$ insserv -n                       # dry run: report cycles and would-be changes
$ insserv                          # regenerate .depend.{boot,start,stop}
$ update-rc.d -n myapp defaults    # preview what registration would create
```

If the dry run reports a cycle, the fix belongs in the headers — usually a dependency that belongs in `Should-Start` rather than `Required-Start` — not in the generated files.

## startpar: Parallel Batch Execution

startpar is the execute step: it turns the compiled graph into concurrent work while keeping the console coherent. Three mechanisms matter — the scheduling model, output multiplexing, and the knobs that bound runaway batches.

### Batches and the makefile mode

Under dependency-based boot, `/etc/init.d/rc` does not fork each script itself. It reads the compiled graph and hands the batch to startpar in a makefile-style form; startpar then schedules scripts the way `make` schedules targets — a script may start as soon as its prerequisites have completed, and scripts whose dependencies are still running wait for the next opportunity. Execution therefore proceeds in *rounds* that follow the shape of the graph: depth-0 scripts run first, dependents start as each prerequisite finishes, and the boot completes when the deepest level drains. A slow script blocks only its own dependents, not the whole batch — unless it sits on the critical path (more on that under failure modes).

The shape of a batch, conceptually:

```console
round 0:   [mountkernfs.sh] [hostname.sh]        no prerequisites
round 1:   [mountall.sh]    [checkfs.sh]         need the round-0 scripts
round 2:   [rsyslog]        [dbus]               need $local_fs
round 3:   [apache2]  [sshd]  [cron]             need $network, $syslog
```

Mechanically it is not round-synchronized: startpar schedules like `make -j`, starting any script the moment its last prerequisite exits and throttling only at the `-p` cap. Rounds are the mental model; the wall clock is filled continuously as dependencies drain.

startpar also has a single-script mode (`-a script argument`) that runs one named script through the same output machinery; rc uses it for individual invocations that must not join a parallel batch, such as scripts flagged interactive.

### Output multiplexing and interactive scripts

Naive parallel boot garbles the console: ten scripts writing to the same terminal interleave mid-line. startpar solves this by collecting each child's stdout and stderr and forwarding it to the console in controlled units, so lines from different scripts arrive intact and roughly ordered. It also watches for scripts that need interactive input; combined with rc's handling of the `X-Interactive: true` header flag (crypto passphrase prompts being the canonical case), such scripts are kept out of parallel batches and run serially, where they can own the console. The tradeoff is deliberate: correctness of the prompt beats a fraction of a second of parallelism.

### Parallelism, timeouts, and flags

The flags that matter in practice (full list in [startpar(1)](https://manpages.debian.org/bookworm/startpar/startpar.1.en.html)):

| Flag | Behavior |
|---|---|
| `-p N` | cap on concurrently running scripts; small by default, conservative on purpose |
| `-t SEC` / `-T SEC` | timeouts that bound how long startpar waits on unresponsive scripts before treating them as hung/interactive, so one wedged script cannot stall the batch indefinitely |
| `-i RATE` | readahead rate for child output buffering (tuning output forwarding) |
| `-a SCRIPT ARG` | single-script mode for one script plus one action argument |
| `-v` | verbose reporting |

The historical pattern across releases was rc choosing a concurrency mode and invoking startpar accordingly; the `-p` cap exists because unbounded process spawns during boot are their own problem (disk and CPU saturation make everything slower — parallelism is not free).

### The CONCURRENCY variable's evolution

Debian's `/etc/init.d/rc` historically exposed a `CONCURRENCY` variable that switched execution strategy, and its accepted values moved across releases: `none` (the old serial default), `shell` (spawn same-sequence-number groups in background with no dependency knowledge — fast but racy), `startpar` (batch via startpar using sequence groups), and `makefile` (dependency batches built from insserv's `.depend.*` files, the mode dependency-based booting uses). Which values existed and which was the default varied by release (roughly etch through wheezy), and on current Debian the setting has effectively faded — update-rc.d assigns conservative `S01` numbers and the rc walk is sequential again unless dependency tooling is installed. The honest takeaway: read the `rc` script on the system in front of you rather than trusting any fixed list, and treat `CONCURRENCY=shell`-style anecdotes as history, not documentation.

## Authoring Headers for Parallel Safety

Headers are the source code of the boot graph, and parallel boot compiles them with far less forgiveness than the serial walk did. Three areas need deliberate care: which edges you declare, how your script behaves when it is reached twice, and what happens when it must own the console.

### Required versus Should placement

Every dependency you declare shapes two things: correctness and the critical path. The placement rules:

- **Hard facts in `Required-Start`.** If the script genuinely fails without a facility, it belongs in Required: an unsatisfied Required is an error; a satisfied one enforces order. Over-using Required serializes boot (you add edges to the critical path) and risks cycles with other packages' headers.
- **Preferences in `Should-Start`.** "Works better if X is up" — a resolver, time sync — goes here. Should-edges order when possible and are dropped when they would close a cycle, which is why they are the safe tool for cross-package niceties. Under-declaring (putting a real dependency in Should) produces the worst failure class: a race that usually works and occasionally corrupts.
- **`$local_fs` before filesystem writes.** A script that writes `/var/log/myapp.log` or touches anything outside the early-boot root filesystem must require `$local_fs` (or `$remote_fs`, which subsumes it) — otherwise it can run while `/var` is still a mountpoint-less directory on read-only root, and its writes vanish or block.
- **`$named` only when resolving.** Do not make DNS a hard dependency for scripts that merely bind ports; that puts the resolver on the critical path of every boot.

### Locking and idempotent starts

Under parallel execution, your script can be invoked concurrently (rc batch, an admin, `invoke-rc.d` from a postinst) and may be reached twice. Two guards make that safe:

```sh
# Serialize whole-script execution: two invocations would race on the pidfile.
exec 9>/run/lock/myapp.init.lock
flock -n 9 || { logger -t myapp "init script already active"; exit 0; }
```

and the idempotence rule: `start` on a running service must exit 0, not error, because in dependency mode "already started" is a normal outcome, not an anomaly. Likewise a `start` must tolerate having been run seconds earlier by another batch. The lock file (`flock(1)`, util-linux) plus an early already-running check closes both double-start and lost-update windows on the pidfile.

### X-Interactive and scripts that cannot parallelize

Add `X-Interactive: true` when the script prompts (passphrases, confirmations). rc then runs it serially outside the parallel batches. Use it sparingly: every interactive script is a straggler serialized against the rest of the boot, so the correct fix is usually removing the prompt (key files on tmpfs with proper permissions, unattended disk unlock via a keyfile) rather than marking it.

## Failure Modes Catalog

Parallel boot converts ordering bugs from "obvious boot failure" into "rare race", which makes the catalog worth memorizing:

| Failure | What happens | Prevention |
|---|---|---|
| Missing Required/Should dep | script starts before its dependency is ready — port conflicts, "config service not up", flaky boots that pass 9 times in 10 | declare the real dependency; Required if fatal, Should if cosmetic |
| Cycle from misplaced Should | regeneration errors (Required cycles) or edges silently dropped (Should cycles), order surprises after an edit | keep Should edges acyclic by construction; run `insserv -n` after header edits |
| Pidfile race | two invocations write/read the same pidfile; double daemon or kill of wrong PID | flock guard + idempotent start + one owner of process identity (see [init-scripts.md](./init-scripts.md)) |
| Port race | two daemons compete for one port; loser dies or wedges | dependency edge on the service that owns the port, or distinct ports |
| Garbled console output | unbuffered echo from N scripts interleaves mid-line | route messages through `log_daemon_msg`/startpar's multiplexer, not raw echo |
| One straggler dominates | everything waits on one 20-second script — parallel speedup collapses (Amdahl's law: the serial fraction bounds the gain) | measure (below), then fix the straggler or remove it from the critical path |
| Stale .depend graph | hand-edited header with no regeneration: new dependency ignored, boot reverts to old order | regenerate (`insserv -n`, then `insserv`); never edit the .depend files |
| Non-idempotent start | second invocation errors (exit 1/7), boot reports failure for a healthy service | exit 0 on already-running; test the double-start case |

The straggler row deserves emphasis because it is the honest limit of the whole approach: if one script takes 25 seconds and everything else is sub-second, dependency-based parallel boot gains you almost nothing. The fix is measurement, then dependency surgery.

## Measuring a Parallel Boot

`bootlogd(8)` records the boot console — including the `log_daemon_msg` output of every script — into `/var/log/boot` with per-line timestamps, which makes it the zero-dependency profiling tool for sysv boots:

```console
Sat Jul 12 08:41:03 2025: Starting enhanced syslogd: rsyslogd.
Sat Jul 12 08:41:03 2025: Starting system message bus: dbus.
Sat Jul 12 08:41:07 2025: Starting OpenBSD Secure Shell server: sshd.
Sat Jul 12 08:41:07 2025: Starting Apache httpd: apache2.
```

`bootlogd` itself is started near the beginning of the boot, attaches to the console devices, and copies everything to `/var/log/boot` until it is stopped at the end of the sequence — so the file is a complete transcript of the boot console, including your `log_daemon_msg` output, not a sample. Because the transcript is timestamped per line, it also survives comparison across reboots: collect two or three boots, diff the gaps, and the chronic stragglers identify themselves.

Diff consecutive timestamps to find gaps: the four-second hole before `sshd` is where the real time went. For a graphical view, bootchart2 renders process start/stop timelines across the boot (inline mention; see your distribution's packaging for the tool). After a migration to systemd, the same questions are answered by `systemd-analyze blame` and `systemd-analyze critical-chain` — the direct successors of this exercise, covered in [systemd — Boot Process](../systemd/boot-process.md).

## How systemd and OpenRC Do It Differently

The sysv accelerator pair is a *compile-once graph + batch runner*: insserv computes the order at package-management time, startpar drains it in rounds, and nothing is supervised afterwards. systemd generalizes both halves at runtime: one continuous dependency graph over all units, a transaction solver that starts every satisfiable unit as early as possible (not in rounds), and per-unit supervision with `Restart=` so the graph stays live after boot. Its socket activation removes an entire class of ordering edges — the socket is opened by PID 1 before any daemon exists, so "who came first" stops mattering (see [systemd — Socket Activation](../systemd/socket-activation.md)).

OpenRC keeps the per-script model and adds a switch: `rc_parallel="YES"` in `/etc/rc.conf` runs independent services concurrently, accepting interleaved output — conceptually the "shell mode" idea with a real dependency engine behind it. The comparison is covered from the architectural side in [OpenRC — Overview and Architecture](../openrc/overview-architecture.md). What all three share is the insight that sequence numbers are the wrong abstraction; where they differ is whether the graph is compiled once (sysv+insserv), evaluated per boot in batches (OpenRC), or evaluated continuously with supervision (systemd).

## Interview Questions

### Q: What problem does dependency-based boot solve that sequence numbers cannot?

Sequence numbers are a hand-assigned total order with no dependency semantics: every pair of scripts has an artificial relative order, even unrelated ones, and nothing encodes *why* an ordering exists. insserv replaces that with a graph compiled from declared metadata (`Provides`, `Required-Start`, `Should-Start`), computes a minimal topological order, and writes it into the `.depend.*` files rc and startpar consume. The win is twofold: correctness (order follows declared facts, and cycles surface as errors at regeneration time instead of as broken boots) and freedom (scripts unrelated by the graph have no imposed order, which is exactly the room startpar needs to run them concurrently). The S?? numbers survive only as inclusion flags — they decide whether a script participates in a runlevel, not when it runs.

### Q: Required-Start versus Should-Start — how do you decide where a dependency goes?

Required is for hard facts: the script fails or misbehaves without the facility, so the edge must be enforced and a cycle involving it must be an error. Should is for preferences: boot is better with the facility up, but the script tolerates its absence — the edge orders when possible and is dropped if it would close a cycle, which is precisely the property that keeps soft cross-package dependencies from deadlocking boot regeneration. The two failure directions: over-Required inflates the critical path and provokes cycle errors between packages; under-Required (a real dependency hidden in Should) produces the classic racy boot that works nine times out of ten. Concrete anchors: filesystem writes outside early root require `$local_fs`/`$remote_fs` in Required; DNS or time sync for a script that merely binds a port belongs in Should.

### Q: How does startpar keep parallel boot output readable, and how are interactive scripts handled?

startpar buffers each child's stdout/stderr and forwards it to the console in controlled units, so lines from concurrent scripts arrive intact instead of interleaving mid-line — the multiplexing is a first-class feature, not an afterthought. Interactive scripts are handled at two levels: startpar detects unresponsive/prompting children (bounded by its timeout flags), and rc keeps scripts marked `X-Interactive: true` in their LSB headers out of parallel batches entirely, running them serially so they own the console. The cost of an interactive script is serialization against the boot's critical path, which is why the good fix for passphrase prompts is eliminating the prompt (keyfiles), not flagging it.

### Q: You enabled parallel boot and boot time barely moved. What do you measure and why?

Boot time under parallelism is the critical path through the dependency graph, and Amdahl's law caps the gain: if 20% of the boot is inherently serial (one straggler, a chain of hard edges), no amount of `-p` helps. Measure with `bootlogd`'s timestamped `/var/log/boot`: diff consecutive line timestamps to find where the wall-clock time goes — a multi-second gap between two "Starting ..." lines is the straggler. Then fix the cause: a sleeping script (`sleep` as a substitute for readiness polling), a hard Required edge that should be Should, an interactive prompt, or a service that should be dependency-ordered rather than numbered. The systemd-era equivalents of the same exercise are `systemd-analyze blame` and `critical-chain`.

### Q: In dependency-based boot mode, what do the S?? symlink numbers still control, and what do they no longer control?

They still control *inclusion*: the symlink's presence in `/etc/rc2.d` says the script participates in runlevel 2, exactly as in the serial model. They no longer control *ordering*: once rc runs in dependency mode, the execution order comes from the compiled graph in `/etc/init.d/.depend.start` (and siblings), consumed directly by rc or handed to startpar. Corollary interview trap: renumbering symlinks under dependency boot changes nothing, and hand-editing an LSB header without regenerating the graph also changes nothing — the graph is a build artifact that must be rebuilt (`insserv -n` to preview, `insserv` to apply) when headers change.

### Q: Name three race conditions parallel boot introduces that serial boot cannot, and their fixes.

First, pidfile races: two concurrent invocations of the same script double-start the daemon or one kills a recycled PID — fixed with a flock guard on the script, idempotent `start` (exit 0 when running), and a single owner of process identity. Second, port races: two services compete for one port because neither declared the other — fixed by a dependency edge to the port owner or distinct ports. Third, stale-state races from a non-idempotent script being reached twice (once by the batch, once by `invoke-rc.d` from a postinst) — fixed by treating "already started/stopped" as success (exit 0), per the LSB no-op contract. The common thread: parallelism removes the accidental serialization that used to hide these bugs, so the script's own invariants (identity, idempotence, locking) must carry the weight.

## References

- [insserv(8) — insserv man page, Debian bookworm](https://manpages.debian.org/bookworm/insserv/insserv.8.en.html) — the graph compiler: header scanning, facility resolution, `.depend.*` generation, dry-run flags.
- [startpar(1) — startpar man page, Debian bookworm](https://manpages.debian.org/bookworm/startpar/startpar.1.en.html) — the batch executor: makefile mode, `-p` parallelism, timeouts, single-script mode.
- [update-rc.d(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/update-rc.d.8.en.html) — registration front end; documents delegation to insserv under dependency-based booting.
- [init-d-script(5) — sysvinit-utils man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-utils/init-d-script.5.en.html) — the declarative script style whose headers feed the same graph.
- [bootlogd(8) — bootlogd man page, Debian bookworm](https://manpages.debian.org/bookworm/bootlogd/bootlogd.8.en.html) — timestamped boot console recording to `/var/log/boot`; the baseline boot profiler.
- [LSB Core — Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — normative header fields and the action/exit-code contract the graph is built from.
- [Debian Wiki — LSBInitScripts](https://wiki.debian.org/LSBInitScripts) — Debian's header conventions, including the `X-Interactive` extension and facility usage notes.
- [sysvinit source repository (Savannah)](https://git.savannah.nongnu.org/cgit/sysvinit.git/) — hosts `rc`, `startpar`, and the rest of the suite discussed here.

## Cross-References

- [LSB Init Script Headers and Dependency Metadata](./lsb-headers.md) — the `### BEGIN INIT INFO` fields that become graph edges.
- [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) — how symlinks select the script set that dependency mode then orders.
- [/etc/init.d Scripts — Conventions and Patterns](./init-scripts.md) — the script contract (idempotence, exit codes, s-s-d) that parallel boot leans on.
- [Boot Sequence — from BIOS to Login](./boot-sequence.md) — where the rc phases sit in the overall boot timeline.
- [systemd — Boot Process](../systemd/boot-process.md) — the continuous-graph successor and its `systemd-analyze` measurement tools.
- [systemd — Socket Activation](../systemd/socket-activation.md) — how socket ownership removes ordering edges entirely.
- [OpenRC — Overview and Architecture](../openrc/overview-architecture.md) — the per-script dependency engine and its `rc_parallel` mode.
- [Init Systems Hub](../README.md) — section map and reading order.
- [Init System Comparison](../comparison.md) — feature matrix across sysvinit, systemd, OpenRC, runit, and dinit.
