# Kaniko (Container Image Builder for Kubernetes)

Kaniko is an open-source container image builder, developed by Google since 2018. Unlike Docker, Kaniko doesn't require a Docker daemon — it builds images directly inside a container, making it ideal for Kubernetes-based CI/CD. This page covers the architecture, the build process, the cache layer, and the comparison to Docker BuildKit and Buildah.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Kaniko Container (runs in a Pod)                          │
│  - Reads the Dockerfile                                      │
│  - Executes each instruction                                 │
│  - Builds layers in /kaniko (image's filesystem)             │
│  - Pushes the final image to a registry                     │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▼
        │ Dockerfile + context         │ push to registry
        ▼                              ▼
    Git repo / PVC               Registry (ECR, GCR, etc.)
```

Kaniko runs as a container image (`gcr.io/kaniko-project/executor`). The Dockerfile and build context are mounted as volumes. Kaniko reads the Dockerfile, executes each instruction in its own filesystem snapshot, and pushes the final image.

## The Build Process

For a Dockerfile:

```dockerfile
FROM alpine:latest
RUN apk add --no-cache curl
COPY app /app
CMD ["/app/run"]
```

Kaniko:
1. Pulls `alpine:latest` (if not cached).
2. Extracts the image's layers into `/kaniko`.
3. Executes `RUN apk add --no-cache curl`:
   a. Runs the command in a chroot (the `/kaniko` filesystem).
   b. Snapshots the filesystem changes (whatsnew) → creates a new layer.
4. Executes `COPY app /app`:
   a. Copies the local `app` directory into `/kaniko/app`.
   b. Snapshots → new layer.
5. Sets `CMD ["/app/run"]` as metadata.
6. Pushes the final image (with all layers) to the registry.

The key difference from Docker: Kaniko doesn't use a Docker daemon. The container itself is the build environment.

## The Cache Layer

Kaniko supports layer caching for faster builds:

```bash
/kaniko/executor \
    --dockerfile=Dockerfile \
    --context=gs://my-bucket/context.tar.gz \
    --destination=gcr.io/my-project/my-app:v1 \
    --cache=true \
    --cache-dir=/cache
```

With caching:
- Each `RUN` instruction's result is checked against the cache.
- If cached, the layer is reused (skipping the RUN).
- If not cached, the layer is built and added to the cache.

The cache is stored in the registry (`--cache-repo=gcr.io/my-project/cache`). Multi-stage builds share the cache across CI runs.

## Running Kaniko in Kubernetes

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kaniko-build
spec:
  template:
    spec:
      containers:
        - name: kaniko
          image: gcr.io/kaniko-project/executor:latest
          args:
            - --dockerfile=Dockerfile
            - --context=gs://my-bucket/context/
            - --destination=gcr.io/my-project/my-app:v1
            - --cache=true
            - --cache-repo=gcr.io/my-project/cache
          volumeMounts:
            - { name: kaniko-secret, mountPath: /secret }
          env:
            - { name: GOOGLE_APPLICATION_CREDENTIALS, value: /secret/kaniko-secret.json }
      volumes:
        - name: kaniko-secret
          secret:
            secretName: kaniko-secret
      restartPolicy: Never
```

The Job runs Kaniko with credentials for the registry (mounted from a Secret).

## Kaniko vs. Docker BuildKit vs. Buildah

| Aspect | Kaniko | Docker BuildKit | Buildah |
|--------|--------|-----------------|---------|
| Origin | Google 2018 | Docker 2017 | Red Hat 2017 |
| Daemon required | No | Yes (or rootless mode) | No |
| K8s-native | Yes (runs in a Pod) | With BuildKitd + driver | Yes |
| Dockerfile support | Yes | Yes | Yes (also Buildah scripts) |
| Cache | Registry | Local or registry | Local |
| Best for | K8s CI/CD pipelines | Docker-native, BuildKit features | Red Hat ecosystem, custom scripts |

Kaniko is the standard for K8s-based CI/CD pipelines. BuildKit has more features (multi-platform builds, secret mounts). Buildah is for Red Hat / podman ecosystem.

## Production Use Cases

### CI/CD Pipeline

```yaml
# GitLab CI example
build:
  stage: build
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  script:
    - mkdir -p /kaniko/.docker
    - echo "$DOCKER_AUTH_CONFIG" > /kaniko/.docker/config.json
    - /kaniko/executor
      --context=$CI_PROJECT_DIR
      --dockerfile=Dockerfile
      --destination=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
      --cache=true
      --cache-repo=$CI_REGISTRY_IMAGE/cache
```

### Multi-Architecture Builds

Kaniko supports multi-arch builds via `--platform`:

```bash
/kaniko/executor \
    --dockerfile=Dockerfile \
    --context=. \
    --destination=gcr.io/my-project/my-app:v1 \
    --platform=linux/amd64,linux/arm64
```

Builds for both architectures; pushes as a manifest list. Each arch is a separate image; the manifest list combines them.

### Build with Secrets

```dockerfile
# Dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

```bash
/kaniko/executor \
    --dockerfile=Dockerfile \
    --context=. \
    --destination=... \
    --build-arg=BUILDKIT_INLINE_CACHE=1 \
    --secret=id=npmrc,src=$HOME/.npmrc
```

The secret is mounted only for the duration of the RUN; it's not in the image's layers.

## Production Performance

Kaniko's build time depends on:
- Image size (pulling the base image).
- Number of RUN instructions.
- Cache hit rate.

For typical web apps (~10 layers, 500 MB base image): 5-10 minutes for a fresh build, 1-2 minutes with cache.

## Common Pitfalls

1. **Forgetting that Kaniko doesn't support all Dockerfile features.** BuildKit-specific features (like `--mount=type=cache`) may not work; check the Kaniko docs.

2. **Forgetting that the build context must be accessible.** The context (with the Dockerfile) must be in a volume or remote location. Kaniko doesn't have local filesystem access by default.

3. **Forgetting that Kaniko needs registry credentials.** Without credentials, Kaniko can't push (or pull base images from private registries). Mount the credentials as a Secret.

4. **Forgetting that the cache is per-registry.** The cache repo must be writable by Kaniko. For multi-region CI, use a global registry (or accept cache misses).

5. **Forgetting that large build contexts are slow.** The `--context=dir:///path` sends all files; use `.dockerignore` to exclude large files (e.g., node_modules, .git).

6. **Forgetting that Kaniko runs as root in the build container.** The `RUN` instructions execute as root; if your image must run as non-root, add `USER` at the end of the Dockerfile.

## Comparison to Other Container Build Tools

| Tool | Daemon | K8s-native | Multi-arch | Caching | Best for |
|------|--------|------------|-------------|---------|----------|
| Kaniko | No | Yes | Yes (buildx-like) | Registry | K8s CI/CD |
| BuildKit | Optional (rootless) | Yes (with BuildKitd) | Yes | Local + registry | Modern Docker builds |
| Buildah | No | Yes | Limited | Local | Red Hat ecosystem |
| Docker (legacy) | Yes | No | Limited | Local | Legacy Docker |

Kaniko is the choice for K8s-based CI/CD without Docker daemon. BuildKit is the modern Docker choice.

## References

- [Kaniko documentation](https://github.com/GoogleContainerTools/kaniko)
- [Kaniko GitHub](https://github.com/GoogleContainerTools/kaniko)
- [Kaniko + Kubernetes example](https://github.com/GoogleContainerTools/kaniko#running-kaniko-in-a-kubernetes-cluster)
- [Docker BuildKit](https://github.com/moby/buildkit)
- [Buildah (Red Hat)](https://github.com/containers/buildah)
- [Kaniko vs BuildKit vs Buildah comparison](https://blog.aegerter.io/post/kaniko-vs-buildkit-vs-buildah/)
- [LWN: Kaniko overview (2022)](https://lwn.net/Articles/856775/)
