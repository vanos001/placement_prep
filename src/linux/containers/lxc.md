# LXC (Linux Containers)

## Overview

LXC (Linux Containers) is an operating system-level virtualization technology that enables running multiple isolated Linux systems (containers) on a single host kernel. Unlike virtual machines, LXC containers share the host kernel and use kernel features — namespaces, cgroups, and security profiles — to provide isolation. LXC provides a complete Linux environment including its own process tree, network stack, and filesystem, with near-native performance.

LXC was one of the earliest container technologies for Linux, with development starting in 2008. It serves as the foundation for many higher-level container tools and is maintained as a core Linux infrastructure project. While Docker and Podman have gained broader adoption for application packaging, LXC remains widely used for system containers that run full Linux distributions.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Host Kernel                        │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Namespaces│  │ Cgroups  │  │ Security Profiles │  │
│  │ PID, NET  │  │ CPU, Mem │  │ AppArmor/Seccomp  │  │
│  │ MNT, UTS  │  │ BlkIO   │  │ Capabilities      │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│              LXC / liblxc                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │Container1│  │Container2│  │Container3│          │
│  │ Ubuntu   │  │ CentOS   │  │ Alpine   │          │
│  │ /sbin/init│  │ /sbin/init│  │ /bin/sh │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

### Components

- **liblxc**: Core C library providing container management APIs
- **lxc-* tools**: Command-line utilities for container operations
- **LXC templates**: Scripts for creating container root filesystems
- **LXC download templates**: Pre-built images from images.linuxcontainers.org
- **lxcfs**: FUSE filesystem providing per-container resource views

## Installation

### Debian/Ubuntu

```bash
sudo apt install lxc lxc-utils lxc-templates lxcfs
```

### Fedora/RHEL

```bash
sudo dnf install lxc lxc-templates lxcfs
# Or from EPEL on RHEL/CentOS
```

### Arch Linux

```bash
sudo pacman -S lxc lxcfs
```

### From Source

```bash
git clone https://github.com/lxc/lxc.git
cd lxc
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr ..
make -j$(nproc)
sudo make install
```

## Container Lifecycle Management

### Creating Containers

```bash
# Create from download template (recommended)
sudo lxc-create -t download -n mycontainer -- \
    -d ubuntu -r jammy -a amd64

# Create from local template
sudo lxc-create -t ubuntu -n mycontainer -- \
    -r jammy -a amd64

# Create from a custom rootfs
sudo lxc-create -n mycontainer -t none -- \
    --rootfs /path/to/rootfs

# Create with specific storage backend
sudo lxc-create -n mycontainer -t download -B lvm \
    --vgname vg0 --lvname lxc --fssize 5G
```

### Starting and Stopping

```bash
# Start a container
sudo lxc-start -n mycontainer

# Start in foreground (useful for debugging)
sudo lxc-start -n mycontainer -F

# Start with init system
sudo lxc-start -n mycontainer -d  # daemon mode

# Stop gracefully
sudo lxc-stop -n mycontainer

# Force stop (kill)
sudo lxc-stop -n mycontainer -k

# Restart
sudo lxc-stop -n mycontainer
sudo lxc-start -n mycontainer

# Autostart on boot
sudo systemctl enable lxc@mycontainer
```

### Listing and Information

```bash
# List all containers
sudo lxc-ls -f
# NAME        STATE   AUTOSTART  GROUPS  IPV4        IPV6  UNPRIVILEGED
# mycontainer RUNNING 0          -       10.0.3.100  -     false

# Container info
sudo lxc-info -n mycontainer
# Name:           mycontainer
# State:          RUNNING
# PID:            2345
# IP:             10.0.3.100
# CPU use:        0.52 seconds
# Memory use:     45.23 MiB
# KMem use:       12.10 MiB

# Container configuration
sudo lxc-config -l
```

### Attaching to Containers

```bash
# Execute a command in the container
sudo lxc-attach -n mycontainer -- ls /home

# Open a shell
sudo lxc-attach -n mycontainer

# Attach with specific UID/GID mapping
sudo lxc-attach -n mycontainer -e -- bash

# Run as specific user inside container
sudo lxc-attach -n mycontainer -- su - ubuntu
```

