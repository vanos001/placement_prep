# Docker: Exit Codes, Stop Signals, and OOM

> Covers CT-003 (stop flow: STOPSIGNAL, `docker stop`, `docker kill`), CT-004 (exit-code propagation and the 125/126/127/128+N conventions), CT-005 (OOM: `OOMKilled`, memory limits, and why 137 does not prove OOM).

## Introduction

Docker is the layer where kernel wait statuses become the numbers humans quote in incidents. The daemon and its runtime stack watch the container's PID 1, translate its wait status into an exit code, expose it through `docker run`'s return value, `docker ps`, and `docker inspect`, and enforce stop semantics with a two-phase signal flow. This chapter traces each translation step with the official documentation, and then handles the most misread code in container operations: 137.

## Where the numbers come from: the runtime stack

A quick orientation, because every convention below is produced by a specific component ([Docker Internals](../../containers/docker-internals.md) has the full picture):

1. `docker run` asks the daemon (dockerd); the daemon delegates to containerd; containerd starts a per-container **shim**; the shim invokes `runc`, which creates the container (PID namespace, cgroups) and starts PID 1, then exits.
2. The shim remains the container's host-side parent for the container's lifetime — it is the process that `wait()`s for PID 1 and observes its raw wait status.
3. The shim reports the outcome upstream: containerd's Runtime v2 contract requires a `TaskExitEventTopic` "when a task exits expected or unexpected" and a `TaskOOMEventTopic` "if the shim collects Out of Memory events" ([containerd runtime-v2](https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md)).
4. The daemon stores the result in the container state you query with `docker ps`/`docker inspect`, and returns it to `docker run`'s caller.

So: **the kernel produces a wait status; the shim converts and forwards it; the daemon labels it.** Every "surprising" exit code is one of those three steps doing something documented but unexpected.

## What `docker run` returns (CT-004)

