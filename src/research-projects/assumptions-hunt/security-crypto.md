# Security and Crypto Assumptions: What "It Uses HTTPS" Silently Promises

## Overview

Security teaching produces a shelf of shortcuts — "HTTPS means this site is safe", "Math.random() is random enough", "hashing passwords is fine", "nobody will find that endpoint", "comparing strings compares strings" — and each shortcut silently swaps a precise cryptographic statement for a feeling. The precise statements are not obscure: TLS authenticates a hostname and encrypts a transport; `Math.random()` is a deterministic PRNG with finite state; hash functions were designed to be fast and collision-resistant, which is precisely wrong for password storage; obscurity is not an access-control mechanism; and byte-by-byte equality checks leak timing. The gap between the feeling and the statement is where account takeovers, credential dumps, and authentication bypasses live.

This chapter audits the family with the collection's five-step pattern. Primary sources are strong here: MDN and the V8 team's own blog state plainly that `Math.random()` is not for security, OWASP's Password Storage Cheat Sheet specifies the password-hashing parameters, RFC 8725 defines the JWT algorithm-confusion trap, RFC 4086 sets the randomness requirements, and Go's `crypto/subtle` documentation exists because timing-safe comparison is a library-level concern. All cited URLs were fetched and verified during writing; where numbers come from benchmark classes rather than a specific measurement, the text says so.

## Assumption 1: "HTTPS Means This Site Is Safe"

### The taught rule

The padlock in the address bar means the site is legitimate and safe to interact with.

### The hidden assumptions

