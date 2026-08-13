# Rootless Containers

Rootless containers run entirely in user space without requiring root privileges. They leverage
Linux user namespaces, unprivileged networking, and FUSE-based filesystem overlays to provide
container isolation that is secure by default and usable by any regular user.

## Introduction

Traditional container runtimes (Docker, early containerd) require a root-privileged daemon.
If the daemon is compromised, the attacker gains root on the host. Rootless containers eliminate
this attack surface:

- **No root daemon** — the container runtime runs as the invoking user
- **User namespace isolation** — container root (UID 0) maps to an unprivileged host UID
- **Reduced attack surface** — kernel vulnerabilities in the container path don't grant host root
- **Multi-tenant safety** — multiple users can run containers without coordination
- **Compliance** — meets security requirements for running containers without root

## Rootless vs Root Container Architecture

```mermaid
flowchart TB
    subgraph "Root Container (Docker)"
        DOCKERD["dockerd (root)"]
        CONTAINERD["containerd (root)"]
        RUNC1["runc (root)"]
        CONTAINER1["Container (root)"]
        DOCKERD --> CONTAINERD --> RUNC1 --> CONTAINER1
    end

    subgraph "Rootless Container (Podman)"
        USER["Regular user (UID 1000)"]
        PODMAN["podman (user)"]
        RUNC2["crun (user)"]
        CONTAINER2["Container (user ns)"]
        USER --> PODMAN --> RUNC2 --> CONTAINER2
    end
```

| Aspect | Root Container | Rootless Container |
|--------|---------------|-------------------|
| Daemon | Root-privileged daemon | No daemon (or user daemon) |
| Container root | Real UID 0 on host | Mapped to unprivileged UID |
| Network | Full host networking | User-mode networking (slirp/pasta) |
| Storage | /var/lib/docker (root) | ~/.local/share/containers (user) |
| Ports | Any port | Unprivileged ports (or sysctl) |
| Devices | Full access | Limited access |
| Security | Daemon compromise = host root | Escape = unprivileged user |

## User Namespaces

User namespaces are the foundation of rootless containers. They allow a process to have
UID 0 inside the namespace while mapped to an unprivileged UID outside.

### How UID Mapping Works

```mermaid
flowchart LR
    subgraph "Host"
        H_UID["UID 100000-165535"]
        H_USER["Regular user (UID 1000)"]
    end

    subgraph "Container User Namespace"
        C_UID["UID 0-65535"]
        C_ROOT["root (UID 0)"]
    end

    H_USER -->|"owns"| H_UID
    C_ROOT -->|"maps to"| H_UID
```

### Configuration

```bash
# Check if user namespaces are enabled
cat /proc/sys/user/max_user_namespaces
# 28672 (enabled if > 0)

# Enable if needed
sudo sysctl -w user.max_user_namespaces=28672

# /etc/subuid — subordinate UID ranges for user namespace mapping
# Format: username:start_uid:count
cat /etc/subuid
# jdoe:100000:65536

# /etc/subgid — subordinate GID ranges
cat /etc/subgid
# jdoe:100000:65536
```

### Manual User Namespace Example

```bash
# Create a user namespace with UID mapping
unshare --user --map-auto --uid-map 0:100000:65536 --gid-map 0:100000:65536 bash

# Inside the namespace
id
# uid=0(root) gid=0(root) groups=0(root)

# On the host, this process appears as UID 100000
ps -o pid,user,comm -p $$
#   PID USER     COMMAND
# 12345 100000   bash
```

### `/etc/subuid` and `/etc/subgid`

These files define the subordinate UID/GID ranges allocated to each user:

```bash
# Add subordinate ranges for a user
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 jdoe

# Or edit directly
echo "jdoe:100000:65536" | sudo tee -a /etc/subuid
echo "jdoe:100000:65536" | sudo tee -a /etc/subgid

# Verify
grep jdoe /etc/subuid /etc/subgid
# /etc/subuid:jdoe:100000:65536
# /etc/subgid:jdoe:100000:65536

# Remove subordinate ranges
sudo usermod --del-subuids 100000-165535 --del-subgids 100000-165535 jdoe
```

