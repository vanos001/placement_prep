# Follow-up Tree: JWT Authentication

## Overview

"What is a JWT?" is the standard opener for any auth-flavored round, and it escalates faster than almost any other security question because the rehearsed answer hides three separate claims — about cryptography, about state, and about trust — that each fall apart under one follow-up. The ladder here runs from the token's anatomy through the signed-versus-encrypted distinction, into the "stateless authentication" claim that senior interviewers love to probe, and finally to the operational rungs where production systems actually get hurt: revocation, key rotation, and algorithm confusion. The thread tying every rung together is *where the state lives and who vouches for it*: a JWT moves trust from a shared session store into a signature, and every design decision that follows — expiry windows, refresh tokens, denylists, key distribution — is a consequence of that move. This chain stays at the authentication and token-design layer; the book-level mechanics of signature schemes and password handling live in [JWT Internals](../../security/jwt-internals.md), [Authentication](../../security/authentication.md), and [Password Hashing Choices](../why-not-handbook/password-hashing-choices.md). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"What is a JWT?"**

The expected core answer: a JSON Web Token is a compact, URL-safe string of three dot-separated, base64url-encoded segments — header, payload (the "claims" set), and signature. The header names the signing algorithm and key id; the payload carries claims such as `iss` (issuer), `sub` (subject), `aud` (audience), `exp`, `iat`, and custom application claims; the signature is computed over header-plus-payload with a key the verifier trusts ([RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html) defines the format; [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html) defines the JWS signature wrapper it almost always rides in). The verifier re-computes the signature, checks the registered claims, and treats the payload as a statement the issuer vouched for.

A weak answer says "a token with user info inside" and stops. The strong answer names all three segments, distinguishes *integrity* (nobody altered the claims without the key) from *confidentiality* (nobody can read them), and volunteers that the encoding is base64url — visible to anyone who holds the string, not encrypted. The follow-up that escalates: **"Who can read the payload, and who can forge it?"** — which moves the ladder from anatomy to trust.

## Level 2: Signed, Not Encrypted

**What it tests:** whether the signature/encryption distinction is a mechanism you can decompose or a slogan you recited.

**Weak answer:** "JWTs are secure because they're encrypted" — conflates encoding with encryption, cannot name who can read or write the payload, and has never heard of JWE.

**Strong answer:** states that the standard JWT is a JWS — readable by anyone, unforgeable without the key — that confidentiality requires JWE (an encrypted variant most systems do not use), and that the two signature families have different trust models: HMAC (HS256, shared secret — anyone who can *verify* can also *forge*) versus asymmetric signing (RS256/ES256, private key signs, public key verifies — verification can be delegated widely).

**Escalation trigger:** "Your auth server signs with RS256. Why does it matter that your downstream services only hold the public key?"

**Answer.** Because the key distribution shape *is* the trust boundary. With HS256, every service that can check a token also holds the secret that can mint one, so handing a read-only verifier role to twelve microservices gives all twelve minting power — a compromise of any one of them is a compromise of the issuer. With RS256, the private key lives on the issuer alone and verifiers hold the public half: they can check signatures forever and still cannot produce a valid token. That asymmetry is why token verification can be pushed to the edge (gateways, every service independently) without a round trip to the auth server, and it is the mechanical reason the industry moved from shared-secret API-key-style schemes to signed tokens for service-to-service trust. The failure mode that follows — verifiers trusting a public key they fetched from the wrong place, or accepting an attacker-chosen algorithm — is precisely the rung below.

The design twist the strong candidate volunteers: *payload readability is often a feature, not a bug.* Debugging a login failure becomes "paste the token, read the claims," and services can route on payload content without a lookup. But the same property leaks anything sensitive placed carelessly into claims — PII in a URL-parameter token shows up in browser history, proxy logs, and crash reports. The misconception version of this exact confusion is documented in [JWT Is Encrypted](../misconceptions/jwt-is-encrypted.md), and the broader crypto-assumption list — "signed means authentic," "hashed means safe to compare" — lives in [Security & Crypto Assumptions](../assumptions-hunt/security-crypto.md). The follow-up that escalates: **"If the token carries the session, where did the session state go?"**

## Level 3: The Stateless Myth, Expiry, and Refresh

**What it tests:** whether "JWT auth is stateless" is a claim you can defend precisely — or a marketing sentence that collapses when asked how logout works.

**Weak answer:** "JWTs are stateless so there's no session storage and it scales infinitely" — no accounting for where revocation lists, key material, and refresh tokens live, and no cost attached to `exp`.

