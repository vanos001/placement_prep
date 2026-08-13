# Namespaces

## Overview

**Namespaces** are a Linux kernel feature that partitions kernel resources such that one set of processes sees one set of resources while another set of processes sees a different set. Namespaces are the fundamental isolation mechanism behind containers — they make a process believe it has its own isolated instance of the system.

## Motivation

Without namespaces, all processes share:
- The same process ID space (can see each other)
- The same network stack (same IP addresses, ports)
- The same filesystem mount tree
- The same hostname
- The same user ID space

This means Process A can see, signal, and interfere with Process B. Namespaces provide isolation so each group of processes has its own "view" of the system.

```
Without namespaces:
  Process 1 (PID 100) ←── can see ──→ Process 2 (PID 200)
  Both share: network, mounts, hostname, IPC, users

With namespaces:
  Namespace A:                Namespace B:
  Process 1 (PID 1)          Process 2 (PID 1)
  IP: 10.0.1.1               IP: 10.0.2.1
  Hostname: web               Hostname: db
  Mount: /var/www             Mount: /var/lib/mysql
  ←── completely isolated ──→
```

## Namespace Types

```
┌──────────────────────────────────────────────────────────────┐
│              Linux Namespace Types                            │
│                                                              │
│  ┌──────────┐  What's isolated                               │
│  │ PID      │  Process IDs — container sees PID 1 as init    │
│  ├──────────┤                                                │
│  │ Network  │  Network stack — IP, routes, ports, interfaces │
│  ├──────────┤                                                │
│  │ Mount    │  Filesystem mount points                       │
│  ├──────────┤                                                │
│  │ UTS      │  Hostname and domain name                      │
│  ├──────────┤                                                │
│  │ IPC      │  Inter-process communication (semaphores, etc.)│
│  ├──────────┤                                                │
│  │ User     │  User and group IDs (UID/GID mapping)         │
│  ├──────────┤                                                │
│  │ Cgroup   │  Cgroup root directory view                    │
│  ├──────────┤                                                │
│  │ Time     │  System clocks (Linux 5.6+)                    │
│  └──────────┘                                                │
└──────────────────────────────────────────────────────────────┘
```

### PID Namespace

```
Host PID namespace:
  PID 1: systemd
  PID 234: container runtime
  PID 567: container process (host sees this)

Container PID namespace:
  PID 1: container init process (container sees this)
  PID 2: application
  PID 3: worker

Mapping:
  Host PID 567 = Container PID 1 (same process!)
  Host PID 568 = Container PID 2
  Host PID 569 = Container PID 3

Container processes can't see or signal host processes.
Host can see and manage container processes via their host PIDs.
```

```bash
# Create PID namespace
unshare --pid --fork --mount-proc bash

# Inside namespace:
ps aux
# PID 1 is bash (init process in this namespace)
# Can't see host processes!

# View process namespaces
ls -la /proc/$$/ns/
# lrwxrwxrwx 1 root root 0 ... cgroup -> 'cgroup:[4026531835]'
# lrwxrwxrwx 1 root root 0 ... ipc -> 'ipc:[4026531839]'
# lrwxrwxrwx 1 root root 0 ... mnt -> 'mnt:[4026531840]'
# lrwxrwxrwx 1 root root 0 ... net -> 'net:[4026531969]'
# lrwxrwxrwx 1 root root 0 ... pid -> 'pid:[4026531836]'
# lrwxrwxrwx 1 root root 0 ... user -> 'user:[4026531837]'
# lrwxrwxrwx 1 root root 0 ... uts -> 'uts:[4026531838]'
```

### Network Namespace

```
Host Network:
  eth0: 192.168.1.100
  docker0: 172.17.0.1 (bridge)

Container A Network:          Container B Network:
  eth0: 10.0.1.2               eth0: 10.0.2.2
  lo: 127.0.0.1                lo: 127.0.0.1
  Default GW: 10.0.1.1         Default GW: 10.0.2.1

Each container has its own:
  - IP addresses
  - Routing tables
  - Firewall rules (iptables)
  - Network interfaces
  - Port space (both can use port 80!)
```

