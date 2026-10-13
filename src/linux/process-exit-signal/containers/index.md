# Exit Codes and Signals in Containers and Orchestration

## Introduction

Containers change who observes a process's death — but not the kernel semantics of that death. A containerized process still terminates either by calling `exit_group()` with a status, or by being killed by a signal, and the runtime still learns the outcome the same way any parent does: by reaping a child and reading its kernel wait status (see the wait4/waitid syscall pages). What containers and orchestrators add is a chain of observers — shell entrypoints, init forwarders, runtimes, shims, the Docker daemon, the kubelet — and each link in that chain can forward, translate, drop, or misreport an exit code or a signal.

This part of the book is the containers and orchestration angle of the exit-codes/signals material: not "how containers work" (that is covered by [Docker Internals](../../containers/docker-internals.md), [Runtime Internals](../../containers/runtime-internals.md), [Primitives](../../containers/primitives.md), and [Kubernetes and Linux](../../containers/kubernetes.md)), but **what status each layer actually reports, why, and how to prove it**.

## Why this chapter exists

Three facts make container exit semantics worth their own treatment:

1. **PID 1 in a container is not a normal process.** The kernel applies special rules to the first process of a PID namespace, and most images get that process wrong (a shell, a supervisor script, a Java launcher...).
2. **The number you see is usually not what the process wrote.** `exit 3` propagates faithfully, but a signal death becomes `128+N` — a convention applied by runtimes and shells — and several unrelated causes produce the same famous `137`.
3. **Orchestration multiplies the failure modes.** Kubernetes adds grace periods, lifecycle hooks, restart policies, backoff, and eviction — each of which can produce an exit status that looks like an application bug but is not.

## Chapter map

| Page | Covers | IDs |
|------|--------|-----|
| [PID 1 and Entrypoints](pid1-signals.md) | Kernel rules for PID 1, zombie reaping, shell-vs-exec form, `exec` and wrapper patterns, init-forwarders (tini/docker-init), statuses lost through nested processes | CT-001, CT-002, CT-009, CT-010 |
| [Docker](docker.md) | `docker run` exit propagation, 125/126/127, the 128+N convention, STOPSIGNAL/`docker stop`/`docker kill`, OOM and `OOMKilled` evidence | CT-003, CT-004, CT-005 |
| [Kubernetes](kubernetes.md) | kubelet termination flow, restart policies and CrashLoopBackOff, container states/reasons, OOM vs eviction, termination messages, Job `backoffLimit` | CT-006, CT-007, CT-008 |
| [Troubleshooting Scenarios](troubleshooting-scenarios.md) | Evidence-driven diagnosis: 137 after deploy, ignored SIGTERM, 143 vs 137 vs 139, zombies, CrashLoopBackOff with exit 1 | CT-011 |

## Reading order and conventions

- Start with [PID 1 and Entrypoints](pid1-signals.md) if you have ever wondered why `docker stop` hangs or your app never sees SIGTERM.
- Each chapter ends with `## Related Topics` and `## References`. Claims cite the official documentation of the tool or kernel component involved (man-pages, kernel.org, docs.docker.com, kubernetes.io); behavior is labeled as **documented**, **common practice**, or **implementation detail/version-dependent** where the sources differ in authority.
- Commands shown are for Linux; outputs marked *example output* are representative, not verbatim from a fixed environment.

## Incident quickstart

If you arrived here from a live incident, the shortest path:

1. **What is the code?** Decode it with the conventions in [Docker](docker.md): 0–127 app, 125–127 Docker itself, 128+N signal death (143=TERM, 137=KILL, 139=SEGV).
2. **Who killed it?** Check `OOMKilled` / `reason: OOMKilled` and the kernel `oom_kill` counter before believing any OOM theory ([Troubleshooting Scenarios](troubleshooting-scenarios.md), Scenario 1).
3. **Did the app see SIGTERM at all?** If PID 1 is a shell, no — fix the entrypoint first ([PID 1 and Entrypoints](pid1-signals.md), Scenario 2).
4. **Is it looping?** Read the exit code *and* the termination message via `restartPolicy` semantics and `FallbackToLogsOnError` ([Kubernetes](kubernetes.md), Scenario 6).

## What this part does not cover

- General container architecture (namespaces, cgroups, image layers): see [Primitives](../../containers/primitives.md) and [cgroups-v2](../../containers/cgroups-v2.md).
- Signal delivery mechanics on bare Linux: see [Signals](../../sysprog/signals.md) and the per-syscall pages under [Signals & Time syscalls](../../syscalls/signals-time/overview.md).
- Service-manager supervision on the host (systemd as PID 1 on a real boot): see the [Init Systems](../../init-systems/README.md) part; the in-container equivalents are discussed in [PID 1 and Entrypoints](pid1-signals.md).

## Related Topics

- [Docker Internals](../../containers/docker-internals.md) — daemon/shim/runtime stack that produces the statuses documented here
- [Runtime Internals](../../containers/runtime-internals.md) — runc/containerd internals, the layer between kernel rules and orchestration policy
- [Primitives](../../containers/primitives.md) — namespaces and cgroups, including the PID namespace rules PID 1 lives under
- [Kubernetes and Linux](../../containers/kubernetes.md) — CRI, kubelet, and node-level mechanics
- [Signals](../../sysprog/signals.md) — disposition, delivery, and handler semantics referenced throughout
- [Process Control](../../sysprog/process-control.md) — fork/exec/wait fundamentals behind every exit code

## References

- Docker Docs — Dockerfile reference, CLI references (`run`, `stop`, `kill`), resource constraints, Engine API. https://docs.docker.com/ (accessed October 2026)
- Kubernetes Documentation — Pod lifecycle, container lifecycle hooks, node-pressure eviction, Jobs, Pod API reference. https://kubernetes.io/docs/ (accessed October 2026)
- Linux man-pages project — `pid_namespaces(7)`, `wait(2)`, `signal(7)`. https://man7.org/linux/man-pages/ (accessed October 2026)
- Kernel Documentation — Control Group v2 (memory controller). https://www.kernel.org/doc/Documentation/cgroup-v2.txt (accessed October 2026)
- krallin/tini README — PID 1, zombie reaping, signal forwarding, exit-code remapping. https://github.com/krallin/tini (accessed October 2026)
