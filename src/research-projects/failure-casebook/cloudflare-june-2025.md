# Cloudflare, June 12, 2025: A Third-Party Storage Failure Behind Workers KV and 2 Hours 28 Minutes of Cascading Failure

## Overview

On June 12, 2025, Cloudflare suffered a significant service outage lasting **2 hours and 28 minutes** that affected a large set of its critical services: Workers KV, WARP, Access, Gateway, Images, Stream, Workers AI, Turnstile and Challenges, AutoRAG, Zaraz, and parts of the Cloudflare Dashboard. The company's first-party postmortem — authored by Jeremy Hartman and CJ Desai — states the cause plainly: "a failure in the underlying storage infrastructure used by our Workers KV service," part of which was "backed by a third-party cloud provider, which experienced an outage today and directly impacted availability of our KV service" [1]. During the incident window, **90.22 percent of Workers KV requests failed**, and the post confirms the outage was not an attack and that no data was lost [1].

What makes the case exceptional for study is not the trigger but the topology. Workers KV sits underneath dozens of Cloudflare products as their configuration, authentication, and asset-delivery substrate, so a storage-layer failure propagated into identity infrastructure (Access failed **100 percent of identity-based logins**), edge networking (Gateway, WARP), media services (Stream exceeded 90 percent errors), and AI services (Workers AI inference failed entirely for the duration) [1]. The postmortem is explicit about the systemic lesson in its own words: "the cascading impact from the failure from Workers KV exacerbated the issue and significantly broadened the blast radius" [1]. This is the June 2025 sibling of [AWS DynamoDB, 2015](./aws-dynamodb-2015.md): a shared low-level dependency that many higher-level products assumed without designing for its loss.

## System Context

Workers KV is Cloudflare's globally distributed key-value store, used both by external customers and internally by other Cloudflare products to store configuration, identity data, and static assets for Workers and Pages. The postmortem describes its intended architecture with a phrase worth internalizing: Workers KV is built as a **"coreless" service — "there should be no single point of failure as the service runs independently in each of our locations worldwide"** [1]. Read requests are served from caches in each location; only reads that miss the cache, and all writes, must reach what the post calls KV's **"central data store to provide a source of truth for data"** [1]. The availability contract of the whole system therefore reduces, at the edges, to the cache hit ratio: a value already cached is served locally; a cold read requires the central store.

That central store was in transition at the time of the incident. The post states that Workers KV "is in the process of being transitioned to significantly more resilient infrastructure," and that during a re-architecture — migrating the backend toward Cloudflare R2 to fix data-consistency issues in the original syncing design and to support data residency — **"Workers KV removed a storage provider"** [1]. The post then names the consequence with unusual candor: "regrettably, we had a gap in coverage which was exposed during this incident" [1]. Cloudflare's stated design philosophy — build services on its own platform building blocks — is also why the dependency graph is so dense: "many of our internal and external services rely heavily on Workers KV," which under normal conditions centralizes storage engineering and, as this day showed, centralizes its failure [1].

## What Happened

| Time (UTC, Jun 12, 2025) | Event | Source |
|---|---|---|
| 17:52 | Incident start: WARP team sees new device registrations fail, investigates, declares an incident | [1] |
| 18:05 | Access team alerted on rapid error-rate increase; SLOs drop below targets across multiple services | [1] |
| 18:06 | Service-specific incidents merged into one; shared cause identified as Workers KV unavailability; priority P1 | [1] |
| 18:21 | Upgraded to P0 as severity becomes clear | [1] |
| 18:43 | Access begins exploring removal of its Workers KV dependency via migration to a different backing datastore | [1] |
| 19:09 | Gateway begins graceful degradation of rules referencing identity or device posture | [1] |
| 19:32 | Access and Device Posture force-drop identity and posture requests to shed load on KV until the third-party service recovers | [1] |
| 20:23 | Services begin recovering as the storage infrastructure recovers; residual errors and rate limits as caches repopulate | [1] |
| 20:25 | Access and Device Posture restore KV calls; third-party service restored | [1] |
| 20:28 | Impact end and incident end: SLOs return to pre-incident levels | [1] |