```bash
# Create network namespace
sudo ip netns add mynet

# View interfaces in namespace
sudo ip netns exec mynet ip addr
# Only loopback (lo) — isolated!

# Create veth pair (virtual ethernet)
sudo ip link add veth0 type veth peer name veth1
sudo ip link set veth1 netns mynet

# Configure
sudo ip addr add 10.0.1.1/24 dev veth0
sudo ip link set veth0 up
sudo ip netns exec mynet ip addr add 10.0.1.2/24 dev veth1
sudo ip netns exec mynet ip link set veth1 up

# Test connectivity
sudo ip netns exec mynet ping 10.0.1.1
```

```
Network Namespace Architecture:

┌─────────────────────────────────────────────────┐
│  Host Network Namespace                          │
│                                                  │
│  ┌──────┐    ┌──────────┐    ┌───────────┐      │
│  │ eth0 │    │ docker0  │    │  veth0    │      │
│  │ .100 │    │ 172.17.1 │    │ 10.0.1.1  │      │
│  └──┬───┘    └────┬─────┘    └─────┬─────┘      │
│     │             │                │             │
│     └───── bridge ┘                │             │
│                                    │ veth pair   │
│  ┌─────────────────────────────────┼───────────┐ │
│  │ Container Network Namespace     │           │ │
│  │                                 ▼           │ │
│  │  ┌──────────┐  ┌───────────┐               │ │
│  │  │   lo     │  │  veth1    │               │ │
│  │  │ 127.0.0.1│  │ 10.0.1.2  │               │ │
│  │  └──────────┘  └───────────┘               │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Mount Namespace

```
Host mounts:
  /dev/sda1 on /
  /dev/sda2 on /home
  NFS on /data

Container mounts (isolated view):
  overlay on / (container root filesystem)
  /dev/sda2 on /home (if explicitly mounted)
  proc on /proc (container-specific proc)
  tmpfs on /tmp

Container can't see host's /home, /data, or other mounts
unless explicitly bind-mounted.
```

```bash
# Create mount namespace
unshare --mount bash

# Mounts in this namespace don't affect host
mount -t tmpfs tmpfs /mnt
# Only visible in this namespace

# View mount namespace
cat /proc/self/mountinfo
```

### User Namespace

```
Host UID space:
  root (0), alice (1000), bob (1001)

Container user namespace:
  Container root (0) → maps to host UID 100000 (unprivileged!)
  Container user 1000 → maps to host UID 101000

This means container "root" is NOT host root!
Even if container root is compromised, it's unprivileged on host.
```

```bash
# Create user namespace
unshare --user --map-root-user bash

# Inside: appears as root
id
# uid=0(root) gid=0(root)

# But on host: unprivileged user
# cat /proc/<pid>/status | grep Uid
# Uid: 100000  100000  100000  100000

# UID mapping
cat /proc/self/uid_map
#          0       1000      65536
# Container UID 0 → Host UID 1000, range 65536
```

### UTS Namespace

```bash
# Isolate hostname
unshare --uts bash

# Change hostname (only affects this namespace)
hostname my-container
hostname
# my-container

# Host still has its original hostname
```

### IPC Namespace

```bash
# Isolate IPC resources (shared memory, semaphores, message queues)
unshare --ipc bash

# IPC resources created here are not visible on host
ipcmk -M 1024  # Create shared memory segment
ipcs            # Only shows IPC resources in this namespace
```

## Combining Namespaces (Container)

```bash
# Create a minimal container-like environment
sudo unshare --pid --mount --net --uts --ipc --user \
    --fork --mount-proc bash

# This gives you:
# - PID namespace: PID 1 is bash
# - Mount namespace: isolated mounts
# - Network namespace: only loopback
# - UTS namespace: separate hostname
# - IPC namespace: separate IPC
# - User namespace: separate UID space
```

## Real-World Examples

### Docker Namespaces

```bash
# Docker creates all namespaces for each container

# View container namespaces
docker inspect --format '{{.State.Pid}}' mycontainer
# 12345

