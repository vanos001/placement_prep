# Kubernetes Admission Webhooks

Admission webhooks are HTTP callbacks that Kubernetes calls during API request processing, after authentication and authorization but before the resource is persisted to etcd. They allow operators and platform teams to enforce policies, inject defaults, and mutate resources before they reach the cluster. This page covers the two webhook types (mutating and validating), the webhook configuration, the request/response format, and the operational patterns that have made webhooks the dominant Kubernetes extensibility mechanism.

## Where Webhooks Sit

```text
Client (kubectl, controller, API) → API Server
                                      │
                                      ▼
                                  Authentication (who are you?)
                                      │
                                      ▼
                                  Authorization (can you do this?)
                                      │
                                      ▼
                                  Admission Controllers:
                                  ┌─────────────────┐
                                  │ Built-in         │  ← e.g., NamespaceLifecycle,
                                  │ (always-on)      │    ResourceQuota, LimitRanger
                                  └─────────────────┘
                                      │
                                      ▼
                                  Mutating Webhooks  ← invoke external HTTP services to modify objects
                                      │
                                      ▼
                                  Validating Webhooks ← invoke external HTTP services to reject objects
                                      │
                                      ▼
                                  Schema Validation
                                      │
                                      ▼
                                  etcd (object persisted)
```

Mutating webhooks run before validating webhooks so the latter can check the post-mutation state. Both run only for `CREATE`, `UPDATE`, `DELETE`, and (rarely) `CONNECT` operations — not for `GET`/`LIST`.

## Mutating vs Validating

- **Mutating webhook**: can modify the object (e.g., inject a sidecar container, set default labels, set image digests). Returns a JSON patch describing the changes.
- **Validating webhook**: cannot modify the object; can only accept or reject. Returns a yes/no decision with an error message.

Most production policies use both: a mutating webhook to set defaults, then a validating webhook to enforce hard rules.

## Webhook Configuration

Mutating webhooks are configured via `MutatingWebhookConfiguration`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: inject-sidecar.example.com
webhooks:
- name: inject-sidecar.example.com
  clientConfig:
    service:
      name: sidecar-injector
      namespace: platform
      path: /mutate
    caBundle: <base64 of CA cert>
  rules:
  - operations: ["CREATE"]
    apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
  namespaceSelector:
    matchLabels:
      sidecar-injection: enabled
  failurePolicy: Fail   # if webhook is unavailable, reject the request
  timeoutSeconds: 10    # max time to wait for webhook response
```

Validating webhooks are configured via `ValidatingWebhookConfiguration`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: require-image-digest.example.com
webhooks:
- name: require-image-digest.example.com
  clientConfig:
    service:
      name: policy-validator
      namespace: platform
      path: /validate
    caBundle: <base64 of CA cert>
  rules:
  - operations: ["CREATE", "UPDATE"]
    apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
  failurePolicy: Fail
  timeoutSeconds: 5
```

The `clientConfig.service` references a Kubernetes Service that load-balances to the webhook server pods. The `caBundle` is the CA that signed the webhook server's TLS cert (the API server verifies it).

## The Webhook Request

When the API server invokes a webhook, it sends an `AdmissionReview` request:

```json
{
  "apiVersion": "admission.k8s.io/v1",
  "kind": "AdmissionReview",
  "request": {
    "uid": "9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a",
    "kind": { "group": "", "version": "v1", "kind": "Pod" },
    "resource": { "group": "", "version": "v1", "resource": "pods" },
    "name": "myapp-abc123",
    "namespace": "production",
    "operation": "CREATE",
    "userInfo": {
      "username": "alice@example.com",
      "groups": ["system:authenticated", "developers"]
    },
    "object": { ... full Pod object ... },
    "oldObject": null,
    "options": { ... kubectl options ... }
  }
}
```

For UPDATE/DELETE, `oldObject` contains the previous version. The webhook can compare `object` and `oldObject` to enforce immutability rules.

## The Webhook Response

The webhook returns an `AdmissionReview` response:

```json
{
  "apiVersion": "admission.k8s.io/v1",
  "kind": "AdmissionReview",
  "response": {
    "uid": "9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a",
    "allowed": true,
    "patchType": "JSONPatch",
    "patch": "W10="  // base64-encoded JSON patch
  }
}
```

For a validating webhook rejecting the request:

```json
{
  "apiVersion": "admission.k8s.io/v1",
  "kind": "AdmissionReview",
  "response": {
    "uid": "9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a",
    "allowed": false,
    "status": {
      "code": 403,
      "message": "Pod rejected: image must use a digest, not a tag"
    }
  }
}
```

The `patch` is a JSON Patch (RFC 6902) describing the mutations to apply. A typical patch might inject a sidecar:

```json
[
  {
    "op": "add",
    "path": "/spec/containers/-",
    "value": {
      "name": "istio-proxy",
      "image": "istio/proxyv2:1.20",
      ...
    }
  }
]
```

