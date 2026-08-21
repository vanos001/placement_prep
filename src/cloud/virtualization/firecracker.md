# AWS Firecracker

AWS Firecracker is a virtual machine monitor written in Rust, released as
open source by AWS in 2018. It is not a competitor to QEMU in the
general-purpose sense — QEMU can emulate a 1995-era SPARCstation; Firecracker
can boot a Linux guest on KVM, full stop. What it gives up in generality it
buys back in two scarce currencies: **startup time** and **memory
footprint**. A Firecracker microVM boots in roughly 125 ms wall-clock from a
cold start, occupies about 5 MiB of resident memory for the VMM process, and
packs thousands of microVMs per host — properties required to make
per-customer, per-request virtualization economically viable in serverless
platforms such as AWS Lambda and Fargate.

## Design constraints

Firecracker's design derives from a fixed workload profile: short-running
functions or containers that

- boot a known, minimal Linux kernel,
- need a network interface and one or more block devices,
- never use a graphical console, sound, USB, or any other hardware that
  requires full platform emulation,
- run untrusted tenant code that must be isolated at the hardware level.

Given that profile, Firecracker can:

- ship **no device model** beyond what is strictly required (serial console,
  virtio-net, virtio-block, virtio-balloon, virtio-rng, virtio-vsock),
- avoid **PCI bus emulation** by using MMIO transport for virtio devices,
- avoid **BIOS/UEFI emulation** by using a custom minimal loader (no SeaBIOS,
  no OVMF),
- run as a **single-threaded epoll loop** (with a tiny control thread for
  the API socket),
- pre-allocate and lock all guest memory at startup and never grow it.

The result is a VMM with roughly 50 KLoC of Rust, versus QEMU's millions of
lines of C.

## Boot path

A Firecracker microVM boot has the following stages:

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. firecracker process started by orchestrator        │
  │    - reads JSON API on a Unix socket                   │
  │    - opens /dev/kvm                                    │
  └──────────────┬─────────────────────────────────────────┘
                 │
  ┌──────────────▼─────────────────────────────────────────┐
  │ 2. configure: kernel image path, kernel cmdline,       │
  │    initrd (optional), vCPU count, memory, network      │
  │    TAPs, block device files, balloon, vsock            │
  └──────────────┬─────────────────────────────────────────┘
                 │
  ┌──────────────▼─────────────────────────────────────────┐
  │ 3. allocate guest memory (mmap + madvise, locked,      │
  │    hugepage-able)                                      │
  │    register with KVM_SET_USER_MEMORY_REGION             │
  └──────────────┬─────────────────────────────────────────┘
                 │
  ┌──────────────▼─────────────────────────────────────────┐
  │ 4. create KVM VM + vCPUs                               │
  │    load kernel image at guest_phys=0x80000 (or higher) │
  │    build zero-page + boot_params (e820 map, cmdline)   │
  │    set initial RIP to kernel entry                      │
  └──────────────┬─────────────────────────────────────────┘
                 │
  ┌──────────────▼─────────────────────────────────────────┐
  │ 5. KVM_RUN — guest kernel boots, runs /init           │
  │    VMM sits in epoll loop: handle KVM_EXIT_MMIO,       │
  │    KVM_EXIT_IO, virtio queue kicks, serial output,     │
  │    API events                                          │
  └────────────────────────────────────────────────────────┘
