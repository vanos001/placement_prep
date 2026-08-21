# Kubernetes Kubelet

The kubelet is the primary "node agent" in Kubernetes — the process running on every node that manages the lifecycle of pods assigned to that node. It's the workhorse of the Kubernetes data plane, translating PodSpecs from the API server into running containers via a container runtime (containerd, CRI-O). This page covers the architecture, the pod lifecycle, the probe mechanism, and the production tuning.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Kubelet (one per node)                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pod Manager                                              │ │
│  │  - Watches API server for pods assigned to this node    │ │
│  │  - Translates PodSpecs to runtime calls                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CRI (Container Runtime Interface) client                │ │
│  │  - Talks to containerd / CRI-O via gRPC                  │ │
│  │  - Manages containers' lifecycle                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Probe Manager                                            │ │
│  │  - Runs liveness/readiness probes periodically           │ │
│  │  - Updates pod status based on probe results             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Status Manager                                           │ │
│  │  - Reports pod status to the API server                  │ │
│  │  - Includes IP, phase, container statuses                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Volume Manager                                           │ │
│  │  - Mounts/unmounts volumes for pods                       │ │
│  │  - Handles PVC -> PV binding                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PLEG (Pod Lifecycle Event Generator)                    │ │
│  │  - Periodically inspects running containers              │ │
│  │  - Generates events for state changes                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ watches API server           │ gRPC to containerd
        ▼                              ▼
   API server                       Container Runtime
                                          │
                                          ▼
                                       Containers
```

## The Pod Lifecycle

```text
1. Scheduler assigns Pod P to this node (writes to etcd).
2. Kubelet's watch sees the new Pod.
3. Kubelet reads the PodSpec and:
   a. Mounts volumes (via the Volume Manager).
   b. Calls CRI to create the Pod's "sandbox" (the pause container with network namespace).
   c. Calls CRI to start the init containers sequentially.
   d. Calls CRI to start the regular containers in parallel.
4. Kubelet sets up probes (liveness, readiness, startup).
5. Kubelet reports status to API server (Phase=Running).
6. PLEG periodically inspects containers; on changes, updates status.
7. If a container dies:
   a. Kubelet checks the restart policy.
   b. If "Always" or "OnFailure": restarts the container.
   c. If "Never": leaves the container exited; pod phase becomes "Failed" if all containers exited.
8. On pod deletion:
   a. Kubelet receives the deletion event.
   b. Kubelet calls CRI to stop the containers.
   c. Kubelet unmounts volumes.
   d. Kubelet removes the pod from its state.
   e. API server removes the pod object.
```

## The CRI (Container Runtime Interface)

The kubelet doesn't manage containers directly — it uses the CRI, a gRPC API:

```protobuf
service RuntimeService {
    rpc RunPodSandbox(RunPodSandboxRequest) returns (RunPodSandboxResponse);
    rpc StopPodSandbox(StopPodSandboxRequest) returns (StopPodSandboxResponse);
    rpc CreateContainer(CreateContainerRequest) returns (CreateContainerResponse);
    rpc StartContainer(StartContainerRequest) returns (StartContainerResponse);
    rpc StopContainer(StopContainerRequest) returns (StopContainerResponse);
    rpc RemoveContainer(RemoveContainerRequest) returns (RemoveContainerResponse);
    rpc ListContainers(ListContainersRequest) returns (ListContainersResponse);
    rpc ContainerStatus(ContainerStatusRequest) returns (ContainerStatusResponse);
    // ... and many more
}

service ImageService {
    rpc ListImages(ListImagesRequest) returns (ListImagesResponse);
    rpc PullImage(PullImageRequest) returns (PullImageResponse);
    rpc RemoveImage(RemoveImageRequest) returns (RemoveImageResponse);
}
```

The CRI lets Kubernetes support multiple runtimes (containerd, CRI-O, runc, kata, gVisor) via the same kubelet.

## Probes

Kubelet runs three types of probes per pod:

### Liveness Probe

Determines if the container is "alive". If a liveness probe fails, kubelet restarts the container (per the restart policy).

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

If `/health` returns non-2xx for 3 consecutive checks (30 seconds), the container is killed and restarted.

### Readiness Probe

Determines if the container is "ready to serve traffic". If a readiness probe fails, the pod is removed from the service's endpoints (no traffic routed).

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

Different from liveness: readiness failure doesn't restart the container — it just stops traffic. Use this for "not ready yet" (e.g., warming up the cache).

### Startup Probe

Determines if the container has finished starting up. Until the startup probe succeeds, liveness and readiness probes are disabled.

```yaml
startupProbe:
  httpGet:
    path: /started
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

