# Docker

## Overview

**Docker** is a platform that uses OS-level virtualization to deliver software in packages called **containers**. Docker popularized containers by making them easy to build, ship, and run. It provides a complete ecosystem: image format, runtime, registry, and CLI tools.

## Motivation

Before Docker, deploying applications required:
- Installing dependencies on each server
- "Works on my machine" problems
- Complex deployment scripts
- Heavy VMs for isolation

Docker solves this by packaging the application with its dependencies into a portable, reproducible container image.

## Docker Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Architecture                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Docker CLI (docker)                                  │    │
│  │  User interface for building, running, managing       │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │ REST API                          │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Docker Daemon (dockerd)                              │    │
│  │  • Image management                                   │    │
│  │  • Container lifecycle                                │    │
│  │  • Network management                                 │    │
│  │  • Volume management                                  │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │ gRPC                              │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  containerd                                          │    │
│  │  • Container runtime (high-level)                     │    │
│  │  • Image pull/push                                    │    │
│  │  • Container execution                                │    │
│  │  • Snapshot management                                │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │ OCI runtime spec                  │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  runc (OCI Runtime)                                   │    │
│  │  • Creates namespaces                                 │    │
│  │  • Sets up cgroups                                    │    │
│  │  • Applies seccomp profiles                           │    │
│  │  • Calls execve() to start container process          │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Linux Kernel                                         │    │
│  │  Namespaces + Cgroups + Seccomp + Capabilities        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Container Lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│              Container States                                 │
│                                                              │
│  ┌──────────┐  docker create  ┌──────────┐  docker start    │
│  │  Image   │────────────────►│  Created │────────────────►│
│  └──────────┘                 └──────────┘                  │
│                                                              │
│                                    ┌──────────┐              │
│                              ┌────►│ Running  │◄────┐       │
│                              │     └────┬─────┘     │       │
│                         docker start    │           │       │
│                              │     docker pause     │       │
│                              │          │     docker unpause │
│                              │          ▼           │       │
│                              │     ┌──────────┐    │       │
│                              │     │  Paused  │────┘       │
│                              │     └──────────┘              │
│                              │          │                   │
│                              │     docker stop              │
│                              │          │                   │
│                              │          ▼                   │
│                              │     ┌──────────┐            │
│                              └─────│  Stopped │            │
│                            docker  └────┬─────┘            │
│                            restart       │                  │
│                                    docker rm                │
│                                          │                  │
│                                          ▼                  │
│                                     ┌──────────┐            │
│                                     │  Removed │            │
│                                     └──────────┘            │
└──────────────────────────────────────────────────────────────┘
```

## Dockerfile

```dockerfile
# Multi-stage build
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server .

