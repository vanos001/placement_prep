# PID 1 and Entrypoints: Signals and Exit Codes Inside a Container

> Covers CT-001 (why PID 1 is special), CT-002 (shell entrypoints and the signal-forwarding problem), CT-009 (init-in-container: tini/docker-init), CT-010 (nested processes and transformed/lost exit statuses).

## Introduction

Every container gets its own PID namespace, and the first process in that namespace is PID 1 — whether or not it is prepared for the job. The kernel, the shell that many Dockerfiles install as PID 1, and init programs like `tini` treat this position very differently, and the differences are exactly what turns "we sent SIGTERM" into "the container ignored us" or "the exit code was 143 instead of 3".

The stakes are easy to state: the container's exit code **is** PID 1's wait status, and the container's lifetime **is** PID 1's lifetime. Everything else — supervisors, wrappers, forwarding inits — exists to make those two facts harmless.

This chapter explains the kernel rules, the classic entrypoint mistakes, the standard fixes, and the ways exit statuses get transformed or lost when processes are nested inside wrappers.

## The kernel rules at a glance

| Rule | Source | Effect you can observe |
|------|--------|------------------------|
| First process of a PID namespace is its "init" (PID 1) and becomes the parent of all orphans in the namespace | `pid_namespaces(7)` | Zombie reaping is PID 1's job; orphans reparent to it |
| Namespace members can only signal PID 1 with signals it has handlers for (even when privileged) | `pid_namespaces(7)` | A handler-less PID 1 shrugs off SIGTERM — the famous "docker stop does nothing" |
| SIGKILL/SIGSTOP are forcibly deliverable **from an ancestor namespace** | `pid_namespaces(7)` | The host runtime can always destroy the container |
| Death of the namespace init SIGKILLs every remaining process in the namespace | `pid_namespaces(7)` | Container lifetime == PID 1 lifetime |
| SIGKILL/SIGSTOP cannot be caught, blocked, or ignored | `signal(7)` | No userland defense exists against them |
| Zombies hold kernel process-table slots until waited for | `wait(2)` | Un-reaped zombies eventually starve the container of PIDs |
| Standard signals do not queue | `signal(7)` | A burst of TERMs coalesces — a blocked PID 1 sees one, not many |
| Orphans go to init, or to the nearest **subreaper** (`prctl(PR_SET_CHILD_SUBREAPER)`) | `wait(2)` | Host shims and `tini -s` can intercept orphans on their side |

One more rule from `signal(7)` matters for every entrypoint chain: *"A child created via fork(2) inherits a copy of its parent's signal dispositions. During an execve(2), the dispositions of handled signals are reset to the default; the dispositions of ignored signals are left unchanged."* Three practical consequences:

- A wrapper that installs handlers and then `exec`s the real server loses them (handled → default), which is usually what you want.
- An ignored signal (e.g., `nohup`-style SIG_IGN for SIGHUP) **survives** `exec` — a daemon started from such a shell inherits the ignore and will not react to SIGHUP reloads.
- Signal *mask* inheritance follows the same fork/exec story and is why launchers that block signals around startup can silently neuter the first TERM.

## Why PID 1 is not a normal process (CT-001)

When a new PID namespace is created (which is what every container runtime does), the first process in it gets PID 1 and inherits a set of special rules. The authoritative statement is in `pid_namespaces(7)` ([man7.org](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)):

> "The first process created in a new namespace ... has the PID 1, and is the 'init' process for the namespace. This process becomes the parent of any child processes that are orphaned because a process that resides in this PID namespace terminated."

Two consequences dominate container behavior:

1. **Signal delivery is restricted.** Per `pid_namespaces(7)`: *"Only signals for which the 'init' process has established a signal handler can be sent to the 'init' process by other members of the PID namespace. This restriction applies even to privileged processes."* In other words, if your PID 1 has no SIGTERM handler, a SIGTERM sent from inside the namespace is silently dropped. The exceptions are SIGKILL and SIGSTOP, and even those are *forcibly delivered only from an ancestor PID namespace* — which is precisely how the runtime on the host can always kill the container.

2. **Death of PID 1 kills the namespace.** From the same man page: *"If the 'init' process of a PID namespace terminates, the kernel terminates all of the processes in the namespace via a SIGKILL signal."* A container therefore lives exactly as long as its PID 1, and the runtime's view of "the container's exit status" is *the wait status of PID 1 and nothing else*.

