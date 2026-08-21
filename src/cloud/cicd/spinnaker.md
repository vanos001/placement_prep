# Spinnaker (Continuous Delivery Platform)

Spinnaker is an open-source multi-cloud continuous delivery platform, originally developed at Netflix in 2014 and donated to CNCF. It provides a unified API for deploying to multiple cloud targets (AWS, GCP, Azure, Kubernetes), with sophisticated deployment strategies (blue/green, canary, rolling) and a web UI for visibility. This page covers the architecture, the application model, the deployment strategies, and the comparison to ArgoCD and Flux.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Spinnaker Services (microservices)                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Deck (UI)                                              │ │
│  │  Gate (API gateway)                                     │ │
│  │  Orca (orchestration engine)                            │ │
│  │  Clouddriver (cloud provider interface)                 │ │
│  │  Front50 (persistence)                                  │ │
│  │  Rosco (image baking)                                  │ │
│  │  Igor (CI integration)                                  │ │
│  │  Echo (notifications)                                 │ │
│  │  Fiat (authorization)                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▼
        │ API calls                   │ cloud API calls
        ▼                              ▼
    User (browser)              AWS, GCP, Azure, K8s
```

Spinnaker is a microservices architecture — each component (Deck, Gate, Orca, etc.) runs as a separate service. They communicate via Clouddriver for cloud operations and Orca for orchestration.

## The Application Model

In Spinnaker, an "application" is a logical grouping of resources:

```text
Application: my-app
  Clusters:
    prod-cluster:
      ServerGroups:
        - v1 (deployed, 50% traffic)
        - v2 (deployed, 50% traffic, canary)
      LoadBalancers:
        - prod-lb
      SecurityGroups:
        - prod-sg
    staging-cluster:
      ServerGroups:
        - v1 (deployed, 100% traffic)
