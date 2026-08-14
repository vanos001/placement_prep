# Kubernetes Storage Deep Dive

## Volume Types

Volumes provide storage to pods that outlives the container's lifecycle (but not the pod's lifecycle, except for PersistentVolumes).

| Volume Type | Lifetime | Use Case |
-------------|----------|----------|
| **emptyDir** | Pod lifetime | Scratch space, sidecar communication, caching |
| **hostPath** | Node lifetime | Development, node daemon access (avoid in production) |
| **configMap** | ConfigMap lifetime | Inject configuration files into containers |
| **secret** | Secret lifetime | Inject sensitive data as files or env vars |
| **downwardAPI** | Pod lifetime | Expose pod metadata (name, labels, annotations) as files |
| **persistentVolumeClaim** | Independent of pod | Databases, stateful applications |
| **nfs** | External | Shared file storage across pods |
| **iscsi / ceph rbd / awsElasticBlockStore** | External | Block storage for databases |

### emptyDir
```yaml
volumes:
  - name: cache-volume
    emptyDir:
      medium: Memory  # Uses tmpfs (RAM-backed), limited by node memory
      sizeLimit: 256Mi
```

Default emptyDir uses the node's disk. With `medium: Memory`, it uses RAM (tmpfs)—fast but counts against the pod's memory limit. Common use case: a sidecar container writes to an emptyDir volume that the main container reads from (e.g., log shipper sidecar).

## PersistentVolumes and PersistentVolumeClaims

The PV/PVC abstraction decouples storage provisioning from consumption.

```
┌──────────────────┐     ┌───────────────────────────┐     ┌──────────────────┐
│    Admin/         │     │  PV: 50Gi SSD, RWO       │     │  Pod             │
│  Dynamic          │────▶│  PVC: 10Gi, ReadWriteOnce│◀────│  mounts PVC       │
│  Provisioning     │     │  StorageClass: fast-ssd   │     │                  │
└──────────────────┘     └───────────────────────────┘     └──────────────────┘
```

| Concept | Role | Who Creates |
---------|------|-------------|
| **PV** | Actual storage resource in the cluster | Admin or dynamic provisioning |
| **PVC** | Storage request (size, access mode, class) | Developer (user) |
| **StorageClass** | Provisioner + parameters for dynamic provisioning | Admin |

Access modes:

| Access Mode | Abbreviation | Supported By |
-------------|-------------|---------------|
| ReadWriteOnce | RWO | 1 node (block storage) |
| ReadOnlyMany | ROX | Multiple nodes (file storage) |
| ReadWriteMany | RWX | Multiple nodes (file storage: NFS, CephFS, EFS) |
| ReadWriteOncePod | RWOP | Exactly 1 pod (K8s 1.27+, prevents multi-attach) |

## Storage Classes

StorageClasses enable dynamic provisioning—PVCs are automatically fulfilled without pre-created PVs.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "5000"
  throughput: "250"
  encrypted: "true"
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

| Parameter | Effect |
-----------|--------|
| `reclaimPolicy: Retain` | PV kept after PVC deleted (data preserved, manual cleanup needed) |
| `reclaimPolicy: Delete` | PV and underlying volume automatically deleted |
| `volumeBindingMode: Immediate` | PVC bound immediately (may schedule on wrong node) |
| `volumeBindingMode: WaitForFirstConsumer` | PVC bound only when pod using it is scheduled (zone-aware) |
| `allowVolumeExpansion: true` | Allows resizing PVCs |

**WaitForFirstConsumer** is critical for zone-aware provisioning (EBS, PD). Without it, the volume might be provisioned in `us-east-1a` while the pod gets scheduled in `us-east-1b`, causing a mount failure.

## StatefulSet Volume Management

StatefulSets use volume claim templates to provision a unique PVC per pod:

```yaml
apiVersion: apps/v1
kind: StatefulSet
spec:
  serviceName: "mysql-headless"
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 100Gi
```

This creates PVCs named `data-mysql-0`, `data-mysql-1`, etc. When pod `mysql-2` is deleted and recreated, it reclaims `data-mysql-2`. This identity is why StatefulSets are used for databases.

## CSI (Container Storage Interface)

CSI is the standard interface for storage vendors to integrate with Kubernetes. Before CSI, storage drivers were compiled into the Kubernetes binary (in-tree plugins).

