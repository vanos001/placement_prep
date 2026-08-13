# Remote Direct Memory Access (RDMA)

## Introduction

Remote Direct Memory Access (RDMA) is a technology that allows one computer to directly access the memory of another computer without involving either operating system's kernel or CPU. This kernel-bypass approach eliminates the overhead of traditional network I/O — copying data between user buffers, kernel buffers, and NIC buffers — achieving latencies as low as 1–2 microseconds and throughput exceeding 200 Gbps on modern hardware.

RDMA is the backbone of high-performance computing (HPC), AI/ML training clusters, financial trading systems, and high-performance storage fabrics. Linux has first-class RDMA support through the `rdma-core` userspace library and the in-kernel RDMA subsystem.

## RDMA vs Traditional Networking

Traditional TCP/IP networking involves multiple data copies and context switches:

```mermaid
sequenceDiagram
    participant App as Application
    participant K as Kernel
    participant NIC as NIC

    App->>K: send() syscall
    K->>K: Copy user buffer → kernel buffer
    K->>K: TCP/IP processing
    K->>NIC: DMA copy kernel buffer → NIC TX ring
    NIC->>NIC: Transmit on wire
    Note over App,NIC: Multiple copies, context switches, CPU involvement
```

RDMA eliminates these steps by allowing the NIC (RNIC) to read/write application memory directly:

```mermaid
sequenceDiagram
    participant App as Application
    participant RNIC as RNIC (RDMA NIC)

    App->>RNIC: Post work request to Send Queue
    RNIC->>RNIC: DMA directly from registered memory
    RNIC-->>RNIC: Remote NIC writes to registered memory
    RNIC->>App: Completion notification (CQ)
    Note over App,RNIC: Zero-copy, kernel-bypass, CPU offloaded
```

## Core Architecture

### Components

```mermaid
graph TB
    subgraph "User Space"
        APP["Application"]
        VERBS["libibverbs<br>(Verbs API)"]
    end
    subgraph "Kernel Space"
        RDMA_SUB["RDMA Subsystem<br>drivers/infiniband/"]
        CM["Connection Manager<br>(rdma_cm)"]
        IB_CORE["IB Core"]
    end
    subgraph "Hardware"
        RNIC["RDMA NIC<br>(HCA/RNIC)"]
        subgraph "On-NIC Resources"
            QP["Queue Pairs"]
            CQ["Completion Queues"]
            MR["Memory Regions"]
        end
    end

    APP --> VERBS
    VERBS --> RDMA_SUB
    RDMA_SUB --> IB_CORE
    RDMA_SUB --> CM
    IB_CORE --> RNIC
    CM --> RNIC
    RNIC --> QP
    RNIC --> CQ
    RNIC --> MR
```

### Queue Pairs (QP)

Every RDMA endpoint uses a **Queue Pair**, consisting of:

- **Send Queue (SQ)**: Work requests to send data or perform RDMA operations
- **Receive Queue (RQ)**: Buffers posted to receive incoming messages

A QP is the fundamental communication channel. Two endpoints each create a QP and connect them. The RNIC processes work requests from the SQ asynchronously, without CPU involvement.

### Completion Queues (CQ)

When work requests finish, the RNIC posts a **Work Completion (WC)** entry to the Completion Queue. Applications poll the CQ to determine when operations are done. A single CQ can serve multiple QPs.

### Memory Registration

Before RDMA operations can access application memory, it must be **registered** with the RNIC:

1. `ibv_reg_mr()` pins physical pages and creates a **Memory Region (MR)**
2. The RNIC receives a **lkey** (local key) for local access and **rkey** (remote key) for remote access
3. Registration establishes DMA mappings so the NIC can perform zero-copy transfers

Memory registration is expensive (involves pinning pages and IOMMU setup). Applications typically register large buffers once and reuse them.

## RDMA Operations

| Operation | Description | Use Case |
|-----------|-------------|----------|
| **SEND/RECEIVE** | Two-sided messaging; sender posts SEND, receiver posts RECEIVE | Control messages, request/response |
| **RDMA WRITE** | One-sided; write directly to remote memory without remote CPU | Data push, storage writes |
| **RDMA READ** | One-sided; read directly from remote memory | Data pull, storage reads |
| **Atomic** | Compare-and-swap or fetch-and-add on remote memory | Distributed locks, counters |

