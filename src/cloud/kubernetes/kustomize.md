# Kustomize (Kubernetes Configuration Customization)

Kustomize is a Kubernetes configuration management tool, originally developed at Google in 2017 and integrated into kubectl since 1.14 (2019). Unlike Helm (which uses templates), Kustomize uses "overlays" — patches that modify existing YAML without templating. This page covers the architecture, the overlay model, the patch types, and the comparison to Helm.

## The Architecture

```text
base/                     ← the original manifests
  deployment.yaml
  service.yaml
  kustomization.yaml

overlays/
  dev/                    ← dev-specific patches
    kustomization.yaml
    deployment-patch.yaml
  staging/
    kustomization.yaml
    deployment-patch.yaml
  production/
    kustomization.yaml
    deployment-patch.yaml
```

Kustomize reads the base manifests and applies overlays to produce the final manifests for a specific environment.

## The kustomization.yaml

Each directory with a `kustomization.yaml` is a "kustomization":

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml

commonLabels:
  app: my-app
```

```yaml
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patches:
  - path: deployment-patch.yaml
  - path: service-patch.yaml

configMapGenerator:
  - name: app-config
    files:
      - config.properties

images:
  - name: my-app
    newName: registry.example.com/my-app
    newTag: v1.0.0
```

The overlay:
- `resources`: includes the base.
- `patches`: applies patches (YAML or JSON6902).
- `images`: replaces image names/tags.
- `configMapGenerator`: generates ConfigMaps from files.

## Patches

### Strategic Merge Patch

```yaml
# deployment-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 5
  template:
    spec:
      containers:
        - name: my-app
          resources:
            limits:
              cpu: 1000m
              memory: 1Gi
```

The patch overrides the base's values for the specified fields. Fields not in the patch are preserved.

### JSON 6902 Patch

For more complex operations (add/remove/list items):

```yaml
# deployment-patch.yaml
- op: replace
  path: /spec/replicas
  value: 5
- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: NEW_ENV_VAR
    value: "true"
```

JSON patches are more flexible but more verbose. Useful for list manipulation (e.g., adding a container to a list).

## Common Transformations

### commonLabels and commonAnnotations

```yaml
commonLabels:
  app: my-app
  env: production
commonAnnotations:
  maintained-by: devops@example.com
```

Adds labels/annotations to all resources in the kustomization.

### namePrefix and nameSuffix

```yaml
namePrefix: production-
```

All resources get renamed: `my-app` becomes `production-my-app`. Useful for multi-tenant clusters (avoid name conflicts).

### images

```yaml
images:
  - name: my-app
    newName: registry.example.com/my-app
    newTag: v1.0.0
  - name: busybox
    digest: sha256:abc123...
```

Replaces image references. Useful for promoting images through environments (dev → staging → production).

## ConfigMap and Secret Generators

```yaml
configMapGenerator:
  - name: app-config
    files:
      - config.properties
      - logging.conf
    literals:
      - DATABASE_URL=postgres://...
      - LOG_LEVEL=info

secretGenerator:
  - name: app-secrets
    files:
      - tls.crt
      - tls.key
    literals:
      - API_KEY=secret-value
```

Generators create ConfigMaps and Secrets with content-addressed names (e.g., `app-config-abc123`). When the content changes, the name changes, which triggers Pod restarts (because the env var referencing the ConfigMap changes).

## Using Kustomize

```bash
# Build (render) the manifests
kustomize build overlays/production/

# Or via kubectl (built-in since 1.14)
kubectl apply -k overlays/production/

# Diff against the cluster
kustomize build overlays/production/ | kubectl diff -f -

# Print the manifests (for review)
kustomize build overlays/production/ > production.yaml
```

## Production Patterns

### Multi-Environment Promotion

```text
base/
  deployment.yaml (replicas: 1)
  kustomization.yaml

overlays/dev/
  kustomization.yaml (patches replicas: 1)

overlays/staging/
  kustomization.yaml (patches replicas: 3)

overlays/production/
  kustomization.yaml (patches replicas: 5, with resources limits)
```

```bash
# Deploy to dev
kubectl apply -k overlays/dev/

# Promote to staging
kubectl apply -k overlays/staging/

# Promote to production
kubectl apply -k overlays/production/
```

### Helm + Kustomize

Kustomize can consume Helm charts:

```yaml
# kustomization.yaml
helmCharts:
  - name: my-app
    repo: https://charts.example.com
    version: 1.0.0
    releaseName: my-app
    valuesInline:
      replicaCount: 3
```

Kustomize renders the Helm chart, then applies its overlays on top.

## Comparison to Helm

| Aspect | Kustomize | Helm |
|--------|-----------|------|
| Origin | Google 2017 | Deis 2016 |
| Templating | None (overlay-based) | Go templates |
| Distribution | Git repos | OCI registries, HTTP |
| Configuration | kustomization.yaml | values.yaml |
| Lifecycle | Stateless (just apply) | Tracked (releases) |
| Patches | Strategic merge / JSON 6902 | N/A (templates only) |
| Best for | Customizing existing manifests | Reusable, parameterized charts |

Kustomize is for customizing; Helm is for packaging. Many deployments use both.

## Common Pitfalls

1. **Forgetting that Kustomize doesn't track resources.** Unlike Helm, Kustomize just renders and applies. There's no "release" to uninstall.

2. **Forgetting that ConfigMap generators create new names.** A ConfigMap with `name: app-config` becomes `app-config-abc123`. Pod references must use the generated name; use `configMapRef: { name: app-config }` and Kustomize handles the rename.

3. **Forgetting that strategic merge patches are field-level.** A patch with `spec.containers[0].resources.limits.cpu` overrides only that field; other fields in the same container are preserved.

4. **Forgetting that JSON 6902 patches use list indices.** `path: /spec/template/spec/containers/0` refers to the first container; if the order changes, the patch may target the wrong container.

5. **Forgetting that overlays can be nested.** An overlay can include another overlay; the chain is resolved recursively. Don't create circular references.

6. **Forgetting that Kustomize doesn't validate the rendered manifests.** `kustomize build` produces YAML; it doesn't check against Kubernetes' schema. Use `kubectl apply --dry-run=server` for validation.

## References

- [Kustomize documentation](https://kubectl.docs.kubernetes.io/pages/kustomize.html)
- [Kustomize GitHub](https://github.com/kubernetes-sigs/kustomize)
- [Kustomize Tutorial](https://kubectl.docs.kubernetes.io/pages/kustomize.html)
- [Strategic Merge Patch](https://kubectl.docs.kubernetes.io/pages/app_management/strategic_merge_patch.html)
- [JSON 6902 Patches](https://kubectl.docs.kubernetes.io/pages/app_management/json_patch.html)
- [Helm + Kustomize Integration](https://kubectl.docs.kubernetes.io/pages/app_management/helm.html)
- [LWN: Kustomize overview (2020)](https://lwn.net/Articles/815575/)