- TLS authenticates a *hostname* (via the certificate chain) and encrypts the *transport*. It says nothing about who operates the host, what they do with the data, or whether the code the host serves is malicious.
- Domain-validated certificates are free and automatically issued (the repo's ACME chapter covers the automation), so a phishing site's certificate is as valid as a bank's. Certificate authorities verify control of a domain, not honesty of its operator.
- "Safe" also has to include what the page *runs*: third-party scripts, CDNs, and ad networks are executed in the page's origin, so a single `<script src>` from a compromised provider defeats the transport security that mattered so much.

### Counterexample

A phishing campaign sends links to `secure-login.example-bank.co` behind a valid, browser-trusted certificate: the padlock is green-adjacent and genuine, and victims' credentials are harvested anyway — HTTPS protected the attacker's delivery, not the user. The documented variant that reaches even careful users is script-level: a page with otherwise-excellent security posture includes analytics from a third party; that provider is compromised; the injected script reads the DOM and keystrokes inside the trusted page's origin. Both attacks require no certificate fraud and no TLS break — they operate entirely inside what HTTPS *does* guarantee, which is the point.

### What changes when the assumption is removed

Corrected statement: *HTTPS is a precondition for safety on the web, not a judgment of it — it tells you who owns the pipe, not who owns the pipe's contents.* The corrected user-facing rule is "check the identity (domain) the certificate names, not the padlock", and the corrected engineering rule is that page-level safety requires the rest of the web-security stack: content-security policy to constrain script sources, subresource integrity for pinned third-party code, and the server-side input handling that TLS never touches. The misconceptions project treats the false claim in its own chapter; the repo's web-security page carries the defense catalog.

### Consequences

"Is it HTTPS?" is a compliance checkbox; "what runs in this origin?" is the security review. In interviews, the follow-up "phishing sites have valid certificates — what *does* the padlock buy you?" tests whether a candidate can state exactly what TLS guarantees and, just as important, what it does not.

## Assumption 2: "Math.random() Is Random Enough"

### The taught rule

`Math.random()` returns random numbers; use it to generate tokens, reset codes, session IDs, and shuffles.

### The hidden assumptions

- `Math.random()` is a pseudo-random number generator: a deterministic function of hidden internal state. MDN states directly that it does not provide cryptographically secure random numbers and must not be used for anything security-related; Python's random-module documentation carries the same warning and points security work at the `secrets` module; RFC 4086 defines the entropy requirements such generators must meet and PRNGs like these do not.
- The state is finite and recoverable: V8's own blog post ("There's Math.random(), and then there's Math.random()") documents that V8 implements `Math.random()` with xorshift128+ — a 128-bit-state generator chosen for speed and statistical quality, with the post itself noting the algorithm is unsuitable for cryptographic purposes. Statistical quality (passing test suites) and unpredictability to an adversary are different properties, and only the first is claimed.
- Token *space* matters independently of the generator: even a true RNG used to pick a 6-digit code offers one million possibilities, and online guessing makes that an arithmetic problem rather than a cryptographic one.

### Counterexample

A service generates password-reset tokens as `Math.floor(Math.random() * 1000000)` — a six-digit code. The guessing arithmetic is decisive: at 200 attempts per second against the un-throttled reset endpoint, an attacker covers the expected half of the space in about 2,500 seconds (42 minutes) and the full million-value space in 5,000 seconds (under an hour and a half) — verified arithmetic, no special tooling. Against the same endpoint using `crypto.getRandomValues()`-quality tokens but the same six-digit space, the identical attack works: the generator upgrade without the entropy upgrade changes nothing. And for the generator itself, public research has repeatedly demonstrated recovering xorshift128+ state from a modest run of consecutive outputs using SMT solvers — the 128-bit state is no hedge once outputs are observable (this is an interpretation of the documented research class; the V8 post's own caveat is the primary justification).

### What changes when the assumption is removed

Corrected statement: *security-sensitive randomness needs a CSPRNG seeded from the operating system's entropy pool (`crypto.getRandomValues`, `crypto.randomBytes`, Python's `secrets`), and its security is bounded by the token space and the online-guessing defenses, not by the generator's statistical quality.* Rule of thumb for the interview: the generator must make offline attacks the only avenue, and the token space must make even offline attacks hopeless — both statements quantified (128+ bits of space; rate limiting for the online side).

### Consequences

"Random enough for what?" is the interview question that exposes the assumption: shuffling a playlist and generating session tokens sit on opposite sides of the line, and candidates who can name the line (predictability to an adversary with observed outputs) and the right primitive per side demonstrate the model rather than the habit. The secrets-management page in the security track covers the storage and rotation half of the token lifecycle.

## Assumption 3: "Hashing Passwords With MD5/SHA Is Fine"

### The taught rule

Passwords must never be stored in plaintext, so hash them (MD5, SHA-1, SHA-256) and store the digest.

### The hidden assumptions

- General-purpose hash functions are engineered to be *fast* — gigabytes per second on CPUs, tens of billions of short-input hashes per second on GPUs. Password storage wants the opposite: deliberately slow, memory-hard computation so that offline guessing after a database theft is expensive.
- Salting defeats precomputed rainbow tables but not speed: each target's salt forces per-target computation, yet the attacker's GPU still evaluates candidates at full rate. Salt is necessary and nowhere near sufficient.
- MD5's cryptographic breakage (collision attacks demonstrated by Wang and collaborators in 2004; the Flame malware's forged certificate via an MD5 collision in 2012) is almost beside the point for password storage — the *speed* problem condemns every member of the fast-hash family, SHA-256 included.

### Counterexample

Order-of-magnitude arithmetic against a stolen unsalted-MD5 password table (benchmark classes, not a specific rig: modern GPUs crack MD5 at roughly 10¹⁰ short hashes per second; hashcat-published benchmark classes support this range). An 8-character lowercase password has 26⁸ ≈ 2.09×10¹¹ possibilities — exhaustible in about 21 seconds. The same table hashed with bcrypt at cost 12 (~250 ms per hash per CPU core — again an approximate, widely reported class figure) moves the same exhaustion to roughly 2.09×10¹¹ × 0.25 s ≈ 1,655 core-years: a slowdown factor near 10⁹, which is the entire game. OWASP's Password Storage Cheat Sheet (linked in the ledger) encodes the conclusion: Argon2id as the first choice with a memory/time/parallelism configuration it specifies, bcrypt with a work factor of at least 10, or PBKDF2 with hundreds of thousands of iterations where FIPS constraints apply — and explicitly not the raw fast hashes.

### What changes when the assumption is removed

Corrected statement: *password storage needs a password-hashing scheme — Argon2id, bcrypt, or scrypt/PBKDF2 — with per-user salts and parameters tuned so a single verification costs the tolerable latency ceiling (tens to a couple hundred milliseconds), because the hash function's job is to make offline guessing expensive after a breach, not to be fast.* Re-tune parameters as hardware improves; store the parameters alongside the hash so old entries can be upgraded on login.

### Consequences