### SEND/RECEIVE Flow

```mermaid
sequenceDiagram
    participant Client
    participant C_QP as Client QP
    participant S_QP as Server QP
    participant Server

    Server->>S_QP: Post RECEIVE WR
    Client->>C_QP: Post SEND WR
    C_QP->>S_QP: Data transfer (RNIC DMA)
    S_QP->>Server: CQ completion notification
```

### RDMA WRITE Flow

```mermaid
sequenceDiagram
    participant Writer
    participant W_QP as Writer QP
    participant Remote_Memory as Remote Memory
    participant Remote_CQ as Remote CQ

    Note over Remote_Memory: rkey grants write access
    Writer->>W_QP: Post RDMA WRITE WR<br>(remote addr + rkey)
    W_QP->>Remote_Memory: Direct DMA write
    W_QP->>Writer: CQ completion (local)
    Note over Remote_Memory: Remote CPU NOT involved
```

## RDMA Transports

Linux supports three RDMA transport protocols:

### InfiniBand

- **Native RDMA transport** over dedicated fabric
- Bandwidth: SDR (2.5 Gbps) through NDR (400 Gbps) and XDR (800 Gbps)
- Subnet Manager (SM) manages routing and topology
- Lossless by design with credit-based flow control
- See [InfiniBand](../storage/infiniband.md) for detailed coverage

### RoCE (RDMA over Converged Ethernet)

- **RoCE v1**: RDMA over Ethernet at Layer 2 (no IP routing)
- **RoCE v2**: RDMA over UDP/IP at Layer 3 (routable)
- Uses standard Ethernet infrastructure with DCB/PFC for lossless behavior
- Most common RDMA transport in data centers

```bash
# Configure RoCE v2 on Linux
# Install required packages
sudo apt install rdma-core ibverbs-utils perftest

# Check RDMA devices
ibv_devices
ibv_devinfo -d mlx5_0

# Assign IP to RoCE-capable interface
sudo ip addr add 192.168.100.1/24 dev enp1s0f0
sudo ip link set enp1s0f0 up
```

### iWARP (Internet Wide Area RDMA Protocol)

- RDMA over TCP/IP
- Works over existing TCP infrastructure without special switch configuration
- Higher latency than RoCE due to TCP overhead
- Better for WAN/metro deployments

```bash
# iWARP modules
sudo modprobe iw_cxgb4    # Chelsio T4/T5/T6
sudo modprobe iw_nes       # NetEffect NE020
sudo modprobe siw          # Software iWARP (for testing)
```

## Linux RDMA Stack

```mermaid
graph TB
    subgraph "User Space (libibverbs)"
        APP["Application"]
        VERBS["ibv_* API"]
        RDMA_CM_U["rdma_cm (userspace)"]
    end
    subgraph "Kernel"
        IB_CORE["IB Core<br>drivers/infiniband/core/"]
        RDMA_CM_K["rdma_cm<br>drivers/infiniband/core/cma.c"]
        IB_UVERBS["ib_uverbs<br>(/dev/infiniband/uverbs*)"]
        subgraph "HW Drivers"
            MLX5["mlx5_ib<br>(ConnectX-4/5/6/7)"]
            MLX4["mlx4_ib<br>(ConnectX-3)"]
            BNXT["bnxt_re<br>(Broadcom)"]
            EFA["efa<br>(AWS)"]
            SIW["siw<br>(Software iWARP)"]
        end
    end
    subgraph "Hardware"
        HCA["HCA / RNIC"]
    end

    APP --> VERBS
    APP --> RDMA_CM_U
    VERBS --> IB_UVERBS
    RDMA_CM_U --> RDMA_CM_K
    IB_UVERBS --> IB_CORE
    RDMA_CM_K --> IB_CORE
    IB_CORE --> MLX5
    IB_CORE --> MLX4
    IB_CORE --> BNXT
    IB_CORE --> EFA
    IB_CORE --> SIW
    MLX5 --> HCA
    MLX4 --> HCA
```

### Key Kernel Paths