ls -la /proc/12345/ns/
# All namespaces listed with unique inode numbers

# Compare with host
ls -la /proc/1/ns/
# Different inode numbers = different namespaces
```

### nsenter — Enter Container Namespaces

```bash
# Enter a container's namespace from host
PID=$(docker inspect --format '{{.State.Pid}}' mycontainer)

# Enter all namespaces
sudo nsenter --target $PID --all bash

# Enter specific namespaces
sudo nsenter --target $PID --net --pid bash

# Debug network issues inside container
sudo nsenter --target $PID --net tcpdump -i eth0
```

### Kubernetes Namespace Security

```yaml
# Pod security context with namespace options
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  hostNetwork: false    # Use pod network namespace (default)
  hostPID: false        # Use pod PID namespace (default)
  hostIPC: false        # Use pod IPC namespace (default)
  containers:
  - name: app
    image: myimage
    securityContext:
      runAsUser: 1000
      runAsNonRoot: true
```

## Namespace Lifecycle

```bash
# Namespaces are reference-counted
# A namespace exists as long as any process or file descriptor references it

# Persist a namespace (keep it alive after all processes exit)
touch /run/netns/mynetns
mount --bind /proc/$PID/ns/net /run/netns/mynetns

# Later, join the persisted namespace
nsenter --net=/run/netns/mynetns bash
```

## Interview Questions

### Beginner

**Q: What are Linux namespaces?**
A: Namespaces are a kernel feature that isolates system resources. Each namespace provides a process group with its own view of a particular resource — its own PID space, network stack, filesystem mounts, hostname, etc. This makes each group believe it has its own isolated system, which is the foundation of container technology.

**Q: What namespace types exist in Linux?**
A: There are 8 namespace types: PID (process IDs), Network (IP, routes, interfaces), Mount (filesystem mounts), UTS (hostname), IPC (inter-process communication), User (UID/GID mapping), Cgroup (cgroup root view), and Time (system clocks, Linux 5.6+).

### Intermediate

**Q: How do user namespaces improve container security?**
A: User namespaces map container UIDs to different host UIDs. Container root (UID 0) maps to an unprivileged host UID (e.g., 100000). This means even if an attacker escapes the container as root, they're unprivileged on the host. Without user namespaces, container root is host root — a serious security risk.

**Q: How do containers use network namespaces?**
A: Each container gets its own network namespace with its own IP address, routing table, and port space. A veth (virtual ethernet) pair connects the container's namespace to the host's bridge network. This allows multiple containers to each use port 80 independently and provides network isolation.

### FAANG-Level

**Q: Design a network architecture for 1000 containers on a single host that need to communicate with each other and the outside network.**

A:

```
Architecture: Bridge + VXLAN + eBPF

1. Per-container network namespace:
   Each container gets:
   - Its own network namespace
   - A veth pair connecting to host bridge
   - Unique IP from cluster CIDR (e.g., 10.244.0.0/16)

2. Host bridge network:
   ┌────────────────────────────────────────────┐
   │  Host Network Namespace                     │
   │                                             │
   │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
   │  │ cni0    │  │ eth0    │  │ flannel.1│    │
   │  │ bridge  │  │ host    │  │ VXLAN   │    │
   │  │ 10.244  │  │ NIC     │  │ tunnel  │    │
   │  │ .0.1    │  │         │  │         │    │
   │  └────┬────┘  └────┬────┘  └────┬────┘    │
   │       │             │            │          │
   │  ┌────┴─────────────┴────────────┴────┐    │
   │  │         Routing / iptables         │    │
   │  └────────────────────────────────────┘    │
   │       │         │            │              │
   │  ┌────┴───┐ ┌───┴───┐ ┌────┴───┐          │
   │  │veth0   │ │veth1   │ │veth2   │          │
   │  │10.244  │ │10.244  │ │10.244  │          │
   │  │.0.2    │ │.0.3    │ │.0.4    │          │
   │  └────────┘ └────────┘ └────────┘          │
   └────────────────────────────────────────────┘

3. Container-to-container (same host):
   Container A → veth0 → bridge → veth1 → Container B
   Uses ARP/bridge forwarding (no encapsulation needed)

