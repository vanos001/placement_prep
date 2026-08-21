# containerd Internals

containerd is a container runtime, originally developed by Docker and donated to CNCF in 2017, becoming a graduated project in 2019. It is the runtime used by Kubernetes (via `containerd` CRI plugin), Docker Engine, and other container platforms. containerd provides image management, container lifecycle, and runtime primitives, leaving orchestration to higher-level systems. This page covers the architecture, the OCI runtime shim model, the image distribution model, and the CRI integration.

## The Architecture

containerd has a layered design:

```text
┌──────────────────────────────────────────────────────────┐
│  Containerd daemon (single process)                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Services:                                            │ │
│  │  - Content (image pulling, content store)              │ │
│  │  - Images (image metadata)                            │ │
│  │  - Containers (container metadata)                     │ │
│  │  - Tasks (container runtime)                           │ │
│  │  - Events (lifecycle events)                           │ │
│  │  - Leases (reference counting for content)            │ │
│  └──────────────────────────────────────────────────────┘ │
│         │                                                 │
│         │ GRPC API (Unix socket)                          │
│         ▼                                                 │
└──────────────────────────────────────────────────────────┘
        │
        │ exec and shim control
        ▼
┌──────────────────────────────────────────────────────────┐
│  OCI Runtime Shim (per-container process)                  │
│  - containerd-shim-runc-v2 (default)                       │
│  - containerd-shim-runc-v1 (legacy)                       │
│  - kata-shim (for Kata Containers)                        │
│  - windows-shim (for Windows containers)                  │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  OCI Runtime (low-level, per-container process)            │
│  - runc (default, Linux namespaces)                       │
│  - crun (C alternative to runc)                            │
│  - kata-runtime (for VM-isolated containers)              │
│  - runsc (gVisor sandbox)                                 │
└──────────────────────────────────────────────────────────┘
```

containerd is the "middle layer": it manages images and containers but delegates actual container execution to lower-level runtimes (runc, crun, etc.) via shims.

## The Shim Model

The shim is the key abstraction. When containerd starts a container:

