# DevOps Project Implementation Guides

Practical DevOps and infrastructure projects that demonstrate you understand how software gets built, tested, deployed, and monitored at scale. These projects go beyond using managed services — you build the infrastructure yourself. Complements the ideas in [project-ideas.md](project-ideas.md).

---

## 1. CI/CD Pipeline from Scratch

### What to Build
A lightweight CI/CD engine (not using GitHub Actions or Jenkins) that watches a Git repository, runs build steps on push, executes tests, builds Docker images, and deploys to a target environment. Build your own pipeline runner to understand what tools like Jenkins actually do.

### Why It Matters
Every company has CI/CD, but few engineers understand how it works under the hood. Building one from scratch separates you from engineers who only configure YAML files.

### Suggested Tech Stack
- **Language**: Go or Python
- **Git Integration**: Git CLI or go-git library (watch via webhooks)
- **Execution**: Docker-in-Docker or child processes with isolated workspaces
- **Artifact Storage**: Local filesystem or S3-compatible storage
- **Web UI**: Simple HTML + WebSocket for live build logs

### Architecture

```
Git Push → Webhook → Pipeline Scheduler
                          │
                    ┌─────┼─────┐
                    ▼     ▼     ▼
               Builder Builder Builder  (parallel stages)
                    │     │     │
                    └─────┼─────┘
                          ▼
                    Test Runner
                          │
                    ┌─────┼─────┐
                    ▼           ▼
               Docker Build   Artifact Store
                    │
                    ▼
               Deploy (SSH/K8s API)
```

### Key Implementation Details
- **Pipeline DSL**: YAML or simple TOML config defining stages, dependencies, and triggers
- **Workspace isolation**: each build runs in a clean Docker container
- **Log streaming**: stream build output to WebSocket in real-time
- **Artifact management**: versioned artifacts with metadata

### Pipeline Config Example
```yaml
pipeline:
  trigger: push
  branch: main
  stages:
    - name: build
      image: golang:1.21
      commands:
        - go build ./...
    - name: test
      image: golang:1.21
      commands:
        - go test -v ./...
    - name: docker
      image: docker:latest
      commands:
        - docker build -t myapp:${COMMIT_SHA} .
    - name: deploy
      image: alpine
      commands:
        - kubectl set image deployment/myapp myapp=myapp:${COMMIT_SHA}
```

### Interview Discussion Points
- "What is Docker-in-Docker and why is it controversial?" → security, nested containers, privileged mode
- "How do you handle flaky tests?" → retry mechanism, quarantine, test history tracking
- "How does your pipeline compare to GitHub Actions?" → ours is simpler but demonstrates the core concepts
- "How do you prevent secrets in pipeline configs?" → encrypted environment variables, vault integration

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 2. Kubernetes Cluster Setup with Monitoring

### What to Build
Deploy a production-like Kubernetes cluster (using kubeadm or k3s on VMs, or minikube locally) running a sample microservice application with:
- Ingress controller with TLS termination
- Horizontal Pod Autoscaler
- Persistent volume claims
- Prometheus + Grafana monitoring stack
- Centralized logging (EFK stack or Loki)

### Why It Matters
Kubernetes is the de facto container orchestration platform. Setting it up end-to-end (not just `kubectl apply`) demonstrates operational maturity that separates practitioners from dabblers.

### Suggested Tech Stack
- **Cluster**: k3s (lightweight) on 3 VMs, or minikube for local
- **Workload**: 3-tier microservice app (frontend, API, database)
- **Monitoring**: Prometheus Operator + Grafana
- **Logging**: Promtail + Loki or Fluent Bit + Elasticsearch
- **Ingress**: NGINX Ingress Controller with cert-manager for TLS

### Architecture

```
                  ┌────────────────────────┐
                  │     Load Balancer      │
                  └──────────┬─────────────┘
                             ▼
                  ┌────────────────────────┐
                  │  Ingress Controller    │
                  │  (NGINX + cert-manager)│
                  └──────────┬─────────────┘
                             ▼
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │ Frontend  │      │ API Svc   │      │ Worker    │
   │ (React)   │─────►│ (Node.js) │─────►│ (Go)      │
   └───────────┘      └─────┬─────┘      └───────────┘
                            ▼
                     ┌───────────┐
                     │ PostgreSQL │
                     │ (PVC)      │
                     └───────────┘

Monitoring:
  Prometheus → Grafana (dashboards)
  Pods → Promtail → Loki (logs)
  Alerts → AlertManager → Slack/Email
```

### Key Implementation Steps
1. **Cluster bootstrap**: k3s install on 3 nodes (1 master, 2 workers)
2. **Namespace isolation**: separate namespaces for app, monitoring, logging
3. **Deploy app**: Helm charts or raw manifests with resource limits
4. **Add monitoring**: Prometheus Operator with service monitors
5. **Add logging**: Loki stack with Promtail daemonset
6. **Create dashboards**: CPU, memory, request latency, error rate, pod restarts
7. **Set up alerts**: 90% CPU for 5 minutes, pod crash loop, PVC filling up

### Interview Discussion Points
- "What is a ServiceMonitor and why is it better than annotating pods?"
- "How does HPA work under the hood?" → metrics server, replica count calculation
- "Why Loki over Elasticsearch for Kubernetes logs?" → simpler, cheaper, better label-based querying
- "How do you handle secrets in Kubernetes?" → Sealed Secrets, External Secrets Operator, Vault CSI

### Difficulty: Intermediate-Hard | Estimated Time: 2–3 weeks

---

## 3. Infrastructure as Code with Terraform

