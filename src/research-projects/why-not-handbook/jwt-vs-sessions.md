# JWTs vs Server Sessions: Where Does Authentication State Live?

## Overview

"JWTs are stateless and scale; sessions are legacy" — the claim is repeated so often that the mechanism behind it goes unexamined. The sharper question is: **where does the fact "this browser is authenticated as user 42" physically live, who can change it, how fast, and at what cost per request?** A server session puts that fact in a store the server owns, keyed by an opaque cookie; every request pays a lookup, and revocation is a delete. A JSON Web Token puts the fact in claims signed by the issuer and carried by the client; every request pays a signature verification, and revocation is a problem the token format does not solve. Both mechanisms implement the same contract — requests carry proof of identity — but they relocate state, cost, and risk in opposite directions.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **sessions centralize truth and buy instant revocation at the price of a lookup and a store that must stay up; JWTs decentralize truth into the token's remaining lifetime and buy lookup-free verification at the price of revocation machinery — denylists, short expiries, refresh tokens — that progressively re-import the session store.** Neither is "more scalable" in the abstract: a session lookup against a well-sharded cache is measured in fractions of a millisecond, while JWT verification at scale is a CPU bill plus a key-distribution problem. The decision hinges on revocation latency, who needs to verify, and which failure mode — dead session store or unrevocable token — the product can afford.

## Step 1: The Problem and Its Constraints

The abstract shape: after a login, subsequent requests must prove identity without re-sending credentials. Constraints that decide where that proof should live:

- **Revocation latency.** When a password changes, a token is stolen, or an account is banned, how quickly must access end? Instantly (delete a session) or within the token's remaining TTL (a JWT's structural answer)? "Logout everywhere" is a product requirement that maps directly onto this mechanism.
- **Who verifies?** One monolith, or five services and a CDN edge that all need to check identity? Verification without a shared-store hop is the JWT mechanism's home turf; a shared hot cache is the session mechanism's.
- **Per-request budget.** A network/cache round trip per request (sessions) versus CPU for a signature per request (JWTs). Both scale; they scale on different resources.
- **Client population.** Browsers honor cookies with their security attributes; native apps and service-to-service callers do not carry cookie semantics naturally and often prefer bearer tokens.
- **Key and store operations capability.** JWTs demand key rotation, algorithm discipline, and (with asymmetric signing) a JWKS distribution path. Sessions demand a replicated, low-latency store and its failure drills.
- **Compliance and audit.** Some regimes want server-side visibility of every active session — an inventory a pure token design does not have.

## Step 2: The Mechanisms

### Server sessions

