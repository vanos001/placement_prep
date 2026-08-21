# Kata Containers

Kata Containers is a container runtime that runs each container (or pod)
inside a lightweight virtual machine, but presents a normal OCI (Open
Container Initiative) interface to the rest of the stack. From the perspective
of Docker, containerd, or Kubernetes, a Kata container *is* a container —
same `runc`-shaped CLI, same OCI bundle, same image format. From the
perspective of the host kernel, however, the container's processes live
inside a separate guest kernel, running under KVM (or another supported
hypervisor).

The goal is to recover the security boundary of a VM at the operational
cost of a container.

## Architectural overview

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Kubernetes / Docker / containerd                            │
   │  ┌──────────────────────────────────────────────────────┐    │
   │  │  CRI shim (containerd cri plugin or CRI-O)            │    │
   │  └──────────────────────┬───────────────────────────────┘    │
   │                         │ OCI runtime invocation              │
   │  ┌──────────────────────▼───────────────────────────────┐    │
   │  │  kata-runtime  (OCI runtime, drop-in for runc)        │    │
   │  │  - parses OCI config.json                             │    │
   │  │  - decides to create or attach to a "pod sandbox"     │    │
   │  │  - launches kata-shim + kata-agent inside the VM      │    │
   │  └──────────────────────┬───────────────────────────────┘    │
   │  ┌──────────────────────▼───────────────────────────────┐    │
   │  │  qemu-system + kvm  (or Cloud Hypervisor / Firecracker)│    │
   │  │  - host-side VMM                                     │    │
   │  │  - virtio devices net→TAP, block→host file,           │    │
   │  │    vsock→multiplexed channel                          │    │
   │  └──────────────────────┬───────────────────────────────┘    │
   └─────────────────────────┼──────────────────────────────────────┘
                             │
   ┌─────────────────────────▼──────────────────────────────────────┐
   │  guest VM                                                      │
   │  ┌────────────────────────────────────────────────────────┐    │
   │  │  guest kernel (custom-built, ~5 MiB stripped)           │    │
   │  └────────────────────────────────────────────────────────┘    │
   │  ┌────────────────────────────────────────────────────────┐    │
   │  │  kata-agent  (statically linked Go binary, PID 1)      │    │
   │  │  - exposes gRPC over vsock to the host                  │    │
   │  │  - creates container namespaces inside the VM          │    │
   │  │  - mounts the OCI rootfs via virtio-fs (host-backed)    │    │
   │  │  - execs the container entrypoint                      │    │
   │  └────────────────────────────────────────────────────────┘    │
   │  ┌────────────────────────────────────────────────────────┐    │
   │  │  container 1   container 2   container 3   ...         │    │
   │  │  (runc-style inside guest)                             │    │
   │  └────────────────────────────────────────────────────────┘    │
   └────────────────────────────────────────────────────────────────┘
