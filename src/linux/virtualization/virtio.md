# Virtio: Paravirtualized I/O for Virtual Machines

Virtio is the standard paravirtualization framework for I/O in virtual machines.
Instead of emulating real hardware, virtio defines an efficient guest-hypervisor
communication protocol that both sides understand natively. This chapter covers
virtio device types (net, blk, scsi), vhost, vDPA, packed virtqueues, and
performance tuning.

---

## 1. What Is Paravirtualization?

```mermaid
flowchart TB
    subgraph Emulated["Full Emulation (Slow)"]
        E_DRV["Guest Driver<br>(e.g., e1000)"] --> E_EM["QEMU Emulator<br>(full hardware model)"]
    end
    subgraph PV["Paravirtualization (Fast)"]
        P_DRV["Virtio Driver<br>(guest)"] --> P_VQ["Virtqueue<br>(shared ring)"] --> P_HYP["Hypervisor Backend"]
    end
    subgraph Direct["Passthrough (Fastest)"]
        D_DRV["Native Driver"] --> D_HW["Physical Hardware"]
    end
```

| Approach | Performance | Compatibility | Complexity |
|----------|-------------|---------------|------------|
| Full emulation | 10–30% native | Works with any OS | High (emulate hardware) |
| Paravirt (virtio) | 70–95% native | Requires virtio driver | Medium |
| Passthrough (VFIO) | ~100% native | Needs dedicated HW | High |

---

## 2. Virtqueue Architecture

### 2.1 Split Virtqueues (Traditional)

A virtqueue consists of three descriptor tables shared between guest and host:

```mermaid
flowchart LR
    subgraph Guest
        AVAIL["Available Ring<br>(guest writes)"]
    end
    subgraph Shared_Memory["Shared Memory"]
        DESC["Descriptor Table<br>(buffer pointers)"]
        USED["Used Ring<br>(host writes)"]
    end
    AVAIL -->|"buffer index"| DESC
    DESC -->|"completed buffers"| USED
    USED -->|"notification"| Guest
```

- **Descriptor Table** — Array of buffer descriptors (addr, len, flags, next)
- **Available Ring** — Guest tells host which descriptors are ready
- **Used Ring** — Host tells guest which descriptors are done

### 2.2 Packed Virtqueues (Linux 4.20+, Virtio 1.1)

Packed virtqueues merge all three tables into a single descriptor ring, improving
cache locality and reducing memory barriers.

```mermaid
flowchart LR
    subgraph Packed["Packed Virtqueue"]
        D0["Desc 0<br>avail+used"]
        D1["Desc 1<br>avail+used"]
        D2["Desc 2<br>avail+used"]
        D3["Desc 3<br>avail+used"]
    end
    D0 --> D1 --> D2 --> D3 --> D0
```

Benefits:
- **Better cache performance** — single contiguous memory region
- **Fewer memory barriers** — driver and device flags in same descriptor
- **Up to 10–20% throughput improvement** for small messages

---

## 3. Virtio Device Types

### 3.1 virtio-net — Network Device

```mermaid
flowchart LR
    subgraph Guest
        APP[Application] --> VNET[virtio-net driver]
    end
    subgraph Host
        BACKEND["TAP device / vhost-net"]
        BRIDGE["Linux Bridge / OVS"]
    end
    VNET -->|"virtqueue TX/RX"| BACKEND
    BACKEND --> BRIDGE
```

**Guest driver:**

```bash
# Linux guest — check driver
ethtool -i eth0
# driver: virtio_net

# Features negotiation
ethtool -k eth0
# tcp-segmentation-offload: on
# generic-receive-offload: on
```

**Host configuration (QEMU):**

```bash
qemu-system-x86_64 \
    -device virtio-net-pci,netdev=net0,mac=52:54:00:12:34:56 \
    -netdev tap,id=net0,script=/etc/qemu-ifup,vhost=on
```

**libvirt XML:**

```xml
<interface type='bridge'>
  <source bridge='br0'/>
  <model type='virtio'/>
  <driver name='vhost' queues='4'>
    <host mrg_rxbuf='on'/>
  </driver>
</interface>
```

### 3.2 virtio-blk — Block Device

Simple block device interface. One virtqueue per device.

```bash
qemu-system-x86_64 \
    -device virtio-blk-pci,drive=drive0 \
    -drive file=disk.qcow2,format=qcow2,if=none,id=drive0,aio=native,cache=none
```

Guest verification:

