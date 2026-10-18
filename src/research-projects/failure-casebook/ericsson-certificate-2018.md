# Ericsson, December 6, 2018: An Expired Certificate in Core-Network Software That Took Mobile Data Offline Across 11 Countries

## Overview

On December 6, 2018, mobile data services failed nationwide at major carriers on two continents. In the United Kingdom, O2 — the country's second-largest mobile network — lost 3G and 4G data services through the working day and into the night, with full restoration expected only by the following morning per its own statements. In Japan, SoftBank's mobile data, fixed-line, and Air services were down from **1:39 p.m. to 6:04 p.m. JST** nationwide. The common denominator was identified by the equipment vendor itself within a day: Ericsson stated that "an initial root cause analysis indicates that the main issue was **an expired certificate in the software versions installed with these customers**," affecting core-network nodes running two specific software versions of the **SGSN-MME** — the Mobility Management Entity that authenticates and attaches subscribers to the packet-switched data network [1][2].

SoftBank's own incident statement supplies the scale and the mechanism in one paragraph: Ericsson packet switches at its Tokyo and Osaka centers malfunctioned "covering our mobile customers nationwide," Ericsson reported that the software "has been in operation since nine months ago," the "same software" failure "occurred simultaneously in other telecom carriers across **11 countries**," and SoftBank recovered by "adapting the older version of the software to all packet switching machines" [1]. The case is the purest example in this casebook of a failure whose trigger was scheduled months in advance: no deployment, no operator action, and no traffic pattern caused the outage — a timestamp inside the software simply passed.

## System Context

The SGSN-MME is the control-plane heart of a mobile carrier's packet core. Every phone attaching to 3G or 4G data service negotiates with the MME: identity verification, authentication vector exchange, session and bearer establishment, mobility handling as the device moves between cells. The node is therefore on the critical path of every data session a subscriber initiates, and it is deployed as redundant pools of physical or virtual nodes — SoftBank ran Ericsson packet switches at two central sites, Tokyo and Osaka [1]. When MME capacity or availability collapses, devices can often still camp on the radio network and place voice calls through legacy paths, but data sessions fail to establish — which is exactly the service signature O2 reported: voice and SMS largely functioning, data network down [1].

Mobile operators increasingly buy the packet core as vendor-operated infrastructure: Ericsson supplies the nodes, the software, and in many deals the day-to-day management of them. This means two things that shape this incident. First, the operator's visibility into the software internals — including which certificates the software carries and when they expire — is limited to what the vendor surfaces; O2 publicly characterized the event as "a global software issue" in its supplier's network [1]. Second, the fleet is a monoculture: carriers around the world run the same vendor's software versions, so a defect or an embedded timer in those versions detonates simultaneously everywhere it is installed. Ericsson's CEO Börje Ekholm acknowledged both halves in his public statement: "The faulty software that has caused these issues is being decommissioned, and we apologise not only to our customers but also to their customers" [1].

## What Happened