The interview question "why is SHA-256 bad for passwords even though MD5's collisions don't apply?" has a two-sentence answer (speed and GPUs; collision resistance is irrelevant to offline guessing) that cleanly separates candidates who understand the threat model from those who memorized "MD5 broken". The repo's cryptography page develops the primitive families; the authentication page covers where the hash sits in the credential flow.

## Assumption 4: "Hidden Endpoint = Secure"

### The taught rule

Administrative endpoints are protected by obscurity: long URLs, unlinked pages, non-default ports, and names nobody guesses.

### The hidden assumptions

- Obscurity is not authorization: the secret is the *URL*, but URLs leak — referrer headers, browser history, proxy logs, link-sharing, source-code repos, JavaScript bundles, and vulnerability scanners that enumerate wordlists.
- Even a perfectly kept secret degrades statistically: any fixed secret URL is one screenshot, one log aggregate, or one departing employee away from public, and it has no revocation story.
- Access control is the mechanism with revocation, per-user identity, audit logging, and least privilege; obscurity has none of these properties and is not degraded gracefully when it fails — it fails completely.

### Counterexample

A staging admin panel lives at `/admin-7f3a9-panel/`, unlinked and firewalled from search engines. It is nonetheless indexed by an internal URL shortener, appears in a Git-tracked nginx config, and is referenced by a JavaScript error message; a contractor's browser sends it as a referrer to a third-party script. Three unrelated leaks later, the URL is in a public exploit scrape. Nothing about the panel's security changed — it never had any beyond the URL. The same endpoint behind authentication plus authorization returns 401 to everyone but the role, regardless of how the path leaked, and the leak becomes an incident footnote instead of a breach.

### What changes when the assumption is removed

Corrected statement: *every endpoint's security must reduce to authentication and authorization checks that fail closed; obscurity may be layered on top as friction, but it is never the control.* Deny by default (unknown routes, unknown roles, unknown methods), enforce authorization server-side per request, and audit-log administrative paths — so the design question "what happens when this URL leaks?" has the answer "nothing".

### Consequences

The penetration-testing genre's most reliable finding is an administrative surface whose only defense was its path; the interview probe "your admin panel is unlinked and has a random path — is it secure?" wants the answer "only by accident; here is the control that makes the path irrelevant". The repo's zero-trust pages carry the architectural version of this principle.

## Assumption 5: "Comparing Strings Is Comparing Strings" (Timing and Algorithm Confusion)

### The taught rule

Validate secrets with ordinary equality: `if (token == expected)` or `memcmp(a, b, n)`, and reject mismatched JWT signatures or API keys the same way.

### The hidden assumptions

- Byte-by-byte comparison implementations typically short-circuit at the first mismatch, so the comparison time depends on the length of the matching prefix. Under repeated measurement, that timing difference is a side channel that leaks the prefix itself.
- Verification code can trust the *attacker-selected* parameters of a token rather than the service's own configuration: the JWT algorithm-confusion class (RFC 8725's "Algorithm Verification" section names it as a best-current-practice violation) is exactly this — a verifier that reads the token header's `alg` and uses it lets an attacker present `alg: none` or swap an HMAC key for a public key, producing tokens the verifier accepts without any secret.
- Timing leaks are statistical, not boolean: network jitter buries one bit of difference, but aggregation over thousands of trials recovers it — the documented result of Crosby and Wallach's remote-timing-attack research, which is why the defense is algorithmic rather than "jitter will hide it".

### Counterexample

A token-validations endpoint compares a submitted secret against the stored value byte-by-byte with early exit. Measured over many requests, responses matching the first byte take measurably longer on average than those failing at the first byte; iterating the attack byte by byte reconstructs the secret without ever guessing it whole — the prefix-oracle mechanism Crosby and Wallach formalized for network-visible timing differences. The JWT variant needs no timing at all: a service configured for RS256 that selects the algorithm from the token header accepts an attacker-minted token labeled `alg: HS256` signed with the *public* RSA key (the verifier fetches the public key and uses it as the HMAC secret) — a documented confusion pattern that RFC 8725 §2.1 closes by requiring the verifier to check the algorithm against the key's expected type, never the reverse. Go's `crypto/subtle` package documentation states the purpose of constant-time primitives explicitly and exists because the correct comparison is not expressible in portable high-level code.

### What changes when the assumption is removed

