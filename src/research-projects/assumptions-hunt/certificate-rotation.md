# Certificate Rotation Assumptions: What "Automated Renewal" Silently Promises

## Overview

TLS certificate expiry is one of the few failure modes with a date printed on it, and the industry's answer — ACME automation (RFC 8555) plus renewal daemons — has made "certs renew themselves" the default belief. That belief stacks four silent promises: that a renewal job running means certificates are being renewed, that a renewed certificate on disk equals renewed trust in every client, that revocation gives you an incident-time kill switch, and that expiry alerts are configured everywhere a certificate exists. Each promise fails distinctly: renewal without service reload serves stale material from memory, trust lives in client-side stores no renewal job touches, revocation checks fail open under exactly the outage conditions that make revocation necessary, and alerting covers the certificates someone remembered to scan.

This chapter audits the family with the collection's five-step pattern. The automation mechanics follow the ACME protocol and Let's Encrypt's documented rate limits; the revocation analysis follows RFC 6960 (OCSP) and RFC 5280's revocation model; the named incidents are cited by title where no stable primary URL was verified. The handshake-level mechanics — what actually happens when a client and server exchange certificates — live in the follow-up tree's TLS chapter; here the subject is the operational lifecycle around those handshakes: issuance, deployment, trust distribution, and the day something needs to die. The unifying lesson is that a certificate is not one thing but three: a file, a key pair, and a position in other people's trust stores — and rotation automation typically handles only the first.

## Assumption 1: "Certs Renew Themselves"

### The taught rule

Certbot (or the platform equivalent) holds a renewal timer; ACME renews every certificate 30 days before expiry; nobody needs to think about it again.

### How it fails

"Renewal runs" and "renewal succeeds" and "renewal deploys" are three different events, and automation commonly breaks at each seam in a different way. *The timer:* a cron entry or systemd timer exists on one host per certificate; hosts cloned from images carry duplicate or dead timers; a migrated VM loses the timer but keeps the certificate. *The ACME transaction:* renewal requires the ACME server to reach the challenge endpoint on port 80/443, which breaks silently when a CDN is placed in front of the origin, when firewall rules change, or when DNS moved without updating the ACME account's zone — and Let's Encrypt's documented rate limits (including the duplicate-certificate limit of 5 identical certificates per week, at the URL verified for this chapter) turn repeated failed retry storms into a lockout that outlasts the incident. *The deployment:* the classic gap — the renewal writes a new fullchain.pem on disk, but the web server or proxy holds the old certificate in memory until reloaded; certbot's hooks reload the services it knows about, and the one you added last month (the gRPC sidecar, the internal admin listener) is not in the hook list. The result is the most misleading state in ops: the file on disk is fresh, the socket serves the stale one, and monitoring that reads the file reports green.

### Failure scenario

A platform team migrates from Apache to a containerized ingress. The renewal timer survives; hooks still run `systemctl reload apache2`, which now targets a service that no longer exists (exit code swallowed by `|| true`). For four months the ingress container receives a certificate mounted from a secret that nothing updates, while the renewal job happily renews to disk. At day 60 of the 90-day cert's life, an engineer checking "are certs healthy?" greps the renewal log — full of successful lines — and reports yes. On expiry day, every browser and API client on the internet refuses the endpoint. The corrected pipeline treats renewal as a chain with assertions at each link: file mtime advancing, *served* certificate (scanned live over the wire, not read from disk) matching the newest serial, and hook execution verified rather than assumed.

### Detection heuristic and what to assume instead

Detection: scan every public endpoint's served certificate chain over the network on a schedule (the only source of truth is the wire); alert when the served serial lags the newest issued one — that is the reload gap, and it is invisible to disk-based checks. Corrected statement: *a certificate renews itself only if a chain of verified events holds — timer fires, ACME challenge passes, file lands, every consumer of that file reloads — and each link needs its own check, because the chain is exactly as strong as its weakest silent failure.*

## Assumption 2: "Renewal Implies Redeployment of the Trust"

### The taught rule

When the certificate is renewed, the system's TLS is renewed; clients will trust the new certificate the way they trusted the old one.

### How it fails

A renewed leaf certificate is only useful if the *chain* presented with it is intact and if clients' trust stores accept its issuer. Rotation breaks trust in three documented ways. *Chain rot:* a renewed certificate is issued from a newer intermediate (CAs rotate intermediates; RFC 5280's path-building rules mean clients need the full chain); a server that presents only the leaf — or a stale intermediate bundle from a static Docker image — fails on clients that lack the intermediate cached, while succeeding on clients that do. This is the classic "works in curl, fails in the mobile app" split: the desktop's trust store fetched the intermediate long ago. *Pinned trust:* clients that pin a public key or intermediate (common in mobile apps and in mTLS fleets) reject any certificate the CA issues after rotation unless the pin covers the issuer or a backup key was enrolled — a renewal the pinning clients actively punish. *Distributed stores:* the trust store is a per-host, per-image, per-language artifact; a renewed internal CA means updating the CA bundle in base images, JVM cacerts, Python's certifi, Go's system pool, and every appliance — none of which the renewal job touches. In mTLS, the problem doubles: both sides rotate.