| Path | Purpose |
|------|---------|
| `drivers/infiniband/core/` | Core RDMA subsystem |
| `drivers/infiniband/core/uverbs_main.c` | Userspace verbs interface |
| `drivers/infiniband/core/cma.c` | RDMA Connection Manager |
| `drivers/infiniband/hw/mlx5/` | Mellanox ConnectX driver |
| `include/rdma/ib_verbs.h` | Core verbs header |
| `include/rdma/rdma_cm.h` | Connection Manager API |

## Configuration

### Installing RDMA Packages

```bash
# Debian/Ubuntu
sudo apt install rdma-core ibverbs-utils infiniband-diags \
    rdmacm-utils perftest opensm

# RHEL/CentOS/Fedora
sudo dnf install rdma-core libibverbs-utils infiniband-diags \
    librdmacm-utils perftest opensm

# Install MLNX_OFED (Mellanox) for latest drivers
# Download from https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/
sudo ./mlnxofedinstall --add-kernel-support
```

### Loading Kernel Modules

```bash
# Core RDMA modules
sudo modprobe ib_core
sudo modprobe ib_uverbs
sudo modprobe rdma_cm
sudo modprobe rdma_ucm
sudo modprobe ib_cm
sudo modprobe ib_umad

# For Mellanox ConnectX-4/5/6/7
sudo modprobe mlx5_core
sudo modprobe mlx5_ib

# For RoCE
sudo modprobe mlx5_core
sudo modprobe rpcrdma        # NFS over RDMA
sudo modprobe svcrdma         # NFS server over RDMA
```

### Verifying RDMA Devices

```bash
# List available RDMA devices
$ ibv_devices
    device           node GUID
    ------           ----------------
    mlx5_0           0002c90300abcdef
    mlx5_1           0002c90300abcdef

# Detailed device information
$ ibv_devinfo -d mlx5_0
hca_id: mlx5_0
        transport:                      InfiniBand (0)
        fw_ver:                         16.35.2000
        node_guid:                      0002c903:00abcdef
        sys_image_guid:                 0002c903:00abcdef
        vendor_id:                      0x02c9
        vendor_part_id:                 4119
        hw_ver:                         0x0
        phys_port_cnt:                  1
        port:   1
                state:                  PORT_ACTIVE (4)
                max_mtu:                4096 (5)
                active_mtu:             4096 (5)
                sm_lid:                 0
                port_lid:               0
                port_lmc:               0x00
                link_layer:             Ethernet

# Check RDMA link status
rdma link show
rdma link show dev mlx5_0
```

### Configuring RoCE v2

```bash
# Check current RoCE mode
sudo cma_roce_mode -d mlx5_0 -P 1

# Set RoCE mode to v2 only
sudo cma_roce_mode -d mlx5_0 -P 1 -M 2

# Configure DSCP for RoCE traffic
echo "dscp" | sudo tee /sys/class/infiniband/mlx5_0/ports/1/gid_attrs/types/0
```

### PFC (Priority Flow Control) for Lossless RoCE

```bash
# Install Linux Traffic Control utilities
sudo apt install iproute2

# Configure PFC on priority 3 (common for RoCE)
sudo mlnx_qos -i enp1s0f0 --pfc 0,0,0,1,0,0,0,0

# Set DSCP-to-priority mapping
sudo mlnx_qos -i enp1s0f0 --dscp2prio 26,3

# Verify configuration
sudo mlnx_qos -i enp1s0f0
```

## RDMA Connection Manager (rdma_cm)

The `rdma_cm` library provides a connection-oriented interface similar to sockets:

```c
/* RDMA CM client connection example */
#include <rdma/rdma_cma.h>
#include <rdma/rdma_verbs.h>

struct rdma_cm_id *conn;
struct rdma_event_channel *ec;
struct sockaddr_in addr;

/* Create event channel */
ec = rdma_create_event_channel();
rdma_create_id(ec, &conn, NULL, RDMA_PS_TCP);

/* Resolve address and route */
memset(&addr, 0, sizeof(addr));
addr.sin_family = AF_INET;
addr.sin_port = htons(7471);
inet_pton(AF_INET, "192.168.100.2", &addr.sin_addr);

rdma_resolve_addr(conn, NULL, (struct sockaddr *)&addr, 2000);
/* Wait for RDMA_CM_EVENT_ADDR_RESOLVED */

rdma_resolve_route(conn, 2000);
/* Wait for RDMA_CM_EVENT_ROUTE_RESOLVED */

/* Create QP, connect */
struct rdma_conn_param param = {};
rdma_connect(conn, &param);
/* Wait for RDMA_CM_EVENT_ESTABLISHED */
```

