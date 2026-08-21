# AWS EKS (Elastic Kubernetes Service)

Amazon EKS is AWS's managed Kubernetes service, launched in 2018. It runs the open-source Kubernetes control plane (API server, etcd, scheduler, controller-manager) on AWS-managed infrastructure, with the data plane on EC2 instances (customer-managed) or Fargate (AWS-managed). This page covers the architecture, the control plane management, the data plane options, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  EKS Control Plane (AWS-managed)                            │
│  - Kubernetes API server (multi-AZ, HA)                    │
│  - etcd (multi-AZ, HA, automated backups)                  │
│  - Scheduler, controller-manager (AWS-managed)              │
│  - Auth: integrates with AWS IAM                            │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ API calls (kubernetes API)  │ node registration
        ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  Managed Node Group        │    │  Fargate profile           │
│  (EC2 instances, managed   │    │  (serverless pods)         │
│   by EKS via ASG)          │    └──────────────────────────┘
└──────────────────────────┘
        │                              │
        │ AWS-managed AMI              │
        ▼                              ▼
    EC2 instances                  Fargate (Firecracker)
```

EKS abstracts the control plane; you manage the data plane (worker nodes).

## The Control Plane

AWS manages:
- The API server (across multiple AZs).
- etcd (multi-AZ replication; automated backups).
- The scheduler and controller-manager.
- Control plane scaling (based on cluster size).
- Security patches (for the control plane).

The user connects to the API server via a public or private endpoint:
- **Public endpoint**: accessible from the internet; requires IAM auth.
- **Private endpoint**: accessible only from within the VPC; requires VPC peering or transit gateway.

```bash
aws eks create-cluster --name my-cluster --role-arn arn:aws:iam::123:role/eks-cluster --resourcesVpcConfig subnetIds=...,securityGroupIds=...
```

## IAM Authentication

EKS integrates with AWS IAM for authentication:

```bash
# Configure kubectl to use AWS IAM auth
aws eks update-kubeconfig --name my-cluster --region us-east-1

# This generates a kubeconfig with:
# users:
# - name: aws
#   user:
#     exec:
#       apiVersion: client.authentication.k8s.io/v1beta1
#       command: aws
#       args: ["eks", "get-token", "--cluster-name", "my-cluster"]
```

Each user/role that needs cluster access is mapped to a Kubernetes user/group via the `aws-auth` ConfigMap (or via EKS Access Entries since EKS 1.29+).

```bash
# Add an IAM role to the cluster
kubectl edit configmap aws-auth -n kube-system
# Add:
# data:
#   mapRoles: |
#     - rolearn: arn:aws:iam::123:role/my-role
#       username: my-role
#       groups:
#       - system:masters
```

## The Data Plane: Managed Node Groups

A "managed node group" is an EC2 Auto-Scaling Group managed by EKS:

```bash
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name my-nodes \
    --subnets subnet-... --instance-types t3.medium --scaling-config minSize=3,maxSize=10,desiredSize=3 \
    --node-role arn:aws:iam::123:role/eks-node
```

EKS-managed features:
- Auto-scaling (based on pod scheduling pressure).
- Rolling updates (when Kubernetes version or AMI changes).
- Spot instance support (with graceful drain).
- Bottlerocket / Amazon Linux 2 / custom AMI support.

Managed node groups are the standard data plane for most EKS deployments.

## The Data Plane: Fargate

For serverless pods, use Fargate:

```bash
aws eks create-fargate-profile --cluster-name my-cluster --fargate-profile-name my-profile \
    --pod-execution-role-arn arn:aws:iam::123:role/eks-fargate \
    --selectors namespace=default,labels={app=my-app}
```

Pods matching the selector (namespace + labels) run on Fargate instead of EC2. Each pod gets its own Firecracker micro-VM with an ENI.

Fargate trade-offs:
- **Pro**: no EC2 to manage, per-pod billing.
- **Con**: 10-30% more expensive than EC2, no DaemonSets (each pod is isolated).

## Production Deployment Patterns

### Pattern 1: Multi-AZ Managed Node Group

```bash
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name standard \
    --subnets subnet-az1,subnet-az2,subnet-az3 \
    --instance-types t3.large \
    --scaling-config minSize=6,maxSize=20,desiredSize=6