**Strong answer:** states that JWT auth does not eliminate session state, it *relocates* it: the session record in a shared store becomes the signed claim plus the issuer's signing key, and whatever the token asserts is true until `exp` because no one can cheaply unsay it. Then it names the compensating machinery — short access-token lifetimes plus refresh tokens — and the clocks involved.

**Escalation trigger:** "Access tokens live 10 minutes and refresh tokens live 30 days. Explain the exact thing each one buys, and what a stolen refresh token is worth."

**Answer.** The split is a bet on detection time. The access token is short-lived *because* it is unrevokable: the `exp` claim is the only mechanism that ever retires a stolen access token, so its lifetime is the maximum damage window, and everything in it must be true-or-tolerable for that window (user id, roles, tenant). The refresh token is long-lived but is expected to live server-side: presented only to the issuer over TLS, stored hashed at rest, and — in the stronger design — rotated on every use, so a replayed refresh token is evidence of theft and the whole family is revoked. That rotation converts the refresh token from a bearer credential into a liveness check. The cost ledger earns credit: every authenticated request now carries a token-exchange cycle on expiry, clock skew between issuer and verifier becomes a real failure (`nbf`/`exp` checks fail on drift — the general clock problem is [Clocks and Time](../assumptions-hunt/clocks-and-time.md)), and "stateless" services still need distributed, coordinated key management. The honest sentence: state was not eliminated; it was compressed into a signature and moved to the places that mint and rotate keys.

The senior framing: choose per-system. Long-lived opaque session cookies are the right answer when revocation dominates (admin consoles, banking); short JWTs are right when verification fan-out dominates (many independent services, edge-validated traffic) and the revocation requirement is coarse. The follow-up that escalates: **"The CISO says users must be logged out everywhere within seconds. What actually implements that?"**

## Level 4: Revocation, Key Rotation, and Algorithm Confusion

**What it tests:** the expert rung — the mechanisms that quietly reintroduce server state (denylists, JWKS) and the parser bugs that turn a token format into an exploit.

**Weak answer:** "You put revoked tokens in a database" — which re-creates a per-request lookup against every token and misses the two systematic bugs: key rotation without `kid`, and algorithm-confusion attacks.

**Strong answer:** separates three revocation needs with three mechanisms: *kill a token* (short `exp` makes this mostly unnecessary — denylist only the exception cases), *kill a family* (refresh-token rotation with reuse detection), *kill everything signed by a key* (rotate the signing key and let old signatures fail validation), and then explains JWKS: the issuer publishes public keys at a well-known URL, tokens carry a `kid` header, and verifiers fetch and cache the key set so rotation becomes a config change, not a deploy.

**Escalation trigger:** "Where can a JWT implementation go catastrophically wrong, even with a correct design?"

**Answer.** The canonical attacks are verifier bugs, not crypto breaks. Algorithm confusion: a verifier that reads the `alg` header and dispatches on it can be told to verify an RS256-intended token as HS256 — checking the signature with the *public key* as the HMAC secret, which the attacker knows because public keys are public. The fix is policy, not parsing: verifiers pin the allowed algorithms and ignore the header's suggestion — the exact discipline of [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html), the JWT Best Current Practices. The `alg: none` family is the same lesson historically: an optional signature is an unverified one, so a verifier that tolerates missing signatures accepts forgeries. Beyond algorithms, claim hygiene earns the top rung: `aud` must be checked (a token minted for service A must not pass validation at service B), `iss` must match a configured issuer, and `jti` exists so single-use semantics can be enforced when needed. Key rotation closes the loop: JWKS caching with a grace window lets old-key tokens finish their lifetime, and it forces the design question of *who fetches the key set* — a verifier that fetches on every request has rebuilt a per-request dependency on the auth server, recreating the availability coupling signatures were meant to remove.

The judgment sentence that ends the chain well: JWTs buy *decentralized verification* and pay in *centralized revocation*; the moment your requirements weight revocation heavily, either shorten lifetimes until the math works or move back to opaque tokens backed by a session store — and say which you would measure to decide (median damage window of a stolen token vs p99 added latency of a session lookup).

## How to Approach Unfamiliar Variations

The template for token variations — "what about mTLS between services," "should the gateway verify or just forward," "why did the client get 401 at noon but not at 9":

