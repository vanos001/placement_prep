# "It's encrypted, so it can't be tampered with"

## Overview

Encryption is the security control everyone can name, and "encrypted"
routinely gets treated as a synonym for "tamper-proof" and "authentic" in
design docs, code review comments, and interview answers. The three
properties are distinct, and the gap between them has a body count: attacks
that flip ciphertext bits, recover plaintexts one byte at a time through
error messages, and forge payments have all run against *unbroken*
encryption. This page audits the claim in its strongest common form — "it's
encrypted, so it can't be tampered with" — explains the malleability of
stream-cipher and CBC-mode encryption with worked examples, shows why
padding-oracle attacks turn integrity gaps into confidentiality failures,
and presents AEAD (GCM, ChaCha20-Poly1305) as the fix that folds integrity
into encryption itself. It closes by explaining the uncomfortable empirical
reason the myth survives: modern TLS always uses AEAD, so a working
developer may simply never encounter raw malleability.

## The Claim, Stated Fairly

The strongest common form is: "The data is encrypted, so an attacker who
intercepts it cannot modify it meaningfully — tampering would turn it into
garbage and the application would notice." The claim deserves fairness
because it encodes a real intuition with a real pedigree. A single flipped
bit in a naive encryption of a whole file does usually wreck that file, and
defense-in-depth folklore has taught for decades that encryption is the
heavy machinery of security. There is also a historical excuse: for most of
the 1990s the export-grade reality was that even confidentiality was hard
to get, so "we have encryption" was a meaningful upgrade, and the fine print
about integrity was rarely the binding constraint. The question is whether
"ciphertext looks random, so changes get detected" survives actual cipher
arithmetic.

## Verdict

**False.** Confidentiality and integrity are separate properties, and the
most widely deployed historical modes of encryption provide only the first.
Stream-cipher and CTR-mode ciphertext is *malleable by construction*: every
ciphertext bit flip flips exactly one plaintext bit, predictably and without
any key. CBC mode resists bit-level surgery but surrenders to padding
oracles, which decrypt messages through nothing more than a tamper-detect
error message. The industry's fix is not "add integrity as an extra habit"
but a different primitive class — authenticated encryption with associated
data (AEAD), mandatory in TLS 1.3 (RFC 8446) and specified as an interface
in RFC 5116. Encryption authenticates nothing; the authentication tag does,
and unauthenticated encryption does not have one.

## Why People Believe It

The kernel of truth is that careless tampering is usually caught. An
attacker who flips a random bit in an AES-CBC ciphertext of a whole-file
blob will, with high probability, corrupt half of one block and produce
plaintext garbage that a parser rejects. Experience teaches "changed
ciphertext fails loudly," and for whole-file encryption with internal
structure, that heuristic mostly works. The belief also rides on the
conflation of three words that security engineering deliberately separates:
*confidentiality* (the attacker cannot read), *integrity* (the attacker
cannot change undetected), and *authentication* (a holder of the right key
produced or endorsed this data). Encryption delivers the first only.

Three props hold the myth up. First, ciphertext genuinely looks fragile —
"it's random bits, touching them must break it" is an intuitive physical
model. The model is wrong in a specific, general way: in additive
stream-cipher modes the ciphertext is plaintext XOR keystream, so XORing
the ciphertext by a delta XORs the plaintext by the same delta, perfectly.
Second, modern developers meet encryption almost exclusively through TLS,
and TLS 1.3 + most TLS 1.2 suites are AEAD, so tampering *does* fail loudly
in their world — the protection is real, just not supplied by the
encryption they think they are praising. Third, integrity vocabulary is
genuinely confusing: MACs, tags, HMACs, checksums, and signatures all
sound like variants of one thing, so "encrypted" gets recruited as the
umbrella term.

What is lost is the attacker model. "Tampering" in the myth means clumsy
destruction. In the arithmetic, tampering means *controlled
transformation*: pay-to-attacker instead of pay-to-merchant, `is_admin =
true` instead of `false`, or a padding-error side channel that leaks the
plaintext itself. None of those require breaking AES.

## The Correct Formulation

| Property | Definition | Provided by plain encryption? | Provided by AEAD? |
|---|---|---|---|
| Confidentiality | Attacker cannot read plaintext without the key | Yes (if the cipher and mode are sound) | Yes |
| Integrity | Any modification is detected before use | No — ciphertext is malleable | Yes — the tag covers ciphertext and associated data |
| Authentication | Data was produced/endorsed by a key holder | No | Yes, for holders of the *shared* key; asymmetric endorsement needs signatures |

