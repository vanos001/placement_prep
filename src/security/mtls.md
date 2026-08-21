# Mutual TLS (mTLS)

Mutual TLS (mTLS) is an extension of standard TLS where the client also presents an X.509 certificate to the server, in addition to the server presenting its certificate to the client. This provides双向 (bidirectional) authentication: the server proves its identity to the client (standard TLS), and the client proves its identity to the server (the mTLS addition). This page covers the protocol, certificate management, the use cases (service-to-service auth, IoT, financial services), and the operational challenges that have driven adoption of alternative approaches like SPIFFE.

## Why mTLS Exists

Standard TLS authenticates only the server. The client proves its identity through application-layer mechanisms (HTTP Basic Auth, OAuth tokens, session cookies). This works for human-facing applications but has limitations for service-to-service communication:

- **Service-to-service auth needs to be cryptographically strong**, not based on tokens that can be stolen from logs or memory.
- **Tokens are bearer**: any holder can use them. A stolen token grants access until it expires.
- **TLS already exists at the transport layer**: why not use it for client auth too?

mTLS extends TLS to authenticate both sides. A stolen certificate alone doesn't grant access — the attacker also needs the certificate's private key, which is harder to exfiltrate (kept in a separate file, HSM, or OS keychain).

## The Protocol

The TLS 1.3 handshake with mutual authentication:

```text
ClientHello (with client's supported sig algs)
        ↓
ServerHello, Certificate, CertificateRequest ← server asks for client cert
        ↓
Client Certificate ← client presents its cert
Client CertificateVerify ← client proves it has the private key
        ↓
Server verifies client cert chain, completes handshake
```

The `CertificateRequest` message from the server includes:
- A list of acceptable certificate types (e.g., RSA, ECDSA).
- A list of acceptable CAs (the distinguished names of trusted CA subjects).
- A list of acceptable signature algorithms.

The client responds with a `Certificate` message containing its certificate chain. The server verifies the chain against its trust store.

The `CertificateVerify` message proves the client possesses the private key corresponding to the certificate's public key. This is a signature over the handshake transcript — without the private key, the client can't forge it.

