# Google gVisor

gVisor is an application-level kernel — written in Go — that provides a
sandboxed execution environment for untrusted Linux binaries. It implements
enough of the Linux system-call interface to run ordinary containers, but
the syscalls do not flow to the host kernel directly. Instead they are
intercepted and re-implemented in userspace by a process called the
**Sentry**, which exposes a much smaller, heavily filtered surface to the
host kernel. The result is a container that runs a normal `runc`-shaped OCI
bundle but whose every system call is mediated by a separate Go process.

gVisor was open-sourced by Google in 2018 and is the basis of the sandboxing
layer in Google Cloud Run, Google App Engine standard environment, and
Google Kubernetes Engine's "sandboxed pods" feature.

## Architecture

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Host kernel                                                    │
   │  (sees only a tiny subset of syscalls from the Sentry)           │
   └─────────────────────────────────────────────────────────────────┘
            ▲
            │  carefully filtered syscalls (epoll, futex, read/write on
            │  pre-opened FDs, mmap, rt_sigreturn, etc.)
            │
   ┌────────┴────────────────────────────────────────────────────────┐
   │  Sentry  (Go process, runs as the sandbox's "kernel")             │
   │  - implements ~270 Linux syscalls in pure Go                     │
   │  - maintains per-container task table, MM, fds, fs context       │
   │  - schedules goroutines on the runtime's P, G, M                 │
   └────────┬────────────────────────────────────────────────────────┘
            ▲                                ▲
            │ syscalls (platform = ptrace   │ file ops (9p / lisafs)
            │   or KVM trap or systrap)      │
            │                                │
   ┌────────┴──────────┐         ┌──────────┴──────────────────────┐
   │  container app    │         │  Gofer (per-sandbox helper)     │
   │  (untrusted code) │         │  - opens host files on behalf    │
   │                   │         │    of the Sentry                 │
   └───────────────────┘         │  - serves them via 9p / lisafs    │
                                  └──────────────────────────────────┘
```

Three processes per sandbox (Sentry, Gofer, and the container's processes)
plus the host kernel. The key is what is **not** in the picture: there is
no guest kernel, no KVM (in the ptrace/systrap platforms), no QEMU, no
separate address space for the application code itself — the Sentry runs in
the same host kernel address space as the container, but it acts as the
kernel for that container.

## The Sentry: a userspace kernel

The Sentry is the heart of gVisor. It is a Go program that implements the
Linux kernel ABI from the application's perspective. When the container's
init process issues a syscall, the call is intercepted by the chosen
**platform** (more below) and routed into the Sentry's syscall handler.
The handler dispatches by syscall number:

```go
// in pkg/sentry/syscalls/linux64/linux64.go (paraphrased)
var AMD64Syscalls = map[uintptr]kernel.SyscallFn{
    unix.SYS_READ:        SysRead,
    unix.SYS_WRITE:       SysWrite,
    unix.SYS_OPENAT:      SysOpenat,
    unix.SYS_MMAP:        SysMmap,
    unix.SYS_EPOLL_WAIT:  SysEpollWait,
    unix.SYS_CLONE:       SysClone,
    unix.SYS_SOCKET:      SysSocket,
    /* ~270 entries */
}
```

Each handler validates arguments, looks up the relevant kernel objects (FD
table, memory manager, task structure, mounts), and either executes the
operation locally (e.g., `mmap` becomes an `mmap` on the Sentry's own
address space) or forwards it to the Gofer (for file-backed operations).

The Sentry maintains the abstractions a real kernel maintains: `Task`
structs (analog of `task_struct`), `FDTable`, `MemoryManager`,
`MountNamespace`, `Credentials`, `Limits`. Go's goroutine scheduler takes
the place of the kernel's scheduler: each container task is a goroutine,
context-switched by the Go runtime.

This is a significant architectural choice. The Linux kernel scheduler is
preemptive; the Go scheduler is cooperative — a goroutine runs until it
blocks. The Sentry fakes preemption by hooking into platform timers (the
KVM platform sets a one-shot timer that causes a vmexit, which interrupts
the goroutine). On the ptrace/systrap platforms, long-running syscalls are
interrupted by signals.

## Platforms: ptrace, KVM, systrap

gVisor's "platform" is the mechanism by which syscalls from the container
application are intercepted and routed to the Sentry. There are three:

### ptrace (original, portable)

The Sentry `fork`s the container's init process under `PTRACE_O_TRACESECCOMP`
and `PTRACE_O_TRACESYSGOOD`. Each time the child enters a syscall trap, the
Sentry gets a `SIGTRAP`, reads the registers via `PTRACE_GETREGS`, decides
what to do, writes the result back with `PTRACE_SETREGS`, and resumes with
`PTRACE_SYSEMU`. The child never actually executes its own syscalls on the
host kernel — the Sentry emulates them.

```
  child process                  sentry process
  ─────────────────              ──────────────
  int $0x80 (syscall)           waitpid → WIFSTOPPED, SIGTRAP
       ▼                        PTRACE_GETREGS → rax=SYS_open, ...
  SIGTRAP (stops)               emulate openat → return fd=3
                                PTRACE_SETREGS → rax=3
                                PTRACE_SYSEMU (resume, skip syscall)
  resumes, rax=3
```

The ptrace platform is portable (it works on any Linux) but slow: each
syscall is at least four context switches. Saturating more than a few
thousand syscalls per second is difficult.

### KVM platform

In this mode the Sentry itself runs as a KVM guest — but only the Sentry,
not the application. The application runs in **host ring 3**, but the Sentry
runs in **guest ring 0**. The CPU runs the application at full native
speed; when the application issues a syscall, the `SYSCALL` instruction is
configured to cause a VM exit (via the secondary processor-based VM-execution
controls).

```
  ┌────────────────────────────────────────────────────────┐
  │  KVM guest                                             │
  │                                                        │
  │  ring 0:  Sentry  (Go process, privileged)             │
  │  ring 3:  application (sandboxed, untrusted)           │
  │                                                        │
  └────────────────────────────────────────────────────────┘
            ▲
            │  vmexit on SYSCALL / INT 0x80 → routed to Sentry
            ▼
        host KVM
```

The KVM platform avoids ptrace's per-syscall context-switch cost but
introduces the cost of vmexits and the security of having a real CPU
privilege boundary. Performance is roughly 2× better than ptrace on
syscall-heavy workloads.

### systrap (newer, default for many workloads)

The systrap platform is gVisor's modern innovation. Instead of ptrace it
uses Linux's `seccomp-unotify` feature (added in 5.0): the Sentry configures
the child to allow *all* syscalls but immediately traps them to a
notification FD (`SECCOMP_RET_USER_NOTIF`). The Sentry then receives the
syscall via the notification FD, reads its arguments out of the child's
memory, decides what to do, and writes the result back with
`ioctl(SECCOMP_IOCTL_NOTIF_SEND)`.

The advantage: no `PTRACE_*` syscalls at all (which were the bottleneck —
ptrace is famously slow). Systrap is roughly 3–5× faster than ptrace on
common workloads and is the default on Cloud Run.

## The Gofer: a 9p file proxy

A real container accesses its root filesystem (typically an overlay of image
layers). In gVisor, the Sentry does not have direct filesystem access — it
would have to be running as root on the host, which would defeat the
purpose. Instead, file operations go to the **Gofer**, a per-sandbox helper
process that opens the host filesystem on the Sentry's behalf.

```
  app in container        sentry                  gofer        host kernel
  ─────────────────       ───────                 ─────        ────────────
  open("/etc/hosts")
        ▼
  Sentry receives syscall
  proxy request over
  9p / lisafs ──────────► opens /var/lib/.../etc/hosts
                                on host
                          ◄──── returns FD and stat
  Sentry caches file
  contents, hands to app
```

The Gofer is the only process with host filesystem privileges; the Sentry
runs unprivileged with respect to host paths. Files are exchanged via the
9p protocol (historically) or `lisafs` (newer, designed in gVisor for lower
syscall count per file operation).

The consequence: file operations are slower than native. A `stat` syscall
that costs ~1 µs on the host can cost 50–100 µs through the Gofer. gVisor
mitigates this with aggressive caching in the Sentry: once a directory or
file is read, the Sentry caches the contents and most subsequent calls do
not touch the Gofer at all. For typical server workloads (open a few config
files at startup, then serve traffic in memory) this is fine; for build
workloads (walking huge directory trees, lots of file creation) it is not.

## Syscall filtering and limitations

gVisor's Sentry does not implement every Linux syscall. Some unsupported or
partially supported:

- `keyctl`, `kexec_load`, `bpf`, `perf_event_open` — blocked entirely.
- `mount` — implemented only for tmpfs; no real mounting.
- `pivot_root` — partially supported.
- `ioprio_set` — no-op.
- x86 `int 0x80` ABI — supported; `SYSCALL` instruction — supported.
- Some `ioctl` commands on block devices — not supported (the devices do
  not exist).
- `userfaultfd`, `io_uring` — historically limited; recent versions
  expanded support.

For container workloads that depend on these (some Java agents, eBPF
tools, monitoring sidecars), gVisor is a poor fit. gVisor also does not
support running privileged containers meaningfully — `CAP_SYS_ADMIN` inside
the Sentry gives you nothing because the Sentry cannot pass it through to
the host.

## Comparison: gVisor vs runc vs Kata

| Aspect | runc | gVisor | Kata |
|--------|------|--------|------|
| Kernel for application | host kernel | Sentry (Go userspace) | guest kernel (in VM) |
| Isolation boundary | namespaces + seccomp | Sentry + Gofer | hardware (KVM) |
| Boot time | ~10 ms | ~50–100 ms | ~1–2 s |
| Memory overhead | negligible | small (~10 MiB) | significant (~50 MiB) |
| Syscall compatibility | full | subset (most workloads work) | full |
| Raw syscall throughput | native | 2–10× slower | native |
| Filesystem throughput | native overlayfs | reduced (Gofer-mediated) | native (virtiofs) |
| Best for | trusted workloads | untrusted workloads needing fast cold-start | untrusted workloads needing full kernel ABI |
| Kernel exploit risk to host | high (CVE chain) | low (Sentry is the boundary) | very low (must escape VM) |
| Production use | default container runtime | Google Cloud Run, GKE Sandbox, App Engine | OpenStack, k8s operators needing VM isolation |

## Production use: Google Cloud Run

Cloud Run, Google's serverless container execution platform, runs every
container revision inside a gVisor sandbox. Each revision gets its own
Sentry/Gofer pair. The platform's promise — "no shared kernel between
tenants" — comes from gVisor.

The cold-start story is interesting. Cloud Run's "execution environment v2"
uses the systrap platform and warm pools of partially-booted Sentry
processes. A new revision inherits a warm sandbox in under 100 ms in the
steady state; this is faster than Kata (which must boot a kernel) and
competitive with runc.

App Engine standard environment uses gVisor for the same reason —
multi-tenant Python/Java/Go runtime hosting where customers should not be
able to peek at each other's memory via kernel exploits.

GKE's "sandboxed pods" feature lets you opt in to gVisor per pod with
`runtimeClassName: gvisor`:

```yaml
apiVersion: v1
kind: Pod
spec:
  runtimeClassName: gvisor
  containers:
    - name: web
      image: nginx
```

The `gvisor` runtime class is configured in the kubelet's containerd config
to point at `runsc` (gVisor's OCI runtime binary — `runsc create`, etc.).

## Performance characteristics to remember

- **CPU-bound workloads** (hashing, JSON parsing, no syscalls) run at native
  speed — the CPU is the host CPU, the Sentry is not in the data path.
- **Memory-bound workloads** also run at native speed; `mmap` is fast (the
  Sentry uses host `mmap` underneath).
- **Syscall-bound workloads** see the most overhead. A `select()` loop that
  fires thousands of times per second, a small read/write ping-pong, or a
  `getpid()` tight loop will be 2–10× slower than native.
- **File-heavy workloads** (build tools, package managers) are the worst
  case — Gofer round-trips dominate.
- **Network throughput** for TCP is close to native because gVisor has its
  own netstack (a Go re-implementation of the Linux TCP/IP stack inside the
  Sentry); packets go through the Sentry's netstack, then out a TAP device
  on the host.

## Interview questions

**How can a Go program implement a kernel?**
A kernel is fundamentally a piece of code that intercepts system calls and
dispatches them. The traditional Linux kernel does this in ring 0 via
`int 0x80` / `SYSCALL` handlers. gVisor's Sentry does the same thing in
userspace — via ptrace, seccomp-unotify, or a KVM trap — and dispatches in
Go. The semantics are identical from the application's view; the location
is different. Go provides concurrency primitives (channels, goroutines)
that make writing a scheduler straightforward, though Go's GC pauses are a
constant source of work for the gVisor team to bound.

**Why doesn't gVisor just use seccomp?**
Seccomp filters syscalls but cannot *implement* them. A seccomp profile
that blocks `openat` prevents the application from opening files; it does
not provide an alternative `openat`. gVisor wants to allow applications to
open files but route the open through a controlled proxy (the Gofer).
Seccomp is used internally — the Gofer itself runs under a seccomp filter,
the Sentry uses seccomp for its own hardening — but it is the platform, not
the whole sandbox.

**When is gVisor the wrong choice?**
For workloads that (a) need the full kernel ABI (eBPF tools, container
monitoring agents, kernel modules), (b) need very high syscall or file I/O
throughput, or (c) need to call privileged syscalls (mounting real
filesystems, configuring network interfaces). In those cases, `runc` (for
trusted workloads) or Kata (for untrusted but full-ABI workloads) is better.

## Cross-references

- [KVM deep dive](./kvm.md) — the KVM platform gVisor optionally uses
- [Firecracker](./firecracker.md) — alternative hardware-isolation sandbox
- [Kata Containers](./kata-containers.md) — VM-based container runtime
- [Hypervisors overview](./hypervisors.md) — Type 1 vs Type 2
- [VMs vs containers](./vm-vs-container.md) — isolation trade-offs

## References

- [gVisor GitHub repository](https://github.com/google/gvisor)
- [gVisor documentation site](https://gvisor.dev/)
- [gVisor architecture overview](https://gvisor.dev/docs/architecture/)
- [gVisor platforms (ptrace, KVM, systrap)](https://gvisor.dev/docs/user_guide/platforms/)
- [Google Cloud Run documentation (uses gVisor)](https://cloud.google.com/run/docs/about)
- [GKE Sandbox (gVisor) documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- [LWN: The seccomp unotify mechanism (2019)](https://lwn.net/Articles/788332/)
- [gVisor syscall support reference](https://gvisor.dev/docs/user_guide/compatibility/syscalls/)
- [gVisor performance benchmarks](https://gvisor.dev/docs/user_guide/benchmarks/)
- [OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)