```

Three moving parts deserve attention: the **kata-runtime** (host-side OCI
implementation), the **kata-agent** (guest-side PID 1), and **virtio-fs**
(the file server that lets the guest see host-provided OCI image layers
without copying them).

## kata-runtime: the OCI shim

The OCI runtime specification defines a binary with three core commands:
`create`, `start`, and `delete` (plus `kill`, `state`, etc.). `runc` is the
reference implementation. Kata provides `kata-runtime`, which conforms to
the same spec but internally does something completely different.

When `kata-runtime create <container-id>` is invoked with an OCI bundle:

1. It reads `config.json` to find the container's rootfs path, command,
   env, mounts, and cgroup settings.
2. It looks up the pod sandbox (a VM) this container should join —
   determined by OCI annotations or by the CRI's pod UID.
3. If no sandbox exists, it spawns `qemu-system` with a kernel image and
   rootfs located in `/usr/share/kata-containers/`, allocates memory, sets
   up TAP networking and virtio block devices, and waits for the agent to
   report ready over vsock.
4. It sends a `CreateContainer` gRPC request to the agent, including the
   OCI config, the rootfs mount descriptor (for virtio-fs), and any
   additional volumes.
5. The agent, running as PID 1 in the guest, creates namespaces
   (`mount`, `pid`, `net`) inside the guest, mounts the rootfs via
   virtio-fs, `chroot`s, and execs the container entrypoint.

The host-side view is a `qemu` process. The container's PID namespace is
**inside the VM**, not on the host. The host kernel never sees the
container's processes.

## The guest kernel and kata-agent

The guest kernel is a trimmed Linux kernel — typically a 5–10 MiB bzImage
built with only the drivers Kata needs: virtio, 9p (legacy), virtio-fs,
vsock, TTY, balloon. The kernel is shipped with the Kata installation, not
provided per-image. This is what distinguishes Kata from a "general" VM:
the kernel is fixed, operator-controlled, and audited.

The `kata-agent` is a Go binary built with `CGO_ENABLED=0`, statically
linked, and is the guest's init process. Its responsibilities:

- Open a vsock channel and wait for host commands.
- Implement OCI runtime semantics inside the guest: cgroups, namespaces,
  mounts.
- Spawn container processes and reap zombies (since it is PID 1).
- Implement health checks and resource reporting back to the host.

The agent talks to the host over **vsock** — a host-guest socket address
family that does not require networking. `AF_VSOCK` lets the host and guest
exchange datagrams and streams without involving TCP/IP, so the control
channel cannot be probed from the guest's network namespace.

## virtio-fs: sharing image layers without copying

A container image has many layers (a tar.gz per layer). Without virtio-fs,
Kata would have to either

1. copy the assembled rootfs into the VM's block device before start (slow,
   doubles memory), or
2. expose the host's overlay filesystem to the guest somehow (which would
   require trust in the guest kernel to not exploit it).

`virtio-fs` is the answer. It is a FUSE-like protocol over a virtio queue:
the guest kernel mounts a `virtiofs` filesystem that proxies every file
operation back to a host-side daemon called `virtiofsd`. The daemon, running
on the host (often as part of QEMU), reads from the host's overlayfs (the
assembled container rootfs) and returns data over the virtio queue.

```
   container process (in guest)            host
   ┌──────────────────────────┐
   │ open("/etc/passwd")      │
   │   ↓ VFS                  │
   │ virtiofs mount           │
   │   ↓ descriptor enqueue   │
   │ virtio queue (guest RAM) │
   └──────────┬───────────────┘
              │  (kick: write to MMIO)
   ┌──────────▼───────────────┐
   │ vhost-user-fs backend     │  virtiofsd
   │ (host userspace daemon)   │
   │   reads request           │
   │   looks up file in        │
   │   host overlayfs          │
   │   writes reply to         │
   │   virtio queue            │
   │   signals via irqfd       │
   └──────────┬───────────────┘
              │
              ▼
        file content returns to guest
```

The crucial security property: the **guest kernel does not see host paths**.
The guest sees only the files exposed via the virtiofs mount. The guest has
no way to mount host paths it was not given. The daemon serves a fixed root
and the guest cannot escape it.

## OCI compliance and CRI integration

Kata is an OCI-compliant runtime, which means it is invoked the same way
`runc` is. In Kubernetes, the container runtime interface (CRI) talks to a
runtime shim (containerd's `cri` plugin or CRI-O), and the shim chooses the
OCI runtime binary based on a per-pod annotation:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    io.kubernetes.cri.runtime-handler: kata
spec:
  runtimeClassName: kata
  containers:
    - name: web
      image: nginx
```

The runtime class `kata` maps to `/usr/bin/kata-runtime` in the containerd
config. From there, the same gRPC RPCs (`RunPodSandbox`, `CreateContainer`,
`ExecSync`, etc.) flow; they just get dispatched to a VM-backed
implementation.

For density, Kata supports shared-VM sandboxes (multiple containers in one
VM). The default in Kubernetes is one VM per pod, which preserves pod-level
isolation.

## Hardware isolation vs namespace isolation

A `runc` container relies on Linux namespaces for isolation: the container
sees its own PID 1, its own mount tree, its own network namespace, its own
user mapping. The kernel is shared. A kernel exploit (Dirty COW, OverlayFS
privilege escalations, the long list of CVEs in eBPF, user namespaces, etc.)
bypasses namespace isolation entirely — getting root in a container with
`CAP_SYS_ADMIN` or with a kernel bug is identical to getting root on the
host.

A Kata container adds a hardware boundary. The guest kernel is a separate
kernel running in a separate address space, scheduled by KVM. A bug in the
guest kernel cannot reach the host kernel directly; it must first exploit
the guest kernel, then escape the VM (a much narrower surface — basically
the virtio device back-ends and KVM itself).

| Boundary | runc | gVisor | Kata |
|----------|------|--------|------|
| Container process | namespaced | namespaced + Sentry-filtered syscalls | namespaced in guest kernel |
| Filesystem | host kernel VFS (overlay) | Gofer 9p / lisafs proxy | virtiofs proxy |
| Network | host kernel net stack | netstacker inside Sentry | guest kernel net stack (with host TAP) |
| Syscall surface | full host kernel | tiny subset of host kernel | full guest kernel, isolated |
| Kernel exploit risk | high (CVE chain leads to host) | medium (Sentry is the proxy) | low (must escape VM, not just exploit guest kernel) |
| Boot time | ~10 ms | <100 ms | 1–2 s |
| Memory overhead | near zero | small | ~50 MiB per pod |
| Raw syscall throughput | native | medium (Sentry overhead) | native (no proxy) |
| OS flexibility | any Linux binary | some syscalls unsupported | any Linux binary |