```

The kernel is loaded directly into guest RAM at the well-known Linux boot
protocol address. Firecracker's loader code (~500 lines of Rust) constructs
the **zeropage** (`struct boot_params`) with an e820 memory map, the kernel
command-line pointer, and the ramdisk pointer, then sets the vCPU's RIP to
the kernel entry symbol resolved from the Linux boot header. There is no
firmware in the VM, ever.

## The minimal device model

Firecracker exposes virtio devices exclusively via MMIO transport. The guest
kernel is told which MMIO addresses hold virtio devices via the kernel
command line:

```
virtio_mmio.device=4K@0xd0000000:5  \
virtio_mmio.device=4K@0xd0001000:6  \
virtio_mmio.device=4K@0xd0002000:7  \
virtio_mmio.device=4K@0xd0003000:8
```

That is the entire "device discovery protocol": no PCI bus scan, no ACPI
DSDT. The kernel's `virtio_mmio` platform driver probes these fixed addresses,
reads the magic value `0x74726976` ("virt" little-endian) at offset 0, and
instantiates the corresponding device (net, block, balloon, vsock, rng).

The back-end side is similar: Firecracker implements virtio queue processing
in Rust inside the VMM. There is no `vhost-net` kernel module and no vDPA —
the VMM itself polls the rings. This is correct because the whole point is
**isolating tenant data path from the host kernel**: if a buggy tenant
device driver can corrupt a virtio ring, the worst case is the VMM process
crashing, not the host kernel panicking.

## Jailer: defence in depth around the VMM

`jailer` is the binary that sets up the VMM's sandbox before exec-ing the
Firecracker process. It is a separate binary so that compromise of
Firecracker's runtime does not grant the jailer's privilege.

The jailer performs, in order:

1. **Namespace isolation.** Creates new mount, PID, UTS, IPC and net
   namespaces (and a new user namespace if requested), so the VMM cannot see
   the host's processes, mounts, or network.
2. **chroot.** Binds a curated directory tree (containing the Firecracker
   binary, the kernel image, the rootfs, and the API Unix socket) and
   `chroot`s into it. The VMM cannot `open("/etc/passwd")` on the host.
3. **Resource limits.** Sets `RLIMIT_NOFILE`, `RLIMIT_NPROC`, and
   `RLIMIT_FSIZE` to small numbers.
4. **cgroups v2.** Creates a cgroup for the VMM and binds the process to it.
   CPU and memory throttling happen here.
5. **seccomp-bpf filter.** Installs a BPF filter on `seccomp(2)` that allows
   a tiny allow-list (`read`, `write`, `mmap`, `ioctl`, `epoll_*`,
   `clock_gettime`, `futex`, `rt_sigreturn`, `exit`, `exit_group`, `brk`,
   and a handful more). Everything else triggers `SIGSYS`. The filter is
   checked at every syscall, so a memory-corruption exploit in the VMM cannot
   escape by issuing arbitrary syscalls.
6. **Drop privileges.** `setuid` to a per-microVM unprivileged user; clear
   all capabilities; drop the bounding set.

The combined effect: a successful VMM exploit lands in a process that has no
host filesystem view, no network, no other processes visible, no extra
privileges, and can only call a fixed list of syscalls. Even a VM escape (a
CVE in KVM itself) does not directly escalate to host compromise.

## Comparison: Firecracker vs Kata vs gVisor

| Property | Firecracker | Kata Containers | gVisor |
|----------|-------------|------------------|--------|
| Isolation boundary | Hardware (KVM) | Hardware (KVM) | Software (Go user-space kernel) |
| Guest kernel | Required (you supply a kernel image) | Required (thin guest kernel supplied by Kata) | None — host kernel is the only kernel |
| Container interface | No (raw VM, you supply rootfs) | Yes, OCI runtime (`kata-runtime`) | Yes, OCI runtime (`runsc`) |
| Typical boot time | 125 ms | 1–2 s (heavier guest) | <100 ms (no kernel boot) |
| Memory footprint per instance | ~5 MiB VMM + guest | ~30–80 MiB guest | ~10–20 MiB Sentry |
| Device model | virtio MMIO, 5 devices | Full virtio + host-driven virtiofsd | 9p / lisafs over Gofer process |
| Best for | Multi-tenant function execution (Lambda, Fargate) | "container that needs stronger isolation" | Sandbox untrusted code on shared kernel |
| Limitation | You supply the kernel — no general OS image | Heavier than runc; cold start in seconds | Some syscall incompatibilities; lower raw syscall throughput |

The strategic difference is **what is shared with the host**. gVisor shares
the host kernel's system-call surface (the Sentry intercepts syscalls and
re-implements them in Go, so the host kernel sees a heavily filtered subset
of calls); Kata and Firecracker do not — the guest kernel runs in a separate
address space and only the hypervisor (KVM) is shared. For Lambda's security
model (running customer code on a host that also runs other customers' code),
only hardware isolation was considered sufficient.

## Production use: Lambda and Fargate

Lambda's "microVM per function" architecture was the original use case. The
Lambda Worker service — the host-side software that runs on every Lambda
execution host — has a "MicroVM Manager" process that calls Firecracker's API
socket for each invoke:

1. **Cold start.** A new invoke arrives for a function with no warm sandbox.
   The Worker selects a Firecracker process from a warm pool (booted but
   idle), attaches the customer's code as a block device (via a host file),
   jumps the guest's userland into the runtime (Node, Python, Java, …), and
   runs the handler.
2. **Warm invoke.** A subsequent invoke within the keep-alive window reuses
   the running microVM.
3. **Teardown.** After idle, the microVM is killed; the jailer's cgroup and
   namespaces go with it.

The warm pool is the trick that lets Lambda advertise "125 ms cold start":
the VMMs are already booted, sitting at the `execve` boundary between the
guest's init and the runtime, and only need a kick to start running the
user's code. Without warm pooling you would pay kernel-boot time on every
cold invoke.

Fargate uses Firecracker for similar reasons: a Fargate task is a container,
but the task runs inside a Firecracker microVM, so a compromised task cannot
reach the host kernel or another tenant's task. The container abstraction is
preserved via Kata-style runtime adapters on top of Firecracker (an internal
AWS layer, not strictly Kata itself).

## Pitfalls

- **Cold-start tuning.** Memory size has a first-order effect on cold-start
  time because the kernel must zero and map pages. A 256 MiB microVM boots
  faster than a 2 GiB one. Lambda caps memory at 10 GiB but most functions
  stay small.
- **No ballooning on the hot path.** Firecracker supports virtio-balloon but
  using it during steady-state can cause guest page-fault storms when the
  balloon is deflated. Keep balloon action to idle periods.
- **One vCPU per microVM is the sweet spot.** Firecracker scales to many
  vCPUs but the vCPU thread model means each additional vCPU doubles the
  number of threads the host schedules, which can hurt density. Most Lambda
  functions run with 1–2 vCPUs.
- **Kernel image version pinning.** The kernel image is part of the
  deployment, not the VMM. Bumping the kernel image changes microVM behaviour
  more than bumping Firecracker does; pin both.

## Interview-style questions

**Why is Firecracker written in Rust?**
Memory safety in the data path: a use-after-free in the virtio ring
back-end in QEMU has historically been a goldmine for VM escape. Rust's
borrow checker eliminates the entire class of UAF/double-free/iterator
invalidation bugs at compile time. The performance cost is small (no GC, no
runtime, LLVM-optimised) and the ecosystem has the needed primitives
(`epoll`, `mmap`, ioctls via `libc` and `nix`).

**Why not just harden QEMU?**
You can, and people do (QEMU ships a seccomp filter and address-space
randomisation). But QEMU's device model includes decades of legacy — SB16
audio, NE2000 NIC, floppy controllers, SCSI controllers — each one an attack
surface. Removing them all is harder than writing fresh. The minimal subset
Firecracker ships is auditable.

**Why does Firecracker use MMIO virtio and not PCI?**
PCI bus enumeration (Config space, BAR sizing, INTx routing) is complex and
slow. MMIO transport exposes each device at a fixed address, so the guest
just probes known addresses. Boot time shrinks and the VMM has no PCI bus
model to maintain.

## Cross-references

- [KVM deep dive](./kvm.md) — the hypervisor Firecracker drives
- [Kata Containers](./kata-containers.md) — OCI-style alternative
- [gVisor](./gvisor.md) — software-only sandboxing
- [AWS Lambda](../aws/lambda.md) — production use of Firecracker
- [Hypervisors overview](./hypervisors.md) — Type 1 vs Type 2

## References

- [Firecracker GitHub repository](https://github.com/firecracker-microvm/firecracker)
- [Firecracker design document](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md)
- [Firecracker: Lightweight Virtualization for Serverless Function Workloads — Agache et al., NSDI 2020](https://www.usenix.org/conference/nsdi20/presentation/agache)
- [Firecracker security threat model](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md#threat-model)
- [Jailer source and documentation](https://github.com/firecracker-microvm/firecracker/tree/main/src/jailer)
- [AWS: Containers without constructs — Lambda runs Firecracker](https://aws.amazon.com/blogs/compute/containers-without-constructs-aws-lambda-run-firecracker/)
- [Firecracker: the Rust rewrite of AWS Lambda virtualization (AWS open source blog)](https://aws.amazon.com/blogs/opensource/why-aws-loves-rust-and-the-community-we-built-around-firecracker/)
- [virtio specification (OASIS)](https://docs.oasis-open.org/virtio/virtio/v1.2/csprd01/virtio-v1.2-csprd01.html)
- [Linux x86 boot protocol (kernel.org)](https://docs.kernel.org/arch/x86/boot.html)
- [KVM API reference](https://docs.kernel.org/virt/kvm/api.html)
