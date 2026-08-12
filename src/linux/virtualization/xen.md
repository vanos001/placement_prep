# Xen Hypervisor

## Introduction

Xen is a Type-1 bare-metal hypervisor that has been a cornerstone of server virtualization since its inception at the University of Cambridge in 2003. It pioneered paravirtualization on x86 — a technique where the guest operating system is modified to cooperate with the hypervisor, achieving high performance without hardware virtualization extensions.

Xen's architecture is distinct from KVM: rather than turning the host OS into a hypervisor, Xen runs as a thin layer between the hardware and all operating systems, including the management domain (dom0). This design has made it the hypervisor of choice for major cloud providers including AWS (which uses a customized Xen for EC2).

## Architecture Overview

```mermaid
flowchart TB
    subgraph Xen_Hypervisor["Xen Hypervisor"]
        SCHED[Scheduler]
        MEM[Memory Manager]
        EVT[Event Channels]
        HYPER[Hypercall Interface]
    end
    subgraph dom0___Management_Domain["dom0 - Management Domain"]
        D0_LINUX["Linux Kernel<br>Modified"]
        D0_TOOLS["Xen Toolstack<br>xl / libxl / libvirt"]
        D0_BACKEND["Backend Drivers<br>netback, blkback"]
        D0_STOR["Storage / Network"]
    end
    subgraph domU___Guest_Domains["domU - Guest Domains"]
        U1["Guest 1<br>PV or HVM"]
        U2["Guest 2<br>PV or HVM"]
        U3["Guest 3<br>PVH"]
    end
    subgraph Hardware
        CPU[CPUs]
        RAM[Memory]
        NIC[Network]
        DISK[Storage]
    end

    D0_LINUX --> HYPER
    D0_TOOLS --> HYPER
    U1 -->|hypercalls| HYPER
    U2 -->|hypercalls| HYPER
    U3 -->|hypercalls| HYPER
    HYPER --> SCHED
    HYPER --> MEM
    HYPER --> EVT
    SCHED --> CPU
    MEM --> RAM
    D0_BACKEND -->|grant tables| U1
    D0_BACKEND -->|grant tables| U2
    D0_STOR --> NIC
    D0_STOR --> DISK
```

### Domain Types

| Domain | Description | Privileges |
|--------|-------------|------------|
| **dom0** | Initial domain, boots first | Full hardware access, runs toolstack |
| **domU** | Unprivileged guest domains | No direct hardware access |
| **driver domain** | Specialized domU for device drivers | Runs backend drivers for other domains |
| **stubdomain** | Minimal domain per HVM guest | Runs device model (QEMU) in isolation |

## Paravirtualization (PV)

Xen's original approach modifies the guest OS to replace privileged instructions with hypercalls. This avoids the overhead of trapping and emulating privileged operations.

### Hypercall Mechanism

```c
/* Xen hypercall ABI on x86_64 */
static inline long HYPERVISOR_memory_op(int cmd, void *arg) {
    long ret;
    register long r10 asm("r10") = 0;
    register long r8  asm("r8")  = 0;
    asm volatile(
        "syscall"
        : "=a"(ret)
        : "0"(__HYPERVISOR_memory_op),
          "D"(cmd), "S"(arg),
          "r"(r10), "r"(r8)
        : "rcx", "r11", "memory");
    return ret;
}

/* Common hypercalls:
 * __HYPERVISOR_memory_op     — memory management
 * __HYPERVISOR_mmu_update    — page table updates
 * __HYPERVISOR_set_trap_table — exception handlers
 * __HYPERVISOR_console_io    — console I/O
 * __HYPERVISOR_event_channel_op — event channels
 * __HYPERVISOR_grant_table_op   — shared memory
 * __HYPERVISOR_sched_op     — scheduler operations
 */
```

### PV Guest Boot Sequence

```mermaid
sequenceDiagram
    participant Xen
    participant dom0
    participant PV_Guest

    Xen->>dom0: Boot dom0 first
    dom0->>dom0: Load Xen toolstack
    dom0->>Xen: Create domU (HYPERVISOR_domain_create)
    dom0->>Xen: Allocate memory (HYPERVISOR_memory_op)
    dom0->>Xen: Set up page tables (HYPERVISOR_mmu_update)
    dom0->>Xen: Register vCPU (HYPERVISOR_vcpu_op)
    dom0->>Xen: Inject start info (HYPERVISOR_start_info)
    dom0->>Xen: Unpause domain (HYPERVISOR_sched_op)
    Xen->>PV_Guest: Begin execution
    PV_Guest->>PV_Guest: Read start_info page
    PV_Guest->>PV_Guest: Initialize PV drivers
    PV_Guest->>Xen: Register event channel
    PV_Guest->>dom0: Connect to backend drivers
```