CONFIRMED (per the postmortem [1]): the trigger was the failure of underlying KV storage infrastructure, part of it backed by a third-party cloud provider; 91 percent of requests to KV failed during the window; Access's successful-request curve is presented by Cloudflare as a proxy for KV availability over time. Impact specifics confirmed in the post: Access failed 100 percent of identity-based logins (service-token, mTLS, and IP-based authentication unaffected); Gateway proxy/egress/TLS decryption could not connect, register, or log traffic; WARP could not register new clients and its emergency disconnect override was unavailable because of its KV dependency; Stream exceeded 90 percent errors with Live at 100 percent; Workers AI failed 100 percent of inference requests; Pages error rate peaked near 100 percent and builds could not complete; SQLite-backed Durable Objects and D1 — sharing the same storage infrastructure — peaked at 22 percent errors; Workers Builds failed 100 percent of new builds from 18:03 because Access was down. Cloudflare states DNS, Cache, the proxy, WAF, and Magic Transit/WAN were not directly impacted, that no data was lost, and that the v4 API stayed up [1].

## Technical Mechanism

The incident is three mechanisms stacked: a dependency concentration, a cache/origin availability split, and a recovery amplification.

**1. One logical source of truth behind a "coreless" facade.** The architecture distributes serving but not durability: every location's cache ultimately validates against the central store, and every write lands there [1]. When that store failed, "cold reads and writes to the KV namespaces used by services across Cloudflare" failed completely [1]. The 90.22 percent failure figure is the arithmetic of this split — the surviving 9.78 percent is, to first order, the fraction of requests answered from cache (200s and 404s alike) [1]. A service can be coreless in deployment and still have a single point of failure in its data path; the SPOF moved from the compute tier to the storage tier, where nobody thought to look for it.

**2. Fan-out through the internal dependency graph.** KV is the substrate for other products' *configuration and identity*, which is why the failure escaped its own service boundary. Access reads application and policy configuration plus user identity from KV — and **Access is designed to fail closed**: "when it cannot successfully fetch policy configuration or a user's identity," it denies [1]. Gateway made the same fail-closed choice for proxy, egress, and TLS decryption [1]. Fail-closed security converts a storage outage into an authentication outage by design: WARP registrations stopped, Gateway registrations and policy evaluation stopped, and because Workers Builds authenticate through Access, 100 percent of new builds failed from 18:03 [1]. The post's own summary — the cascade "significantly broadened the blast radius" — is the dependency graph talking [1].

**3. Recovery amplification.** When the storage layer returned at 20:23, the system did not snap back: Cloudflare reports "a non-negligible error rate and infrastructure rate limits due to the influx of services repopulating caches" [1]. Every edge location that had been failing cold reads now retried them at once — the classic thundering-herd transition from outage to recovery. This is why the remediation list includes tooling to "progressively re-enable namespaces during storage infrastructure incidents," so that critical dependencies "come up without risking a denial-of-service against our own infrastructure as caches are repopulated" [1]. The same recovery-overload signature drives the [AWS us-east-1, 2021](./aws-us-east-1-2021.md) case.

### Trigger vs Contributing Factors

**Trigger (CONFIRMED):** an outage at a third-party cloud provider backing part of the central storage infrastructure used by Workers KV [1].

**Contributing factors (CONFIRMED):** KV's central source-of-truth store as a common dependency; the removal of a storage provider during the re-architecture, leaving what the post calls "a gap in coverage" [1]; the breadth of Cloudflare products depending on KV for configuration, authentication, and assets [1]; fail-closed designs in Access and Gateway that propagate storage unavailability into the identity plane [1]; cache repopulation pressure at recovery [1].

**Contributing factors (INTERPRETATION):** the post does not name the third-party provider, quantify its share of the backend, or state whether remaining providers' internal redundancy was exhausted before the failure was declared — we make no claim on those points. Our reading that "coreless" described the deployment topology while the data path retained a logical SPOF is analysis of the post's own description, not a quote.

