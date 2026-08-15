# Advanced Cloud & Serverless Computing

This section covers advanced cloud computing topics that go beyond basic deployment — the cutting-edge of how compute, storage, and networking are composed, scheduled, and delivered at scale.

## Files

| File | Topics | Key Interview Themes |
|------|--------|---------------------|
| [serverless.md](serverless.md) | Cold starts, microVMs, durable execution, edge functions, WASM | "Eliminate cold starts in a serverless API" |
| [multi-cloud-advanced.md](multi-cloud-advanced.md) | Cloud bursting, confidential compute, disaggregation, CXL, spot instances | "Design a multi-cloud system with zero vendor lock-in" |
| [cloud-scheduling.md](cloud-scheduling.md) | K8s scheduler, Volcano, FinOps, carbon-aware scheduling, noisy neighbors | "How does Kubernetes decide where to place a pod?" |

## Why This Matters for Interviews

Senior SRE, infrastructure, and backend roles increasingly expect depth in:
- **Serverless internals** — understanding cold starts, Firecracker isolation, and durable execution distinguishes you from AWS Lambda tutorial users.
- **Multi-cloud and disaggregation** — enterprises want flexibility and are moving away from monolithic cloud dependency.
- **Scheduling and cost** — FinOps and carbon-aware computing are board-level concerns that engineers must implement.

## Prerequisites

- Cloud fundamentals (see [overview.md](../overview.md))
- Kubernetes basics (see [kubernetes/README.md](../kubernetes/README.md))
- Basic serverless experience (AWS Lambda, Cloud Functions)
- Networking fundamentals (TCP/IP, load balancing)