### PV Frontend/Backend Model

```mermaid
flowchart LR
    subgraph domU__PV_Guest["domU (PV Guest)"]
        FE_NET["netfront<br>Network Frontend"]
        FE_BLK["blkfront<br>Block Frontend"]
        FE_FB["fbfront<br>Framebuffer Frontend"]
    end
    subgraph Xen_Hypervisor["Xen Hypervisor"]
        GT["Grant Tables<br>Shared Memory"]
        EC["Event Channels<br>Notifications"]
    end
    subgraph dom0__Backend["dom0 (Backend)"]
        BE_NET["netback<br>Network Backend"]
        BE_BLK["blkback<br>Block Backend"]
        BE_FB["fbbackend<br>Framebuffer Backend"]
    end

    FE_NET <-->|grant table + event channel| BE_NET
    FE_BLK <-->|grant table + event channel| BE_BLK
    FE_FB <-->|grant table + event channel| BE_FB
```

## Hardware Virtual Machine (HVM)

HVM mode runs unmodified operating systems (including Windows) by leveraging hardware-assisted virtualization (VT-x/AMD-V). HVM guests require a device model (QEMU) to emulate hardware.

```bash
# HVM guest configuration (xl)
cat > hvm.cfg << 'EOF'
name = "hvm-guest"
type = "hvm"
memory = 2048
vcpus = 4
disk = ['file:/var/lib/xen/images/disk.qcow2,xvda,w']
vif = ['bridge=xenbr0']
boot = "cd"
cdrom = "/var/lib/xen/images/install.iso"
vnc = 1
vnclisten = "0.0.0.0"
serial = "pty"
EOF

xl create hvm.cfg
xl list
# Name                    ID  Mem  VCPUs  State  Time(s)
# Domain-0                 0  4096  4     r-----  1234.5
# hvm-guest                1  2048  4     -b----  56.7
```

### HVM with PV Drivers (PVHVM)

HVM guests can use PV drivers for better I/O performance:

```bash
# Linux HVM guest with PV drivers
# Install xen-guest-tools in the guest
# The guest automatically uses:
# - netfront/netback instead of emulated e1000
# - blkfront/blkback instead of emulated IDE
# - PV timer instead of emulated PIT
```

## dom0 and domU

### dom0 (Domain Zero)

dom0 is the privileged management domain that boots first and has full hardware access:

```bash
# dom0 responsibilities:
# 1. Runs the Xen toolstack (xl, libxl)
# 2. Provides backend drivers for domU I/O
# 3. Manages physical device access
# 4. Controls domain lifecycle

# xl — command-line management tool
xl list                    # List domains
xl info                    # Xen hypervisor info
xl top                     # Real-time domain stats
xl create vm.cfg           # Create domain
xl destroy vm-name         # Force-destroy domain
xl pause vm-name           # Pause domain
xl unpause vm-name         # Unpause domain
xl save vm-name /tmp/save  # Save domain state
xl restore /tmp/save       # Restore domain
xl migrate vm-name dest    # Live migration
xl console vm-name         # Attach to console
xl dmesg                   # Xen hypervisor log
```

### domU (Unprivileged Domain)

```bash
# domU has no direct hardware access
# All I/O goes through frontend → grant table → event channel → backend

# Inside a PV domU, check Xen features
cat /proc/xen/capabilities
# control_d

# Check Xen version
xl version
# Xen version 4.17.0

# Xenstore (shared configuration database)
xenstore-list /
# console
# device
# vm
# backend
# lib
```

## Xenstore

Xenstore is a hierarchical configuration database shared between domains. It's used for:
- Device configuration (frontend ↔ backend negotiation)
- Domain metadata
- Feature flags

