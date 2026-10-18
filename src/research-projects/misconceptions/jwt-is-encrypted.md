# "JWTs are encrypted, so they are secure"

## Overview

The most consequential vocabulary error in web authentication is reading
a JWT as an encrypted container. A JSON Web Token is, in its common form,
three base64url-encoded segments joined by dots: a header, a payload of
claims, and a signature. Encoding is not encryption — anyone holding the
token can decode the payload in one line of code, and typically the only
cryptographic protection present is a signature (the JWS form), which
provides integrity and authenticity, not confidentiality. Encryption is a
different, rarer form (JWE) that most systems never use. This page audits
the claim, walks the anatomy that makes the payload world-readable, works
the classic attacks that a confused model invites — `alg=none` and
algorithm confusion — and delineates the claim from its two security
siblings in this collection. The verdict is false: the payload is
readable by anyone who obtains the token, and "encrypted" names a
protection the token usually does not have.

## The Claim, Stated Fairly

The strongest common form is: "We issue JWTs at login, so the session
data inside is protected — nobody can read or tamper with what we put in
the token." This deserves fairness, because the experience behind it is
real: a JWT is cryptographically protected in one specific sense. When
the token is signed (the ubiquitous JWS form) and the signature is
validated with an allowlisted algorithm, nobody without the signing key
can modify a claim without invalidating the token. Teams see tampering
attempts fail and generalize the protection to cover confidentiality
too.

The claim fails by conflating three different protections: encoding
(base64url, reversible by anyone, protects nothing), signing (integrity
and authenticity — the reader can trust *who* issued the token and that
it was not altered), and encryption (confidentiality — only key holders
can read the contents). JWTs are encoded by definition, usually signed,
and rarely encrypted. The rest of this page follows what each of those
words actually buys.

## Verdict

**False.** The JWT payload in the common JWS form is base64url-encoded,
which is a transport spelling, not a secret: anyone who obtains the
token — from browser storage, a log line, a Referer header, or a shared
machine — can read every claim, byte for byte. Confidentiality requires
the JWE form, which is uncommon in practice. Worse, a confused mental
model that treats the token as an opaque encrypted blob reliably invites
implementation bugs: validators that trust the token's own `alg` header
have historically accepted forged tokens under `alg=none` and under
algorithm-confusion attacks. The claim is not merely overstated; the
model it encodes produces the vulnerabilities.

## Why People Believe It

The kernel of truth is the signature. A validated JWS does give the
receiver real guarantees: the token was issued by whoever holds the
signing key and its claims have not changed since. That is a meaningful
security property, it is the one JWTs are designed to deliver, and it
works — tampering with a signed token in transit or in storage breaks
the signature and the session dies. An engineer who has watched forged
tokens rejected is watching genuine cryptography.

The compression error is a chain of two slippages. First, "protected"
slides from "cannot be tampered with" to "cannot be read" — the exact
confidentiality-versus-integrity conflation that this collection's
encryption audit dissects for ciphers in general. Second, base64url
looks like encryption to the untrained eye: the payload is an
impenetrable-looking string of letters, and the intuition "scrambled
therefore secret" completes the slide. Base64url is a bijective
spelling of the underlying bytes; it has no key, and "decryption" is a
one-call library function any holder of the string can run.

The third reason is architectural habit. Because the *server* validates
the token and the server holds the key, developers experience the token
as secure — from the server's side. The threat that breaks the claim is
client-side: the token sits in the browser (localStorage or a cookie),
travels in every request header, and lands in logs and analytics. Every
one of those locations is readable by XSS payloads, browser extensions,
proxies, and anyone with access to the machine. Confidentiality on the
server side of a channel does nothing for a secret whose ciphertext
(the token itself) the attacker can simply take home — except in this
case it is not even ciphertext.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "The JWT is encrypted" | The JWS form is base64url-encoded and signed; encoding is reversible by anyone, no key involved |
| "Nobody can read the claims" | Anyone with the token can decode header and payload; confidentiality requires JWE (RFC 7516) |
| "Tamper-proof" | True under JWS *if* validated correctly: allowlisted algorithm, checked signature, validated `exp`/`iss`/`aud` claims |
| "Signed means safe to put secrets in" | Wrong axis: signatures protect integrity; secrets in a readable payload leak to every holder |
| "The alg header tells the server what to do" | The header is attacker-controlled input; RFC 8725 requires an algorithm allowlist on the server side |
| "JWTs are bad then" | False — correctly validated JWS is a sound integrity mechanism; the error is expecting secrecy it never promised |

