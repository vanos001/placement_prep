# Proxy Header Assumptions: What "Just Read the Header" Silently Promises

## Overview

Behind every load balancer, CDN, and reverse proxy, application code reads HTTP headers with quiet confidence: the client's IP is in `X-Forwarded-For`, the `Host` header names the site the user typed, and the headers the code sets are the headers the downstream component receives. Each of these is a true description of one hop pretending to be a description of the whole chain. Headers are not a transport layer's contract; they are mutable metadata that every intermediary is permitted — and sometimes required — to add, rewrite, strip, or reorder on the way through. The result is a class of bugs where the application behaves perfectly per its code and reports a fact about the world that is simply false.

This chapter audits the header family with the collection's five-step pattern. The semantics cited below come from RFC 9110 (HTTP Semantics) and RFC 7239 (the `Forwarded` header, which exists precisely because `X-Forwarded-For` was never standardized), plus Mozilla's reference documentation for the de facto header. The trust-boundary reasoning follows the same line as the sibling security chapters: a header is attacker-controlled input until every intermediary on the path has been accounted for. The two practical questions that keep recurring are "which proxy appended this value?" and "who is allowed to set it?" — and most production incidents in this family reduce to one of those two questions having no answer.

## Assumption 1: "X-Forwarded-For Tells the Client IP"

### The taught rule

When you need the client's real IP address behind a proxy, read `X-Forwarded-For` — that is what the header is for.

### The hidden assumptions

- `X-Forwarded-For` is a client-suppliable request header. A curl command can set it to anything before the request ever touches your infrastructure, so the first value in the list may be a lie the attacker typed.
- The header's semantics are append-only at each hop: each proxy *adds* the address it saw, and RFC 7239 documents the resulting list as "the list of proxies the request passed through" — a chain description, not an identity claim. Reading "the first entry is the client" assumes every entry was appended by an honest proxy that had no reason to lie.
- Trust is positional and configuration-dependent: the standard defense is to count entries from the right and trust only the suffix added by proxies you operate. That defense requires knowing the exact number of trusted proxies in every environment — dev, staging, and production frequently differ, and a CDN adds a hop your config has never seen.
- The header can arrive multiple times (several `X-Forwarded-For:` lines that some proxies merge and others do not), can be empty, and silently changes meaning when an intermediary uses proxy protocol, TLS termination, or a different header dialect (`X-Real-IP`, `Client-IP`, the standardized `Forwarded`).

### Counterexample

A rate limiter keys on the first `X-Forwarded-For` entry. An attacker sends `X-Forwarded-For: 1.2.3.4` on every request, each with a different invented address: the limiter sees a distinct innocent-looking IP per request and never throttles, while the connection-level source address — which is unforgeable — was the only trustworthy signal. The fix is structural, not a regex: the edge proxy that terminates the connection overwrites (rather than appends to) the client-supplied value, and the application either trusts only that edge-set value or walks the list from the right, skipping exactly N known-trusted proxies, per the approach RFC 7239 formalizes with its `for` and `by` parameters. Teams that get this wrong usually have the right idea in production and the wrong behavior in staging, where there is one fewer proxy and the "trusted hop count" constant is off by one — which is also how it slips past tests.

### What changes when the assumption is removed

Corrected statement: *`X-Forwarded-For` is a chain of claims appended by whoever handled the request; a client IP derived from it is valid only within an explicitly configured trust boundary, counted from the closest proxy backward.* Concretely: the outermost proxy you control sanitizes the header; the application's IP extraction is a function of (header, configured trusted-hop count), not of the header alone; and the standardized `Forwarded` header is preferred on greenfield paths because its syntax makes the chain explicit instead of implicit in append order.

### Consequences

This assumption powers two interview favorites — "how do you rate limit behind a CDN?" and "why is logging the client IP harder than it sounds?" — and both answers are the same trust-boundary argument. It also connects to security review: any allowlist, audit log, or fraud rule keyed to a spoofable header inherits the spoof, which is why the sibling security chapter treats headers as untrusted input rather than as metadata the infrastructure vouches for.

## Assumption 2: "The Host Header Is Trustworthy"

### The taught rule

The `Host` header identifies which site the client requested, so routing, canonical-URL generation, and redirect construction can rely on it.