The precise statement: encryption protects content from *reading*;
authentication protects content from *changing*. AEAD modes — AES-GCM,
AES-CCM, and ChaCha20-Poly1305 — compute an authentication tag over the
ciphertext plus non-secret "associated data" (headers, version numbers,
record sequence numbers), so any bit changed anywhere in the covered data
fails the tag check at decryption time. Two operational rules follow.
First, the composition matters as much as the parts: encrypt-then-MAC is
the provably sound way to compose a cipher and a MAC (Bellare and
Namprempre, 2000), while the reverse order produced real TLS attacks.
Second, AEAD fails catastrophically in its own way: reusing a nonce in
GCM leaks the authentication key itself, so "upgraded to GCM" without
nonce discipline trades a malleability hole for a forgery hole.

## Where It Breaks

**Stream-cipher bit flipping, worked end to end.** Suppose a payment
message is encrypted with AES-CTR (a stream-cipher mode): the plaintext
block `transfer 100 to merchant` is XORed with a keystream block to make
the ciphertext. The attacker does not know the keystream — but does not
need to. XORing the ciphertext with a delta `d` at position `i` yields, at
decryption, plaintext XOR `d` at position `i`: flipping ciphertext bits
where "merchant" begins converts it, byte for byte, into "attackerX" — a
valid payment to the wrong party — with the decryption routine reporting
unqualified success. Every byte the attacker wants to change costs one
known plaintext byte to guess. This is not an exotic flaw; it is the
defining algebra of the mode, which is why CTR and ChaCha20 are specified
for use *only* inside AEAD constructions.

**The padding oracle: turning tamper-detection into decryption.** CBC
encrypts with padding at the end, and 1990s–2000s APIs reported "bad
padding" distinctly from "bad MAC". Vaudenay (2002) showed that this
error distinction is a decryption oracle: an attacker alters the
last-but-one block, submits the result, and uses the padding-valid or
padding-invalid answer to solve for a plaintext byte, byte by byte. The
class became practical web-scale history — POODLE (2014, against the
then-standard TLS CBC padding) and the Lucky 13 timing variant (2013)
both lived in this gap. The bitter lesson is exactly the misconception
inverted: the *tamper-detection failure mode itself* was the channel that
leaked plaintexts. RFC 8446's answer is structural: TLS 1.3 removed CBC
and all non-AEAD ciphersuites outright.

**When it accidentally works.** The myth's survival is well earned in one
specific regime: a developer whose only exposure to encryption is modern
TLS (or an AEAD library they call without knowing it) will flip no bits,
see no oracles, and enjoy real integrity — supplied by GCM or
ChaCha20-Poly1305 tags, not by the encryption they can name. The industry
did not so much disprove the belief as *meet* it: the fix was to make
encryption come with integrity built in, so the shorthand "encrypted means
protected" produces correct behavior by accident in default
configurations. The danger is precisely the boundary of that accident —
any hand-rolled composition (`AES-CBC` + no MAC, a non-AEAD
`crypto` call in a service, an old library default) exits the regime
silently, and nothing in the code signals that integrity just vanished.

**Integrity still is not authenticity.** Even with a perfect integrity
mechanism, one question remains: *whose* integrity? A MAC under a shared
key proves "someone holding the key produced this" — which is useless if
both parties hold the key and one is dishonest, and it offers no
non-repudiation. Only signatures (asymmetric) attribute a message to a
particular key holder. Design documents that say "encrypted, so
authentic" skip two rungs at once: integrity (tag or MAC) and
authentication (who held the key), and the second needs a key model,
not a cipher mode.

## Practical Implications

- Never deploy bare stream-cipher/CTR or CBC encryption for data an
  attacker can modify; reach for AEAD (AES-GCM, ChaCha20-Poly1305) as the
  default primitive, per the RFC 5116 interface.
- If forced to compose manually, encrypt-then-MAC, and authenticate the
  associated data too: protocol version, algorithm identifiers, sequence
  numbers, and headers are classic forgery targets left outside the MAC.
- Eliminate padding-oracle behavior: uniform error messages and uniform
  timing for "bad padding" and "bad MAC" — or better, remove padding from
  the trust boundary by using AEAD.
- Treat nonces as a correctness requirement, not a configuration detail:
  GCM with a repeated nonce leaks its authentication key; design nonce
  generation (counter or random with collision budget) before rollout.
- In design review, translate "it's encrypted" into the three questions:
  who can read it, who can change it undetected, and who vouches for it —
  and expect three different mechanisms as answers.

## Interview Questions

### An attacker flips one bit of an AES-CTR ciphertext. What happens at decryption, and what does that tell you about the mode?

Exactly one bit of the recovered plaintext flips, at the same position,
because CTR is plaintext XOR keystream and flipping ciphertext XORs the
resulting plaintext by the same delta; the cipher cannot detect it. The
lesson is that CTR provides confidentiality only, and must be paired with
an authentication mechanism (or used inside an AEAD mode such as GCM).
A strong answer distinguishes bit-flipping in stream modes from block
redirection in CBC.

### Why did TLS 1.3 delete CBC ciphersuites instead of fixing the error messages?

