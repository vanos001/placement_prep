# Kubernetes Security Deep Dive

## RBAC (Role-Based Access Control)

Kubernetes RBAC controls who can perform which actions on which resources. It has four object types:

| Object | Scope | Binds To |
|--------|-------|----------|
| `Role` | Single namespace | RoleBinding |
| `ClusterRole` | Cluster-wide | ClusterRoleBinding or RoleBinding |
| `RoleBinding` | Single namespace | Users, groups, service accounts |
| `ClusterRoleBinding` | Cluster-wide | Users, groups, service accounts |

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: pod-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: production
subjects:
  - kind: ServiceAccount
    name: app-sa
    namespace: production
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

A `ClusterRole` bound via a `RoleBinding` grants only the namespaced permissions within that binding's namespace—this is the recommended pattern for reusing cluster-wide roles at namespace scope.

Common built-in ClusterRoles:

| ClusterRole | Purpose |
|-------------|---------|
| `cluster-admin` | Full cluster access (superuser) |
| `admin` | Full access within a namespace, plus read roles |
| `edit` | Read/write in a namespace (no RBAC management) |
| `view` | Read-only in a namespace |

## Network Policies

Network policies are layer 3/4 firewalls that control traffic between pods. By default, all pod-to-pod traffic is **allowed**. A NetworkPolicy only restricts traffic—it cannot grant access that is otherwise denied by the CNI.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - port: 5432
    - to:  # Allow DNS
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - port: 53
          protocol: UDP
```

Key points:
- Selecting no pods (`podSelector: {}`) applies the policy to **all** pods in the namespace
- An empty `ingress: []` or `egress: []` blocks **all** traffic of that direction
- CNI must support NetworkPolicy (Calico, Cilium do; Flannel does not natively without Calico/Calico Enterprise)

## Pod Security Standards

Pod Security Admission (PSA) replaces the deprecated PodSecurityPolicy (PSP) since K8s 1.25. Three built-in policy levels:

| Standard | Description | Key Restrictions |
|----------|-------------|-----------------|
| **Privileged** | Unrestricted | No restrictions at all |
| **Baseline** | Minimally restrictive | Prevents known privilege escalations: no host namespace, no host PID/IPC, must run as non-root (unless pre-registered UID), blocks new privileged containers, blocks dangerous capabilities, blocks volume types (hostPath, etc.) |
| **Restricted** | Heavily restricted | Everything in Baseline + must run as non-root, drops all capabilities, seccomp profile enforced, SELinux restricted, must request security context, read-only root filesystem |

Applied per namespace via labels:

```yaml
# Enforce restricted policy in production
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

| Mode | Behavior |
|------|----------|
| `enforce` | Violations cause pod rejection |
| `audit` | Violations logged as audit annotations |
| `warn` | Violations trigger user-facing warnings |

## Service Account Management

Every pod runs with a service account (SA). By default, this is the `default` SA in the pod's namespace, which has no permissions—but its token is mounted and could be leaked.

```yaml
# Create a dedicated SA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: production
automountServiceAccountToken: false  # Don't mount token unless needed
---
# Use the SA in a pod
spec:
  serviceAccountName: app-sa
  automountServiceAccountToken: false
```

Best practices:
- Never use `default` SA for workloads
- Create dedicated SAs per workload or per team
- Set `automountServiceAccountToken: false` if the pod doesn't need API access
- Bind the SA to minimal RBAC roles (principle of least privilege)
- Rotate SA tokens (K8s 1.24+ uses bound tokens with 1-hour expiry by default)

## Secrets Management

### Native Secrets

```yaml
apiVersion: v1
kind: Secret
type: Opaque
stringData:
  password: super-secret
data:
  username: YWRtaW4=  # base64 encoded
```

Limitations: stored in etcd as base64 (not encrypted at rest by default), no fine-grained access control beyond RBAC, no rotation mechanism, no audit trail.