Useful for applications with long startup (e.g., JVM apps that take 60+ seconds to warm up). Without a startup probe, the liveness probe would fail and restart the container during startup.

## PLEG (Pod Lifecycle Event Generator)

PLEG is the kubelet's mechanism for detecting container state changes:

```text
Every 1 second:
  1. List all containers on the node (via CRI).
  2. Compare with the previous state.
  3. For each container whose state changed:
     a. Generate a PodLifecycleEvent.
     b. Process the event (restart, status update, etc.).
```

PLEG is single-threaded — if listing containers takes too long (e.g., containerd is slow), PLEG backs up and the kubelet can't react to state changes promptly. This is the source of the infamous "PLEG is not healthy" error.

## The Static Pod Path

Kubelet can manage "static pods" — pods defined in a local directory (default `/etc/kubernetes/manifests/`):

```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
    - name: kube-apiserver
      image: registry.k8s.io/kube-apiserver:v1.28
      ...
```

Kubelet reads this file and runs the pod, without going through the API server. This is how Kubernetes bootstraps itself — the control plane components (API server, etcd, controller-manager, scheduler) run as static pods on the master node.

## Production Tuning

```bash
# /etc/kubernetes/kubelet-config.yaml
apiVersion: kubelet.config.k8s.io/v1
kind: KubeletConfiguration
# Pod limits (max pods on this node)
podPidsLimit: 4096
maxPods: 110

# Eviction thresholds (when to evict pods to reclaim resources)
evictionHard:
  memory.available: 100Mi
  nodefs.available: 10%
  nodefs.inodesFree: 5%
  imagefs.available: 15%

# Image garbage collection
imageGCHighThresholdPercent: 85
imageGCLowThresholdPercent: 80

# CRI related
containerRuntime: containerd
```

Key tunables:
- `maxPods`: max pods per node (default 110).
- `evictionHard`: when to evict pods (e.g., if memory < 100 MB).
- `imageGCHighThresholdPercent`: when to start GC'ing images.

## Production Performance

Kubelet's typical performance on a node with 100 pods:
- CPU: 5-10% of one core.
- Memory: 200-500 MB.
- Pod startup latency: 5-30 seconds (image pull + container start).
- PLEG cycle: 1 second (default).

For nodes with 250+ pods, the kubelet's CPU usage increases; consider raising `maxPods` cautiously.

## Common Pitfalls

1. **Forgetting that liveness probes can cause cascading restarts.** A failing dependency (e.g., database) makes liveness probes fail across many pods; they all restart; the dependency is still down; cycle repeats. Use readiness probes for "not ready", not liveness for "down dependency".

2. **Forgetting that `initialDelaySeconds` matters for slow-starting apps.** A JVM that takes 60s to start, with a liveness probe at `initialDelaySeconds=30`, fails the probe and restarts — endless restart loop. Use a startup probe.

3. **Forgetting that PLEG is single-threaded.** A slow container runtime (containerd under load) backs up PLEG; the kubelet can't react to state changes; pods get stuck. Monitor PLEG health.

4. **Forgetting to set resource requests/limits.** Without them, a single pod can starve others; kubelet can't enforce fairness.

5. **Forgetting that static pods aren't managed by the API server.** Static pods aren't visible to `kubectl get pods` directly (they appear as mirror pods); to update, edit the YAML file on the node.

6. **Forgetting that kubelet's config is in a YAML file, not command-line.** Old-style kubelet command-line flags are deprecated; use the KubeletConfiguration YAML.

## References

- [Kubernetes: Kubelet documentation](https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet/)
- [Kubernetes: Container Runtime Interface (CRI)](https://kubernetes.io/docs/concepts/architecture/cri/)
- [Kubernetes: Configure Liveness, Readiness, and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Kubelet: PLEG and the "PLEG is not healthy" error](https://github.com/kubernetes/kubernetes/blob/master/pkg/kubelet/pleg/pleg.go)
- [KubeletConfiguration API reference](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/)
- [Kubernetes: Static Pods](https://kubernetes.io/docs/tasks/configure-pod-container/static-pod/)
- [LWN: Kubelet internals (2020)](https://lwn.net/Articles/815575/)
