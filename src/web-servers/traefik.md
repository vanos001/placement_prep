# Traefik

Traefik is an open-source cloud-native reverse proxy and load balancer, originally developed by Containous (now Traefik Labs) in 2015. It's designed for dynamic, containerized environments — auto-discovering services from Docker, Kubernetes, and other orchestrators, and updating its config without restarts. This page covers the architecture, the providers model, the routing rules, and the comparison to Nginx and Envoy.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Traefik Process (single Go binary)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Entrypoints (listeners: 80, 443, etc.)                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Routers (path/host → service mapping)                   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Middlewares (auth, rate limit, compression, etc.)       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Services (load balancers to backends)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Providers (Docker, K8s, etc. — auto-discovery)         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ API discovery               │ HTTP request
        ▼                              ▼
    Docker / K8s API              Client (browser)
```

Traefik's defining feature: it auto-discovers services from orchestrators (Docker, Kubernetes, Marathon, Consul, ECS, etc.) via "providers". No manual config reload — when a new container starts, Traefik automatically routes to it.

## The Provider Model

A provider is a source of routing configuration. Traefik supports many:

- **Docker**: reads Docker labels on containers.
- **Kubernetes IngressRoute**: reads CRDs (custom resources) in the cluster.
- **File**: reads a YAML/JSON file (for static deployments).
- **Consul Catalog**: reads services from Consul.
- **AWS ECS**: reads task definitions.
- **Marathon**: reads from Mesos/Marathon.

Each provider exposes services and routers; Traefik merges them into a unified routing table.

## Docker Provider Example

```yaml
# traefik.yml
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web
```

A container with these labels:

```yaml
# docker-compose.yml
services:
  myapp:
    image: myapp:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.example.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls.certresolver=letsencrypt"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"
```

Traefik:
1. Notices the container via Docker provider.
2. Reads the labels to learn the routing rule.
3. Routes `myapp.example.com` to the container's port 8080.
4. Provisions a Let's Encrypt cert automatically.

When the container starts/stops, Traefik updates routing without a restart.

## Kubernetes IngressRoute (CRD)

For Kubernetes, Traefik uses custom resources (IngressRoute CRD):

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: myapp
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`myapp.example.com`)
      kind: Rule
      services:
        - name: myapp-svc
          port: 8080
  tls:
    certResolver: letsencrypt
```

This is more powerful than the standard Kubernetes Ingress (which is L7 only). Traefik's IngressRoute supports TCP, UDP, advanced middleware, and per-route TLS.

## The Rule Syntax

Traefik's routing rules are a small DSL:

```text
Host(`myapp.example.com`)                    # host matches
Host(`myapp.example.com`) && PathPrefix(`/api/`)  # host AND path prefix
Path(`/users/{id}`)                          # path with parameter
Host(`example.com`) || Host(`www.example.com`)    # OR
Headers(`X-Api-Key`, `secret`)               # header matches
Method(`GET`, `POST`)                        # HTTP method
ClientIP(`192.168.1.0/24`)                   # client IP CIDR
```

Rules can be combined with `&&`, `||`, and `()`. This is more expressive than Nginx's regex locations.

## Middlewares

Middlewares process requests before they reach the backend:

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
spec:
  rateLimit:
    average: 100
    burst: 50
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: myapp
spec:
  routes:
    - match: Host(`myapp.example.com`)
      middlewares:
        - name: rate-limit
      services:
        - name: myapp-svc
          port: 8080
```

Built-in middlewares:
- **Rate limit**: per-IP rate limiting.
- **Basic auth**: HTTP Basic auth.
- **Forward auth**: delegate to an external auth service.
- **Compression**: gzip.
- **Headers**: add/remove headers (CSP, HSTS).
- **Retry**: retry on failure.
- **Circuit breaker**: trip on failure rate.

Custom middlewares can be written as Go plugins.

## TLS and ACME

Traefik has built-in ACME (Let's Encrypt) support:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web
      # Or DNS challenge for wildcard certs:
      # dnsChallenge:
      #   provider: cloudflare
      #   delayBeforeCheck: 30
```