Kata's niche: when the workload needs full Linux kernel semantics (raw
syscalls, privileged operations, user namespaces, eBPF) but the deployment
cannot tolerate the shared-kernel risk of `runc`. Common examples:
multi-tenant CI runners, build farms, code-execution-as-a-service platforms,
regulated workloads where each tenant must be in a separate kernel boundary.

## Comparison: Kata vs gVisor vs Firecracker

Kata and Firecracker both use KVM, but Firecracker is a *VMM-only* project —
it boots a microVM but has no concept of an OCI bundle. Kata, by contrast,
plugs into the container ecosystem via the OCI runtime contract. AWS's
Lambda and Fargate internally use Firecracker with custom glue to do what
Kata does in the open-source world.

gVisor sits between `runc` and Kata: it provides stronger-than-namespace
isolation but does not require a separate guest kernel — instead, a Go
process called the Sentry intercepts and re-implements the syscalls. Kata is
heavier but the semantic gap is zero (a Kata container can run `mount` with
`CAP_SYS_ADMIN` inside the VM, no proxy needed).

## Operational pitfalls

- **Cold start.** Kata boots a kernel, which is unavoidably slower than a
  process clone. Workloads that scale to zero frequently should use a pool
  of warm VMs (Kata supports this via `vmcache`).
- **Memory overhead per pod.** Even an idle Kata pod uses ~50–80 MiB
  resident (guest kernel + agent). Densities are 10× lower than runc.
- **virtiofs latency.** File-heavy workloads (compiling large trees,
  walking big directories) see higher syscall latency than native overlayfs.
  For I/O-heavy workloads, attach a block device backed by the image
  instead.
- **Kernel tuning.** The guest kernel ships with defaults; long-lived pods
  may need `vm.dirty_ratio` and TCP tuning just like any Linux host.
- **The "VM in front of K8s" failure mode.** Debugging a Kata pod sometimes
  requires entering the guest VM, not just `kubectl exec`. Kata supports
  `kata-runtime exec`, but tools that need `ptrace` or `strace` inside the
  guest require the agent to expose a PTY.

## Interview questions

**When should you use Kata over runc?**
For multi-tenant workloads where tenants do not trust each other (SaaS that
runs customer-supplied code), for regulatory environments that mandate
hardware isolation between tenants, or where the kernel CVE surface of
`runc` is unacceptable. The trade-off is per-pod memory overhead and ~1 s
cold start.

**How does Kata differ from gVisor at a syscall level?**
gVisor's Sentry intercepts each syscall the container makes and
re-implements it in Go on top of a much smaller host-syscall surface. A
syscall that the Sentry does not implement returns `ENOSYS`. Kata does no
such filtering: the guest kernel implements the full Linux ABI, but the
guest kernel is itself isolated from the host by hardware. The security
model is "full kernel, separate address space" rather than "subset kernel,
same address space".

**Why does Kata use virtio-fs and not 9p?**
9p (the legacy Plan 9 filesystem protocol) was used in earlier Kata
versions. It is slow on metadata-heavy workloads (a single `stat` round-trips
several requests), and the 9p kernel client has been the source of CVEs.
virtio-fs is a fresh design with DAX support that maps file pages directly
into guest memory, avoiding round-trips for large reads.

**Can Kata run unmodified Docker images?**
Yes — that is the whole point. From the host's perspective Kata looks like
`runc`, so the same image format, the same `Dockerfile`, the same
`kubectl apply` work without changes.

## Cross-references

- [KVM deep dive](./kvm.md) — the hypervisor Kata builds on
- [Firecracker](./firecracker.md) — alternative KVM-based VMM
- [gVisor](./gvisor.md) — software-only sandboxing for containers
- [Hypervisors overview](./hypervisors.md) — Type 1 vs Type 2
- [VMs vs containers](./vm-vs-container.md) — isolation trade-offs

## References

- [Kata Containers GitHub](https://github.com/kata-containers/kata-containers)
- [Kata Containers documentation site](https://katacontainers.io/)
- [Kata Containers architecture design document](https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture.md)
- [virtio-fs specification](https://gitlab.com/virtio-fs/virtio-fs)
- [OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)
- [Kubernetes RuntimeClass documentation](https://kubernetes.io/docs/concepts/containers/runtime-class/)
- [QEMU virtiofsd source](https://gitlab.com/qemu-project/qemu/-/tree/main/tools/virtiofsd)
- [AF_VSOCK: socket address family for VM/host communication (kernel.org)](https://docs.kernel.org/networking/vsock.html)
- [OpenStack Nova — Kata integration](https://docs.openstack.org/nova/latest/admin/configuration.html)
- [Kata Containers v1.0 release blog](https://katacontainers.io/learn/)