## Performance Benchmarking

The `perftest` suite provides standard RDMA benchmarks:

```bash
# Build perftest (usually pre-packaged)
sudo apt install perftest

# RDMA Write latency test
# Server:
ib_write_lat -d mlx5_0 -a
# Client:
ib_write_lat -d mlx5_0 192.168.100.2

# RDMA Write bandwidth test
# Server:
ib_write_bw -d mlx5_0 -a
# Client:
ib_write_bw -d mlx5_0 192.168.100.2 --report_gbits

# RDMA Read latency
ib_read_lat -d mlx5_0 -a
ib_read_lat -d mlx5_0 192.168.100.2

# SEND/RECEIVE latency
ib_send_lat -d mlx5_0 -a
ib_send_lat -d mlx5_0 192.168.100.2

# Bidirectional bandwidth
ib_write_bw -d mlx5_0 -a --bidir
ib_write_bw -d mlx5_0 192.168.100.2 --bidir --report_gbits

# Atomic operations latency
ib_atomic_lat -d mlx5_0 -a
ib_atomic_lat -d mlx5_0 192.168.100.2
```

### Sample Performance Numbers

| Operation | Latency (μs) | Bandwidth (Gbps) |
|-----------|:------------:|:-----------------:|
| RDMA Write | ~1.0–1.5 | 100–200 |
| RDMA Read | ~1.5–2.0 | 100–200 |
| SEND/RECEIVE | ~1.2–1.8 | 90–190 |
| Atomic CAS | ~1.5–2.5 | N/A |

*Values for ConnectX-6 Dx, 100 GbE RoCE v2, typical single-stream.*

## Performance Tuning

### IRQ Affinity

```bash
# Set IRQ affinity for RDMA NIC interrupts
# Distribute across NUMA-local CPUs
sudo set_irq_affinity.sh mlx5_0

# Manual IRQ affinity
for irq in $(grep mlx5 /proc/interrupts | awk '{print $1}' | tr -d ':'); do
    echo $((irq % $(nproc))) | sudo tee /proc/irq/$irq/smp_affinity_list
done
```

### Memory Tuning

```bash
# Increase locked memory limits
echo "* soft memlock unlimited" | sudo tee -a /etc/security/limits.conf
echo "* hard memlock unlimited" | sudo tee -a /etc/security/limits.conf

# Or per-user
echo "myuser soft memlock unlimited" | sudo tee -a /etc/security/limits.conf

# Verify
ulimit -l
# Should show "unlimited"

# Pin NUMA memory for RDMA buffers
numactl --cpunodebind=0 --membind=0 ./my_rdma_app
```

### Ring Buffer and Queue Depth

```bash
# Increase NIC ring buffer
sudo ethtool -G enp1s0f0 rx 4096 tx 4096

# Increase RDMA completion queue size
# Set via application or verbs API:
# ibv_create_cq(ctx, max_cqe, ...)
```

### Congestion Management (RoCE)

```bash
# Enable ECN marking
sudo mlnx_qos -i enp1s0f0 --ecn 0,0,0,1,0,0,0,0

# Configure DCQCN (Data Center QCN)
sudo mlxconfig -d mlx5_0 set LINK_TYPE_P1=2

# Monitor congestion events
sudo perfquery -a -x | grep -i congst
```

## Use Cases

### NFS over RDMA

```bash
# Server: enable NFS over RDMA
sudo modprobe svcrdma
echo "rdma 20049" | sudo tee /proc/fs/nfsd/portlist

# /etc/exports
/data/share  192.168.100.0/24(rw,sync,no_root_squash)

# Client: mount with RDMA
sudo modprobe rpcrdma
sudo mount -o rdma,port=20049 192.168.100.2:/data/share /mnt/nfs
```

