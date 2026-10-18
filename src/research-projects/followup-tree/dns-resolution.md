# Follow-up Tree: DNS Resolution

## Overview

"How does DNS work?" is the first escalation of the [URL to Page](./url-to-page.md) chain, and it deserves its own ladder because DNS is the system most candidates describe as a lookup when it is actually a globally distributed, eventually-consistent cache with a hierarchy of authorities on top. The follow-ups almost always head the same way: from the happy-path walk through root, TLD, and authoritative servers, into caching and TTL semantics, then into failure and design judgment — where a TTL quietly becomes your incident recovery time. Each rung states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Book-level mechanics are linked rather than repeated: [DNS Resolution](../../networks/dns/resolution.md), [DNS Caching](../../networks/dns/caching.md), and the retry discipline in [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md).

## The Opening Question

**"How does DNS resolution work?"**

The expected core answer: the client's stub resolver asks a recursive resolver (ISP-provided or public) for `api.example.com`; if the answer is not in its cache, the resolver walks the hierarchy iteratively — a root server answers with a referral to the `.com` TLD nameservers, a TLD server answers with a referral to `example.com`'s authoritative nameservers, and the authoritative server returns the record ([RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html) defines this model, [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html) the wire format). Every hop caches what it learns for the record's TTL: the browser, the OS stub, and the recursive resolver all hold copies, so a hot domain resolves from a nearby cache in well under a millisecond while a cold lookup costs tens of milliseconds across several round trips.

A weak answer stops at "DNS translates names to IPs" or recites the hierarchy as a magic incantation without naming who does the walking or who caches. The strong answer adds the two structural facts that make everything else follow: resolution is *recursive for the client and iterative for the resolver* — the stub delegates the walking — and *every participant caches for the TTL*, which means the system's correctness and its recovery speed are both governed by cache lifetimes. The follow-up that escalates: **"Who actually does the iterative walk, and why is it split that way?"** — which forces the recursive/iterative distinction instead of letting it stay vague.

## Level 2: Recursive vs Iterative — Who Does the Walking?

**What it tests:** whether the resolver is a mechanism you can reason about or a magic middle box, and whether you understand the division of labor the split creates.

**Weak answer:** "The recursive resolver asks the root, then the TLD, then the authoritative" — true, but stated as if the *client* did it, and with no account of why the work is placed there.

**Strong answer:** distinguishes the two modes, names what each party is contractually responsible for, and knows the resolver is doing this work *on behalf of millions of clients at once*, which is why its cache is the load-bearing one.

**Escalation trigger:** "Why doesn't the client just walk the hierarchy itself?"

**Answer.** *Iterative* resolution is the mode where the server's best answer is a referral — "I don't know `api.example.com`, ask these `.com` servers" — and the *client* continues. *Recursive* resolution is the mode where the server takes the whole job and returns a final answer or an error. The split exists for three compounding reasons: locality (a resolver near the user, with a warm cache, pays the cold walk once and serves millions of hits), load on the hierarchy (thirteen logical root-server identities — served via anycast from well over a thousand instances worldwide — could not survive every browser walking the tree directly), and policy concentration (filtering, DNSSEC validation, and response shaping happen in one place). The stub resolver in your OS is deliberately dumb: query, cache, timeout, retry.

The senior observation is that the recursive resolver is the system's *convergence point*: caching, negative caching, validation, and rate limiting all live there, so running your own resolver is an architectural decision with blast-radius consequences. Resolver behavior also varies in ways that surprise operators: some cap or extend TTLs, some prefetch popular records, and some answer from cache even after expiry under load. When the interviewer pushes on "what if the resolver itself fails," the honest answer is layered — a stub tries secondary resolvers, retries with backoff, and the failure is usually a *timeout the user feels*, which connects directly to the retry discipline in [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md). The full delegation and referral mechanics live in [DNS Resolution](../../networks/dns/resolution.md).

## Level 3: TTLs and Negative Caching — The Staleness-for-Load Exchange

