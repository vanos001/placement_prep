# Helm (Kubernetes Package Manager)

Helm is the package manager for Kubernetes, originally developed by Deis (acquired by Microsoft) in 2016 and donated to CNCF. It packages Kubernetes manifests into reusable "charts" that can be versioned, shared, and parameterized. This page covers the chart structure, the template engine, the release lifecycle, and the production patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Helm (CLI, runs on user's machine or in CI)               │
│  - Renders templates                                          │
│  - Calls Kubernetes API to install/upgrade                    │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▼
        │ chart (from registry)        │ apply manifests
        ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────┐
│  Chart Registry            │    │  Kubernetes cluster    │
│  - artifacthub.io          │    │  - Helm releases       │
│  - OCI registry (e.g., ECR)│    │    (Secrets per release)│
└──────────────────────────┘    └──────────────────────┘
```

Helm is a CLI tool (not a long-running process). It runs on the user's machine or in CI/CD; it calls the Kubernetes API to install/upgrade releases.

## The Chart Structure

A "chart" is a directory of files:

```text
my-chart/
├── Chart.yaml          ← chart metadata (name, version, dependencies)
├── values.yaml         ← default values
├── values.schema.json  ← values schema (validation)
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── _helpers.tpl    ← reusable template snippets
│   └── NOTES.txt       ← post-install instructions
├── charts/             ← dependency charts (subcharts)
│   └── redis-12.3.4.tgz
├── crds/               ← custom resource definitions
└── README.md
```

### Chart.yaml

```yaml
apiVersion: v2
name: my-app
description: A Helm chart for my-app
type: application
version: 1.0.0          # chart version
appVersion: "1.0.0"     # application version
dependencies:
  - name: redis
    version: "12.x.x"
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
```

### values.yaml

```yaml
replicaCount: 3

image:
  repository: my-app
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

ingress:
  enabled: false
  className: ""
  hosts:
    - host: my-app.example.com
      paths:
        - path: /
          pathType: ImplementationSpecific
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          ports:
            - name: http
              containerPort: 80
              protocol: TCP
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

The template uses Go templates with Helm functions:
- `{{ .Values.replicaCount }}`: accesses values.
- `{{ include "my-app.fullname" . }}`: calls a helper template.
- `{{- ... | nindent 4 }}`: trims whitespace and indents.

## The Template Engine

Helm uses Go's text/template with Helm-specific functions:
- `include`: render a sub-template.
- `required`: error if a value is missing.
- `default`: provide a default.
- `toYaml`: convert a value to YAML.
- `nindent`: indent (newline + spaces).
- `range`: iterate.
- `if`/`else`: conditional.
- `with`: scoped variable.

```yaml
{{- range .Values.ingress.hosts }}
- host: {{ .host }}
  http:
    paths:
      {{- range .paths }}
      - path: {{ .path }}
        pathType: {{ .pathType }}
      {{- end }}
{{- end }}
```

## The Release Lifecycle

```bash
# Install a chart as a release
helm install my-release my-chart/

# Upgrade to a new chart version
helm upgrade my-release my-chart/ --values production.yaml

# Rollback to a previous version
helm rollback my-release 1

# Uninstall (deletes all resources)
helm uninstall my-release

# List releases
helm list
```

Helm tracks each release's history (versions); rollbacks are atomic.

## Production Patterns

### Pattern 1: Multi-Environment Values

```text
my-chart/
  values.yaml              ← defaults
  values-dev.yaml         ← dev overrides
  values-staging.yaml     ← staging overrides
  values-production.yaml  ← production overrides
```

```bash
helm install my-app my-chart/ -f values-production.yaml
```

### Pattern 2: OCI Registry (Modern Chart Distribution)

Since Helm 3.0, charts can be stored in OCI registries (like container images):

```bash
# Package and push
helm package my-chart/
helm push my-chart-1.0.0.tgz oci://registry.example.com/charts

# Install from OCI
helm install my-app oci://registry.example.com/charts/my-chart --version 1.0.0
```

OCI is preferred over the legacy HTTP registry (more secure, integrated with existing container registries).

### Pattern 3: Library Charts (Reusable Templates)

A "library chart" defines helpers and templates that other charts can use:

```yaml
# Chart.yaml of library chart
apiVersion: v2
name: common
type: library
version: 1.0.0
```

Other charts depend on the library:

```yaml
dependencies:
  - name: common
    version: "1.0.0"
    repository: "oci://registry.example.com/charts"
```

The library's templates are available via `include` in the dependent chart.

### Pattern 4: Helm + ArgoCD/Flux

For GitOps, Helm charts can be managed by ArgoCD/Flux:

```yaml
# ArgoCD Application
spec:
  source:
    chart: my-app
    repoURL: oci://registry.example.com/charts
    targetRevision: 1.0.0
    helm:
      values: |
        replicaCount: 3
        image:
          tag: v1.0.0
```

ArgoCD/Flux handle the GitOps; Helm handles the templating.

## Common Pitfalls

1. **Forgetting that Helm doesn't track resources outside its chart.** A `kubectl apply` after Helm install isn't tracked by Helm; `helm uninstall` won't delete it. Use Helm for all resources.

2. **Forgetting that the chart version must bump on every change.** Without a version bump, `helm upgrade` doesn't detect a change.

3. **Forgetting that templates can be syntactically valid YAML but semantically wrong.** A `helm install --dry-run` validates rendering but not the actual K8s schema. Use `helm template | kubectl apply --dry-run=server` for full validation.

4. **Forgetting that Helm's release history grows.** Each upgrade creates a new Secret; over time, hundreds of Secrets accumulate. Set `--history-max` (default 10).

5. **Forgetting that Helm hooks can run at wrong times.** Hooks (`post-install`, `pre-upgrade`) run as Pods; they can fail silently. Use them sparingly.

6. **Forgetting that chart dependencies need `helm dependency update`.** Before installing a chart with subcharts, run `helm dependency update` to fetch them.

## Comparison to Kustomize

| Aspect | Helm | Kustomize |
|--------|------|-----------|
| Origin | Deis 2016 | Google 2017 |
| Templating | Go templates | None (overlay-based) |
| Distribution | OCI registry, HTTP | Git repo |
| Configuration | values.yaml | kustomization.yaml with overlays |
| Lifecycle | Tracked (releases) | Stateless (just apply) |
| Best for | Reusable charts, complex apps | Customizing existing manifests |

Helm and Kustomize are complementary; Helm for distribution, Kustomize for customization. Many deployments use both (Helm chart with Kustomize overlays).

## References

- [Helm documentation](https://helm.sh/docs/)
- [Helm Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Helm GitHub](https://github.com/helm/helm)
- [Artifact Hub (chart catalog)](https://artifacthub.io/)
- [Bitnami Charts (popular reference)](https://github.com/bitnami/charts)
- [Helm vs Kustomize](https://helm.sh/docs/faq/#should-i-use-helm-or-kustomize)
- [LWN: Helm overview (2021)](https://lwn.net/Articles/815575/)
