# Docker Internals

## Introduction

Docker popularized containers but is often misunderstood as being synonymous with containers. In reality, Docker is a platform built on top of Linux kernel primitives (namespaces, cgroups, union filesystems) and a layered architecture of components that have evolved significantly since Docker's initial release in 2013.

This chapter dissects Docker's internal architecture: the container runtime stack, image format, storage drivers, networking implementation, and the standards (OCI) that enable interoperability.

## Docker Architecture

```mermaid
flowchart TB
    subgraph Client
        CLI[docker CLI]
        COMPOSE[docker compose]
        BUILD[docker build]
    end
    subgraph Docker_Engine["Docker Engine"]
        DOCKERD["dockerd<br>Docker daemon<br>REST API, image mgmt, volumes"]
        CONTAINERD["containerd<br>Container lifecycle, snapshots"]
        SHIM["containerd-shim<br>Per-container process"]
        RUNC["runc<br>OCI runtime"]
    end
    subgraph Kernel
        NS[Namespaces]
        CG[cgroups]
        FS[Overlay FS]
        SEC[Seccomp, Capabilities]
    end

    CLI -->|REST API| DOCKERD
    DOCKERD -->|gRPC| CONTAINERD
    CONTAINERD -->|exec| SHIM
    SHIM -->|exec| RUNC
    RUNC --> NS
    RUNC --> CG
    RUNC --> FS
    RUNC --> SEC
```

### Component Roles

| Component | PID | Lifetime | Role |
|-----------|-----|----------|------|
| dockerd | 1 (systemd) | Daemon | API, images, networks, volumes |
| containerd | 1 (systemd) | Daemon | Container lifecycle, snapshots, content |
| containerd-shim | Per container | Container lifetime | Keeps container alive if containerd restarts |
| runc | Per create | Transient | Creates and starts container, then exits |

### The containerd-shim in Detail

The shim is the key component that enables daemon-less container operation:

```c
/* containerd-shim process lifecycle */

/* 1. containerd spawns shim for each container */
/*    Shim inherits: containerd socket address, container ID, bundle path */

/* 2. Shim creates a new TTRPC/GRPC server */
/*    containerd connects to this server for container operations */

/* 3. Shim calls runc create/start */
/*    runc sets up namespaces, cgroups, mounts, then exec's container init */
/*    runc exits immediately after starting container */

/* 4. Shim reaps container process (waitpid) */
/*    Shim becomes the parent of the container process */

/* 5. Shim handles I/O */
/*    stdin, stdout, stderr are piped through the shim */
/*    Shim can buffer I/O even if containerd is down */
```

```bash
# View shim processes
ps aux | grep containerd-shim
# root  1234  ... containerd-shim-runc-v2 -namespace default -id abc123 ...
# root  5678  ... containerd-shim-runc-v2 -namespace default -id def456 ...

# Each shim has its own socket
ls /run/containerd/io.containerd.runtime.v2.task/default/
# abc123/  (container ID)
#   address    (shim socket address)
#   config.json (OCI bundle)
#   log         (shim log)
#   process/    (process metadata)

# Shim version (runc-v2 is current)
# containerd-shim-runc-v2: uses containerd's v2 runtime API
# containerd-shim-runc-v1: legacy (v1 API)
# containerd-shim-kata-v2: Kata Containers integration
```

### Why containerd-shim?

```mermaid
sequenceDiagram
    participant dockerd
    participant containerd
    participant shim
    participant runc
    participant container

    dockerd->>containerd: Create container
    containerd->>shim: Start shim process
    shim->>runc: Create container
    runc->>container: Start container process
    runc->>runc: Exit (container runs under shim)

    Note over containerd: containerd crashes/restarts!
    
    containerd->>shim: Reconnect (shim still running)
    shim->>containerd: Report container status
    
    Note over container: Container still running!<br>Shim maintains container I/O
```

The shim ensures containers survive daemon restarts (live-restore).

### containerd Architecture

containerd itself is a modular container runtime:

```bash
# containerd's internal components:
# - content store: stores image layers (content-addressable)
# - snapshotter: manages overlay/other filesystem snapshots
# - task service: manages running containers
# - image service: manages image metadata
# - namespace service: multi-tenant isolation

# containerd namespaces
ctr namespaces list
# NAME    LABELS
# default
# k8s.io

# containerd tasks (running containers)
ctr tasks list
# TASK      PID    STATUS
# abc123    1234   RUNNING
# def456    5678   RUNNING

# containerd images
ctr images list
# REFERENCE                        TYPE
# docker.io/library/nginx:latest   application/vnd.docker.distribution.manifest.v2+json
```

### containerd Snapshotter

The snapshotter manages filesystem layers. For overlay2:

```bash
# View snapshots
crictl inspect-container abc123 | grep -A5 snapshotter
# "snapshotter": "overlayfs"
# "snapshotKey": "abc123..."

# Snapshot lifecycle:
# 1. Prepare: create upper dir + work dir
# 2. Mount: overlay mount of all layers
# 3. Commit: make read-only (for image layers)
# 4. Remove: cleanup
```

## Container Lifecycle

### Creating a Container

```bash
# What happens when you run: docker run -d nginx

# 1. CLI sends REST API POST /containers/create
#    Body: {"Image": "nginx", "Cmd": ["nginx", "-g", "daemon off;"], ...}

# 2. dockerd pulls image if not present
#    - Check local image store
#    - Pull from registry if missing
#    - Store layers in content-addressable store

# 3. dockerd calls containerd to create container
#    containerd pulls image from local store
#    Creates snapshot (writable layer)
#    Prepares OCI bundle

# 4. containerd spawns containerd-shim
#    shim sets up stdio pipes
#    shim calls runc create

# 5. runc creates the container:
#    - Reads config.json (OCI runtime spec)
#    - Creates namespaces (pid, net, mount, uts, ipc)
#    - Sets up cgroups
#    - Mounts rootfs (overlay)
#    - Sets up seccomp filter
#    - Drops capabilities
#    - Sets up AppArmor/SELinux labels
#    - Creates container process (paused)
```

### OCI Bundle

```json
// config.json (OCI Runtime Specification)
{
    "ociVersion": "1.0.2",
    "process": {
        "terminal": false,
        "user": { "uid": 0, "gid": 0 },
        "args": ["nginx", "-g", "daemon off;"],
        "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
        "cwd": "/",
        "capabilities": {
            "bounding": ["CAP_NET_BIND_SERVICE", "CAP_CHOWN", "CAP_SETUID"],
            "effective": ["CAP_NET_BIND_SERVICE", "CAP_CHOWN", "CAP_SETUID"],
            "inheritable": ["CAP_NET_BIND_SERVICE"],
            "permitted": ["CAP_NET_BIND_SERVICE", "CAP_CHOWN", "CAP_SETUID"],
            "ambient": ["CAP_NET_BIND_SERVICE"]
        },
        "seccomp": {
            "defaultAction": "SCMP_ACT_ERRNO",
            "syscalls": [{"names": ["accept4","read","write"], "action": "SCMP_ACT_ALLOW"}]
        },
        "apparmorProfile": "docker-default",
        "noNewPrivileges": true
    },
    "root": {
        "path": "rootfs",
        "readonly": false
    },
    "linux": {
        "namespaces": [
            {"type": "pid"},
            {"type": "network"},
            {"type": "ipc"},
            {"type": "uts"},
            {"type": "mount"},
            {"type": "cgroup"}
        ],
        "resources": {
            "memory": { "limit": 536870912 },
            "cpu": { "quota": 100000, "period": 100000 }
        },
        "maskedPaths": ["/proc/kcore", "/proc/sysrq-trigger"],
        "readonlyPaths": ["/proc/asound", "/proc/bus"]
    }
}
```

## Image Layers

Docker images are composed of read-only layers stacked on top of each other:

```mermaid
flowchart TB
    subgraph Image_Layers__read_only["Image Layers (read-only)"]
        L1["Layer 1: Ubuntu base<br>77.8MB - apt-get install"]
        L2["Layer 2: Install deps<br>12.3MB - apt-get install libssl"]
        L3["Layer 3: Copy app<br>2.1MB - COPY . /app"]
        L4["Layer 4: Set config<br>0.1KB - ENV, CMD"]
    end
    subgraph Container__read_write["Container (read-write)"]
        RW["Writable Layer<br>Container changes"]
    end
    RW --> L4 --> L3 --> L2 --> L1
```

### Content-Addressable Storage

Each layer is identified by a SHA256 digest of its content:

```bash
# Inspect image layers
docker inspect nginx --format '{{.RootFS.Layers}}'
# sha256:e4d0e95fdb2f... (layer 1)
# sha256:ab6cc02b34bc... (layer 2)
# sha256:4757a108af0a... (layer 3)

# Image storage location
ls /var/lib/docker/overlay2/
# Each layer is a directory with diff/ and link files

# Image manifest
docker manifest inspect nginx:latest
# {
#   "schemaVersion": 2,
#   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
#   "config": {"digest": "sha256:abc123..."},
#   "layers": [
#     {"digest": "sha256:e4d0e95...", "size": 28948291},
#     {"digest": "sha256:ab6cc02b...", "size": 12345678}
#   ]
# }
```

### Layer Sharing

```bash
# Two images sharing the same base layer only store it once
docker images --tree  # (if using buildx with --metadata-file)

# Example:
# nginx:latest  ──┐
#                  ├── ubuntu:22.04 (shared base)
# myapp:latest  ──┘

# Multi-stage builds reduce layers
# FROM golang:1.21 AS builder
# ... build ...
# FROM alpine:3.19
# COPY --from=builder /app/server /usr/local/bin/
# Final image: only alpine layer + binary layer
```

## Overlay2 Storage Driver

Overlay2 is the default storage driver for Docker on Linux:

```mermaid
flowchart TB
    subgraph Container_View["Container View"]
        MOUNT["merged/<br>Container sees unified filesystem"]
    end
    subgraph Overlay2
        UPPER["upper/<br>Container writes go here"]
        WORK["work/<br>Internal use only"]
        LOWER["lower/<br>Image layers (read-only)"]
    end
    MOUNT -->|overlay mount| UPPER
    MOUNT -->|overlay mount| LOWER
    UPPER --> WORK
```

### How Overlay2 Works

```bash
# Docker's overlay2 storage
ls /var/lib/docker/overlay2/
# abc123.../  (image layer)
#   diff/     (layer contents)
#   link      (short name for this layer)
# def456.../  (container layer)
#   diff/     (container-specific changes)
#   link
#   merged/   (mount point - what container sees)
#   work/     (overlay internal)

# The overlay mount:
mount -t overlay overlay \
  -o lowerdir=/lower2:/lower1,upperdir=/upper,workdir=/work \
  /merged

# Copy-on-write behavior:
# Read: file found in lower layer → served from there
# Write: file copied to upper layer → modified in upper
# Delete: "whiteout" file created in upper layer
```

### Overlay2 Layer Internals

The overlay filesystem uses the VFS `dentry` cache and page cache for performance:

```c
/* fs/overlayfs/super.c (simplified) */

struct ovl_fs {
    struct vfsmount *upper_mnt;     /* Upper layer mount */
    struct vfsmount **lower_mnt;    /* Lower layer mounts */
    int numlower;                   /* Number of lower layers */
    struct dentry *workdir;         /* Work directory */
    struct dentry *indexdir;        /* Index directory (for NFS export) */
    /* ... */
};

/* Copy-up: when writing to a lower layer file */
static int ovl_copy_up(struct dentry *dentry)
{
    /* 1. Create parent directories in upper layer */
    /* 2. Copy file data from lower to upper */
    /* 3. Copy file metadata (xattrs, permissions) */
    /* 4. Set redirect xattr for NFS export */
}

/* Whiteout: when deleting a file from lower layer */
static int ovl_whiteout(struct dentry *upper, struct dentry *dentry)
{
    /* Create character device (0,0) in upper layer */
    /* This masks the lower layer file */
    struct inode *inode = ovl_get_whiteout(dentry);
    /* ... */
}
```

