# Rate Limit Header Assumptions: What "HTTP 429" Silently Promises

## Overview

A 429 response with a handful of `X-RateLimit-*` headers looks like a complete contract: the server says "you are over the limit, here is what remains, here is when to come back." The response embeds at least four silent promises that break in production with arithmetic regularity: that a 429 means "retry later with backoff" (rather than "stop for a while, or never with this credential"), that a `Retry-After` header will always be present to tell you how long, that the limit is per-key and stable across time and geography, and that the headers' numbers truthfully describe the quota that actually tripped. Each promise fails in a specific, reproducible way — header dialects differ per provider, client and server clocks disagree by more than a retry delay, fleet-wide deployments share one quota pool that no individual instance sees correctly, and burst allowances mask sustained-rate exhaustion.

This chapter audits the family with the collection's five-step pattern. The HTTP status itself is specified in RFC 6585; the naming conventions it spawned were left to vendors, which is precisely why the dialect problem exists — the IETF "RateLimit Header Fields for HTTP" work item is still a draft, and GitHub, Stripe, and Cloudflare each document their own conventions. Rate limiting's algorithmic side lives in the follow-up tree's rate-limiter design chapter; here we audit what the client may legitimately believe when the limit is enforced against it.

## Assumption 1: "429 Means I Should Retry Immediately With Backoff"

### The taught rule

When an API returns `429 Too Many Requests`, wait a little (exponentially longer each time) and retry; the request was rejected for pacing, not for correctness, so the same request will eventually succeed.

### How it fails

A 429 is not a single condition; it is a category. Quota exhaustion (you used your hour or day allowance), burst rejection (you exceeded a short-window rate), background-load shedding (the provider rejects when *its* capacity is thin, using the same status code), and credential-level penalties (abuse detection) all surface as 429. Only the first two respond well to backoff. Load-shedding 429s demand backing off *harder than backoff* — sometimes minutes, sometimes "stop and page a human" — because the provider is telling you that your aggregate traffic is part of a problem. And an abuse-detection 429 means the retry behavior itself is the offense: automated retries from a flagged credential can convert a temporary flag into a permanent block.

The retry-immediately reading also ignores who emitted the code. A 429 from an intermediary (API gateway, CDN, proxy) describes the intermediary's limiter, not the origin's; the origin may be perfectly willing, and the correct response is to discover which layer tripped rather than to blindly re-drive load through the choke point. Backoff then re-synchronizes fleets: ten thousand instances that hit the quota together schedule near-identical first retries, and the provider sees a synchronized second wave — the retry-storm shape audited in the sibling chapter on timeouts and retries, wearing a status code as a disguise.

### Failure scenario

A batch job's token bucket runs dry at the top of the hour. The scheduler re-queues the job every 60 seconds; 40 worker instances each retry with 1 s, 2 s, 4 s, 8 s backoff, putting roughly 280 additional requests into the first ten seconds of every cycle. The provider's abuse system, which keys on "client whose 429 rate exceeds its success rate," flags the credential. Now every request — including the legitimate ones from other services sharing the key — gets rejected with a 429 that carries no `Retry-After`, and the fleet's backoff, capped at 30 s, keeps the flag warm indefinitely. The correct behavior at minute zero was: read the quota reset time, sleep once until it, and cap fleet concurrency under the sustained limit — not retry.

### Detection heuristic and what to assume instead

Detection: alert on *outbound* 429 rate per dependency and per credential; if a client's 429 rate exceeds a small fraction of its success rate, the retry policy is misconfigured — log the full response header set (not just the status) so the tripping limiter can be identified. Corrected statement: *a 429 is a signal about pacing or aggregate load whose correct response depends on which limiter tripped and why; treat "immediately with backoff" as one option, and "wait until quota reset, reduce fleet concurrency, or stop and alert" as equally available.* A retry decision should consume the response's own metadata (headers, reset times) before consuming CPU.

## Assumption 2: "Retry-After Is Always Present"

### The taught rule

A 429 tells you when to come back via the `Retry-After` header — delay-seconds or an HTTP-date — so the client never has to guess.

### How it fails