A note on sourcing: the frequently repeated claim that "default dispositions for signals PID 1 has no handler for cannot be changed" is implemented in the kernel's signal-delivery path (`kernel/signal.c`, `get_signal()`, commented there as *"Global init gets no signals it doesn't want"*); it is **not** spelled out in `signal(7)`. The man-pages statement you can cite is the PID-namespace rule quoted above, which has the same practical effect for containerized processes: a default-action SIGTERM sent from within the namespace does nothing to a PID 1 that never registered a handler.

For the two signals that always work, `signal(7)` is explicit: *"The signals SIGKILL and SIGSTOP cannot be caught, blocked, or ignored"* ([man7.org](https://man7.org/linux/man-pages/man7/signal.7.html)) — and the PID-namespace rules add that, for the namespace init, they are deliverable *from ancestor namespaces* (the host side).

### Zombie reaping is PID 1's job

`wait(2)`'s NOTES ([man7.org](https://man7.org/linux/man-pages/man2/wait.2.html)) explain the second obligation:

> "A child that terminates, but has not been waited for becomes a 'zombie'. The kernel maintains a minimal set of information about the zombie process (PID, termination status, resource usage information) ... if a parent process terminates, then its 'zombie' children (if any) are adopted by init(1) (or by the nearest 'subreaper' process ...) ... init(1) automatically performs a wait to remove the zombies."

Inside a container there is no systemd to do this: PID 1 **is** the init, so every orphan — backgrounded jobs, double-forked daemons, crash leftovers — is reparented to it. If PID 1 never calls `wait()`, zombies accumulate in the container's process table. A traditional init or `tini` performs this reaping loop continuously ([tini README](https://github.com/krallin/tini)); a plain `nginx` master does not, which is why long-lived containers with careless entrypoints slowly fill their PID limit with `<defunct>` entries. (Diagnosis and fixes: [Troubleshooting Scenarios](troubleshooting-scenarios.md).)

Two kernel escape hatches matter here:

- Setting the SIGCHLD disposition to `SIG_IGN` (or `SA_NOCLDWAIT`) makes children auto-reap instead of becoming zombies — but note the POSIX subtlety `wait(2)` documents: the *default* disposition of SIGCHLD ("ignore") and an *explicit* `SIG_IGN` behave differently.
- `prctl(PR_SET_CHILD_SUBREAPER)` turns any process into a "nearest subreaper" that collects orphans in place of PID 1; this is what the containerd-shim uses on the host side (see below), and what `tini` offers via its subreaper mode.

## Shell as PID 1: the classic mistake (CT-002)

Dockerfile `CMD`/`ENTRYPOINT` come in two forms ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/)):

| Form | Example | What actually runs as PID 1 |
|------|---------|------------------------------|
| Exec form | `CMD ["myapp", "--port", "8080"]` | `myapp` itself |
| Shell form | `CMD myapp --port 8080` | `/bin/sh -c "myapp --port 8080"` |

The shell form is convenient (variable substitution, pipes, `&&`) but structurally wrong for PID 1. Watch the process table of a shell-form image — this is the example output printed in the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) itself, from `docker exec -it test ps aux`:

```text
USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
root 1 0.1 0.0 4448 692 ? Ss+ 00:42 0:00 /bin/sh /run.sh 123 cmd cmd2
root 19 0.0 0.2 71304 4440 ? Ss 00:42 0:00 /usr/sbin/apache2 -k start
```

PID 1 is `/bin/sh`, and Apache is a child — exactly the layout that blocks signals. The same page then documents the consequence verbatim in the ENTRYPOINT section:

> "The shell form of ENTRYPOINT ... starts your ENTRYPOINT as a subcommand of `/bin/sh -c`, which does not pass signals. This means that the executable will not be the container's PID 1, and will not receive Unix signals. In this case, your executable doesn't receive a SIGTERM from `docker stop <container>`."

Why doesn't the shell forward? Because `sh` runs the command **synchronously and has no forwarding logic**: it simply `wait()`s for the child. When SIGTERM arrives at PID 1 (`sh`), either the shell has no handler for it (then, as PID 1, the default action is suppressed per the rules above) or the shell's own behavior handles it without ever notifying the child. The child only learns something happened when the shell eventually exits — typically when the grace period expires and SIGKILL from the host kills everything at once. The observable symptom: `docker stop` / pod deletion always takes *exactly* the full grace period, and the app logs show no shutdown sequence.