### iSCSI Extensions for RDMA (iSER)

```bash
# iSER allows iSCSI to use RDMA transport
# Server (target) with LIO
targetcli
/> /iscsi create iqn.2024-01.com.example:target0
/> /iscsi/iqn.2024-01.com.example:target0/tpg1 create ib=mlx5_0

# Client (initiator)
iscsiadm -m discovery -t sendtargets -p 192.168.100.2
iscsiadm -m node -T iqn.2024-01.com.example:target0 --login
```

### Storage: NVMe over Fabrics with RDMA

See [NVMe over Fabrics](../storage/nvme-of.md) for NVMe-oF RDMA transport configuration.

## Monitoring and Debugging

```bash
# Monitor RDMA counters
rdma counter show

# Per-device statistics
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_rcv_data
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_xmit_data

# Check for errors
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_rcv_errors
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_xmit_discards

# Detailed link status
ibstat mlx5_0
ibstatus mlx5_0

# InfiniBand diagnostics
ibping -S          # Server
ibping -c 10 -L 0  # Client

# ibdiagnet - fabric diagnostics
ibdiagnet -r

# Trace RDMA operations with bpftrace
sudo bpftrace -e 'kprobe:ib_create_cq { printf("CQ created by %s\n", comm); }'

# Monitor RDMA connection events
sudo bpftrace -e 'kprobe:cma_connect_cb { printf("Connection event\n"); }'
```

## Troubleshooting

### Common Issues

**No RDMA devices found:**
```bash
# Check if modules are loaded
lsmod | grep -E "mlx5|ib_core|rdma"

# Check PCI devices
lspci | grep -i mellanox

# Reload drivers
sudo modprobe -r mlx5_ib mlx5_core && sudo modprobe mlx5_core mlx5_ib
```

**Link not active:**
```bash
# Check physical link
ibstatus

# Check cable/transceiver
ethtool -m enp1s0f0

# Verify firmware version
mlxfwmanager --query
```

**RDMA operations fail with "connection refused":**
```bash
# Check if RDMA CM service is listening
rdma_res show

# Verify IP address is assigned to RDMA-capable interface
ip addr show enp1s0f0

# Check firewall rules (RDMA CM uses standard TCP/UDP ports)
sudo iptables -L -n
```

**Memory registration failures:**
```bash
# Check locked memory limits
ulimit -l

# Increase in /etc/security/limits.conf
# user soft memlock unlimited
# user hard memlock unlimited

# Check IOMMU settings
dmesg | grep -i iommu
# If needed, disable IOMMU: intel_iommu=off in kernel cmdline
```

**Poor RoCE performance:**
```bash
# Check PFC counters
sudo mlnx_qos -i enp1s0f0
ethtool -S enp1s0f0 | grep -i pfc

# Verify no packet drops
ethtool -S enp1s0f0 | grep -i drop

# Check for pause frames
ethtool -S enp1s0f0 | grep -i pause
```

## Security Considerations

### RDMA Security Model

RDMA introduces unique security concerns because the NIC directly accesses memory:

1. **Memory Protection**: Memory regions are protected by lkey/rkey tokens. Without the remote key, an attacker cannot read or write memory.
2. **IOMMU**: Modern systems use the IOMMU (Intel VT-d / AMD-Vi) to restrict which physical memory addresses the NIC can access.
3. **Partition Keys (P_Key)**: In InfiniBand, P_Keys isolate traffic between different groups on the same fabric.
4. **RoCE Security**: Since RoCE runs over Ethernet/IP, it inherits network security concerns. Use VLANs and ACLs to restrict access.

```bash
# Enable IOMMU for RDMA protection
# Add to kernel boot parameters:
# intel_iommu=on iommu=pt

# Check IOMMU groups
ls /sys/kernel/iommu_groups/

# Verify IOMMU is active
dmesg | grep -i iommu
```

### P_Key Configuration (InfiniBand)

```bash
# List P_Keys for a port
ibstat -P 1

# Set P_Key index for a QP application
# Applications configure P_Key via ibv_modify_qp() or rdma_cm options
```

## RDMA in Container Environments

### RDMA Device Access in Containers