## Common Patterns

### Pattern 1: Sidecar Injection (Istio, Linkerd)

The Istio sidecar injector adds an `istio-proxy` container to every Pod in namespaces labeled `istio-injection: enabled`. The webhook:

1. Receives the Pod creation request.
2. Inspects the Pod's metadata for injection annotations.
3. Generates a JSON patch to add the sidecar container, the init container, and the necessary volumes.
4. Returns the patch.

### Pattern 2: Image Digest Pinning

A policy webhook that replaces image tags with digest references:

```json
{
  "op": "replace",
  "path": "/spec/containers/0/image",
  "value": "nginx@sha256:abc..."
}
```

The webhook resolves the tag to a digest by querying the registry, then patches the image. This ensures the deployed image is reproducible (no surprise tag updates).

### Pattern 3: Resource Defaults

A webhook that sets default resource requests/limits if not specified:

```json
[
  {
    "op": "add",
    "path": "/spec/containers/0/resources/requests",
    "value": { "cpu": "100m", "memory": "128Mi" }
  }
]
```

### Pattern 4: Policy Enforcement (Kyverno, OPA Gatekeeper)

Kyverno and OPA Gatekeeper are policy engines that run as admission webhooks. They:

1. Receive every AdmissionReview.
2. Evaluate against a policy (YAML in Kyverno, Rego in OPA).
3. Return allow/deny + patches for mutations.

For example, OPA Gatekeeper can enforce "no privileged pods in production namespaces":

```rego
package k8s.denypodprivilege

violation[msg] {
  input.review.object.kind == "Pod"
  input.review.object.metadata.namespace == "production"
  container := input.review.object.spec.containers[_]
  container.securityContext.privileged == true
  msg := sprintf("Privileged container not allowed in production: %v", [container.name])
}
```

## Operational Considerations

1. **Webhook availability is critical.** If a webhook is configured with `failurePolicy: Fail` and the webhook server is down, every API request that matches the webhook's rules fails. This blocks deployments, scaling, even pod restarts. Use `failurePolicy: Ignore` for non-critical webhooks.

2. **Webhook latency affects cluster responsiveness.** Every API request matching the webhook's rules pays the webhook's RTT. A 100 ms webhook on Pod creation slows down rolling updates. Keep webhooks under 100 ms.

3. **The webhook server needs HA.** Run the webhook with multiple replicas (Deployment with 3+ replicas) and use a Service for load balancing. If the webhook is a single Pod, an eviction during a node drain can block cluster operations.

4. **Order matters for mutating webhooks.** Kubernetes runs mutating webhooks in alphabetical order by webhook name. If webhooks A and B both modify the same field, the result depends on order. Use distinct webhook names to control order.

5. **Don't modify immutable fields.** Some fields (e.g., Pod's `spec.containers[*].name` after creation) cannot be modified. A mutating webhook that tries to modify these will fail the entire admission chain.

## Common Pitfalls

1. **Self-deadlock.** If a webhook's own Deployment needs the webhook's approval to scale up, scaling down to 0 (or evicting all pods) blocks further scaling. Always exclude the webhook's own namespace from its rules.

2. **TLS cert rotation breaks the cluster.** The webhook server's TLS cert is referenced in the `MutatingWebhookConfiguration`. If the cert expires without rotation, all API requests that match the webhook's rules fail. Use cert-manager with the `cert-manager.io/inject-ca-from` annotation to auto-rotate.

3. **Slow webhook on the critical path.** A webhook that makes external API calls (e.g., to a CMDB or policy server) can take seconds. Cache aggressively; for resources that can be validated synchronously, do it locally.

4. **Forgetting to handle the `DELETE` operation.** A webhook that handles `CREATE` but not `DELETE` can let a Pod delete itself while a mutating webhook is processing its creation, leading to race conditions.

5. **Not testing webhook changes in a staging cluster.** A bad webhook (e.g., one that rejects all Pods) takes the entire cluster down. Always test in staging first, with `failurePolicy: Ignore` initially.

6. **Forgetting that the API server calls the webhook in-band.** If the webhook is in a different cluster or behind a slow network, the API server's request times out. Run the webhook in the same cluster as the API server.

## References

- [Kubernetes: Admission Controllers Reference](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Kubernetes: Dynamic Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [MutatingWebhookConfiguration API reference](https://kubernetes.io/docs/reference/kubernetes-api/cluster-resources/mutating-webhook-configuration-v1/)
- [Kyverno: policy as code](https://kyverno.io/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/)
- [Istio sidecar injector source code](https://github.com/istio/istio/tree/master/pkg/kube/inject)
- [cert-manager: securing admission webhooks](https://cert-manager.io/docs/concepts/ca-injector/)
- [LWN: Kubernetes admission webhooks (2020)](https://lwn.net/Articles/815529/)