### Whiteout Files

```bash
# When a container deletes a file from a lower layer:
# overlay2 creates a "whiteout" file in the upper layer

# Character device whiteout (0,0 major/minor)
ls -la /var/lib/docker/overlay2/abc/merged/etc/deleted-file
# c--------- 1 root root 0, 0 ...

# Opaque directory whiteout (trusted.overlay.opaque xattr)
getfattr -n trusted.overlay.opaque /var/lib/docker/overlay2/abc/merged/etc/dir
# "y" (yes, opaque - hide lower dir contents)
```

### Overlay2 Performance Characteristics

```bash
# Overlay2 read performance: nearly identical to native
# - First read: lookup in upper, then lower layers
# - Subsequent reads: served from page cache

# Write performance: copy-on-write overhead
# - First write to a file: full file copy from lower to upper
# - Subsequent writes: direct to upper layer (fast)

# Metadata operations (ls, stat):
# - Must check all layers (upper + all lowers)
# - More layers = slower metadata ops

# Docker limits layers to 128 by default
# Each layer adds overhead to lookups
```

### Overlay2 vs Other Storage Drivers

| Driver | Type | Performance | Notes |
|--------|------|-------------|-------|
| overlay2 | Union FS | Good | Default, recommended |
| devicemapper | Block | Moderate | Thin provisioning, deprecated |
| btrfs | CoW FS | Good | Native CoW, no union needed |
| zfs | CoW FS | Good | Deduplication, snapshots |
| vfs | Copy | Slow | Full copy per layer (testing only) |
| fuse-overlayfs | FUSE | Moderate | For rootless containers |

## Docker Networking

### Bridge Network (Default)

```mermaid
flowchart TB
    subgraph Host
        ETH0["eth0<br>192.168.1.100"]
        DOCKER0["docker0<br>172.17.0.1/16<br>Linux bridge"]
        IPT["iptables NAT<br>MASQUERADE"]
        VETH0["veth-abc<br>Container 1 end"]
        VETH1["veth-def<br>Container 2 end"]
    end
    subgraph Container_1["Container 1"]
        C1["eth0<br>172.17.0.2"]
    end
    subgraph Container_2["Container 2"]
        C2["eth0<br>172.17.0.3"]
    end
    
    ETH0 --> IPT
    DOCKER0 --> VETH0
    DOCKER0 --> VETH1
    VETH0 <-->|veth pair| C1
    VETH1 <-->|veth pair| C2
    IPT --> DOCKER0
```

```bash
# Docker creates a linux bridge
ip link show docker0
# docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...

# Each container gets a veth pair
ip link show type veth
# veth123@if4: <BROADCAST,MULTICAST,UP> ... master docker0
# veth456@if6: <BROADCAST,MULTICAST,UP> ... master docker0

# iptables rules for NAT
iptables -t nat -L -n
# Chain POSTROUTING
# MASQUERADE  all  --  172.17.0.0/16  anywhere

# Port publishing (-p 8080:80)
iptables -t nat -L -n
# DNAT  tcp  --  anywhere  anywhere  tcp dpt:8080 to:172.17.0.2:80

# Docker iptables chain
iptables -L DOCKER -n
# ACCEPT  tcp  --  !172.17.0.0/16  172.17.0.2  tcp dpt:80
```

### Bridge Network Internals

Docker's bridge network uses Linux kernel networking primitives:

```c
/* When Docker creates a container: */

/* 1. Create veth pair */
/* ip link add veth-abc type veth peer name veth-def */

/* 2. Move one end into container namespace */
/* ip link set veth-def netns <container-pid> */

/* 3. Attach host end to docker0 bridge */
/* ip link set veth-abc master docker0 */

/* 4. Configure container IP */
/* ip addr add 172.17.0.2/16 dev veth-def */
/* ip link set veth-def up */

/* 5. Set up NAT for outbound */
/* iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE */

/* 6. Set up port forwarding for published ports */
/* iptables -t nat -A DOCKER -p tcp --dport 8080 -j DNAT --to 172.17.0.2:80 */
/* iptables -A DOCKER -d 172.17.0.2 -p tcp --dport 80 -j ACCEPT */
```