```bash
# Check virtio-blk driver
lsblk -t
# NAME   ALIGNMENT MIN-IO OPT-IO PHY-SEC LOG-SEC ROTA SCHED    RQ-SIZE
# vda           0    512      0     512      512    0 mq-deadline     256

cat /sys/block/vda/queue/scheduler
# [mq-deadline] kyber none
```

### 3.3 virtio-scsi — SCSI Device

More feature-rich than virtio-blk: supports multiple LUNs, SCSI commands,
rescan, and discard/TRIM.

```bash
qemu-system-x86_64 \
    -device virtio-scsi-pci,id=scsi0 \
    -device scsi-hd,bus=scsi0.0,drive=drive0 \
    -drive file=disk.qcow2,format=qcow2,if=none,id=drive0
```

**Comparison: virtio-blk vs virtio-scsi**

| Feature | virtio-blk | virtio-scsi |
|---------|------------|-------------|
| Multiple LUNs | One per device | Many per controller |
| SCSI commands | No | Yes (pass-through) |
| Discard/TRIM | Limited | Full |
| Multi-queue | Yes | Yes |
| Performance | Slightly faster (simple) | Slightly slower (more features) |
| Use case | Simple disk | Complex storage, multi-disk |

---

## 4. vhost — Kernel-Based Backend

### 4.1 What Is vhost?

vhost moves the virtio backend from QEMU userspace into the kernel, reducing
context switches and data copies.

```mermaid
flowchart LR
    subgraph Without["Without vhost"]
        QEMU1["QEMU process"] --> TAP1["TAP device"]
    end
    subgraph With["With vhost-net"]
        VHOST["vhost-net kernel thread"] --> TAP2["TAP device"]
    end
    Guest1 -->|virtqueue| QEMU1
    Guest2 -->|virtqueue| VHOST
```

### 4.2 vhost-net

```bash
# Enable vhost-net in QEMU
qemu-system-x86_64 \
    -device virtio-net-pci,netdev=net0 \
    -netdev tap,id=net0,vhost=on

# Verify vhost is active
lsmod | grep vhost
# vhost_net              32768  1
# vhost                  53248  1 vhost_net

# Check vhost thread
ps aux | grep vhost
# root  1234  0.5  vhost-1234-qemu
```

### 4.3 vhost-scsi

```bash
# Use vhost-scsi for SCSI target
qemu-system-x86_64 \
    -device vhost-scsi-pci,wwpn=naa.5001405888888888 \
    -object memory-backend-file,id=mem,size=4G,mem-path=/dev/hugepages,share=on \
    -numa node,memdev=mem
```

### 4.4 vhost-user

For userspace datapath (DPDK, OVS-DPDK):

```bash
# Start OVS-DPDK with vhost-user
ovs-vsctl add-port br0 vhost-user0 -- \
    set Interface vhost-user0 type=dpdkvhostuserclient \
    options:vhost-server-path=/var/run/openvswitch/vhost-user0
```

---

## 5. vDPA — Virtio Data Path Acceleration

### 5.1 What Is vDPA?

vDPA provides a hardware-accelerated virtio datapath. Hardware vendors implement
the virtio datapath in their NIC firmware while the control plane remains
software-defined.

```mermaid
flowchart TB
    subgraph Guest
        DRV[virtio-net driver]
    end
    subgraph vDPA
        VDPA[vDPA bus]
        subgraph HW["Hardware"]
            CTRL["Control plane<br>(software)"]
            DATA["Data plane<br>(hardware/firmware)"]
        end
        VDPA --> CTRL
        VDPA --> DATA
    end
    DRV -->|virtqueue| VDPA
```

### 5.2 vDPA vs SR-IOV vs vhost

| Feature | vhost | SR-IOV | vDPA |
|---------|-------|--------|------|
| Performance | High | Highest | Highest |
| Configurability | Full | Limited | Full (SW control plane) |
| Live migration | Yes | Difficult | Yes |
| Vendor lock-in | None | Some | None (virtio standard) |

### 5.3 Using vDPA

```bash
# Check vDPA devices
vdpa dev list

# Create a vDPA device
vdpa dev add mgmtdev pci/0000:03:00.0 name vdpa0

# Use with QEMU
qemu-system-x86_64 \
    -device virtio-net-pci,netdev=net0 \
    -netdev vhost-vdpa,id=net0,vhostdev=/dev/vhost-vdpa-0
```

---

## 6. Virtio Feature Negotiation

### 6.1 Feature Bits

Devices and drivers negotiate features during initialization:

| Feature | Bit | Description |
|---------|-----|-------------|
| `VIRTIO_NET_F_CSUM` | 0 | Host checksums |
| `VIRTIO_NET_F_GSO` | 6 | Generic segmentation offload |
| `VIRTIO_NET_F_MRG_RXBUF` | 15 | Merge receive buffers |
| `VIRTIO_NET_F_MTU` | 3 | Host sets MTU |
| `VIRTIO_RING_F_INDIRECT_DESC` | 28 | Indirect descriptors |
| `VIRTIO_RING_F_EVENT_IDX` | 29 | Interrupt suppression |
| `VIRTIO_F_ORDER_PLATFORM` | 36 | Platform ordering |

### 6.2 Querying Features

```bash
# QEMU monitor
(qemu) info virtio
# virtio-net: features: 0x100000000 (indirect_desc)

# Guest-side
ethtool -i eth0
cat /sys/class/net/eth0/device/features
```

---

## 7. Multi-Queue Performance

### 7.1 Multi-Queue virtio-net

```bash
# QEMU: enable multi-queue
qemu-system-x86_64 \
    -device virtio-net-pci,netdev=net0,mq=on,vectors=8 \
    -netdev tap,id=net0,script=/etc/qemu-ifup,vhost=on,queues=4

# Guest: configure multi-queue
ethtool -L eth0 combined 4
```

### 7.2 Multi-Queue virtio-blk

```bash
# QEMU
qemu-system-x86_64 \
    -device virtio-blk-pci,drive=drive0,num-queues=4 \
    -drive file=disk.qcow2,format=qcow2,if=none,id=drive0

# Guest: verify
cat /sys/block/vda/queue/nr_requests
cat /sys/block/vda/mq/*/cpu_list
```

---

## 8. Performance Tuning

### 8.1 Guest-Side Tuning

```bash
# Increase virtqueue size
echo 1024 | sudo tee /sys/module/virtio_ring/parameters/max_queue_size

# Enable busy polling
echo 50 | sudo tee /sys/class/net/eth0/napi_defer_hard_irqs

# Use XDP for fast packet processing
ip link set dev eth0 xdpgeneric pass

# Tune interrupt coalescing
ethtool -C eth0 rx-usecs 50 tx-usecs 50
```

### 8.2 Host-Side Tuning

```bash
# Enable vhost for all virtio devices
# (default in modern QEMU)

# Use io_uring for virtio-blk
qemu-system-x86_64 \
    -device virtio-blk-pci,drive=drive0,iothread=iothread0 \
    -object iothread,id=iothread0 \
    -drive file=disk.qcow2,format=qcow2,if=none,id=drive0,aio=io_uring

# Pin vhost threads
taskset -c 0-3 qemu-system-x86_64 ...
```

### 8.3 Hugepages for Virtio

```bash
# Allocate hugepages (reduces TLB misses for virtio buffers)
echo 4096 | sudo tee /proc/sys/vm/nr_hugepages

# QEMU with hugepages
qemu-system-x86_64 \
    -object memory-backend-file,id=mem,size=4G,mem-path=/dev/hugepages,share=on \
    -numa node,memdev=mem \
    ...
```

### 8.4 Benchmark Comparison

```bash
# Network throughput (iperf3)
# Emulated e1000:   ~1 Gbps
# virtio-net:       ~10 Gbps
# virtio-net+vhost: ~18 Gbps
# vDPA:             ~20 Gbps (line rate on 25G NIC)

# Disk I/O (fio)
# Emulated IDE:     ~100 MB/s
# virtio-blk:       ~2 GB/s
# virtio-blk+io_uring: ~3 GB/s
# VFIO NVMe:        ~7 GB/s (native)
```

---

## 9. Virtio in Non-Linux Guests

### 9.1 Windows

Download drivers from [Fedora VirtIO-Win](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/):

```bash
# Attach driver ISO
qemu-system-x86_64 \
    -cdrom virtio-win.iso \
    -device virtio-net-pci,netdev=net0 \
    -device virtio-blk-pci,drive=drive0
```

### 9.2 FreeBSD

FreeBSD has native virtio drivers:

```bash
# In FreeBSD guest
kldload virtio
kldload if_vtnet
kldload virtio_blk
```

---

## 10. Virtio Specification

The Virtio specification is maintained by OASIS:

| Version | Key Features |
|---------|--------------|
| 1.0 | Split virtqueues, basic devices |
| 1.1 | Packed virtqueues, VIRTIO_F_ORDER_PLATFORM |
| 1.2 | Admin virtqueue, virtio-mem, virtio-fs |