### Multiple UID Ranges

```bash
# Multiple ranges for different container sets
cat /etc/subuid
# jdoe:100000:65536
# jdoe:200000:65536

# Use specific range with Podman
podman run --uidmap 0:200000:1000 alpine id
# uid=0(root) gid=0(root)
# On host: UID 200000-200999
```

## slirp4netns

slirp4netns provides unprivileged networking for rootless containers. It creates a TAP
device in the user namespace and translates network traffic using a user-mode TCP/IP stack
(libslirp, derived from QEMU's network code).

### How It Works

```mermaid
flowchart TB
    subgraph "Container Network Namespace"
        APP["Container Process"]
        TAP["tap0 (10.0.2.100)"]
    end

    subgraph "Host"
        SLIRP["slirp4netns process"]
        HOST_NET["Host Network Stack"]
        INTERNET["Internet"]
    end

    APP --> TAP
    TAP -->|"raw packets"| SLIRP
    SLIRP -->|"userspace TCP/IP"| HOST_NET
    HOST_NET --> INTERNET
```

### Usage

```bash
# Create network namespace
ip netns add rootless

# Launch slirp4netns
slirp4netns --configure --mtu=65520 --disable-host-loopback \
    $(cat /proc/self/ns/net | cut -d: -f3 | tr -d '[]') tap0 &

# Verify connectivity
nsenter --net=/var/run/netns/rootless ping -c1 10.0.2.2
```

### slirp4netns Performance Characteristics

```bash
# slirp4netns is slower than kernel networking because:
# 1. Userspace TCP/IP stack (no kernel offloads)
# 2. Context switches between container and slirp process
# 3. No TSO/GRO/GSO offload

# Typical performance:
# Throughput: ~1-5 Gbps (vs 10+ Gbps with kernel networking)
# Latency: +50-200μs overhead per packet
# CPU: Higher (userspace processing)

# Optimize slirp4netns
slirp4netns --configure --mtu=65520 --disable-host-loopback \
    --enable-sandbox --enable-seccomp \
    $(cat /proc/self/ns/net) tap0
```

### slirp4netns vs pasta

pasta (Pack A Subtle Tap Abstraction) is a newer, faster alternative:

```mermaid
flowchart LR
    subgraph "slirp4netns"
        S_APP["Container"] --> S_TAP["TAP"]
        S_TAP --> S_SLIRP["slirp4netns<br>(userspace TCP/IP)"]
        S_SLIRP --> S_HOST["Host Network"]
    end

    subgraph "pasta"
        P_APP["Container"] --> P_TAP["TAP"]
        P_TAP --> P_PASTA["pasta<br>(pass-through)"]
        P_PASTA --> P_HOST["Host Network"]
    end
```

| Aspect          | slirp4netns                          | pasta                                |
|-----------------|--------------------------------------|--------------------------------------|
| **Performance** | Moderate (userspace TCP/IP)          | Fast (pass-through, no translation)  |
| **Latency**     | Higher                               | Lower                                |
| **Port forward**| Via command-line flags               | Automatic for bound ports            |
| **Default in**  | Podman < 4.3                         | Podman >= 4.3 (Fedora 39+)          |
| **Library**     | libslirp                             | passt                                |

```bash
# Using pasta (default in modern Podman)
podman run --network pasta alpine ping -c1 8.8.8.8

# Using slirp4netns explicitly
podman run --network slirp4netns alpine ping -c1 8.8.8.8

# Benchmark comparison
# pasta: ~8 Gbps throughput, ~10μs latency overhead
# slirp4netns: ~2 Gbps throughput, ~100μs latency overhead
```

## fuse-overlayfs

In rootless mode, the kernel's overlayfs requires root privileges (or kernel 5.11+ with
user namespace overlay mounts). fuse-overlayfs provides a FUSE-based implementation that
works without root on any kernel version.

