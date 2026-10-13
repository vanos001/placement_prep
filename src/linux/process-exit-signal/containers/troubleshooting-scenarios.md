# Troubleshooting Scenarios: Exit Codes and Signals in Containers

> Covers CT-011: evidence-driven drills. Each scenario follows the same discipline: **observed status → evidence to collect → plausible causes ranked → how to confirm or rule out.** Where the evidence cannot distinguish two causes, the drill says so explicitly — an exit code is an observation, not a verdict.

## The evidence-first method

The tools referenced throughout, with their documented sources:

| Evidence source | What it proves | Command |
|-----------------|----------------|---------|
| Docker container state | exit code + `OOMKilled` flag | `docker inspect <c> --format '{{json .State}}'` ([Engine API](https://docs.docker.com/reference/api/engine/latest/)) |
| Docker event stream | kill/oom/die timeline with signal numbers | `docker events --filter container=<c>` ([events reference](https://docs.docker.com/reference/cli/docker/system/events/)) |
| Pod container statuses | `lastState.terminated`: exitCode, reason, message | `kubectl get pod <p> -o jsonpath=...` ([Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)) |
| Pod events | BackOff, FailedPreStopHook, OOM events | `kubectl describe pod <p>`, `kubectl events` ([debug-pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)) |
| Kernel OOM log | who the kernel OOM killer killed, when | `dmesg \| grep -i oom` (host) |
| cgroup memory events | `oom_kill` counter per cgroup | `cat .../memory.events` ([cgroup-v2 docs](https://www.kernel.org/doc/Documentation/cgroup-v2.txt)) |
| Process table in container | PID 1 identity, zombies | `docker exec <c> ps aux` / `kubectl exec <p> -- ps aux` |

Example outputs below are representative (`# example output`), not from a fixed environment.

A pocket decode table before the drills (full derivations in [Docker](docker.md)):

| Code | Decoding | Likely producer |
|------|----------|-----------------|
| 0–127 | the process's own `exit()` value | application logic |
| 125 | Docker daemon itself | `docker run` misuse / daemon error |
| 126 | contained command can't be invoked | bad ENTRYPOINT path/permissions |
| 127 | contained command not found | typo, missing binary |
| 128+N | killed by signal N (convention) | SIGTERM=143, SIGKILL=137, SIGSEGV=139 |

Evidence pitfalls to keep in mind throughout:

- **Timestamps are evidence.** A 137 that arrives exactly one grace period after the `Killing` event is a shutdown timeout, not OOM.
- **State is per-start.** `OOMKilled` is defined as "killed ... since the container was last started" ([Engine API](https://docs.docker.com/reference/api/engine/latest/)) — a restart clears the flag even though the code repeats.
- **Backoff hides evidence.** In a crash loop, the current attempt may be minutes old; use `--previous` logs and `lastState` (not `state`) for the *previous* death.
- **Attached clients proxy signals.** `docker run --sig-proxy` defaults to `true`, so signals sent to an attached `docker run` client reach the container process; detached (`-d`) containers only receive signals via `docker stop`/`docker kill`/`docker exec` paths — reproducing a signal problem requires the same attachment mode as production.

## Scenario 1: Container exits 137 right after deploy

**Observed status:** `ExitCode=137` (128+9, i.e., death by SIGKILL under the [128+N convention](docker.md)) shortly after rollout. Frequent in pods: `reason: OOMKilled` or `reason: Error`, crash-looping.

**Evidence checklist (in order):**

```console
# Docker:
$ docker inspect myapp --format '{{json .State}}'
# example output
{"Status":"exited","ExitCode":137,"Error":"","OOMKilled":true,...}

# Kubernetes:
$ kubectl get pod mypod -o jsonpath='{.status.containerStatuses[0].lastState.terminated}'
# example output
{"exitCode":137,"reason":"OOMKilled","finishedAt":"2026-10-12T09:15:47Z",...}

# Kernel/cgroup:
$ dmesg | grep -i oom
# example output
Out of memory: Killed process 12345 (myapp) total-vm:..., anon-rss:...
$ cat /sys/fs/cgroup/.../kubepods/.../memory.events
oom 3
oom_kill 3
```

```console
$ kubectl get pod mypod -o jsonpath='{.status.containerStatuses[0].lastState.terminated}' | jq
# example output
{
  "exitCode": 137,
  "reason": "OOMKilled",
  "startedAt": "2026-10-12T09:14:02Z",
  "finishedAt": "2026-10-12T09:15:47Z"
}
$ kubectl events --for pod/mypod --sort-by=.lastTimestamp | tail -4
# example output
LAST SEEN  TYPE     REASON   OBJECT    MESSAGE
2m         Normal   Killing  pod/mypod Stopping container myapp
95s        Warning  BackOff  pod/mypod Back-off restarting failed container
```

**Plausible causes, ranked:**

1. **Cgroup OOM kill** — memory limit hit; kernel OOM killer chose the process.
2. **Explicit SIGKILL** — operator, automation, `docker kill`, or graceful-shutdown timeout (in k8s: grace period expired after the SIGTERM — look for the earlier `kill signal=15`-equivalent and the ~30 s gap).
3. **Node-pressure eviction / host OOM** — the pod was evicted by the kubelet, or the *host* ran out of memory and the kernel picked victims by `oom_score_adj` ([node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)).

A 137 *without* a preceding `Killing` event, but with a fresh `oom_kill` increment, points at cause 1; a 137 that follows `Killing` by exactly the grace period points at cause 2.

**Confirm / rule out:** 137 alone proves nothing. OOM is established by the *metadata*: `OOMKilled=true` / `reason: OOMKilled`, an `oom` event in `docker events`, a fresh `oom_kill` increment in the container's `memory.events`, or a kernel log line at the incident timestamp. `OOMKilled=false` with 137 means someone sent SIGKILL on purpose — correlate with `docker events`/audit logs and the termination flow ([Kubernetes](kubernetes.md)). Host-level OOM shows the victim *outside* your cgroup or shows eviction events instead. Also note the count: `oom_kill 3` with three restarts is one OOM per restart; `oom_kill 0` after a 137 rules the kernel OOM killer out entirely.

## Scenario 2: Graceful shutdown not working — app never sees SIGTERM

**Observed status:** `docker stop` / pod deletion always takes (nearly) the full grace period; app logs show no "shutting down" line; container then dies with 143 (SIGTERM-era exit) or, in k8s, 137 after the grace expiry SIGKILL. In k8s, the pod sits in `Terminating` for the whole `terminationGracePeriodSeconds` ([Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)).

**Evidence checklist:**

```console
$ docker top myapp
# example output
UID   PID   PPID  CMD
root    1      0  /bin/sh -c java -jar app.jar     # <-- the tell
root    7      1  java -jar app.jar
```

`docker exec myapp ps aux` (or `kubectl exec`) shows the same: if PID 1 is `sh`, the documented shell-form behavior applies — "`/bin/sh -c`, which does not pass signals ... your executable doesn't receive a SIGTERM from `docker stop <container>`" ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/)). Confirm delivery itself with strace where permitted:

```console
$ docker exec myapp sh -c 'apt-get install -y strace >/dev/null; strace -p 1 -e trace=signal'
# then: docker stop myapp
strace: Process 1 attached
--- stopped by SIGSTOP ---
--- SIGTERM {si_signo=SIGTERM, si_pid=...} ---   # TERM arriving (or not) at PID 1
```

Absence of a `SIGTERM` line at PID 1 during a stop means the signal was never delivered to the process you think it was.

**Plausible causes, ranked:**

1. **Shell-form CMD/ENTRYPOINT (PID 1 is `sh -c`)** — signals stop at the shell.
2. **App has no SIGTERM handler** — the PID-1 rule makes this lethal: TERM sent to the namespace init is dropped unless a handler exists ([pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)), so the process *survives* the TERM and dies only at grace-expiry SIGKILL (hence exit 137, not 143). This differs from the same app running as a non-PID-1 child, where the default action terminates it immediately (a Go program without `signal.Notify`, a C program without `signal(2)`) — but with no cleanup, which is why even 143 can indicate a handler defect.
3. **Handler exists but blocks** — JVM shutdown hooks, lengthy Go `context` draining, or a wrapper's trap that cleans up for longer than the grace period (in k8s, preStop time counts against the same budget; see the documented 55+10 > 60 example in [Container lifecycle hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)).
4. **preStop hook hangs** — `FailedPreStopHook` events or a pod stuck in `Terminating`; hook logs are not in events, so check the pod logs.
5. **Signal mask inherited blocked** — a launcher that blocked signals around startup and `exec`ed with the mask still set defers the first TERM indefinitely; rare, but invisible in logs and visible in `strace` only.

**Confirm / rule out:** `docker top`/`ps` identifies cause 1 instantly (fix: exec form, `exec` in the wrapper, or `--init`). If PID 1 is the app, cause 2 vs 3 is distinguishable by logs and timing (a handler that *starts* draining logs immediately; a missing handler logs nothing before the SIGKILL). Runtime/tooling version differences (e.g., older shell images) can matter — verify in the failing image itself, not in a similar one.

## Scenario 3: Stop takes the full grace period *every* time

**Observed status:** identical wall-clock stop duration across all instances, ending in SIGKILL.

This is Scenario 2's degenerate case: **no handler at all**. The distinction is consistency — a working handler makes stop duration variable (drain time depends on load); a full-grace-period stop every time means the TERM did nothing. Evidence: compare `docker events` — a healthy stop shows `kill ... signal=15` followed by `die ... exitCode=143` *before* the timeout; a broken one shows the 15 and then a `signal=9`/timeout path or exitCode 137 ([events reference](https://docs.docker.com/reference/cli/docker/system/events/)):

```text
# example output — healthy stop
t=0s   container kill ... signal=15
t=1.2s container die  ... exitCode=143
# example output — ignored SIGTERM, daemon escalates at the 10 s default
t=0s   container kill ... signal=15
t=10s  container kill ... signal=9
t=10s  container die  ... exitCode=137
```

Rank: (1) PID 1 is a shell or a binary with no TERM handling; (2) handler registered but on the wrong signal (app listens for SIGHUP/INT, image STOPSIGNAL sends something else — check `STOPSIGNAL` in the image); (3) app is stopped-state (T-state) so signals queue. Confirm by sending the signal manually inside the container (`kill -TERM 1` from an exec — for PID 1 this may be dropped by the kernel rule unless a handler exists; use the runtime's own stop path for a faithful reproduction) and watching the logs.

## Scenario 4: exit 143 vs 137 vs 139 — the triage flow

| Code | Meaning | What it tells you | Next question |
|------|---------|-------------------|---------------|
| 143 | 128+15, SIGTERM | Someone *asked* for a stop and the process (or its forwarding PID 1) died by TERM | Was it requested (deploy, scale-down) or stray (misconfigured probe, signal-forwarding wrapper)? Exit 0 expected after a *handled* TERM — 143 often means "handler missing but shell propagated" |
| 137 | 128+9, SIGKILL | Something *forced* the death; never the app's own choice | Who: OOM killer (check `OOMKilled`/reason/`memory.events`), grace-expiry, `docker kill`, manual kill -9? ([Docker](docker.md) table) |
| 139 | 128+11, SIGSEGV | The process crashed on an invalid memory access — a genuine application/bug signature (or bad NIF/FFI/C code) | Core dump/config of the language runtime; not an orchestration fault |

**Flow:** (1) read the code with its 128+N decoding; (2) classify: 139 → app bug path; 143 → stop path; 137 → *force* path; (3) for 137, apply the Scenario 1 evidence checklist — only metadata (OOMKilled/reason/kernel log) upgrades "SIGKILL" to "OOM"; (4) for 143 in a workload that should exit 0 on TERM, treat as a shutdown-handling defect ([PID 1 and Entrypoints](pid1-signals.md); tini's README documents exactly this 143 problem for Java apps). Remember exit codes ≥128 are *convention* ([bash(1)](https://www.gnu.org/software/bash/manual/), POSIX >128), so a non-shell runtime could, in principle, report signal deaths differently — confirm what your shim/runtime does before betting an incident on the arithmetic.

## Scenario 5: Zombie accumulation in a container

**Observed status:** `ps aux` inside the container shows growing `[defunct]` entries; over time `fork` fails ("cannot allocate memory" is the classic misleading errno for PID exhaustion).

```console
$ kubectl exec mypod -- ps aux | grep defunct | wc -l
412
```

**Causes, ranked:** (1) PID 1 is an application (or shell) that never calls `wait()`; orphans reparent to PID 1 by the namespace rule — "This process becomes the parent of any child processes that are orphaned" ([pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)) and stay as zombies because "if a wait is not performed, then the terminated child remains in a 'zombie' state" ([wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html)); (2) a wrapper forwards signals but doesn't reap; (3) cron-like containers spawning short-lived children with an unreaping init.

**Confirm / rule out:** zombies have the parent they wait on; `ps -o ppid= -p <zombie-pid>` pointing at PID 1 confirms nobody reaps. Note the counter-example: a **subreaper** (shim on the host, `tini -s`) can absorb some orphans — but only processes whose reparenting path reaches it; *inside* the container namespace, PID 1 is always the fallback. Fix options, in order of preference:

1. Run an init: `--init` on Docker ("forwards signals and reaps processes"), `ENTRYPOINT ["tini","--"]` in the image, or dumb-init — this fixes reaping *and* signal forwarding together.
2. Make PID 1 reap: explicit `wait()` loop in the supervisor, or the SIGCHLD trick — `signal(SIGCHLD, SIG_IGN)` / `SA_NOCLDWAIT` — remembering the POSIX caveat from `wait(2)` that explicitly ignoring SIGCHLD changes child accounting (children are auto-reaped instead of becoming zombies; `wait()` then fails with `ECHILD`).
3. Fix the spawner so it reaps its own children (the correct long-term fix for libraries that fork helpers).

## Scenario 6: CrashLoopBackOff with exit 1 — app bug or config error?

**Observed status:** pod in `Waiting/CrashLoopBackOff`; `kubectl describe pod` shows the documented `Back-off restarting failed container` event; `lastState.terminated.exitCode: 1`.

The pod-lifecycle docs list the cause classes to separate ([pod-lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)): "Application errors that cause the container to exit", "Configuration errors, such as incorrect environment variables or missing configuration files", "Resource constraints", and failing probes.

**Evidence checklist:**

```console
$ kubectl get pod mypod -o jsonpath='{.status.containerStatuses[0].lastState.terminated}' | jq
# example output
{ "exitCode": 1, "reason": "Error",
  "message": "pq: password authentication failed for user \"app\"", ... }

$ kubectl logs mypod --previous | tail -5
# example output
FATA config: missing required env DB_PASSWORD
```

The `message` field is populated from `terminationMessagePath` (default `/dev/termination-log`), and with `terminationMessagePolicy: FallbackToLogsOnError` the kubelet fills it from the last chunk of container logs when the file is empty and the container exited with an error — "limited to 2048 bytes or 80 lines" ([Pod API reference](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/)). Adding that policy to your containers is the cheapest permanent improvement to this drill:

```yaml
containers:
- name: myapp
  image: myapp:1.4.2
  terminationMessagePath: /dev/termination-log
  terminationMessagePolicy: FallbackToLogsOnError
```

The pod-lifecycle docs' own triage list for a crash loop maps onto this scenario: "Check logs ... Inspect events ... Review configuration ... Check resource limits ... Debug application" — the exit code feeds the *state*, the message feeds the *diagnosis*, and the two are only the same thing for well-behaved applications.

**Causes, ranked:** (1) app-level error (stack trace / FATA in logs; message populated); (2) configuration error (missing env/secret/bad mount — identical symptom, different fix owner; the termination message usually says which); (3) resource constraint at startup (OOMKilled reason instead of Error — exit 1 wouldn't appear); (4) probe kills (events show liveness/readiness failures; code will be 137, not 1). Confirm by reproducing locally with the same env (`docker run -e ... image`), and rule out config drift with `kubectl exec` on a sibling healthy pod. Timing note: restarts follow the backoff (initial immediate attempt, then exponential — implementation values 10 s→300 s cap, reset after ~10 min; documented as "exponential backoff" in the docs, constants are kubelet implementation detail — [Kubernetes](kubernetes.md)), so *when* evidence is collected matters: logs from `--previous` survive, but the pod's current attempt may be minutes old.

## Cross-scenario rules of thumb

1. **Codes classify, metadata convicts.** 0–127: the process's own exit; ≥128: signal convention; 125–127 under `docker run`: Docker itself. Only `OOMKilled`/`reason`/kernel counters establish OOM.
2. **Check PID 1 before blaming the app.** `sh -c` as PID 1 explains a whole class of "ignored signals" symptoms by itself.
3. **Timestamps are part of the evidence.** Grace-expiry SIGKILLs carry a ~grace-period delay; OOM kills do not; backoff resets change what "recent" logs mean.
4. **Fix the entrypoint before stretching the grace period.** A full-grace-period stop is a symptom; raising `terminationGracePeriodSeconds`/`-t` only makes the symptom slower. (Common practice — the docs define the grace period, not this ordering.)
5. **When evidence is ambiguous, say so.** If OOM metadata is absent *and* no kill event is visible (rotated, pruned, wrong project), the honest report is "SIGKILL of unknown origin" — with the collection commands above attached, not a guess.

## Quick command reference

| Goal | Command |
|------|---------|
| Container exit state (Docker) | `docker inspect <c> --format '{{json .State}}'` |
| OOM flag only | `docker inspect <c> --format '{{.State.OOMKilled}}'` |
| Kill/oom/die timeline | `docker events --since 30m --filter type=container` |
| PID 1 identity | `docker top <c>` or `kubectl exec <p> -- ps aux` |
| Pod last termination | `kubectl get pod <p> -o jsonpath='{.status.containerStatuses[0].lastState.terminated}'` |
| Pod events | `kubectl describe pod <p>`, `kubectl events --for pod/<p>` |
| Previous attempt logs | `kubectl logs <p> --previous` |
| Kernel OOM history | `dmesg \| grep -i oom` |
| Per-cgroup OOM counter | `cat /sys/fs/cgroup/.../memory.events` (`oom_kill` line) |
| Entrypoint sanity check | `docker run --rm <image> <cmd>; echo $?` (126/127 decode first) |

## Related Topics

- [PID 1 and Entrypoints](pid1-signals.md) — the kernel rules behind scenarios 2, 3, and 5
- [Docker](docker.md) — exit-code conventions, stop flow, OOMKilled evidence (scenarios 1 and 4)
- [Kubernetes](kubernetes.md) — termination flow, reasons, backoff, eviction (scenarios 1, 3, 6)
- [Signals](../../sysprog/signals.md) — disposition and delivery mechanics
- [Process States](../../kernel/processes/process-states.md) — zombie state fundamentals
- [Kubernetes and Linux](../../containers/kubernetes.md) — kubelet/runtime architecture

## References

- Docker Docs — Engine API (`ContainerState`: `ExitCode`, `OOMKilled`, `Status` enum). https://docs.docker.com/reference/api/engine/latest/ (accessed October 2026)
- Docker Docs — `docker system events` reference (`kill`/`oom`/`die` events; `signal=15 → exitCode=143` example). https://docs.docker.com/reference/cli/docker/system/events/ (accessed October 2026)
- Docker Docs — Dockerfile reference (shell-form signal warning; exec form; STOPSIGNAL). https://docs.docker.com/reference/dockerfile/ (accessed October 2026)
- Docker Docs — `docker container stop` / `docker container kill` references (grace period, 10 s Linux default, SIGKILL default). https://docs.docker.com/reference/cli/docker/container/stop/ , https://docs.docker.com/reference/cli/docker/container/kill/ (accessed October 2026)
- Kubernetes Docs — Pod Lifecycle (termination, container states, restart policy, CrashLoopBackOff causes and diagnosis). https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ (accessed October 2026)
- Kubernetes Docs — Container Lifecycle Hooks (preStop timing, failure events, logs not in events). https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/ (accessed October 2026)
- Kubernetes Docs — Node-pressure eviction (kernel oom_killer fallback, `oom_score_adj` table). https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/ (accessed October 2026)
- Kubernetes API Reference — Pod v1 (`terminationMessagePath`, `terminationMessagePolicy: FallbackToLogsOnError` limits). https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/ (accessed October 2026)
- Kubernetes Docs — Debug Pods and Determine the Reason for Pod Failure. https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/ (accessed October 2026)
- Linux man-pages — `pid_namespaces(7)` (orphan reparenting, PID 1 signal restriction), `wait(2)` (zombie semantics, SIGCHLD caveat). https://man7.org/linux/man-pages/ (accessed October 2026)
- Kernel Documentation — Control Group v2 (`memory.events`: `oom`, `oom_kill`). https://www.kernel.org/doc/Documentation/cgroup-v2.txt (accessed October 2026)
- GNU Bash Reference Manual — Exit Status (128+n convention). https://www.gnu.org/software/bash/manual/ (accessed October 2026)
- krallin/tini README (143 exit-code remapping for Java apps; reaping). https://github.com/krallin/tini (accessed October 2026)