```mermaid
flowchart TB
    subgraph Xenstore_Tree["Xenstore Tree"]
        ROOT["/"]
        LOCAL["/local"]
        DOMAIN["/local/domain"]
        D0["/local/domain/0"]
        D1["/local/domain/1"]
        D1_VM["/local/domain/1/vm"]
        D1_DEVICE["/local/domain/1/device"]
        BACKEND["/local/domain/0/backend"]
        BE_VBD["/local/domain/0/backend/vbd"]
        BE_VIF["/local/domain/0/backend/vif"]
    end
    ROOT --> LOCAL
    LOCAL --> DOMAIN
    DOMAIN --> D0
    DOMAIN --> D1
    D1 --> D1_VM
    D1 --> D1_DEVICE
    D0 --> BACKEND
    BACKEND --> BE_VBD
    BACKEND --> BE_VIF
```

```bash
# Xenstore operations
xenstore-list /local/domain/1
# console
# cpu
# device
# memory
# vm
# name

xenstore-read /local/domain/1/name
# hvm-guest

xenstore-read /local/domain/1/vm
# /vm/a1b2c3d4-...

# Write a value (requires appropriate permissions)
xenstore-write /local/domain/1/data/mykey "myvalue"

# Watch for changes
xenstore-watch /local/domain/1/device/vif/0/state

# Device state negotiation via xenstore:
# Frontend sets state → Backend reads → Backend sets state → Frontend reads
xenstore-read /local/domain/1/device/vbd/768/state
# 4 (Connected)
```

### Grant Tables

Grant tables provide secure shared memory between domains:

```c
/* Grant table reference — dom0 shares a page with domU */
struct gnttab_map_grant_ref {
    uint64_t host_addr;      /* Host virtual address */
    uint32_t flags;          /* GNTMAP_host_map, etc. */
    grant_ref_t ref;         /* Grant reference number */
    domid_t dom;             /* Domain ID */
    int16_t status;          /* GNTST_okay on success */
    uint64_t dev_bus_addr;   /* Device bus address (for DMA) */
};

/* Flow:
 * 1. domU grants access to a page: GNTTABOP_grant_access
 * 2. dom0 maps the page: GNTTABOP_map_grant_ref
 * 3. Both can now read/write the shared page
 * 4. Cleanup: GNTTABOP_unmap_grant_ref
 */
```

### Event Channels

Event channels are the Xen equivalent of inter-processor interrupts (IPIs):

```c
/* Event channel operations */
struct evtchn_bind_interdomain {
    domid_t remote_dom;
    evtchn_port_t remote_port;
    evtchn_port_t local_port;  /* Output */
};

/* Flow:
 * 1. domU allocates event channel: EVTCHNOP_alloc_unbound
 * 2. dom0 binds to it: EVTCHNOP_bind_interdomain
 * 3. domU sends event: EVTCHNOP_send
 * 4. dom0 receives via registered callback
 */
```

## Credit Scheduler

The Credit scheduler is Xen's default CPU scheduler. It's a proportional-share scheduler that distributes CPU time fairly among domains.

### How It Works

```mermaid
flowchart TB
    subgraph Credit_Scheduler["Credit Scheduler"]
        POOL["Credit Pool<br>Global CPU credits"]
        D0_C["dom0: weight=512<br>credits=200"]
        D1_C["domU1: weight=256<br>credits=100"]
        D2_C["domU2: weight=256<br>credits=50"]
    end
    subgraph States
        BOOST["BOOST<br>Recently received I/O"]
        UNDER["UNDER<br>Has credits remaining"]
        OVER["OVER<br>Credits exhausted"]
    end
    POOL --> D0_C
    POOL --> D1_C
    POOL --> D2_C
    D0_C --> BOOST
    D1_C --> UNDER
    D2_C --> OVER
```

**Scheduler states:**
- **BOOST** — Domain recently received an event (I/O completion). Gets priority scheduling.
- **UNDER** — Domain still has credits. Can run but yields to BOOST domains.
- **OVER** — Domain has exhausted its credits. Gets lowest priority.

```bash
# View scheduler configuration
xl sched-credit -d 0
# Name: Domain-0
# Weight: 512
# Cap: 0 (unlimited)

# Set domain weight (relative share of CPU)
xl sched-credit -d hvm-guest -w 256

# Cap CPU usage (percentage of one physical CPU)
xl sched-credit -d hvm-guest -c 50  # 50% of one CPU

# List all domains with scheduler info
xl sched-credit -a
```

### Other Schedulers

| Scheduler | Algorithm | Use Case |
|-----------|-----------|----------|
| **Credit** | Proportional-share | General purpose (default) |
| **Credit2** | Improved Credit | Better NUMA awareness |
| **RTDS** | Real-time deferrable server | Real-time workloads |
| **null** | No scheduling | Testing only |

