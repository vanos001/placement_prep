# SHA-256 vs bcrypt vs scrypt vs Argon2id: Making Verification Deliberately Slow

## Overview

Password hashing inverts every other performance goal in systems engineering: the correct design is one that **cannot be made fast**. A stolen password database is only as safe as the cost per guess, and the cost per guess is a property of the hash function chosen. SHA-256 — a fine message-digest primitive — verifies a password in well under a microsecond, which means an attacker with commodity GPUs tests billions of guesses per second per card; a password with 40 bits of entropy falls in minutes. The password-hashing functions — bcrypt, scrypt, Argon2 — exist to push that cost back up by doing deliberately expensive work: iteration (bcrypt), memory-hard table walks (scrypt), or tunable memory-and-time hardness (Argon2, the Password Hashing Competition winner).

The question "why not SHA-256 plus a salt?" is therefore the central interview question, and this page runs the [handbook framework](./index.md) on the four-way choice. The preview: **salts stop precomputation but not parallel guessing; speed is the vulnerability; memory hardness is the current best defense because GPUs and ASICs are throughput machines with small fast memories; Argon2id is the modern default, bcrypt remains solid where it is already deployed or where library support dominates, scrypt is sound but largely superseded, and raw SHA-2 is correct only for inputs that are not human passwords** (high-entropy keys and tokens — see the [crypto assumptions audit](../assumptions-hunt/security-crypto.md) for the surrounding threats).

## Step 1: The Problem and Its Constraints

The workload: at registration, transform a (low-entropy, human-chosen) password into a stored verifier; at login, verify a candidate against it. The database will eventually leak. Constraints:

- **Attack model.** The adversary has the hash database (a breach), commodity hardware (GPU farms, cloud credits), and a dictionary of likely passwords. Offline guessing at hardware speed is the threat; online rate limiting is a separate, weaker layer.
- **Input entropy is the real budget.** A 128-bit random token needs no stretching — brute force is already infeasible. A human password carries maybe 20–40 bits; the hash must add cost per guess to compensate. This is why the same function is not always right for passwords and for API keys.
- **Server budget.** Verification cost is paid on every login: memory and time per hash are capacity decisions. 64 MiB and 500 ms per login at 1,000 logins/second is a real memory bill — the defense is not free, and login endpoints become a DoS surface.
- **Compliance constraints.** Some environments require FIPS-validated primitives, which historically meant PBKDF2-HMAC rather than bcrypt/scrypt/Argon2; [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) governs the expectations. The policy tail wags the crypto dog more often than engineers expect.
- **Migration reality.** Existing hashes cannot be "upgraded" in place — the plaintext is gone. Migration is a rehash-on-login program measured in years of user activity.

## Step 2: The Mechanisms

### Option 1: Raw SHA-256 (+ salt) — the fast hash

- **The mechanism is speed.** SHA-256 is a compression function optimized for throughput; a GPU evaluates it at gigahashes per second per card. Salting (a unique random value hashed alongside each password) defeats rainbow tables and cross-user amortization — real wins — but does nothing about *per-guess speed*: every candidate still costs nanoseconds, and the attacker's parallelism is untouched.
- **Why it survives in the wild anyway.** It appears in older systems and in contexts where the input is genuinely high-entropy (tokens, keys) and speed is a feature. The strawman here is not "SHA-256 is broken" — it is not — but "SHA-256 is the wrong tool for human-chosen secrets."

### Option 2: bcrypt — iteration-hardened

- **The mechanism is a tunable cost loop.** bcrypt is the EksBlowfish key schedule run 2^cost times, with the salt inside the loop. Cost 12 on 2010s hardware meant ~250 ms; the knob raises the cost exponentially as hardware improves. It is battle-tested since 1999, available in every ecosystem, and produces a self-describing stored string (`$2b$12$...`) carrying algorithm, cost, and salt.
- **The limits.** Its memory footprint is small (about 4 KiB), so GPUs still evaluate it efficiently per core — bcrypt is *compute*-hard, not *memory*-hard, and the cost-per-guess gap versus specialized hardware is smaller than Argon2's. And the 72-byte input limit truncates longer passwords silently — a real correctness edge (Step 5).

