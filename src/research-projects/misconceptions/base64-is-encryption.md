# "It's base64-encoded, so it's encrypted"

## Overview

This page audits the oldest cipher-confusion in software: the claim that
base64 encoding protects data, heard as "the password is base64-encrypted in
the config", "the license key is safe because it's base64", or "the JWT
payload is opaque". The confusion is structural rather than careless:
ciphertext and base64 output both look like scrambled noise to a human
glancing at a config file, so the eye generalizes "unreadable to me" into
"unreadable". But base64 is an *encoding* — a keyless, deterministic,
reversible rewriting of bytes defined in RFC 4648, invented so that octets
survive channels that mangle raw binary, such as mail gateways, URLs, and
JSON strings. It has no key, no key space, no security parameter, and no
secrecy goal; its inversion is a fixed table lookup that takes microseconds.
Encryption, by contrast, is a *keyed* transformation whose defining property
is that inversion without the key is computationally infeasible. This page
states the claim fairly, separates the three transformations it merges
(encoding, encryption, hashing), and runs the one-command disproof that has
ended this argument in every code review where it was actually tried.

## The Claim, Stated Fairly

The strongest common form is: "We store the API key base64-encoded in the
database, so even if the database is dumped the key is protected; base64 is
a standard encryption scheme and attackers would need to break it." Stated
this way, the claim is not a strawman. It appears in real schemas from
production systems, in onboarding documents that call the encoding step
"encryption", in interview answers from candidates who were taught the word
incorrectly, and in log-redaction tickets where "it's already encoded" was
accepted as "it's not plaintext".

The kernel deserves fairness too, and history supports it: base64 was
standardized for MIME so attachments would survive mail gateways that
only passed seven-bit text, and it remains the standard armoring for
binary data inside JSON, HTTP headers, cookies, and data URLs. Base64
does solve a real problem, and the people who reach for it are usually
trying to solve exactly that problem: moving bytes through a text-only
channel without corruption. A PNG attachment in a MIME mail, a binary
session ticket inside an HTTP cookie, a SHA-256 digest inside a JSON
field — all of these need base64 or they will be mangled by layers that
assume text. The failure is not in using base64; it is in reading
"protected from mangling" as "protected from reading".

## Verdict

