# Kubernetes

## Overview

**Kubernetes (K8s)** is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. While Docker runs containers on a single host, Kubernetes manages containers across a cluster of machines, providing service discovery, load balancing, self-healing, and automated rollouts.

## Motivation

Running containers in production requires more than just `docker run`:
- **Scaling**: How do you run 100 copies of a service?
- **Self-healing**: What happens when a container crashes?
- **Load balancing**: How do you distribute traffic?
- **Rolling updates**: How do you update without downtime?
- **Service discovery**: How do services find each other?
- **Resource management**: How do you schedule containers across nodes?

Kubernetes solves all of these.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Kubernetes Architecture                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Control Plane (Master Node)                          │    │
│  │                                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │ API      │ │Scheduler │ │Controller│ │etcd    │  │    │
│  │  │ Server   │ │          │ │ Manager  │ │        │  │    │
│  │  │          │ │ Assigns  │ │ Maintains│ │Cluster │  │    │
│  │  │ Frontend │ │ pods to  │ │ desired  │ │ state  │  │    │
│  │  │ for all  │ │ nodes    │ │ state    │ │ store  │  │    │
│  │  │ operatns │ │          │ │          │ │        │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Worker Nodes                                         │    │
│  │                                                      │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐    │    │
│  │  │  Node 1             │  │  Node 2             │    │    │
│  │  │  ┌──────┐ ┌──────┐ │  │  ┌──────┐ ┌──────┐ │    │    │
│  │  │  │kubelet│ │kube- │ │  │  │kubelet│ │kube- │ │    │    │
│  │  │  │      │ │proxy │ │  │  │      │ │proxy │ │    │    │
│  │  │  └──────┘ └──────┘ │  │  └──────┘ └──────┘ │    │    │
│  │  │  ┌──────┐ ┌──────┐ │  │  ┌──────┐          │    │    │
│  │  │  │ Pod A│ │ Pod B│ │  │  │ Pod C│          │    │    │
│  │  │  │      │ │      │ │  │  │      │          │    │    │
│  │  │  └──────┘ └──────┘ │  │  └──────┘          │    │    │
│  │  │  Container Runtime  │  │  Container Runtime  │    │    │
│  │  │  (containerd/CRI-O) │  │  (containerd/CRI-O) │    │    │
│  │  └─────────────────────┘  └─────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Pod

The smallest deployable unit — one or more containers sharing network and storage.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  containers:
  - name: app
    image: myapp:v1
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: "250m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
  - name: sidecar
    image: envoyproxy/envoy:v1.28
    # Sidecar pattern: proxy alongside app
```

```
Pod Networking:
  ┌─────────────────────────────────────┐
  │  Pod (shared network namespace)     │
  │                                     │
  │  ┌──────────┐  ┌──────────┐        │
  │  │ App      │  │ Sidecar  │        │
  │  │ :8080    │  │ :9090    │        │
  │  └────┬─────┘  └────┬─────┘        │
  │       │              │              │
  │  ┌────┴──────────────┴────┐         │
  │  │   eth0 (shared IP)     │         │
  │  │   10.244.1.5           │         │
  │  └────────────────────────┘         │
  │  Containers share localhost!        │
  └─────────────────────────────────────┘
```

### Deployment

Manages ReplicaSets and provides declarative updates.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v2
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 20
```

### Service

Stable network endpoint for a set of pods.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP  # ClusterIP, NodePort, LoadBalancer

---
# Ingress for external access
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp
            port:
              number: 80
```

```
Service Types:
  ClusterIP (default): Internal cluster IP only
  NodePort: Exposes on each node's IP at a static port
  LoadBalancer: Provisions external load balancer
  ExternalName: CNAME to external DNS

Service Discovery:
  DNS: myapp.default.svc.cluster.local
  Environment: MYAPP_SERVICE_HOST, MYAPP_SERVICE_PORT
```

### Storage

```yaml
# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myapp-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 10Gi

---
# Pod using PVC
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp
    volumeMounts:
    - mountPath: /data
      name: data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: myapp-data
```

## Kubernetes Networking Model

```
┌──────────────────────────────────────────────────────────────┐
│  Kubernetes Networking                                       │
│                                                              │
│  Rules:                                                      │
│  1. Every Pod gets its own IP                                │
│  2. Pods can communicate without NAT                         │
│  3. Agents on a node can communicate with all pods           │
│                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐            │
│  │  Pod A   │     │  Pod B   │     │  Pod C   │            │
│  │ 10.244.1.│     │ 10.244.2.│     │ 10.244.3.│            │
│  │ 5        │────►│ 3        │────►│ 7        │            │
│  └──────────┘     └──────────┘     └──────────┘            │
│       │                │                 │                   │
│  Node 1           Node 2            Node 3                  │
│       │                │                 │                   │
│  ┌────┴────────────────┴─────────────────┴────┐            │
│  │          CNI Plugin (Calico/Cilium/Flannel)│            │
│  │          Handles cross-node Pod routing    │            │
│  └────────────────────────────────────────────┘            │
│                                                              │
│  Service (virtual IP):                                       │
│  myapp.default.svc.cluster.local → 10.96.0.100             │
│  kube-proxy load balances to Pods matching selector          │
└──────────────────────────────────────────────────────────────┘
```

## Real-World Examples

### Scaling

```bash
# Manual scaling
kubectl scale deployment myapp --replicas=5

# Auto-scaling (HPA)
kubectl autoscale deployment myapp \
    --cpu-percent=70 --min=2 --max=10

# View HPA
kubectl get hpa
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/myapp myapp=myapp:v2

# Check rollout status
kubectl rollout status deployment/myapp

# Rollback
kubectl rollout undo deployment/myapp

# View rollout history
kubectl rollout history deployment/myapp
```

### Resource Management

```yaml
# ResourceQuota per namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"

