# OCI Image Specification

The OCI (Open Container Initiative) Image Specification, standardized in 2017 (current version 1.1.0, 2023), defines the format for container images — the standard unit of deployment in modern container platforms (Docker, Kubernetes, containerd, CRI-O). This page covers the manifest format, the layer model, the digest-based content addressing, and the production use cases.

## The Specification

The OCI Image Spec defines:
- **Image Manifest**: describes the layers and config of an image.
- **Image Index** (manifest list): a list of manifests for different platforms.
- **Image Config**: the image's runtime configuration (env, entrypoint, layers).
- **Layer**: a tarball of filesystem changes (additions, deletions via whiteouts).
- **Descriptor**: a reference to a blob (manifest, layer, config) with its digest and size.

All blobs (manifests, configs, layers) are stored in a "blob store" — typically a content-addressable store keyed by SHA-256.

## The Manifest Format

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:abc123...",
    "size": 7023
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:def456...",
      "size": 32
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:789abc...",
      "size": 1024
    }
  ],
  "annotations": {
    "org.opencontainers.image.created": "2024-01-15T12:34:56Z",
    "org.opencontainers.image.source": "https://github.com/my-org/my-app"
  }
}
```

The manifest references:
- `config`: the image's config (a small JSON describing runtime settings).
- `layers`: ordered list of layer blobs.

## The Image Index (Manifest List)

For multi-architecture images:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.index.v1+json",
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:amd64-manifest-digest...",
      "size": 1234,
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:arm64-manifest-digest...",
      "size": 1234,
      "platform": {
        "architecture": "arm64",
        "os": "linux"
      }
    }
  ]
}
```

The image index lists manifests for different platforms (architecture + OS). The runtime (containerd, Docker) picks the right manifest based on its platform.

## The Image Config

```json
{
  "created": "2024-01-15T12:34:56Z",
  "architecture": "amd64",
  "os": "linux",
  "config": {
    "Env": ["PATH=/usr/local/bin:/usr/bin:/bin"],
    "Entrypoint": ["/app/run"],
    "Cmd": ["--config", "/etc/app.conf"],
    "WorkingDir": "/app",
    "User": "1000:1000",
    "Volumes": {"/data": {}},
    "Labels": {
      "maintainer": "devops@example.com"
    }
  },
  "rootfs": {
    "type": "layers",
    "diff_ids": [
      "sha256:layer1-content-sha256...",
      "sha256:layer2-content-sha256..."
    ]
  },
  "history": [
    {"created": "2024-01-15T12:34:56Z", "created_by": "ADD file:..."},
    {"created": "2024-01-15T12:35:00Z", "created_by": "RUN apk add curl"}
  ]
}
```

The config:
- `config`: runtime settings (env, entrypoint, etc.).
- `rootfs.diff_ids`: the SHA-256 of each layer's content (uncompressed).
- `history`: the Dockerfile instructions that created each layer.

## The Layer Model

Each layer is a tarball of filesystem changes:
- New files: added to the tar.
- Modified files: added (overwrites the previous version).
- Deleted files: a "whiteout" file (e.g., `.wh.filename`) marks the deletion.

```text
Layer 1: alpine base
  bin/busybox
  etc/os-release
  ...

Layer 2: RUN apk add curl
  bin/curl           ← added
  usr/lib/libcurl.so ← added

Layer 3: COPY app /app
  app/run            ← added
  app/config         ← added
  bin/curl.wh.<previous>  ← whiteout (curl was deleted in this layer)
```

The runtime stacks layers in order; whiteouts remove files from earlier layers.

## Content Addressing

Every blob (manifest, config, layer) is identified by its SHA-256 digest:

```text
Manifest:    sha256:abc123...
Config:      sha256:def456...
Layer 1:     sha256:789abc...
Layer 2:     sha256:012def...
```

The digest is computed over the blob's content. Two images with the same layer have the same digest (deduplication in registries and runtimes).

The `diff_id` in the config is the SHA-256 of the layer's content (uncompressed); the `digest` in the manifest is the SHA-256 of the compressed blob. These differ because the layer is stored compressed.

## The Distribution Spec

The OCI Distribution Spec (RFC-equivalent) defines how images are pushed/pulled:

```text
GET /v2/<name>/manifests/<reference>   ← fetch manifest (reference = tag or digest)
POST /v2/<name>/blobs/uploads/        ← initiate layer upload
PUT /v2/<name>/blobs/uploads/<uuid>   ← upload layer content
GET /v2/<name>/blobs/<digest>         ← fetch blob (layer or config)
```

Registries (Docker Hub, ECR, GCR, GitHub Container Registry) implement this spec. Modern registries also support OCI Artifact extensions (for non-image content like Helm charts, WASM modules).

## Production Use Cases

### Multi-Arch Images

```bash
# Build amd64 and arm64 images
docker buildx build --platform linux/amd64,linux/arm64 -t my-app:v1 --push .
```

BuildKit creates a manifest list with both architectures; users pull `my-app:v1` and get the right arch automatically.

### Image Signing (Sigstore)

```bash
cosign sign my-app:v1
# Pushes a signature as an OCI artifact to the registry.
# Verifiers check the signature before pulling.
```

The signature is stored as an OCI artifact (separate from the image). Kubernetes can enforce signature verification via admission webhooks (Kyverno, OPA Gatekeeper).

### SBOM (Software Bill of Materials)

```bash
syft my-app:v1 -o json > sbom.json
cosign attach sbom --artifact-type application/spdx+json my-app:v1
```

An SBOM lists all software in the image (for security scanning). Stored as an OCI artifact alongside the image.

## Common Pitfalls

1. **Forgetting that digest references are immutable.** A digest like `sha256:abc...` refers to a specific blob; if the image is rebuilt, the digest changes. Pin digests for reproducibility.

2. **Forgetting that tag references are mutable.** A tag like `v1` can be moved to a different digest; users may get different images over time. Pin digests in production deployments.

3. **Forgetting that layers are content-addressable.** Two images with the same layer have the same digest; registries deduplicate. This is a bandwidth optimization, not a security feature.

4. **Forgetting that the manifest references the config and layers.** A manifest without a config or layers is invalid. Validate before pushing.

5. **Forgetting that the layer order matters.** A layer can depend on a previous layer's content. Reordering breaks the build.

6. **Forgetting that whiteouts are needed for deletes.** A `RUN rm file` in Docker doesn't actually delete the file from earlier layers; it adds a whiteout. The total image size may not shrink.

## Comparison to Other Container Image Formats

| Format | Standard | Description |
|--------|---------|-------------|
| OCI Image Spec | OCI (2017) | Modern, standardized |
| Docker Image Manifest v2 | Docker (pre-OCI) | Legacy, still supported |
| AppC (appc) | CoreOS (2014) | Deprecated (replaced by OCI) |
| Singularity (SIF) | Singularity (2018) | HPC-focused |

OCI is the modern standard; Docker's v2 is backward-compatible. AppC is deprecated.

## References

- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)
- [OCI Artifacts (for non-image content)](https://github.com/opencontainers/artifacts)
- [Docker Image Manifest v2 (legacy)](https://docs.docker.com/registry/spec/manifest-v2-2/)
- [Sigstore (image signing)](https://www.sigstore.dev/)
- [Syft (SBOM generation)](https://github.com/anchore/syft)
- [OCI vs Docker Image Spec](https://www.docker.com/blog/oci-image-spec-clarification/)
- [LWN: OCI overview (2021)](https://lwn.net/Articles/820133/)