The ["Run containers" reference](https://docs.docker.com/engine/containers/run/) (the page historically at `engine/reference/run`) defines the exit-status contract:

> "Any exit code other than 125, 126, and 127 represent the exit code of the provided container command."

So the normal case is faithful propagation of PID 1's exit status:

```console
$ docker run busybox /bin/sh -c 'exit 3'
$ echo $?
3
```

Three codes are reserved by the *Docker CLI/daemon* and never come from your process:

| Code | Meaning (per docs) | Example from the docs |
|------|--------------------|-----------------------|
| 125 | "the error is with Docker daemon itself" | `docker run --foo busybox` → `flag provided but not defined` |
| 126 | "the specified contained command can't be invoked" | `docker run busybox /etc` → `Container command '/etc' could not be invoked` |
| 127 | "the contained command can't be found" | `docker run busybox foo` → `Container command 'foo' not found or does not exist` |

These mirror the shell/POSIX convention for command-not-found (127) and not-executable (126) (see [POSIX XCU §2.8](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)), which makes triage intuitive: 126/127 from `docker run` mean the image/entrypoint is wrong before the app ever ran.

### Where 128+N comes from

When a container process is *killed by a signal* instead of exiting, there is no `exit()` status — the kernel records a signal-death wait status (the `WIFSIGNALED`/`WTERMSIG` encoding described in [wait4/waitid](../../syscalls/process/wait4.md)). Userspace cannot return signal numbers through `wait`'s exit-code slot directly, so a convention is used:

- POSIX requires shells to map a signal death to an exit status **greater than 128**, with the exact value implementation-defined ([POSIX.1-2024 XCU §2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)).
- `bash(1)` documents the concrete convention: *"The return value of a simple command is its exit status, or 128+n if the command is terminated by signal n"* ([bash reference manual](https://www.gnu.org/software/bash/manual/)).
- Container runtimes follow the same convention when they report a signal death as an exit code: **128 + signal number**. It is a *convention used by runtimes and shells*, not a kernel-produced number.

The Docker event log shows the translation happening in real time — the [`docker events` reference](https://docs.docker.com/reference/cli/docker/system/events/) example shows a SIGTERM stop:

```text
container kill 0fdb...ff37 (image=alpine:latest, name=test, signal=15)
container die  0fdb...ff37 (image=alpine:latest, name=test, exitCode=143)
```

`signal=15` (SIGTERM) → `exitCode=143` = 128+15. The same mapping produces 137 (SIGKILL, 128+9) and 139 (SIGSEGV, 128+11). For the corresponding signal table and disposition semantics, see [Signals](../../sysprog/signals.md); for how the shim observes the raw wait status, see [PID 1 and Entrypoints](pid1-signals.md).

Two adjacent CLI flags shape this signal story in attached workflows ([`docker run` reference](https://docs.docker.com/reference/cli/docker/container/run/)):

- `--sig-proxy` — "Proxy received signals to the process", **default `true`**: with an attached container, signals you send to the foreground `docker run` client are forwarded to the container process.
- `--stop-timeout` — "Timeout (in seconds) to stop a container" (API 1.25+): the per-container variant of the daemon-level 10 s default discussed below.

### Docker restart policies and exit codes

Exit codes also drive the daemon's own restart decisions ([`docker run` reference](https://docs.docker.com/reference/cli/docker/container/run/), "Restart policies (--restart)"):

| Policy | Documented behavior |
|--------|---------------------|
| `no` | "Don't automatically restart the container. (Default)" |
| `on-failure[:max-retries]` | "Restart the container if it exits due to an error, which manifests as a **non-zero exit code**"; optional retry cap; "only prompts a restart if the container exits with a failure" |
| `always` | "Always restart the container if it stops. If it's manually stopped, it's restarted only when Docker daemon restarts or the container itself is manually restarted." |
| `unless-stopped` | "Similar to always, except that when the container is stopped (manually or otherwise), it isn't restarted even after Docker daemon restarts." |

Note the exit-code coupling: under `on-failure`, a SIGTERM stop (143) and a SIGKILL (137) both *restart* the container (non-zero), while a clean exit 0 does not — the same 0-vs-nonzero split Kubernetes encodes in `restartPolicy: OnFailure` (see [Kubernetes](kubernetes.md)). The documented retry cap:

```console
$ docker run --restart on-failure:5 myapp   # up to 5 restarts, non-zero exits only
```

When a restart policy is active, the container's status view shows the policy taking effect; combined with `docker events`, restart loops leave the same `die` → `start` rhythm that Kubernetes renders as a crash loop.

## Stopping containers (CT-003)

### STOPSIGNAL and --stop-signal

The image can declare its preferred stop signal ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/)):

> "The STOPSIGNAL instruction sets the system call signal that will be sent to the container to exit. This signal can be a signal name in the format SIG<NAME>, for instance SIGKILL, or an unsigned number ... The default is SIGTERM if not defined."

The docs add two boundary conditions worth quoting: STOPSIGNAL "applies to the signal sent by `docker stop` (and by the Docker daemon when stopping a container)" and does *not* affect Ctrl+C-style SIGINT; and the image default can be overridden per container with `--stop-signal` on `docker run`/`docker create`.

### docker stop: SIGTERM, then SIGKILL

The [`docker stop` reference](https://docs.docker.com/reference/cli/docker/container/stop/) defines the two-phase flow:

> "The main process inside the container will receive SIGTERM, and after a grace period, SIGKILL. The first signal can be changed with the STOPSIGNAL instruction in the container's Dockerfile, or the --stop-signal option to docker run and docker create."

Timeout rules, verbatim from the same page:

- `-t, --timeout` — "Seconds to wait before killing the container"; if the container is still alive at expiry, "it's forcibly killed with a SIGKILL signal".
- `--timeout -1` — "no timeout is applied, and the daemon waits indefinitely".
- Default: "The default timeout can be specified using the `--stop-timeout` option when creating the container. If no default is configured for the container, the Daemon determines the default, and is **10 seconds for Linux containers, and 30 seconds for Windows containers**."

So the full sequence for `docker stop myapp` on Linux is: SIGTERM (or the image's STOPSIGNAL) → up to 10 s grace → SIGKILL from the host side (the one signal that cannot be ignored, delivered through the ancestor PID namespace; see [PID 1 and Entrypoints](pid1-signals.md)).

A stop of a container that *ignores* the stop signal looks like this in the event stream (example output; compare the SIGTERM death in the [events reference](https://docs.docker.com/reference/cli/docker/system/events/) where `die` follows `kill signal=15` immediately):

```text
t=0s   container kill  ... signal=15     # docker stop: TERM (or STOPSIGNAL)
# ... 10 seconds pass: nobody exits ...
t=10s  container kill  ... signal=9      # grace expired: daemon escalates
t=10s  container die   ... exitCode=137  # 128+9 convention, OOMKilled=false
```

A healthy stop compresses the same timeline into two adjacent events ending in `exitCode=143`.

```console
$ docker stop -t 30 myapp        # extend the grace period to 30 s
myapp
$ docker stop -t -1 myapp        # wait forever instead of killing
```

### docker kill: default SIGKILL

[`docker kill`](https://docs.docker.com/reference/cli/docker/container/kill/) skips the grace period entirely:

> "docker kill ... The main process inside the container is sent SIGKILL signal (default), or the signal that is specified with the --signal option."

The page also notes that a `--signal` value "may be non-terminal" (e.g., SIGHUP) — so `docker kill --signal=HUP` is a reload idiom, not a stop. And because kill bypasses STOPSIGNAL, `docker stop` failing to stop a container within its grace period tells you the app ignored the *stop signal*; `docker kill` is the enforcement, not the diagnosis (see [Troubleshooting Scenarios](troubleshooting-scenarios.md)).

Summary table:

| Command | First signal | Second signal | Default grace (Linux) | Configurable signal? |
|---------|--------------|---------------|----------------------|----------------------|
| `docker stop` | SIGTERM (or image STOPSIGNAL / `--stop-signal`) | SIGKILL | 10 s (daemon default) | first signal only, via STOPSIGNAL/`--stop-signal` |
| `docker kill` | SIGKILL | — | — | yes, `--signal` |
| `docker stop -t -1` | SIGTERM (or configured) | none | infinite | as `docker stop` |

## OOM and the OOMKilled flag (CT-005)

### What the kernel does

With a memory limit set, the container's cgroup has a hard `memory.max` (cgroup v2; see [cgroups-v2](../../containers/cgroups-v2.md)). When reclaim fails inside that limit, the kernel's OOM killer selects a victim inside the cgroup. Docker's ["Resource constraints" guide](https://docs.docker.com/engine/containers/resource_constraints/) frames the stakes:

> "On Linux hosts, if the kernel detects that there isn't enough memory to perform important system functions, it throws an OOME, or Out Of Memory Exception, and starts killing processes to free up memory."

and documents the operator flags: `-m, --memory` (minimum allowed value 6m), `--memory-swap`, `--memory-reservation` (soft limit), and `--oom-kill-disable` — with the warning that disabling the OOM killer is only safe on containers that also have `-m` set. The docs are also explicit that `--memory-swap` is "a modifier flag that only has meaning if `--memory` is also set" and "represents the total amount of memory and swap that can be used, and `--memory` controls the amount used by non-swap memory" — so `--memory="300m" --memory-swap="1g"` means 300 m memory + 700 m swap. If `--memory-swap` is unset, "the container can use as much swap as the `--memory` setting ... if the host has swap memory configured" (e.g., 600 m total for a 300 m limit); only the explicit `--memory-swap=-1` allows unlimited swap.

### How an OOM death is reported

The Engine API container state ([inspect/ContainerState, API ≥ 1.53 spec](https://docs.docker.com/reference/api/engine/latest/)) carries the metadata:

| Field | Documented meaning |
|-------|--------------------|
| `Status` | one of `created`, `running`, `paused`, `restarting`, `removing`, `exited`, `dead` |
| `ExitCode` | "The last exit code of this container" |
| `OOMKilled` | "Whether a process within this container has been killed because it ran out of memory since the container was last started" |
| `Error` | error string from the runtime, if any |
| `StartedAt` / `FinishedAt` | last start/exit timestamps |

An OOM-killed container typically surfaces as `Status=exited`, `ExitCode=137`, `OOMKilled=true`. The 137 is the 128+9 convention applied to the SIGKILL the kernel sent; the **authoritative OOM evidence is the flag, not the number**.

Beyond the two headline fields, the state carries the timeline: `StartedAt` ("the time when this container was last started") and `FinishedAt` ("the time when this container last exited") bracket the incident, and `Error` holds a runtime error string when one exists — useful for separating "ran and died" from "never started" (a 126/127 case leaves its own traces). A quick reading session:

```console
$ docker ps -a --filter name=myapp --format 'table {{.Names}}\t{{.Status}}'
# example output
NAMES   STATUS
myapp   Exited (137) 2 minutes ago

$ docker events --since 10m --filter container=myapp --filter type=container
# example output
container kill  ... signal=9
container die   ... exitCode=137
container oom   ...          # only on OOM
```

`docker ps` STATUS strings use the same `Exited (N)` rendering, which is why the 137-vs-143 distinction is visible at a glance — and why it must not be *concluded* from alone.

### 137 does not prove OOM

Every one of these produces a 137-like observation (exit code 137 and/or a `kill signal=9` event) with *no* memory problem at all:

| Cause | Who sends SIGKILL | Distinguishing evidence |
|-------|-------------------|--------------------------|
| cgroup OOM kill | kernel OOM killer | `OOMKilled=true`; kernel log; `memory.events` counter |
| `docker kill` | operator/automation | `docker events` shows `kill ... signal=9`; OOMKilled stays `false` |
| `docker stop` grace expiry | daemon, after timeout | preceded by `kill ... signal=15` (or STOPSIGNAL) event ~10 s earlier |
| manual `kill -9` from host | human/script | `docker events`; OOMKilled `false` |
| kubelet eviction (in k8s) | kubelet/runtime | k8s-side reason/`OOMKilled` field (see [Kubernetes](kubernetes.md)) |

Evidence checklist that actually separates OOM from everything else:

```console
$ docker inspect myapp --format '{{json .State}}' | python3 -m json.tool
{
    "Status": "exited",
    "ExitCode": 137,
    "Error": "",
    "OOMKilled": true,          # <- the flag is the proof
    ...
}
```

- **Docker metadata:** `.State.OOMKilled` (above) — set by the runtime from kernel/OOM events; the containerd shim even has a dedicated event topic for this ([`TaskOOMEventTopic`](https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md)).
- **Docker event stream:** `docker events --filter event=oom` — `oom` is a documented container event type ([docker events reference](https://docs.docker.com/reference/cli/docker/system/events/)).
- **Kernel log:** `dmesg | grep -i oom` shows the OOM killer's victim report (common practice for host-level triage; the kernel log format varies by kernel version).
- **cgroup counter:** read `memory.events` of the container's cgroup; the kernel documents its `oom_kill` entry as *"The number of processes belonging to this cgroup killed by any kind of OOM killer"* ([kernel cgroup-v2 docs](https://www.kernel.org/doc/Documentation/cgroup-v2.txt)). A non-zero counter that incremented at the incident time is kernel-level proof; the cgroup v2 files are described in [cgroups-v2](../../containers/cgroups-v2.md).

Conversely: `OOMKilled=true` with `ExitCode=0`-adjacent oddities, or 137 with `OOMKilled=false`, are both possible — the code alone is never the conclusion. (Full worked diagnosis: [Troubleshooting Scenarios](troubleshooting-scenarios.md).)

### Memory limits versus node memory

The [resource constraints guide](https://docs.docker.com/engine/containers/resource_constraints/) draws the same two-scope distinction the Kubernetes eviction docs do: a container that stays within its own limits can still be killed when the *node* is exhausted (the kernel OOM killer ranks victims across the whole host — Docker notes it adjusts the daemon's OOM priority, not containers'), while a container that busts its own `--memory` limit is killed precisely and locally. Setting limits converts "random host-wide OOM" into "deterministic, attributable 137 with `OOMKilled=true`" — which is why the first mitigation the guide proposes is "Limit the amount of memory your container can use".

## Practical defaults

1. Set `--memory` (and `--memory-swap` deliberately) on anything memory-sensitive; OOM inside a known limit is diagnosable, OOM of the host is not ([Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)).
2. Treat exit codes as *observations*: 125/126/127 = Docker-side; 0–127 = process's own choice; ≥128 = 128+N signal convention.
3. Use `docker events` (kill/oom/die events) as the timeline, and `docker inspect .State.OOMKilled` as the OOM verdict.

Common traps that combine the above:

- `docker run` returning 125 with a confusing message usually means a CLI flag error, not a container failure — read the message before the code.
- `--restart always` will resurrect containers you stopped on purpose after a daemon restart; the docs' `unless-stopped` exists precisely for maintenance windows.
- A shell-form `CMD` plus `--init` still fixes signals and reaping (tini becomes PID 1), but adds a forwarding hop; the exec form remains the cleaner answer.

## Related Topics

- [PID 1 and Entrypoints](pid1-signals.md) — why the "main process" may never see the SIGTERM this chapter describes
- [Kubernetes](kubernetes.md) — the same semantics behind `terminationGracePeriodSeconds`, `reason: OOMKilled`, and eviction
- [Troubleshooting Scenarios](troubleshooting-scenarios.md) — 143 vs 137 vs 139 and OOM-after-deploy drills
- [Docker Internals](../../containers/docker-internals.md) — daemon → containerd → shim → runc path the events traverse
- [wait4 / waitid](../../syscalls/process/wait4.md) — the kernel wait-status encoding behind exit codes
- [cgroups-v2](../../containers/cgroups-v2.md) — memory.max and the memory controller's OOM behavior

## References

- Docker Docs — Run containers (exit status: 125/126/127 and "exit code of the provided container command"). https://docs.docker.com/engine/containers/run/ (canonical successor of `engine/reference/run`; accessed October 2026)
- Docker Docs — Dockerfile reference (STOPSIGNAL: default SIGTERM, scope, `--stop-signal` override). https://docs.docker.com/reference/dockerfile/ (accessed October 2026)
- Docker Docs — `docker container stop` reference (SIGTERM → SIGKILL after grace; `--timeout`; 10 s Linux / 30 s Windows daemon defaults; `-1` = wait indefinitely). https://docs.docker.com/reference/cli/docker/container/stop/ (accessed October 2026)
- Docker Docs — `docker container kill` reference (default SIGKILL; `--signal`; non-terminal signal caveat). https://docs.docker.com/reference/cli/docker/container/kill/ (accessed October 2026)
- Docker Docs — `docker container run` reference (CLI flags incl. `--stop-signal`, `--memory`, `--oom-kill-disable`, `--init`). https://docs.docker.com/reference/cli/docker/container/run/ (accessed October 2026)
- Docker Docs — Resource constraints (OOME, `--memory` minimum 6m, `--oom-kill-disable`, OOM priority). https://docs.docker.com/engine/containers/resource_constraints/ (accessed October 2026)
- Docker Docs — Engine API reference, `ContainerState` (`Status` enum, `ExitCode`, `OOMKilled` wording, `Error`, timestamps). https://docs.docker.com/reference/api/engine/latest/ (verified against moby `api/docs/v1.53.yaml`; accessed October 2026)
- Docker Docs — `docker system events` reference (`oom`, `kill`, `die` event types; `signal=15` → `exitCode=143` example). https://docs.docker.com/reference/cli/docker/system/events/ (accessed October 2026)
- Kernel Documentation — Control Group v2: `memory.events` (`oom`, `oom_kill` counters). https://www.kernel.org/doc/Documentation/cgroup-v2.txt (accessed October 2026)
- POSIX.1-2024 — Shell Command Language §2.8 (exit statuses > 128 for signal deaths; 126/127 semantics). https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html (accessed October 2026)
- GNU Bash Reference Manual — Exit Status (128+n convention). https://www.gnu.org/software/bash/manual/ (wording verified via `bash(1)`; accessed October 2026)
- containerd — Runtime v2 shim contract (`TaskOOMEventTopic`, `TaskExitEventTopic`). https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md (accessed October 2026)
