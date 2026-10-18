# "Containers are lightweight virtual machines"

## Overview

This page examines the framing that made containers popular and confused
their security model: the idea that a container is just a smaller, faster
virtual machine. The mechanism is entirely different. A container is a
normal Linux process whose *view* of the system is narrowed by namespaces
and whose *resource use* is bounded by cgroups — all sharing the host's
kernel. A VM runs a separate guest kernel on emulated hardware behind a
hypervisor. Shared kernel versus separate kernel is not a size difference;
it is the difference in isolation strength that the entire sandboxing
ecosystem exists to paper over. This page states the claim fairly, walks
the escape classes, and pins down where the confusion comes from.

## The Claim, Stated Fairly

The strongest common form of the claim is: "A container is a lightweight
VM — it gives you the same isolation with less overhead, so 'container
versus VM' is purely a performance and density choice, and running
untrusted code in a container is as safe as running it in a VM." Stated
this way, the claim is not a caricature; it is exactly the sentence that
gets said when a team decides whether third-party code can run on shared
infrastructure, and exactly what "containers are fast VMs" product copy
has implied for a decade.

The claim deserves its fairness because the *ergonomics* overlap is real:
a container gives you your own root filesystem, your own process tree, your
own network stack view, and your own root user — the same subjective
experience as logging into a tiny server. Both artifacts are created from
declarative images and start in seconds or less. The question is whether
"feels like a small VM" honestly compresses to "is a VM, lighter".

## Verdict

**False.** Containers and VMs achieve isolation by different mechanisms with
different strength: namespaces plus cgroups share one host kernel and
protect nothing from a kernel compromise, while a VM's hypervisor boundary
isolates a separate guest kernel from the host. The "lightweight VM"
framing is not a compression — it is a category error with a security
consequence.

## Why People Believe It

The kernel of truth is fourfold. First, the felt experience matches: inside
a container you are "root" on a filesystem you can wipe and rebuild, with
a PID 1 you own. Second, both are provisioned from images and both scale
horizontally, so planning documents file them in the same drawer. Third,
the speed difference is real — container start is process creation plus
namespace setup, tens of milliseconds, versus guest-kernel boot of seconds,
and per-host density of hundreds versus tens follows from sharing instead
of duplicating kernels (reasoning magnitudes, not measurements). Fourth,
a decade of "containers replace VMs" writing trained the analogy.

What disappears in compression is *what is being shared*. Every container
on a host executes syscalls against the same kernel image, the same driver
code, and the same set of global resources (module state, the page cache,
the network stack implementation). Namespaces isolate *visibility*; cgroups
account *resources*; neither builds a barrier around the kernel itself.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Container = lightweight VM" | A container is a process view (namespaces) plus resource limits (cgroups) on a shared kernel; a VM is a separate guest kernel behind a hypervisor |
| "Same isolation, cheaper" | Cheaper because isolation is weaker: one boundary is syscall-level sharing, the other is hardware emulation |
| "It's sandboxed" | Default containers are not sandboxes; seccomp filters, user-namespace remapping, capability drops, and rootless modes *harden* the boundary without making it hardware |
| "Kernel bugs don't matter" | A single kernel vulnerability affects every container and the host simultaneously; patching cadence is a host-wide security control |
| "VMs are obsolete" | Hostile multi-tenancy still warrants the hypervisor boundary (or a microVM) because the attack surface is device emulation, not the entire syscall interface |

The correct sentence: "Containers give you an isolated *view* and bounded
*resources* on one shared kernel; VMs give you an isolated *kernel* behind
a hypervisor. Pick by threat model, not by startup time."

## Where It Breaks

**The shared-kernel escape classes.** Walk them in increasing sophistication.
Configuration escape: a container started privileged, holding
`CAP_SYS_ADMIN`, or with the host's Docker socket mounted is a boundary in
name only — the "tenant" can mount host paths or ask the daemon to do it.
Kernel-vulnerability escape: an exploit for a kernel bug needs no container
awareness at all, because the container is making syscalls into the same
vulnerable kernel — Dirty COW (CVE-2016-5195, a race in copy-on-write
handling) is the canonical example of a kernel privilege escalation that
works from inside a container straight to the host. Runtime escape:
CVE-2019-5736 overwrote the host's runc binary from inside a container via
`/proc/self/exe`, turning ordinary container execution into host code
execution. Historical probes like Shocker (2014) abused a powerful
capability (`CAP_DAC_READ_SEARCH` with `open_by_handle_at`) to read host
files from a "contained" process. None of these require breaking a
hypervisor; they require the shared substrate the claim pretends does not
exist. VM escape vulnerabilities exist, but they live in the much narrower
surface of virtual device emulation — which is why security-sensitive
multi-tenancy kept a hypervisor between tenants.

**The bootstrap of the whole sandboxing ecosystem proves the point.** If
containers were lightweight VMs, gVisor — a userspace kernel that
intercepts syscalls to give containers a smaller, separate implementation —
would be pointless, as would Kata Containers, which literally runs each pod
inside a real VM, and rootless mode, user-namespace remapping, and default
seccomp profiles. These exist because the plain container boundary was
judged insufficient for hostile workloads. The ecosystem is a standing
document of the difference.