**What it tests:** whether you can reason about the TTL as a *quantitative trade-off* rather than a config value, and whether you know that "no such domain" is itself a cached answer.

**Weak answer:** "Lower the TTL when you want changes to propagate fast" — correct, but with no model of the other side of the trade, and no awareness of negative caching.

**Strong answer:** states both currencies explicitly (resolver load and query volume versus staleness and failover time), knows TTL is a *request* that some resolvers override, and can explain a domain resolving again only *after* the negative TTL expired.

**Escalation trigger:** "You fixed the record five minutes ago — why do some users still get NXDOMAIN?"

**Answer.** Every cached record carries a TTL, and the TTL is a three-way trade: smaller TTLs cut staleness and speed failover but multiply authoritative query volume and cold-lookup tail latency; larger TTLs do the reverse. The classic operator mistake is tuning TTLs for *load* reasons and then needing them for *failover* reasons — the two demands pull in opposite directions, and the value chosen for calm weather becomes your storm recovery time. Two wrinkles earn credit: first, the TTL is advisory — caches *should* expire when told but some resolvers deliberately clamp values in either direction, so "propagation" is a probabilistic decay curve, not a switch that flips; second, DNS servers-to-server notifications (RFC 1996 NOTIFY) exist only for zone transfers between authoritative secondaries — client-side caches learn about changes by *pulling on expiry*, never by being pushed.

**Negative caching** is the rung's non-obvious edge: when an authoritative server answers NXDOMAIN, the response carries the SOA record of the zone, and its minimum field tells caches how long to remember that the name *does not exist* ([RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html) standardizes this). The failure story is now standard in migrations and onboarding: an app queries a not-yet-created hostname, the NXDOMAIN sticks in the recursive cache for the negative TTL, and fixing the record upstream does not fix the users inside the window. The senior diagnostic habit: when "it works from my machine," check which resolver answered and its remaining TTL — `dig` shows both. The record types that make this work (SOA, TTL semantics per record) are catalogued in [DNS Record Types](../../networks/dns/record-types.md).

## Level 4: Failure, Failover, and the NS-Change Lag

**What it tests:** whether "what if DNS fails?" gets a layered answer — resolver timeout, stale data, unhealthy-but-served records, and slow delegation changes — instead of a single shrug.

**Weak answer:** "DNS is pretty reliable" or "use a backup nameserver" — no failure taxonomy, and no awareness that DNS happily serving a *wrong or dead* address is the more common production failure.

**Strong answer:** separates unavailability (resolution fails, user sees an error) from staleness (resolution succeeds and points somewhere dead), knows that DNS does no health checking, and can explain why nameserver changes lag by design.

**Escalation trigger:** "Your primary data center died — how long until users stop hitting it?"

**Answer.** The taxonomy has four layers. *Unavailability*: the resolver cannot reach any authority — users see timeouts; retry policy and fallback resolvers decide whether the error is instant or a five-second hang. *Staleness*: the record resolves fine but to a dead endpoint — this is the expensive one, because nothing is "broken"; traffic just keeps flowing into the crater for up to one TTL. *Served-but-wrong*: DNS does zero health checking — health-aware failover (Route 53 health checks and routing policies; see [Route 53](../../cloud/aws/route53.md)) is a *provider feature*, not a DNS property. *Delegation lag*: moving your authoritative nameservers is slower than changing A records, because the parent zone's NS and glue records carry their own long TTLs — commonly a day or more for major TLDs — so the old delegation lives on in thousands of recursive caches; hence NS changes are planned like migrations, old nameservers kept answering through the overlap.