Because the failure was structural: encrypt-then-MAC ordering in TLS 1.2
was still followed by a padding check whose timing and error behavior
leaked (Lucky 13), and the MAC-then-encrypt composition that produced
Vaudenay's padding oracles (and POODLE) could not be fully sanitized at
the implementation layer. Removing CBC and making TLS 1.3 AEAD-only
(RFC 8446) deletes the attack surface class rather than patching each
side channel. The design point: choose compositions with proofs, and
when a composition keeps failing, remove it.

### Your service encrypts a session cookie with AES-CBC and no MAC. What are two concrete attacks?

First, bit-flipping-style block manipulation: the attacker who knows or
guesses one plaintext block can shift ciphertext blocks to move another
plaintext block into view (CBC's block-shuffle property), or corrupt
targeted bytes in the block that follows. Second, a padding oracle if
the application returns distinguishable errors for malformed padding:
the Vaudenay attack decrypts the cookie value-for-value through the
error channel. Fix: AEAD, or encrypt-then-MAC over the cookie with
associated data binding user and version.

### "The MAC proves the sender is authentic." Under what key model is that true, and when does it fail?

True for symmetric endorsement: all MAC key holders are trusted, and
any MAC verifies as "produced by a key holder". It fails in two common
cases: when the recipient also holds the key (so the MAC proves nothing
about *which* party sent it — no non-repudiation, and a malicious
recipient can forge third-party-looking messages), and when the same
key is shared across parties that should not be able to impersonate one
another. Attribution to a specific identity requires asymmetric
signatures with a key-to-identity binding, such as certificates.

## Key Takeaways

- Confidentiality, integrity, and authentication are three properties;
  encryption buys only the first. "Encrypted" never implies "tamper-proof".
- Stream-cipher and CTR modes are malleable by algebra: any ciphertext
  delta is a plaintext delta. CBC resists bit-flips but enabled the
  padding-oracle family (Vaudenay 2002, Lucky 13, POODLE 2014).
- AEAD (AES-GCM, ChaCha20-Poly1305; RFC 5116 interface) is the correct
  primitive: one operation delivers confidentiality plus a tag covering
  ciphertext and associated data — with nonce reuse as its own hard
  failure mode.
- Encrypt-then-MAC is the sound manual composition; MAC-then-encrypt is
  the composition that produced two decades of TLS attacks.
- The myth survives because default TLS is AEAD everywhere — integrity
  arrives as an invisible rider on encryption. The moment you compose
  primitives by hand, the rider is gone.

## Cross-References

- [Misconception: The Padlock Means This Site Is Safe](./https-means-secure.md)
  — the sibling TLS-adjacent myth: what the certificate and the channel
  each do and do not vouch for
- [Assumptions Hunt: Security & Crypto](../assumptions-hunt/security-crypto.md)
  — the hidden assumptions packed into "we use encryption" claims
- [Misconception: Checksums Match, So the File Is Intact](./crc-equality-means-file-equality.md)
  — error detection versus cryptographic integrity versus authenticity,
  the non-adversarial cousin of this page
- [Cryptography](../../security/cryptography.md) — the book's treatment
  of ciphers, MACs, hashes, and their compositions
- [HTTPS](../../networks/http/https.md) — the protocol context in which
  AEAD became the invisible default
- [mTLS](../../security/mtls.md) — authentication as a *peer* property,
  which no cipher mode supplies by itself

## References

- J. Rizzo, T. Duong, and K. Bödh. *The POODLE Attacks: SSL 3.0 CBC
  Padding* (2014), cited by title (the CBC padding attack that ended
  SSL 3.0).
- N. J. AlFardan and K. G. Paterson. *Lucky Thirteen: Breaking the TLS
  and DTLS Record Protocols*. IEEE S&P 2013, cited by title.
- S. Vaudenay. *Security Flaws Induced by CBC Padding — Applications to
  SSL, IPSEC, WTLS...*. EUROCRYPT 2002, cited by title.
- M. Bellare and C. Namprempre. *Authenticated Encryption: Relations
  among Notions and Analysis of the Generic Composition Paradigm*.
  ASIACRYPT 2000, cited by title (the encrypt-then-MAC result).
- D. McGrew and J. Viega. *The Galois/Counter Mode of Operation (GCM)*.
  NIST SP 800-38D, cited by standard name.
- Y. Nir and A. Langley. *ChaCha20 and Poly1305 for IETF Protocols*.
  RFC 8439, June 2018. <https://www.rfc-editor.org/rfc/rfc8439.html>
- D. McGrew. *An Interface and Algorithms for Authenticated Encryption*.
  RFC 5116, January 2008. <https://www.rfc-editor.org/rfc/rfc5116.html>
- E. Rescorla. *The Transport Layer Security (TLS) Protocol Version 1.3*.
  RFC 8446, August 2018 (AEAD-only record layer, CBC removal).
  <https://www.rfc-editor.org/rfc/rfc8446.html>