### How It Works

```mermaid
flowchart TB
    subgraph "Container View"
        MNT["Merged Mount"]
    end

    subgraph "fuse-overlayfs (FUSE)"
        FOVL["fuse-overlayfs process"]
    end

    subgraph "Filesystem"
        UPPER["Upper dir (writable)"]
        LOWER1["Lower dir 1 (base)"]
        LOWER2["Lower dir 2 (app)"]
    end

    MNT -->|"VFS"| FOVL
    FOVL --> UPPER
    FOVL --> LOWER1
    FOVL --> LOWER2
```

### Installation and Usage

```bash
# Install
sudo apt install fuse-overlayfs   # Debian/Ubuntu
sudo dnf install fuse-overlayfs   # Fedora

# Verify
fuse-overlayfs --version

# Podman uses it automatically in rootless mode
podman info | grep -A5 graphDriver
# graphDriverName: overlay
# graphOptions:
#   overlay.mount_program:
#     /usr/bin/fuse-overlayfs

# Manual usage
mkdir lower upper work merged
fuse-overlayfs -o lowerdir=lower,upperdir=upper,workdir=work merged
```

### fuse-overlayfs Performance

```bash
# fuse-overlayfs has overhead compared to kernel overlayfs:
# - Read: ~10-30% slower (FUSE context switches)
# - Write: ~20-50% slower (FUSE + copy-up)
# - Metadata: ~30-60% slower (lookup, stat)

# Kernel 5.11+ native overlay is much faster
# fuse-overlayfs is only needed for kernel < 5.11

# Check which overlay Podman is using
podman info | grep -A5 graphDriver
# If mount_program is present → fuse-overlayfs
# If no mount_program → native overlayfs (kernel 5.11+)
```

### Kernel 5.11+ Native Overlay

Linux 5.11 added support for overlayfs in user namespaces without FUSE:

```bash
# Check kernel version
uname -r
# 6.1.0

# Podman automatically uses native overlay on 5.11+
podman info | grep graphDriverName
# graphDriverName: overlay
# (no mount_program = using native overlayfs)

# Performance comparison
# Native overlay: near-identical to kernel overlayfs
# fuse-overlayfs: 10-60% slower depending on workload
```

## cgroup Delegation

For rootless containers to manage their own resources, cgroups must be delegated to the
unprivileged user.

### cgroup v2

```bash
# Check cgroup version
stat -fc %T /sys/fs/cgroup
# cgroup2fs (v2)

# Enable cgroup delegation via systemd
sudo mkdir -p /etc/systemd/system/user@.service.d
cat <<EOF | sudo tee /etc/systemd/system/user@.service.d/delegate.conf
[Service]
Delegate=cpu cpuset io memory pids
EOF

sudo systemctl daemon-reload

# Or per-user (via systemd-run)
systemd-run --user --scope \
    -p "Delegate=yes" \
    podman run -it alpine sh

# Verify cgroup delegation
cat /sys/fs/cgroup/user.slice/user-$(id -u).slice/cgroup.controllers
# cpu cpuset io memory pids
```

### cgroup v1

```bash
# cgroup v1 is more limited for rootless
# Memory and CPU delegation requires manual setup

# /etc/cgconfig.conf
# jdoe {
#   memory {
#     jdoe {
#       memory.limit_in_bytes = 2G;
#     }
#   }
#   cpu {
#     jdoe {
#       cpu.shares = 1024;
#     }
#   }
# }
```

### cgroup Delegation Architecture

```mermaid
flowchart TB
    subgraph "systemd cgroup tree"
        ROOT["/sys/fs/cgroup/"]
        USER_SLICE["user.slice"]
        USER["user-1000.slice"]
        SESSION["user-1000.session-1.scope"]
        CONTAINER["libpod-<id>.scope"]
    end

    ROOT --> USER_SLICE
    USER_SLICE --> USER
    USER --> SESSION
    SESSION --> CONTAINER

    style CONTAINER fill:#f9f,stroke:#333
```