Login succeeds; the server generates a random, meaningless identifier, stores the session record (user, roles, expiry, CSRF secret) in Redis or the database, and sets the identifier in a cookie governed by [RFC 6265](https://www.rfc-editor.org/rfc/rfc6265.html) attributes (`HttpOnly`, `Secure`, `SameSite`). Every request carries the identifier; the server looks it up. The mechanisms that matter:

- **Truth is centralized and mutable.** The store is the live set of logged-in principals. Revocation is `DEL`; "logout everywhere" is a scan by user index; changing roles takes effect on the next request because nothing is cached client-side. Sliding expiry (touch the record on access) models real engagement — a token with a fixed `exp` does not.
- **The lookup is the tax and the feature.** A sub-millisecond shared-cache read per request keeps the session store on every request's critical path — which is precisely why the store's failure is an outage of the logged-in world, and why sticky sessions (pinning users to the server holding their session) trade that outage for load-balancing rigidity.
- **Cookie availability is a constraint, not a default.** Cookies are same-site-scoped, size-capped (~4 KB), and attach automatically — which is what makes them CSRF-relevant and what makes cross-domain APIs and native apps awkward clients.

### JWTs

A JWT is three dot-joined, [Base64url](https://www.rfc-editor.org/rfc/rfc7519.html)-encoded parts: header, claims payload, signature. The issuer signs (HMAC with a shared secret, or RSA/ECDSA with a private key); anyone holding the public key verifies without network I/O. The mechanisms that matter:

- **Truth is frozen at issuance.** Claims — user ID, roles, expiry — are valid until `exp` because no one can cheaply unsay them. Verification is local CPU: no store, no hop, which is why a fleet of independent services (and CDN edge workers) can each authenticate without a shared dependency. The OWASP [session management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) frames the trade directly: short lifetimes limit the blast radius of stolen tokens.
- **Revocation is an add-on, and every add-on is a session store in disguise.** A `jti` denylist must be checked before trusting the token — a lookup per request, returning the caller to where sessions started, except the lookup only has to be authoritative for the token's remaining life. Refresh tokens (long-lived, exchangeable for short-lived access tokens) reintroduce a server-side record per client — again, a session store with extra rotation steps.
- **Key management is the second half of the system.** Algorithm agility must be constrained (the verifier dictates the algorithm; the header's `alg` is untrusted input), keys must rotate on a schedule, and asymmetric verification needs a distribution mechanism (JWKS endpoints, cached with fallbacks — a fetch failure becomes an outage).
- **Tokens are credentials with a size.** Claims live in cookies or `Authorization` headers; the 4 KB cookie ceiling and header bloat are real budgets, and [what a signature does and does not protect](../misconceptions/jwt-is-encrypted.md) — integrity, not confidentiality — decides what may be claimed at all.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Server sessions | JWTs |
|----------|-----------------|------|
| Where truth lives | Server-side store, mutable | Client-held signed claims, frozen until `exp` |
| Per-request cost | One lookup (I/O) | One signature verification (CPU) |
| Revocation | Immediate (`DEL`), user-indexed | After `exp`, or via denylist/refresh machinery |
| Logout-everywhere | Native (delete the user's records) | Re-issue design + denylist, or wait out TTLs |
| Multi-service verification | Shared store on each request's path | Local verification with distributed public keys |
| Expiry model | Sliding (activity-based) or fixed | Fixed at issuance; extension = refresh flow |
| Backing dependency | Store availability = logged-in availability | Key/JWKS availability = verification availability |
| Transport fit | Cookies (browser-native) | Any header; cookie or bearer |
| Size budget | Opaque ID, ~32 bytes | Claims payload; cookie/header limits apply |
| Signature vs secrecy | Store contents never client-visible | Payload is readable by anyone holding it |
| Characteristic failure | Store outage logs out everyone | Stolen token valid until expiry; clock drift expires sessions early |

The **revocation axis** deserves the arrow drawn. Every design answers "how fast can the system change its mind?" Sessions answer "one delete, effective now" and pay a lookup on every request forever. JWTs answer "when the token expires, unless you build the list" — and the denylist, checked per request with TTLs matched to token life, is the session mechanism re-entering through a narrower door. The honest framing for interviews: **the choice is not stateful versus stateless; it is whether the revocation set is the whole session table or only the exception list.** A system that rarely revokes early profits from the exception-list model; a system that revokes constantly has reinvented sessions and should stop pretending otherwise.

## Step 4: When Each Wins

| Condition | Choice | Why |
|-----------|--------|-----|
| Instant revocation is a product requirement (bans, password change, "log out all devices") | Sessions | Delete is immediate and indexed by user |
| Many independent services/edges verify identity without a shared hop | JWTs | Local signature verification; JWKS distributes trust |
| Browser-first monolith, server-rendered, existing cache tier | Sessions | Cookies do the transport; lookup is sub-millisecond; simplest correct system |
| Mobile/API clients across origins, no cookie semantics | JWTs (bearer) | Transport-neutral; `Authorization` header works everywhere |
| Session inventory/audit required server-side | Sessions | The store *is* the live session list |
| Edge/CDN-level auth gating per request | JWTs | Verification with cached keys runs at the edge |
| Claims must stay secret | Either, carefully | JWT payloads are signed, not encrypted — see the confidentiality caveat |

**Sessions win** for the common web application: one product, browser clients, a Redis already in the stack, revocation that must work tonight. **JWTs win** at machine boundaries and architectural seams: service-to-service auth, first-party APIs consumed by mobile apps, verification that must happen at the edge, and multi-team platforms where no one wants a shared session store on every call path. **The honest hybrid** is the industry's de facto standard and deserves its complexity named: a short-lived (minutes) access token for verification economics plus a server-side refresh token carrying the revocation authority — accept the fact that revocation lives server-side again, size the access-token TTL to the worst-case revocation delay the product tolerates, and stop describing the result as "stateless."

## Step 5: Edge Cases and Counterexamples

- **The denylist that becomes the session table.** A team adds a `jti` denylist "just for immediate revocation," then adds per-user invalidation on password change, then per-role invalidation on a breach. Each addition grows the checked set until every request pays a lookup whose hit rate approaches a session store's — with more moving parts (token issuance, refresh, key rotation) than the session design it replaced. The mechanism predicts it: an exception list consulted per request and populated by policy converges to the table it was exempting itself from.
- **Clock drift as a fleet-wide logout.** `exp` and `iat` are checked against the *verifier's* clock. An NTP misconfiguration that steps a fleet's clocks forward by ten minutes invalidates every outstanding token at once — sessions expire in aggregate, retries re-authenticate, and the login service meets the traffic spike of an outage. Fixed-lifetime tokens inherit every verifer's timekeeping; a small leeway window is standard, but the mechanism — time as a distributed input — is the [clock assumptions](../assumptions-hunt/clocks-and-time.md) problem wearing an auth badge.
- **The 4 KB cookie ceiling, hit from below.** JWT-in-cookie designs that keep appending claims (roles, entitlements, feature flags per service) eventually exceed the browser's per-cookie limit; the browser silently drops the cookie; users log out in loops that no log explains, because the failure is client-side and per-cookie. The token's size budget is a real interface constraint, and claims bloat is the mechanism that spends it.
- **Symmetric single points, differently dressed.** The session store dies: everyone is logged out until it recovers. The JWKS endpoint (or its cached keys) becomes unavailable right after a key rotation: verification fails fleet-wide until propagation completes. Neither design eliminates the central dependency; they relocate it — from a session store to a key distribution path — and each outage drill must target its own location.
- **Algorithm confusion, the verifier's bug.** A verifier that trusts the token header's `alg` accepts `none` or accepts an HMAC forged with the public key of an RSA pair. The format is not at fault — RFC 7519 requires the verifier to constrain algorithms — but the mechanism explains the bug class: the token advertises its own verification rule, and trusting the advertisement hands the attacker the choice. Pinning the algorithm server-side is the fix that costs nothing and prevents the class.

## Step 6: Decision Framework

1. **How fast must revocation take effect, worst case?** Instantly, or within seconds → sessions (or the hybrid's refresh authority). "Within the access token's TTL" → JWTs with TTL sized to that requirement.
2. **Who verifies, and can they share a store?** One service or a tightly coupled fleet → sessions. Many independent services or edge → JWTs with JWKS.
3. **What are the clients?** Browsers → cookies (either mechanism). Native apps / cross-origin APIs → bearer tokens, usually JWTs.
4. **Does the product need a live session inventory?** Yes → server-side state of some kind exists already; make sessions use it honestly.
5. **What does the team operate well?** A proven replicated cache and its failure drills → sessions. Key rotation, algorithm discipline, token issuance → JWTs. Anything else → pick the one whose on-call rotation can carry it.
6. **Default in doubt:** short-lived JWT access token plus server-side refresh token; revocation requirement drives the access-token TTL; document the worst-case revocation delay as an explicit product parameter rather than an accident of configuration.

## Interview Questions

1. **Why is "JWTs are stateless" an incomplete claim?** Verification is lookup-free, but revocation, refresh tokens, and per-user invalidation are server-side state by construction. The accurate claim: JWTs move state from every-request-critical to exception-only, and the design question is whether the exception set stays small.
2. **A regulator asks: "list every currently active session for this user." What does your design answer?** A session store: a user-indexed query. A pure JWT design: nothing — the system has no live inventory, only tokens in the wild; the honest answer requires refresh-token records or a denylist, i.e., server-side state. This question exposes where truth actually lives.
3. **Your JWTs are signed with HS256 and one service's secret leaks. What is the blast radius and the fix?** Every token minted with that shared secret is forgeable across all services sharing it — the symmetry is the problem. Rotate the secret (invalidating all tokens at once) and move to asymmetric signing so verifiers hold public keys only, limiting any single leak to signing, not forging.
4. **Why does sliding expiry fall out of sessions but not JWTs?** Sliding expiry means the credential's life extends on activity — a write to the credential's state. Sessions mutate the store on access for free; a JWT's claims are frozen at issuance, so the equivalent is the refresh flow — a server round trip that is a session lookup with extra steps.
5. **Where do CSRF and XSS land differently across the two?** Cookie-carried credentials (either mechanism) are CSRF-relevant because browsers attach them automatically — `SameSite` and CSRF tokens are the answer. JWTs in `Authorization` headers are not auto-attached and dodge CSRF, but any XSS can read browser-stored tokens; `HttpOnly` cookies protect against theft at the price of CSRF exposure. The transport, not the token format, decides the attack surface.

## Key Takeaways

- The fork is **where authentication truth lives**: a mutable server-side table (sessions — instant revocation, per-request lookup) or a client-held signed claim set (JWTs — lookup-free verification, revocation only through expiry or added machinery).
- Revocation latency is the product-facing parameter that should drive the decision; every revocation capability added to a JWT design re-imports session state.
- Both designs have a central dependency — the session store for one, the key distribution path for the other — and failure drills must target the right location.
- The dominant production answer is a hybrid (short-lived access token + server-side refresh), whose honest description includes the server-side state it necessarily keeps.
- Transport follows clients: cookies for browsers with their CSRF/`HttpOnly` trade-offs; bearer tokens for apps and services.

## Cross-References

- [Stateless vs Stateful: Why-Not Handbook](./stateless-vs-stateful.md) — the broader state-placement fork this auth-specific decision instantiates.
- [Auth, Identity, and Session: Connection Atlas](../connection-atlas/auth-identity-session.md) — the dependency web joining tokens, cookies, and identity providers.
- [JWT is Encrypted: Misconceptions](../misconceptions/jwt-is-encrypted.md) — the signed-not-encrypted confusion behind the claims-confidentiality edge case.
- [Stateless Means No State: Misconceptions](../misconceptions/stateless-means-no-state.md) — the slogan this page's revocation axis dissects.
- [JWT](../../backend/auth/jwt.md) and [Session Management](../../backend/auth/session-management.md) — the book's implementation-level chapters for each half.
- [Cookies and Storage](../../web-development/cookies-storage.md) — the transport mechanics (attributes, limits) behind the cookie edge cases.
- [Security and Crypto: Assumptions Hunt](../assumptions-hunt/security-crypto.md) — the deployment assumptions beneath key management and verification.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