In TLS 1.2, the flow is similar but the messages are in different order (the client cert is sent in the same flight as the server cert verification, before the server's Finished).

## Certificate Provisioning

mTLS requires every client to have a certificate. The certificate lifecycle:

1. **Issuance**: a CA issues a certificate to the client (often an internal CA, since public CAs charge per cert and the volume of internal service-to-service certs is high).
2. **Distribution**: the cert + private key are deployed to the client (via secrets management, filesystem, or HSM).
3. **Rotation**: certs expire; the deployment must rotate them before expiry.
4. **Revocation**: if a client is compromised, its cert must be revoked via a CRL or OCSP.

Production deployments use one of these patterns:

### Pattern 1: Long-lived certs with manual rotation

Certs are issued with a 1-year validity and rotated annually via the secrets management system. Simple but risky (human error in rotation).

### Pattern 2: SPIFFE/SPIRE for short-lived certs

The SPIFFE (Secure Production Identity Framework for Everyone) standard, with the SPIRE runtime, issues certs with short validity (e.g., 1 hour). The SPIRE agent on each workload requests a new cert before the previous one expires. The rotation is automatic.

```text
SPIRE Server (cluster-level)
    │
    │ Issues certs to agents based on workload identity
    ▼
SPIRE Agent (per node)
    │
    │ Issues certs to workloads via workload API
    ▼
Workload (e.g., service A)
    │ Uses cert + private key (in-memory, not on disk) for mTLS
```

SPIFFE's cert format (SVID, SPIFFE Verifiable Identity Document) is a standard X.509 cert with a URI SAN in the format `spiffe://example.com/ns/default/sa/serviceA`. The URI is the workload's identity.

### Pattern 3: Cloud-native identity (e.g., AWS IAM Roles for Service Accounts, GCP Workload Identity)

The cloud platform injects credentials into the workload. mTLS is replaced with token-based auth (the token proves the workload's identity), and the transport is standard TLS (authenticating only the server). This is simpler than mTLS but ties you to the cloud platform.

## Use Cases

### Service-to-service in microservices

The classic mTLS use case: every service in a mesh authenticates every other service at the transport layer, regardless of the application protocol.

```text
Service A (client cert: spiffe://.../sa/serviceA)
    │ mTLS handshake
    ▼
Service B (client cert: spiffe://.../sa/serviceB)
```

Istio, Linkerd, Consul Connect, and AWS App Mesh all use mTLS for service mesh authentication. SPIFFE is the underlying identity standard for Istio and Linkerd.

### IoT devices

IoT devices have a unique identity (typically a cert burned into the device at manufacturing). mTLS authenticates the device to the cloud platform, preventing rogue devices from impersonating legitimate ones.

### Financial services (PSD2)

The EU's PSD2 directive requires strong customer authentication for online payments. Some implementations use mTLS with smartcard-based client certs for corporate banking.

### Internal PKI

Corporate VPN clients (OpenVPN, Cisco AnyConnect) often use client certs for authentication, alongside or instead of passwords.

## mTLS in Service Meshes

A service mesh (Istio, Linkerd) deploys a sidecar proxy on each service. The sidecar handles mTLS:

```text
Service A
    │
    │ HTTP request (no TLS, localhost)
    ▼
Envoy sidecar (Service A)
    │
    │ mTLS to Envoy sidecar of Service B
    ▼
Envoy sidecar (Service B)
    │
    │ HTTP request (no TLS, localhost)
    ▼
Service B
```

The services themselves don't need to handle mTLS — the sidecars do it. This is the basis of zero-trust networking in Kubernetes.

The sidecars share a CA (typically via SPIRE or a Kubernetes-local CA) and rotate certs automatically based on the workload's identity.

## Comparison to Alternatives

| Approach | Transport auth | App-layer auth | Complexity | Cloud-portable |
|----------|----------------|-----------------|------------|----------------|
| mTLS + SPIFFE | ✓ (strong) | Optional | High | Yes |
| Bearer tokens (OAuth) | ✗ | ✓ (medium) | Medium | Yes |
| Cloud IAM (AWS, GCP) | ✗ | ✓ (medium) | Low | No |
| Network ACLs (IP allow) | ✗ | ✗ | Low | No |

mTLS's advantage is cryptographic strength + cloud-agnostic. Its disadvantage is operational complexity — cert provisioning, rotation, revocation.

## Operational Challenges

1. **Cert provisioning**: every service needs a cert. Manual provisioning doesn't scale; use SPIFFE or a cloud-managed CA.

2. **Cert rotation**: certs expire. Without automatic rotation, services go down on cert expiry. SPIRE rotates hourly; manual systems need a 2-month buffer.

3. **Revocation is hard**: CRLs are slow to propagate (clients must fetch and check them); OCSP has performance and privacy issues. Short-lived certs (1 hour) sidestep revocation — a revoked cert is invalid within 1 hour.

4. **Debugging is hard**: a mTLS failure gives a generic "handshake failure" error. Figuring out which cert is wrong (client cert, server cert, CA) requires access to both sides' logs.

5. **Performance**: mTLS handshakes are slightly slower than one-way TLS (one extra cert exchange + signature verification). With TLS 1.3 session resumption, this overhead is amortized across requests.

## Common Pitfalls

1. **Using long-lived certs without revocation.** A 1-year cert that's stolen is valid for a year. Either use short-lived certs or implement revocation properly.

2. **Trusting the wrong CA.** The server must trust the CA that issued the client's cert, not any public CA. Use a private CA for service-to-service mTLS.

3. **Forgetting to validate the certificate's identity.** The server should verify the client's cert has the expected SPIFFE ID (or expected SAN). Just verifying the chain is not enough — anyone with a valid cert from the same CA can authenticate.

4. **Storing private keys on disk unencrypted.** The private key file should be readable only by the service account, not by every user on the host. Better: use a SPIRE agent that delivers the key in-memory only.

5. **Mixing mTLS with bearer tokens.** A common anti-pattern is using mTLS for transport auth and OAuth tokens for app auth, but treating them as redundant (any one suffices). This gives attackers two paths to compromise. Pick one auth model and use it consistently.

6. **Not handling cert rotation gracefully.** A rotation that drops in-flight TLS connections will cause request failures. The server should accept both the old and new cert during a rotation window.

## References

- [RFC 8446: TLS 1.3](https://datatracker.ietf.org/doc/html/rfc8446) — section on client authentication
- [RFC 5280: X.509 certificates](https://datatracker.ietf.org/doc/html/rfc5280)
- [SPIFFE specification](https://github.com/spiffe/spiffe)
- [SPIRE: SPIFFE Runtime Environment](https://github.com/spiffe/spire)
- [Istio mTLS documentation](https://istio.io/latest/docs/concepts/security/#mutual-tls-authentication)
- [Linkerd mTLS documentation](https://linkerd.io/2/features/mtls/)
- [AWS App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html)
- [LWN: SPIFFE and workload identity (2021)](https://lwn.net/Articles/856642/)