The senior framing, worth saying almost verbatim: **a record's TTL is the upper bound on how long the world can keep doing the wrong thing — it is your blast-radius timer, and you choose it before the incident.** The coupled discipline: lower TTLs *in advance* (lower, wait one old TTL, then change) — lowering them at the moment of failure helps no one who already cached the long value. The catastrophic version of "resolution succeeded into nothing" appears when DNS fails as a *symptom* of a lower-layer failure — the October 2021 Facebook outage withdrew BGP routes, making authoritative nameservers unreachable and every property unresolvable at once, which [The Facebook BGP Outage of 2021](../failure-casebook/facebook-bgp-2021.md) walks in full. Related reading: [DNS Security](../../networks/dns/security.md) for spoofing and hijacking, and [DNSSEC](../../networks/dns/dnssec.md) for what cryptographic origin authentication does and does not fix.

## Level 5: Anycast, Scale, and DNS as a Global Eventually-Consistent Cache

**What it tests:** design judgment at the top rung — can you characterize DNS's *consistency model* and use anycast, cache hierarchy, and TTL sizing as deliberate design tools?

**Weak answer:** "Big DNS providers use anycast" as a finished fact, with no account of what anycast changes about failure, and no consistency model for DNS.

**Strong answer:** explains anycast mechanically (same IP announced from many sites; BGP steers each user to the nearest announcing site; failures are absorbed by withdrawing announcements), then names DNS's consistency honestly — it is a pull-based, eventually-consistent cache where staleness is bounded by TTL and updates are *never* instantaneous.

**Escalation trigger:** "If DNS is eventually consistent, what's the worst case, and how would you bound it?"

**Answer.** Anycast works because DNS responses are small, stateless, and cacheable: the same anycast address is announced from dozens of sites, BGP's route selection lands each user on a nearby one, a site failure is handled by routers re-converging to the next-nearest announcer, and the recursive resolver's cache absorbs the flap for records already resolved. The same mechanism fronts CDN edges (see [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md)), and it is why root and TLD service survives attacks that would flatten a unicast service: attack traffic lands near its source, and each site sheds only its own share. The trade: anycast makes *where* your query lands a routing decision you do not control, complicating debugging (two users, same resolver IP, different sites) and geo-sensitive answers.

The consistency characterization that earns the rung: DNS is a *write-rarely, read-everywhere* system where the authoritative server is the only source of truth and every cache between it and the user holds a possibly-stale copy whose age is bounded by TTL. Worst-case staleness is therefore `record TTL + resolver deviation`, and you bound it by (a) sizing TTLs to your actual failover requirement, (b) verifying what popular public resolvers actually honor, and (c) moving health-driven steering *below* DNS (load balancers, anycast, health-checked routing) wherever sub-TTL reaction is needed. The encrypted-DNS wrinkle (DoH/DoT — see [DNS over HTTPS](../../networks/dns/doh.md) and [Encrypted DNS](../../networks/advanced/encrypted-dns.md)) changes who runs the resolver and concentrates cache behavior into a few public providers — making their TTL policies matter more, not less. The template below turns this rung into answers for the variations interviewers ask.

## How to Approach Unfamiliar Variations

The template for "make DNS do X" and "what happens if DNS Y" questions:

1. **Locate the cache and its TTL first.** Every variation — propagation delays, migration ghosts, CDN origin changes, split-horizon answers — is a question about some cache's key, value, and lifetime. Name the cache (browser, OS stub, recursive, CDN, authoritative secondaries) before proposing any fix.
2. **Split "fails" into unreachable, stale, and unhealthy.** Unreachable needs redundancy and retries; stale needs TTL sizing done in advance; unhealthy needs health checking DNS does not have, so the answer moves to a layer that has it.
3. **Ask who controls resolution.** The stub, recursive resolver, authoritative provider, and network path have different owners and attack surfaces — encrypted DNS, DNSSEC, and split-horizon setups answer "who do you trust to answer" at different layers.
4. **Convert design questions into TTL economics.** "Design DNS for a global service" is answered with: anycast for proximity, cache-friendly small responses, TTL sized to failover needs, and health-aware steering below DNS when sub-TTL reaction is required — then say what you would monitor (authoritative query rates, cache-hit ratio, NXDOMAIN rate).

## Interview Questions