### Container DNS Resolution

Docker runs an embedded DNS server (127.0.0.11) that resolves container names:

```bash
# Docker DNS architecture:
# Container → 127.0.0.11 (Docker DNS) → /etc/hosts + Docker network → External DNS

# The DNS server is implemented by Docker's libnetwork
# It intercepts DNS queries on the container's loopback interface

# Custom DNS per container:
docker run --dns 8.8.8.8 --dns-search example.com nginx

# DNS entries for containers:
docker run --network mynet --name web nginx
docker run --network mynet alpine nslookup web
# web.mynet → 10.0.3.2 (resolved by Docker DNS)

# Docker also sets up /etc/hosts entries:
docker exec web cat /etc/hosts
# 172.17.0.2  web
# (container's own IP with hostname)
```

### Network Drivers

```bash
# List networks
docker network ls
# NETWORK ID     NAME      DRIVER    SCOPE
# abc123...      bridge    bridge    local
# def456...      host      host      local
# ghi789...      none      null      local

# Create custom bridge
docker network create --driver bridge \
  --subnet 10.0.2.0/24 \
  --ip-range 10.0.2.128/25 \
  --gateway 10.0.2.1 \
  my-net

# Docker creates a new bridge and iptables rules
ip link show br-$(docker network inspect my-net --format '{{.Id}}' | head -c12)

# Container on custom network
docker run --network my-net --name web nginx
```

### Network Driver Internals

```bash
# bridge driver: creates Linux bridge + veth pairs
# - Uses iptables for NAT and port forwarding
# - Docker DNS for container name resolution
# - Supports ICC (inter-container communication) control

# host driver: container shares host network namespace
# - No network isolation
# - Best performance (no NAT overhead)
# - Cannot publish ports (already on host)

# none driver: no network at all
# - Container has only loopback
# - For isolated workloads

# overlay driver: multi-host networking (Swarm)
# - Uses VXLAN tunneling between hosts
# - Requires Swarm or external KV store
# - encrypt option for VXLAN encryption

# macvlan driver: assign MAC address to container
# - Container appears as physical device on network
# - Requires promiscuous mode on host NIC
# - Good for legacy applications
```

### Docker iptables Internals

```bash
# Docker creates its own iptables chains:
# DOCKER     - filter table: container access control
# DOCKER-NAT - nat table: port forwarding
# DOCKER-ISOLATION-STAGE-1 - isolation between networks
# DOCKER-ISOLATION-STAGE-2 - isolation between networks

# View all Docker iptables rules
iptables -L -n -v
iptables -t nat -L -n -v

# Port publishing creates DNAT + filter rules:
# -p 8080:80 creates:
#   1. NAT: DNAT from host:8080 to container:80
#   2. Filter: ACCEPT to container:80 from outside
#   3. NAT: MASQUERADE for container outbound

# Disable Docker's iptables management (NOT recommended)
# /etc/docker/daemon.json:
# { "iptables": false }
```

## Docker Storage

### Volumes vs Bind Mounts vs tmpfs

```bash
# Named volumes (managed by Docker)
docker volume create mydata
docker volume inspect mydata
# {
#     "Mountpoint": "/var/lib/docker/volumes/mydata/_data",
#     "Driver": "local",
#     "Scope": "local"
# }

# Bind mounts (host path)
docker run -v /host/path:/container/path:ro nginx

# tmpfs (in-memory)
docker run --tmpfs /app/cache:rw,noexec,nosuid,size=100m nginx

# Volume drivers for distributed storage
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw \
  --opt device=:/exports/data \
  nfs-data
```

## Docker Build System

### BuildKit

```bash
# BuildKit is Docker's modern build engine
# Enabled by default in Docker 23.0+

# BuildKit features:
# - Parallel build stages
# - Build cache import/export
# - Secret mounts (--mount=type=secret)
# - SSH agent forwarding (--mount=type=ssh)
# - Multi-platform builds

# Build with BuildKit
DOCKER_BUILDKIT=1 docker build -t myapp .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t myapp .
```

