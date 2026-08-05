# Containerization

Containerization packages applications with their dependencies into portable, reproducible units. This section covers the container ecosystem from Docker to Kubernetes to service meshes.

## In This Section

- [Docker](./docker.md) — Container fundamentals and Dockerfile best practices
- [Kubernetes](./kubernetes.md) — Container orchestration at scale
- [Service Mesh](./service-mesh.md) — Network infrastructure for microservices

## Container vs VM

| Aspect | Container | Virtual Machine |
|--------|-----------|-----------------|
| Isolation | Process-level | Hardware-level |
| Startup | Seconds | Minutes |
| Size | MBs | GBs |
| Overhead | Minimal | Significant |
| OS | Shared kernel | Full OS |
| Density | 100s per host | 10s per host |