---
# LimitRange for defaults
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: team-a
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

### Security

```yaml
# Pod Security Standards
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
        add: ["NET_BIND_SERVICE"]
```

## Interview Questions

### Beginner

**Q: What is Kubernetes and why do we need it?**
A: Kubernetes is a container orchestration platform that automates deployment, scaling, and management of containerized applications across clusters. We need it because running containers in production requires handling scaling, self-healing, load balancing, rolling updates, and service discovery — all of which Kubernetes provides out of the box.

**Q: What is a Pod in Kubernetes?**
A: A Pod is the smallest deployable unit in Kubernetes. It's a group of one or more containers that share the same network namespace (IP address and port space) and storage volumes. Containers in a Pod can communicate via localhost. Pods are ephemeral — when they die, they're replaced, not resurrected.

### Intermediate

**Q: Explain the difference between a Deployment and a StatefulSet.**
A:
- **Deployment**: For stateless applications. Pods are interchangeable, can be created/destroyed in any order, get random names, and share a single Service endpoint.
- **StatefulSet**: For stateful applications (databases, caches). Pods have stable names (pod-0, pod-1), stable network identities, persistent storage, and are created/deleted in ordered sequence. Each Pod gets its own PersistentVolumeClaim.

**Q: How does Kubernetes service discovery work?**
A: Two methods:
1. **DNS**: CoreDNS runs in the cluster. A Service `myapp` in namespace `default` is resolvable as `myapp.default.svc.cluster.local`. Pods use this DNS name to find services.
2. **Environment variables**: When a Pod starts, Kubernetes injects `MYAPP_SERVICE_HOST` and `MYAPP_SERVICE_PORT` environment variables for each existing Service.

### FAANG-Level

**Q: Design a Kubernetes deployment for a microservices application with 10 services, each requiring different resource profiles, scaling policies, and security requirements.**

A:

```
Architecture:

1. Namespace isolation:
   ┌─────────────────────────────────────────┐
   │ Cluster                                 │
   │                                         │
   │ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
   │ │production│ │staging   │ │monitoring│ │
   │ │namespace │ │namespace │ │namespace │ │
   │ └──────────┘ └──────────┘ └──────────┘ │
   └─────────────────────────────────────────┘

2. Per-service configuration:
   
   API Gateway (high CPU, auto-scale):
   - resources: {cpu: 500m-2, memory: 256Mi-1Gi}
   - HPA: cpu=60%, min=3, max=20
   - PDB: minAvailable=2
   - Ingress with TLS

   Auth Service (medium, security-critical):
   - resources: {cpu: 250m-1, memory: 512Mi-2Gi}
   - HPA: cpu=70%, min=2, max=10
   - SecurityContext: runAsNonRoot, readOnlyFilesystem, drop ALL caps
   - Secret: JWT signing key via external secret store

   Database (StatefulSet):
   - resources: {cpu: 1-4, memory: 4Gi-16Gi}
   - StatefulSet with PVC (100Gi SSD)
   - PodAntiAffinity: spread across nodes
   - No HPA (fixed replicas=3)

   Cache (StatefulSet):
   - resources: {cpu: 500m-2, memory: 2Gi-8Gi}
   - StatefulSet, PVC for persistence
   - AntiAffinity: spread across zones

   Background Workers:
   - resources: {cpu: 250m-1, memory: 512Mi-2Gi}
   - Deployment, HPA: queue_length based (KEDA)
   - Lower priority (PriorityClass: low)

3. Network policies:
   # Only API gateway can reach auth service
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: auth-allow-gateway
   spec:
     podSelector:
       matchLabels:
         app: auth
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: api-gateway

4. Resource quotas:
   Production namespace:
     requests.cpu: 32
     requests.memory: 128Gi
     limits.cpu: 64
     limits.memory: 256Gi
     pods: 200

5. Monitoring:
   - Prometheus + Grafana for metrics
   - Custom metrics for HPA (queue length, latency)
   - Alerting on error rate, latency P99, resource exhaustion

6. GitOps deployment:
   - ArgoCD syncs from Git repository
   - All changes through PRs
   - Automated rollback on failure

7. Cost optimization:
   - Cluster autoscaler: scale nodes with demand
   - Spot instances for batch workers
   - Resource right-sizing based on actual usage
```

## Common Mistakes

1. **Not setting resource requests/limits**: Pods without limits can consume all resources, causing OOM kills for other pods.
2. **Using `latest` tag**: Always pin image versions for reproducibility.
3. **No health checks**: Without readiness/liveness probes, unhealthy pods receive traffic.
4. **No Pod Disruption Budgets**: During node maintenance, all replicas may be killed at once.
5. **Running everything as root**: Use `securityContext` to run as non-root.

## Summary

| Concept | Purpose |
|---------|---------|
| Pod | Smallest deployable unit |
| Deployment | Manages ReplicaSets, rolling updates |
| Service | Stable network endpoint |
| Ingress | External HTTP routing |
| ConfigMap/Secret | Configuration and secrets |
| PV/PVC | Persistent storage |
| HPA | Horizontal Pod Autoscaler |
| RBAC | Role-based access control |

## Cross-References

- [Containers Overview](README.md) — Container concepts
- [Cgroups](cgroups.md) — Resource limits K8s uses
- [Namespaces](namespaces.md) — Isolation K8s uses
- [Docker](docker.md) — Container runtime for K8s
- [Security: Access Control](../security/access-control.md) — K8s RBAC


## Cross References

- [Docker](../os/containers/docker.md)
- [K8s Pods](../cloud/kubernetes/pods.md)
- [K8s Deployments](../cloud/kubernetes/deployments.md)
- [Service Discovery](../distributed/microservices/discovery.md)