### What to Build
Use Terraform to provision a complete cloud infrastructure: VPC, subnets, security groups, EC2 instances, RDS database, S3 buckets, and an application load balancer. Include modular design, remote state with locking, and CI/CD for Terraform itself (Atlantis or GitHub Actions).

### Why It Matters
IaC is a non-negotiable skill for modern infrastructure teams. Building a Terraform project shows you can codify and version-control infrastructure.

### Suggested Tech Stack
- **IaC**: Terraform with modules
- **State Backend**: S3 + DynamoDB for locking
- **Provider**: AWS (most common) or GCP/Azure
- **CI**: GitHub Actions running `terraform plan` on PRs, `terraform apply` on merge

### Module Structure
```
terraform/
├── main.tf                 # Root module orchestration
├── variables.tf
├── outputs.tf
├── backend.tf              # S3 state backend config
├── modules/
│   ├── networking/
│   │   ├── main.tf         # VPC, subnets, route tables, IGW
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   │   ├── main.tf         # EC2 launch template, ASG, ALB
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf         # RDS instance, subnet group, param group
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/
│   │   └── terraform.tfvars
│   └── prod/
│       └── terraform.tfvars
```

### Key Practices to Implement
- **Remote state with locking**: S3 backend + DynamoDB table for state locking
- **State isolation per environment**: separate state files for dev/staging/prod
- **Variable validation**: custom validation blocks in Terraform
- **Output values**: expose resource IDs and endpoints for other modules or tools
- **Import existing resources**: `terraform import` for brownfield adoption

### Interview Discussion Points
- "How do you handle state file drift?" → `terraform plan` to detect, `terraform import` for existing resources
- "What happens if two people run `terraform apply` simultaneously?" → state locking prevents concurrent writes
- "How do you manage secrets in Terraform?" → Vault provider, AWS Secrets Manager, or SSM Parameter Store
- "How do you roll back a bad Terraform change?" → version control, `terraform rollback` (enterprise), or manual `terraform apply` of previous state

### Difficulty: Intermediate | Estimated Time: 2 weeks

---

## 4. GitOps Workflow

### What to Build
Implement a GitOps workflow where the desired state of Kubernetes is stored in Git, and any change to Git automatically triggers reconciliation. Build (or configure) the controller that watches Git and applies changes to the cluster.

### Why It Matters
GitOps is the modern standard for declarative infrastructure management. It provides auditability, rollback via Git history, and a single source of truth.

### Suggested Tech Stack
- **GitOps Tool**: ArgoCD or Flux (configure, don't build from scratch)
- **Source**: GitHub repository with Kustomize overlays for environments
- **Cluster**: k3s or minikube
- **Notification**: ArgoCD webhooks → Slack on deployment events

### Repository Structure
```
k8s-manifests/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── replica-count.yaml    # 1 replica
│   └── prod/
│       ├── kustomization.yaml
│       └── replica-count.yaml    # 5 replicas
└── argocd-app.yaml                # ArgoCD Application manifest
```

### Key Concepts
- **Desired state in Git**: Kubernetes manifests committed and reviewed via PR
- **Reconciliation loop**: controller continuously compares Git state vs. cluster state
- **Drift detection**: if someone manually changes the cluster, the controller reverts it
- **Rollback**: `git revert` the commit → controller restores previous state

### Interview Discussion Points
- "Why GitOps over imperative `kubectl apply`?" → audit trail, declarative, rollback, self-healing
- "How do you handle secrets in Git?" → Sealed Secrets, SOPS, or External Secrets
- "What is drift and how does GitOps handle it?" → manual cluster changes are detected and reverted
- "How do you promote between environments?" → Kustomize overlays, or Helm values per environment

### Difficulty: Intermediate | Estimated Time: 1–2 weeks

---

## 5. Container Orchestration (Build Your Own Mini-K8s)

### What to Build
A simplified container orchestrator that can schedule Docker containers across multiple nodes based on resource availability, perform health checks, restart failed containers, and provide a basic API for management.

### Why It Matters
Building even a toy orchestrator gives you deep intuition for how Kubernetes works — scheduling, health checking, service discovery, and the control loop pattern.

### Suggested Tech Stack
- **Language**: Go (Docker SDK + HTTP API)
- **Runtime**: Docker Engine API (not docker CLI)
- **Communication**: gRPC between nodes and the control plane
- **Discovery**: Simple etcd or Consul for cluster state

### Key Components
1. **API Server**: REST endpoint for submitting container specs
2. **Scheduler**: assigns containers to nodes based on CPU/memory constraints
3. **Agent**: runs on each node, manages containers via Docker API, reports health
4. **Health Checker**: HTTP or TCP health probes, restart policy

### Interview Discussion Points
- "How does your scheduler compare to kube-scheduler?" → simplified, no affinity/anti-affinity, no preemption
- "What is the control loop pattern?" → observe → diff → act (reconcile loop)
- "How do you handle node failures?" → heartbeat timeout → reschedule containers to healthy nodes
- "Why is this project valuable?" → understanding internals helps debug real Kubernetes issues

### Difficulty: Very Hard | Estimated Time: 4–6 weeks

---

## Project Selection Guide

| Your Level | Recommended Starting Point |
|---|---|
| DevOps beginner | #2 K8s Setup + Monitoring, #4 GitOps Workflow |
| DevOps intermediate | #3 Terraform IaC, #1 CI/CD Pipeline |
| Systems/Platform engineer | #5 Build Your Own Orchestrator |
| Interview prep (2 weeks) | #2 K8s Setup (most bang for buck) |
