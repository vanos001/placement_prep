# Cloud Computing Reference Library

This page is a verified index of primary sources for cloud & devops: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Hyperscale and developer-focused providers, infrastructure as code, containers and orchestration, observability, reliability frameworks, and a two-track path from the OCI specs to Kubernetes internals and platform engineering.

**93 entries** across 10 categories, plus **57 education & reference-implementation resources** (26 basic / 31 advanced), plus **10 video resources** and **5 conference sources**.

Every link HTTP-verified on **2026-10-07**.

## Contents

- [1. Hyperscale cloud providers](#1-hyperscale-cloud-providers) — 6
- [2. Developer-focused & regional providers](#2-developer-focused--regional-providers) — 8
- [3. Infrastructure as code](#3-infrastructure-as-code) — 6
- [4. Containers & orchestration](#4-containers--orchestration) — 11
- [5. Observability](#5-observability) — 6
- [6. Standards, reference architectures & ecosystem](#6-standards-reference-architectures--ecosystem) — 8
- [7. Local clusters, service mesh & networking](#7-local-clusters-service-mesh--networking) — 8
- [8. Security, policy & supply chain](#8-security-policy--supply-chain) — 6
- [9. Scaling, delivery & cost](#9-scaling-delivery--cost) — 7
- [10. Research papers & open-access literature](#10-research-papers--open-access-literature) — 27
- [Education & reference implementations](#education--reference-implementations) — 57 (26 basic / 31 advanced)
- [Video courses, channels & talks](#video-courses-channels--talks) — 10
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 5


## 1. Hyperscale cloud providers

### Amazon Web Services

- **Docs:** [docs.aws.amazon.com](https://docs.aws.amazon.com/)
- **Developer / API:** [aws.amazon.com/developer/tools](https://aws.amazon.com/developer/tools/)
- **Source:** [github.com/aws](https://github.com/aws)
- **SDKs & repos:** SDKs for 10+ languages (boto3, aws-sdk-js-v3, aws-sdk-go-v2), CDK, SAM, CLI
- **Downloadable / offline:** Every AWS guide is downloadable as PDF — look for the PDF link on any docs page
- *Note:* The documentation is vast and uneven. The service FAQ pages and the Well-Architected lenses are often better starting points than the user guides.

### Microsoft Azure

- **Docs:** [learn.microsoft.com/en-us/azure](https://learn.microsoft.com/en-us/azure/)
- **Developer / API:** [learn.microsoft.com/en-us/azure/developer](https://learn.microsoft.com/en-us/azure/developer/)
- **Source:** [github.com/Azure](https://github.com/Azure)
- **SDKs & repos:** Azure SDKs per language, Bicep, ARM templates, Azure CLI
- **Downloadable / offline:** Microsoft Learn supports PDF export per module and offline reading
- *Note:* Learn is better organised than AWS's docs but moves content frequently; prefer stable anchors when bookmarking.

### Google Cloud

- **Docs:** [cloud.google.com/docs](https://cloud.google.com/docs)
- **Developer / API:** [cloud.google.com/apis/docs/overview](https://cloud.google.com/apis/docs/overview)
- **Source:** [github.com/GoogleCloudPlatform](https://github.com/GoogleCloudPlatform)
- **SDKs & repos:** Client libraries, gcloud, Config Connector
- **Downloadable / offline:** Docs site; architecture framework separately
- *Note:* The architecture centre is consistently the strongest part of Google's documentation.

### Oracle Cloud Infrastructure

- **Docs:** [docs.oracle.com/en-us/iaas/Content/home.htm](https://docs.oracle.com/en-us/iaas/Content/home.htm)
- **Developer / API:** [docs.oracle.com/en-us/…](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdks.htm)
- **Source:** [github.com/oracle](https://github.com/oracle)
- **SDKs & repos:** SDKs for Java, Python, Go, TypeScript, .NET; OCI CLI
- **Downloadable / offline:** Docs downloadable

### IBM Cloud

- **Docs:** [cloud.ibm.com/docs](https://cloud.ibm.com/docs)
- **Source:** [github.com/IBM-Cloud](https://github.com/IBM-Cloud)
- **SDKs & repos:** SDKs, CLI, Terraform provider
- **Downloadable / offline:** Docs site

### Alibaba Cloud

- **Docs:** [alibabacloud.com/help/en](https://www.alibabacloud.com/help/en/)
- **Source:** [github.com/aliyun](https://github.com/aliyun)
- **SDKs & repos:** SDKs across languages; Terraform provider
- **Downloadable / offline:** Docs site
- *Note:* The most complete documentation for the major non-Western cloud.


## 2. Developer-focused & regional providers

### DigitalOcean

- **Docs:** [docs.digitalocean.com](https://docs.digitalocean.com/)
- **Developer / API:** [docs.digitalocean.com/reference/api](https://docs.digitalocean.com/reference/api/)
- **Source:** [github.com/digitalocean](https://github.com/digitalocean)
- **SDKs & repos:** godo, pydo, doctl; Terraform provider
- **Downloadable / offline:** Docs site
- *Note:* The community tutorials are frequently better than the official docs of larger clouds for Linux and networking basics.

### Akamai Cloud (Linode)

- **Docs:** [techdocs.akamai.com/cloud-computing/docs](https://techdocs.akamai.com/cloud-computing/docs/)
- **Source:** [github.com/linode](https://github.com/linode)
- **SDKs & repos:** linode-cli, linodego, Terraform provider
- **Downloadable / offline:** Docs site
- *Note:* Linode is now Akamai Cloud Computing; older linode.com documentation links redirect here.

### Hetzner

- **Docs:** [docs.hetzner.com](https://docs.hetzner.com/)
- **Developer / API:** [docs.hetzner.cloud](https://docs.hetzner.cloud/)
- **Source:** [github.com/hetznercloud](https://github.com/hetznercloud)
- **SDKs & repos:** hcloud CLI and Go library; Terraform provider
- **Downloadable / offline:** Docs site

### Cloudflare

- **Docs:** [developers.cloudflare.com](https://developers.cloudflare.com/)
- **Developer / API:** [developers.cloudflare.com/api](https://developers.cloudflare.com/api/)
- **Source:** [github.com/cloudflare](https://github.com/cloudflare)
- **SDKs & repos:** Workers, Wrangler, R2, D1, Durable Objects
- **Downloadable / offline:** Docs site
- *Note:* The Workers documentation is the best introduction to edge compute as a model, not just as a product.

### Fly.io

- **Docs:** [fly.io/docs](https://fly.io/docs/)
- **Developer / API:** [fly.io/docs/machines/api](https://fly.io/docs/machines/api/)
- **Source:** [github.com/superfly](https://github.com/superfly)
- **SDKs & repos:** flyctl; Machines API
- **Downloadable / offline:** Docs site
- *Note:* Also publishes some of the best free systems writing on the web, including the Gossip Glomers distributed-systems challenges.

### Vercel

- **Docs:** [vercel.com/docs](https://vercel.com/docs)
- **Developer / API:** [vercel.com/docs/rest-api](https://vercel.com/docs/rest-api)
- **Source:** [github.com/vercel](https://github.com/vercel)
- **SDKs & repos:** Vercel CLI, SDK
- **Downloadable / offline:** Docs site

### Netlify

- **Docs:** [docs.netlify.com](https://docs.netlify.com/)
- **Developer / API:** [docs.netlify.com/api/get-started](https://docs.netlify.com/api/get-started/)
- **Source:** [github.com/netlify](https://github.com/netlify)
- **SDKs & repos:** Netlify CLI, functions
- **Downloadable / offline:** Docs site

### Render

- **Docs:** [render.com/docs](https://render.com/docs)
- **Developer / API:** [render.com/docs/api](https://render.com/docs/api)
- **Source:** [github.com/renderinc](https://github.com/renderinc)
- **SDKs & repos:** Blueprint-based deployment
- **Downloadable / offline:** Docs site


## 3. Infrastructure as code

### Terraform

- **Docs:** [developer.hashicorp.com/terraform/docs](https://developer.hashicorp.com/terraform/docs)
- **Developer / API:** [registry.terraform.io](https://registry.terraform.io/)
- **Source:** [github.com/hashicorp/terraform](https://github.com/hashicorp/terraform)
- **SDKs & repos:** 4000+ providers in the registry; CDKTF
- **Downloadable / offline:** Docs site; registry documents every provider and resource
- *Note:* Licence changed to BUSL in 2023, which is why OpenTofu exists. The registry is the actually useful documentation.

### OpenTofu

- **Docs:** [opentofu.org/docs](https://opentofu.org/docs/)
- **Source:** [github.com/opentofu/opentofu](https://github.com/opentofu/opentofu)
- **SDKs & repos:** Terraform-compatible; Linux Foundation governed
- **Downloadable / offline:** Docs site
- *Note:* The open-source fork after the licence change. Largely drop-in compatible.

### Pulumi

- **Docs:** [pulumi.com/docs](https://www.pulumi.com/docs/)
- **Developer / API:** [pulumi.com/registry](https://www.pulumi.com/registry/)
- **Source:** [github.com/pulumi/pulumi](https://github.com/pulumi/pulumi)
- **SDKs & repos:** Infrastructure in TypeScript, Python, Go, C#, Java, YAML
- **Downloadable / offline:** Docs site
- *Note:* Real programming languages instead of HCL. Suits teams who already write code more than config.

### AWS CloudFormation

- **Docs:** [docs.aws.amazon.com/cloudformation](https://docs.aws.amazon.com/cloudformation/)
- **Developer / API:** [docs.aws.amazon.com/AWSCloudFormation/…](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/)
- **SDKs & repos:** Native AWS templating
- **Downloadable / offline:** PDF download available

### AWS CDK

- **Docs:** [docs.aws.amazon.com/cdk/v2/guide/home.html](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- **Developer / API:** [docs.aws.amazon.com/cdk/api/v2](https://docs.aws.amazon.com/cdk/api/v2/)
- **Source:** [github.com/aws/aws-cdk](https://github.com/aws/aws-cdk)
- **SDKs & repos:** TypeScript, Python, Java, Go, C#
- **Downloadable / offline:** Docs + API reference

### Crossplane

- **Docs:** [docs.crossplane.io](https://docs.crossplane.io/)
- **Source:** [github.com/crossplane/crossplane](https://github.com/crossplane/crossplane)
- **SDKs & repos:** Kubernetes-native control plane for cloud resources
- **Downloadable / offline:** Docs site
- *Note:* Manage cloud infrastructure through the Kubernetes API. A genuinely different model from Terraform's.


## 4. Containers & orchestration

### Kubernetes

- **Docs:** [kubernetes.io/docs/home](https://kubernetes.io/docs/home/)
- **Developer / API:** [kubernetes.io/docs/reference](https://kubernetes.io/docs/reference/)
- **Source:** [github.com/kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)
- **SDKs & repos:** client-go, client-python, kubectl, controller-runtime
- **Downloadable / offline:** Docs per version; reference API documentation generated from source
- *Note:* The concepts section is good; the reference is authoritative. KEPs in `kubernetes/enhancements` record design reasoning.

### Docker

- **Docs:** [docs.docker.com](https://docs.docker.com/)
- **Developer / API:** [docs.docker.com/reference/api/engine](https://docs.docker.com/reference/api/engine/)
- **Source:** [github.com/docker](https://github.com/docker)
- **SDKs & repos:** Docker Engine API, Compose, BuildKit
- **Downloadable / offline:** Docs site

### containerd

- **Docs:** [containerd.io/docs](https://containerd.io/docs/)
- **Source:** [github.com/containerd/containerd](https://github.com/containerd/containerd)
- **SDKs & repos:** The runtime under both Docker and Kubernetes
- **Downloadable / offline:** Docs site

### OCI Image Specification

- **Docs:** [github.com/opencontainers/image-spec](https://github.com/opencontainers/image-spec)
- **Source:** [github.com/opencontainers/image-spec](https://github.com/opencontainers/image-spec)
- **SDKs & repos:** Defines what a container image is
- **Downloadable / offline:** Markdown spec in-repo
- *Note:* Short. Read it and image layers stop being mysterious.

### OCI Distribution Specification

- **Docs:** [github.com/opencontainers/distribution-spec](https://github.com/opencontainers/distribution-spec)
- **Source:** [github.com/opencontainers/distribution-spec](https://github.com/opencontainers/distribution-spec)
- **SDKs & repos:** The registry HTTP API
- **Downloadable / offline:** Spec in-repo

### Helm

- **Docs:** [helm.sh/docs](https://helm.sh/docs/)
- **Developer / API:** [helm.sh/docs/helm](https://helm.sh/docs/helm/)
- **Source:** [github.com/helm/helm](https://github.com/helm/helm)
- **SDKs & repos:** Chart templating and release management
- **Downloadable / offline:** Docs site

### Argo CD

- **Docs:** [argo-cd.readthedocs.io](https://argo-cd.readthedocs.io/)
- **Developer / API:** [argo-cd.readthedocs.io/en/…](https://argo-cd.readthedocs.io/en/stable/developer-guide/api-docs/)
- **Source:** [github.com/argoproj/argo-cd](https://github.com/argoproj/argo-cd)
- **SDKs & repos:** GitOps continuous delivery for Kubernetes
- **Downloadable / offline:** Sphinx docs

### Flux

- **Docs:** [fluxcd.io/flux](https://fluxcd.io/flux/)
- **Developer / API:** [fluxcd.io/flux/components](https://fluxcd.io/flux/components/)
- **Source:** [github.com/fluxcd/flux2](https://github.com/fluxcd/flux2)
- **SDKs & repos:** GitOps toolkit, CNCF graduated
- **Downloadable / offline:** Docs site

### Knative

- **Docs:** [knative.dev/docs](https://knative.dev/docs/)
- **Developer / API:** [knative.dev/docs/serving](https://knative.dev/docs/serving/)
- **Source:** [github.com/knative](https://github.com/knative)
- **SDKs & repos:** Serverless workloads on Kubernetes
- **Downloadable / offline:** Docs site

### HashiCorp Nomad

- **Docs:** [developer.hashicorp.com/nomad/docs](https://developer.hashicorp.com/nomad/docs)
- **Developer / API:** [developer.hashicorp.com/nomad/api-docs](https://developer.hashicorp.com/nomad/api-docs)
- **Source:** [github.com/hashicorp/nomad](https://github.com/hashicorp/nomad)
- **SDKs & repos:** Scheduler for containers and non-container workloads alike
- **Downloadable / offline:** Docs site
- *Note:* Much simpler than Kubernetes, and sufficient for many workloads.

### OpenFaaS

- **Docs:** [docs.openfaas.com](https://docs.openfaas.com/)
- **Source:** [github.com/openfaas/faas](https://github.com/openfaas/faas)
- **SDKs & repos:** Functions on Kubernetes
- **Downloadable / offline:** Docs site


## 5. Observability

### Prometheus

- **Docs:** [prometheus.io/docs](https://prometheus.io/docs/)
- **Developer / API:** [prometheus.io/docs/…](https://prometheus.io/docs/prometheus/latest/querying/api/)
- **Source:** [github.com/prometheus/prometheus](https://github.com/prometheus/prometheus)
- **SDKs & repos:** Client libraries in all major languages; exporters; PromQL
- **Downloadable / offline:** Docs site
- *Note:* The de facto metrics standard. Learn PromQL properly — it is the part people skip and then suffer.

### Grafana

- **Docs:** [grafana.com/docs](https://grafana.com/docs/)
- **Developer / API:** [grafana.com/docs/…](https://grafana.com/docs/grafana/latest/developers/http_api/)
- **Source:** [github.com/grafana/grafana](https://github.com/grafana/grafana)
- **SDKs & repos:** Dashboards, alerting, plugins
- **Downloadable / offline:** Docs site

### OpenTelemetry

- **Docs:** [opentelemetry.io/docs](https://opentelemetry.io/docs/)
- **Developer / API:** [opentelemetry.io/docs/specs/otel](https://opentelemetry.io/docs/specs/otel/)
- **Source:** [github.com/open-telemetry](https://github.com/open-telemetry)
- **SDKs & repos:** SDKs for 12+ languages; the Collector; OTLP protocol
- **Downloadable / offline:** Docs site; specification separately
- *Note:* The convergence point for traces, metrics and logs. Instrument with OTel rather than a vendor SDK.

### Jaeger

- **Docs:** [jaegertracing.io/docs](https://www.jaegertracing.io/docs/)
- **Source:** [github.com/jaegertracing/jaeger](https://github.com/jaegertracing/jaeger)
- **SDKs & repos:** Distributed tracing backend
- **Downloadable / offline:** Docs per version

### Grafana Loki

- **Docs:** [grafana.com/docs/loki/latest](https://grafana.com/docs/loki/latest/)
- **Developer / API:** [grafana.com/docs/…](https://grafana.com/docs/loki/latest/reference/loki-http-api/)
- **Source:** [github.com/grafana/loki](https://github.com/grafana/loki)
- **SDKs & repos:** Log aggregation indexed by labels rather than content
- **Downloadable / offline:** Docs site

### Thanos

- **Docs:** [thanos.io](https://thanos.io/)
- **Developer / API:** [thanos.io/tip/thanos/design.md](https://thanos.io/tip/thanos/design.md/)
- **Source:** [github.com/thanos-io/thanos](https://github.com/thanos-io/thanos)
- **SDKs & repos:** Long-term storage and global query for Prometheus
- **Downloadable / offline:** Docs site


## 6. Standards, reference architectures & ecosystem

### CNCF Landscape

- **Docs:** [landscape.cncf.io](https://landscape.cncf.io/)
- **Developer / API:** [cncf.io/projects](https://www.cncf.io/projects/)
- **Source:** [github.com/cncf/landscape](https://github.com/cncf/landscape)
- **SDKs & repos:** The full map of the cloud-native ecosystem
- **Downloadable / offline:** Interactive site; data in the repo
- *Note:* Overwhelming by design. Filter by graduated projects first — that cuts hundreds of options to a few dozen credible ones.

### CloudEvents

- **Docs:** [cloudevents.io](https://cloudevents.io/)
- **Developer / API:** [github.com/cloudevents/spec](https://github.com/cloudevents/spec)
- **Source:** [github.com/cloudevents/spec](https://github.com/cloudevents/spec)
- **SDKs & repos:** Vendor-neutral event format; SDKs in 9 languages
- **Downloadable / offline:** Spec in-repo

### Backstage

- **Docs:** [backstage.io/docs/overview/what-is-backstage](https://backstage.io/docs/overview/what-is-backstage/)
- **Developer / API:** [backstage.io/docs](https://backstage.io/docs/)
- **Source:** [github.com/backstage/backstage](https://github.com/backstage/backstage)
- **SDKs & repos:** Developer portal framework from Spotify
- **Downloadable / offline:** Docs site

### AWS Well-Architected

- **Docs:** [aws.amazon.com/architecture/well-architected](https://aws.amazon.com/architecture/well-architected/)
- **SDKs & repos:** Six pillars plus domain-specific lenses
- **Downloadable / offline:** Whitepapers as PDF
- *Note:* Readable in an afternoon and applicable well beyond AWS.

### Azure Well-Architected Framework

- **Docs:** [learn.microsoft.com/en-us/…](https://learn.microsoft.com/en-us/azure/well-architected/)
- **SDKs & repos:** Microsoft's equivalent
- **Downloadable / offline:** Learn, offline export

### Google Cloud Architecture Framework

- **Docs:** [cloud.google.com/architecture/framework](https://cloud.google.com/architecture/framework)
- **SDKs & repos:** Google's equivalent, plus a large reference-architecture library
- **Downloadable / offline:** Docs site
- *Note:* The broader architecture centre is the best part of Google's documentation.

### The Twelve-Factor App

- **Docs:** [12factor.net](https://12factor.net/)
- **SDKs & repos:** Twelve principles for cloud-native applications
- **Downloadable / offline:** Free, short
- *Note:* Dated in places, still the shared vocabulary. Thirty minutes to read.

### Google SRE books

- **Docs:** [sre.google/books](https://sre.google/books/)
- **SDKs & repos:** Site Reliability Engineering, the Workbook, and Building Secure and Reliable Systems
- **Downloadable / offline:** All free to read online
- *Note:* The SRE book defined how the industry talks about reliability. Chapters on SLOs and error budgets are the essential ones.


## 7. Local clusters, service mesh & networking

### kind

- **Docs:** [kind.sigs.k8s.io](https://kind.sigs.k8s.io/)
- **Developer / API:** [kind.sigs.k8s.io/docs/user/quick-start](https://kind.sigs.k8s.io/docs/user/quick-start/)
- **Source:** [github.com/kubernetes-sigs/kind](https://github.com/kubernetes-sigs/kind)
- **SDKs & repos:** Kubernetes clusters in Docker containers; what the project itself uses for CI
- **Downloadable / offline:** Docs site
- *Note:* The fastest way to a throwaway multi-node cluster on a laptop.

### minikube

- **Docs:** [minikube.sigs.k8s.io/docs](https://minikube.sigs.k8s.io/docs/)
- **Developer / API:** [minikube.sigs.k8s.io/docs/commands](https://minikube.sigs.k8s.io/docs/commands/)
- **Source:** [github.com/kubernetes/minikube](https://github.com/kubernetes/minikube)
- **SDKs & repos:** Single-node local Kubernetes with an addon system
- **Downloadable / offline:** Docs site

### k3s

- **Docs:** [docs.k3s.io](https://docs.k3s.io/)
- **Source:** [github.com/k3s-io/k3s](https://github.com/k3s-io/k3s)
- **SDKs & repos:** Lightweight certified Kubernetes in a single binary
- **Downloadable / offline:** Docs site
- *Note:* Production-viable at the edge, and small enough to actually read the deployment story.

### Talos Linux

- **Docs:** [talos.dev](https://www.talos.dev/)
- **Developer / API:** [talos.dev/docs](https://www.talos.dev/docs/)
- **Source:** [github.com/siderolabs/talos](https://github.com/siderolabs/talos)
- **SDKs & repos:** Immutable, API-managed Linux built only to run Kubernetes — no shell, no SSH
- **Downloadable / offline:** Docs per version
- *Note:* A genuinely different operating model. Worth studying even if you never deploy it. Docs now redirect to docs.siderolabs.com — old talos.dev deep links have rotted.

### Cilium

- **Docs:** [docs.cilium.io](https://docs.cilium.io/)
- **Developer / API:** [docs.cilium.io/en/stable/api](https://docs.cilium.io/en/stable/api/)
- **Source:** [github.com/cilium/cilium](https://github.com/cilium/cilium)
- **SDKs & repos:** eBPF-based networking, observability and security for Kubernetes; Hubble
- **Downloadable / offline:** Docs per version
- *Note:* The best practical demonstration of eBPF at scale. See the OS index for eBPF fundamentals.

### Istio

- **Docs:** [istio.io/latest/docs](https://istio.io/latest/docs/)
- **Developer / API:** [istio.io/latest/docs/reference](https://istio.io/latest/docs/reference/)
- **Source:** [github.com/istio/istio](https://github.com/istio/istio)
- **SDKs & repos:** The most widely deployed service mesh
- **Downloadable / offline:** Docs per version

### Linkerd

- **Docs:** [linkerd.io/2/overview](https://linkerd.io/2/overview/)
- **Developer / API:** [linkerd.io/2/reference](https://linkerd.io/2/reference/)
- **Source:** [github.com/linkerd/linkerd2](https://github.com/linkerd/linkerd2)
- **SDKs & repos:** Lightweight service mesh with a Rust data plane
- **Downloadable / offline:** Docs site
- *Note:* Deliberately simpler than Istio. Read both before choosing.

### Envoy

- **Docs:** [envoyproxy.io/docs](https://www.envoyproxy.io/docs)
- **Developer / API:** [envoyproxy.io/docs/envoy/latest/api/api](https://www.envoyproxy.io/docs/envoy/latest/api/api)
- **Source:** [github.com/envoyproxy/envoy](https://github.com/envoyproxy/envoy)
- **SDKs & repos:** The proxy underneath most service meshes; xDS configuration protocol
- **Downloadable / offline:** Docs per version
- *Note:* Learn the xDS API — it is the actual interface meshes are built on.


## 8. Security, policy & supply chain

### HashiCorp Vault

- **Docs:** [developer.hashicorp.com/vault/docs](https://developer.hashicorp.com/vault/docs)
- **Developer / API:** [developer.hashicorp.com/vault/api-docs](https://developer.hashicorp.com/vault/api-docs)
- **Source:** [github.com/hashicorp/vault](https://github.com/hashicorp/vault)
- **SDKs & repos:** Secrets management, dynamic credentials, PKI
- **Downloadable / offline:** Docs site

### Open Policy Agent

- **Docs:** [openpolicyagent.org/docs](https://www.openpolicyagent.org/docs/)
- **Developer / API:** [openpolicyagent.org/docs/latest/rest-api](https://www.openpolicyagent.org/docs/latest/rest-api/)
- **Source:** [github.com/open-policy-agent/opa](https://github.com/open-policy-agent/opa)
- **SDKs & repos:** General-purpose policy engine with the Rego language
- **Downloadable / offline:** Docs site
- *Note:* Policy as code, decoupled from the service enforcing it. The Rego tutorial is short and worth doing.

### Kyverno

- **Docs:** [kyverno.io/docs](https://kyverno.io/docs/)
- **Source:** [github.com/kyverno/kyverno](https://github.com/kyverno/kyverno)
- **SDKs & repos:** Kubernetes-native policy without a separate language
- **Downloadable / offline:** Docs site
- *Note:* Easier than OPA if your policies are only about Kubernetes resources.

### Sigstore

- **Docs:** [docs.sigstore.dev](https://docs.sigstore.dev/)
- **Source:** [github.com/sigstore](https://github.com/sigstore)
- **SDKs & repos:** Keyless signing for software artifacts; cosign, Fulcio, Rekor
- **Downloadable / offline:** Docs site
- *Note:* Signing containers without managing long-lived keys. Rapidly becoming the default.

### SLSA

- **Docs:** [slsa.dev](https://slsa.dev/)
- **Developer / API:** [slsa.dev/spec](https://slsa.dev/spec/)
- **SDKs & repos:** Supply-chain integrity framework with graded levels
- **Downloadable / offline:** Spec free online
- *Note:* A short, practical spec. Read the levels before claiming any of them.

### Falco

- **Docs:** [falco.org/docs](https://falco.org/docs/)
- **Developer / API:** [falco.org/docs/reference](https://falco.org/docs/reference/)
- **Source:** [github.com/falcosecurity/falco](https://github.com/falcosecurity/falco)
- **SDKs & repos:** Runtime security monitoring using eBPF syscall visibility
- **Downloadable / offline:** Docs site


## 9. Scaling, delivery & cost

### KEDA

- **Docs:** [keda.sh/docs](https://keda.sh/docs/)
- **Developer / API:** [keda.sh/docs/latest](https://keda.sh/docs/latest/)
- **Source:** [github.com/kedacore/keda](https://github.com/kedacore/keda)
- **SDKs & repos:** Event-driven autoscaling on arbitrary metrics and queue depths
- **Downloadable / offline:** Docs per version

### Karpenter

- **Docs:** [karpenter.sh/docs](https://karpenter.sh/docs/)
- **Source:** [github.com/aws/karpenter-provider-aws](https://github.com/aws/karpenter-provider-aws)
- **SDKs & repos:** Just-in-time node provisioning; bin-packs and consolidates automatically
- **Downloadable / offline:** Docs site
- *Note:* Usually the single largest cluster cost reduction available on AWS.

### Tekton

- **Docs:** [tekton.dev/docs](https://tekton.dev/docs/)
- **Developer / API:** [tekton.dev/docs/pipelines](https://tekton.dev/docs/pipelines/)
- **Source:** [github.com/tektoncd/pipeline](https://github.com/tektoncd/pipeline)
- **SDKs & repos:** Kubernetes-native CI/CD primitives
- **Downloadable / offline:** Docs site

### GitHub Actions

- **Docs:** [docs.github.com/en/actions](https://docs.github.com/en/actions)
- **Developer / API:** [docs.github.com/en/rest/actions](https://docs.github.com/en/rest/actions)
- **Source:** [github.com/actions](https://github.com/actions)
- **SDKs & repos:** Hosted CI/CD; reusable workflows and OIDC federation to cloud providers
- **Downloadable / offline:** Docs site
- *Note:* The OIDC section is the important one — it removes long-lived cloud credentials from CI entirely.

### Terragrunt

- **Docs:** [terragrunt.gruntwork.io/docs](https://terragrunt.gruntwork.io/docs/)
- **Source:** [github.com/gruntwork-io/terragrunt](https://github.com/gruntwork-io/terragrunt)
- **SDKs & repos:** Keeps large Terraform/OpenTofu codebases DRY
- **Downloadable / offline:** Docs site

### LocalStack

- **Docs:** [docs.localstack.cloud](https://docs.localstack.cloud/)
- **Developer / API:** [docs.localstack.cloud/references](https://docs.localstack.cloud/references/)
- **Source:** [github.com/localstack/localstack](https://github.com/localstack/localstack)
- **SDKs & repos:** Local emulation of AWS services for development and testing
- **Downloadable / offline:** Docs site
- *Note:* Fidelity is imperfect — verify against real AWS before trusting anything subtle.

### OpenCost

- **Docs:** [opencost.io/docs](https://www.opencost.io/docs/)
- **Developer / API:** [opencost.io/docs/integrations/api](https://www.opencost.io/docs/integrations/api)
- **Source:** [github.com/opencost/opencost](https://github.com/opencost/opencost)
- **SDKs & repos:** CNCF cost monitoring for Kubernetes workloads
- **Downloadable / offline:** Docs site
- *Note:* Allocates spend per namespace, deployment and label. The honest starting point for cluster cost work.


## 10. Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### arXiv cs.DC (Distributed Computing)

- **Docs:** [arxiv.org/list/cs.DC/recent](https://arxiv.org/list/cs.DC/recent)
- **SDKs & repos:** Cloud, cluster and distributed infrastructure preprints
- **Downloadable / offline:** Free

### USENIX NSDI

- **Docs:** [usenix.org/conference/nsdi25](https://www.usenix.org/conference/nsdi25)
- **SDKs & repos:** Networked systems design — most large-scale cloud infrastructure papers
- **Downloadable / offline:** Every paper free, with talk videos
- *Note:* Borg, Maglev-class infrastructure papers and their successors live here.

### ACM SoCC

- **Docs:** [acmsocc.org](https://acmsocc.org/)
- **SDKs & repos:** Symposium on Cloud Computing — the dedicated cloud venue
- **Downloadable / offline:** Via ACM DL; many preprints on arXiv
- *Note:* The main academic venue specifically about cloud.

### USENIX SREcon

- **Docs:** [usenix.org/srecon](https://www.usenix.org/srecon)
- **SDKs & repos:** Practitioner conference on reliability and operations
- **Downloadable / offline:** Slides and talk videos posted free
- *Note:* Not research, but the talks are where real operational practice is described honestly, including the failures.

### AWS Builders' Library

- **Docs:** [aws.amazon.com/builders-library](https://aws.amazon.com/builders-library/)
- **SDKs & repos:** How Amazon builds and operates services: timeouts, retries, load shedding, health checks
- **Downloadable / offline:** Free, long-form articles
- *Note:* Written by principal engineers about production systems. More immediately useful than most cloud papers.

### Google Research publications

- **Docs:** [research.google/pubs](https://research.google/pubs/)
- **SDKs & repos:** MapReduce, GFS, Bigtable, Chubby, Borg, Spanner, Maglev, Dapper
- **Downloadable / offline:** Free PDFs
- *Note:* The foundational cloud infrastructure papers. Read Borg and Dapper before adopting Kubernetes or tracing.

### Microsoft Research publications

- **Docs:** [microsoft.com/en-us/research/publications](https://www.microsoft.com/en-us/research/publications/)
- **SDKs & repos:** Azure infrastructure, serverless, datacentre networking
- **Downloadable / offline:** Free PDFs

### Amazon Science

- **Docs:** [amazon.science/publications](https://www.amazon.science/publications)
- **SDKs & repos:** AWS systems research, including the DynamoDB and S3 papers
- **Downloadable / offline:** Free

### All Things Distributed

- **Docs:** [allthingsdistributed.com](https://www.allthingsdistributed.com/)
- **SDKs & repos:** Werner Vogels on distributed systems and AWS design decisions
- **Downloadable / offline:** Free

### Engineering at Meta

- **Docs:** [engineering.fb.com](https://engineering.fb.com/)
- **SDKs & repos:** Production infrastructure at very large scale
- **Downloadable / offline:** Free

### CNCF reports & research

- **Docs:** [cncf.io/reports](https://www.cncf.io/reports/)
- **SDKs & repos:** Annual surveys, project adoption data, technology radars
- **Downloadable / offline:** Free
- *Note:* Useful for adoption trends. Treat as industry data, not peer-reviewed research.

### Papers We Love — distributed systems

- **Docs:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** Curated classics including the Google infrastructure papers
- **Downloadable / offline:** Repo cloneable


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*26 resources across 6 topics.*


#### Understand the primitives before the platforms

- **[The Twelve-Factor App](https://12factor.net/)** — Thirty minutes, and it explains why cloud applications are structured the way they are.
- **[OCI Image Specification](https://github.com/opencontainers/image-spec)** — Short spec. Read it and container images stop being magic.
- **[OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)** — The registry API, in a few pages.
- **[Docker documentation](https://docs.docker.com/)** — Get fluent with images, layers and Compose before touching orchestration.
- **[containerd](https://containerd.io/docs/)** — The runtime that both Docker and Kubernetes actually use.


#### Kubernetes, learned properly

- **[Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)** — Build a cluster by hand, component by component, with no automation. The single most effective Kubernetes learning resource.
- **[Kubernetes documentation](https://kubernetes.io/docs/home/)** — Work through the concepts section in order; it is well structured.
- **[Kubernetes reference](https://kubernetes.io/docs/reference/)** — The API reference is authoritative. Learn to read it rather than copying YAML.
- **[Helm](https://helm.sh/docs/)** — Packaging and templating, once raw manifests become painful.


#### Pick one cloud and go deep

- **[AWS documentation](https://docs.aws.amazon.com/)** — Start with IAM, VPC, S3 and EC2. Everything else assumes those four.
- **[Azure documentation](https://learn.microsoft.com/en-us/azure/)** — Start with resource groups, RBAC and networking.
- **[Google Cloud documentation](https://cloud.google.com/docs)** — Start with IAM, VPC and Cloud Run.
- **[DigitalOcean docs and tutorials](https://docs.digitalocean.com/)** — Simpler surface area; the community tutorials are excellent for Linux fundamentals.


#### Free structured training from the providers

- **[AWS Skill Builder](https://skillbuilder.aws/)** — Large free tier including foundational learning plans.
- **[Google Cloud Skills Boost](https://www.cloudskillsboost.google/)** — Hands-on labs in real projects; a substantial free catalogue.
- **[Microsoft Learn training](https://learn.microsoft.com/en-us/training/)** — Entirely free, well-structured learning paths with sandboxes.
- **[Linux Foundation training](https://training.linuxfoundation.org/)** — Several genuinely free courses, including Kubernetes and cloud-native introductions.


#### Infrastructure as code, from the start

- **[Terraform documentation](https://developer.hashicorp.com/terraform/docs)** — Learn state, modules and providers. State is where every beginner gets hurt.
- **[Terraform Registry](https://registry.terraform.io/)** — The real reference for every resource you will write.
- **[OpenTofu](https://opentofu.org/docs/)** — The open-source fork; worth knowing which you are running.
- **[Pulumi](https://www.pulumi.com/docs/)** — If your team would rather write code than HCL.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*31 resources across 6 topics.*


#### Reliability engineering

- **[Google SRE books](https://sre.google/books/)** — All free. SLOs, error budgets, toil, incident response — the shared vocabulary of the discipline.
- **[AWS Well-Architected](https://aws.amazon.com/architecture/well-architected/)** — The six pillars and the lenses. Applicable beyond AWS.
- **[Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/)** — A second perspective on the same questions.
- **[Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework)** — Plus the reference architecture library, which is extensive.
- **[System Design Primer](https://github.com/donnemartin/system-design-primer)** — Breadth-first revision of the design concepts these frameworks assume.


#### Observability in depth

- **[OpenTelemetry specification](https://opentelemetry.io/docs/specs/otel/)** — Read the spec, not just the SDK quickstart. The semantic conventions matter more than the API.
- **[OpenTelemetry docs](https://opentelemetry.io/docs/)** — Collector architecture and instrumentation strategy.
- **[OpenTelemetry source](https://github.com/open-telemetry)** — SDKs and the Collector; the Collector is a good study in pipeline design.
- **[Prometheus](https://prometheus.io/docs/)** — PromQL, recording rules, and the pull model's consequences.
- **[Thanos design docs](https://thanos.io/tip/thanos/design.md/)** — How to make Prometheus global and durable; a real distributed-systems design.
- **[Grafana Loki](https://grafana.com/docs/loki/latest/)** — Label-indexed logging — understand the trade-off before adopting it.
- **[Jaeger](https://www.jaegertracing.io/docs/)** — Trace storage and sampling strategies.


#### Platform engineering & GitOps

- **[Argo CD](https://argo-cd.readthedocs.io/)** — GitOps in practice: sync waves, drift detection, app-of-apps.
- **[Flux](https://fluxcd.io/flux/)** — The other graduated GitOps toolkit; more composable, less opinionated.
- **[Crossplane](https://docs.crossplane.io/)** — Infrastructure as Kubernetes resources. Read the composition model carefully.
- **[Backstage](https://backstage.io/docs/overview/what-is-backstage/)** — Developer portals and software catalogues.
- **[CloudEvents](https://cloudevents.io/)** — A small spec that removes a lot of integration friction.


#### Kubernetes internals

- **[Kubernetes source](https://github.com/kubernetes/kubernetes)** — Read the controller pattern first — `controller-runtime` and one simple controller.
- **[Kubernetes reference docs](https://kubernetes.io/docs/reference/)** — API machinery, admission control, the resource model.
- **[etcd](https://etcd.io/docs/)** — The Raft store underneath. See the distributed-systems index for the consensus material.
- **[Knative](https://knative.dev/docs/)** — Serverless primitives built as Kubernetes extensions — a good study in extending the API.
- **[Nomad](https://developer.hashicorp.com/nomad/docs)** — A simpler scheduler. Useful for seeing which Kubernetes complexity is essential and which is incidental.


#### Serverless & edge

- **[Cloudflare Workers](https://developers.cloudflare.com/)** — The best documentation of the edge compute model, including Durable Objects and R2.
- **[Fly.io docs](https://fly.io/docs/)** — Machines API and multi-region deployment, explained unusually honestly.
- **[Knative Serving](https://knative.dev/docs/serving/)** — Scale-to-zero and request-driven autoscaling.
- **[OpenFaaS](https://docs.openfaas.com/)** — Functions without vendor lock-in.
- **[AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/home.html)** — Typed infrastructure for serverless architectures.


#### Navigating the ecosystem

- **[CNCF Landscape](https://landscape.cncf.io/)** — Filter to graduated projects. That one filter makes it usable.
- **[CNCF projects](https://www.cncf.io/projects/)** — Maturity levels are a reasonable proxy for production readiness.
- **[Linux Foundation training](https://training.linuxfoundation.org/)** — Certification paths (CKA, CKAD, CKS) if credentials matter in your context.
- **[Google Cloud Skills Boost](https://www.cloudskillsboost.google/)** — Advanced hands-on labs, not only introductory ones.


---

## Video courses, channels & talks

*10 resources across 1 group.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[AWS](https://www.youtube.com/@AmazonWebServices)** — Official AWS: re:Invent sessions and service deep dives — a huge, searchable archive.
- **[Google Cloud Tech](https://www.youtube.com/@GoogleCloudTech)** — Official Google Cloud: product talks and architecture series.
- **[Microsoft Azure](https://www.youtube.com/@MicrosoftAzure)** — Official Microsoft Azure channel: Ignite sessions and service explainers.
- **[CNCF](https://www.youtube.com/@cncf)** — KubeCon keynotes and project-maintainer talks across the cloud-native landscape.
- **[Kubernetes](https://www.youtube.com/@kubernetescommunity)** — Official Kubernetes community channel.
- **[The Linux Foundation](https://www.youtube.com/@LinuxFoundationOrg)** — The Linux Foundation channel: kernel and LF event recordings.
- **[InfoQ](https://www.youtube.com/@InfoQ)** — Conference keynotes and architecture talks — good for orientation, verify specifics elsewhere.
- **[HashiCorp](https://www.youtube.com/@HashiCorp)** — HashiConf talks: Terraform, Vault, Consul, Nomad — vendor, but the design talks are real.
- **[Grafana Labs](https://www.youtube.com/@GrafanaLabs)** — GrafanaCon and observability talks; the open-source telemetry stack is documented here in video form.
- **[Tech Field Day](https://www.youtube.com/@TechFieldDay)** — Multi-vendor engineering sessions on cloud and infrastructure; good for comparing implementations.

*Note:* Cloud video is dominated by vendor marketing; it is worth watching for service mechanics and release behaviour, and worthless for architecture judgment.

## Conference videos, notes & archives

*5 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

Cloud video is mostly vendor content, with two exceptions: SREcon is practitioner-authored, and the open-source conferences publish everything.

### Conference channels & video archives

- **[SREcon](https://www.usenix.org/conference/srecon)** — The site reliability engineering conference, run by USENIX — practitioner-authored, no marketing.
- **[USENIX ATC '26](https://www.usenix.org/conference/atc26)** — Where the research behind cloud behaviour gets published; open.
- **[EuroSys](https://www.eurosys.org/)** — Proceedings and selected recordings for the systems side of cloud.
- **[FOSDEM video archive](https://video.fosdem.org/)** — Containers, cloud-infrastructure and observability devrooms.

### Notes, proceedings & paper-adjacent archives

- **[USENIX ;login:](https://www.usenix.org/publications/login/)** — Operations and reliability write-ups; the text equivalent of SREcon.

## If you only do three things

1. **Do Kubernetes the Hard Way.** Build a cluster component by component with no automation. Nothing else teaches it as well.
2. **Read the OCI image and distribution specs.** Two short documents that demystify the entire container ecosystem.
3. **Read the Google SRE book's SLO and error-budget chapters.** Free, and they change how you argue about reliability.

## Honest notes

- **Pick one cloud and learn it deeply** before comparing. IAM and networking are the hard parts everywhere; the rest is services.
- **Terraform's licence changed in 2023** (BUSL), which is why OpenTofu exists. Know which one your organisation is actually running.
- **Linode is now Akamai Cloud Computing.** Old documentation links redirect; bookmarks will rot.
- **The CNCF Landscape is not a shortlist.** Filter to graduated projects, or it is actively unhelpful.
- **Instrument with OpenTelemetry, not a vendor SDK.** It is the one decision here that is genuinely hard to reverse.
- **The free tiers of AWS Skill Builder, Google Cloud Skills Boost and Microsoft Learn are substantial.** Most people pay for courses that duplicate them.

---

## Related sections of this book

- [Cloud & DevOps](../cloud/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