**False.** The claim is contradicted outright: base64 decoding is a
deterministic, unkeyed transformation, so any party who can read the
encoded bytes can read the original bytes with one command and no search.
There is no configuration, key length, or usage pattern that changes this,
because secrecy is not a property the format attempts to provide. RFC 4648
defines base64 purely as a representation for carrying octets through
systems that mishandle binary — it specifies an alphabet and padding, and
its security-relevant text is about padding errors, not adversaries. The
claim becomes dangerous whenever it closes a threat-model question ("is the
credential exposed?") with an encoding answer.

## Why People Believe It

Three forces keep this claim alive. First, the outputs rhyme. Ciphertext and
base64 are both ASCII soup to a human reader, and perception is the only
instrument most people apply: if it looks scrambled, it is scrambled.
Ciphertext, however, is scrambled *as a side effect of a keyed permutation*
whose inversion is hard, while base64 is scrambled as a side effect of a
base conversion whose inversion is a table lookup. Same eye, opposite
security.

Second, the vocabulary is genuinely slippery in older literature. Tutorials
from the 2000s — and more than one certification guide — describe base64 as
"encryption" or "weak encryption", and the word stuck in job titles,
questionnaires, and schema comments. Once a codebase's own documentation
says `-- encrypt the token`, the next reader inherits the frame.

Third, base64 usually appears *near* real cryptography, which lends it
borrowed credibility. JWTs carry their payload base64url-encoded next to a
real cryptographic signature; TLS certificates are base64-wrapped DER next
to real signatures; encrypted blobs are base64-armored for transport. The
encoding is the envelope around the protection, and the envelope absorbs the
credit. The effect is strong enough that the claim survives even among
engineers who could define a block cipher on demand.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Encoding" | A keyless, deterministic, reversible byte rewriting; anyone can invert it; goal is representation fidelity |
| "Encryption" | A keyed transformation; inversion without the key is computationally infeasible; goal is confidentiality |
| "Hashing" | A one-way digest; no inversion at all (only guessing plus comparison); goal is integrity verification and password verifiability |
| "Base64 is weak encryption" | It is not encryption at any strength; it has no key, so there is nothing to break — and nothing to slow an attacker down |
| "It looks random" | Human unreadability is not secrecy; a machine inverts base64 in microseconds |
| "What base64 is for" | Carrying binary through text-only channels (mail, URLs, JSON); it adds 33% size overhead (3 bytes become 4 characters) and zero secrecy |

The correct sentence: "Base64 changes how bytes are written, not who can
read them; encryption changes who can read them; hashing makes reading
irreversible. If the requirement is that a database dump must not reveal the
key, base64 contributes nothing — the requirement needs a key management
service or a password-hashing function, depending on whether the data must
be recoverable."

## Where It Breaks

**The one-command disproof.** Take the "protected" credential from the
schema in the claim:

```bash
echo 'cGFzc3dvcmQxMjM=' | base64 -d
# output: password123
```

No key, no wordlist, no compute. The `base64` utility ships in every
operating system, every language runtime has a one-line decoder, and many
log viewers decode on the fly. Multiply by a breach: a dump of 10 million
rows with base64'd passwords yields 10 million plaintexts in the time it
takes to run one script — this is precisely why historical incidents
involving "encoded" credential stores are indistinguishable from plaintext
stores in their impact. The encoding bought a 33% size increase and no
resistance.

**The JWT envelope is readable by construction.** A JSON Web Token's middle
segment is base64url encoding (RFC 4648 Section 5) of the claims JSON, and
it decodes in any browser console or with `cut` and `base64 -d` on the
command line. The token's protection is its signature — which proves
integrity and identity, and provides zero confidentiality, which is why the
sibling page on JWTs exists. When a team "encrypts" a session by putting it
in a JWT, they have published the session contents to anyone who receives
the token, with a cryptographic proof that the published contents are
genuine.

**The keyspace argument, stated as arithmetic.** Every cipher's security is
a number: the size of the key space an attacker must search. AES-128 offers
2^128 keys; a good password hash offers work-factor scaling on top of its
key space. Base64's security parameter is 0 bits — there is no key, so
there is nothing to search, and "breaking" it is not a search problem but a
definition problem. This is the cleanest interview formulation: an encoding
moves the adversary's cost to zero because there is no unknown; an
encryption moves the adversary's cost to 2^n because there is one.

**The inverse harm: encoding defeats the leak detectors.** A side effect
rarely priced into the claim: organizations that base64 credentials "for
safety" also tend to grep their logs and repositories for plaintext
secrets, and the encoded form sails past every scanner tuned to the raw
value. The result is the worst of both worlds — no protection against an
adversary (who decodes in one command) and degraded detection against
the accidental leak (a debug log containing `cGFzc3dvcmQxMjM=` matches
nothing in the secret-detection ruleset). Encoding a secret does not
merely fail to protect it; it can actively hide the secret from the
tooling whose job is noticing exposure. Any log-redaction or
secret-scanning rollout must therefore decode-and-match, or the encoded
copies become the durable blind spot.

**Where each transformation actually belongs.** The honest usage table:
binary over text channels — base64; confidentiality against a reader —
authenticated encryption with a key from a KMS; stored passwords that must
be checked but never recovered — a salted, memory-hard password hash
(bcrypt, scrypt, argon2); integrity of a message — a MAC or signature.
Notice that the encoding never appears on the confidentiality row, and that
the three transformations are composable: an encrypted-then-encoded token
uses both, and neither substitutes for the other. The claim fails because
it substitutes the cheapest, keyless member of the family for the keyed one.

**Why the confusion is so durable in review.** The encoded value passes
every superficial test a reviewer applies: it does not grep as plaintext,
it does not appear in logs as the raw secret, pasting it into the
application works. Every one of those tests measures *human* readability,
and none measures *machine* recoverability. The fix is procedural, not
technical: security review questions ask "what is the key and where does it
live?", and any transformation proposed as protection that cannot answer
that question is an encoding.

## Practical Implications

- In threat models and questionnaires, replace "is it encoded?" with "what
  is the key, where is it stored, and who can call decrypt?" — any answer
  without a key is an encoding.
- Treat base64 in credential stores, license checks, and "hidden" API
  parameters as plaintext with extra steps when assessing exposure; size
  the incident accordingly.
- Use base64 for its actual purpose without apology: binary payloads in
  mail, cookies, JSON, URLs (base64url), and protocol armoring — and note
  the 33% size overhead when capacity planning.
- For stored passwords, use a salted, memory-hard hash; for recoverable
  secrets, use a KMS; for tokens that must be readable but tamper-evident,
  sign — and document which guarantee each layer provides.

## Interview Questions

### An interviewer asks whether base64 encoding provides any confidentiality. What is the precise answer?

None. Base64 is a keyless, deterministic, reversible encoding defined in
RFC 4648; anyone holding the encoded bytes can invert it with a table
lookup. Its security parameter is zero — there is no key space to search.
What it provides is representation fidelity for binary data across
text-handling layers, at a 33% size cost. Confidentiality requires a keyed
transformation: authenticated encryption for data, a memory-hard hash for
passwords that are checked but never recovered.

### A config file stores a database password as `cGFzc3dvcmQxMjM=`. Is this a finding, and how severe?

Yes — effectively plaintext storage. The value decodes to `password123`
with one command, so an attacker with file read access (or a repository, or
a support bundle containing the config) has the credential. Severity is the
same as a plaintext-password finding; the encoding adds no mitigation. The
remediation is a secrets manager or environment-scoped credential with
rotation, not a stronger encoding.

### Why do JWTs base64url-encode their payload if it is not meant to be secret?

Because JWTs are containers whose security goal is integrity and
authenticity, not confidentiality: the signature covers the exact payload
bytes, and encoding makes those bytes safely transportable in HTTP headers
and URLs. Anyone holding the token can read every claim. Confidentiality
would require JWE (encrypted JWT) with a real key, and even then the
encoding remains just transport. The design choice is deliberate: most
token consumers need to inspect claims without a key.

### Name the three transformations — encoding, encryption, hashing — and one sentence each on their guarantee.

Encoding rewrites bytes deterministically with no key; anyone can invert
it, and the guarantee is fidelity across channels. Encryption rewrites
bytes under a key; without the key inversion is infeasible, and the
guarantee is confidentiality (with AEAD, integrity too). Hashing maps
input to a fixed-size digest irreversibly; the guarantee is that a
verifier can check equality without storing the input, which is why
passwords are hashed and files are fingerprinted.

## Key Takeaways

- Base64 is a keyless, deterministic, reversible encoding; its purpose is
  byte fidelity over text channels, and its secrecy contribution is zero.
- "Looks scrambled" measures human readability, not machine
  recoverability; `base64 -d` is the entire attack.
- The family is encoding (representation), encryption (confidentiality
  under a key), hashing (irreversible verification); no member substitutes
  for another, and base64 is the only keyless one.
- JWT payloads are base64url-encoded by design: readable to everyone,
  protected by signature, confidential only under JWE.
- In reviews, the operative question for any "protected" blob is where the
  key lives; a transformation with no key is an encoding and provides no
  confidentiality.

## Cross-References

- [Misconception: "It's encrypted, so it can't be tampered with"](./encryption-means-authenticated.md)
  — the sibling conflation on the integrity axis: that page shows
  confidentiality not implying tamper-resistance, this one shows encoding
  not implying confidentiality; both fail by smuggling a second property
  into one word.
- [Misconception: "JWTs are secure because they're encrypted"](./jwt-is-encrypted.md)
  — the token-shaped instance of this claim: a signed JWT is base64url
  encoding plus a signature, readable by anyone holding it.
- [Assumptions Hunt: Encodings & Text](../assumptions-hunt/encodings-and-text.md)
  — the hidden-assumptions sweep for "the bytes sent are the bytes that
  are", the transport-side twin of this confidentiality claim.
- [Why-Not Handbook: Password Hashing Choices](../why-not-handbook/password-hashing-choices.md)
  — what should stand where the claim wants base64: the parameters and
  trade-offs of password-hashing functions.
- [Security: Cryptography](../../security/cryptography.md) — the mechanics
  of keyed transformations that actually deliver the guarantee the claim
  borrows.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- S. Josefsson. *The Base16, Base32, and Base64 Data Encodings*. RFC 4648,
  October 2006 — the specification, whose stated purpose is representation
  of octets in a character alphabet, not secrecy.
  <https://www.rfc-editor.org/rfc/rfc4648.html>
- M. Jones, J. Bradley, N. Sakimura. *JSON Web Token (JWT)* — cited by
  title; defines the base64url-encoded segments whose readability the
  sibling misconception mislabels as encryption.