## Why Safeguards Didn't Prevent It

- **Architectural intent was not architectural fact.** "There should be no single point of failure" [1] described the serving tier, not the durability tier. The safeguard most relied upon — geographic distribution — was irrelevant to the failure that occurred, because the shared component was behind the caches, not inside them. Safeguards fail when they protect the tier that was already replicated.
- **The migration removed a provider before the destination covered the gap.** The post's own framing — re-architecting toward R2, removing a provider, "a gap in coverage" [1] — is a transition-management failure: the system passed through a state less resilient than either endpoint. Cutovers need overlap, not handoffs, especially when the thing being replaced is the write path.
- **Detection worked; prevention had nothing to detect with.** SLO alerts fired within 13 minutes of the first symptom [1], incidents merged quickly, and severity escalated correctly to P0. But no amount of detection prevents a provider outage; the only prevention was redundancy in the store itself, which was the thing being rebuilt.
- **Load shedding was improvised, not pre-designed.** Gateway's graceful degradation at 19:09 and the force-drop of identity/posture traffic at 19:32 [1] were the right moves and protected KV from a crush of retries — but they were engineered mid-incident by the affected teams. The postmortem's remediation list effectively promotes these to permanent mechanisms.
- **Kill switches had their own failure mode.** The Challenge platform's kill switches disabled siteverify calls to keep eyeballs moving — and while active, the API "could redeem valid tokens multiple times, potentially allowing for attacks where a bad actor might try to use a previously valid token to bypass" [1]. Every emergency lever trades one risk for another; the trade was disclosed, but it was not pre-communicated.
- **Durability held; availability did not.** "No data was lost" [1] — the durability engineering (the thing the R2 migration targeted) was never the problem. The incident is a reminder that the resilience properties you invested in least recently are not necessarily the ones the next outage tests.

## Lessons & Mitigations

1. **Map dependencies through your own products, not just your vendors.** Cloudflare's blast radius was large because Cloudflare products consume KV. Any internal platform service is a shared fate; product teams that treat platform storage as "someone else's SLA" inherit its worst hour. The [common failure catalog](../../failure-modes/common-failures.md) files this under cascading failure; the 2015 DynamoDB case is its canonical AWS form.
2. **A central source of truth is a real SPOF regardless of what the architecture diagram says.** If cold reads and writes must traverse one logical store, that store's availability is the system's. Redundancy work belongs there first, and cutover plans must overlap providers — never remove the old backing store until the new one demonstrably survives the failure of any single component.
3. **Decide fail-closed versus fail-open per dependency, and pre-build degradation.** Access and Gateway's fail-closed posture is correct for a security product — and it must come with pre-built degraded modes (serve stale policy, cache identity with bounded TTL, queue registrations) so the identity plane does not go fully dark with the storage. Gateway's mid-incident graceful degradation [1] should be the designed default, not the improvisation.
4. **Engineer the recovery as carefully as the outage.** Cache repopulation is a retry storm in festive clothing. Progressive namespace re-enablement, warm-up rate limits, and priority ordering (auth paths first) turn recovery from a second incident into a schedule. Bulkheads ([SRE: bulkheads](../../sre/bulkheads.md)) and the shedding patterns here apply to the ramp as much as to the plateau.
5. **Own your dependencies out loud.** The post's accountability statement — "the proximate cause (or trigger) for this outage was a third-party vendor failure, we are ultimately responsible for our chosen dependencies and how we choose to architect around them" [1] — is the correct stance. In design reviews, "the vendor failed" must be an in-scope answer, because to your customers it is indistinguishable from your failure.
6. **Pre-review emergency levers.** Kill switches that disable verification paths create bounded security windows (here, token reuse). Document what each lever trades away, decide who may pull it, and pre-brief the risk acceptance — the decision is better made in daylight than at 18:21 UTC during a P0.

## Interview Questions