### Failure scenario

An internal CA certificate rotates on schedule; the platform renews the server certificates fleet-wide. Three months later, a team redeploys a service from a six-month-old base image whose CA bundle predates the rotation. The service cannot call any internal endpoint: TLS verification fails with "certificate signed by unknown authority" — on exactly one deployment lineage. Because most clients succeeded, the incident reads as "that team's config," and the fix (rebuilding on a current image) lands per-team, discovering one stale lineage per week. What was missing was a trust-deployment contract: the CA bundle is an artifact with a version, fleet-wide rollout is tracked by *distribution* (what fraction of running containers carries bundle ≥ N), and pinning decisions are reviewed against rotation plans before the CA rotates, not after a client fails.

### Detection heuristic and what to assume instead

Detection: continuously scan served chains for completeness (leaf + intermediates to a trusted root) and report chain-health per endpoint, not just expiry dates; inventory pinning clients as first-class dependents of the CA. Corrected statement: *renewal deploys the leaf; trust is redeployed by a separate act — updating chains presented, CA bundles trusted, and pins enrolled — and until that act completes, the fleet is running on a mix of old and new trust whose failures will be partial and therefore confusing.*

## Assumption 3: "Revocation Works at Incident Time"

### The taught rule

If a private key leaks, revoke the certificate; browsers and clients check revocation and refuse the revoked cert, containing the incident.

### How it fails

Revocation is the TLS ecosystem's weakest operational promise, and its failure modes compound during incidents. *Fail-open clients:* most client stacks treat an unreachable or slow revocation responder as "soft fail" — proceed without proof — because hard-failing on a flaky OCSP service would break the web; so the attacker who has the key usually also enjoys clients that cannot confirm revocation. *Responder availability:* OCSP (RFC 6960) requires a live responder at incident time; a traffic spike from every client rechecking the revoked cert is a self-inflicted DDoS on the responder you need most. *Latency and staleness:* CRLs are snapshots with `nextUpdate` windows; clients that cache a CRL for hours act on stale data long after the revocation landed. *Coverage:* many non-browser clients — a large fraction of service-to-service TLS libraries in their default configuration — never check revocation at all. *Ecosystem drift:* Let's Encrypt publicly announced it would end OCSP support in favor of CRLs, which is documented and citable by title — the revocation infrastructure itself rotates under you. The net effect: revocation is best understood as *advisory*, and containment must not depend on it.

### Failure scenario

A build system's private key for its TLS endpoint leaks into a public repository. The team revokes the certificate within 20 minutes — textbook response. Attacker-supplied connections continue for three days because (a) the scraping clients that found the key do not check OCSP at all, (b) internal Java services run with revocation checking disabled by default, and (c) the OCSP responder, hit by the incident-driven spike, times out for the clients that did check — and they soft-fail. The containment that actually worked was cryptographic rotation: the key was replaced, the new certificate deployed, and the old key's material made worthless by infrastructure change (IP allowlisting, mTLS requirement), not by the revocation status bit. The post-incident review's honest line: "revocation was performed; revocation did nothing."

### Detection heuristic and what to assume instead

Detection: test revocation behavior of your own fleet annually — revoke a canary certificate and measure how long each client class stops accepting it; the results will embarrass the default configuration into being fixed. Corrected statement: *revocation is a compliance step, not a control; containment at incident time comes from key rotation, network-level exclusion, and short certificate lifetimes that cap the window any leaked key is useful — treat every revocation-dependent failure mode in your threat model as live until tested otherwise.*

## Assumption 4: "Expiry Alerts Are Configured Everywhere"

### The taught rule

Monitoring watches all certificate expiry dates and alerts at 30/14/7 days; no cert expires unannounced.

### How it fails