```

Key concepts:
- **Application**: top-level grouping.
- **Cluster**: a logical group of server groups (e.g., per environment).
- **Server Group**: a deployed version (e.g., v1, v2).
- **Load Balancer**: routes traffic to server groups.
- **Security Group**: firewall rules.

The model is more abstract than Kubernetes; Spinnaker translates to each cloud's resources (ASG in AWS, Managed Instance Group in GCP, Deployment in K8s).

## Deployment Strategies

### Red/Black (Blue/Green)

```text
1. Deploy v2 alongside v1 (both running).
2. Switch the load balancer from v1 to v2 (instantaneous).
3. If v2 is healthy, scale down v1.
4. If v2 is unhealthy, switch back to v1 (rollback).
```

The "red/black" name comes from Netflix's UI (red = disabled, black = enabled). The deployment is instantaneous; rollback is fast.

### Canary

```text
1. Deploy v2 with 10% of v1's capacity (e.g., 1 instance vs 10).
2. Route 10% of traffic to v2.
3. Monitor metrics for N minutes.
4. If metrics are good, scale v2 up to 100%, scale v1 to 0.
5. If metrics are bad, rollback (scale v2 to 0).
```

Canary requires a metrics system (Prometheus, Datadog) to evaluate v2's health. Spinnaker's "Canary Analysis" feature compares v2's metrics to v1's baseline; if v2 deviates significantly, the canary fails.

### Rolling

```text
1. Deploy v2 instances one at a time.
2. As each v2 instance becomes healthy, drain and terminate a v1 instance.
3. Repeat until all instances are v2.
```

Slower than blue/green but uses less capacity (only N+1 instances during the deployment).

## Pipelines

Spinnaker pipelines are defined via JSON (or via the UI):

```json
{
  "name": "Deploy to Production",
  "stages": [
    {
      "type": "Bake",
      "name": "Build Image",
      "cloudProvider": "aws",
      "recipe": "my-app-ami.json"
    },
    {
      "type": "Deploy",
      "name": "Deploy to Staging",
      "clusters": [{"account": "staging", "cluster": "my-app"}]
    },
    {
      "type": "ManualJudgment",
      "name": "Approve for Production",
      "instructions": "Review staging deployment; approve for production."
    },
    {
      "type": "Deploy",
      "name": "Deploy to Production",
      "strategy": "redblack",
      "clusters": [{"account": "production", "cluster": "my-app"}]
    },
    {
      "type": "Canary",
      "name": "Canary Analysis",
      "canaryConfig": {...}
    }
  ],
  "triggers": [
    {
      "type": "jenkins",
      "job": "my-app-build",
      "propertyFile": "image_tag.txt"
    }
  ]
}
```

Stages:
- **Bake**: build an image (AMI, container).
- **Deploy**: deploy to a cluster (with a strategy).
- **ManualJudgment**: wait for human approval.
- **Canary**: run canary analysis.

Triggers: events that start the pipeline (Jenkins build, cron, webhook).

## Production Use Cases

### Multi-Cloud Deployment

For applications deployed across AWS, GCP, and Azure:
- Spinnaker's Clouddriver abstracts each cloud's API.
- The same pipeline deploys to all clouds.
- Per-cloud configurations are in Spinnaker's account settings.

### Sophisticated Canary Analysis

For applications where new versions may have subtle bugs:
- Spinnaker's Kayenta (canary analysis service) compares v2's metrics to v1's.
- Statistical tests (Mann-Whitney U) detect significant deviations.
- Auto-rollback on canary failure.

### Compliance-Heavy Deployments

For enterprises with strict approval workflows:
- Each stage requires approval (via ManualJudgment).
- Approval audit logs are stored (in Front50's persistence).
- RBAC (via Fiat) controls who can approve.

## Production Deployment

Spinnaker is deployed via Halyard (the configuration tool) or via the modern Kubernetes deployment (Armory Spinnaker, open Spinnaker on K8s):

```bash
# Install via Halyard
hal deploy apply
```

For Kubernetes, deploy via the Spinnaker Helm chart:

```bash
helm install spinnaker spinnaker/spinnaker
```

Spinnaker itself runs in a Kubernetes cluster (often the management cluster, not the workload clusters).

## Comparison to ArgoCD and Flux

| Aspect | Spinnaker | ArgoCD | Flux |
|--------|-----------|--------|------|
| Origin | Netflix 2014 | Intuit 2018 | Weaveworks 2016 |
| Focus | Multi-cloud CD | K8s GitOps | K8s GitOps |
| UI | Rich (Deck) | Built-in | Limited |
| Deployment strategies | First-class (redblack, canary, rolling) | Manual (via Helm/Kustomize) | Manual |
| Multi-cloud | Yes (AWS, GCP, Azure, K8s) | K8s only | K8s only |
| Best for | Multi-cloud, sophisticated deployments | K8s GitOps | Lightweight K8s GitOps |

Spinnaker is more powerful for multi-cloud and complex deployments; ArgoCD and Flux are simpler for K8s-only GitOps.

## Common Pitfalls

1. **Forgetting that Spinnaker is a microservices architecture.** Each component (Orca, Clouddriver, etc.) needs resources. For small deployments, the overhead is significant.

2. **Forgetting that Spinnaker's pipeline JSON is complex.** Use the UI to design pipelines; export to JSON for version control. Don't write JSON by hand.

3. **Forgetting that Clouddriver caches cloud state.** Changes made outside Spinnaker (e.g., via `aws ec2`) take time to reflect (default 30-second cache).

4. **Forgetting that canary analysis needs a metrics backend.** Without Prometheus or Datadog, Kayenta can't analyze canaries. Set up metrics first.

5. **Forgetting that Spinnaker's RBAC is per-application.** A user with access to one app doesn't have access to others. Configure RBAC (via Fiat) carefully.

6. **Forgetting that Spinnaker's "redblack" strategy needs a load balancer.** Without a load balancer that supports weighted routing, the strategy doesn't work.

## References

- [Spinnaker documentation](https://spinnaker.io/docs/)
- [Spinnaker GitHub](https://github.com/spinnaker/spinnaker)
- Netflix, "[Spinnaker: Continuous Delivery at Scale](https://netflixtechblog.com/spinnaker-continuous-delivery-from-2-of-the-3-leading-cloud-providers-efb983514841)" (2014)
- [Kayenta (Canary Analysis)](https://github.com/spinnaker/kayenta)
- [Armory Spinnaker (enterprise)](https://www.armory.io/)
- [Spinnaker vs ArgoCD comparison](https://www.armory.io/blog/spinnaker-vs-argo-cd/)
- [LWN: Spinnaker overview (2021)](https://lwn.net/Articles/820133/)