```

6 instances spread across 3 AZs (2 per AZ); auto-scales to 20 max.

### Pattern 2: Spot + On-Demand Mix

```bash
# Two node groups: Spot for stateless, On-Demand for stateful
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name spot \
    --instance-types "c5.large,c5a.large,m5.large" --capacity-type SPOT \
    --scaling-config minSize=3,maxSize=100,desiredSize=10

aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name on-demand \
    --instance-types "m5.large" --capacity-type ON_DEMAND \
    --scaling-config minSize=3,maxSize=10,desiredSize=3
```

Stateless pods on Spot (cheaper, tolerates interruption); stateful on On-Demand (reliable).

### Pattern 3: Bottlerocket AMI

Bottlerocket is AWS's container-optimized OS (smaller, more secure):

```bash
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name bottlerocket \
    --ami-type BOTTLEROCKET_x86_64 \
    --instance-types m5.large \
    --scaling-config minSize=3,maxSize=10,desiredSize=3
```

Bottlerocket has no shell, no package manager; updates are atomic (reboot to apply). More secure than Amazon Linux.

## The EKS Add-Ons

EKS offers managed add-ons for common components:

```bash
# Install the VPC CNI (for pod networking)
aws eks create-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.16.0

# Install the kube-proxy
aws eks create-addon --cluster-name my-cluster --addon-name kube-proxy --addon-version v1.28.0

# Install CoreDNS
aws eks create-addon --cluster-name my-cluster --addon-name coredns --addon-version v1.10.1
```

EKS-managed add-ons are versioned with the cluster; upgrades are coordinated.

## Production Performance

EKS limits (per cluster):
- Max nodes: 1000 (default; can be raised).
- Max pods per node: depends on instance type (default 110, can be raised with `--max-pods`).
- Max pods per cluster: 150,000 (theoretical).

The control plane auto-scales; you don't manage it.

## Common Pitfalls

1. **Forgetting that EKS control plane has SLA but no SLA for nodes.** If a node fails, the control plane is fine, but your pods need to be rescheduled. Use multi-AZ deployments for HA.

2. **Forgetting that the VPC CNI consumes ENIs.** Each pod gets an IP from the VPC's subnet. Subnet exhaustion is a common EKS issue. Use "prefix delegation" (one ENI gets 16 IPs) for high-density nodes.

3. **Forgetting that EKS Fargate pods can't use DaemonSets.** DaemonSets (e.g., for logging agents, monitoring) need EC2 nodes. Run them on a small EC2 node group alongside Fargate.

4. **Forgetting that IAM is the auth mechanism.** Without proper IAM roles, users can't access the cluster. Use AWS SSO + IAM Identity Center for team-based access.

5. **Forgetting that the EKS API server has rate limits.** The API server has a per-cluster QPS limit (~300/sec for default clusters). For high-throughput operators (e.g., the Kubernetes scheduler), this can be a bottleneck.

6. **Forgetting that EKS upgrades take time.** A cluster upgrade (e.g., 1.27 → 1.28) involves: (1) upgrade the control plane (AWS-managed, ~30 minutes), (2) upgrade the nodes (rolling), (3) upgrade the add-ons. Plan for ~2 hours per major version.

## Comparison to Other Managed K8s

| Aspect | EKS | GKE (Google) | AKS (Azure) | OpenShift |
|--------|-----|---------------|---------------|-----------|
| Control plane | AWS-managed | Google-managed | Azure-managed | Red Hat-managed |
| Pricing | $0.10/hour + EC2/Fargate | Free (control plane) for standard; paid for autopilot | Free (control plane) | Per-core pricing |
| Data plane | EC2 or Fargate | GCE or Autopilot | AKS or ACI | Any |
| Best for | AWS-native | GCP-native | Azure-native | Enterprise |

EKS, GKE, and AKS are similar; the choice depends on the cloud you're already in. OpenShift is for enterprises that want Red Hat's support.

## References

- [AWS EKS documentation](https://docs.aws.amazon.com/eks/latest/userguide/)
- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices-guide/)
- [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [EKS IAM Auth](https://docs.aws.amazon.com/eks/latest/userguide/cluster-auth.html)
- [EKS Add-Ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [EKS vs GKE vs AKS comparison](https://www.cloudzero.com/blog/eks-vs-gke-vs-aks)
- [LWN: AWS EKS overview (2022)](https://lwn.net/Articles/820133/)