The corrected sentence: "A JWT is a signed (or, rarely, encrypted) set of
claims, encoded in base64url so it can travel in headers and URLs. The
signature lets the verifier trust the issuer and the contents; it gives
the *holder* no secrecy at all, so claims must be treated as readable by
anyone who can obtain the token, and the validation code must choose the
algorithm itself, not the token."

The anatomy makes this concrete. A typical token:

`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiIsInJvbGUiOiJhZG1pbiJ9.bOiu7WHYVq4UM1hFyLbo3ddJ4S56xf5mvUjvATklZDo`

The first segment decodes to `{"alg":"HS256","typ":"JWT"}`; the second
decodes to `{"sub":"42","role":"admin"}`. The third segment is the HMAC
signature — the only part whose verification requires a key. Two of the
three segments are plaintext by construction, and the standard `jwt.io`
debugger exists precisely because decoding them is trivial.

## Where It Breaks

**The readable payload.** A team embeds the user's email, role, tenant
ID, and entitlement list in the token, confident that "it is encrypted".
The token sits in localStorage; a marketing-site XSS payload exfiltrates
it; the attacker decodes the claims and now holds a structured
inventory of the user's permissions — before even attempting to *use*
the token. Confidentiality was never present to lose: every byte of the
payload was readable at every point in the token's life. The design
rule that falls out: put in claims only what you can accept being
public, because functionally it is.

**`alg=none`.** The token's header names the algorithm, and a validator
that obeys it will, for `{"alg":"none"}`, accept a token with an empty
signature section. An attacker takes a legitimate token, rewrites the
header to `none`, edits the payload (say, `"role":"admin"`), and sends
an unsigned token that a misconfigured library verifies successfully.
The 2015 wave of library vulnerabilities (Tim McLean's write-up is the
standard reference; CVE-2015-9235 tracks the `jsonwebtoken` Node family)
made this attack famous, and modern libraries reject unsigned tokens by
default — but the attack's persistence comes from its breeding
conditions: homegrown validators, proxies and gateways doing their own
verification, and code that passes the token's algorithm into the
crypto call instead of consulting a server-side allowlist.

**Algorithm confusion (RS256 → HS256).** The server signs tokens with
RS256 (asymmetric): the private key signs, and — crucially — the
public key is public by design. A validator that reads the token's
header and matches "algorithm" to verifier can be told `HS256`, where
HMAC takes a shared secret. The attacker supplies the *public key
bytes* as the HMAC secret, signs a forged token with them, and the
confused validator — which verifies HS256 tokens against the public
key it advertises — accepts. The "secret" was published on a
certificate endpoint; the forgery takes one script. RFC 8725's best
current practice exists largely to outlaw exactly this pattern: the
verifier's algorithm set is configured, not negotiated, per token.

**The validation that quietly does not happen.** The signature proves
issuer and integrity; it says nothing about freshness or audience.
Tokens without enforced `exp` (or with clock-skew-tolerant validators
that accept arbitrarily stale tokens), tokens whose `aud` is never
compared, and tokens accepted on endpoints they were not issued for are
all "valid" signatures over unacceptable sessions. And the revocation
story deserves its own sentence: a JWT is typically stateless, so
"logging the user out" means waiting for expiry unless the server keeps
state — the property that made the token convenient is the property
that makes it sticky after compromise. When it accidentally works: a
correctly configured JWS deployment — allowlisted algorithm, enforced
claims, short expiry — genuinely delivers tamper-evident,
issuer-authenticated sessions, which is the honest core of the belief.

## Practical Implications

- Treat JWT payloads as public: encode only identifiers and low-sensitivity
  claims; put entitlements server-side behind the identifier.
- Configure the verifier with an algorithm allowlist (RFC 8725); never
  pass the token's `alg` header to the cryptographic call.
- Enforce `exp`, `iss`, and `aud` on every validation, and pick an
  expiry that matches your revocation story — stateless tokens are
  unrevokable for their lifetime.
- If confidentiality is actually required, use JWE (RFC 7516) — or
  better, keep the sensitive data server-side and let the token carry
  only an opaque reference.
- Store tokens defensively: HttpOnly, Secure cookies over localStorage
  where the threat model includes XSS, and keep tokens out of logs and
  analytics pipelines, where their readable payloads leak as data.
- When auditing, decode every JWT in flight during a test: the payload
  inventory is the fastest way to find secrets teams believed were
  encrypted.

## Interview Questions

### What does a JWT actually protect, and what does it not?