### Build Cache

```bash
# Build cache is layer-based
# Each instruction in Dockerfile creates a layer
# If the instruction and context haven't changed, cached layer is used

docker build -t myapp .
# Step 1/5 : FROM alpine:3.19
#  ---> Using cache  (abc123)
# Step 2/5 : RUN apk add --no-cache curl
#  ---> Using cache  (def456)
# Step 3/5 : COPY . /app
#  ---> New layer    (ghi789)  # Context changed!

# Cache invalidation:
# COPY/ADD: invalidated if file content changes
# RUN: NOT invalidated (use --no-cache to force)
# ARG: invalidated if value changes
```

## Docker Security

```bash
# Security features applied to containers:
# 1. Namespaces (pid, net, mount, uts, ipc, cgroup)
# 2. Seccomp profile (default blocks ~44 of 300+ syscalls)
# 3. Capabilities (drops ~14 of ~37 capabilities)
# 4. AppArmor profile (docker-default)
# 5. Read-only rootfs (--read-only)
# 6. No new privileges (--security-opt no-new-privileges)
# 7. User namespace remapping (--userns-remap)

# Run with all security features
docker run \
  --security-opt seccomp=profile.json \
  --security-opt apparmor=docker-default \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges \
  --user 1000:1000 \
  nginx

# Docker Content Trust (image signing)
export DOCKER_CONTENT_TRUST=1
docker pull nginx  # Only pulls signed images
```

## Docker Context / Info

```bash
# Docker system information
docker system info
# Server:
#  Containers: 5
#   Running: 3
#   Paused: 0
#   Stopped: 2
#  Images: 12
# Storage Driver: overlay2
#  Backing Filesystem: ext4
# Logging Driver: json-file
# Cgroup Driver: systemd
# Cgroup Version: 2
# Kernel Version: 6.1.0
# Operating System: Ubuntu 22.04
# Architecture: x86_64

# Disk usage
docker system df
# TYPE        ACTIVE   SIZE     RECLAIMABLE
# Images      3        1.2GB    800MB (66%)
# Containers  3        50MB     30MB (60%)
# Local Volumes 2      500MB    200MB (40%)
# Build Cache 5        2GB      2GB (100%)

# Cleanup
docker system prune -a --volumes  # Remove everything unused
```

## Alternatives to Docker

| Tool | Architecture | Rootless | Notes |
|------|-------------|----------|-------|
| **Podman** | Daemonless | ✅ | Docker CLI compatible |
| **containerd** | Daemon | ✅ | K8s CRI standard |
| **CRI-O** | Daemon | ✅ | K8s-specific runtime |
| **LXC/LXD** | Daemon | ✅ | System containers |
| **runc** | Standalone | ✅ | Low-level runtime only |

```bash
# Podman is a drop-in Docker replacement
alias docker=podman
podman run --rm alpine echo "Hello from Podman"
# No daemon needed!
# Rootless by default
```

## References

1. Docker Architecture Documentation. [https://docs.docker.com/get-started/overview/](https://docs.docker.com/get-started/overview/)
2. OCI Runtime Specification. [https://github.com/opencontainers/runtime-spec](https://github.com/opencontainers/runtime-spec)
3. OCI Image Specification. [https://github.com/opencontainers/image-spec](https://github.com/opencontainers/image-spec)
4. containerd Documentation. [https://containerd.io/docs/](https://containerd.io/docs/)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Docker Documentation](https://docs.docker.com/)
- [containerd GitHub](https://github.com/containerd/containerd)
- [runc — OCI Runtime](https://github.com/opencontainers/runc)
- [BuildKit Documentation](https://github.com/moby/buildkit)
- [Docker Networking Deep Dive](https://docs.docker.com/network/)
- [Podman Documentation](https://podman.io/docs)

## Related Topics

- [Container Overview](./overview.md) — container concepts
- [Container Primitives](./primitives.md) — kernel features used by Docker
- [cgroups v2](./cgroups-v2.md) — resource management
- [Kubernetes and Linux](./kubernetes.md) — container orchestration