The specification defines:
- Device initialization and feature negotiation
- Virtqueue layout and operation
- Device-specific configuration (net, blk, scsi, etc.)
- Transport bindings (PCI, MMIO, CCW)

---

## 11. virtio-fs — Shared Filesystem

virtio-fs provides host-guest file sharing using FUSE on the host side and a
virtio transport. It replaces the older 9p/virtio transport with significantly
better performance.

```mermaid
flowchart LR
    subgraph Guest
        APP[Application] --> VFS[Guest VFS]
        VFS --> VFSMOD[virtiofs driver]
    end
    subgraph Host
        VFSMOD -->|"virtqueue"| FUSE[FUSE daemon]
        FUSE --> HOSTFS[Host filesystem]
    end
```

### Using virtio-fs

```bash
# Create shared directory on host
mkdir -p /tmp/shared

# Start QEMU with virtiofs
echo 2048 > /proc/sys/vm/nr_hugepages
qemu-system-x86_64 \
    -object memory-backend-file,id=mem,size=4G,mem-path=/dev/hugepages,share=on \
    -numa node,memdev=mem \
    -chardev socket,id=char0,path=/tmp/vhost-fs.sock \
    -device vhost-user-fs-pci,chardev=char0,tag=myfs \
    -numa node,memdev=mem \
    ...

# Mount in guest
mount -t virtiofs myfs /mnt/shared

# In /etc/fstab:
# myfs  /mnt/shared  virtiofs  defaults  0  0
```

### virtio-fs vs 9p vs NFS

| Feature | virtio-fs | 9p/virtio | NFS |
|---------|-----------|-----------|-----|
| Performance | Excellent | Poor | Good |
| POSIX compliance | High | Limited | High |
| mmap support | Yes | No | Yes |
| DAX support | Yes (Linux 5.15+) | No | No |
| Setup complexity | Medium | Low | Medium |
| Security | Sandboxed | Basic | Network |

DAX (Direct Access) allows guest to mmap host files directly, bypassing
the guest page cache — critical for large file access.

```bash
# Mount with DAX
cd /sys/kernel/tracing
mount -t virtiofs -o dax=always myfs /mnt/shared
```

## 12. virtio-vsock — Guest-Host Communication

virtio-vsock provides a socket-based communication channel between guest and
host without network configuration:

```mermaid
flowchart LR
    subgraph Guest
        APP_G[Application] --> VSOCK_G[vsock socket]
    end
    subgraph Host
        APP_H[Application] --> VSOCK_H[vsock socket]
    end
    VSOCK_G -->|"virtqueue"| VSOCK_H
```

### Using virtio-vsock

```bash
# QEMU: enable vhost-vsock
qemu-system-x86_64 \
    -device vhost-vsock-pci,guest-cid=3 \
    ...

# Guest: listen on vsock
socat VSOCK-LISTEN:1234,reuseaddr,fork EXEC:/bin/bash

# Host: connect to guest
socat VSOCK-CONNECT:3:1234 -

# CID (Context ID) identifies the guest
# CID 2 = host, CID 3+ = guests

# Guest side (C code)
# #include <linux/vm_sockets.h>
# int fd = socket(AF_VSOCK, SOCK_STREAM, 0);
# struct sockaddr_vm addr = {
#     .svm_family = AF_VSOCK,
#     .svm_cid = VMADDR_CID_HOST,
#     .svm_port = 1234,
# };
# connect(fd, (struct sockaddr *)&addr, sizeof(addr));
```

### Use Cases for virtio-vsock

- **Guest management** — SSH, serial console without network
- **File transfer** — fast guest-host file copy
- **Agent communication** — cloud-init, qemu-guest-agent
- **Development** — debug servers without network forwarding

## 13. virtio-gpu — Virtual GPU

virtio-gpu provides GPU access for guests, supporting both 2D and 3D rendering:

```bash
# QEMU: enable virtio-gpu
qemu-system-x86_64 \
    -device virtio-gpu-pci \
    -display gtk,gl=on \
    ...

# For VirGL (3D acceleration via host GPU)
qemu-system-x86_64 \
    -device virtio-gpu-pci \
    -display gtk,gl=on \
    -spice gl=on,rendernode=/dev/dri/renderD128 \
    ...

# Guest: verify virtio-gpu
ls /dev/dri/
# card0  renderD128

glinfo | head -5
# Vendor:   Red Hat, Inc.
# Renderer: virgl
# Version:  4.5 (Core Profile)
```

## 14. Virtio Security Considerations

### Attack Surface