### Option 3: scrypt — memory hardness arrives

- **The mechanism is a memory-filling walk.** scrypt (Percey/Rompré... — Colin Percival, 2009) fills RAM with pseudorandom blocks (parameters N, r, p; typically tens of MiB) and indexes into them data-dependently. The memory requirement is the defense: GPU cores each have little fast memory, so either the attack runs at CPU speed or the attacker buys memory — both blunt the parallel advantage that breaks fast hashes.

### Option 4: Argon2id — tunable memory and time

- **The mechanism is the PHC winner.** Argon2 (2015 Password Hashing Competition winner) exposes memory cost, time cost, and parallelism as independent knobs; Argon2id — the variant recommended by [RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106) — hybrids Argon2i's data-independent passes (side-channel resistant, right for inputs that must not leak through memory access patterns) with Argon2d's data-dependent passes (GPU-resistant). The [RFC 9106 recommendation](https://datatracker.ietf.org/doc/html/rfc9106) is explicit: Argon2id with generous memory first (e.g., 2 GiB where feasible), time cost as the second lever — the first formal "memory-first" guidance in a standard-track document.
- **Salts and the PHC string format** are common to bcrypt/scrypt/Argon2: a unique per-password salt, an algorithm identifier, and parameters stored with the hash, so cost can rise per-user over time without a schema change. Peppers — a server-side secret mixed in — add defense against database-only theft, at the price of key management (see [secrets management](../../security/secrets-management.md)).

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | SHA-256 + salt | bcrypt | scrypt | Argon2id |
|----------|----------------|--------|--------|----------|
| Cost per guess (CPU) | Microseconds | Milliseconds (cost-tunable) | Milliseconds (N/r/p-tunable) | Milliseconds (memory/time-tunable) |
| Memory hardness | None | Weak (~4 KiB) | Yes (tens of MiB) | Yes, tunable to GiB |
| GPU/ASIC resistance | None | Partial | Good | Best |
| Input length limit | None practical | 72 bytes, silently truncated | None | None practical |
| Side-channel posture | Neutral | Good | Neutral | Argon2id: hybrid — i-passes for secret-dependent inputs |
| Standardization | FIPS 180-4 (as a digest) | Not FIPS-validated; de facto standard | IETF (RFC 7914) | RFC 9106; PHC winner |
| Library availability | Universal | Universal, oldest tooling | Good | Excellent in modern stacks (libsodium et al.) |
| Signature failure | Fast offline cracking | Silent truncation; GPU gap vs memory-hard | Parameter-misconfiguration (too little RAM) | Mis-tuned memory (too low) re-creates the bcrypt gap |

**The hardware-economics column is the real comparison.** Fast hashes let an attacker's dollar buy billions of guesses; memory-hard hashes force the attacker's dollar to buy memory — and memory is the resource GPUs have least. The design question "how much memory can my login path afford per verification?" is therefore also the question "how expensive do I make a stolen-database attack?" The two budgets are the same knob.

## Step 4: When Each Wins

**Argon2id wins** for new deployments with modern library support: tune memory to what the login path can afford (hundreds of MiB where traffic allows, tens of MiB where it does not), then time cost; it offers the strongest hardware-attack resistance and standard-track guidance ([RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)). This is the [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) default.

**bcrypt wins** when: it is already deployed and correct (migration risk beats marginal gains); the ecosystem's best-supported library is bcrypt (some languages/frameworks); or server memory is too constrained for meaningful Argon2 memory costs — a compute-hard hash you can afford beats a memory-hard hash tuned to 8 MiB of defensiveness. The 72-byte limit must be handled consciously.

**scrypt wins** narrowly: as a historically important stepping stone, and in environments where it is already in place with sane parameters. New designs have little reason to prefer it over Argon2id — its niche has been absorbed.

**Raw SHA-2/PBKDF2 wins** in two cases: FIPS-constrained environments that mandate validated modules (PBKDF2-HMAC-SHA-256 with high iteration counts — weaker than memory-hard options, but compliant); and non-password inputs with high intrinsic entropy (API keys, tokens), where the brute-force budget is already hopeless for the attacker and fast verification is a feature. Matching the function to the input's entropy is the sophisticated answer.

## Step 5: Edge Cases and Counterexamples

- **bcrypt's 72-byte silent truncation.** bcrypt hashes only the first 72 bytes; `correct horse battery staple Correct Horse...` variants past 72 collide with their prefixes. Worse, pre-hashing with SHA-256 to "fix" this introduces its own classic bug: raw SHA-256 output contains zero bytes that truncate some bcrypt implementations' C-string handling — libraries that hex-encode before bcrypt exist because of this exact incident class. The safe answers: handle the limit explicitly, or use a function without it.
- **Passkeys and high-entropy inputs change the calculus.** A WebAuthn credential's secret is server-opaque and high-entropy; hashing it like a password wastes the budget and misreads the threat model — the verification problem moved from "stretch low entropy" to "store and challenge" (see [FIDO2/WebAuthn](../../security/advanced/fido2-webauthn.md)). Password hashing is for *human-memorable* secrets; applying it to everything is cargo-culting.
- **The FIPS corner.** Regulated environments often run FIPS 140-validated crypto modules, which have historically excluded bcrypt/scrypt/Argon2 — NIST SP 800-63B's list starts at PBKDF2. The engineering response is honest weakening: PBKDF2 with maximal iteration counts, compensating controls, and a migration plan if policy allows Argon2 (recent SP 800-63 revisions have moved toward admitting memory-hard schemes — verify against the current revision, not this page).
- **Verification DoS: the defense is an attack surface.** A login endpoint spending 500 ms and 256 MiB per attempt is a denial-of-service amplifier: unauthenticated requests purchase server work. Rate limiting, queue caps, and cheap rejection paths (invalid usernames) are part of the hashing design, not an afterthought — the [threat modeling](../../security/threat-modeling.md) chapter owns that pairing.
- **Rehash-on-login is the migration mechanism.** You cannot rehash what you cannot read; instead, wrap: on successful login (plaintext briefly available), verify with the old scheme, then re-verify/re-store with the new one. Migration completes at the pace of user logins — years — which is why parameter modernity at *initial* choice matters, and why the stored string must carry its own algorithm/parameters (the PHC format does exactly this).
- **Salts are not peppers, and neither is optional.** A salt is public, per-record, and exists to stop precomputation; a pepper is global, secret, and exists to stop database-only theft — but losing the pepper bricks every password. Systems that conflate them (e.g., a hardcoded "salt" in source code shared across users) get the protection of neither (see [cryptography](../../security/cryptography.md) for the primitives and [secrets management](../../security/secrets-management.md) for the pepper's storage).

## Step 6: Decision Framework

1. **Is the input a human-chosen password?** Yes → memory-hard function; raw SHA-2 is eliminated regardless of salting.
2. **Greenfield with modern libraries and memory headroom?** → Argon2id, memory-first tuning per RFC 9106 guidance; store the PHC-formatted string with parameters.
3. **bcrypt already deployed and correct?** → Keep it, plan cost-factor audits, handle the 72-byte limit explicitly; do not migrate for fashion.
4. **FIPS-validated modules mandated?** → PBKDF2-HMAC-SHA-256 at maximum tolerable iterations; document the gap versus memory-hard options as accepted risk.
5. **Is the input high-entropy (token, key, passkey secret)?** → Fast verification is correct (HMAC-SHA-256); the work-factor machinery is for entropy-poor inputs.
6. **What does a stolen database cost the attacker?** Set the memory/time budget from the login path's capacity, rate-limit the endpoint, and re-evaluate parameters on a schedule — cost per guess is a maintained system property, not a one-time choice.

## Interview Questions

1. **Why doesn't salting fix the SHA-256 password problem?** A salt defeats precomputation (rainbow tables) and cross-user amortization — each user needs fresh work. It does nothing about per-guess cost: SHA-256 still verifies in under a microsecond, so GPUs test billions of candidates per second. Salts address *which* work is reusable; work factors address *how much* work each guess costs. Both are needed, and the fast hash lacks the second entirely.
2. **What is memory hardness, and why does it blunt GPU attacks specifically?** Requiring a large data-dependent working set means the attacker must either run at CPU-like speeds (GPU cores lack fast local memory for the tables) or buy memory proportional to parallelism. Compute-hard hashes scale to thousands of GPU cores; memory-hard hashes bind the parallelism to the memory budget — changing the hardware economics rather than the constant factor.
3. **A legacy system stores bcrypt hashes; a new CTO wants to migrate everything to Argon2id immediately. What is the correct plan?** Immediate mass rehashing is impossible without plaintexts. Wrap-rehash on login: verify with bcrypt, then re-store with Argon2id on successful authentication; force-reset for high-value accounts; complete at login pace over months to years. Meanwhile bcrypt at audited cost factors remains safe — migration urgency is a risk question, not a fashion one.
4. **Why is Argon2id the recommended variant rather than Argon2i or Argon2d?** The hybrid runs data-independent passes first (side-channel resistant — memory access patterns do not leak the input) and data-dependent passes after (maximally resistant to GPU/ASIC acceleration). Argon2i alone is weaker against GPU attacks; Argon2d alone leaks through cache-timing. Argon2id composes the two threat models — and RFC 9106 recommends it with memory-first parameterization.
5. **Your login endpoint uses Argon2id at 256 MiB per verification and is rate-limited to 10 attempts/minute per user. What residual risks remain?** Credential stuffing at scale across users (rate limits are per-user; the fleet budget is what matters — cap global verification concurrency too), verification DoS via distributed unauthenticated attempts (each request purchases 256 MiB — queue caps needed), and enumeration via timing/response differences. Password hashing is one layer of an authentication design, not the design.

## Key Takeaways

- Password hashing is deliberate slowness: salts stop precomputation, work factors stop cheap guessing, and the stored string must carry its own algorithm and parameters (PHC format) so cost can evolve.
- Speed is the vulnerability in raw SHA-2 for passwords; the same fast hash is correct for high-entropy tokens — matching function to input entropy is the mark of understanding.
- Memory hardness is the current economics argument: it converts the attacker's parallelism advantage into a memory bill, which is why Argon2id (RFC 9106) is the modern default and bcrypt's ~4 KiB footprint is its structural ceiling.
- bcrypt is not obsolete: deployed-and-correct, library-constrained, and memory-constrained environments are legitimate homes for it — with the 72-byte truncation handled explicitly.
- The verification budget cuts both ways: login-path capacity and attack cost are the same knob, and an unthrottled expensive login endpoint is a DoS amplifier.

## Cross-References

- [Security and Crypto Assumptions: Assumptions Hunt](../assumptions-hunt/security-crypto.md) — the hidden assumptions behind crypto deployments, including key handling.
- [Cryptography](../../security/cryptography.md) — the hash and MAC primitives underneath this comparison.
- [Authentication](../../security/authentication.md) — where password verification sits in the login flow.
- [FIDO2/WebAuthn](../../security/advanced/fido2-webauthn.md) — the passkey model that removes the low-entropy input this page defends against.
- [Secrets Management](../../security/secrets-management.md) — pepper storage and the key-management boundary.
- [Threat Modeling](../../security/threat-modeling.md) — pairing the hashing budget with rate limiting and abuse cases.
- [HTTPS Means Secure: Misconceptions](../misconceptions/https-means-secure.md) — transport protection does not substitute for stored-secret protection.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
