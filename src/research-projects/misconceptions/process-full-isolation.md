# "A process is completely isolated from other processes"

## Overview

Process isolation is one of the operating system's proudest guarantees, and
the claim that processes are "completely isolated" is a half-truth built on
it. What the MMU enforces is address-space isolation: one process cannot read
or write another's virtual memory directly. That is a strong, load-bearing
property — and it is not completeness. Processes share the kernel, the
filesystem, physical CPUs and caches, and a long menu of sanctioned and
unsanctioned communication channels. This page separates the isolation
guarantee into its dimensions, shows what remains shared in each, and places
processes in the gradation of isolation strength between containers and VMs.

## The Claim, Stated Fairly

The strongest common form: "Each process gets its own virtual address space;
a bug or an attacker in one process cannot touch another process's memory or
state. Isolation is the whole point of processes." Stated fairly, the first
sentence is true and important — it is why a crashed browser tab (well, a
crashed renderer process) does not corrupt the kernel, and why processes beat
threads for fault isolation. The claim errs by promoting one dimension of
isolation to a totality.

## Verdict

**False.** Process isolation is strong *address-space* isolation, not total
isolation: the kernel, filesystem, CPU and caches, resource limits, and
numerous IPC channels are shared, and side-channel attacks cross even the
memory boundary.

## Why People Believe It

The kernel of truth is the most consequential fact in operating systems: the
MMU plus page tables make every virtual address translation per-process, so
process A's pointer 0x7fff... refers to different physical memory than
process B's identical pointer. A wild write in process A hits A's pages (or
segfaults), not B's data. This is enforced by hardware, tested by decades of
use, and genuinely total *for the dimension it covers* — direct memory
access.

The overreach comes from conflating that dimension with "isolation" as a
whole. An engineer who has never had to think about the OOM killer, a shared
/tmp, or a Spectre-class leak has never observed any of the other dimensions
failing, so the single dimension they have observed feels like the whole
contract.

## The Correct Formulation

| Dimension | Isolated? | What remains shared |
|---|---|---|
| Address space | Strongly (MMU-enforced) | Kernel mappings visible in every address space; Meltdown-class flaws leaked them on affected CPUs |
| CPU | Not isolated | Shared scheduler; contention; shared last-level cache enables cross-process timing channels |
| Filesystem | Not isolated | Shared directory tree, permissions only partition it; same-user files are mutually readable; /tmp is a classic venue |
| Memory capacity | Not isolated | Shared physical memory; a memory hog can trigger the OOM killer to kill an unrelated process |
| IPC | Not isolated | Pipes, shared memory (`shm`), Unix sockets, signals — sanctioned channels by design |
| Visibility | Not isolated | `/proc/<pid>/` exposes cmdline, status, fds, and environment hints of same-user processes |
| Kernel surface | Not isolated | Every process calls the same kernel; a kernel bug is shared attack surface for all |

The correct statement: process isolation is gradated. Within one address
space, isolation from *direct memory access* is hardware-enforced and
complete. Everything else — CPU time, cache, disk, network, kernel, visible
filesystem — is shared with policy controls (permissions, cgroups,
ulimits), and policy controls are softer than page tables. Containers are
*less* isolated than processes (namespaces and cgroups virtualize the view,
but all containers share one kernel); VMs are *more* isolated (separate
kernels on virtualized hardware); processes sit between them.

## Where It Breaks

**The OOM killer.** Process A leaks memory until the kernel's out-of-memory
heuristic fires; the kernel picks a victim by badness score and sends
SIGKILL. Nothing in process B's code — no bug, no misbehavior — is required;
B can be killed because A misbehaved. "Completely isolated" fails its most
practical test: A's failure terminated B.

**/proc visibility.** Any process with the same UID (or root) can read
`/proc/<pid>/status`, `cmdline`, `environ` (subject to ptrace restrictions),
and open file descriptors of another process. Debugging depends on this;
confidentiality does not survive it. Namespaces hide *other users'* processes
from containers, not the sharing between same-UID processes.

**Sanctioned channels.** Pipes, shared memory segments, Unix domain sockets,
and signals exist precisely to let processes communicate; a process that
mmaps a shared segment shares every byte of it by design. `shmat` on an
attacker-known segment is a data-sharing contract, not a violation.

