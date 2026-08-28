# Unikernels and Library OSes — the Single-Address-Space Machine

A unikernel is a machine image in which the application and exactly the OS code it uses are compiled (or linked) into a single address space that boots directly on a hypervisor or bare metal. There is no kernel boundary to cross, no second process to schedule, no shell to escape into. The idea descends straight from the exokernel libOS line — ExOS was already a library operating system in 1995 (see [exokernels](./exokernels.md)) — but the modern systems changed the premise: instead of an exokernel underneath, the hypervisor itself provides the hardware multiplexing, and the libOS owns everything above it. This page is a mechanism-level tour of four systems (MirageOS, IncludeOS, rump kernels, Unikraft), what actually happens at boot, how images get built down to tens of pages of memory, and where the security-surface argument genuinely holds and where it does not.

## Why single address space changes the OS

Removing the process model removes most of what a classical kernel does:

- **No syscall boundary.** Application → network stack is a function call (often inlined by LTO). The cost basis for a packet path drops from several traps to zero traps; the remaining costs are memory and the NIC.
- **No fork/exec.** Image construction replaces process creation. State that a POSIX system inherits through `fork` (open files, credentials, sockets) is instead *compile-time* configuration — a unikernel boots already "launched."
- **Protection shifts to one of two places.** Either the language runtime (MirageOS: OCaml's type system and GC make unsafe memory access unrepresentable) or the address space itself (C-based systems like IncludeOS/Unikraft rely on the hypervisor boundary being the only protection domain — one bug in the image is game over *inside* the VM, but is still contained by the VM).
- **The boot image is the OS ABI.** What the hypervisor loads defines everything: entry point, boot-parameter page, memory map, paravirtualized device rings.

```text
POSIX VM                          Unikernel VM
+----------------------------+    +----------------------------+
| app  | app  | shell | sshd |    |        application         |
+------+------+------+------+    +----------------------------+
| libc | libc | libc  | libc |    |  libOS: only used code     |
+------+------+------+------+    |  (net + fs + drivers, LTO) |
| kernel (one shared copy)    |    +----------------------------+
| syscall boundary everywhere |    |  no boundary: calls inline |
+----------------------------+    +----------------------------+
        ^ |                                   ^ |
        v | traps + context switches          v | hypercall / virtio only
   hypervisor                          hypervisor
```

## Four systems, four answers

| System | Language / base | What it links | Primary host targets | Distinctive mechanism |
|--------|-----------------|---------------|----------------------|-----------------------|
| MirageOS | OCaml | Typed OCaml closure of the app + OCaml net/fs stacks | Xen PV, KVM/QEMU, solo5 targets | Whole-image type safety; config-as-code in OCaml |
| IncludeOS | C++ | C++ runtime + minimal net stack | QEMU/KVM (x86-64, ARM64) | Service binaries with tiny boot; liveupdate-friendly design |
| rump kernels | NetBSD C | *Real NetBSD kernel components* as libraries | POSIX process, Xen, KVM | Kernel code reused unmodified via composable interfaces ("anykernel") |
| Unikraft | C (+ posix syscalls) | Composable "micro-library" cores built by a config system | linuxu, KVM (x86_64/arm64), Xen, Firecracker | Kconfig + preprocessing + LTO: per-app specialization, adaptive pluggability |

Notes worth making in an interview: rump kernels are the strongest evidence that kernel code *can* be consumed as a library — the NetBSD approach ("anykernel") lets the same file-system driver run in-kernel, in userspace as an rump process, or inside a unikernel, and the NetBSD project documents rump-based testing/automated-fuzzing uses for kernel drivers. Unikraft is the current research-grade synthesis (EuroSys '21): it models OS functionality as fine-grained, Kconfig-selectable micro-libraries and exploits dead-code elimination and LTO so hard that image sizes and boot times become design outputs rather than afterthoughts.

## Boot protocols — what the hypervisor actually loads

A unikernel is just a bootable binary whose "firmware contract" is a hypervisor protocol:

```text
Xen PV boot                KVM / QEMU boot             Firecracker microVM
---------------            ------------------          -------------------
kernel image ELF           multiboot / -kernel         kernel ELF (Linux-style)
  + xen start_info page      + bzImage-style stub        + serial console
  + grant tables             + virtio-mmio/-pci          + virtio-mmio devices
  + xenbus ring              + PVH entry (hvm_start_info)
unikernel runs 32-bit ->   32->64-bit handoff, page    minimal loader: no ACPI
64-bit, hypercall page     tables built by the guest   (delegation to host)
mapped, rings registered   then stacks virtio on top   boot in tens of ms
```

Three concrete contracts dominate:

1. **Xen paravirtualized boot.** The guest finds a `start_info` structure (its own PFN layout, store/console rings), maps the hypercall page, and thereafter talks to the hypervisor via hypercalls and event channels. MirageOS and Unikraft's Xen platform both speak this; drivers are split drivers with a backend in dom0 or a driver domain.
2. **Linux-boot-alike / PVH.** KVM targets follow the Linux boot protocol shape (and PVH's `hvm_start_info`): the loader provides a memory map and entry, the guest builds its own page tables — trivial when you are the only address space. Firecracker strips this to a serial port and virtio-mmio devices, which is why unikernels on Firecracker boot in tens of milliseconds.
3. **linuxu / POSIX process.** Unikraft's `linuxu` platform and rump kernels can run the "unikernel" as a plain userspace process on Linux, using standard syscalls instead of a hypervisor — the library-OS discipline without a VM boundary. This is the cheapest development loop and the sharpest reminder that "unikernel" is an *image format*, not a hardware feature.

## Devices without a kernel: three driver stories

A unikernel still must move packets and blocks, and each system picks a different driver story:

- **MirageOS** speaks Xen split-driver protocols (netfront/blockfront) against a backend domain, plus solo5-style lean targets — devices are paravirtualized rings, not hardware.
- **Unikraft** supports both virtual devices (virtio) and, increasingly, direct hardware via its driver set; because everything is a micro-library, a data-plane build can swap virtio-net for a DPDK-class polled NIC path inside the same image (the kernel-bypass mechanics are those of [DPDK internals](./dpdk.md)).
- **rump kernels** reuse the actual NetBSD driver code, so exotic hardware support appears for free wherever the NetBSD driver exists — the trade is that the linked surface includes that driver's kernel-grade complexity.

## The build pipeline is the product

Unikraft's EuroSys '21 contribution is largely a *build-time* claim: an OS as a set of micro-libraries, each with Kconfig fragments, compiled with LTO and garbage-collected sections so the image contains only reachable code. MirageOS achieves a similar closure differently — the OCaml compiler links only the transitively referenced modules of a typed language. The demo at the bottom of this page reproduces that reachability computation deterministically. The pipeline shape:

```text
app source + config (Kconfig / opam)
        |  dependency resolution (menuconfig / package solver)
        v
micro-library selection:  [lwip|own-stack|...]

Unikraft layout (illustrative):
- configuration: per-library options prune code paths at preprocess time
- compilation:   -ffunction-sections/-fdata-sections, then --gc-sections
- LTO:           cross-library inlining (e.g., socket call into app logic)
- image:         single ELF; platform bootstrap + libOS + app, one address space
```

The measurable consequences (per the papers and project docs): unikernels frequently land in the low-megabyte image range with sub-50-millisecond boots — both are *derived* numbers, consequences of eliminating unreachable code and interpreters of unused abstractions.

## The security-surface debate, stated precisely

The ASPLOS '13 MirageOS paper argued that by minimizing the trusted computing base to the application's own type-checked closure — no shell, no unused daemons, memory safety from the type system — the exploitable surface collapses. That claim is true *for the code that is absent* and for memory-safe languages. The counter-evidence is equally real:

- **Linking a real kernel keeps a kernel's surface.** The EuroSys '20 study "A Linux in unikernel clothing" (Kuo, Williams, Koller, Mohan) built a unikernel around Linux Kernel Library code and demonstrated that the resulting images inherit a large attack surface — on the order of a million lines of kernel C — and ran exploit-class experiments against it. "Unikernel packaging" of unmodified kernel C does not buy Mirage-style minimality.
- **Single address space concentrates damage.** Without intra-image isolation, one memory-safety bug in a C libOS (Unikraft/IncludeOS territory) is a full VM compromise; MirageOS's answer is language safety, not partitioning.
- **What remains true:** the *hypervisor* boundary still bounds blast radius, images expose no interactive shell or packet-filter-bypassing services by construction, and patch surface shrinks to the linked set. The defensible summary: unikernels trade breadth of surface for concentration of it, and the trade pays only when the linked code is small or memory-safe.

## Deployment tradeoffs in 2026 terms

| Dimension | Unikernel reality | Practical consequence |
|-----------|-------------------|------------------------|
| Boot time | Tens of ms on Firecracker/KVM | Serverless-style per-request VMs become viable (compare [Firecracker microVMs](../../cloud/virtualization/firecracker.md)) |
| Density | 1000s of images/host (few MB each) | More tenants per host than full VMs; no kernel shared between tenants |
| Observability | No SSH, no gdb-by-default, no /proc | Debugging = guest console + tracing baked in at build; tooling gap vs. containers |
| Compatibility | No fork/exec; some syscalls absent | Porting effort concentrates in build, not code, for Unikraft/rump; stricter for MirageOS (OCaml-only) |
| Updates | Rebuild + reboot the whole image | Immutable-infra fits; hot-patching does not |
| Ecosystem | Drivers/protocols limited to linked sets | Kernel-bypass and virtio cover the common NIC/storage cases |

The container comparison is the one interviewers actually ask: containers share a host kernel and carry full syscall surface per tenant; unikernels each carry their own (minimal) kernel and expose nothing to neighbors but the hypervisor interface. Kata-style pods ([kata containers](../../cloud/virtualization/kata-containers.md)) restore per-tenant VM isolation but keep the entire guest Linux — the unikernel removes precisely that guest bulk. MirageOS targets and the Xen/KVM support in [Xen](../../linux/virtualization/xen.md) and [KVM](../../linux/virtualization/kvm.md) are the concrete host-side anchors.

## Interview questions

1. **"Why is a unikernel not just a statically linked binary?"** Because it must satisfy a hypervisor boot contract: provide entry-point and memory-map handling, drive paravirtualized devices without kernel help, and often build its own page tables. The "static binary" is the artifact; the boot protocol and libOS are the substance.
2. **"How do rump kernels reuse kernel code safely?"** The anykernel architecture factors NetBSD kernel components behind composable interfaces so the *same* driver code runs in-kernel, in a userspace rump process, or in a unikernel — enabling syscall-fuzzing and driver testing outside the kernel without code forks.
3. **"Where exactly does the unikernel security argument fail?"** When the image links a large C code base (the Linux-in-unikernel-clothing result: ~million-line surface inherited from LKL), and whenever single-address-space confinement means any C memory-safety bug is VM-level. It holds where linked code is small and/or memory-safe (MirageOS-style typed closures).
4. **"What replaces fork/exec in a unikernel world?"** Compile-time image construction plus supervisor restart. Concurrency comes from threads/continuations inside the single address space; scaling out is hypervisor instantiation, which is why boot time substitutes for process-creation time.
5. **"You need TLS termination at 100 Gbps for one tenant — which libOS choice and why?"** A C-based Unikraft image with a polled NIC path avoids syscall and interrupt overhead and can be size-tuned; a MirageOS image buys type-safe protocol code but with GC pauses and OCaml throughput ceilings. The deciding variables are language runtime cost vs. memory-safety requirements, not 'unikernel vs. not.'

## Worked model — image construction as reachability

Unikraft's GC-sections + LTO and MirageOS's closure compilation reduce to one computation: keep exactly the objects transitively reachable from boot roots. The model below links a miniature libOS deterministically and reports the elimination.

```python
# Dead-code elimination over a miniature libOS: only what the application
# transitively references gets linked into the unikernel image.
# (models the effect Unikraft achieves with LTO/GC-sections and MirageOS
# achieves by compiling the OCaml closure of the program)
OBJECTS = {                      # name: (size_bytes, dependencies)
    "app.main":        (1200, ["net.socket", "time.sleep", "app.handler"]),
    "app.handler":     (600,  ["crypto.sha256", "net.socket"]),
    "net.socket":      (4800, ["net.ipv4", "net.udp"]),
    "net.ipv4":        (9600, ["net.nic"]),
    "net.udp":         (5200, ["net.ipv4"]),
    "net.tcp":         (14000, ["net.ipv4"]),       # unused: app is UDP-only
    "net.nic":         (7600, ["plat.dma"]),
    "plat.dma":        (3400, ["plat.cpu_start"]),
    "plat.cpu_start":  (900,  []),
    "crypto.sha256":   (2600, []),
    "time.sleep":      (300,  ["plat.cpu_start"]),
    "fs.vfs":          (11000, ["fs.blkdev"]),      # unused: no storage
    "fs.blkdev":       (6400, ["plat.dma"]),
    "proc.fork":       (9800, ["plat.cpu_start"]),  # unused: single address space
    "posix.printf":    (800,  []),
}

def link_image(roots):
    seen = []
    stack = list(roots)
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.append(n)
            stack.extend(reversed(OBJECTS[n][1]))    # deterministic order
    return sorted(seen)

roots = ["plat.cpu_start", "app.main"]
kept = link_image(roots)
dropped = [n for n in OBJECTS if n not in kept]
total = sum(s for s, _ in OBJECTS.values())
retained = sum(OBJECTS[n][0] for n in kept)
print("linked-in objects (deterministic DFS from roots):")
for n in kept:
    deps = OBJECTS[n][1]
    print(f"  {n:16s} {OBJECTS[n][0]:6d} B  deps: {', '.join(deps) if deps else '(none)'}")
print(f"retained: {len(kept)}/{len(OBJECTS)} objects, {retained} bytes")
print(f"total   : {len(OBJECTS)} objects, {total} bytes")
print(f"eliminated: {total - retained} bytes ({100*(total-retained)/total:.1f}% smaller)")
print("dropped :", ", ".join(sorted(dropped)))
```

Real output:

```text
linked-in objects (deterministic DFS from roots):
  app.handler         600 B  deps: crypto.sha256, net.socket
  app.main           1200 B  deps: net.socket, time.sleep, app.handler
  crypto.sha256      2600 B  deps: (none)
  net.ipv4           9600 B  deps: net.nic
  net.nic            7600 B  deps: plat.dma
  net.socket         4800 B  deps: net.ipv4, net.udp
  net.udp            5200 B  deps: net.ipv4
  plat.cpu_start      900 B  deps: (none)
  plat.dma           3400 B  deps: plat.cpu_start
  time.sleep          300 B  deps: plat.cpu_start
retained: 10/15 objects, 36200 bytes
total   : 15 objects, 78200 bytes
eliminated: 42000 bytes (53.7% smaller)
dropped : fs.blkdev, fs.vfs, net.tcp, posix.printf, proc.fork
```

The dropped set is the entire point: `net.tcp` (UDP-only app), `fs.*` (diskless network appliance), `proc.fork` (no processes), `posix.printf` (console discipline). Every byte dropped is simultaneously image size, attack surface, and boot work — which is why build systems, not boot code, are the core of modern unikernel engineering.

## References

1. A. Madhavapeddy, R. Mortier, C. Rotsos, D. Scott, B. Singh, T. Gazagnaire, S. Smith, S. Hand, J. Crowcroft, "Unikernels: Library Operating Systems for the Cloud," ASPLOS '13. DOI: [10.1145/2451116.2451167](https://doi.org/10.1145/2451116.2451167) (Crossref-verified author list and venue).
2. S. Kuenzer, V.-A. Bădoiu, H. Lefeuvre, et al., "Unikraft: Fast, Specialized Unikernels the Easy Way," EuroSys '21. DOI: [10.1145/3447786.3456248](https://doi.org/10.1145/3447786.3456248) (Crossref-verified; note: EuroSys, not USENIX ATC).
3. H.-C. Kuo, K. Williams, R. Koller, S. Mohan, "A Linux in unikernel clothing," EuroSys '20. DOI: [10.1145/3342195.3387526](https://doi.org/10.1145/3342195.3387526) (Crossref-verified; the attack-surface counter-evidence).
4. MirageOS project site (official): <https://mirage.io/> (HTTP 200).
5. Unikraft documentation (official): <https://unikraft.org/> (HTTP 200).
6. IncludeOS project site (official): <https://www.includeos.org/> (HTTP 200).
7. NetBSD Wiki, rump kernel pages (official project wiki; the former rumpkernel.org domain currently serves unrelated content, so it is not cited): <https://wiki.netbsd.org/rumpkernel/> (HTTP 200).