```bash
# Enable RDMA device passthrough with --device
sudo docker run --device /dev/infiniband/uverbs0 \
    --device /dev/infiniband/ucm0 \
    --device /dev/infiniband/umad0 \
    -v /sys/class/infiniband:/sys/class/infiniband \
    rdma-app:latest

# Using Kubernetes with RDMA device plugin
# Install the Mellanox RDMA device plugin
kubectl apply -f https://raw.githubusercontent.com/Mellanox/k8s-rdma-shared-dev-plugin/master/k8s-rdma-shared-dev-plugin-config.yaml

# Pod spec with RDMA resources:
# resources:
#   limits:
#     rdma/hca: 1
```

### RDMA in Virtual Machines

```bash
# SR-IOV for RDMA in VMs
# Enable SR-IOV on the physical NIC
sudo mlxconfig -d mlx5_0 set SRIOV_EN=1 NUM_OF_VFS=16

# Create VFs
echo 8 | sudo tee /sys/class/infiniband/mlx5_0/device/sriov_numvfs

# Assign VF to VM (libvirt)
# <hostdev mode='subsystem' type='pci'>
#   <source>
#     <address domain='0x0000' bus='0x03' slot='0x00' function='0x1'/>
#   </source>
# </hostdev>
```

## Advanced Topics

### Reliable Connected (RC) vs Unreliable Datagram (UD)

| Feature | Reliable Connected (RC) | Unreliable Datagram (UD) | Extended Reliable Connected (XRC) |
|---------|:----------------------:|:-----------------------:|:--------------------------------:|
| Delivery guarantee | Yes | No | Yes |
| Connection model | Point-to-point | Multicast-capable | Shared receive queues |
| Scalability | O(n²) connections | O(n) | O(n) |
| RDMA operations | All supported | SEND only | All supported |
| Use case | Storage, HPC | Management, multicast | Large-scale HPC |

### Shared Receive Queues (SRQ)

SRQs allow multiple QPs to share a single receive buffer pool, reducing memory consumption:

```c
/* Create a shared receive queue */
struct ibv_srq_init_attr srq_attr = {
    .attr.max_wr = 1024,
    .attr.max_sge = 1,
};
struct ibv_srq *srq = ibv_create_srq(pd, &srq_attr);

/* Post receives to SRQ */
struct ibv_recv_wr wr = {
    .wr_id = 0x1234,
    .sg_list = &sge,
    .num_sge = 1,
};
ibv_post_srq_recv(srq, &wr, &bad_wr);
```

### Extended Connection (XRC) Transport

XRC reduces the number of QPs needed in large clusters by sharing receive-side resources. In a cluster of N nodes, RC requires N×(N-1) QPs, while XRC requires only N QPs per node.

```bash
# XRC requires kernel support
# Check: ibv_devinfo | grep -i xrc
```

### Dynamically Connected Transport (DCT)

Available in ConnectX-5 and later, DCT further reduces connection state:

```c
/* Create DCT target */
struct ibv_qp_init_attr_ex attr_ex = {
    .qp_type = IBV_QPT_DRIVER,
    /* DCT-specific attributes */
};
```

## RDMA Application Programming

### Minimal RDMA SEND/RECEIVE Example

```c
/* Minimal RDMA ping-pong using libibverbs */
#include <infiniband/verbs.h>

/* Create protection domain */
struct ibv_pd *pd = ibv_alloc_pd(ctx);

/* Register memory */
char *buf = malloc(4096);
struct ibv_mr *mr = ibv_reg_mr(pd, buf, 4096,
    IBV_ACCESS_LOCAL_WRITE |
    IBV_ACCESS_REMOTE_READ |
    IBV_ACCESS_REMOTE_WRITE);

/* Create completion queue */
struct ibv_cq *cq = ibv_create_cq(ctx, 16, NULL, NULL, 0);

/* Create queue pair */
struct ibv_qp_init_attr qp_attr = {
    .send_cq = cq,
    .recv_cq = cq,
    .cap = {
        .max_send_wr = 16,
        .max_recv_wr = 16,
        .max_send_sge = 1,
        .max_recv_sge = 1,
    },
    .qp_type = IBV_QPT_RC,
};
struct ibv_qp *qp = ibv_create_qp(pd, &qp_attr);

/* Transition QP: RESET -> INIT -> RTR -> RTS */
struct ibv_qp_attr attr = {};
attr.qp_state = IBV_QPS_INIT;
attr.pkey_index = 0;
attr.port_num = 1;
attr.qp_access_flags = IBV_ACCESS_LOCAL_WRITE |
                        IBV_ACCESS_REMOTE_READ |
                        IBV_ACCESS_REMOTE_WRITE;
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);
```