The same warning is repeated on the [`docker kill` reference](https://docs.docker.com/reference/cli/docker/container/kill/): *"ENTRYPOINT and CMD in the shell form run as a child process of `/bin/sh -c`, which does not pass signals."* This is documented behavior, not a quirk of one shell.

## The standard fixes

### 1. Use exec form and handle signals yourself

`CMD ["myapp"]` makes your binary PID 1 directly. Then the PID-1 signal rules apply *to your program*: any signal you want to survive must have a handler installed, and any signal with the default disposition is dropped (SIGTERM included, when sent from inside the namespace). Applications written as proper daemons (nginx, PostgreSQL) already install handlers and work fine this way.

### 2. `exec` in wrapper scripts

When a script must do setup work (env, chown, templating) before starting the app, end the script with `exec`:

```sh
#!/bin/sh
set -e
./setup-config.sh
exec myapp --port 8080    # replaces the shell; myapp becomes PID 1
```

Without `exec`, `myapp` is a child of the shell and the shell (now PID 1) again blocks signals. With `exec`, the shell process image is replaced and there is exactly one process. Docker's own documentation shows this pattern using `exec` (and `gosu` for user switching) in the starter-script example of the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/).

### 3. Wrapper that forwards: `trap` + `wait`

If you genuinely need two processes (or cleanup after the child dies), the documented Docker example uses a trap ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/), ENTRYPOINT "starter script" example):

```sh
#!/bin/sh
trap 'echo TRAPed signal' HUP INT QUIT TERM
/usr/sbin/apachectl start        # service in background
read                             # keep script in foreground
/usr/sbin/apachectl stop         # cleanup after SIGTERM arrives
echo "exited $0"
```

In production, forward the signal and wait for the child so the *child's* exit status is what PID 1 reports:

```sh
#!/bin/sh
trap 'kill -TERM "$child" 2>/dev/null' TERM INT
myapp & child=$!
wait "$child"
exit $?
```

Two classic pitfalls with this pattern:

- After a trap fires, POSIX shells re-run `wait`; in bash, a trapped `wait` returns with status >128 and the trap action runs, so a loop is the robust form:

  ```sh
  trap 'kill -TERM "$child"' TERM INT
  myapp & child=$!
  while ! wait "$child"; do :; done   # re-enter wait after every trap
  exit $?
  ```
- The script above reports the child's status (good), but a sloppier variant that `exit`s from the trap immediately would report the wrapper's own status instead (see the lost-status table below).
- Signals delivered *while the trap handler runs* queue (bash defers them until the handler returns); long cleanup handlers therefore stretch shutdown by exactly that much — inside Kubernetes that time is charged to `terminationGracePeriodSeconds`.

### 4. Init-in-container: tini, docker-init, dumb-init (CT-009)