| Time (Dec 6, 2018) | Event | Source |
|---|---|---|
| ~9 months earlier | The affected Ericsson SGSN-MME software versions entered operation at customer networks (per Ericsson's report to SoftBank) | [1] |
| From early morning (UK time) | O2 data services degrade; O2 publicly attributes the outage to "a global software issue" | [1] |
| 1:39 p.m. JST | SoftBank Network Center detects malfunction in all Ericsson packet switches at Tokyo and Osaka centers; nationwide impact | [1] |
| Dec 6, during the day | Carriers in 11 countries experience simultaneous failures of the same software | [1] |
| 6:04 p.m. JST | SoftBank service restored after rolling all packet switches back to the older software version | [1] |
| Dec 6, evening (UK time) | O2 3G data returning; full restoration expected by 9:30 p.m. GMT, with 4G restored overnight; CEO Mark Evans: "full service will be restored for customers by the morning" | [1] |
| Dec 6–7 | Ericsson issues statements: expired certificate identified as the main issue; faulty software being decommissioned; comprehensive root cause analysis in progress | [1][2] |

CONFIRMED (per the quoted statements [1]): the timestamps, the 11-country simultaneity, the nine-month software age, the SGSN-MME software-version identification, the certificate root cause, and both carriers' recovery narratives. INTERPRETATION: contemporary press reporting also attributed disruptions to **Swisscom** in Switzerland and placed O2's subscriber base at roughly 32 million — both widely repeated at the time but not verified against a primary statement in this writing pass, and marked accordingly.

## Technical Mechanism

A certificate is a lease on trust with a machine-checked expiry. In a mobile packet core, nodes authenticate each other and validate security associations using X.509 certificates; a node software that must present or validate a certificate will, at some operation, compare the current time against the certificate's validity window and refuse or fail when `notAfter` has passed. Ericsson's statement identifies the failure precisely at this layer: an expired certificate "at" the software versions installed at affected customers [1][2]. What the public statements do not specify — and what we therefore label interpretation — is the exact embedding: whether the certificate was bundled into the software build, generated at installation with a fixed lifetime, or used for inter-node/IPsec validation. Any of these produces the same operational result.

The failure mode is a **time-synchronized crash loop across a fleet**. Every node running the affected software versions crossed the expiry threshold at the same wall-clock instant, because the certificate's `notAfter` is a single value replicated in every installation. Compare this to the fleet-heterogeneity failures in [Knight Capital, 2012](./knight-capital-2012.md) and [CrowdStrike, July 2024](./crowdstrike-july-2024.md): there, a *configuration* difference made one replica or one content revision fail while siblings survived. Here the opposite invariant failed — perfect uniformity meant the timer fired everywhere at once, with no behavioral diversity to absorb it. Redundancy protects against independent failures; it provides nothing against a correlated one, and an embedded expiry date is the most perfectly correlated failure a fleet can experience.

```text
software built with embedded certificate (valid until T)
deployed across carriers in 11 countries (9 months before T)
        |
        v  wall clock reaches T — no deployment, no operator action
every SGSN-MME on affected versions fails certificate validation
        |
        v
subscriber attach / session establishment fails fleet-wide
        |
        v
nationwide mobile DATA outages; voice/SMS paths partially survive
```

Recovery, as both carriers describe it, was a downgrade: SoftBank "adapt[ed] the older version of the software to all packet switching machines" [1], and Ekholm said the faulty software was "being decommissioned" [1]. The older version worked either because its certificate had not expired or because it lacked the failing validation — the statements do not say. Note the operational asymmetry: the failure required zero action, but recovery required a fleet-wide software operation, executed at carrier scale, on the nodes that authenticate every data session.

### Trigger vs Contributing Factors

**Trigger (CONFIRMED):** the certificate embedded in two Ericsson SGSN-MME software versions reaching its expiry timestamp on December 6, 2018 [1][2].

**Contributing factors (CONFIRMED):** the same software versions deployed across carriers in 11 countries, making the failure simultaneous [1]; the software having been in operation for nine months without the expiry being addressed [1]; the packet core's position as the authentication and session-establishment chokepoint for all mobile data [1]; vendor-operated networks limiting carrier-side insight into the software's internals [1].

**Contributing factors (INTERPRETATION):** the absence of an expiry-aware fleet telemetry — no alarm fired at "this certificate dies in N days" — is inferred from the shape of the event (the first detection was the outage itself at a network operations center), not from any public statement about Ericsson's monitoring. We also read the December 6 timing as the case's sharpest irony — a holiday-season change freeze is irrelevant to a clock set nine months earlier — but that framing is analysis, not sourced fact.

## Why Safeguards Didn't Prevent It

- **Certificate expiry was invisible in the operational tooling.** Expiry is deterministic and known years in advance of `notAfter` — it is the rare failure that can be enumerated precisely. The event shape shows no safeguard acted on that knowledge: the first signal was subscriber-facing outage. Certificates in vendor-shipped software sat outside the operators' own certificate-management programs (which handle their public TLS estate), and evidently outside any vendor-side expiry watchdog as well.
- **Redundancy was oriented at random failures, not correlated ones.** Dual sites (Tokyo and Osaka), redundant nodes, and carrier-grade engineering all protect against independent faults. A shared `notAfter` value makes redundancy irrelevant: both sites failed within the same minute [1]. High availability requires diversity of failure modes, and identical software with an identical embedded timer has one failure mode.
- **The vendor boundary diffused accountability.** O2's public framing — "a global software issue" at its supplier — reflects the managed-service reality: the carrier operates the service, the vendor operates the software [1]. Neither side owned the question "when do the certificates inside the core software expire?" The customers hurt, as Ekholm's apology acknowledged, were the carriers' customers [1].
- **Staging and soak testing could not see it.** The software had run in production for nine months [1] — any test window shorter than that passes. A time-triggered defect defeats conventional verification because the test environment's clock is never the production clock at the failure instant. Only explicit time-manipulation testing (running with accelerated or future clocks) or expiry telemetry catches this class.
- **Rollback existed but was the recovery, not the prevention.** The working older version was available and the rollback executed within hours [1] — genuinely good recovery. But nothing in the incident shape suggests the fleet knew in advance which version to fail back to or that the expiry was imminent; the rollback was diagnosis-driven, not playbook-driven.

## Lessons & Mitigations

1. **Inventory certificates like you inventory services — especially embedded ones.** Fleet certificate hygiene requires a registry of every certificate the system will ever validate, its `notAfter`, and alerts at escalating offsets (90/30/7 days). The public TLS discipline covered in [certificate lifecycle: Let's Encrypt and ACME](../../security/letsencrypt-acme.md) and the automation patterns in [cert-manager](../../cloud/kubernetes/cert-manager.md) apply doubly inside vendor black boxes, where the buyer must demand expiry data contractually.
2. **Treat time as a test dimension.** Any code path that compares a clock against a stored date must be exercised with manipulated time: unit tests with injected clocks, soak tests run with future-dated environments, and canary fleets deliberately time-shifted ahead of the production clock. A nine-month soak is not a mitigation for a defect that fires on day 270.
3. **Design for correlated failure.** Ask of every fleet: what single value, if it flipped, would fail every replica at once? Embedded dates, shared credentials with expiry, license servers, and synchronized configuration TTLs are the usual suspects. Behavioral diversity — staggered expiry, per-node jitter on timers, heterogeneous versions — converts a simultaneous detonation into a rolling, visible one.
4. **Vendor dependency is an architectural fact with operational consequences.** When a supplier operates your critical path, demand the same observability you would run yourself: expiry dashboards, health APIs, and incident-notification SLAs. The general discipline is [supply chain security](../../security/supply-chain-security.md); the carrier case adds a contractual angle — the apology after the fact is not a substitute for expiry visibility before it.
5. **Keep rehearsed, version-pinned rollback paths.** The recovery that worked was "go back to the previous version, everywhere." That succeeds only if the previous version is known-good, deployable at fleet scale, and exercised. Roll-forward-only cultures should note that the fix here was a downgrade [1].
6. **Separate the auth chokepoint from the data path where feasible.** Long-lived sessions, graceful degradation of established bearers, and cached authentication state blunt the blast radius of a control-plane outage. The packet core's design concentrates attach-time trust in one component; application architectures that depend on such components should assume their occasional unavailability.

## Interview Questions

1. Your platform embeds TLS certificates in binaries shipped to thousands of customer clusters. Design the lifecycle: how are they generated, rotated, inventoried, and expired — and how do you alert on an expiry that is 200 days away in a fleet you cannot log into?
2. Explain to an interviewer why N+1 redundancy did not help SoftBank, and give three concrete engineering changes that would have converted this simultaneous failure into a staggered one.
3. How would you test a system whose defect triggers only when the wall clock passes a stored date nine months after install? Describe the testing apparatus, from injected clocks to production canaries shifted in time.
4. You operate infrastructure managed by a vendor. What contract terms, APIs, and dashboards do you require so that "the vendor's software" does not become "the vendor's outage"? Relate to the O2–Ericsson boundary in this case.
5. A change freeze is in effect for the holiday season. What failure classes — like this one — are unaffected by freezes, and what monitoring would you insist on running during a freeze anyway?

## Key Takeaways

- Nationwide mobile data outages in at least 11 countries, simultaneously, from a certificate expiry embedded in two SGSN-MME software versions [1] — a failure scheduled nine months earlier and detonated by wall-clock time.
- Redundancy is defeated by correlation: identical software with an identical `notAfter` fails everywhere at once, and no amount of node-level HA helps. Availability against correlated failure requires diversity, not duplication.
- The warning was computable — expiry is known years ahead — but no safeguard consumed it. Certificates inside vendor software need contractual expiry visibility, not hope, and time-based defects need clocks as a test dimension.
- Recovery was a fleet-wide downgrade [1]. A rehearsed rollback to a known-good previous version is a production safety net, not an admission of failure — and it is the only recovery that works when the current version is the bug.
- Vendor-managed infrastructure does not outsource accountability, only visibility. If the supplier operates the nodes, expiry dashboards, health APIs, and incident-notification terms must be bought explicitly — O2 learned of its core network's state through its subscribers, not through a dashboard.

## Sources

1. Corinne Reichert, "Ericsson: Expired certificate caused O2 and SoftBank outages," ZDNet, December 6, 2018. https://www.zdnet.com/article/ericsson-expired-certificate-caused-o2-and-softbank-outages/ (fetched and quoted; contains verbatim statements from Ericsson, Ericsson CEO Börje Ekholm, O2/Telefónica UK including CEO Mark Evans, and SoftBank's incident statement, including the 11-country and nine-month software details)
2. Ericsson, press statements of December 6–7, 2018 on the software malfunction affecting customer networks. Cited by org+date; ericsson.com pages return 403 to automated fetch, so no URL is cited; statement text used here as quoted verbatim by [1].
3. SoftBank Corp., incident statement of December 6, 2018 (packet-switch malfunction detection at 1:39 p.m. JST, restoration by 6:04 p.m. JST via rollback). Cited by org+date; text used as quoted verbatim by [1].
4. O2 (Telefónica UK), customer statements and CEO statement of December 6, 2018 (3G restoration timeline, overnight 4G restoration). Cited by org+date; text used as quoted verbatim by [1].

Quotation policy for this page: every Ericsson, SoftBank, and O2 statement quoted here was taken from the ZDNet article's verbatim transcription, which was fetched in full during writing; ericsson.com itself was not machine-accessible, so no URL for the vendor's own press pages is asserted. Statements are attributed to their original speakers with ZDNet as the verified publication channel.

## Cross-References

- [CrowdStrike, July 2024](./crowdstrike-july-2024.md) — a vendor's security-relevant content update simultaneously crashing customer fleets; the update-channel sibling of the expiry-channel failure.
- [Knight Capital, 2012](./knight-capital-2012.md) — fleet homogeneity and heterogeneity as failure determinants: Knight died from one divergent replica, Ericsson from perfectly synchronized ones.
- [Fastly, June 2021](./fastly-june-2021.md) — a latent condition in vendor-managed edge infrastructure triggered globally by a routine customer action.
- [AWS S3 us-east-1, 2017](./aws-s3-us-east-1-2017.md) — a single low-level parameter with a global blast radius; authorization chokepoints and their failure economics.
- [Certificate lifecycle: Let's Encrypt and ACME](../../security/letsencrypt-acme.md) — expiry management, renewal automation, and the monitoring that should have caught this nine months out.
- [Supply chain security](../../security/supply-chain-security.md) — vendor-operated infrastructure, contractual observability, and the trust boundary between carrier and supplier.
- [Cert-manager](../../cloud/kubernetes/cert-manager.md) — automated certificate issuance and rotation patterns applicable far beyond Kubernetes.

Together these targets cover the three layers of the incident: the certificate mechanics (lifecycle and automation pages), the vendor-trust boundary (supply chain security and the CrowdStrike case), and the fleet-correlation geometry that made the failure simultaneous (Knight Capital, Fastly, and the S3 case's chokepoint economics).
