# cert-manager — Kubernetes Certificate Management

cert-manager is the de-facto TLS certificate controller for Kubernetes. Originally developed by Jetstack (now part of Venafi), it graduated in the CNCF in 2024 and is installed on a majority of production clusters. It does three jobs: it issues certificates (from internal CAs or Let's Encrypt/ZeroSSL), it rotates them before they expire, and it puts them into Kubernetes `Secret`s that Pods, Ingresses, and other CRDs consume. Underneath, it's a controller-runtime application that watches a set of CRDs and orchestrates the ACME/CA workflow asynchronously.

## CRDs (the API surface)

cert-manager adds six core CRDs:

```
ClusterIssuer         -- cluster-scoped CA configuration
Issuer                -- namespace-scoped CA configuration
Certificate           -- the "I want a cert for these names" request
CertificateRequest    -- internal sub-resource; one per cert per renewal attempt
Order (acme.cert-manager.io)   -- ACME order object, one per cert per issuance
Challenge (acme.cert-manager.io) -- ACME challenge solver state
```

### Certificate CRD

The most user-facing CRD. A `Certificate` describes the desired state — a private key, a set of hostnames, a target Secret, and an Issuer reference. cert-manager reconciles the cluster toward this state.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-tls
  namespace: default
spec:
  secretName: api-tls                 # where the cert+key land
  duration: 2160h                     # 90d (must be <= issuer's max)
  renewBefore: 720h                   # start renewing 30d before expiry
  subject:
    organizations: ["Acme Inc."]
  commonName: api.example.com
  dnsNames:
    - api.example.com
    - api-v2.example.com
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  privateKey:
    algorithm: ECDSA
    size: 256
  usages:
    - digital signature
    - server auth
  keystores:
    pkcs12:
      create: true
      passwordSecretRef:
        name: p12-password
        key: password
        # the secret holding the password must already exist
```

The `status` field reports `Ready: True`, `NotAfter`, and `FailureTime` after a reconciliation cycle. cert-manager writes the issued `tls.crt`, `tls.key`, and `ca.crt` keys to the referenced Secret with type `kubernetes.io/tls`.

### Issuer and ClusterIssuer

`Issuer` and `ClusterIssuer` are the same object with different scopes — namespace-scoped vs cluster-scoped. They describe *how* to get a cert, not which cert to get. There are four kinds:

| Type                  | Use case                                                                 |
|-----------------------|---------------------------------------------------------------------------|
| `acme`                | Public-trusted certs via Let's Encrypt / ZeroSSL / Buypass                |
| `ca`                  | Internal PKI; signer key lives in a Secret                               |
| `selfsigned`          | Bootstrapping: generates a CA cert from its own public key                |
| `vault`               | HashiCorp Vault PKI mount integration                                     |
| `venafi`              | Venafi TPP / Flex (enterprise commercial CA)                              |

#### ACME ClusterIssuer

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    email: ops@example.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod-key     # cert-manager stores the ACME account key here
    solvers:
      - http01:
          ingress:
            class: nginx
      - selector:
          dnsZones:
            - "example.com"
        dns01:
          route53:
            region: us-east-1
            hostedZoneID: Z2KVMVRTXXXXXX
            auth:
              kubernetes:
                serviceAccountRef:
                  name: cert-manager-route53
```

The `privateKeySecretRef` field is *the ACME account key*, not a TLS key. cert-manager generates an ECDSA P-256 keypair on first use, registers an ACME account at the `server` URL with the configured `email`, and stores the private key in the named Secret. All subsequent ACME orders are signed with this key.

#### Self-signed (bootstrap) Issuer

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: bootstrap-selfsigned
spec:
  selfsigned: {}
```

The self-signed issuer signs the cert with the key whose public key the cert contains. It's the cryptographic chicken-and-egg escape hatch: you use it to mint a CA cert, then turn that CA cert into a `ca` Issuer.

#### CA Issuer

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: internal-ca
  namespace: default
spec:
  ca:
    secretName: internal-ca-keypair   # must contain tls.crt + tls.key
```

The CA Issuer signs CertificateRequest CSRs with the private key in `secretName`. The Secret can be populated manually or bootstrapped via the self-signed flow.

## ACME integration: solvers and challenge routing

`spec.acme.solvers` is a list of ACME challenge solvers. cert-manager walks the list to pick one per identifier (matching via `selector.dnsZones`, `selector.dnsNames`, `selector.matchLabels`). The two solver types correspond exactly to the two ACME challenges that work for normal Kubernetes deployments:

### HTTP01 solver

```yaml
solvers:
  - http01:
      ingress:
        class: nginx            # apply to Ingresses with kubernetes.io/ingress.class: nginx
        serviceType: ClusterIP  # NodePort works too; needed if behind ELB
        ingressTemplate:
          metadata:
            annotations:
              nginx.ingress.kubernetes.io/whitelist-source-range: "0.0.0.0/0"
```

How it works: when a challenge needs solving, cert-manager creates a Pod running a tiny HTTP server that returns the ACME `key authorization` at `/.well-known/acme-challenge/<token>`. It also creates a temporary Ingress resource (with the configured `class`) routing the host to that Service. Let's Encrypt hits the Ingress, gets the right response, and validates the challenge. After validation cert-manager deletes the Pod, Service, and Ingress.

The temporary Ingress typically looks like:

```
cm-acme-http-solver-<random>:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /.well-known/acme-challenge/<token>
            pathType: Prefix
            backend:
              service:
                name: cm-acme-http-solver-<random>
                port:
                  number: 8089
```

A common failure mode: the temporary Ingress conflicts with the production Ingress for the same hostname, especially with `ingress-nginx`. The fix is to either (a) use the `ingressTemplate` to inject a specific ingress class, or (b) ensure the production Ingress does not already define a path matching `/.well-known/acme-challenge`.

### DNS01 solver

```yaml
solvers:
  - dns01:
      cloudflare:
        email: ops@example.com
        apiKeySecretRef:
          name: cloudflare-api
          key: apikey
  - dns01:
      route53:
        region: us-east-1
        hostedZoneID: Z2KVM...
        auth:
          kubernetes:
            serviceAccountRef:
              name: cert-manager-route53
```

cert-manager supports Cloudflare, Route53, Google Cloud DNS, Azure DNS, DigitalOcean, Akamai, RFC2136 (dynamic DNS), and webhook providers (which extend the controller without code changes). DNS01 is the only way to get **wildcard** certificates from Let's Encrypt (`*.example.com`).

The mechanics: cert-manager publishes a TXT record at `_acme-challenge.<domain>` via the provider's API, polls the authoritative DNS via `8.8.8.8`/`1.1.1.1` until it sees the record, then asks the ACME server to validate. After validation, it deletes the TXT record.

DNS01 has subtle failure modes:

- **Propagation delays** — Some authoritative DNS servers take 60+ seconds to reflect a TXT record update. cert-manager has a configurable `--dns01-recursive-nameservers-only` flag and default `Wait For` time.
- **Stale records** — If a previous TXT record wasn't cleaned up, the new one may be appended (TXT records can have multiple values), and the CA may pick the wrong one. Always use unique token values.
- **Provider API rate limits** — Cloudflare's API allows 1200 req/5min per zone; bulk re-issuance can hit this.

### Order and Challenge sub-CRDs

When cert-manager issues a Certificate via an ACME Issuer, it creates:

1. A `CertificateRequest` (which encapsulates the CSR for the cert-manager controller).
2. An `Order` (the ACME order object — has status `pending`, `valid`, `invalid`).
3. One `Challenge` per authorization in the order. Each Challenge has status `pending → processing → valid/invalid`.

```
Certificate (api-tls)
  └─> CertificateRequest (api-tls-1)
        └─> Order (api-tls-1-<rand>)
              ├─> Challenge (http-01, status=valid)
              ├─> Challenge (http-01, status=valid)
              └─> [server returns cert]
                    └─> cert-manager writes Secret api-tls
```

You typically only see the `Certificate` directly; `Order` and `Challenge` are managed for you but are useful for debugging.

## Certificate rotation

Two fields control timing:

| Field          | Default | Purpose                                        |
|----------------|---------|-------------------------------------------------|
| `duration`     | 2160h (90d) for ACME; CA-dependent otherwise | Cert validity window           |
| `renewBefore`   | 1/3 of duration (30d for 90d)  | When to start renewal attempts                |
| `revisionHistoryLimit` | 1 | How many old CertificateRequests to retain |

Note: `renewBefore` can be 1/3 .. 2/3 of duration per cert-manager validation rules — values outside this range are rejected.

cert-manager runs a renewal loop every minute. For every Certificate, it computes `notAfter - now < renewBefore`; if true, it kicks off a new issuance cycle. After a successful renewal, the *new* `tls.key`+`tls.crt` are written atomically to the Secret, replacing the old ones. Pods that mount the Secret will see the new bytes — but only after a Pod restart or a manual reload, unless you've plumbed `inotify`/`fsnotify` or use a sidecar that reloads (e.g., `nginx-ingress` watches and reloads automatically; a `python` app does not).

`rotationPolicy: Always` forces a new private key on every renewal (good hygiene, slower). `rotationPolicy: Never` reuses the private key (faster, simpler; matches Let's Encrypt's default behavior since certbot doesn't rotate keys either).

```yaml
spec:
  rotationPolicy: Always       # rotate private key on every renewal
  privateKey:
    rotationPolicy: Always     # alias supported in v1.13+
```

## Wildcard certificates

Wildcards are first-class. The Certificate spec simply lists the wildcard as one of the `dnsNames`:

```yaml
spec:
  secretName: wildcard-tls
  dnsNames:
    - example.com
    - "*.example.com"
  issuerRef:
    name: letsencrypt-prod-dns01
    kind: ClusterIssuer
```

The referenced Issuer must have a DNS01 solver because HTTP-01 cannot validate wildcards. The two SANs (`example.com` and `*.example.com`) cover both the apex and one level of subdomain.

## Ingress shim (the Ingress integration)

cert-manager can issue certs directly from Ingress annotations, without an explicit `Certificate` manifest:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    cert-manager.io/common-name: api.example.com
    cert-manager.io/duration: 2160h
    cert-manager.io/renew-before: 720h
spec:
  ingressClassName: nginx
  tls:
    - hosts: [api.example.com, api-v2.example.com]
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8080
```

When cert-manager sees this Ingress with `cert-manager.io/cluster-issuer`, it synthesizes a `Certificate` with the `spec.tls.hosts` list and `secretName`, then reconciles. The result is exactly what you'd write by hand.

The Ingress shim handles HTTP-01 challenges elegantly: the cert-manager-controller modifies the *production* Ingress (not a temporary one) to add the `/.well-known/acme-challenge/<token>` path during validation, then removes it after. This avoids the temporary-Ingress conflicts that the standalone HTTP01 solver can hit.

## End-to-end debug of a stuck cert

When a `Certificate` is stuck in `Pending` or `Ready: False`, the typical debug path:

```bash
# 1. Inspect the Certificate's status.conditions
kubectl describe certificate api-tls -n default

# 2. The condition "Ready" message references the failed CertificateRequest
kubectl get certificaterequest -n default
kubectl describe certificaterequest api-tls-1 -n default

# 3. For ACME issuers, the Order and Challenge are next
kubectl get order,challenge -n default

# 4. The Challenge status shows what cert-manager did and what the ACME server replied
kubectl describe challenge <challenge-name> -n default

# 5. cert-manager logs (controller Pod)
kubectl logs -n cert-manager -l app.kubernetes.io/component=controller --tail=200

# 6. If it's an HTTP01 failure, check the temporary solver Pod / Ingress
kubectl get pods,ingress -n default -l acme.cert-manager.io/http01-solver=true
```

The most common failures are: HTTP01 ingress-class mismatch (solver Ingress can't be served because no Ingress controller watches the class), DNS01 propagation timeouts (TXT record published but authoritative DNS hasn't propagated), and rate limits (the order stays `invalid` and the ACME error is `urn:ietf:params:acme:error:rateLimit`).

## Architecture under the hood

```
                 +---------------------------------+
                 |  cert-manager-controller (Pod)  |
                 |  - Starters (each watches CRDs) |
                 |   o Issuer controller           |
                 |   o Certificate controller       |
                 |   o CertificateRequest controller|
                 |   o Order controller             |
                 |   o Challenge controller         |
                 +----------------+----------------+
                                  |
       +--------------------------+--------------------------+
       |                          |                          |
       v                          v                          v
+----------------+         +----------------+         +----------------+
| Internal CA    |         | Vault PKI mount|         | ACME (LE, etc.)|
| (Secret+CA Iss)|         |                |         |                |
+----------------+         +----------------+         +----------------+
       |                                                       |
       |        +-----------------------------------------------+ 
       |        |  challenge solvers                            |
       |        |   o http01: Pod + Service + Ingress           |
       |        |   o dns01: provider API (Route53/CF/...)       |
       |        +-----------------------------------------------+
       |
       v
  Kubernetes Secret (tls.crt, tls.key, ca.crt)
       |
       v
  Mounted by Pods / consumed by Ingress
```

cert-manager runs as a Deployment of 1 replica (the controllers are leader-elected so you can scale horizontally) plus an optional cainjector that helps with webhook CA bootstrap.

## A minimal Python helper: poll Certificate Ready

```python
import base64
import json
import time
import urllib3
from kubernetes import client, config


def wait_for_certificate_ready(name: str, namespace: str, timeout_s: int = 600) -> bool:
    """Block until cert-manager's Certificate is Ready or timeout."""
    config.load_kube_config()
    crds = client.CustomObjectsApi()

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        obj = crds.get_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            namespace=namespace,
            plural="certificates",
            name=name,
        )
        for cond in obj.get("status", {}).get("conditions", []):
            if cond["type"] == "Ready" and cond["status"] == "True":
                return True
            if cond["type"] == "Ready" and cond["status"] == "False":
                print(f"Certificate {name} not ready: {cond.get('message')}")
        time.sleep(5)
    return False


def read_tls_secret(name: str, namespace: str) -> dict:
    """Fetch cert-manager-written Secret and decode its tls.crt and tls.key."""
    config.load_kube_config()
    corev1 = client.CoreV1Api()
    sec = corev1.read_namespaced_secret(name=name, namespace=namespace)
    return {
        "tls.crt": base64.b64decode(sec.data["tls.crt"]).decode("ascii"),
        "tls.key": base64.b64decode(sec.data["tls.key"]).decode("ascii"),
        "ca.crt": (base64.b64decode(sec.data["ca.crt"]).decode("ascii")
                   if "ca.crt" in sec.data else None),
    }
```

Note that `wait_for_certificate_ready` is a polling approach; in production you'd watch the CRD with `stream()` for event-driven notification.

## Operational best practices

- **Use the staging issuer first.** Let's Encrypt's staging endpoint has generous rate limits and is otherwise identical. Switch to prod after cert issuance works.
- **Pin cert-manager versions.** cert-manager occasionally breaks CRD compatibility across minor versions; review upgrade notes for `kubectl apply`.
- **Protect the ACME account key Secret.** It's tied to your Let's Encrypt account; if lost, you can re-register but rate-limit history is tied to the account.
- **Don't disable the `cert-manager-cainjector`.** It bootstraps the CA for the validating webhook; disabling it means future cert-manager Pod restarts can't validate CRDs.
- **Always set `renewBefore` explicitly.** Defaults of "1/3 of duration" change between cert-manager versions; pinning prevents surprises.
- **Use `revisionHistoryLimit: 5`** in high-traffic clusters to debug failed renewals.

## Comparison with alternatives

| Tool                                | Scope                                        |
|-------------------------------------|-----------------------------------------------|
| cert-manager                         | Cluster-wide CRD-based, multi-issuer          |
| External-secrets                     | Pulls TLS material from external secret stores (Vault, AWS SM) — doesn't issue |
| HashiCorp Vault Agent sidecar       | Per-Pod mounting of Vault-issued material     |
| Traefik's built-in ACME              | Simpler; only Traefik ingress, no Ingress-Nginx |
| Caddy                                | Single-binary webserver with built-in ACME    |

cert-manager wins on portability across ingress controllers and the ability to mix issuers (internal CA for mTLS, Let's Encrypt for public).

## References

- cert-manager official documentation — https://cert-manager.io/docs/
- cert-manager GitHub (Jetstack/cert-manager) — https://github.com/cert-manager/cert-manager
- cert-manager configuration reference — https://cert-manager.io/docs/reference/
- cert-manager troubleshooting — https://cert-manager.io/docs/troubleshooting/
- cert-manager Ingress shim — https://cert-manager.io/docs/usage/ingress/
- Kubernetes Ingress concept documentation — https://kubernetes.io/docs/concepts/services-networking/ingress/
- Kubernetes Ingress network path — https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/
- RFC 8555 (ACME) — https://www.rfc-editor.org/rfc/rfc8555
- cert-manager security disclosures and policies — https://github.com/cert-manager/cert-manager/security/policy
- CNCF cert-manager graduation announcement (2024) — https://www.cncf.io/announcements/2024/06/25/cert-manager-graduates-from-cncf-incubator/
- Jetstack corporate site — https://www.jetstack.io/

## Interview Questions

1. **What's the difference between an `Issuer` and a `ClusterIssuer`? When would you use each?**
2. **Walk through how cert-manager satisfies an HTTP-01 challenge. What resources does it create?**
3. **Why must wildcard certs use a DNS01 solver? What does cert-manager do to publish the TXT record?**
4. **Explain the relationship between `Certificate`, `CertificateRequest`, `Order`, and `Challenge`.**
5. **A `Certificate` is stuck in `Ready: False`. Walk through your debug path.**
6. **What does `renewBefore` control? What happens if it's larger than `duration`?**
7. **How does the Ingress shim differ from an explicit `Certificate` resource?**
8. **What does the `cainjector` Pod do, and what breaks if you disable it?**
9. **You have an internal CA. How would you configure cert-manager to issue internal-trusted certs for mTLS between services?**
10. **Compare cert-manager to running Vault's PKI engine as a sidecar. Why pick one over the other?**