A tiny init program as PID 1 gives you both missing pieces — signal forwarding and zombie reaping — without per-app code. The [tini README](https://github.com/krallin/tini) is explicit about the two jobs:

> "All Tini does is spawn a single child (Tini is meant to be run in a container), and wait for it to exit all the while reaping zombies and performing signal forwarding."

> "It ensures that the *default signal handlers* work for the software you run in your Docker image. For example, with Tini, SIGTERM properly terminates your process even if you didn't explicitly install a signal handler for it."

Docker ships this as a built-in: the [`docker run` reference](https://docs.docker.com/reference/cli/docker/container/run/) documents `--init` as *"Run an init inside the container that forwards signals and reaps processes"*, and explains that *"The default init process used is the first `docker-init` executable found in the system path of the Docker daemon process. This docker-init binary, included in the default installation, is backed by tini."* Kubernetes has no `--init` equivalent — the pod spec contains no init-forwarder knob — so the choice is baked into the image's ENTRYPOINT, or made by using a purpose-built image. Either way, the kubelet still sends TERM to whatever PID 1 the image provides (see [Kubernetes](kubernetes.md)).

Facts about tini worth knowing from its README ([tini](https://github.com/krallin/tini)):

- **Exit-code reuse:** "Tini will reuse the child's exit code when exiting" — so the container exit code equals the child's code, keeping `128+N` and app codes intact.
- **Remapping:** the `-e` flag can map a chosen exit code to 0 (the README's example remaps the 143 a SIGTERM produces, which the README notes can be awkward for Java apps).
- **Subreaper mode:** "By default, Tini needs to run as PID 1 so that it can reap zombies ... If for some reason, you cannot run Tini as PID 1, you should register Tini as a process subreaper instead (only in Linux >= 3.4)" via `-s` or `TINI_SUBREAPER`; "Tini will issue a warning if it detects that it isn't running as PID 1 and isn't registered as a subreaper" — a useful build-time signal that your entrypoint wiring is wrong.
- **Scope:** tini forwards signals to its single child; it does not broadcast to every process in the container. Multi-process containers still need their own supervision story.

`dumb-init` (by Yelp) is a similar, widely used alternative that runs as PID 1 and forwards signals to its child process group; treat its exact defaults as documented in its own repository.

### Who reaps in orchestrator stacks?

In a Kubernetes/Docker stack there are two "parents" and they reap different things:

- **Inside the PID namespace:** orphans reparent to the container's PID 1 (see `pid_namespaces(7)` above). No host-side component can wait() for them — they are not visible as children outside the namespace. Reaping stays PID 1's responsibility.
- **On the host:** the container init process's host-side parent is the runtime shim (e.g., `containerd-shim-runc-v2`, or conmon under CRI-O). The shim exists to outlive daemon restarts and to observe the container process: containerd's Runtime v2 contract requires every shim to publish a `TaskExitEventTopic` *"when a task exits expected or unexpected"*, and defines `TaskOOMEventTopic` *"if the shim collects Out of Memory events"* ([containerd runtime-v2 doc](https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md)). The exit event is what the daemon/kubelet turn into the status you query. The architecture of this layer is covered in [Runtime Internals](../../containers/runtime-internals.md) and [Docker Internals](../../containers/docker-internals.md).

Summarized: two reapers, two scopes.

| Orphan originates | Reparents to | Reaped by |
|-------------------|---------------|-----------|
| Any process inside the container (parent died) | Container's PID 1 (namespace rule) | Whatever PID 1 does — init program, reaping loop, or nothing |
| The container's init itself (it exited) | Namespace teardown: kernel SIGKILLs the rest | The host-side shim records the final wait status |
| Host-side children of the shim (rare, runtime internals) | The shim, if it is a subreaper | Shim's own reaping (runtime implementation) |

This is why "add tini" fixes in-container zombie growth, while "the shim will reap it" does not: the shim never sees the namespace-internal orphans as waitable children.

## Nested processes and lost statuses (CT-010)

The container exit code is **always the wait status of PID 1**, converted by the runtime (see [Docker](docker.md) for the 125/126/127 and 128+N conventions). Everything that happens below PID 1 is visible only if PID 1 propagates it. Common transformations:

| Scenario | What PID 1 does | What the runtime reports |
|----------|-----------------|--------------------------|
| Wrapper script, no `exec`, app runs foreground | shell waits for app, then exits with app's status | app's code (correct, but signals blocked while shell is PID 1) |
| Wrapper exits early (config error, `return` instead of `exec`) | shell exits with its own status | **wrapper's** code; app may still be running orphaned or never started |
| Shell form + app backgrounds (`myapp &`) | shell exits immediately with 0 | container exits 0 immediately; app is killed when the namespace dies with PID 1 |
| `myapp &` + `wait` | shell waits, exits with app's status | app's code — but still via the shell, with the PID-1 signal caveats |
| `nohup app &` / `disown` | SIGHUP disposition set to ignore for the child (and SIG_IGN survives later `execve`s) | child ignores hangup-style signals only; other signals unaffected; status still visible only if PID 1 waits for it |
| `setsid app` | app leaves the process group / new session | signals sent by the runtime target PID 1 only, never the daemon; container status is PID 1's status |
| Double-fork daemonizing app | daemon's parent exits; daemon reparents to PID 1 | PID 1 exits when it chooses — the daemon's later death is invisible to the container status |
| App killed by signal, PID 1 propagates | PID 1 exits with 128+N (shell convention) | container code 128+N; the kernel itself recorded a "killed by signal" wait status (see [Docker](docker.md)) |
| PID 1 killed by SIGKILL from host | namespace destroyed | kernel SIGKILLs all remaining processes (`pid_namespaces(7)`); container status = SIGKILL death (typically 137) |

The general law: **statuses are not inherited upward automatically; they exist only in the wait status of the direct child the runtime reaps.** Every intermediate process is an opportunity to replace the interesting status with its own. This is the container-layer twin of the shell-level rules in the exit-status chapter of this part.

One more kernel subtlety matters when wrappers delay handling: standard signals **do not queue**. From `signal(7)`: *"Standard signals do not queue. If multiple instances of a standard signal are generated while that signal is blocked, then only one instance of the signal is marked as pending (and the signal will be delivered just once when it is unblocked)."* In a container this means a PID 1 that blocks or delays SIGTERM while shutting down work cannot "catch up" on three TERMs sent in quick succession — it will see one. Grace-period logic that assumes one signal per shutdown tick miscounts for exactly this reason.

A worked example of status replacement — the app never ran, but the container reports a plausible-looking code:

```console
$ docker run --rm demo-wrap   # ENTRYPOINT ["/bin/sh","-c","./render-templates && exec myapp"]
# example output
render-templates: line 3: config.yaml: Permission denied
$ echo $?                     # wrapper's failure, not myapp's
1
```

The `1` is the *shell's* status for the failed `&&` chain. myapp's exit code would only have surfaced had the chain reached the `exec`. Distinguish this from the inverse failure mode — the wrapper exits 0 while the app is still running — which produces a container that ends before its work does (row 3 of the table above).

When status loss and zombie accumulation combine, the process table inside the container is the evidence:

```console
$ docker exec myapp ps aux
# example output
USER   PID  %CPU %MEM COMMAND
root     1  0.2  0.1  myapp
root    37  0.0  0.0  [loader] <defunct>     # orphan, reparented to PID 1
root    38  0.0  0.0  [worker] <defunct>     # nobody reaped it
```

Each `<defunct>` entry is a slot held in the kernel process table for a status nobody has read ([wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html)) — the counter-example to "the runtime will clean it up": the runtime reaps exactly one child, PID 1.

## Practical defaults

1. Prefer exec-form `ENTRYPOINT`/`CMD` ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/)).
2. If you need a wrapper: `exec` when possible; `trap`+forward+`wait` when not.
3. If the workload spawns children you cannot control (cron-like containers, shell-heavy images): run an init (`--init` on Docker; tini/dumb-init as entrypoint elsewhere).
4. Decide deliberately what PID 1's SIGTERM behavior should be — "nothing happens" is the documented default-action outcome, not a bug in the runtime.
5. Sanity-check the final image once: run it, `ps aux` inside, confirm PID 1 is the binary you intended and that `docker stop` returns in the time your app needs to drain — not in the full grace period.

## Related Topics

- [Docker](docker.md) — how the daemon turns the wait status into 125/126/127 and 128+N
- [Kubernetes](kubernetes.md) — where the kubelet sends TERM during pod termination, and what it records
- [Troubleshooting Scenarios](troubleshooting-scenarios.md) — zombie accumulation, silent SIGTERM, exit 137 diagnosis
- [Docker Internals](../../containers/docker-internals.md) — daemon/shim/runtime component roles
- [Runtime Internals](../../containers/runtime-internals.md) — runc and shim internals
- [Signals](../../sysprog/signals.md) — dispositions, handlers, and delivery rules
- [wait4 / waitid](../../syscalls/process/wait4.md) — the wait-status encoding this chapter summarizes

## References

- Linux man-pages project — `pid_namespaces(7)`: namespace init, orphan reparenting, signal restriction, namespace teardown. https://man7.org/linux/man-pages/man7/pid_namespaces.7.html (accessed October 2026)
- Linux man-pages project — `wait(2)`: zombie definition, process-table exhaustion, orphan adoption by init/subreaper. https://man7.org/linux/man-pages/man2/wait.2.html (accessed October 2026)
- Linux man-pages project — `signal(7)`: "SIGKILL and SIGSTOP cannot be caught, blocked, or ignored". https://man7.org/linux/man-pages/man7/signal.7.html (accessed October 2026)
- Linux kernel source — `kernel/signal.c`, `get_signal()`: "Global init gets no signals it doesn't want" (implementation detail of PID 1 default-action suppression). https://github.com/torvalds/linux/blob/master/kernel/signal.c (accessed October 2026)
- Docker Docs — Dockerfile reference: shell and exec form, ENTRYPOINT signal warning, `exec`/`gosu` and trap starter-script examples, STOPSIGNAL. https://docs.docker.com/reference/dockerfile/ (accessed October 2026)
- Docker Docs — `docker run` reference: `--init` flag ("forwards signals and reaps processes"), docker-init backed by tini. https://docs.docker.com/reference/cli/docker/container/run/ (accessed October 2026)
- krallin/tini README — zombie reaping as PID 1, subreaper mode (`-s`, `TINI_SUBREAPER`), exit-code reuse and `-e` remapping. https://github.com/krallin/tini (accessed October 2026)
- containerd — Runtime v2 (shim) contract: task exit/OOM event topics. https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md (accessed October 2026)
- Yelp dumb-init — alternative PID 1 signal forwarder. https://github.com/Yelp/dumb-init (named for completeness; behavior per its own README)