### Encryption at Rest

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}  # fallback to unencrypted
```

### External Solutions

| Solution | Approach | Key Feature |
|----------|----------|-------------|
| **Sealed Secrets** (Bitnami) | Encrypt secrets client-side; only the controller in-cluster can decrypt | Simple, GitOps-friendly |
| **External Secrets Operator** | Syncs secrets from AWS Secrets Manager, GCP Secret Manager, Azure Key Vault | Cloud-native integration |
| **HashiCorp Vault** | Centralized secrets platform with dynamic secrets, PKI, transit encryption | Most feature-rich, complex to operate |
| **SOPS** (Mozilla) | Encrypts entire files; decryption via KMS at deploy time | File-based, works with Flux/ArgoCD |

Sealed Secrets workflow:
1. Developer runs `kubeseal < secret.yaml > sealed-secret.yaml`
2. Sealed Secret contains an encrypted blob—safe to commit to Git
3. Sealed Secrets Controller in the cluster decrypts and creates a standard Secret

## Image Security

### Image Scanning

Scan container images for known CVEs before they reach the cluster:

| Tool | Type | Integration |
|------|------|-------------|
| **Trivy** (Aqua) | Vulnerability scanner | CLI, CI/CD, admission controller |
| **Grype** (Anchore) | Vulnerability scanner | CLI, CI/CD |
| **Clair** (Quay) | Vulnerability scanner | Daemon, API server |
| **Snyk** | Commercial scanner | CI/CD, IDE, registry integration |

### Image Admission Control

Block unscanned or vulnerable images at the gate:

```yaml
# OPA Gatekeeper example: require image from trusted registry
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: trustedregistry
spec:
  crd:
    spec:
      names:
        kind: TrustedRegistry
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        violation[{"msg": "Image not from trusted registry"}] {
          not startswith(input.review.object.spec.containers[_].image, "registry.internal.com/")
        }
```

### Signed Images

- **Cosign** (Sigstore): Sign and verify container images using keyless signing (OIDC-based) or key-based signing
- **Notation** (Notary v2): OCI-native image signing
- Admission webhooks can enforce signature verification before allowing a pod to run

```bash
# Sign an image
cosign sign --key cosign.key registry.internal.com/app:v1.2.0

# Verify in an admission webhook or CI pipeline
cosign verify --key cosign.pub registry.internal.com/app:v1.2.0
```

## References

- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)

## Interview Questions

### Q1: How does RBAC work in Kubernetes?
**Answer**: RBAC has four objects: Role/ClusterRole define permissions (API groups, resources, verbs), and RoleBinding/ClusterRoleBinding connect those permissions to subjects (users, groups, service accounts). Roles are namespace-scoped; ClusterRoles are cluster-wide. A ClusterRole can be bound at namespace scope via a RoleBinding, granting only namespace-level permissions. The API server evaluates RBAC on every request after authentication.

### Q2: What is the default behavior of network policies and why does it matter?
**Answer**: By default, **all** pod-to-pod traffic is allowed in Kubernetes. Network policies can only restrict—they cannot open traffic that's already allowed. This means a misconfigured or absent network policy leaves your pods exposed to lateral movement. In production, you should apply a default-deny policy to each namespace and then explicitly allow only required traffic.

### Q3: How would you manage secrets in a production Kubernetes cluster?
**Answer**: I would avoid native Secrets in etcd as the primary solution. Instead, use **External Secrets Operator** to sync from a cloud KMS (AWS Secrets Manager/GCP Secret Manager), or **Sealed Secrets** for a GitOps workflow where encrypted secrets are committed to the repo. For the most sensitive workloads, **HashiCorp Vault** with the Vault Agent injector provides dynamic secrets, automatic rotation, and fine-grained audit trails. I'd also enable encryption at rest for etcd as a defense-in-depth measure, and use OPA/Gatekeeper to enforce that no secret values appear in ConfigMaps or environment variables directly.

### Q4: Explain Pod Security Standards and their migration from PSP.
**Answer**: Pod Security Admission (PSA) replaced PodSecurityPolicy in K8s 1.25. PSA applies one of three policies at the namespace level via labels: **Privileged** (no restrictions), **Baseline** (prevents known privilege escalations like host namespace, hostPath, privileged containers), and **Restricted** (additionally requires non-root, drops all capabilities, read-only root filesystem). You apply them with enforce/audit/warn modes. Unlike PSP, PSA is simpler but less flexible. For advanced use cases, teams migrate to OPA Gatekeeper or Kyverno.

### Q5: How do you prevent untrusted container images from running in your cluster?
**Answer**: Defense in depth: (1) **Image scanning** with Trivy/Grype in CI/CD to catch CVEs before images reach the registry. (2) **Admission controllers** (OPA Gatekeeper or Kyverno) to enforce policies: only allow images from trusted registries, reject critical CVEs, require signed images. (3) **Image signing** with Cosign to verify provenance and integrity at deploy time. (4) **Private registry** with access controls so developers can only pull from approved registries. (5) **Periodic re-scanning** of running workloads since new CVEs are discovered over time.