When a new host is routed, Traefik provisions a cert automatically. For wildcard certs, use DNS challenge (with a supported DNS provider).

## Production Performance

Traefik's published performance:
- HTTP/1.1 throughput: ~50K req/sec (single instance).
- HTTP/2 throughput: ~70K req/sec.
- Latency: ~1 ms per request.
- Memory: ~50 MB base.

For higher throughput, run multiple Traefik instances behind a load balancer (or use Traefik's Enterprise distributed mode).

## Comparison to Nginx and Envoy

| Aspect | Traefik | Nginx | Envoy |
|--------|---------|-------|-------|
| Origin | 2015 | 2002 | 2016 |
| Language | Go | C | C++ |
| Auto-discovery | First-class | Limited (with extra tooling) | First-class (xDS) |
| Let's Encrypt | Built-in | Requires external | Requires external |
| K8s CRD | IngressRoute | Ingress | Ingress + Gateway API |
| Config reload | Hot (no restart) | Reload (briefly drops connections) | Hot (xDS) |
| Middleware | Pluggable | Lua modules | WASM filters |
| Best for | Containerized, dynamic | Edge proxy, content serving | Service mesh |

Traefik is the choice for dynamic, containerized environments; Nginx for traditional edge proxy; Envoy for service mesh.

## Production Use Cases

### Docker Compose with HTTPS

```yaml
# docker-compose.yml
services:
  traefik:
    image: traefik:v3.0
    command:
      - --providers.docker
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.email=admin@example.com
      - --certificatesresolvers.le.acme.storage=/acme.json
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./acme.json:/acme.json
  
  myapp:
    image: myapp:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.example.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls.certresolver=le"
```

A complete HTTPS setup with Let's Encrypt in 30 lines of compose.

### Kubernetes Ingress

```bash
# Install Traefik via Helm
helm install traefik traefik/traefik

# Apply IngressRoute
kubectl apply -f ingress-route.yaml
```

Traefik auto-discovers services via the K8s API; routes are added/removed as services change.

### Multi-Tenant API Gateway

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: tenant1-api
spec:
  routes:
    - match: Host(`api.tenant1.com`) && PathPrefix(`/v1/`)
      middlewares:
        - name: tenant1-auth
        - name: rate-limit-100
      services:
        - name: tenant1-api-svc
          port: 8080
```

Per-tenant routing, auth, and rate limiting in one resource.

## Common Pitfalls

1. **Forgetting that auto-discovery can be overwhelming.** With many containers/services, the routing table can grow huge. Use `exposedByDefault: false` and opt-in per service.

2. **Forgetting that ACME cert provisioning has rate limits.** Let's Encrypt limits 50 certs per week per domain. Don't restart Traefik too often (which triggers re-provisioning).

3. **Forgetting that middleware chains run per-request.** A complex chain (auth + rate limit + headers + compression) adds latency. Keep chains short.

4. **Forgetting that the routing rule DSL is small.** No regex path matching; no per-query parameter routing. Use Path with `{param}` for parameter extraction.

5. **Forgetting that Traefik's file storage (acme.json) must be secure.** It contains the Let's Encrypt private keys. Restrict file permissions (`600`).

6. **Forgetting that Traefik's K8s CRD is more powerful than Ingress.** If using Ingress, you're limited; use IngressRoute for TCP/UDP and advanced features.

## References

- [Traefik documentation](https://doc.traefik.io/traefik/)
- [Traefik Providers](https://doc.traefik.io/traefik/providers/overview/)
- [Traefik Routers and Rules](https://doc.traefik.io/traefik/routing/routers/)
- [Traefik Middlewares](https://doc.traefik.io/traefik/middlewares/overview/)
- [Traefik + Let's Encrypt](https://doc.traefik.io/traefik/https/acme/)
- [Traefik GitHub repository](https://github.com/traefik/traefik)
- [Traefik vs Nginx vs Envoy comparison](https://traefik.io/blog/comparing-traefik-and-nginx/)
- [LWN: Traefik overview (2022)](https://lwn.net/Articles/856775/)