## PVH (Paravirtualized HVM)

PVH combines the best of PV and HVM:

```mermaid
flowchart LR
    subgraph PV_Guest["PV Guest"]
        PV_K[PV Kernel] --> PV_HYPER[Hypercalls]
        PV_K --> PV_PV[PV Drivers]
    end
    subgraph HVM_Guest["HVM Guest"]
        HVM_K[Unmodified Kernel] --> HVM_EMUL[Emulated Devices]
        HVM_K --> HVM_PV[PV Drivers]
    end
    subgraph PVH_Guest["PVH Guest"]
        PVH_K[PV-aware Kernel] --> PVH_HYPER[Hypercalls]
        PVH_K --> PVH_PV[PV Drivers]
        PVH_K --> PVH_HVM["HVM Hardware<br>VT-x/AMD-V"]
    end
```

**PVH advantages:**
- Uses hardware virtualization (VT-x/AMD-V) for CPU and memory
- Uses PV drivers for I/O (no QEMU device model needed)
- No BIOS/UEFI emulation required
- Simpler and faster than HVM
- Smaller attack surface (no QEMU)

```bash
# PVH guest configuration
cat > pvh.cfg << 'EOF'
name = "pvh-guest"
type = "pvh"
memory = 1024
vcpus = 2
kernel = "/boot/vmlinuz-6.1-xen"
ramdisk = "/boot/initramfs-6.1-xen.img"
extra = "root=/dev/xvda console=hvc0"
disk = ['file:/var/lib/xen/images/disk.raw,xvda,w']
vif = ['bridge=xenbr0']
EOF

xl create pvh.cfg
```

## Live Migration

Xen supports live migration of running domains:

```bash
# Live migrate a domain to another host
xl migrate hvm-guest destination-host

# With SSH tunneling
xl migrate hvm-guest destination-host --ssh=/usr/bin/ssh

# Migration flow:
# 1. Pre-copy: iterate memory pages, send dirty pages
# 2. Stop-and-copy: briefly pause domain, send remaining pages
# 3. Resume on destination
# Typical downtime: 50-500ms
```

```mermaid
sequenceDiagram
    participant Source as Source Host
    participant Dest as Destination Host
    
    Source->>Source: Pause domain briefly
    Source->>Dest: Send domain metadata
    loop Pre-copy iterations
        Source->>Dest: Send memory pages
        Source->>Source: Track dirty pages
    end
    Source->>Source: Stop domain (final pause)
    Source->>Dest: Send remaining dirty pages
    Source->>Dest: Send device state
    Dest->>Dest: Resume domain
    Source->>Source: Destroy old domain
```

## Security Features

### FLASK (Xen Security Module)

```bash
# FLASK provides mandatory access control for Xen
# Similar to SELinux policies for the hypervisor

# Example policy rules:
# allow dom0 domU:create
# allow domU dom0:device_access { vbd vif }
# deny domU domU:interdomain_communication
```

### Stub Domains

```bash
# HVM guests run QEMU for device emulation
# By default, QEMU runs in dom0 (security risk)
# Stub domains run QEMU in a separate, minimal domU

# Enable stub domains
xl create hvm.cfg -F  # Force stub domain
# Now QEMU runs in an isolated stub domain
# Even if QEMU is compromised, dom0 is protected
```

## Xen vs KVM

| Aspect | Xen | KVM |
|--------|-----|-----|
| Architecture | Standalone hypervisor | Linux kernel module |
| dom0 | Required management domain | Host OS is the management domain |
| PV support | Native | Via virtio |
| HVM support | Via VT-x/AMD-V + QEMU | Via VT-x/AMD-V + QEMU |
| PVH | ✅ | N/A |
| Security model | dom0/domU separation | Linux namespaces/cgroups |
| Use cases | Cloud (AWS), security-critical | General purpose, cloud (GCP) |
| Community | Xen Project (Linux Foundation) | Linux kernel community |

## References