A signed JWT (JWS) protects integrity and authenticity: the verifier
can trust the issuer and that claims are unmodified. It provides no
confidentiality — the payload is base64url-encoded and readable by
anyone holding the token. Confidentiality requires JWE. A strong answer
separates encoding, signing, and encryption as three different
protections and places the common JWT in the second category only.

### Walk me through the algorithm-confusion attack.

The server signs with an asymmetric algorithm (RS256) whose public key
is published. A validator that trusts the token's header is told the
token is HS256, so it verifies the HMAC using the *public key bytes* as
the shared secret. The attacker, who has the public key, forges any
payload and signs it correctly. The fix is structural: the verifier
uses a configured algorithm allowlist and never the token-supplied
`alg` — this is RFC 8725's core rule.

### Where should you put sensitive user data if not in the JWT?

Server-side, keyed by the token's subject — the token carries an opaque
identifier, and authorization data lives in your store where it can be
updated and revoked without reissuing tokens. If the payload must carry
sensitive claims, the token must be a JWE, accepting the operational
costs of key management and larger tokens. The anti-pattern is sensitive
claims inside a readable JWS payload.

### How is this misconception different from "encryption means tamper-proof"?

Different axes of the same family. The sibling audit covers systems
that *encrypt* and assume integrity follows — confidentiality does not
give tamper-resistance. This audit covers tokens that only *sign* and
assume secrecy follows — integrity does not give confidentiality. The
two audits are mirror images, and together they encode the lesson that
confidentiality and integrity are separate properties needing separate
mechanisms (AEAD, or sign-then-encrypt with care).

### A JWT travels over HTTPS and sits in the browser. Where has secrecy been lost?

HTTPS protects the token in transit, not the token itself — after TLS
terminates, the full payload is plaintext at the browser (devtools,
extensions, XSS), in proxy and server logs, and anywhere the token is
forwarded. This is the same boundary lesson as the padlock audit: a
transport guarantee covers one hop, and the artifact outlives the hop.
The design consequence is to treat every claim as public regardless of
how well the channel is protected.

## Key Takeaways

- JWT = encoded claims; JWS = signed; JWE = encrypted. The common JWT
  is the second: tamper-evident, world-readable.
- Base64url is a spelling, not a secret — no key, trivially reversible,
  and the payload is public by construction.
- The signature validates issuer and integrity only; validation code
  must enforce algorithm allowlists and `exp`/`iss`/`aud` itself.
- `alg=none` and RS256→HS256 confusion are the canonical bugs born from
  the confused mental model; RFC 8725 is the codified fix.
- Design rule: claims are public, so sensitive data lives server-side
  behind an identifier — or in a genuinely encrypted form if secrecy is
  required.

## Cross-References

- [Misconceptions: encryption-means-authenticated](./encryption-means-authenticated.md)
  — the mirror-image sibling, delineated in the text: encryption
  without integrity versus signature without secrecy
- [Misconceptions: https-means-secure](./https-means-secure.md) — the
  transport sibling: TLS protects a hop; the token outlives it
- [Connection Atlas: Auth, Identity & Sessions](../connection-atlas/auth-identity-session.md)
  — where tokens sit among sessions, cookies, and identity flows
- [Assumptions Hunt: Security & Crypto](../assumptions-hunt/security-crypto.md)
  — the hidden assumptions behind "it is encrypted, therefore safe"
- [Security: JWT Internals](../../security/jwt-internals.md) — the
  token format, validation mechanics, and pitfalls in depth
- [Security: Authentication](../../security/authentication.md) — the
  session-management context tokens operate in
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- M. Jones, J. Bradley, N. Sakimura. *JSON Web Token (JWT)*. RFC 7519,
  May 2015. <https://www.rfc-editor.org/rfc/rfc7519.html>
- M. Jones, J. Bradley, N. Sakimura. *JSON Web Signature (JWS)*. RFC
  7515, May 2015. <https://www.rfc-editor.org/rfc/rfc7515.html>
- M. Jones, J. Hildebrand. *JSON Web Encryption (JWE)*. RFC 7516, May
  2015. <https://www.rfc-editor.org/rfc/rfc7516.html>
- Y. Sheffer, R. Barnes, D. Hardt, P. Dickman. *Best Current Practices
  for JSON Web Token (JWT)*. RFC 8725, February 2020.
  <https://www.rfc-editor.org/rfc/rfc8725.html>
- T. McLean. *Critical Vulnerabilities in JSON Web Token Libraries*,
  2015 — the `alg=none` and algorithm-confusion write-ups, cited by
  title.