The alerting assumption fails on coverage, not on machinery. The scanner is configured against a registry of hosts someone typed in — and certificates exist outside the registry: on appliances, in service meshes with their own workload identities, on internal endpoints never exposed to the scanner, inside Kubernetes secrets created by teams that never joined the inventory, and on the private key side entirely (a key approaching old age has no expiry, so no alert can fire). The 2020 Microsoft Teams outage (documented in Microsoft's own postmortem as EX206867) was caused by a certificate expiry in a downstream authentication dependency — an organization with mature monitoring missed an alert because the certificate belonged to a dependency boundary nobody scanned. Alert routing has its own silent assumptions: the alias `cert-alerts@` that forwards to a distribution list whose members churn, the severity tuned down during a noisy quarter and never restored. And pluralities break: a wildcard renewal covers `*.example.com` but not the apex; a SAN list that once covered all hostnames drifts as services are added.

### Failure scenario

An e-commerce platform's scanner covers 212 public hostnames and alerts reliably. On Black Friday, checkout settlement fails: the *internal* settlement service certificate (hostname `settle.internal`, terminating on a mesh workload, never in the public scanner) expires at 02:10, and the batch settlement jobs fail until 06:00, when the on-call notices the queue. The public scanner had been green all night — because the failing certificate was not in its list. Total loss: one settlement cycle delayed, plus a review that adds 47 internal hostnames to scanning and moves expiry checks into the service mesh's own telemetry, where every workload's certificate is visible by construction.

### Detection heuristic and what to assume instead

Detection: derive the certificate inventory from infrastructure (mesh identities, Kubernetes TLS secrets, load balancer configs) rather than from a hand-maintained list; reconcile the two weekly and treat unregistered certificates as findings. Corrected statement: *expiry alerting is only as complete as the inventory it derives from, and inventories from manual lists are always incomplete — build coverage from the systems that terminate or hold certificates, alert on the served-chain scan (Assumption 1), and include trust-store and pin health in the same telemetry.*

## Interview Questions

1. **Your renewal automation logs show successful renewals for months, yet clients saw an expired certificate. Reconstruct the failure.** Renewal succeeded to disk; deployment to the *serving* process did not (dead reload hook), and monitoring read files instead of scanning served certificates over the wire. Fix: verify the served chain live, assert served serial equals newest issued.
2. **Why can a renewed certificate fail in one client and succeed in another?** Chain presentation and trust state are per-client: one has the intermediate cached, one does not; one pins the issuer, one does not; base images carry different CA bundle versions. Trust redeployment is a distribution problem with a fleet-wide completeness metric.
3. **You revoke a leaked certificate. Why might an attacker keep connecting?** Clients soft-fail on unreachable responders, many non-browser clients skip revocation checks entirely, CRL caches are stale for hours, and incident-time OCSP load degrades the responder. Containment requires key rotation and network controls, with revocation as a compliance step.
4. **What does ACME automation actually cover, and what three things does it not touch?** It covers issuance and renewal transactions (RFC 8555). It does not cover service reloads, client trust-store distribution, or revocation semantics — each needs its own mechanism and check. Let's Encrypt's rate limits additionally punish retry storms after a broken challenge path.
5. **Design expiry monitoring for a fleet where half the certificates are internal.** Derive inventory from terminating infrastructure (mesh, k8s secrets, LB configs), scan served chains over the wire where reachable, read mesh telemetry for workload certs, reconcile weekly, and alert on lag between issued and served serials — not just on dates.

## Key Takeaways

- A certificate is three artifacts — file, key pair, trust position — and renewal automation typically advances only the first; the reload gap between disk and socket is the classic silent failure.
- Trust redeployment (chains, CA bundles, pins) is a separate rollout with its own completeness metric; partial deployment produces partial, confusing failures.
- Revocation fails open under exactly the conditions that make it necessary; containment must come from key rotation, network exclusion, and short lifetimes, with revocation treated as advisory.
- Expiry alerting inherits the blind spots of its inventory; derive coverage from infrastructure, not from typed lists, and scan served certificates, not files.
- Let's Encrypt's documented rate limits (duplicate certificates per week) can lock out a broken pipeline at the worst time — renewal failures deserve alerting as much as expiry does.

## Cross-References

- [TLS handshake](../followup-tree/tls-handshake.md) — what the certificate exchange actually validates, the mechanics this lifecycle wraps.
- [Security and crypto assumptions](security-crypto.md) — the trust-model assumptions (endorsement, unpredictability) that certificate hygiene exists to support.
- [Let's Encrypt and ACME](../../security/letsencrypt-acme.md) — the book chapter on the issuance protocol and its operational envelope.
- [Mutual TLS](../../security/mtls.md) — the both-sides-rotate case, where trust redeployment doubles.
- [RFC 8555](https://www.rfc-editor.org/rfc/rfc8555.html) — the ACME protocol; [RFC 6960](https://www.rfc-editor.org/rfc/rfc6960.html) — OCSP; [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html) — X.509 path validation and revocation (all verified).
- Let's Encrypt rate limit documentation — [verified](https://letsencrypt.org/docs/rate-limits/); the OCSP-to-CRL transition announcement cited by title. The Microsoft Teams February 2020 postmortem (EX206867) cited by title.