1. containerd forks a shim process (e.g., `containerd-shim-runc-v2`).
2. The shim forks the container process (with runc's help).
3. The shim becomes the parent of the container; containerd is no longer the parent.

Why the shim? Because:
- **Lifetime decoupling**: containerd can be restarted without affecting running containers (the shim keeps them alive).
- **Reaping**: the shim reaps the container's zombies.
- **Stdio management**: the shim holds the container's stdin/stdout/stderr file descriptors, even after containerd restarts.

The shim is small (~10 MB) and per-container. A node with 100 running containers has 100 shim processes.

## Image Distribution

containerd pulls images from OCI-compliant registries (Docker Hub, ECR, GCR, etc.):

```text
1. containerd receives a PullImage request.
2. containerd contacts the registry: GET /v2/library/nginx/manifests/latest
3. The registry returns a manifest: list of layer digests.
4. containerd fetches each layer: GET /v2/library/nginx/blobs/sha256:abc...
5. Each layer is downloaded, verified by SHA256, and stored in the content store.
6. containerd unpacks the layers into a snapshot (the unionfs/overlayfs view).
```

The content store is content-addressable: each blob is stored by its SHA256. Two images that share a layer share the blob (deduplication).

The snapshotter creates the container's root filesystem:
- **overlayfs** (default on Linux): stack of layers, with the top being writable.
- **native**: copies each layer into the next (slow, no CoW).
- **stargz / nydus**: lazy-pulling filesystems, only fetches layers on demand.

## The CRI Plugin

Kubernetes's Container Runtime Interface (CRI) is a gRPC API for kubelet to communicate with the container runtime. containerd implements CRI as a plugin:

```text
kubelet → CRI gRPC API → containerd CRI plugin → containerd daemon
```

The CRI API has three main RPCs:
- `RunPodSandbox`: start the pod's infrastructure container.
- `CreateContainer`: create a container within a pod sandbox.
- `StartContainer`: actually start the container.

containerd's CRI plugin adds pod-level concepts (sandbox, pod networking) that containerd's core doesn't have. The plugin manages pod-level cgroups, network namespaces, and IP assignment.

## Container Lifecycle

```text
1. Kubelet sends RunPodSandbox to containerd.
2. containerd creates the pod's network namespace, assigns an IP.
3. containerd starts the pod's "pause" container (the sandbox).
4. Kubelet sends CreateContainer for each container in the pod.
5. containerd creates the container's rootfs (overlayfs of the image layers).
6. containerd forks a shim, which forks the container process.
7. Kubelet sends StartContainer; the container begins executing.
8. The container runs until it exits or kubelet sends StopContainer.
9. On exit, the shim reaps the container's zombies and notifies containerd.
```

## Production Deployment

containerd is typically installed on each Kubernetes node (or, in some setups, on bare Docker hosts). The standard config file `/etc/containerd/config.toml`:

```toml
version = 2

[plugins."io.containerd.grpc.v1.cri"]
  # Use systemd as the cgroup driver
  cgroup_driver = "systemd"
  # Sandbox image
  sandbox_image = "registry.k8s.io/pause:3.9"
  # Container registry config
  [plugins."io.containerd.grpc.v1.cri".registry]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
      "docker.io" = {
        endpoint = ["https://registry-1.docker.io"]
      }

[plugins."io.containerd.grpc.v1.cri".containerd]
  # Default runtime
  default_runtime_name = "runc"
  # Snapshotter
  snapshotter = "overlayfs"
```

## Common Operations

```bash
# Pull an image
ctr -n k8s.io image pull docker.io/library/nginx:latest

# List images
ctr -n k8s.io image list

# List running containers
ctr -n k8s.io container list

# Connect to containerd's socket
sudo ctr -n k8s.io

# View containerd's metrics
curl -s http://localhost:1338/v1/metrics | head
```

The `ctr` CLI is containerd's debug tool. In production, kubelet manages containerd via CRI; `ctr` is for inspection.

## Comparison to CRI-O

CRI-O is Red Hat's alternative CRI implementation (used in OpenShift). The two are similar:

| Aspect | containerd | CRI-O |
|--------|-----------|-------|
| Origin | Docker, donated to CNCF | Red Hat, OpenShift |
| Default runtime | runc | runc (crun on RHEL) |
| Image format | OCI | OCI |
| Default snapshotter | overlayfs | overlayfs |
| Default CNI plugin | CNI | CNI |
| Production users | Kubernetes (most distros), Docker | OpenShift |
| Feature parity | ~95% | ~95% |

For new Kubernetes deployments, containerd is the standard. CRI-O is used in OpenShift and some RHEL-based setups.

## Common Pitfalls

1. **Forgetting that containerd's default snapshotter is overlayfs.** Some filesystems (e.g., ZFS, BTRFS) have their own snapshotters. Using overlayfs on ZFS works but is suboptimal.

2. **Forgetting the garbage collection.** containerd retains old images until disk pressure triggers GC. Configure `imageGCHighThresholdPercent` (default 85%) to avoid OOD.

3. **Forgetting that containerd's socket is per-namespace.** The `k8s.io` namespace holds Kubernetes-managed containers; the default namespace holds `ctr`-created containers. They don't share images.

4. **Forgetting that the shim doesn't auto-restart containers.** If a container crashes, the shim reports the exit to containerd, but doesn't restart. Restart policies (Always, OnFailure) are kubelet-level concerns, not containerd's.

5. **Forgetting to set `systemd` as cgroup driver.** The default is `cgroupfs`, which conflicts with systemd on most Linux distributions. Set `cgroup_driver = "systemd"` explicitly.

6. **Forgetting that containerd's image pull doesn't verify signatures.** Container images can be tampered with in a registry compromise. Use Sigstore/Cosign for signature verification.

## References

- [containerd documentation](https://containerd.io/docs/)
- [containerd GitHub](https://github.com/containerd/containerd)
- [containerd architecture documentation](https://github.com/containerd/containerd/blob/main/docs/architecture.md)
- [CRI plugin source code](https://github.com/containerd/containerd/tree/main/plugins/cri)
- [Kubernetes: Container Runtime Interface](https://kubernetes.io/docs/concepts/architecture/cni/)
- [OCI Runtime specification](https://github.com/opencontainers/runtime-spec)
- [OCI Image specification](https://github.com/opencontainers/image-spec)
- [CRI-O documentation](https://cri-o.io/)
