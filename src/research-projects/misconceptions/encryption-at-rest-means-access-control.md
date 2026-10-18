# "The data is encrypted at rest, so access is controlled"

## Overview

This page audits one of the most common lines in compliance documents and
architecture reviews: the claim that because a database, bucket, or volume is
"encrypted at rest", access to the data is therefore controlled. The reality
is a clean separation of concerns that the sentence quietly deletes:
encryption at rest protects the *medium* — it defends against someone
acquiring a disk, a snapshot, a backup tape, or a decommissioned SSD. Access
control is a *policy* question — it is decided by the authorization layer
that decides who may ask the database for the data, and by key management,
which decides who may ask the key service for the key. Anyone holding valid
application credentials walks through the encryption as if it were not there,
because the running application decrypts on their behalf all day long. This
page states the claim fairly, separates the two protections it merges, and
works the credential-theft counterexample end to end.

## The Claim, Stated Fairly

The strongest common form of the claim is: "We enabled encryption at rest on
the database and object store, so the data is access-controlled; a leaked
credential or an over-broad role is not a data-exposure risk because the
attacker would only get ciphertext." Stated this way, the claim is not a
strawman — it appears in security questionnaires, in audit defenses ("we have
AES-256 at rest, so we are compliant on data protection"), and in the
reasoning of engineers who conflate the security controls slide with the
authorization matrix.

The claim deserves its fairness because the kernel is real. Encryption at
rest is a genuinely valuable and genuinely required control: it defeats the
stolen-disk scenario, satisfies regulator expectations for stored data, and
protects every copy that leaves the operating context — backups, snapshots,
replicas shipped to a DR site, drives returned under RMA. The question is
whether "confidentiality against media theft" honestly compresses to "access
is controlled".

## Verdict

**Incomplete.** The claim is true in the regime where the attacker's
capability is limited to *reading the medium* — stolen hardware, exposed
snapshots, mislaid backups. It omits the precondition that dominates real
breaches: the attacker's capability is usually limited to *using valid
credentials*, and against that adversary encryption at rest provides exactly
zero protection. The claim becomes false whenever "access is controlled" is
taken to mean "authorization is handled" — that is a different control on a
different surface, and it must be designed, reviewed, and tested separately.

## Why People Believe It

Three forces keep this claim alive. First, compliance frameworks list
"encryption at rest" as a discrete checkbox, and checkboxes invite the
inference that checking one covers a concern — the checkbox is named
"data protection", so passing it feels like having addressed data protection.
Second, the two controls genuinely rhyme: both are about confidentiality,
both are usually implemented by the platform team, and both appear in the
same slide under "Security". A control that is adjacent in the taxonomy feels
like a substitute in the architecture.

Third, and most importantly, encryption is *concrete* while authorization is
*social*. You can point at the console toggle that says "SSE-KMS: enabled";
you cannot point at a console toggle that says "no role is over-broad". Teams
under deadline pressure reach for the tangible control, document it, and let
the intangible one ride on habit. The result is systems where the key
management story is excellent and the IAM policy is `*:*` on the production
role — encrypted ciphertext, one stolen token away from plaintext.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Access is controlled" | Encryption at rest controls access to the *medium*, not to the *data through the service* |
| "A leaked credential is safe" | A credential that can read rows reads *plaintext*; the service decrypts for authorized callers by design |
| "Who can decrypt?" | The key policy — who may call the KMS decrypt API — is itself an access-control surface, not a substitute for one |
| "Encryption and authorization" | Orthogonal axes: confidentiality of stored bytes versus who may invoke operations on the data |
| "Compliance checkbox" | Frameworks (PCI DSS, HIPAA) require *both* encryption at rest and access control precisely because neither covers the other |
| "Where at-rest encryption helps" | Media theft, snapshot leakage, backup exposure, decommissioned hardware, forensic defense-in-depth |

The correct sentence: "Encryption at rest protects the data against anyone
who obtains the storage medium without the key; access control protects the
data against anyone who obtains a credential without the entitlement. The
breach paths that matter — stolen tokens, over-broad roles, compromised
service accounts — go through the second control, not the first."

## Where It Breaks

**The credential counterexample, worked end to end.** An attacker phishes one
engineer and obtains an SSO session with a role that can read the production
database. Every query that role issues returns plaintext: the database
process reads its own encrypted pages, decrypts them with the key it holds
(via its instance profile or injected key material), and serves the bytes.
The attacker never touches a disk, never sees a ciphertext byte, and never
needs the "data key" — they borrowed the application's own decryptor. The
encryption at rest did all the work it was designed for and the breach
happened anyway. This is not a corner case; credential abuse is the dominant
breach pattern, which is why OWASP's broken-access-control category has sat
at the top of the web risk list while "weak at-rest encryption" barely
appears.

**Key management is access control wearing a different uniform.** The honest
defender will say: "But the keys are in a KMS, so you still need key access."
True — and now count the principals with key-decrypt permission: the
application role, the backup role, the analytics pipeline, the break-glass
account. Each is a credential away from plaintext, and each widens the
authorization surface the claim said was covered. Encryption at rest *with
poorly governed key policy* is a single control pretending to be two. When
the key policy is as over-broad as the data policy, the architecture has
relocated the access-control problem, not solved it.

**Field-level encryption is the exception that proves the rule.** There is
one configuration where "encrypted, therefore access-controlled" approaches
the truth: when the *application* encrypts specific fields with keys the
database and its operators never hold, a stolen database credential yields
ciphertext for those fields and the decryption decision moves back into the
authorization layer the attacker did not breach. This is why payments
systems isolate card vaults with application-managed keys and why
end-to-end-encrypted features exist. Notice what the configuration costs,
though: it surrenders server-side search and indexing on those fields, and
it concentrates all the key-management risk inside the application team.
The general-purpose "encrypt the store" toggle buys none of this — it is
transparency by design, and transparent decryption for every authorized
caller is exactly the property the claim mistakes for a control.

**The copies multiply the surface.** Backups, read replicas, analytical
extracts, and log archives each carry the data, each has its own encryption
setting, and each has its own authorization matrix — usually weaker, because
the copy was made for convenience. The claim was made about the primary
store; breaches routinely happen in the copy nobody encrypted, or in the copy
everybody in the data team can read. "Access controlled" is a property of
every path to the data; encryption at rest is a setting on one store.

**What the medium-protection is actually for.** Strip the overreach and the
control remains valuable. Disk theft and drive disposal are real: without
at-rest encryption, every decommissioned SSD is a data leak and every
physical attacker with a datacenter badge reads raw pages. Regulators treat
at-rest encryption as table stakes because it converts hardware loss from a
reportable incident into a non-event. Defense-in-depth is the honest frame:
the medium control and the authorization control cover disjoint adversary
capabilities, and you need both, and neither substitutes for the other.

## Practical Implications

- In design reviews and questionnaires, split the sentence: state what
  protects the medium (at-rest encryption, key custody) and what protects
  access (IAM policy, database roles, row-level security) as two separate
  controls with separate owners.
- Audit the KMS key policy as an authorization artifact: enumerate the
  principals that can decrypt, and hold it to the same least-privilege
  standard as the data plane. Key access is data access.
- Put real effort into the credential path the claim ignores: short-lived
  credentials, MFA on break-glass roles, least-privilege review, and
  detection on anomalous reads — because that is the path breaches take.
- Do not let "encrypted at rest" close an audit finding about access
  control; auditors who accept the substitution are producing the paper
  trail for the next breach report.
- Remember the copies: every backup, replica, and extract needs the
  encryption setting *and* its own access review, or the primary store's
  discipline is cosmetic.

## Interview Questions

### Your database has encryption at rest enabled with KMS-managed keys. An attacker steals a service-account token that can query it. What data do they get?

All of it, as plaintext. The database engine decrypts pages transparently for
any caller it authorizes, and the stolen token is an authorized caller. At-rest
encryption protects the medium, not the API surface; the key never leaves the
trust boundary the engine defines. A strong answer then pivots to the real
fixes: least privilege on the role, short-lived credentials, and detection on
read volume.

### Why do compliance frameworks require both encryption at rest and access control if encryption "protects the data"?

Because the two controls address disjoint adversary capabilities. Encryption
at rest addresses an adversary with the medium but not the key — stolen disk,
leaked snapshot. Access control addresses an adversary with a credential but
no entitlement — the far more common breach. Either control alone leaves one
whole capability class uncovered, so the frameworks list them as separate
requirements rather than substitutes.

### Where does key management overlap with access control, and where does it differ?

They overlap because a KMS key policy is an authorization decision: whoever
may call decrypt can read the data regardless of database roles. They differ
in scope and failure mode: the data plane answers "who may query rows", the
key plane answers "who may turn ciphertext into plaintext", and a compromise
of the key plane is usually broader — it defeats every store that uses the
key. Treating key policy as a second, independent IAM surface is the
disciplined position.

### Name three situations where encryption at rest is the control that saves you, and three where it is irrelevant.

It saves you when a drive is stolen or RMA'd, when a snapshot or backup is
exposed, and when hardware is decommissioned without certified wiping. It is
irrelevant when a credential is stolen, when an application bug returns other
users' rows (IDOR), and when an insider with a legitimate query interface
exfiltrates through the API. The two lists are disjoint, which is the whole
point.

## Key Takeaways

- Encryption at rest controls access to the storage *medium*; authorization
  controls access to the data *through the service*. The claim merges two
  controls that cover different adversaries.
- Anyone with valid application credentials reads plaintext by design; the
  engine is the decryptor and the credential makes them the application.
- Key policy is an access-control surface in its own right and must be held
  to least privilege; otherwise you have one control impersonating two.
- Breaches overwhelmingly travel the credential path, which is exactly the
  path at-rest encryption does not touch.
- Keep the control, lose the inference: at-rest encryption converts hardware
  loss into a non-event and is worth deploying — alongside, never instead
  of, real access control.

## Cross-References

- [Misconception: "It's encrypted, so it can't be tampered with"](./encryption-means-authenticated.md)
  — the sibling cipher-conflation on the integrity axis: this page is about
  confidentiality not covering authorization, while that page is about
  confidentiality not covering tamper-resistance; both fail by smuggling a
  second property into the word "encrypted".
- [Misconception: "JWTs are secure because they're encrypted"](./jwt-is-encrypted.md)
  — the token-shaped variant: a signed JWT is readable by anyone holding it,
  just as at-rest-encrypted rows are readable by anyone holding a
  credential; encoding or encrypting data does not decide who may use it.
- [Misconception: "The padlock means this site is safe"](./https-means-secure.md)
  — the transport twin: TLS protects bytes on the wire the way at-rest
  encryption protects bytes on the disk, and neither says anything about
  what the endpoint is allowed to do with them.
- [Assumptions Hunt: Security & Crypto](../assumptions-hunt/security-crypto.md)
  — the hidden-assumptions sweep for "we use encryption, therefore we are
  secure", of which this claim is the storage-tier instance.
- [Authorization](../../security/authorization.md) — the control this claim
  assumed away, and where the real access decisions live.
- [Vault & Secrets Management](../../security/vault.md) — how key custody
  and secret distribution are actually engineered, and why key policy is an
  IAM surface.
- [Encrypted Databases](../../dbms/advanced/encrypted-databases.md) — the
  mechanics of transparent page-level encryption that make credentials
  route around it.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- E. Barker. *Recommendation for Key Management, Part 1: General*.
  NIST SP 800-57 Part 1, Rev. 5, May 2020.
  <https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf>
- M. Souppaya and K. Scarfone. *Guide to Storage Encryption Technologies for
  End User Devices*. NIST SP 800-111, November 2007 — the formal statement
  of what storage encryption does and does not protect.
  <https://csrc.nist.gov/pubs/sp/800/111/final>
- OWASP. *OWASP Top 10* — Broken Access Control ranked as the leading web
  application security risk, the category this claim's substitution ignores.
  <https://owasp.org/Top10/>
- PCI Security Standards Council. *PCI DSS v4.0* — Requirement 3 (protect
  stored account data) and Requirement 7 (restrict access) as separate
  families, cited by title.
- M. Coates, K. Levchenko, et al. *Postmortem for the MongoDB ransom
  attacks* and industry breach reports, 2017 — the wave of exposed,
  unauthenticated stores showing that encryption toggles and access
  discipline fail independently, cited by title.