**Where the confusion is measurable.** The numbers people cite as proof of
the claim — startup and density — are real and are consequences of sharing,
not of equivalent isolation. Tens of milliseconds to start (one process,
several namespaces) versus seconds (a guest kernel booting); hundreds of
tenants per host versus tens (kernel memory paid once versus per tenant).
The performance win and the isolation loss have the same root cause:
containers share, VMs duplicate. You do not get the first without the
second.

**Root inside is not a contained root.** By default a container's root user
maps to host UID 0 — the most privileged identity in the kernel — unless
user-namespace remapping is configured. "Root in my little box" is a UI
fiction layered on "UID 0 in the shared kernel," which is why capability
drops and remapping are hardening defaults rather than optional niceties.

## Practical Implications

- Threat-model the boundary, not the branding: trusted code on shared
  infrastructure is a container workload; untrusted or hostile code wants a
  VM, a microVM (Firecracker-class), or a hardened sandbox (gVisor) in
  front of the container.
- Harden by default: run as non-root with user-namespace mapping, drop all
  capabilities, apply seccomp profiles, read-only root filesystems, and
  never mount the Docker socket or host paths into tenant containers.
- Treat kernel patching as a container-security control: one CVE, every
  container on the host, plus the host — your blast radius is the kernel's.
- Do not write "VM-level isolation" in a security review about containers;
  write what is true: namespace/cgroup isolation on a shared kernel, with
  the specific hardening layers enumerated.
- Interview framing: "containers virtualize the *view*; VMs virtualize the
  *machine*." Everything else — speed, density, escape surface — follows.

## Interview Questions

### What actually separates a container from a VM?

Mechanism: a container is a process whose visibility is restricted by
namespaces (mount, PID, network, IPC, UTS, user, cgroup, time) and whose
resources are limited by cgroups — sharing the host kernel directly. A VM
runs a separate guest kernel on virtual hardware mediated by a hypervisor.
Consequences: containers start faster and pack denser (no per-tenant
kernel), but a kernel vulnerability or misconfiguration crosses the
boundary; a VM's stronger boundary costs per-tenant kernel memory and boot
time.

### A pentest says "container escape via kernel exploit" — why doesn't the container isolation stop that?

Because the container makes syscalls into the very kernel being exploited;
namespaces restrict what the process can *see*, not what the kernel can do
once a privilege escalation succeeds. Dirty COW (CVE-2016-5195) is the
textbook case: a kernel race, exploited from inside a container, yields
host access. Mitigations are hardening (minimal capabilities, seccomp,
userns) and fast kernel patching — not the container boundary itself.

### Your platform runs customers' untrusted build jobs. Container-per-job on shared hosts — safe?

Not as stated. Shared-kernel containers are the wrong sole boundary for
hostile code: the escape classes above (privileged misconfig, kernel CVEs,
runtime bugs like CVE-2019-5736) all apply. A defensible answer adds a
stronger outer boundary — per-job microVMs (Firecracker, Kata) or a
gVisor-class syscall sandbox — plus container hardening, short-lived
tokens, and no host socket access. Density drops; that is the honest price
of the boundary.

## Key Takeaways

- Containers = namespaces (view) + cgroups (limits) on one shared kernel;
  VMs = separate kernel behind a hypervisor. Different mechanism, different
  guarantee.
- Isolation strength follows the boundary: syscall-level sharing exposes
  the entire kernel as attack surface; the hypervisor's device-emulation
  surface is far smaller.
- The escape classes are concrete and named: privileged misconfiguration,
  kernel CVEs (Dirty COW), runtime bugs (CVE-2019-5736), capability misuse
  (Shocker).
- Startup and density advantages are real *because* isolation is weaker;
  you cannot bank one without pricing the other.
- The sandboxing ecosystem (gVisor, Kata, rootless, seccomp) exists
  precisely because "lightweight VM" was never true.

## Cross-References

- [A process is completely isolated from other processes](./process-full-isolation.md)
  — the same shared-kernel logic one level down, for plain processes
- [Namespaces](../../os/containers/namespaces.md) — the isolation
  primitives, in the repo's own treatment
- [Control Groups (cgroups)](../../os/containers/cgroups.md) — the resource
  half of the container mechanism
- [VM vs Container](../../cloud/virtualization/vm-vs-container.md) — the
  side-by-side comparison this page deepens
- [gVisor](../../cloud/virtualization/gvisor.md) and
  [Kata Containers](../../cloud/virtualization/kata-containers.md) — the
  projects that add the boundary plain containers lack
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Linux man-pages project. *namespaces(7)* — overview of Linux namespace
  types. <https://man7.org/linux/man-pages/man7/namespaces.7.html>
- Linux man-pages project. *cgroups(7)* — control groups overview.
  <https://man7.org/linux/man-pages/man7/cgroups.7.html>
- CVE-2016-5195 ("Dirty COW") — kernel copy-on-write privilege escalation,
  widely demonstrated from containers; cited by CVE identifier.
- CVE-2019-5736 — runc container escape via `/proc/self/exe` overwrite,
  cited by CVE identifier.
- Sebastian Krahmer. *Shocker* (2014) — container file-read escape via
  `open_by_handle_at` and `CAP_DAC_READ_SEARCH`, cited by exploit name.