### The hidden assumptions

- `Host` is set by the client. Browsers set it from the URL bar, but any HTTP client can set it to anything, and the load balancer forwards it to whichever virtual host the routing layer selects — meaning an attacker can often choose which backend receives a hostile `Host`.
- RFC 9110 defines the request target and `Host` as two separately controlled inputs, and allows the absolute-form request target to override the `Host` header. Proxy clients in particular send absolute URIs, so "the host" can differ depending on which field the server implementation prefers.
- Application frameworks commonly rebuild absolute URLs from `Host` (password-reset links, OAuth redirect URIs, canonical tags). That turns a header an attacker controls into a string embedded in emails and redirects — the mechanism behind password-reset poisoning, where the reset link points at the attacker's domain.
- Proxies and CDNs may rewrite `Host` to the origin's name, so the value the application sees may be neither what the user typed nor what the router matched, and cache layers that key on `Host` can be poisoned into storing responses under the wrong one.

### Counterexample

An app generates password-reset links as `https://{Host}/reset?token=...`, reading `Host` from the request. An attacker requests a reset for a victim's account with `Host: attacker.example` (accepted because the default virtual host answers any name). The app emails the victim a reset link pointing at `attacker.example`, the victim clicks it, and the token lands on the attacker's server. Every component worked as coded; the vulnerability was trusting a client-supplied header in a security-relevant URL. The fix pattern: construct external URLs from a server-configured canonical base URL, validate `Host` against an allowlist at the edge (rejecting requests whose host does not match), and treat `X-Forwarded-Host` — same trust position as `X-Forwarded-For` — with the same suspicion.

### What changes when the assumption is removed

Corrected statement: *`Host` selects routing but does not certify identity; any value used for URL construction, caching keys, or security decisions must come from configuration or from a validated, allowlisted set.* The operational checklist is short: allowlist hosts at the edge, never build absolute URLs from request-supplied hostnames in security-sensitive contexts, and log the mismatch between `Host` and the routing decision — mismatches are usually probes for exactly this bug.

### Consequences

Interviewers reach for this one in "how does virtual-host routing interact with security?" and cache-poisoning discussions; the answer that stands out distinguishes `Host`'s routing role (legitimate) from its identity role (illegitimate without validation). The sibling API-contracts chapter makes the general point in contract form: anything a client controls, including "obvious" headers, is input, and input needs validation rules written down.

## Assumption 3: "Headers I Set Are Headers the App Sees"

### The taught rule

The platform sets security headers, request IDs, and tenant metadata on responses or requests; what was set is what arrives.

### The hidden assumptions

- HTTP defines hop-by-hop headers (listed in the `Connection` header, per RFC 9110) that every proxy must strip and never forward — a proxy that faithfully forwards your `Connection: keep-alive`-listed header is more correct than the code expecting it downstream.
- Intermediaries add their own headers unconditionally: `X-Forwarded-For` appended, `Via` appended, request IDs replaced, `Host` rewritten. A header the application "set" can arrive with an extra value, a merged value, or two copies; duplicate-header handling (join with commas, take first, take last) differs per stack.
- Frameworks normalize names: some environments deliver `X_Request_Id` when code wrote `X-Request-Id` or vice versa, underscores are often dropped or converted by proxies for ambiguity reasons, and casing is case-insensitive per spec but string-keyed in some code paths.
- Header size limits are real: a proxy that hits its limit truncates the header block, and the failure mode is a silently missing header, not an error — the response looks normal and lacks the one header the middleware promised.
- HTTP/2 and HTTP/3 convert the header name to lowercase on the wire; middleware comparing `Header-Name` with exact string equality works on HTTP/1.1 traces and fails on h2 traces depending on where in the stack the comparison happens.

### Counterexample

A platform ships a security middleware that sets a strict `Content-Security-Policy` on responses. The team validates it in staging — direct connection, header present. In production the response passes through an API gateway whose response-header-size limit is exceeded because the policy is long and a second large header joins the same response; the gateway drops the oversized header silently, the browser sees no CSP, and the dashboard that "proves" CSP coverage by checking application logs still shows the middleware executed. The gap is visible only from outside the trust boundary, which is why the detection has to be a probe from the client side — a synthetic check asserting the response as the browser sees it — rather than a log line from inside.

