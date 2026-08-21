# Zero Trust Network Access (ZTNA)

"Zero trust" is the architectural position that no network location is more trustworthy than another: every access decision is made dynamically, based on the identity of the user, the posture of the device, and the sensitivity of the resource, regardless of whether the request originates inside or outside the corporate network. The term was coined by John Kindervag at Forrester in 2010, formalized by NIST in SP 800-207 (2020), and popularized by Google's BeyondCorp papers (2014-2017). This page covers the model, the components, the contrast with perimeter VPNs, microsegmentation, and the SASE convergence trend.

## Why "Zero Trust"

The traditional enterprise security model was castle-and-moat:
- Inside the corporate LAN, machines trusted each other.
- Outside the LAN, the VPN gateway was the chokepoint.
- Once a user connected to the VPN, they were "on the network" — they could reach any IP that the routing table allowed.

This broke for several reasons:

1. **Lateral movement.** A phishing compromise gave an attacker a foothold on one laptop inside the VPN; from there, they could reach every internal service. The 2013 Target breach and 2017 NotPetya both exploited this: the initial foothold was a low-privilege VPN/session, but lateral movement to the billing and SCM systems was unimpeded because the internal network had no per-application auth.

2. **Perimeter leaks.** Cloud services, SaaS apps, and remote workers meant the "perimeter" was no longer a clean line. A user on a home WiFi could be just as "inside" as a user on the office WiFi.

3. **Insider risk.** A helpdesk technician on the corporate LAN could read the HR database by IP routing alone — there was no application-layer identity check.

Zero trust removes the assumption that being "on the network" grants anything. Every request is evaluated against policy; the network is just a transport.

## NIST SP 800-207: The Reference Architecture

NIST SP 800-207 defines zero trust in terms of three components:

```text
                    +----------------------+
                    |   Policy Engine (PE) |
                    |  + Policy Decision   |
                    |    Point (PDP)       |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |  Policy Enforcement  |
                    |  Point (PEP) — proxy |
                    |  in front of resource|
                    +----------+-----------+
                               |
        +----------------------+----------------------+
        |                                             |
   +----v----+                                  +----v----+
   | Subject |                                  | Resource |
   | (user + |                                  | (app/db/ |
   |  device)|                                  |  API)    |
   +---------+                                  +----------+
```

- **Policy Engine (PE/PDP)** — the brain. Reads signals (identity, device posture, time, geo, risk score) and decides allow or deny per request.
- **Policy Enforcement Point (PEP)** — the bouncer. Sits in the data path (reverse proxy, sidecar, agent), terminates the user's session, and forwards only allowed requests to the resource.
- **Trust algorithm** — the function the PE uses. NIST describes two approaches: explicit rules (allow/deny per principal+resource+context) and risk-scored (a numeric threshold applied to a weighted signal sum).

The control plane (PE + PEP config) is decoupled from the data plane (PEP forwarding traffic). The PEP is a per-application proxy, not a network-wide VPN concentrator.

## Device Posture

Device posture is a set of signals that the PE evaluates alongside user identity:

| Signal | Example | Source |
|---|---|---|
| OS version | Windows 11 23H2, kernel 6.5 | device agent |
| Disk encryption | BitLocker on, FileVault on | OS query |
| EDR status | CrowdStrike sensor running | EDR API |
| Patch level | No critical CVEs older than 30 days | MDM API |
| Root / jailbreak | False | device agent |
| Cert serial | X.509 cert issued by corporate CA | MDM |

A device agent or MDM (Jamf for Mac, Intune for Windows, Fleet for Linux) collects these and posts them to the PE. The PE's trust algorithm produces a per-request verdict:

```text
trust_score = w1 * identity_score
            + w2 * device_score
            + w3 * behavior_score
            - w4 * risk_score

if trust_score >= resource_threshold:
    allow
elif trust_score >= step_up_threshold:
    require_mfa()
else:
    deny
```

The threshold is per-resource: a "low" resource (internal wiki) accepts any compliant device with a valid identity; a "high" resource (production DB) requires managed device + hardware MFA + just-in-time approval.

## Continuous Verification

Traditional auth is point-in-time: you log in at 9 AM and are trusted until 5 PM. Zero trust re-evaluates continuously:

1. **Per-request** — every HTTP request to a PEP-protected resource re-triggers policy. The PEP caches the verdict for a few seconds to a minute; beyond that, it queries the PE again.
2. **On signal change** — if the EDR detects anomalous behavior on the user's device (e.g., a beaconing pattern), the device posture flips to "untrusted" and the PE revokes the session.
3. **On risk event** — if the identity provider detects impossible travel (login from Mumbai at 9:00 and São Paulo at 9:05), the session is revoked.

This requires short-lived tokens (e.g., 1-minute access tokens issued by the PEP after each PE check) rather than long-lived VPN sessions. Refresh tokens rotate per request via token exchange (RFC 8693).

## Identity-Aware Proxy (IAP)

The PEP is most commonly deployed as a reverse proxy in front of an application — Google IAP, Cloudflare Access, AWS Verified Access, and Azure Application Proxy all implement this pattern.

```text
User (browser)              IAP (PEP)            Backend app
   |                          |                       |
   | GET /admin               |                       |
   |------------------------->|                       |
   |                          |                       |
   | 302 to IdP (SAML/OIDC)   |                       |
   |<-------------------------|                       |
   |                          |                       |
   | POST credentials         |                       |
   +--------> IdP             |                       |
   |<--------+ ID token       |                       |
   |                          |                       |
   | GET /admin + Bearer      |                       |
   |------------------------->|                       |
   |                          |                       |
   |                   verify token with IdP         |
   |                   query device posture          |
   |                   evaluate policy: alice on      |
   |                     managed device, allow /admin |
   |                          |                       |
   |                          |  GET /admin           |
   |                          |  X-Webauth-User: alice|
   |                          |  + mTLS to backend     |
   |                          |---------------------->|
   |                          |                       |
   |                          |    200 OK             |
   |                          |<----------------------|
   |    200 OK                |                       |
   |<-------------------------|                       |
```

