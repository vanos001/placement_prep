# Containers

## Overview

Containers are a lightweight OS-level virtualization technology that package an application with its dependencies into an isolated environment. Unlike virtual machines, containers share the host kernel and use kernel features — **namespaces** for isolation and **cgroups** for resource control — to provide process-level separation with near-native performance.

## Motivation

Why containers instead of VMs?

```
Virtual Machines:                    Containers:
┌─────────────────────┐              ┌─────────────────────┐
│    App A  │  App B  │              │    App A  │  App B  │
│  ┌─────┐  │ ┌─────┐ │              │  ┌─────┐  │ ┌─────┐ │
│  │Bins │  │ │Bins │ │              │  │Bins │  │ │Bins │ │
│  │Libs │  │ │Libs │ │              │  │Libs │  │ │Libs │ │
│  └─────┘  │ └─────┘ │              │  └─────┘  │ └─────┘ │
│  Guest OS │Guest OS │              │  ┌─────────────────┐│
│  ┌────────────────┐ │              │  │   Host Kernel    ││
│  │   Hypervisor   │ │              │  │ (shared)         ││
│  └────────────────┘ │              │  └─────────────────┘│
│  Host OS            │              │  Host OS            │
│  Hardware           │              │  Hardware           │
└─────────────────────┘              └─────────────────────┘

VM: Heavy (full OS per app), slow startup, high overhead
Container: Light (shared kernel), fast startup, minimal overhead
```

| Aspect | VM | Container |
|--------|----|-----------|
| Isolation | Full (hardware level) | Process level |
| Startup | Minutes | Seconds/milliseconds |
| Overhead | High (full OS) | Minimal |
| Size | GBs | MBs |
| Security | Stronger (separate kernel) | Weaker (shared kernel) |
| Density | 10s per host | 100s-1000s per host |

## Container Technology Stack

```
┌──────────────────────────────────────────────────────────────┐
│              Container Technology Stack                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Container Orchestrators                              │    │
│  │  Kubernetes, Docker Swarm, Nomad                      │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Container Runtimes (High-Level)                      │    │
│  │  containerd, CRI-O, Podman                            │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Container Runtimes (Low-Level / OCI)                 │    │
│  │  runc, crun, kata-containers                          │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Kernel Features                                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │    │
│  │  │Namespaces│  │ Cgroups  │  │ Seccomp  │           │    │
│  │  │(isolation)│  │(resources)│  │(syscalls)│           │    │
│  │  └──────────┘  └──────────┘  └──────────┘           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │    │
│  │  │ Capabilities││ AppArmor │  │ SELinux  │           │    │
│  │  └──────────┘  └──────────┘  └──────────┘           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Linux Kernel                                         │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## OCI Standards

The **Open Container Initiative (OCI)** defines container standards:

| Standard | Description |
|----------|-------------|
| **Image Spec** | How container images are built and formatted |
| **Runtime Spec** | How containers are configured and executed |
| **Distribution Spec** | How container images are distributed (registries) |

```
Container Image Layers:

┌─────────────────────────┐
│  Application Layer      │ ← COPY myapp /usr/bin/
├─────────────────────────┤
│  Dependency Layer       │ ← RUN apt install libfoo
├─────────────────────────┤
│  Base OS Layer          │ ← FROM ubuntu:22.04
└─────────────────────────┘

Images are read-only layers stacked via OverlayFS
Container adds a writable layer on top
```

## Topics in This Chapter

| Topic | Description |
|-------|-------------|
| [Cgroups](cgroups.md) | Resource control and limiting |
| [Namespaces](namespaces.md) | Process isolation |
| [Docker](docker.md) | Docker architecture and usage |
| [Kubernetes](kubernetes.md) | Container orchestration |

## Container Security Layers

```
┌──────────────────────────────────────────────────────┐
│  Container Security Defense in Depth                  │
│                                                      │
│  1. Namespaces: Isolate view (PID, net, mount, etc.) │
│  2. Cgroups: Limit resources (CPU, memory, I/O)      │
│  3. Capabilities: Drop unnecessary privileges         │
│  4. Seccomp: Restrict syscalls                       │
│  5. SELinux/AppArmor: Mandatory access control       │
│  6. Read-only rootfs: Prevent filesystem modification│
│  7. No-new-privileges: Prevent privilege escalation   │
│  8. Rootless containers: Run without root at all     │
└──────────────────────────────────────────────────────┘
```

## Quick Revision

- **Containers**: Lightweight isolation using kernel features (namespaces + cgroups)
- **VMs**: Full hardware virtualization with separate kernel
- **Namespaces**: Isolate what a process can see (PID, network, filesystem)
- **Cgroups**: Limit what a process can use (CPU, memory, disk)
- **Docker**: Container runtime and image management
- **Kubernetes**: Container orchestration at scale
- **OCI**: Standards for container images and runtimes

## Cross-References

- [Cgroups](cgroups.md) — Resource control
- [Namespaces](namespaces.md) — Isolation mechanisms
- [Docker](docker.md) — Docker in detail
- [Kubernetes](kubernetes.md) — Orchestration
- [Security: Access Control](../security/access-control.md) — DAC/MAC in containers
- [Security: SELinux](../security/selinux.md) — SELinux in containers


## Cross References

- [Docker](../os/containers/docker.md)
- [Kubernetes](../os/containers/kubernetes.md)
- [Namespaces](../os/containers/namespaces.md)
- [VM vs Container](../cloud/virtualization/vm-vs-container.md)
- [Hypervisors](../cloud/virtualization/hypervisors.md)