```mermaid
flowchart TB
    subgraph Guest
        DRV[Virtio Driver] --> VQ[Virtqueue]
    end
    subgraph Host
        BACKEND[Backend Process] --> HOSTMEM[Host Memory]
    end
    VQ -->|"shared memory"| BACKEND
    
    subgraph Risks
        R1["Malicious guest driver"]
        R2["Shared memory corruption"]
        R3["Virtqueue descriptor manipulation"]
        R4["Resource exhaustion"]
    end
```

### Security Best Practices

```bash
# 1. Use vhost (kernel backend) — smaller attack surface than QEMU
# vhost-net, vhost-scsi process requests in kernel

# 2. Memory isolation — IOMMU for virtio
qemu-system-x86_64 \
    -device virtio-net-pci,netdev=net0,disable-legacy=on,iommu_platform=on \
    ...

# 3. Input validation — backends must validate all guest-provided
#    descriptor chains, lengths, and flags

# 4. Resource limits — prevent guest from exhausting host resources
#    Limit virtqueue size, number of requests, memory usage

# 5. Seccomp sandboxing — restrict backend system calls
# QEMU uses seccomp by default: -sandbox on

# 6. Separate backends — run different device backends in different
#    processes/user IDs for isolation
```

### CVE Mitigations

```bash
# Common virtio vulnerability patterns:
# - Out-of-bounds access via malicious descriptors
# - Integer overflow in descriptor chain parsing
# - Use-after-free in virtqueue management
# - Information leak via uninitialized memory in used ring

# Mitigations:
# - Kernel: hardening patches (KASAN, KCSAN, stack protector)
# - QEMU: sandbox mode, -sandbox on
# - IOMMU: DMA remapping prevents guest DMA attacks
# - Disable legacy: disable-legacy=on (forces modern virtio)
```

## 15. Virtio Transport Bindings

### PCI Transport (Most Common)

```bash
# virtio PCI devices appear in lspci
lspci | grep -i virtio
# 00:03.0 Ethernet controller: Red Hat, Inc. Virtio network device
# 00:04.0 SCSI storage controller: Red Hat, Inc. Virtio SCSI
# 00:05.0 Unclassified device: Red Hat, Inc. Virtio filesystem

# PCI configuration
lspci -v -s 00:03.0
# Capabilities: [98] MSI-X: Enable+ Count=5

# PCI feature bits
cat /sys/bus/pci/devices/0000:00:03.0/features
# Shows negotiated feature bits in hex
```

### MMIO Transport (Embedded/ARM)

```bash
# Used for embedded and ARM systems without PCI
# Device Tree describes virtio-mmio devices

# QEMU with virtio-mmio
qemu-system-aarch64 \
    -machine virt \
    -device virtio-net-device,netdev=net0 \
    -device virtio-blk-device,drive=drive0 \
    ...

# Device tree entry:
# virtio_mmio@a000000 {
#     compatible = "virtio,mmio";
#     reg = <0x0a000000 0x200>;
#     interrupts = <0 16 1>;
# };
```

### CCW Transport (s390x)

```bash
# Channel Command Word (CCW) transport for IBM Z/s390x
qemu-system-s390x \
    -device virtio-net-ccw,netdev=net0 \
    ...
```

## 16. Virtio in the Cloud

```bash
# Major cloud providers use virtio:
# - AWS: Enhanced Networking (ENA) + virtio
# - GCP: virtio-net, virtio-scsi
# - Azure: Hyper-V devices (similar concepts)
# - OpenStack: virtio for KVM guests

# Verify virtio in cloud VM
lspci | grep -i virtio
# On AWS: also check for ENA (enhanced network adapter)
ethtool -i eth0
# driver: vif_net on xen / virtio_net on KVM
```

## Further Reading

- [Virtio Specification 1.2 — OASIS](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)
- [Linux Virtio Documentation — docs.kernel.org](https://docs.kernel.org/driver-api/virtio/index.html)
- [vhost Documentation — docs.kernel.org](https://docs.kernel.org/virt/kvm/vhost.html)
- [vDPA Documentation — docs.kernel.org](https://docs.kernel.org/networking/device_drivers/ethernet/mellanox/mlx5/vdpa.html)
- [Packed Virtqueues — LWN.net](https://lwn.net/Articles/773778/)
- [virtio-net driver — docs.kernel.org](https://docs.kernel.org/networking/device_drivers/net/virtio_net.html)
- [QEMU Virtio Devices](https://www.qemu.org/docs/master/system/devices/virtio.html)
- [DPDK vhost-user](https://doc.dpdk.org/guides/prog_guide/vhost_lib.html)
- [OASIS Virtio TC](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=virtio)