### Destroying Containers

```bash
# Destroy a stopped container
sudo lxc-destroy -n mycontainer

# Force destroy (stop if running)
sudo lxc-destroy -n mycontainer -f

# Destroy and remove storage
sudo lxc-destroy -n mycontainer -s
```

## Container Configuration

### Configuration File

Each container has a configuration file at `/var/lib/lxc/<name>/config`:

```ini
# Container identification
lxc.uts.name = mycontainer

# Distribution and architecture
lxc.arch = amd64

# Root filesystem
lxc.rootfs.path = dir:/var/lib/lxc/mycontainer/rootfs

# Networking
lxc.net.0.type = veth
lxc.net.0.flags = up
lxc.net.0.link = lxcbr0
lxc.net.0.hwaddr = 00:16:3e:xx:xx:xx
lxc.net.0.ipv4.address = 10.0.3.100/24
lxc.net.0.ipv4.gateway = 10.0.3.1

# Capabilities to drop
lxc.cap.drop = sys_module mac_admin mac_override sys_time

# AppArmor profile
lxc.apparmor.profile = lxc-container-default

# Seccomp profile
lxc.seccomp.profile = /usr/share/lxc/config/common.seccomp

# Console
lxc.tty.max = 4
lxc.pty.max = 1024

# Init command
lxc.init.cmd = /sbin/init

# Environment
lxc.environment = TERM=xterm

# Mount entries
lxc.mount.fstab = /var/lib/lxc/mycontainer/fstab
lxc.mount.auto = proc:sys:cgroup
```

### Default Configuration

LXC provides default configuration templates:

```bash
ls /usr/share/lxc/config/
# common.conf          - Common settings
# common.seccomp       - Default seccomp profile
# userns.conf          - User namespace config
# nesting.conf         - Nested container config
# oci.common.conf      - OCI-compatible settings
```

Include defaults in your container config:

```ini
# /var/lib/lxc/mycontainer/config
lxc.include = /usr/share/lxc/config/common.conf
lxc.include = /usr/share/lxc/config/nesting.conf
```

## Cgroup Integration

LXC uses cgroups to limit and account for container resources:

### CPU Limits

```ini
# Limit to 50% of one CPU
lxc.cgroup2.cpu.max = 50000 100000

# Pin to specific CPUs (cpuset)
lxc.cgroup2.cpuset.cpus = 0-3

# CPU shares (relative weight, default 1024)
lxc.cgroup2.cpu.weight = 512
```

### Memory Limits

```ini
# Limit memory to 512MB
lxc.cgroup2.memory.max = 536870912

# Or with human-readable format
lxc.cgroup2.memory.max = 512M

# Memory + swap limit
lxc.cgroup2.memory.max = 512M
lxc.cgroup2.memory.swap.max = 256M

# Soft limit (memory.low for protection)
lxc.cgroup2.memory.low = 256M

# OOM control
lxc.cgroup2.memory.oom.group = 1
```

### I/O Limits

```ini
# Block I/O weight (10-1000, default 100)
lxc.cgroup2.io.weight = 50

# I/O bandwidth limit
lxc.cgroup2.io.max = 8:0 rbps=10485760 wbps=10485760
# 8:0 = major:minor of device, rbps/wbps = bytes/sec

# I/O latency target
lxc.cgroup2.io.latency = 8:0 target=5000
# target in microseconds
```

### Process Limits

```ini
# Maximum number of processes
lxc.cgroup2.pids.max = 256
```

### Checking Cgroup Status

```bash
# Show cgroup for a container
cat /sys/fs/cgroup/lxc/mycontainer/cgroup.controllers

# Show memory usage
cat /sys/fs/cgroup/lxc/mycontainer/memory.current

# Show CPU usage
cat /sys/fs/cgroup/lxc/mycontainer/cpu.stat
```

## Networking

### Default Bridge (NAT)

LXC creates a default bridge `lxcbr0` with NAT:

```bash
# Check default bridge
ip addr show lxcbr0

# Default config: /etc/default/lxc-net
USE_LXC_BRIDGE="true"
LXC_BRIDGE="lxcbr0"
LXC_ADDR="10.0.3.1"
LXC_NETMASK="255.255.255.0"
LXC_NETWORK="10.0.3.0/24"
LXC_DHCP_RANGE="10.0.3.2,10.0.3.254"
LXC_DHCP_MAX="253"
```