The backend app sees the request as coming from the PEP, with a header like `X-Webauth-User: alice@example.com` set by the PEP. The app trusts the PEP (because the PEP is the only network path to the app — the firewall allows only the PEP's IP). The app does NOT trust the network itself; even an internal service that can route to the app's IP cannot get in, because the app requires the PEP-set header that only the PEP can produce.

This pattern — short-lived tokens issued by an IdP, verified by a PEP, with a single allowed network path — is the backbone of every commercial ZTNA offering.

## Microsegmentation

ZTNA applies the zero-trust principle at the network layer too: every workload can only talk to the specific workloads it needs, on the specific ports it needs, and the policy is enforced by a sidecar or host firewall rather than by a perimeter firewall.

In a Kubernetes cluster with a service mesh (Istio, Linkerd, Cilium), mTLS is enforced per-service-pair with policies like:

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payments-to-checkout
  namespace: checkout
spec:
  selector:
    matchLabels:
      app: checkout
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/payments/sa/payments-sa"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/checkout/*"]
```

This policy says: only the `payments` service account in the `payments` namespace can call `/api/checkout/*`, and only via GET/POST. Every other source — including other namespaces, even within the cluster — is denied by default. The enforcement is in the Envoy sidecar (the PEP), based on the SPIFFE ID (the workload identity).

The key insight is that the **default** is deny. There is no "inside the cluster is trusted" — a compromised pod cannot reach the checkout service unless a policy explicitly allows it.

## Comparison to Traditional VPN

| Property | Traditional VPN | ZTNA |
|---|---|---|
| Access granularity | Network-level (any IP routed) | Per-application (per-request) |
| Trust lifetime | Hours (the VPN session) | Minutes (per-request tokens) |
| Device check | None (or at connect time) | Continuous |
| Auth model | "On the network" | "Authorized for this resource" |
| Lateral movement | Trivial (any reachable IP) | Blocked by default-deny |
| Client | L3 VPN client (heavy) | Browser / lightweight agent |
| Perimeter | VPN concentrator | PEP in front of each app |
| Operational cost | One gateway to maintain | One PEP per app + central PE |

A common transitional pattern is "ZTNA for new apps, VPN for legacy." As legacy apps are refactored to sit behind a PEP, the VPN's role shrinks until it can be retired.

## SASE Convergence

Secure Access Service Edge (SASE), coined by Gartner in 2019, packages ZTNA with other network security functions (SWG, CASB, FWaaS, SD-WAN) into a single cloud-delivered service. The convergence is real for two reasons:

1. **All these functions are policy decisions on traffic.** A SWG (secure web gateway) is a PEP for HTTP egress; CASB is a PEP for SaaS apps; FWaaS is a PEP for arbitrary TCP. If they all share a PE and a device-posture feed, they can be one service.
2. **Latency.** A remote user's traffic should not hairpin through a corporate datacenter. SASE moves the PEP to the nearest edge POP (Cloudflare has 300+ cities; Zscaler has 100+; Cato has 80+), reducing RTT to the protected resource.

The downside of SASE is vendor lock-in: the PE's policy language is proprietary per SASE vendor, and migrating between vendors requires re-expressing the policy. The most common workaround is to express policy in a vendor-neutral language (e.g., OPA/Rego, Cedar) and compile it to each SASE's dialect.

## Operational Realities

1. **Device posture is the hard part.** Collecting signal is easy; the trust algorithm (which signals matter, for which resources) is months of tuning. Many deployments default to "managed device = trusted" and skip behavioral signals, which is closer to "VPN + extra steps" than true ZTA.

2. **The PEP must be the only path.** If a backend app also accepts direct connections from "trusted" internal IPs (e.g., a developer's jump host), the model breaks. The network must be reconfigured: backends live in private subnets with no inbound internet routing AND no inbound corporate-LAN routing — only PEP routing.

3. **Break-glass access.** If the PE is down, no one can access anything. A break-glass account (e.g., an emergency SSH key kept offline in a sealed envelope) is mandatory for production ZTNA.

4. **Performance.** Every request goes through a PEP, which adds latency. Cloudflare Access adds ~20-50 ms per request when the PEP is far from the backend. Mitigation: deploy PEPs as close to backends as possible, and use short-lived token caching aggressively (1-minute tokens, validated and cached at the PEP).

5. **Audit and observability.** Every access decision is logged by the PE with subject + device + resource + verdict. This is the audit trail required by most compliance frameworks (SOC 2, ISO 27001) and is a side benefit of ZTNA over VPN — VPN logs only show "user X connected at 9 AM" with no record of what they accessed.

## Common Pitfalls

1. **Treating ZTNA as a VPN replacement without changing policy.** If the new ZTNA policy is "all managed devices can access all apps," the lateral-movement risk of VPN is preserved. ZTNA requires least-privilege policies, or it is just an expensive VPN.

2. **Trusting the device agent.** A compromised device can lie about its posture. Defense in depth: cross-check the device's self-reported posture with MDM server data and EDR telemetry (which the agent cannot tamper with, since they come from server-side APIs).

3. **Ignoring service-to-service traffic.** A ZTNA that protects only human-to-app access leaves the service-to-service traffic on the internal network unauthenticated. Pair ZTNA with mTLS / SPIFFE for service identity.

4. **Long-lived access tokens.** If the PEP issues 8-hour tokens, the continuous-verification promise is broken. Tokens should be short (5-15 minutes) and rotated via the OAuth refresh-token exchange.

5. **Confusing identity with authorization.** A user authenticated by the IdP is not necessarily authorized for every resource. The PE must enforce authorization decisions — identity is one input, not the verdict.

## References

- [NIST SP 800-207: Zero Trust Architecture (Rose et al., 2020)](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-207.pdf)
- [Google BeyondCorp: A New Approach to Enterprise Security (Ward & Beyer, 2014)](https://research.google/pubs/pub43223/)
- [BeyondCorp II: Design to Deployment (Ward et al., 2016)](https://research.google/pubs/pub45728/)
- [BeyondCorp III: The Access Proxy (Pescatore & Beyer, 2017)](https://research.google/pubs/pub46344/)
- [Cloudflare Access documentation (ZTNA implementation)](https://developers.cloudflare.com/cloudflare-one/)
- [Google Identity-Aware Proxy (IAP) concepts](https://cloud.google.com/iap/docs/concepts-overview)
- [CISA Zero Trust Maturity Model](https://www.cisa.gov/zero-trust)
- [SPIFFE: workload identity for service-to-service ZTA](https://github.com/spiffe/spiffe)
- [RFC 8693: OAuth 2.0 Token Exchange (short-lived access tokens)](https://datatracker.ietf.org/doc/html/rfc8693)
- [Istio AuthorizationPolicy reference](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
