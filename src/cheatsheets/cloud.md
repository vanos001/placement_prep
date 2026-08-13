# Cloud & DevOps Cheat Sheet

## Cloud Service Models

```
IaaS: VMs, storage, networking (EC2, GCE, Azure VMs)
PaaS: Runtime, managed (Elastic Beanstalk, App Engine, Heroku)
SaaS: End-user apps (Gmail, Slack, Salesforce)
FaaS/Serverless: Functions (Lambda, Cloud Functions, Azure Functions)
```

## AWS Key Services

| Category | Service | Use |
|----------|---------|-----|
| Compute | EC2 | Virtual machines |
| Compute | Lambda | Serverless functions |
| Compute | ECS/EKS | Container orchestration |
| Storage | S3 | Object storage |
| Storage | EBS | Block storage |
| Storage | EFS | File storage |
| Database | RDS | Managed SQL |
| Database | DynamoDB | NoSQL |
| Database | ElastiCache | Redis/Memcached |
| Database | Aurora | MySQL/PostgreSQL compatible |
| Network | VPC | Virtual network |
| Network | ELB | Load balancer |
| Network | CloudFront | CDN |
| Network | Route 53 | DNS |
| Messaging | SQS | Queue |
| Messaging | SNS | Pub/sub |
| Messaging | Kinesis | Stream processing |
| Analytics | Athena | Query S3 with SQL |
| ML | SageMaker | ML platform |

## Kubernetes Quick Reference

```yaml
# Core Objects
Pod: Smallest deployable unit (1+ containers)
Deployment: Manages ReplicaSets, rolling updates
Service: Stable network endpoint (ClusterIP, NodePort, LoadBalancer)
ConfigMap/Secret: Configuration management
Ingress: HTTP routing, TLS termination
PV/PVC: Persistent storage
Namespace: Resource isolation

# Key Commands
kubectl get pods -n <namespace>
kubectl logs <pod> -f
kubectl exec -it <pod> -- /bin/bash
kubectl apply -f manifest.yaml
kubectl rollout undo deployment/<name>
```

## Container vs VM

| | Container | VM |
|---|-----------|-----|
| Startup | Seconds | Minutes |
| Size | MBs | GBs |
| Isolation | Process-level | Hardware-level |
| OS | Shared kernel | Full OS |
| Density | 100s per host | 10s per host |

## CI/CD Pipeline

```
Code → Build → Test → Stage → Deploy → Monitor

Build: Compile, lint, unit tests
Test: Integration, e2e, security scan
Stage: Canary, blue-green, rolling
Deploy: Progressive rollout
Monitor: Metrics, logs, alerts
```

## Deployment Strategies

| Strategy | Downtime | Risk | Rollback Speed |
|----------|----------|------|----------------|
| Rolling | Zero | Medium | Fast |
| Blue-Green | Zero | Low | Instant |
| Canary | Zero | Low | Fast |
| Recreate | Yes | High | Slow |

## Observability Pillars

```
Metrics: Numbers over time (CPU, memory, request rate, error rate)
  → Prometheus, Grafana, CloudWatch

Logging: Structured events
  → ELK Stack, Loki, CloudWatch Logs

Tracing: Request flow across services
  → Jaeger, Zipkin, OpenTelemetry

Alerting: Threshold-based notifications
  → PagerDuty, OpsGenie, Alertmanager
```

## SLO/SLA/SLI

```
SLI: Service Level Indicator (measured metric, e.g., latency p99)
SLO: Service Level Objective (target, e.g., p99 < 200ms)
SLA: Service Level Agreement (contract with penalties)

Error Budget: 1 - SLO = allowed failure rate
```

## GitOps

```
Git as single source of truth
Declarative infrastructure (Terraform, Pulumi)
Automated reconciliation (ArgoCD, Flux)
Pull-based deployment (cluster pulls from git)
```

## Infrastructure as Code

| Tool | Type | Language |
|------|------|---------|
| Terraform | Declarative | HCL |
| Pulumi | Imperative/Declarative | Python/TS/Go |
| CloudFormation | Declarative | YAML/JSON |
| Ansible | Procedural | YAML |

## Cost Optimization

- Right-sizing instances
- Reserved/spot instances
- Auto-scaling policies
- Storage tiering (S3 Standard → Glacier)
- Delete unused resources
- Tag everything for cost allocation

## Interview Quick Tips

1. Know the trade-offs between services (RDS vs DynamoDB, SQS vs Kinesis)
2. Design for failure (multi-AZ, multi-region)
3. Security: least privilege, encrypt at rest and in transit
4. Cost matters: mention reserved capacity, spot instances
5. Monitoring is not optional: discuss what to measure