### What changes when the assumption is removed

Corrected statement: *headers are best-effort metadata across a proxy chain; anything load-bearing must be verified at the final vantage point, made small enough to survive every hop's limits, and named with the dialect every hop agrees on.* Practical responses: end-to-end synthetic checks on security headers, single trusted request-ID injection point (usually the edge) with overwrite-on-conflict semantics, explicit per-hop documentation of which headers are added, rewritten, and stripped, and integration tests that run through the real proxy topology, not around it.

### Consequences

The interview probe "your security header is missing in production but the code sets it — where do you look?" has a short answer with a long tail: hop-by-hop stripping, size limits, duplicate handling, and name normalization, each plausible and each invisible from application logs. The rate-limit-headers chapter records the same phenomenon in its own domain — header dialects disagreeing across a chain — and the api-gateway follow-up tree covers the gateway's side of the rewrite behavior.

## Interview Questions

1. **You are behind a CDN and need the true client IP for rate limiting. Walk me through the trust problem.** `X-Forwarded-For` is client-suppliable and append-only; the answer is a trust boundary counted from the closest trusted proxy backward (or edge-side overwrite per RFC 7239's model), plus a note that staging and production hop counts differ.
2. **Why can the `Host` header be dangerous even though the router needs it?** Routing use is legitimate; identity use is not. Client-controlled `Host` fed into URL generation becomes password-reset poisoning and cache-key confusion; fix is edge allowlisting plus configuration-driven canonical URLs.
3. **A middleware sets a header but production responses lack it. List four mechanisms.** Hop-by-hop stripping via `Connection`, response header-size limits with silent truncation, unconditional rewriting by intermediaries, and name normalization (case, underscore conversion) breaking a string-equality check downstream.
4. **What does RFC 7239 give you that `X-Forwarded-For` does not?** A standardized, explicit syntax for the forwarding chain (`for`, `by`, `host`, `proto` parameters), removing the ambiguity of comma-joined append order and multiple header lines.
5. **How would you test header behavior across a proxy chain?** Integration tests through the real topology, plus external synthetic probes asserting what the client actually receives — never in-process logs, which sit inside the trust boundary the bug lives across.

## Key Takeaways

- `X-Forwarded-For` describes a chain of claims, not an identity; a client IP is real only inside an explicitly configured trust boundary counted from the right.
- `Host` is a routing input and an attacker-controlled one; security-relevant URLs and cache keys must come from configuration or an allowlist.
- Headers are mutable across every hop: stripped (hop-by-hop), added, rewritten, duplicated, truncated, and renamed — the application's view is the chain's output, not the code's input.
- The standardized `Forwarded` header and edge-side overwrite semantics exist because the de facto headers' implicit append order kept failing; prefer explicit contracts.
- Detection for header assumptions must run from outside the trust boundary — synthetic client-side checks, not application logs.

## Cross-References

- [Security and crypto assumptions](security-crypto.md) — headers as untrusted input in the broader security assumption audit.
- [Rate limit headers](rate-limit-headers.md) — the same header-dialect disagreement problem in the rate-limiting domain.
- [API contracts](api-contracts.md) — why client-controlled inputs, including obvious headers, belong in the written contract.
- [HTTPS means secure (misconception)](../misconceptions/https-means-secure.md) — TLS protects the channel, not the header semantics at each hop.
- [Load balancing and partitioning](../connection-atlas/load-balancing-partitioning.md) — the intermediary layer where header rewrites happen.
- [Auth, identity, and session](../connection-atlas/auth-identity-session.md) — where trust boundaries and identity claims meet request metadata.
- [API gateway escalation chain](../followup-tree/api-gateway.md) — the gateway's own rewrite and pass-through behavior, interviewed layer by layer.
- [Proxy architecture escalation chain](../followup-tree/proxy-architecture.md) — the proxy-chain topology these header assumptions live across.
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — Host/request-target relationship and hop-by-hop header rules, from the source.
- [RFC 7239: Forwarded HTTP Extension](https://www.rfc-editor.org/rfc/rfc7239.html) — the standardized forwarding-chain header.
- [MDN: X-Forwarded-For](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For) — the de facto header's documented caveats.
