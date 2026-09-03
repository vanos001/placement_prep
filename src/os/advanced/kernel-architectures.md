# Kernel Architectures

Monolithic kernels (Linux, FreeBSD) place all services — filesystems, drivers, networking — in a single address space with full hardware access. While performant, this design creates enormous attack surfaces and makes formal verification intractable. Alternative kernel architectures restructure where functionality lives: in separate address spaces (microkernels), in application libraries (exokernels/unikernels), or distributed across cores (multikernels). Understanding these designs is essential for reasoning about isolation, performance trade-offs, and the engineering constraints that shaped modern systems.

## Monolithic Kernels — The Baseline

Linux, FreeBSD, and Windows NT are monolithic: every kernel subsystem runs in ring 0 with shared address space and direct hardware access. System calls cross a single boundary via `syscall`/`sysenter` instructions, and inter-subsystem communication uses direct function calls. Linux mitigates the resulting stability risks with loadable kernel modules (LKM), `lockdep` for deadlock detection, and address sanitizer (KASAN) for memory bugs, but a single buggy driver can corrupt any kernel data structure.

The performance advantage comes from avoiding IPC overhead. A `read()` system call in Linux goes: VFS → filesystem → block layer → driver → hardware, all via function calls with pointer passing. No message serialization, no context switches between protection domains.

## Microkernels

Microkernels move all non-essential services — filesystems, device drivers, network stacks — into user-space servers. Only scheduling, IPC, and address space management remain in the kernel. The canonical examples are MINIX 3, QNX Neutrino, and L4 family kernels (L4Ka::Pistachio, Fiasco.OC).

The key mechanism is **IPC as the fundamental primitive**. In the L4 microkernel family, IPC maps directly to register-level message passing with a single `l4_ipc()` system call that atomically switches threads and transfers message registers. This is dramatically faster than the Mach microkernel's approach of copying messages through port rights.

```
┌─────────────────────────────────────────────────────┐
│                   User Space                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ FS Server│  │Net Server│  │Dev Driver│          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │                │
│       └──────────────┴──────────────┘                │
│                      │ IPC                           │
├──────────────────────┼──────────────────────────────┤
│            Microkernel (ring 0)                       │
│         IPC │ Scheduler │ AS Management              │
└──────────────────────┼──────────────────────────────┘
                       │                               │
                   Hardware                             │
```

### QNX Neutrino — Production Microkernel

QNX achieves hard real-time guarantees with a microkernel under 100 KB. Its `MsgSend`/`MsgReceive`/`MsgReply` operations implement **zero-copy message passing** where the kernel re-maps the sender's buffer into the receiver's address space without copying. QNX has been used in automotive (GM, Audi), medical devices, and industrial control systems where deterministic response times and fault isolation are mandatory.

### The L4 Family and Minimalism

Jochen Liedtke's L4 microkernel (1995) proved that microkernel IPC could be fast — 10x faster than Mach — by minimizing abstraction. L4Ka::Pistachio implements IPC in ~20 instructions on x86. The key insight: **minimize kernel code path length, not the number of abstractions**. The seL4 kernel (see below) extended this with formal verification.

## Exokernels

Exokernels (MIT, 1995) take the opposite approach from microkernels: instead of abstracting hardware away, they **expose hardware resources directly to applications** and multiplex at the lowest level. The kernel's only job is to securely multiplex CPU, memory, and disk — not to provide abstractions like files or sockets.

Applications implement their own OS abstractions as **library operating systems (libOS)** linked directly into the application. A database can implement a custom buffer cache that knows about its access patterns, rather than suffering through the kernel's generic page cache.

```
Traditional:  App → System Call → Kernel Abstraction → Hardware
Exokernel:   App + libOS → Secure Binding → Hardware
```

Aegis (1995) and XOS (2000) demonstrated that exokernels could match or beat monolithic kernel performance for specific workloads because the libOS eliminated cross-abstraction overhead. However, the lack of standardized abstractions made application portability difficult, and the approach never achieved mainstream adoption.

## Unikernels

Unikernels compile the application and only the required OS components into a single, specialized machine image that runs directly on a hypervisor (Xen, KVM) or bare metal. There is no POSIX layer, no shell, no multi-process support — only what the application needs. Examples include MirageOS (OCaml), IncludeOS (C++), and Rumprun.

```
┌───────────────────────┐
│  Application Code     │
├───────────────────────┤
│  Required LibOS Only  │  ← no unused drivers, no shell
│  (network, libc stub) │
├───────────────────────┤
│  Minimal Hypervisor   │
└───────────────────────┘
  Image size: often < 1 MB
  Boot time:  milliseconds
  Attack surface: minimal
```

MirageOS compiles OCaml applications into Xen unikernels. A DNS server unikernel might be 1.2 MB with ~5 ms boot time. The security advantage is significant: there is no shell to escape to, no unused network stack to exploit. Docker uses unikernel principles in its `linuxkit` initiative for minimal container base images.

The trade-off: no fork/exec, no multi-process debugging, limited ecosystem. Unikernels excel for single-purpose cloud functions and network appliances, not general-purpose computing.

## Multikernel — Barrelfish

Barrelfish (ETH Zurich / Microsoft Research, 2009) treats a multicore machine as a **distributed system**. Rather than sharing kernel data structures protected by locks, each core runs its own independent kernel instance with its own scheduler, memory allocator, and device driver. Inter-core communication uses explicit message passing — the same abstractions used in distributed systems.