### Resource Limits in Rootless Mode

```bash
# Set memory limit for rootless container
podman run --memory=512m alpine sh -c "cat /sys/fs/cgroup/memory.max"

# Set CPU limit
podman run --cpus=1.5 alpine sh -c "cat /sys/fs/cgroup/cpu.max"

# Set I/O limit
podman run --device-read-bps=/dev/sda:10mb alpine sh

# Verify cgroup limits from host
cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/libpod-<id>.scope/memory.max
```

## Putting It All Together

### Podman Rootless Workflow

```bash
# 1. Verify setup
podman info --format '{{.Host.Security.Rootless}}'
# true

# 2. Run a container (rootless by default)
podman run -d --name web -p 8080:80 nginx

# 3. Check the user namespace mapping
podman top web -o pid,user,huser
#   PID USER   HUSER
#     1 root   100000
#    23 nginx  100001

# 4. Networking works via slirp4netns or pasta
curl http://localhost:8080
# Welcome to nginx!

# 5. Filesystem uses fuse-overlayfs or native overlay
podman exec web touch /tmp/test
podman diff web
# C /tmp
# A /tmp/test
```

### Buildah Rootless

```bash
# Build images without root
buildah from alpine
buildah run alpine-working-container apk add --no-cache curl
buildah commit alpine-working-container myimage:latest

# Build with multi-stage
buildah bud -t myapp:latest .

# Push to registry
buildah push myimage:latest docker://registry.example.com/myimage:latest
```

### containerd Rootless

```bash
# Install rootless containerd
containerd-rootless-setuptool.sh install

# Verify
containerd-rootless.sh --version

# Use with nerdctl
nerdctl run -d --name web -p 8080:80 nginx
nerdctl build -t myapp:latest .
nerdctl compose up -d
```

### Docker Rootless Mode

```bash
# Install Docker rootless
dockerd-rootless-setuptool.sh install

# Set environment
export PATH=/usr/bin:$PATH
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock

# Verify
docker info | grep -i rootless
# Security Options: rootless

# Run containers
docker run -d --name web -p 8080:80 nginx
```

## Limitations

### Known Limitations

| Limitation                          | Status                                   |
|-------------------------------------|------------------------------------------|
| AppArmor not supported              | Use SELinux or seccomp instead           |
| ping (ICMP)                         | Requires `ping_group_range` sysctl       |
| Privileged ports (< 1024)           | Requires `net.ipv4.ip_unprivileged_port_start=0` |
| cgroup v1 delegation                | Limited; cgroup v2 strongly recommended  |
| Cross-namespace mounts              | Kernel 5.11+ needed for overlay          |
| `/dev/fuse` access                  | Required for fuse-overlayfs              |
| Checkpoint/restore (CRIU)           | Limited in rootless mode                 |
| NFS home directory                  | May not work (overlayfs on NFS)          |
| systemd in container                | Requires user namespace + cgroup delegation |

### Workarounds

```bash
# Allow unprivileged ping
echo "net.ipv4.ping_group_range = 0 200000" | sudo tee -a /etc/sysctl.d/99-rootless.conf
sudo sysctl -p /etc/sysctl.d/99-rootless.conf

# Allow privileged ports
echo "net.ipv4.ip_unprivileged_port_start = 0" | sudo tee -a /etc/sysctl.d/99-rootless.conf
sudo sysctl -p /etc/sysctl.d/99-rootless.conf

# Enable /dev/fuse
sudo chmod 666 /dev/fuse
# Or add user to the fuse group
sudo usermod -aG fuse $USER

# Use slirp4netns for port forwarding (if pasta not available)
podman run --network slirp4netns:port_handler=slirp4netns -p 8080:80 nginx
```

## Security Implications

Rootless containers provide defense-in-depth:

```mermaid
flowchart TB
    subgraph "Root Container Attack"
        A1["Container Breakout"] -->|"UID 0 on host"| A2["Full root access"]
    end

    subgraph "Rootless Container Attack"
        B1["Container Breakout"] -->|"UID 100000 on host"| B2["Unprivileged access only"]
        B2 --> B3["Cannot load kernel modules"]
        B2 --> B4["Cannot modify system files"]
        B2 --> B5["Cannot access other users' data"]
    end

    style A2 fill:#f66,stroke:#333
    style B2 fill:#6f6,stroke:#333
```

Even if an attacker escapes a rootless container, they are still an unprivileged user on
the host with no ability to:

- Load kernel modules
- Modify `/etc`, `/boot`, or other system directories
- Access other users' files or containers
- Mount filesystems
- Change network configuration

### Security Audit

```bash
# Verify container is truly rootless
# 1. Check process UID on host
ps -eo pid,user,comm | grep -E "crun|runc|podman"
# Should show unprivileged UID, not root

# 2. Check container root mapping
podman top <container> -o pid,user,huser
# root inside → unprivileged UID outside

# 3. Verify no root processes
pgrep -u root | xargs ps -p
# Should not show container processes

# 4. Check capabilities
podman run --rm alpine cat /proc/1/status | grep Cap
# Should show limited capabilities
```

## Troubleshooting

### Common Issues

```bash
# Issue: "cannot find mappings in /etc/subuid"
# Fix: Add subordinate UID/GID ranges
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(whoami)

# Issue: "slirp4netns not found"
# Fix: Install slirp4netns
sudo apt install slirp4netns  # Debian/Ubuntu
sudo dnf install slirp4netns  # Fedora

# Issue: "fuse-overlayfs not found"
# Fix: Install fuse-overlayfs
sudo apt install fuse-overlayfs

# Issue: "cannot open /dev/fuse"
# Fix: Enable /dev/fuse
sudo chmod 666 /dev/fuse
sudo usermod -aG fuse $(whoami)

# Issue: "rootless containers require cgroup v2"
# Fix: Switch to cgroup v2 (if on v1)
# Edit /etc/default/grub:
# GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"
# sudo update-grub && sudo reboot

# Issue: "port already in use" for privileged ports
# Fix: Allow unprivileged port binding
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=0

# Issue: "too many subuid/subgid ranges"
# Fix: Clean up stale entries
sudo usermod --del-subuids 100000-165535 --del-subgids 100000-165535 $(whoami)
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(whoami)
```

### Debugging Rootless Containers

```bash
# Enable debug logging
podman --log-level=debug run alpine echo hello

# Check Podman system info
podman info

# Verify user namespace
podman unshare cat /proc/self/uid_map
#          0       1000          1
#          1     100000      65536

# Check storage driver
podman info | grep -A5 store
# store:
#   configFile: /home/jdoe/.config/containers/storage.conf
#   graphDriverName: overlay
#   graphRoot: /home/jdoe/.local/share/containers/storage

# Monitor system calls
podman --log-level=trace run alpine echo hello 2>&1 | head -50
```

## References

- [Podman Rootless Tutorial](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md)
- [User Namespaces man page](https://man7.org/linux/man-pages/man7/user_namespaces.7.html)
- [slirp4netns](https://github.com/rootless-containers/slirp4netns) — rootless networking
- [pasta](https://passt.top/passt/) — fast rootless networking
- [fuse-overlayfs](https://github.com/containers/fuse-overlayfs) — FUSE overlay
- [LWN: Rootless containers](https://lwn.net/Articles/761021/) — design overview
- [Rootless Containers](https://rootlesscontaine.rs/) — comprehensive resource

## Related Topics

- [Podman](./podman.md) — rootless-first container engine
- [Container Security](./security.md) — security features and best practices
- [OCI Standards](./oci.md) — container standards
- [cgroups](../kernel/processes/cgroups.md) — resource management