1. Barham, P., et al. (2003). "Xen and the Art of Virtualization." *SOSP '03*.
2. Xen Project Documentation. [https://xenproject.org/documentation/](https://xenproject.org/documentation/)
3. Chisnall, D. (2007). *The Definitive Guide to the Xen Hypervisor*. Prentice Hall.
4. Xen Source Code. [https://xenbits.xen.org/gitweb/?p=xen.git](https://xenbits.xen.org/gitweb/?p=xen.git)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Xen Project Wiki](https://wiki.xenproject.org/)
- [Xen Documentation](https://xenproject.org/documentation/)
- [xl(1) Man Page](https://xenbits.xen.org/docs/4.17-testing/man/xl.1.html)
- [AWS and Xen](https://aws.amazon.com/ec2/faqs/)
- [Xen Security Advisory Process](https://xenbits.xen.org/xsa/)

## Xen on ARM

Xen supports ARM architectures (ARMv7 and ARMv8/AArch64), where it leverages hardware virtualization extensions (ARM Virtualization Host Extensions, or VHE):

```bash
# Xen on ARM64 uses VHE (ARMv8.1+)
# The hypervisor runs at EL2 (Exception Level 2)
# dom0 and domU run at EL1 (Exception Level 1)

# Key differences from x86:
# - No QEMU device model required (PV I/O only)
# - Uses GICv3/GICv4 for interrupt virtualization
# - SMMU (System MMU) for DMA isolation
# - No BIOS/UEFI — uses Device Tree or ACPI
# - dom0 is typically a Linux or FreeBSD kernel

# ARM64 Xen dom0 configuration (Device Tree):
# xen,xen {
#     compatible = "xen,xen";
#     reg = <0x0 0x40000000 0x0 0x20000>;
#     interrupts = <1 15 0xf08>;
# };
```

### ARM Virtualization Features

| Feature | Description |
|---------|-------------|
| VHE (Virtualization Host Extensions) | Efficient hypervisor context switching |
| GICv3/GICv4 | Interrupt controller virtualization |
| SMMU | DMA remapping and isolation |
| Stage-2 page tables | Hardware-assisted memory virtualization |
| PSCI | Power State Coordination Interface for CPU lifecycle |

## Xen Disaggregation

Xen's security model allows disaggregating system components into separate domains:

```mermaid
flowchart TB
    subgraph "Monolithic dom0 (Traditional)"
        D0_NET["Network Stack"]
        D0_BLK["Block I/O"]
        D0_USB["USB"]
        D0_GPU["GPU"]
        D0_TOOL["Toolstack"]
    end
    subgraph "Disaggregated (Security-focused)"
        NETDOM["Network Domain<br>runs netback"]
        BLKDOM["Block Domain<br>runs blkback"]
        USBDOM["USB Domain<br>runs USB backend"]
        STUB["Stub Domain<br>per HVM guest"]
        TOOLDOM["Toolstack Domain<br>minimal privileges"]
    end
    direction TB
    NETDOM --> D0_NET
    BLKDOM --> D0_BLK
```

### Driver Domains

```bash
# Create a network driver domain
xl create netdom.cfg
# netdom.cfg:
# name = "netdom"
# type = "PV"
# vcpus = 2
# memory = 512
# disk = ['phy:/dev/vg/netdom,xvda,w']
# vif = ['bridge=xenbr0']

# Assign physical NIC to the driver domain
xl pci-assignable-add 0000:03:00.0
xl pci-attach netdom 0000:03:00.0

# Other domains now use netdom as their network backend
# instead of dom0
```

## Credit2 Scheduler

Credit2 is an improved version of the Credit scheduler with better NUMA awareness:

```bash
# Switch to Credit2 scheduler
xl sched credit2

# Set domain weight
xl sched-credit2 -d domain-name -w 256

# Credit2 improvements over Credit:
# - Better NUMA node locality
# - Per-CPU run queues (less lock contention)
# - More fair CPU distribution
# - Improved handling of overcommitted scenarios
```

## Xen Security Advisories (XSAs)

Xen has a formal security advisory process:

```bash
# Check current XSAs
# https://xenbits.xen.org/xsa/

# Apply XSA patches
# Patches are released as git commits on the Xen stable branch
git clone https://xenbits.xen.org/git-http/xen.git
cd xen
git checkout stable-4.17
# Apply XSA patches (e.g., XSA-444)
git log --oneline | grep XSA

# Check running Xen version for vulnerabilities
xl info | grep xen_version
# xen_version : 4.17.0

# Subscribe to xen-announce mailing list for XSA notifications
# https://lists.xenproject.org/
```

## Xen vs KVM: Detailed Comparison

| Aspect | Xen | KVM |
|--------|-----|-----|
| Architecture | Standalone hypervisor | Linux kernel module |
| dom0 | Required management domain | Host OS is the management domain |
| PV support | Native | Via virtio |
| HVM support | Via VT-x/AMD-V + QEMU | Via VT-x/AMD-V + QEMU |
| PVH | ✅ | N/A |
| Security model | dom0/domU separation | Linux namespaces/cgroups |
| Use cases | Cloud (AWS), security-critical | General purpose, cloud (GCP) |
| Community | Xen Project (Linux Foundation) | Linux kernel community |
| ARM support | Yes (VHE) | Yes (VHE) |
| Live migration | ✅ (mature) | ✅ (mature) |
| Nested virtualization | Limited | Yes |
| Device passthrough | PCI passthrough | VFIO |
| Memory | Balloon, PoD, vNUMA | Balloon, KSM, vNUMA |

## Xen and IOMMU (VT-d/AMD-Vi)

Xen uses IOMMU for safe device passthrough to guest domains:

```bash
# Enable IOMMU in Xen
# Add to Xen hypervisor command line:
iommu=1

# Check IOMMU groups
xl dmesg | grep -i iommu

# Passthrough a PCI device to a domU
# 1. Find the device's BDF (Bus:Device.Function)
lspci | grep -i nvidia
# 03:00.0 VGA compatible controller: NVIDIA Corporation ...

# 2. Hide the device from dom0
xl pci-assignable-add 0000:03:00.0

# 3. Add to domU configuration
# In vm.cfg:
pci = ['0000:03:00.0']

# 4. Create the domain with device passthrough
xl create vm.cfg

# Inside the domU, the device appears as if directly attached
lspci  # Shows the NVIDIA GPU

# IOMMU groups ensure that devices in the same group
# must be passed through together (they share IOMMU context)
```

### IOMMU Safety

```bash
# IOMMU provides:
# - DMA remapping: prevents guests from accessing arbitrary physical memory
# - Interrupt remapping: prevents interrupt injection attacks
# - Device isolation: each device gets its own DMA address space

# Without IOMMU, a malicious guest could DMA into dom0 memory
# IOMMU is REQUIRED for safe device passthrough

# Check if IOMMU is active
dmesg | grep -i 'DMAR\|IOMMU'
# DMAR: IOMMU enabled
```

## Xenstore Watch Mechanism

Xenstore provides a watch/notify mechanism for monitoring configuration changes:

```c
/* Watch for device state changes */
/* Used by frontend drivers to detect backend readiness */

/* Frontend creates a watch on its device state: */
/* xenstore-watch /local/domain/<domid>/device/vif/0/state */

/* State transitions:
 * 0: Unknown
 * 1: Initialising (backend created)
 * 2: InitWait (backend waiting)
 * 3: Initialised (frontend created)
 * 4: Connected (both sides ready)
 * 5: Closing (frontend closing)
 * 6: Closed (frontend closed)
 * 7: Reconfiguring
 * 8: Reconfigured
 */
```

```bash
# Monitor xenstore changes in real-time
xenstore-watch /local/domain/1/device/vif/0/state

# Watch all changes under a path
xenstore-watch -n /local/domain/1/device/
```

## Xen Memory Management

### Balloon Driver

```bash
# The balloon driver adjusts domain memory at runtime

# Inflate balloon (give memory back to hypervisor)
xl mem-set domain-name 512

# Deflate balloon (give more memory to domain)
xl mem-set domain-name 2048

# Check current memory
xl list
# Name                    ID  Mem  VCPUs  State  Time(s)
# Domain-0                 0  4096  4     r-----  1234.5
# hvm-guest                1  2048  4     -b----  56.7

# Memory can also be adjusted via xenstore
xenstore-write /local/domain/1/memory/target 2048
```

### PoD (Populate on Demand)

```bash
# PoD allows domains to claim more memory than initially allocated
# Memory is allocated on first access (similar to overcommit)

# In domain config:
memory = 2048
maxmem = 4096  # Can grow up to 4GB

# The hypervisor tracks which pages are actually used
# Unused pages can be reclaimed by the balloon driver
```

## Related Topics

- [Virtualization Overview](./overview.md) — virtualization types and comparison
- [KVM Internals](./kvm.md) — alternative kernel-based virtualization
- [QEMU](./qemu.md) — device emulation used with Xen HVM
- [Container Overview](../containers/overview.md) — alternative isolation mechanism


