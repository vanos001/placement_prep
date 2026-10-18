# DNS Assumptions: What "Just Change the TTL" Silently Promises

## Overview

DNS is the internet's oldest indirection layer, and its operational model is widely understood in one sentence — "records have a TTL, so changes propagate within it" — that compresses several false assumptions into a single clause. This chapter audits the family with the collection's five-step pattern: that a 300-second TTL means 5-minute failover; that DNS changes are quickly reversible; that clients respect TTLs at all; that round-robin DNS load balances; and that NXDOMAIN means the name is gone. Each is true under the textbook resolver behavior of RFC 1035 and false in at least one way that matters during an incident — which is precisely when the assumption was being relied upon.

The stakes are asymmetric. DNS changes are performed calmly, but they are most often *needed* during outages — traffic failover, disaster-region promotion, emergency provider migration — and every caching layer between the authoritative server and the application process gets a vote on how quickly the change takes effect. Teams that have never measured their real failover lag routinely carry minutes-to-hours assumptions that are wrong by an order of magnitude. The mechanisms cited here (TTL semantics per RFC 2181, negative caching per RFC 2308, serving-stale behavior per RFC 8767, Java's process-level resolver cache) are documented protocol and runtime behavior; the book's DNS chapters cover resolution mechanics in depth, and the focus here is the promises the configuration seems to make.

## Assumption 1: "TTL 300 Means 5-Minute Failover"

### The taught rule

Set the record's TTL to 300 seconds, and any change — failover, IP swap, provider migration — is fully visible to all clients within five minutes.

### The hidden assumptions

- A TTL is an *upper bound on caching from the moment of a lookup*, not a deadline from the moment of a change. A recursive resolver that answered a query at t = 0 holds its cached record until t = 300 even if the authoritative answer changed at t = 1; worst case for a client is TTL plus the time since its resolver last refreshed, and resolvers refresh on *demand*, not on schedule.
- The cache hierarchy has more layers than the plan admits: the recursive resolver, the OS stub cache, browser and language-runtime caches, and long-lived connections that never re-resolve. Each adds its own lag, and several ignore the TTL entirely.
- "All clients" is doing enormous work. Some recursive operators clamp or extend TTLs to reduce load; RFC 8767 legitimizes serving stale answers during upstream failures — a resiliency feature that also extends failover lag exactly when the failover is happening.
- Failover speed measured from the *control plane* (the change is committed) is not failover speed measured from the *client*: a client mid-request on a dead IP fails at the TCP layer, retries, re-resolves only after its cached answer expires, and only then sees the new address.

### Counterexample

A region fails and the runbook switches the `api.example.com` A record from region A to region B at t = 0 with a 300-second TTL. Measured recovery: users on freshly-resolving clients converge within minutes; users behind a large recursive resolver that answered at t = 299 wait until t ≈ 599; an enterprise resolver that serves stale during upstream failure stretches the tail further; and a fleet of JVM services with the default `networkaddress.cache.ttl` behavior — "forever" under a security manager — never re-resolve until the *process* restarts. The five-minute number was a promise only to the resolvers that honor the TTL exactly, once. The honest planning number is TTL + longest client-side cache + connection lifetime, measured per client population.

### What changes when the assumption is removed

Corrected statement: *a TTL bounds one cache's holding time from one lookup; end-to-end failover lag is TTL plus every downstream cache that outlives it, and only measurement establishes the tail.* Design for the lag rather than pretending it away: keep TTLs low *before* you need them (lowering TTL at incident time is itself subject to Assumption 2), pair DNS failover with health-checked load balancing that redirects at the connection layer, and treat long-lived connections as the real cache — draining and re-dialing on schedule or on failure beats any TTL setting.

### Consequences

"Lower the TTL before the migration" is half-remembered folklore that this assumption completes: the TTL must be lowered one cache-refresh period *ahead* of the event, because the change to a lower TTL is itself subject to the old TTL. The interview probe "you set TTL 60; why did users still hit the dead region for an hour?" has the layered answer above — and the follow-up "which layer ignored the TTL?" separates operators from readers.

## Assumption 2: "DNS Changes Are Quickly Reversible"

### The taught rule

If a change goes wrong, revert it; since the old values were in place for a long time, everything returns to normal within the TTL.

### The hidden assumptions

- Reverting is a *new* change, subject to exactly the same cache lag as the original — and now the caches hold the *wrong* answer, so the revert's lag is measured from when each cache last fetched the broken record, not from the revert.
- "NXDOMAIN means the name is gone" fails too: negative caching (RFC 2308) caches the *absence* for the negative TTL derived from the SOA record's minimum field. A name deleted by mistake refuses to exist for that window even after being restored — DNS caches errors as readily as answers.
- TTL hygiene decays: records that lived for years at 3600-second TTLs cannot be reverted quickly, because the revert inherits the 3600-second cache from every resolver that read the record before anyone thought to lower it.
- Registry and registrar layers add their own propagation delays at the delegation level — a nameserver-level mistake does not revert on record TTLs at all.

### Counterexample

During a migration, an operator deletes the `www` A record instead of updating it, catches the mistake in two minutes, and re-adds the record. Users keep seeing "server IP address could not be found" for the next hour. Mechanism: resolvers that queried during the window cached NXDOMAIN for the SOA negative TTL — commonly 300 seconds or, on zones with inherited defaults, *hours* — and will not ask again until it expires. Nothing about the re-add invalidates those caches; DNS has no push. The same asymmetry applies to CNAME-flattening layers at CDNs and to enterprise forwarders, each with its own negative-cache policy. The incident class is "the fix landed but users still see the failure," and its signature is that the *error* is cached, not just the data.

### What changes when the assumption is removed

Corrected statement: *reversibility is a property you provision before the incident: sane negative TTLs, low TTLs on records that might change, and client-side fallbacks that do not depend on DNS answers being corrected.* Keep SOA negative TTLs bounded (minutes, not hours) on zones where records change; never delete-then-recreate a record in one maintenance window when an update achieves the same result; and in client software, distinguish "name does not exist" (retry soon; may be negative-cached) from "name exists but is unreachable" (fail over locally) so a cached NXDOMAIN cannot become a hard failure.

### Consequences

The interview probe "you deleted the wrong record and fixed it; why are users still broken?" is this assumption with the negative-caching answer expected by name (RFC 2308, SOA minimum). The deeper lesson generalizes to every caching layer in this collection: you cannot invalidate someone else's cache, so every removal is a deprecation with a window you do not control.

## Assumption 3: "Clients Respect TTLs"

### The taught rule

TTL is a contract: clients cache for at most TTL seconds and re-resolve afterward.

### The hidden assumptions

- TTL semantics are "at most," but only for resolvers that choose to comply — and compliance is opt-in at every layer. RFC 2181 is explicit that the TTL is a recommendation to caches, and RFC 8767 formalizes serving stale data when refresh fails, within a bounded staleness window.
- Application runtimes cache independently of the OS resolver: the JVM's `networkaddress.cache.ttl` defaults to caching forever under a security manager (documented Java behavior), many HTTP client pools resolve once per connection, and browsers keep their own DNS caches with their own policies.
- Long-lived connections outlive any TTL: a gRPC channel, database connection, or keep-alive HTTP session pinned to an IP never re-resolves while healthy. DNS changes only affect *new* connections, so connection recycling is part of the failover mechanism whether or not anyone wrote it down.
- The reverse violation exists too: some stubs re-resolve far more aggressively than the TTL requires (every request), making the authoritative servers part of the request path's failure domain — the opposite failure with the same root: no one pinned the client's caching behavior.

### Counterexample

A platform team lowers TTLs to 60 seconds and declares the failover problem solved. The next regional failure shows three distinct client behaviors: Go services with default resolver settings converge within a minute (the plan works); a fleet of JVM services with `networkaddress.cache.ttl=-1` under the security manager keep dialing the dead region until each process is restarted — the emergency becomes a rolling-restart exercise; and long-lived gRPC channels hold half their traffic on dead IPs until connection pools are drained by hand. The TTL change only governed the layer that was already well-behaved. The platform fix is contractual: standardize resolver settings in base images, cap connection lifetimes, dial behind health-aware balancers, and test failover *per client framework*, because "the clients" are many implementations with many defaults.

### What changes when the assumption is removed

Corrected statement: *client caching behavior is a per-runtime configuration fact, not a zone property — enumerate the clients, pin their caching and connection policies, and verify with measurements.* Set `networkaddress.cache.ttl` explicitly in JVM security properties; use short or zero caching only where the resolver path is robust; route through local load balancers or service-mesh sidecars where health-aware endpoint selection matters more than DNS; and add "re-resolution under failure" to the failover test plan for each runtime in the fleet.

### Consequences

This is the assumption that turns DNS incidents into multi-team incidents: the zone is configured correctly, and the bug is in a client nobody grouped under "DNS." Interviewers probe it as "why doesn't lowering TTL fix Java clients?" — the answer names the JVM's independent cache and the security-manager default. The lesson parallels the timeouts chapter: a guarantee you did not configure at every layer is not a guarantee.

## Assumption 4: "Round-Robin DNS Load Balances"

### The taught rule

Return several A records and let DNS rotate the order; traffic distributes evenly, and removing a dead record's IP handles failures.

### The hidden assumptions

- Rotation distributes *answers*, not traffic: recursive resolvers cache the whole record set and hand their clients whatever ordering policy they implement, so one resolver's client population (an office, an ISP, a mobile carrier) lands on one IP. The unit of distribution is the resolver, not the user, and resolver populations are wildly uneven.
- Nothing checks health: round-robin returns the dead IP with the same confidence as the live one until a human removes it. Client-side happy-eyeballs and retries help, but a blackholed (rather than refused) IP imposes full TCP timeouts on every attempt.
- Weighting is not part of the mechanism: DNS round-robin is an unweighted rotation; capacity differences between backends cannot be expressed in the record set (managed DNS vendors add weighted records on top, which is a different feature).
- The rotation can defeat itself: clients that pick the first record concentrate load whenever answer ordering repeats, and clients that try records in order turn "multiple IPs" into a failover list with failover latency paid per dead record.

### Counterexample

A service publishes four A records via plain round-robin, sizes all four backends identically, and observes that one backend receives several times the traffic of another. The skew source: a national ISP's recursive resolver serves a large subscriber base and, due to caching plus its internal ordering, repeatedly delivers one IP first; a second backend sits behind resolvers with tiny populations. During a backend crash, the dead IP stays in the answer set for the TTL-plus-cleanup window, and clients that honor record ordering pay a full connect timeout before trying the next record. The result is simultaneous under-utilization and overload — the mechanism promised load distribution and delivered resolver-population luck. The corrected designs move decisions closer to traffic: health-checked load balancers (DNS pointing at anycast or VIP addresses of balancers rather than backends), weighted records only where the DNS vendor actually supports them, and client-side balancers for fleets that need locality awareness.

### What changes when the assumption is removed

Corrected statement: *round-robin DNS is an availability primitive at best — it enumerates candidates — and a load-balancing policy only if every client population's resolver behavior happens to cooperate.* Use DNS to reach a balancing layer (anycast VIPs, L4/L7 balancers, service mesh), keep health checking out-of-band and fast, and reserve DNS-level failover (vendor health checks rewriting answers) for coarse, cross-region failover where its lag profile is acceptable.

### Consequences

"Scale by adding A records" fails in both directions — skew at steady state, dead-record penalties at failure — and the interview probe "why is round-robin DNS not load balancing?" expects the resolver-population answer plus the health-check gap. It is also the assumption behind a recurring architecture error: pointing DNS at backend instances instead of balancers, which couples the zone's contents to instance lifetimes and turns every scaling event into a DNS change.

## Interview Questions

1. **You set TTL to 60 seconds. Why did some users still reach the dead datacenter an hour into a failover?** The TTL bounds only one cache layer from one lookup; downstream layers (resolvers extending or serving stale, JVM process caches, long-lived connections) each add lag. End-to-end lag is TTL + longest downstream cache + connection lifetime, and only measurement establishes it.
2. **A deleted record was re-added within two minutes, yet users saw "name not found" for an hour. What cached the failure?** Negative caching (RFC 2308): resolvers cache NXDOMAIN for the SOA-derived negative TTL, and re-adding the record cannot invalidate those caches. Keep negative TTLs bounded and prefer updating over delete-and-recreate.
3. **Which clients do not respect TTLs, and how do you compensate?** JVM default resolver caching (forever under a security manager), connection pools that resolve once per connection, browsers and OS stubs with independent policies — plus resolvers legitimately serving stale per RFC 8767. Compensate by pinning runtime settings, capping connection lifetimes, and using health-aware balancers rather than DNS-only failover.
4. **Why is round-robin DNS not a load balancer?** It rotates answers, not traffic: resolvers cache and serve populations of wildly different sizes, health is unchecked, and weighting is not part of the mechanism. Use it to reach balancers, not as one.
5. **Where does DNS belong in a failover design, and where not?** Coarse, cross-region failover with acceptable lag, using vendor health checks where available; not as the mechanism for per-instance failure, per-request load balancing, or anything needing sub-TTL convergence — those belong to balancers and client-side endpoint selection.

## Key Takeaways

- A TTL bounds one cache's holding time from one lookup; end-to-end change lag is TTL plus every downstream cache, connection, and stale-serving policy, and it must be measured per client population, not inferred from zone settings.
- There is no DNS push: reverting is a new change subject to the same lag, and negative caching means a briefly-absent name can stay absent in caches for the negative-TTL window.
- Client TTL compliance is opt-in at every layer — resolver, OS, runtime, browser, connection pool — so "the clients respect TTLs" is a testable claim about each runtime, not a zone property.
- Round-robin DNS distributes resolver populations, not requests; without health checks it publishes failures, and without weights it cannot express capacity.
- Design DNS for its real role — coarse indirection and cross-region failover — and put health-aware, sub-second decisions in balancers and client-side endpoint selection.

## Cross-References

- [Caching assumptions](caching.md) — TTLs as consistency fiction, the general caching-layer pattern DNS instantiates.
- [Network and distributed assumptions](network-distributed.md) — the reliability and failure-detection assumptions DNS failover leans on.
- [Facebook, October 2021](../failure-casebook/facebook-bgp-2021.md) — authoritative DNS made unreachable by BGP withdrawal; the DNS-as-dependency case study.
- [DNS caching](../../networks/dns/caching.md) and [resolution](../../networks/dns/resolution.md) — resolver mechanics, cache layers, and negative caching in depth.
- [Record types](../../networks/dns/record-types.md) — the record semantics (A, CNAME, SOA fields) the TTL and negative-caching math lives in.
- [Anycast and geo-routing](../../networks/cdn/anycast-and-geo-routing.md) — the balancing layer that replaces round-robin at scale.
- [Load-balancing algorithms](../../networks/load-balancing/algorithms.md) — health checking and weighting DNS cannot provide.
- RFCs 1034/1035 (DNS core), 2181 (TTL semantics), 2308 (negative caching), and 8767 (serving stale data) are cited by number from rfc-editor.org.