FROM alpine:3.18
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/server /usr/local/bin/server
EXPOSE 8080
USER 1000:1000
ENTRYPOINT ["server"]
```

```
Dockerfile Instructions:
  FROM        Base image
  RUN         Execute command during build
  COPY        Copy files from host to image
  ADD         Copy + extract archives / fetch URLs
  WORKDIR     Set working directory
  ENV         Set environment variables
  EXPOSE      Document listening ports (doesn't publish)
  USER        Set user for subsequent commands
  ENTRYPOINT  Container startup command
  CMD         Default arguments (overridden by docker run args)
  VOLUME      Declare mount points
  ARG         Build-time variables
  HEALTHCHECK Container health check
```

## Docker Storage

```
┌──────────────────────────────────────────────────────────────┐
│  Docker Storage Layers                                       │
│                                                              │
│  Container Layer (writable)                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Modified/created files                              │    │
│  │  (Copy-on-write from image layers)                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Image Layers (read-only)                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Layer 4: COPY --from=builder /app/server            │    │
│  ├──────────────────────────────────────────────────────┤    │
│  │  Layer 3: RUN apk add ca-certificates                │    │
│  ├──────────────────────────────────────────────────────┤    │
│  │  Layer 2: (alpine base)                              │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  OverlayFS merges layers for container's view                │
└──────────────────────────────────────────────────────────────┘

Volumes (persistent data):
  Named volume:   docker volume create mydata
  Bind mount:     -v /host/path:/container/path
  tmpfs:          --tmpfs /container/tmp (RAM-backed)
```

```bash
# Manage volumes
docker volume create mydata
docker volume ls
docker volume inspect mydata

# Run with volume
docker run -v mydata:/app/data myimage

# Bind mount
docker run -v /host/code:/app myimage

# tmpfs (memory-backed, for sensitive data)
docker run --tmpfs /app/tmp:rw,noexec,nosuid myimage
```

## Docker Networking

```bash
# Network types
docker network ls
# NETWORK ID     NAME      DRIVER    SCOPE
# abc123         bridge    bridge    local
# def456         host      host      local
# ghi789         none      null      local

# Bridge network (default)
docker run --network bridge myimage
# Container gets IP from 172.17.0.0/16

# Host network (shares host network stack)
docker run --network host myimage
# No network isolation, best performance

# None (no networking)
docker run --network none myimage

# Custom bridge network (recommended)
docker network create mynet
docker run --network mynet --name web myimage
docker run --network mynet --name db myimage
# Containers can resolve each other by name (DNS)

# Port publishing
docker run -p 8080:80 myimage    # Host 8080 → Container 80
docker run -p 127.0.0.1:8080:80  # Bind to localhost only
```

## Docker Security

```bash
# Drop all capabilities, add only what's needed
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage

# Read-only filesystem
docker run --read-only --tmpfs /tmp myimage

# No new privileges
docker run --security-opt no-new-privileges myimage

# Custom seccomp profile
docker run --security-opt seccomp=profile.json myimage

# User namespace remapping
# /etc/docker/daemon.json:
# { "userns-remap": "default" }

# Rootless Docker
# Runs daemon as non-root user
# No root privilege required at all

# Scan images for vulnerabilities
docker scout cves myimage
trivy image myimage
```

## Real-World Examples

### Common Docker Commands

```bash
# Build image
docker build -t myapp:v1 .

# Run container
docker run -d --name myapp -p 8080:80 myapp:v1

# View running containers
docker ps

# View logs
docker logs -f myapp

# Execute command in container
docker exec -it myapp bash

# Inspect container
docker inspect myapp

# Resource limits
docker run -d --cpus="1.5" --memory=512m myapp

# Health check
docker run --health-cmd="curl -f http://localhost/" \
           --health-interval=30s myapp
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8080:80"
    environment:
      - DB_HOST=db
    depends_on:
      - db
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    networks:
      - app-net

  db:
    image: postgres:15
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    networks:
      - app-net

volumes:
  db-data:

networks:
  app-net:
```

## Interview Questions

### Beginner

**Q: What is Docker and how does it differ from a VM?**
A: Docker is a container platform that packages applications with their dependencies into lightweight, portable containers. Unlike VMs which include a full guest OS and run on a hypervisor, Docker containers share the host kernel and use kernel features (namespaces, cgroups) for isolation. This makes containers much lighter (MBs vs GBs), faster to start (seconds vs minutes), and more resource-efficient.

**Q: What is a Dockerfile?**
A: A Dockerfile is a text file containing instructions to build a Docker image. Each instruction creates a layer — `FROM` sets the base image, `RUN` executes commands, `COPY` adds files, `CMD` sets the default command. Multi-stage builds allow using different images for building and running, reducing final image size.

### Intermediate

**Q: Explain Docker's storage drivers and how OverlayFS works.**
A: Docker uses storage drivers (OverlayFS, devicemapper, etc.) to manage image layers. OverlayFS stacks a writable layer on top of read-only image layers. When a container modifies a file, OverlayFS copies it to the writable layer (copy-on-write). Reads check the writable layer first, then image layers. This enables efficient storage — multiple containers share the same image layers.

**Q: How does Docker networking work? What is the bridge network?**
A: The default bridge network creates a virtual bridge (`docker0`) on the host. Each container gets a virtual ethernet interface (veth) connected to the bridge, with an IP from the bridge's subnet (172.17.0.0/16). NAT enables internet access. Custom bridge networks add DNS resolution — containers can find each other by name. Host network mode removes isolation for maximum performance.

### FAANG-Level

**Q: Design a secure Docker image build pipeline for a production microservice that handles payment data.**

A:

```
Requirements: PCI-DSS compliance, minimal attack surface, reproducible

1. Multi-stage build:
   Stage 1 (builder): Full toolchain, compile application
   Stage 2 (runtime): Minimal base, only runtime dependencies

2. Base image selection:
   - Use distroless or scratch (no shell, no package manager)
   - Or Alpine with minimal packages
   - Pin exact versions (no :latest)
   - Verify image signatures (Docker Content Trust)

3. Security hardening:
   FROM gcr.io/distroless/static-debian12:nonroot
   USER 65534:65534  # nobody:nobody
   # No shell available = can't exec into container
   # No package manager = can't install tools

4. Build-time scanning:
   - Scan base image for CVEs (Trivy, Snyk)
   - Scan application dependencies (npm audit, go vuln)
   - Fail build on critical/high CVEs
   - Generate SBOM (Software Bill of Materials)

5. Runtime security:
   docker run \
     --cap-drop=ALL \              # Drop all capabilities
     --read-only \                 # Read-only filesystem
     --tmpfs /tmp:rw,noexec \      # Writable tmp only
     --no-new-privileges \         # No privilege escalation
     --security-opt seccomp=pci.json \  # Strict syscall filter
     --memory=512m --cpus=1 \      # Resource limits
     --network=payment-net \       # Isolated network
     --health-cmd="..." \          # Health monitoring
     payment-service:v1.2.3

6. Secrets management:
   - Never bake secrets into image
   - Use Docker secrets or external secret store
   - Mount secrets as tmpfs (memory-only)
   - Rotate secrets without rebuilding

7. Image signing and verification:
   - Sign images with Docker Content Trust (Notary)
   - Verify signatures before deployment
   - Use immutable tags (SHA256 digest)

8. Registry security:
   - Private registry with authentication
   - Vulnerability scanning on push
   - Retention policies for old images
   - Image provenance (who built, when, from what)

Pipeline:
  Code → Build → Scan → Sign → Push → Deploy → Verify
```

## Common Mistakes

1. **Using `:latest` tag**: Always pin specific versions for reproducibility.
2. **Running as root**: Use `USER` directive to run as non-root.
3. **Large image size**: Use multi-stage builds and minimal base images.
4. **Baking secrets into images**: Use runtime secret injection instead.
5. **Not handling signals**: PID 1 must handle SIGTERM for graceful shutdown. Use `exec` in entrypoint scripts.
6. **Ignoring health checks**: Always define health checks for production containers.

## Summary

| Component | Purpose |
|-----------|---------|
| Dockerfile | Build instructions for images |
| Image | Read-only template with application + dependencies |
| Container | Running instance of an image |
| Volume | Persistent data storage |
| Network | Container connectivity |
| Registry | Image storage and distribution |

## Cross-References

- [Containers Overview](README.md) — Container concepts
- [Cgroups](cgroups.md) — Resource limits Docker uses
- [Namespaces](namespaces.md) — Isolation Docker uses
- [Kubernetes](kubernetes.md) — Orchestrating Docker containers
- [Security: Capabilities](../security/capabilities.md) — Docker capability management


## Cross References

- [Namespaces](namespaces.md)
- [Cgroups](cgroups.md)
- [VM vs Container](../../cloud/virtualization/vm-vs-container.md)
- [Kubernetes](kubernetes.md)