**Q: You are migrating a service to a new IP. Walk me through doing it with zero downtime.**
A: Lower the record's TTL well in advance (e.g. 60 s), wait at least one *old* TTL so caches holding the long value expire, then switch traffic — ideally at the load balancer behind a stable name rather than the DNS record itself. During the overlap, both endpoints must serve, because some resolver still holds the old address. The zero-downtime claim comes from the overlap, not from DNS being instant.

**Q: Why do some users still see the old site two hours after a record change with a 300-second TTL?**
A: In order of likelihood: a resolver ignoring or extending TTLs; a longer TTL on a different record type (NS or glue from a delegation) than the A record they changed; a negative-cached answer for a new hostname whose negative TTL outlived the fix; or a client-side/OS cache outside the resolver's control. The diagnosis is always the same: resolve through the affected users' resolver and read the remaining TTL.

**Q: Your authoritative nameservers are healthy but the site is unreachable worldwide. What class of failure is this, and what do you check?**
A: Reachability, not DNS itself — the classic case is a routing failure (BGP withdrawal or hijack) making the anycast-prefix nameservers unreachable, exactly the Facebook 2021 pattern. Check route announcements for your prefixes, then whether anycast sites are advertising. DNS "failing" is very often the network under DNS failing, and the distinction changes who you page.

**Q: When would you deliberately use a long TTL, and what would you put in place first?**
A: For records behind which you can absorb change at another layer — a stable LB VIP, an anycast edge, a CNAME to a provider whose failover you trust — because long TTLs cut authoritative load and cold-lookup latency. First in place: a health-checked layer below DNS that can redirect traffic sub-TTL, and a runbook that lowers TTLs before, not during, planned changes.

## Key Takeaways

- DNS resolution is iterative at the hierarchy and recursive for the client; the resolver is the system's convergence point for caching, validation, and load-shielding.
- Every hop caches for the TTL, and NXDOMAIN is cached too (negative caching, RFC 2308) — migrations fail on both.
- The TTL is a staleness-for-load exchange, and it is advisory: resolvers may clamp it, so "propagation" is a decay curve, not a switch.
- DNS does no health checking; failover speed is bounded by TTL unless health-aware steering lives at a lower layer — set TTLs to match your real failover requirement before the incident.
- Anycast plus the cache hierarchy is what makes global DNS scale and survive attack; its consistency model is eventual, pull-based, and bounded by the TTL you chose — and when resolution fails worldwide, the fault often belongs to a lower layer, as BGP withdrawal makes healthy nameservers unreachable.

## Cross-References

- [URL to Page](./url-to-page.md) — the parent chain whose first rung this ladder expands.
- [TCP Lifecycle](./tcp-lifecycle.md) — the connection stage DNS feeds into, with its own escalation ladder.
- [DNS Resolution](../../networks/dns/resolution.md) — the book's full treatment: referrals, delegation, and record mechanics.
- [DNS Caching](../../networks/dns/caching.md) — TTL semantics, resolver cache behavior, and negative caching details.
- [DNS Record Types](../../networks/dns/record-types.md) — SOA, A/AAAA, CNAME, NS, and what each contributes to the walk.
- [DNS Security](../../networks/dns/security.md) — spoofing, hijacking, and the trust model of the resolver.
- [DNSSEC](../../networks/dns/dnssec.md) — cryptographic origin authentication and what it leaves unsolved.
- [DNS over HTTPS](../../networks/dns/doh.md) and [Encrypted DNS](../../networks/advanced/encrypted-dns.md) — DoH/DoT mechanics and the resolver-concentration consequences.
- [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md) — the same anycast mechanism at CDN scale.
- [Route 53](../../cloud/aws/route53.md) — health checks and routing policies: the failover layer DNS lacks.
- [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md) — the retry discipline behind every "resolver failed" answer.
- [The Facebook BGP Outage of 2021](../failure-casebook/facebook-bgp-2021.md) — DNS failing as a symptom of routing withdrawal, at global scale.
- [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html), [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html), [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html) — the primary sources for the resolution model, wire format, and negative caching.