### Bridge Configuration

```ini
# Container network config
lxc.net.0.type = veth
lxc.net.0.flags = up
lxc.net.0.link = lxcbr0
lxc.net.0.hwaddr = 00:16:3e:xx:xx:xx

# Static IP
lxc.net.0.ipv4.address = 10.0.3.100/24
lxc.net.0.ipv4.gateway = 10.0.3.1

# DHCP (requires DHCP server on bridge)
# Don't set ipv4.address; use DHCP client inside container
```

### MACVLAN

```ini
# Direct network access (no bridge, no NAT)
lxc.net.0.type = macvlan
lxc.net.0.macvlan.mode = bridge
lxc.net.0.link = eth0
lxc.net.0.flags = up
lxc.net.0.hwaddr = 00:16:3e:xx:xx:xx
```

### VLAN

```ini
# VLAN tagged interface
lxc.net.0.type = vlan
lxc.net.0.link = eth0
lxc.net.0.vlan.id = 100
```

### Physical Interface

```ini
# Assign physical interface directly to container
lxc.net.0.type = phys
lxc.net.0.link = eth1
lxc.net.0.flags = up
```

### Multiple Interfaces

```ini
lxc.net.0.type = veth
lxc.net.0.flags = up
lxc.net.0.link = lxcbr0
lxc.net.0.ipv4.address = 10.0.3.100/24

lxc.net.1.type = macvlan
lxc.net.1.macvlan.mode = bridge
lxc.net.1.link = eth0
lxc.net.1.flags = up
```

## Security Profiles

### Capabilities

LXC drops dangerous capabilities by default:

```ini
# Drop specific capabilities
lxc.cap.drop = sys_module mac_admin mac_override sys_time sys_rawio

# Keep only necessary capabilities
lxc.cap.keep = net_bind_service sys_chroot

# The default common.conf drops:
# sys_module, mac_admin, mac_override, sys_time, sys_rawio
```

### AppArmor

```ini
# Use default container profile
lxc.apparmor.profile = lxc-container-default

# Use profile with nesting support
lxc.apparmor.profile = lxc-container-default-with-nesting

# Custom profile
lxc.apparmor.profile = /etc/apparmor.d/lxc/my-profile

# Disable AppArmor (not recommended)
lxc.apparmor.profile = unconfined
```

Default AppArmor profile restricts:
- Mount operations
- File writes to `/proc/sysrq-trigger`, `/proc/sys/`, etc.
- Loading kernel modules
- Accessing host paths outside the container

### Seccomp

```ini
# Use default seccomp profile
lxc.seccomp.profile = /usr/share/lxc/config/common.seccomp

# Custom seccomp profile
lxc.seccomp.profile = /etc/lxc/my-container.seccomp
```

Default seccomp profile blocks:
- `kexec_load` — loading a new kernel
- `open_by_handle_at` — file handle access
- `init_module` / `finit_module` — module loading
- `bpf` — eBPF operations
- `mount` — in some configurations

### SELinux

```ini
# SELinux context for container processes
lxc.selinux.context = system_u:system_r:container_t:s0:c100,c200

# SELinux MCS (Multi-Category Security) label
lxc.selinux.category = yes
```

### User Namespaces (Unprivileged Containers)

```ini
# Map container root (UID 0) to host UID 100000
lxc.idmap = u 0 100000 65536
lxc.idmap = g 0 100000 65536

# Or in /etc/subuid and /etc/subgid:
# user:100000:65536
```

```bash
# Create unprivileged container as regular user
lxc-create -n mycontainer -t download -- \
    -d ubuntu -r jammy -a amd64

# Start without root
lxc-start -n mycontainer
```

## lxcfs

lxcfs is a FUSE filesystem that provides per-container views of `/proc` and `/sys`:

```bash
# Install lxcfs
sudo apt install lxcfs

# lxcfs mounts at /var/lib/lxcfs
ls /var/lib/lxcfs/
# proc/  sys/

# Container sees its own resource limits:
# /proc/cpuinfo    — shows assigned CPUs
# /proc/meminfo    — shows container memory limit
# /proc/stat       — shows container CPU usage
# /proc/uptime     — shows container uptime
```

### Configuration

```ini
# In container config
lxc.autodev = 1
lxc.mount.auto = cgroup:rw proc:rw sys:rw

# lxcfs provides:
# /proc/cpuinfo
# /proc/diskstats
# /proc/meminfo
# /proc/stat
# /proc/swaps
# /proc/uptime
# /sys/devices/system/cpu/
```

## Snapshots and Cloning

### Snapshots

```bash
# Create a snapshot
sudo lxc-snapshot -n mycontainer

# List snapshots
sudo lxc-snapshot -n mycontainer -L
# snap0 (/var/lib/lxc/mycontainer/snaps/snap0)

# Restore a snapshot
sudo lxc-snapshot -n mycontainer -r snap0

# Destroy a snapshot
sudo lxc-snapshot -n mycontainer -d snap0

# Create snapshot with comment
sudo lxc-snapshot -n mycontainer -c "Before upgrade"
```

### Cloning

```bash
# Clone (copy) a container
sudo lxc-copy -n mycontainer -N mycontainer-clone

# Clone as snapshot (thin copy, saves space)
sudo lxc-copy -n mycontainer -N mycontainer-snap -s

# Clone to different storage backend
sudo lxc-copy -n mycontainer -N mycontainer-clone -B lvm
```

## Systemd Integration

```bash
# Enable container autostart
sudo systemctl enable lxc@mycontainer

# Start via systemd
sudo systemctl start lxc@mycontainer

# Check status
sudo systemctl status lxc@mycontainer

# LXC systemd service template
cat /lib/systemd/system/lxc@.service
```

## Advanced Features

### Nested Containers

```ini
# Enable nesting in container config
lxc.include = /usr/share/lxc/config/nesting.conf
# Or manually:
lxc.mount.auto = cgroup:rw proc:rw sys:rw
lxc.apparmor.profile = lxc-container-default-with-nesting
```

### Container Hooks

```ini
# Pre-start hook
lxc.hook.pre-start = /etc/lxc/pre-start.sh

# Post-start hook
lxc.hook.post-start = /etc/lxc/post-start.sh

# Pre-stop hook
lxc.hook.pre-stop = /etc/lxc/pre-stop.sh

# Post-stop hook
lxc.hook.post-stop = /etc/lxc/post-stop.sh

# Clone hook
lxc.hook.clone = /etc/lxc/clone-hook.sh
```

### Container API

```c
#include <lxc/lxccontainer.h>

int main() {
    struct lxc_container *c = lxc_container_new("mycontainer", NULL);
    c->load_config(c, NULL);

    if (!c->is_running(c))
        c->start(c, 0, NULL);

    c->shutdown(c, 30);
    lxc_container_put(c);
    return 0;
}
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Container won't start | Missing rootfs | Check `lxc.rootfs.path` |
| No network | Bridge not configured | Check `lxcbr0` and `lxc-net` |
| Permission denied | AppArmor/SELinux | Check profiles, use `unconfined` for testing |
| Cannot attach | Container not running | `lxc-start` first |
| Slow startup | DNS resolution | Check `/etc/resolv.conf` in container |
| Cgroup errors | cgroup v1/v2 mismatch | Ensure consistent cgroup version |

## Further Reading

- **LXC documentation**: https://linuxcontainers.org/lxc/documentation/
- **LXC GitHub**: https://github.com/lxc/lxc
- **LXC download images**: https://images.linuxcontainers.org/
- **Stéphane Graber's blog**: Extensive LXC/LXD tutorials
- **man pages**: `lxc(7)`, `lxc.container.conf(5)`, `lxc-create(1)`
- **Related**: [Namespaces](../kernel/filesystems/namespaces.md) — isolation foundation
- **Related**: [Cgroups](../kernel/processes/cgroups.md) — resource control
- **Related**: [AppArmor](../security/apparmor.md) — security profiles
- **Related**: Seccomp — syscall filtering
- **Related**: [Docker](docker-internals.md) — higher-level container platform