Corrected statement: *secret comparison is a constant-time operation (`crypto/subtle`, `hmac.compare_digest`, `MessageDigest.isEqual`-style helpers), and token verification must pin the algorithm from configuration or key type — the attacker controls the token's header, so nothing in it can be trusted to configure its own verification.* The general form: validation logic must depend only on server-side configuration and cryptographic verification, never on attacker-supplied metadata.

### Consequences

Security code review gains two permanent checklist items from this section: "is every secret comparison constant-time?" and "where does the algorithm used to verify a credential come from?" Both are cheap to fix and expensive to discover, and both have canonical interview forms: "how would you compare two secrets?" and "what is JWT algorithm confusion?"

## Interview Questions

1. **A phishing site has a valid HTTPS certificate. What does the padlock actually guarantee, and what doesn't it?** It guarantees the hostname was validated by a CA and the transport is encrypted to that host. It says nothing about the operator's honesty, the page's code, or third-party scripts running in the origin — security on the page requires CSP, SRI, and server-side controls.
2. **Why can `Math.random()` output be predicted, and what are the two fixes for a reset-token system?** It is a deterministic PRNG (V8 uses xorshift128+ with 128-bit state) whose state is recoverable from observed outputs, and its statistical quality is not unpredictability. Fixes: a CSPRNG (`crypto.getRandomValues`/`secrets`) and enough token entropy plus rate limiting, since even a true RNG in a six-digit space falls to online guessing in under two hours.
3. **Why is SHA-256 wrong for password storage even though its collision resistance is fine?** Password hashing's threat is offline guessing after a breach; SHA-256 is engineered for speed, so GPUs guess billions per second (an 8-char lowercase space in ~21 seconds unsalted). Use Argon2id/bcrypt/scrypt/PBKDF2 with per-user salts and tunable cost — a ~10⁹× slowdown is the goal.
4. **Is an unlinked admin endpoint with a random path secure? What is the control?** No — URLs leak through referrers, logs, bundles, and screenshots, and obscurity has no revocation or audit story. The control is authentication plus authorization failing closed on every request; then the leak is harmless.
5. **Name two ways a JWT verifier can be tricked into accepting a forged token, and the BCP for each.** (1) Honoring the token's `alg` header — fixed by pinning the algorithm per RFC 8725's Algorithm Verification; (2) using a public key as an HMAC secret under `HS256` — fixed by binding key type to algorithm. And all secret comparisons (including signature checks) should be constant-time (`crypto/subtle`).

## Key Takeaways

- HTTPS authenticates a hostname and encrypts a transport — it is a precondition for web safety, not evidence of it.
- `Math.random()` is deterministic PRNG output unsuitable for security; CSPRNG from the OS entropy pool, plus a token space large enough that even offline attack fails, plus rate limiting online.
- Fast hashes verify data; password hashes resist GPUs — Argon2id/bcrypt with per-user salts and tunable cost, parameters stored alongside the hash.
- Obscurity is friction, not a control: every endpoint's security must reduce to fail-closed authn/authz so that a leaked URL is a non-event.
- Secret comparison is a timing channel; use constant-time primitives, and never let attacker-supplied metadata (the token's `alg`) configure its own verification.
- Each corrected statement here is cheap to implement and expensive to learn from incidents — the asymmetry is the reason this chapter exists.

## Cross-References

- [Cryptography](../../security/cryptography.md) — the primitive families (symmetric, asymmetric, hashing, KDFs) behind these rules.
- [Authentication](../../security/authentication.md) — where password hashes, tokens, and MFA fit the credential flow.
- [JWT internals](../../security/jwt-internals.md) — token structure, verification, and the algorithm-pinning details.
- [Web security](../../security/web-security.md) — CSP, SRI, and the origin-level defenses HTTPS does not provide.
- [Secrets management](../../security/secrets-management.md) — storage, rotation, and distribution of the secrets these schemes protect.
- [HTTPS means secure](../misconceptions/https-means-secure.md) — the misconception form of Assumption 1.
- [Heartbleed 2014](../failure-casebook/heartbleed-2014.md) — a transport-layer failure inside the TLS stack itself.
- [Input constraints](input-constraints.md) — the adversarial-input mindset that motivates most of these audits.
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — the parameter reference for password hashing.
- [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html) — Best Current Practices for JWT, including Algorithm Verification.