```
Core 0          Core 1          Core N
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Local    │   │ Local    │   │ Local    │
│ Scheduler│   │ Scheduler│   │ Scheduler│
│ Local MM │   │ Local MM │   │ Local MM │
├──────────┤   ├──────────┤   ├──────────┤
│ Message  │◄─►│ Message  │◄─►│ Message  │
│  Pass    │   │  Pass    │   │  Pass    │
└──────────┘   └──────────┘   └──────────┘
     │                               │
     └──────── Network-on-Chip ──────┘
```

The motivation is cache coherence scalability. As core counts grow (64, 128, 256+), hardware cache coherence protocols (MESI, MOESI) become bottlenecks. Barrelfish's message-passing model avoids shared-writer contention entirely. The research demonstrated that for core counts above ~32, message-passing outperforms shared-memory locking for many kernel workloads. However, the programming model is significantly more complex, and no mainstream OS has adopted this approach yet.

## seL4 — Formally Verified Microkernel

seL4 (NICTA/UNSW, now HENSOLDT Cyber) is a L4-family microkernel that was the **first general-purpose OS kernel with a machine-checked mathematical proof of implementation correctness** (2009). The proof covers: implementation adherence to specification (functional correctness), absence of uninitialized memory reads, absence of data type violations, and absence of certain information flows.

The seL4 capability system provides fine-grained access control. Every kernel object (page tables, IPC endpoints, interrupts) is accessed through unforgeable capabilities stored in a CSpace (capability space). Capabilities confer specific rights — read, write, grant — and cannot be forged because they are indexed, not pointer-based.

```
Capability Layout in CSpace:
┌──────┬──────┬──────┬──────┐
│ CSpace │ CPTR │Rights│ Type │
├──────┼──────┼──────┼──────┤
│       │  0x4 │ R/W  │ Page │
│       │  0x8 │ Grant│ EP   │
│       │ 0x10 │ R    │ PT   │
└──────┴──────┴──────┴──────┘
```

Performance: seL4 IPC is ~100 ns on ARM Cortex-A53, ~150 ns on x86-64. This is within 2-3x of a Linux system call, despite full isolation. seL4 is used in defense systems (HENSOLDT Cyber), aerospace, and is being evaluated for automotive use under ISO 26262.

## Library OS — Brief Deep Dive

A Library OS (libOS) links the operating system functionality directly into the application as a user-space library. Rather than making system calls, the application calls libOS functions that manage resources. **Graphene** (later renamed **Gramine**), a user-space library OS designed to run unmodified Linux applications inside Intel SGX enclaves, and gVisor's Sentry use libOS principles to provide compatibility layers. In the exokernel model, the libOS *is* the OS; in container runtimes like gVisor, the libOS translates POSIX semantics to host kernel primitives, providing a compatibility and isolation layer without full virtualization. (Note: GrapheneOS is a separate, unrelated project — a hardened Android mobile OS — and should not be confused with Graphene/Gramine.)

## Comparison

| Feature | Monolithic (Linux) | Microkernel (seL4) | Exokernel | Unikernel (MirageOS) | Multikernel (Barrelfish) |
|---------|-------------------|---------------------|-----------|----------------------|--------------------------|
| Kernel size | ~30M LoC | ~10K LoC | ~5K LoC | Minimal (app-only) | Per-core small |
| IPC mechanism | Function calls | Kernel IPC | Secure bindings | N/A (single process) | Message passing |
| Isolation | None (kernel-wide) | Full (per-server) | Per-application | Hypervisor-level | Per-core |
| Formal verification | No | Yes (seL4) | No | No | No |
| Performance | Best (raw) | ~2-3x syscall cost | Application-optimal | Near-bare-metal | Scales with cores |
| Ecosystem | Massive | Limited | Academic | Growing (cloud) | Academic |
| Use cases | General purpose | Safety-critical | Research | Serverless, IoT | Manycore research |

## Interview Questions

1. **"Why doesn't Linux use a microkernel?"** Answer hint: Linux's monolithic design maximizes syscall throughput by avoiding IPC between protection domains. The LKM system provides modularity without the IPC cost. Torvalds' 1992 Tanenbaum-Torvalds debate centered on this: microkernels of that era (Mach) were 2-10x slower. Modern L4 microkernels narrowed the gap, but Linux's ecosystem lock-in makes migration impractical.

2. **"When would you choose a unikernel over a container?"** Answer hint: Unikernels eliminate the host OS kernel attack surface and reduce image size by 10-100x. Choose unikernels for single-purpose network functions (DNS, TLS termination, API gateways) where boot speed and minimal attack surface matter. Choose containers when you need the full POSIX ecosystem, multi-process support, and standard tooling.

3. **"What is the fundamental insight of the Barrelfish multikernel?"** Answer hint: That cache coherence doesn't scale to 100+ cores for kernel data structures, so treat the machine as a distributed system with message passing between core-local kernels. This trades programming complexity for scalability.

4. **"How does seL4's capability system prevent privilege escalation?"** Answer hint: Capabilities are unforgeable indices into a CSpace, not raw pointers. Even with a memory corruption bug, an attacker cannot fabricate a valid capability to access protected objects. The formal proof guarantees that the implementation enforces capability access control.

## References
- Liedtke, J. "On Micro-Kernel Construction." SOSP 1995.
- Engler et al. "Exokernel: An Operating System Architecture for Application-Level Resource Management." SOSP 1995.
- Baumann et al. "The Multikernel: A New OS Architecture for Scalable Multicore Systems." SOSP 2009.
- Klein et al. "seL4: Formal Verification of an OS Kernel." SOSP 2009.
- Madhavapeddy et al. "Unikernels: Library Operating Systems for the Cloud." ASPLOS 2013.