4. Container-to-container (different host):
   Container A → bridge → VXLAN encapsulation → network → 
   Host B → VXLAN decapsulation → bridge → Container B
   VXLAN adds 50-byte overhead but enables L2 over L3

5. Container-to-external:
   Container → bridge → NAT (MASQUERADE) → eth0 → internet
   iptables -t nat -A POSTROUTING -s 10.244.0.0/16 -o eth0 -j MASQUERADE

6. External-to-container (Service):
   External → NodePort/LoadBalancer → iptables/IPVS → Container
   Or: Ingress controller → route by hostname → Service → Pod

7. Performance optimizations:
   - eBPF (Cilium): bypass iptables, direct packet steering
   - SR-IOV: direct NIC access for high-performance pods
   - DPDK: kernel-bypass networking
   - Huge pages: reduce TLB misses for network buffers

Scale considerations for 1000 containers:
- Bridge MAC table: 1000 entries (fine)
- iptables rules: can become slow at scale → use IPVS or eBPF
- ARP broadcast: can be noisy → use VXLAN with proxy ARP
- DNS: CoreDNS must handle 1000+ services
```

**Q: A container can see host processes in /proc despite being in a PID namespace. Diagnose and fix.**

A:

```
Diagnosis:
1. Check if PID namespace is actually enabled:
   ls -la /proc/<container-pid>/ns/pid
   Compare inode with host PID 1 — if same, no PID namespace!

2. Check if /proc is correctly mounted:
   cat /proc/<container-pid>/mountinfo | grep proc
   Should show: proc on /proc type proc (rw,...)
   If it shows host /proc, mount namespace is wrong

3. Check Docker/containerd config:
   docker inspect <container> | grep PidMode
   Should be "" (empty = new PID namespace)
   If "host", container uses host PID namespace

4. Check security context (Kubernetes):
   hostPID: true → shares host PID namespace
   Should be false (or omitted, default is false)

Fix:
1. Ensure PID namespace is created:
   # Docker
   docker run --pid=private myimage  # Default, explicit
   
   # Kubernetes
   spec:
     hostPID: false  # Ensure this is set

2. Ensure /proc is remounted in PID namespace:
   # unshare --pid --mount-proc
   # --mount-proc remounts /proc to show only namespaced PIDs

3. If using nsenter, don't share PID namespace:
   nsenter --target $PID --pid  # Shares the container's PID ns
   # Don't use --pid without --target

4. Verify after fix:
   docker exec <container> ps aux
   # Should only show container processes
   # PID 1 should be the container's init process
```

## Common Mistakes

1. **Not remounting /proc**: Creating a PID namespace without `--mount-proc` means `/proc` still shows host processes.
2. **Sharing host namespaces**: Using `--pid=host`, `--net=host`, or `--uts=host` removes isolation. Avoid unless necessary.
3. **Forgetting user namespaces**: Without user namespaces, container root is host root — a serious security risk.
4. **Network namespace without veth**: Creating a network namespace alone gives only loopback. You need veth pairs for connectivity.
5. **Not handling PID 1 responsibilities**: The init process in a PID namespace must handle zombie reaping. Use `tini` or `dumb-init` as PID 1.

## Summary

| Namespace | Isolates | Key Use |
|-----------|----------|---------|
| PID | Process IDs | Container sees PID 1 as init |
| Network | IP, routes, ports | Each container has own network |
| Mount | Filesystem mounts | Container has own root filesystem |
| UTS | Hostname | Container has own hostname |
| IPC | Shared memory, semaphores | IPC isolation |
| User | UID/GID mapping | Container root ≠ host root |
| Cgroup | Cgroup view | Hide cgroup hierarchy |
| Time | System clocks | Different clock offsets |

## Cross-References

- [Cgroups](cgroups.md) — Resource control (complementary to namespaces)
- [Docker](docker.md) — Docker's use of namespaces
- [Kubernetes](kubernetes.md) — Kubernetes pod isolation
- [Security: Access Control](../security/access-control.md) — Access control in containers