### Error Handling

```bash
# Check work completion status
# ibv_wc_status values:
#   IBV_WC_SUCCESS - Operation completed successfully
#   IBV_WC_LOC_LEN_ERR - Local length error
#   IBV_WC_LOC_QP_OP_ERR - Local QP operation error
#   IBV_WC_LOC_PROT_ERR - Local protection error
#   IBV_WC_WR_FLUSH_ERR - Work request flush error
#   IBV_WC_RETRY_EXC_ERR - Retry count exceeded
#   IBV_WC_RNR_RETRY_EXC_ERR - RNR retry exceeded

# Common causes:
# - LOC_LEN_ERR: Send buffer size mismatch
# - REM_ACCESS_ERR: Wrong rkey or insufficient remote permissions
# - RETRY_EXC_ERR: Remote side not responding (connection lost)
# - RNR_RETRY_EXC_ERR: Remote receive queue empty
```

## Ecosystem and Related Projects

| Project | Description |
|---------|-------------|
| **rdma-core** | Userspace RDMA library suite (libibverbs, librdmacm) |
| **MLNX_OFED** | NVIDIA Mellanox OFED distribution with latest features |
| **perftest** | RDMA benchmarking suite (ib_write_bw, ib_read_lat, etc.) |
| **SPDK** | Storage Performance Development Kit — uses RDMA for NVMe-oF target |
| **MPI** | Message Passing Interface (OpenMPI, MVAPICH) over RDMA for HPC |
| **UCX** | Unified Communication X — transport framework for HPC and AI |
| **gRPC-RDMA** | gRPC transport over RDMA (experimental) |
| **NVMe-oF** | NVMe over Fabrics using RDMA transport |
| **NFS/RDMA** | NFS over RDMA for high-performance file serving |
| **SMB Direct** | SMB/CIFS over RDMA (Windows and ksmbd) |

## References

- Linux kernel RDMA subsystem: `drivers/infiniband/`
- `rdma-core` project: <https://github.com/linux-rdma/rdma-core>
- `libibverbs` API documentation: `man ibv_reg_mr`, `man ibv_create_qp`
- `rdma_cm` API: `man rdma_connect`, `man rdma_resolve_addr`
- OFED documentation: <https://www.openfabrics.org/>
- NVIDIA MLNX_OFED: <https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/>
- perftest suite: <https://github.com/linux-rdma/perftest>
- InfiniBand Trade Association: <https://www.infinibandta.org/>
- Red Hat RDMA Guide: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_infiniband_and_rdma_networks>
- "InfiniBand Network Architecture" by Intel Press
- DigitalOcean RDMA Explained: <https://www.digitalocean.com/community/conceptual-articles/rdma-high-performance-networking>
- VMware RDMA Basics: <https://www.vmware.com/docs/the-basics-of-remote-direct-memory-access-rdma-in-vsphere>
- UCX Framework: <https://openucx.org/>

- Linux kernel RDMA subsystem: `drivers/infiniband/`
- `rdma-core` project: <https://github.com/linux-rdma/rdma-core>
- `libibverbs` API documentation: `man ibv_reg_mr`, `man ibv_create_qp`
- `rdma_cm` API: `man rdma_connect`, `man rdma_resolve_addr`
- OFED documentation: <https://www.openfabrics.org/>
- NVIDIA MLNX_OFED: <https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/>
- perftest suite: <https://github.com/linux-rdma/perftest>
- InfiniBand Trade Association: <https://www.infinibandta.org/>
- Red Hat RDMA Guide: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_infiniband_and_rdma_networks>
- "InfiniBand Network Architecture" by Intel Press
- DigitalOcean RDMA Explained: <https://www.digitalocean.com/community/conceptual-articles/rdma-high-performance-networking>