`Retry-After` is optional. RFC 6585 defines 429 as *advising* the client about when it may retry and explicitly allows the origin to omit the header. Vendors diverge: some always send it on 429, some send it only on some endpoints, some send it on gateway-level rejections but strip it when the origin produces the 429, and some never send it and expect clients to read their proprietary reset headers instead. Client code written against the happy path — `response.headers["Retry-After"]` — then either crashes on a missing key, or, worse, treats a `None`/absent value as "zero seconds" and retries instantly, which converts a missing header into a retry storm. The header also has two formats: an integer number of seconds and an HTTP-date; a parser that assumes one format fails on the other, and the HTTP-date variant silently depends on the clock-skew problem (Assumption 1 of this chapter's sibling, clocks and time): a date compared against a skewed client clock can yield a negative or hours-long delay.

There is also a semantics gap: `Retry-After` on a 429 means "this is a reasonable interval before your *next single* request," not "your fleet's aggregate rate should be X." A thousand instances each honoring a 60-second `Retry-After` individually still generate a synchronized 1,000-request burst at t + 60 s. Jitter is not optional decoration; it is the mechanism that prevents the header's per-client semantics from becoming a fleet-wide denial pattern.

### Failure scenario

An SDK's retry policy is `sleep(int(response.headers["Retry-After"]))`. A provider's edge tier begins emitting 429s during a regional capacity event — without `Retry-After`, because that tier's configuration predates the header convention. The SDK's header lookup throws; the SDK's error handler catches the exception and classifies it as "malformed response — retry immediately." Every failing call now retries with zero delay: the client turns the provider's overload signal into a request multiplier, and the provider's own dashboards show this customer as the top offender. Nobody changed the SDK; the provider changed a header. The fix that survives: treat `Retry-After` as *maybe present*, parse both formats defensively, clamp the interpreted delay to a sane range, and fall back to the vendor's reset headers, then to exponential backoff with jitter.

### Detection heuristic and what to assume instead

Detection: contract-test the dependency's 429 shape — assert which headers actually appear (sampled in staging, verified against the vendor's documented behavior), and fuzz the client's parser with both `Retry-After` formats, both absent, and unparseable values. Corrected statement: *`Retry-After` is an optional courtesy, not a contract; a production retry policy must be total — defined for present-seconds, present-date, absent, and garbage — and must never let a missing header mean "zero."*

## Assumption 3: "Limits Are Per-Key and Stable"

### The taught rule

The limit is a fixed number attached to my API key (600 requests per minute, 50,000 per day), documented in the provider's pricing page, and identical for every request my service makes.

### How it fails

The stable-per-key picture breaks along four axes. *Composition:* limits are typically layered — per key, per user, per IP, per endpoint class, per region — and any one of them can trip while the headers describe another. A fleet behind one NAT egresses from one IP; a per-IP limiter you never read about enforces first. *Scale:* many limits are graded by plan tier, and a tier change, a trial expiry, or an account-level suspension silently rewrites the numbers. *Shape:* burst and sustained allowances differ — a token bucket permits 100 requests instantly and refills at 10/s; a client that "tested the limit once" (100 requests in a second, all accepted) concludes the limit is 100/s and designs its batching on that, then discovers at production scale that only 600/min exist. *Sharing:* a shared service key used by every instance of your fleet makes the quota a global pool; each instance's local view ("I've sent 3 requests") is meaningless against a pool consumed by ten thousand instances — the same class of error as assuming a process-local rate limiter protects a distributed deployment, which the follow-up tree's rate-limiter design chapter works through from the enforcement side.

Stability also fails in time: providers change limits with notice periods measured in weeks, ship different limits per datacenter region while your traffic pattern is global, and expose different headers per API version — the same fleet can straddle two dialects during a migration.

### Failure scenario

A service scales from 20 to 300 pods during a launch. Each pod's code contains `assert responses_used_today < 40000` based on the documented per-key daily quota, checked against its own local counter. No pod ever exceeds 400 — but the pool is exhausted by 09:40 because 300 × 130 average calls ≈ 39,000. The per-pod assertion never fires; the first symptom is 429s on the *hot* path with `X-RateLimit-Remaining: 0` (GitHub's documented convention: a reset epoch timestamp accompanies the remaining count). Recovery requires the coordination the code never had: a shared token bucket whose refill is paced at a fraction of the documented sustained limit, so fleet demand is bounded below the provider's numbers by construction.

### Detection heuristic and what to assume instead

Detection: track *summed* remaining-quota across all clients of the same credential (a single metric: fleet-wide `remaining` minimum), alert when its slope predicts exhaustion before the reset time; treat "we tested the limit" numbers as burst-only until verified against sustained traffic. Corrected statement: *a limit is an attribute of a quota pool — credential × scope × window × tier — not of your code; model the pool explicitly, enforce the sustained rate client-side, and treat every documented number as burst-inclusive until the vendor's limiter documentation says otherwise.*

## Assumption 4: "Headers Tell the Truth About Remaining Quota"

### The taught rule

`X-RateLimit-Remaining: 437` and `X-RateLimit-Reset: 1721332800` report the limiter's actual state; a client can budget against them directly.

### How it fails

The headers are a *projection* of limiter state, and the projection lags, approximates, or lies in documented ways. Staleness: the value was computed when the response was generated; a client-side fan-out that fires 100 concurrent requests after reading `Remaining: 500` overshoots, because each response's header was rendered before its siblings consumed. Approximation: some limiters update counters in batches or per-shard, and the header reports a shard-local number — two regional endpoints can both report plentiful remaining while the global pool is dry. Dialect: `X-RateLimit-Reset` is an epoch timestamp in some implementations and a *delay in seconds* in others (several providers' header conventions differ on exactly this point); a client that treats seconds-remaining as an epoch schedules its retry in 1970 — or in 54,000 years, depending on parse direction. Clock: even a correct epoch assumes client-server clock agreement, which NTP steps and skew make unreliable to the second — enough to matter when the budget is measured in seconds. And completeness: the headers describe the quota the *responder* knows about; a gateway in front of the origin may report its own limiter's state while the origin's independent limiter is what will reject your next request.