| Aspect | In-Tree (deprecated) | CSI |
--------|---------------------|-----|
| Code location | Kubernetes source | External container/image |
| Release cycle | Tied to K8s releases | Independent vendor releases |
| Install | Built-in | Deploy as DaemonSet + StatefulSet + CSIDriver |

CSI architecture:

```
  Kubelet ──▶ CSI Node Plugin (on each node)
                  │
                  ▼
             CSI Controller Plugin (on control plane or as operator)
                  │
                  ▼
           Storage Backend (EBS, GCE PD, NFS, Ceph, etc.)
```

Major CSI drivers:

| Driver | Storage | Notes |
--------|---------|-------|
| `ebs.csi.aws.com` | AWS EBS | EKS default |
| `pd.csi.storage.gke.io` | GCE Persistent Disk | GKE default |
| `disk.csi.azure.com` | Azure Disk | AKS default |
| `secrets-store.csi.k8s.io` | External secrets | Mounts secrets as volumes |
| `cephfs.csi.ceph.com` | CephFS | File storage, RWX |
| `rbd.csi.ceph.com` | Ceph RBD | Block storage, RWO |

## References

- [Kubernetes Storage Concepts](https://kubernetes.io/docs/concepts/storage/)
- [CSI Specification](https://github.com/container-storage-interface/spec)
- [Dynamic Provisioning](https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/)

## Interview Questions

### Q1: What is the difference between a Volume, a PersistentVolume, and a PersistentVolumeClaim?
**Answer**: A **Volume** is defined in the pod spec and has the same lifetime as the pod—when the pod is deleted, the volume's data is gone (except for some types like hostPath). A **PersistentVolume (PV)** is a cluster-level resource representing actual storage (a disk, NFS share, etc.) with an independent lifecycle. A **PersistentVolumeClaim (PVC)** is a user's request for storage—specifying size, access mode, and storage class. The PVC is bound to a PV (statically by admin or dynamically via StorageClass), and the PVC is referenced in the pod spec. The PVC can outlive pods that mount it.

### Q2: Why is WaitForFirstConsumer important for StorageClasses?
**Answer**: Cloud block storage (EBS, GCE PD, Azure Disk) is zone-specific. With `volumeBindingMode: Immediate`, the PVC is bound to a PV before the pod is scheduled—so the volume might be created in `us-east-1a` while the scheduler places the pod in `us-east-1b`, causing a mount failure. `WaitForFirstConsumer` delays PVC binding until a pod that uses it is scheduled. The scheduler then selects a node, and the volume is provisioned in the same zone. This prevents zone mismatch failures.

### Q3: How does StatefulSet volume management differ from Deployment?
**Answer**: StatefulSets use `volumeClaimTemplates` which create a unique, named PVC for each pod replica (e.g., `data-mysql-0`, `data-mysql-1`). When a pod is deleted and recreated, it reattaches to the same PVC, preserving data identity. Deployments share a PVC template but all pods could theoretically share one PVC (with RWX) or get ephemeral volumes. StatefulSets also guarantee ordered creation/deletion, so pod-1 isn't created until pod-0 is running, and pod-0 isn't deleted until all others are down.

### Q4: What is CSI and why did Kubernetes move away from in-tree storage drivers?
**Answer**: CSI (Container Storage Interface) is a standardized gRPC interface that decouples storage drivers from Kubernetes core. Previously, storage drivers were compiled into the Kubernetes binary (in-tree), meaning any driver bug or update required a Kubernetes release. CSI moves drivers to external plugins, allowing vendors to release independently, support multiple K8s versions, and innovate without the K8s release cycle. CSI drivers run as DaemonSets (node plugin) and StatefulSets/Deployments (controller plugin) on the cluster.

### Q5: When would you use emptyDir vs. a PVC?
**Answer**: Use **emptyDir** for temporary, ephemeral data that the pod needs during its lifetime but doesn't need to persist across restarts: scratch space, caching, git clone workspaces, or shared data between containers in the same pod (sidecar pattern). Use a **PVC** when data must survive pod deletion/recreation: databases, file uploads, application state. An emptyDir with `medium: Memory` (tmpfs) is useful for high-speed temporary data like computation intermediaries. A common mistake is using emptyDir for data that should persist—when the pod reschedules, the data is lost.