**Side channels.** Spectre (Kocher et al., 2019) uses speculative execution
to leak data via cache timing across trust boundaries; Meltdown (Lipp et al.,
2018) read kernel memory from user space on affected CPUs. These attacks
cross the strongest boundary in the table — the MMU itself — using shared
microarchitectural state. They demonstrated empirically that hardware
enforcement has a hardware-dependent boundary too.

**Resource contention.** Process A saturating the last-level cache or memory
bandwidth measurably slows process B on the same socket — the "noisy
neighbor" problem at process granularity, addressed (imperfectly) with cgroups
and cache allocation technology.

## Practical Implications

- Match the isolation boundary to the threat: hostile code in a container on
  a shared kernel is weaker isolation than a VM; for truly adversarial code,
  VM (or hardware-level) boundaries plus side-channel mitigations are the
  floor.
- Plan for shared fate: per-service memory limits and OOM score adjustments,
  so one service's leak cannot select another service as its victim.
- Treat same-UID processes as mutually trusting: drop privileges for anything
  whose filesystem or /proc visibility would be a problem.
- Understand that IPC is a design choice with an attack surface: a shared
  memory segment or Unix socket is a deliberate hole in the isolation you
  now must guard.
- Remember the gradation when choosing runtime units: process > container
  (kernel-shared) and VM > process for fault and security isolation, with
  density usually running the other way.

## Interview Questions

### What exactly does the OS isolate between processes, and what does it not?

It isolates virtual address spaces via page tables — one process cannot
directly read or write another's memory. It does not isolate CPU time,
caches, filesystem (subject to permissions), physical memory capacity (OOM
killer), or the kernel itself; and it deliberately provides IPC channels that
bridge the boundary.

### How do containers, processes, and VMs rank on isolation strength, and why?

VMs are strongest (separate kernel on virtualized hardware), processes next
(MMU-enforced address spaces under one kernel), containers weakest of the
three (namespaces/cgroups virtualize views, but all share one kernel — a
kernel bug or the OOM killer is common fate). The ranking is about how much
kernel and hardware state is shared.

### Give a concrete scenario where process A's behavior harms process B without any bug in B.

A leaks memory until the OOM killer SIGKILLs B (shared physical memory); or A
saturates the shared LLC, doubling B's cache-miss latency (shared
microarchitecture); or A fills the shared /tmp or a shared filesystem quota
that B needs. No violation of address-space isolation occurs in any of these.

## Key Takeaways

- Process isolation is one dimension — address space — enforced by hardware,
  and it is genuinely complete for that dimension.
- Kernel, filesystem, CPU and caches, memory capacity, visibility, and
  deliberate IPC channels remain shared: isolation is gradated, not total.
- The gradation for deployment choices: container (shares kernel) < process
  (shares OS instance) < VM (shares only hardware) — with density usually
  inverting the ranking.
- Side channels (Spectre, Meltdown) cross even the hardware-enforced
  boundary via shared microarchitectural state; isolation strength is a
  hardware property too.
- "Completely isolated" is not just wrong but operationally dangerous: it
  predicts that the OOM killer and noisy neighbors cannot happen.

## Cross-References

- [Processes](../../os/processes/README.md) — address spaces, fork/exec, and
  process state
- [Virtual Memory](../../os/memory/README.md) — the page-table mechanism
  behind the isolated dimension
- [VM vs Container](../../cloud/virtualization/vm-vs-container.md) — the
  gradation above in deployment terms
- [Assumptions Hunt: Concurrency and Scheduling](../assumptions-hunt/concurrency-and-scheduling.md)
  — shared-resource assumptions between execution units
- [Deadlock Requires CPU](./deadlock-requires-cpu.md) — another case where
  one resource dimension (CPU) hides a failure paid elsewhere
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Linux man-pages project. *proc(5)* — the process information
  pseudo-filesystem and what same-user processes can observe.
  <https://man7.org/linux/man-pages/man5/proc.5.html>
- P. Kocher et al. *Spectre Attacks: Exploiting Speculative Execution*,
  IEEE Symposium on Security and Privacy, 2019.
  <https://spectreattack.com/spectre.pdf>
- M. Lipp et al. *Meltdown: Reading Kernel Memory from User Space*, USENIX
  Security Symposium, 2018.
  <https://meltdownattack.com/meltdown.pdf>