1. Your globally distributed KV store serves 99 percent of reads from cache, with a central store for cold reads and writes. Walk through what happens when the central store fails, and design the recovery sequence — which namespaces re-enable first, at what rate, and why?
2. A security service is designed to fail closed on a configuration-fetch dependency. Propose three degraded modes that preserve the security guarantee while keeping the identity plane partially available, and state the risk each mode accepts.
3. During a storage-provider migration, when is it safe to decommission the old backend? Give the checklist you would demand before the removal of any provider from a write path.
4. Your CDN's traffic management rerouted traffic during an upstream failure, but "a portion of traffic was not rerouted as expected" [1]. Design the verification loop that catches rerouting partial-failure within minutes.
5. Cloudflare activated kill switches that allowed previously valid challenge tokens to be redeemed multiple times. How would you structure the pre-authorization for emergency mode trade-offs so the decision is fast, documented, and revisited after the incident?

## Key Takeaways

- 2 hours 28 minutes, 90.22 percent of Workers KV requests failing, 100 percent of Access identity logins failing, no data lost [1] — availability failed everywhere except the cache, durability held everywhere.
- The "coreless" service had a logical SPOF in its central source of truth, and the provider removal during re-architecture left a "gap in coverage" that the incident exposed [1].
- Fail-closed security plus a dead dependency equals a self-inflicted authentication outage; degradation paths must be designed in advance, as Gateway's mid-incident adaptation demonstrated [1].
- Kill switches are risk trades, not free wins: the Turnstile lever bounded availability while opening a token-reuse window that had to be disclosed [1].
- Recovery is part of the outage: cache repopulation caused rate limits and residual errors until progressive re-enablement exists [1]. The same lesson as DynamoDB 2015 and us-east-1 2021, in Cloudflare's own words: "we are ultimately responsible for our chosen dependencies" [1].

## Sources

1. Jeremy Hartman and CJ Desai, "Cloudflare service outage June 12, 2025," Cloudflare Blog, June 12, 2025. https://blog.cloudflare.com/cloudflare-service-outage-june-12-2025 (fetched and quoted in full; all figures, timeline timestamps, service-impact percentages, and quotations in this page are from this post)

This page is deliberately single-source. Cloudflare's postmortem is the first-party account, published the day of the incident and updated on the same page; every number, timestamp, service impact, and mitigation listed above traces to it. Where the post is silent — the identity of the third-party provider, its share of the backend, per-customer impacts — this page is silent too, rather than filling the gaps from secondary accounts. Readers who need the provider's identity or external impact measurements should treat any figure from press coverage as unverified against this page's sourcing standard, exactly as the ledger for this casebook records. No secondary source is cited here because none was needed to substantiate any claim made on the page.

## Cross-References

- [AWS DynamoDB, 2015](./aws-dynamodb-2015.md) — a shared low-level metadata dependency whose outage cascaded into other AWS services; the closest structural sibling to this incident.
- [AWS us-east-1, 2021](./aws-us-east-1-2021.md) — recovery overload and retry amplification prolonging an incident after the root trigger cleared.
- [Cloudflare, November 2025](./cloudflare-november-2025.md) — the same company's control-plane outage five months later; a permissions change corrupting a security feature file rather than a storage dependency.
- [Fastly, June 2021](./fastly-june-2021.md) — one latent trigger propagating globally through shared edge infrastructure.
- [Key-value stores](../../dbms/nosql/key-value.md) — the data-model and consistency trade-offs behind caches backed by a central source of truth.
- [Bulkheads](../../sre/bulkheads.md) — partitioning and load-shedding patterns for the dependency fan-out and the recovery ramp.
- [Cell architecture](../../sre/cell-architecture.md) — containing blast radius by construction when a shared substrate fails.

The four sibling cases bracket this incident: DynamoDB 2015 and us-east-1 2021 supply the dependency-cascade and recovery-amplification mechanics, while the November 2025 and Fastly June 2021 cases show the same company and the same industry failing through entirely different layers — evidence that the failure surface is a property of the architecture, not of one component.