1. **Ask what the token asserts, and who is vouching.** Every variation — opaque session id (asserts "look it up"), JWT (asserts signed claims), mTLS certificate (asserts a CA-vouched identity) — changes the voucher and the verification site. Name both, then the consequence for revocation.
2. **Answer state questions with a map of where state lives.** Signing key, JWKS cache, refresh-token store, denylist, clock skew tolerance: five pieces of state hide inside "stateless" auth. Any proposed change moves one of them; draw the map before answering.
3. **Treat every lifetime as a damage window, and every rotation as a detection mechanism.** Short-lived unrevokable plus long-lived rotatable is the default split; deviations must say which side they are optimizing.
4. **Verifier bugs beat crypto breaks.** When asked "is it secure," enumerate what the verifier enforces: pinned algorithms, `aud`/`iss` checks, expiry, signature-required. The attacks in the wild (alg confusion, `none`, missing audience checks) are all verifier-side.

## Interview Questions

**Q: Your team ships JWT logout by deleting the token from the client's localStorage. What does this actually achieve?**
A: Almost nothing security-wise — a copied token still validates until `exp`. Real logout needs either a short enough `exp` that the window is acceptable, a server-side denylist for the exceptional revokes (compromise reports, admin bans), or refresh-token revocation at the issuer so the client cannot mint replacements. The client-side delete is UX hygiene, not revocation; saying which layer each action secures is the senior answer.

**Q: Why do access and refresh tokens have different lifetimes, and what breaks if you set both to 30 days?**
A: The access token's lifetime is the unrecoverable damage window for a stolen token — it cannot be revoked, only expired. At 30 days, every theft is effectively a month of access unless you add a denylist, which reintroduces the state you removed. The refresh token at 30 days is acceptable *only* with rotation and reuse detection, because it lives server-side and can be revoked by the issuer. Equal lifetimes collapse the two-token bet into the worst of both.

**Q: A verifier accepts tokens signed with either HS256 or RS256, chosen from the token header. Describe the attack.**
A: Algorithm confusion. The attacker takes a token the issuer would sign RS256, changes the header to HS256, and signs it with the RSA *public key* treated as an HMAC secret — public keys are public, so the attacker can compute it. The verifier dispatches on `alg`, verifies successfully, and accepts the forged token. The fix per RFC 8725 is to pin the algorithm set per issuer and never let the token choose its own verification method.

**Q: When would you deliberately choose opaque session tokens over JWTs?**
A: When revocation granularity dominates verification fan-out: an admin panel or banking app wants "terminate this session now" semantics, and a per-request session lookup is a trivially cheap p99 cost at that traffic level. JWTs earn their complexity when many independent services must verify without a shared store, and the revocation requirement is coarse. The deciding metric is damage window of a stolen credential versus added latency of a central lookup.

## Key Takeaways

- A JWT is signed, not encrypted: anyone can read it, only key-holders can forge it, and HS256 versus RS256 changes who can mint versus who can verify.
- "Stateless" is a relocation claim, not an elimination claim — the state moved into the signing key, the JWKS cache, the refresh store, and the expiry windows.
- Short access tokens plus rotated refresh tokens is a bet on detection time: the access token's `exp` is the only revocation it will ever get.
- Revocation is three different problems — kill a token, kill a family, kill a key — and each has its own mechanism; a global denylist is the blunt fallback.
- The production JWT bugs are verifier bugs: algorithm confusion, `alg: none`, unchecked `aud`/`iss`. Pin algorithms and claims; never let the token pick its own verification.

## Cross-References

- [JWT Is Encrypted](../misconceptions/jwt-is-encrypted.md) — the misconception behind "nobody can read my payload," documented and dismantled.
- [Security & Crypto Assumptions](../assumptions-hunt/security-crypto.md) — the hidden assumptions ("signed means authentic") that JWT bugs exploit.
- [Password Hashing Choices](../why-not-handbook/password-hashing-choices.md) — the complementary credential-side decision: what to do with the password before any token exists.
- [Auth, Identity & Session](../connection-atlas/auth-identity-session.md) — the cross-system map connecting login, tokens, cookies, and service identity.
- [API Gateway](./api-gateway.md) — where token verification is usually placed, and the blast radius of that placement.
- [TLS Handshake](./tls-handshake.md) — the transport trust layer underneath token delivery; attacker-readability of tokens assumes this layer holds.
- [JWT Internals](../../security/jwt-internals.md) — the book-level treatment: header/claim tables, JWE, and library behaviors.
- [OAuth2 Internals](../../security/oauth2-internals.md) — the authorization framework that issues these tokens and defines the refresh flow.
- [Clocks and Time](../assumptions-hunt/clocks-and-time.md) — why `exp`/`nbf` checks are a distributed-clock problem, not just a comparison.
- [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html), [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html), [RFC 7517](https://www.rfc-editor.org/rfc/rfc7517.html), [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html) — JWT format, JWS signing, JWK key format, and the JWT Best Current Practices.