None of this makes the headers useless — it makes them advisory. The draft IETF RateLimit header fields exist precisely because the `X-` ecosystem was inconsistent enough to warrant standardization, and even that draft carefully worded the semantics to avoid promising exactness.

### Failure scenario

A data pipeline implements "credit-aware" throttling: each worker reads `Remaining` from its last response and self-throttles to `remaining / seconds_until_reset` requests per second. With 50 workers fanning out concurrently, every worker's view is the pre-burst snapshot, so aggregate in-flight demand is 50× the computed budget; the pool empties mid-cycle, and because the reset header is an epoch compared against an NTP-stepped clock that is 3 seconds behind, the workers wake "early," see nonzero remaining (the limiter's counters refill on the server's schedule, not theirs), sprint, and re-exhaust. The system oscillates — polite for 55 seconds of every minute, abusive for 5 — which is exactly the traffic shape that limiter-side abuse detection keys on. The stable design never budgets from a snapshot: a client-side token bucket paces demand, and headers serve only as feedback for slowing down faster.

### Detection heuristic and what to assume instead

Detection: log `remaining` alongside the actual acceptance outcome; if accepted-after-low-remaining and rejected-after-high-remaining events occur at measurable rates, the headers are stale or shard-local — stop budgeting on them. Corrected statement: *rate limit headers are advisory telemetry about one limiter's view at one instant; use them to steer (slow down, wait for reset), never as the authoritative budget — the authoritative budget is the one you enforce client-side, fleet-wide, at a fraction of the documented limit.*

## Interview Questions

1. **Your client gets 429s without a `Retry-After` header. What does your retry code do, and what should it do?** A fragile client treats the missing header as zero delay and storms the provider. A total policy: parse both formats defensively, fall back to vendor reset headers, then exponential backoff with jitter, clamped to a floor and cap — and distinguish quota exhaustion (wait for reset) from load-shedding (back off hard, reduce concurrency).
2. **Two services share one API key behind a load balancer. Why does per-instance quota tracking fail, and what replaces it?** The quota is a global pool; each instance's local count is meaningless against fleet demand. Replace with a shared token bucket (Redis-backed or similar) paced under the documented sustained limit, and monitor summed `remaining` across clients for exhaustion slope.
3. **`X-RateLimit-Reset` is 1721332800 — when do you retry?** First determine the dialect: epoch timestamp or delay-in-seconds; the same header name means both in the wild. Then compare against a trustworthy clock — NTP skew makes second-level budgets unreliable — and add jitter so a synchronized fleet does not arrive as one wave.
4. **You tested an endpoint at 100 requests per second and all succeeded. Can you design for 100 rps sustained?** No — that number may be the burst bucket of a token bucket whose sustained refill is far lower. Design under the documented sustained rate, verify with a controlled ramp, and watch for the limiter's two-regime behavior.
5. **Where does rate-limit handling belong: client, gateway, or provider?** All three, with different jobs: the provider enforces; the gateway aggregates and shields (its own 429s may not describe the origin's limiter); the client must treat 429 as advisory pacing signal, not error — which is why the retry-storm arithmetic from the sibling chapter on timeouts and retries applies verbatim.

## Key Takeaways

- A 429 is a category, not a condition: quota exhaustion, burst rejection, load shedding, and abuse flags all wear it, and they have different correct responses.
- `Retry-After` is optional and dialect-split (seconds vs HTTP-date); a production retry policy must be total over its absence and never interpret "absent" as "zero."
- Limits are properties of quota pools (credential × scope × window × tier), not of your code; a shared key turns the pool global while every instance's local view stays local.
- Rate limit headers are advisory projections: stale under fan-out, shard-local under regional deployment, and dialect-inconsistent on the meaning of `Reset`.
- The stable client-side design is a fleet-wide token bucket paced under the documented sustained limit, with headers used as feedback, not budget.

## Cross-References

- [Rate limiter design](../followup-tree/rate-limiter-design.md) — the enforcement-side escalation chain: algorithms, distributed counting, and why client-visible headers differ from limiter state.
- [Timeout and retry assumptions](timeouts-and-retries.md) — the retry-amplification and jitter arithmetic that 429 handling inherits.
- [Backpressure](../connection-atlas/backpressure.md) — load shedding as a feedback signal, and why rejection codes encode overload rather than policy.
- [Rate limiting (HLD)](../../interview/system-design/rate-limiter.md) — where the limiter, its quota pools, and its headers sit in a designed system.
- [RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.html) — the specification that defined 429 and made `Retry-After` optional.
- GitHub REST API rate limit documentation and the IETF "RateLimit Header Fields for HTTP" draft — cited by title as the dialect examples; the draft is not a published RFC, so no URL is asserted.
