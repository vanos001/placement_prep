# Randomness and Identifier Assumptions: What `Math.random()` and a UUID Silently Promise

## Overview

Identifiers are the connective tissue of every system — session tokens, request ids, order numbers, API keys — and the sentence "let's just generate a random id" packs four assumptions into four words: that the library function called "random" produces unpredictable output, that uniqueness and secrecy are the same property, that a random-looking id cannot be guessed, and that a generator seeded once at boot stays unpredictable for the process's lifetime. None of the failures announces itself: a predictable generator mints perfectly plausible session ids, a UUIDv1 leaks its host's MAC address to everyone who sees it, and a forked worker copies its parent's randomness state and mints duplicates forever after.

This chapter separates three properties that are routinely conflated: *statistical quality* (outputs look uniform — simulation-grade PRNGs have it), *unpredictability* (an adversary who has seen past outputs cannot compute future ones — only CSPRNGs provide it), and *uniqueness* (no two draws collide — a birthday-bound property of width plus generator health). The audited corrections are correspondingly concrete: use the CSPRNG for anything security-adjacent, budget entropy in bits against the birthday bound, treat identifier *schemes* (UUIDv1/v4/v7, Snowflake, ULID) as trade-offs between unguessability, index locality, and coordination, and re-seed or re-instantiate around every fork, snapshot, and container start. The security-crypto sibling chapter audits the endpoint-level consequences; here the focus is the generator mechanics underneath them, in the collection's five-step pattern.

## Assumption 1: "`Math.random()` / `rand()` Is Random Enough"

### The taught rule

The standard library's random function gives unpredictable values; for ids and tokens, "random" is "random".

### The hidden assumptions

- Library PRNGs are built for *speed and statistical distribution*, not unpredictability. Python's `random` module and many language defaults implement the Mersenne Twister (MT19937): it passes statistical test batteries and is simultaneously fully predictable, because its state is 624 32-bit words and the algorithm is public.
- Predictability follows from observation: MT19937's state is recoverable from 624 consecutive 32-bit outputs, after which every past and future output is computable. A token generator drawing 32-bit values from MT19937 therefore leaks the entire stream — including tokens already issued — after a few hundred observable draws.
- `rand()` with `srand(time(NULL))` adds a second layer of weakness: the seed space is the current second (or millisecond), so an attacker who knows roughly when the process started brute-forces a few million candidate seeds offline and reproduces the whole output stream.
- "Random enough" quietly assumes the adversary only checks *uniqueness* (collisions), never *prediction* (guessing the next token). Those are different threats with different requirements: collisions need entropy, prediction needs CSPRNG construction.

### Counterexample

A service mints password-reset tokens by truncating `Math.random().toString(36)` to six characters — roughly 31 bits of entropy from a predictable generator. An attacker who can trigger token issuance collects observed outputs, recovers PRNG state, and computes the tokens the service will issue next; if the draw order is shared process-wide, every other user's pending token is inside the recovered stream. Both are documented: Python's `random` documentation warns against security use and points to `secrets`, and [OWASP's session management cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) specifies at least 64 bits of CSPRNG entropy for session tokens (128 where convenient). The corrected construction: `secrets.token_urlsafe(32)`, `crypto.randomBytes(32)`, `SecureRandom` — the CSPRNG with a stated entropy budget, sized so the birthday bound (Assumption 2) and the guessing bound both clear the threat model.

### What changes when the assumption is removed

Corrected statement: *simulation-grade PRNGs (MT19937, xorshift, PCG) are for models; anything an adversary could gain by predicting needs the OS CSPRNG (`getrandom(2)`, `/dev/urandom` wrappers, `crypto.getRandomValues`) with an explicit entropy budget per token.* RFC 4086, "Randomness Requirements for Security," is the canonical statement of how much entropy each use needs and why user-space generators fall short. The [security assumptions](security-crypto.md) chapter carries the endpoint consequences (session fixation, credential stuffing); the contribution here is the mechanism: prediction is a property of the generator's construction, not of how outputs look.

### Consequences

The interview probe "what's wrong with `Math.random()` for a token?" has a three-part senior answer: the generator's construction (state recovery from a bounded observation window), the entropy budget (bits needed versus bits provided), and the seed (a small seed space makes even a strong algorithm brute-forceable). Answering only "it's not cryptographically secure" demonstrates the label without the mechanism.

## Assumption 2: "UUID Collisions Can Be Ignored, So UUIDs Are Secrets"

### The taught rule

UUIDs are unique — 122 random bits in v4 means collisions effectively never happen — so a UUID can double as an unguessable secret: a capability URL, an API key, a session id.

### The hidden assumptions

- The collision half is conditionally true: for v4 with *healthy* randomness, the birthday bound puts 50% collision odds near 2.6 × 10^18 draws — astronomically far away at a billion ids per year. But the bound assumes a working generator: a broken or predictable PRNG (the Debian OpenSSL 2008 episode, where the effective seed space collapsed to the process id) collapses 122 nominal bits to a handful of real ones, and collisions move from theoretical to actual.
- The secrecy half is false as stated. Uniqueness and unpredictability are orthogonal: UUIDv1 is *unique* by construction (timestamp plus MAC address plus clock sequence) and simultaneously *not secret at all* — it embeds the generating host's MAC and a timestamp readable from the id itself, as [RFC 4122](https://www.rfc-editor.org/rfc/rfc4122) documents; its successor [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html) retains the layout.
- Even v4 is a secret only if generated from a CSPRNG — the RFC explicitly permits weaker randomness sources for non-security uses, and a v4 minted from a time-seeded PRNG inherits Assumption 1's predictability while wearing a random-looking format.
- Capability URLs (the "unguessable link grants access" pattern) therefore need the identifier to be a *token*: CSPRNG-sourced, entropy-budgeted, rotatable. A UUIDv1 in that role publishes its host identity to every recipient of the link.

### Counterexample

A document-sharing feature uses `uuid1()` for share links: anyone with a link can read the document. Three failures compose. Each link discloses the file server's MAC address and its creation timestamp — reconnaissance for free. The timestamps of many links reveal issuance volume. And because v1's entropy lives mostly in the clock sequence (14 bits) plus timestamp, an attacker who can narrow the issuance window guesses candidates in a space far smaller than 2^122 — the "unique" guarantee said nothing about guessability. The corrected design: v4 from the CSPRNG (or a 128-bit `secrets` token) for capability URLs, and no time-ordered identifier on unauthenticated links, per the [session management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

### What changes when the assumption is removed

Corrected statement: *uniqueness is a birthday-bound property of width and generator health; secrecy is a construction property — CSPRNG sourcing and entropy budget — and neither implies the other.* Audit id schemes by three questions: where does the entropy come from, how many bits are actually random, and what does the format leak (v1: MAC and time; v4: nothing but also no ordering; v7: creation time by design). The trade-off space is the subject of the sibling [Snowflake versus UUID comparison](../why-not-handbook/snowflake-vs-uuid.md); the URL-shortener design page shows the same choice appearing in an interview setting.

### Consequences

"Can a UUID be an API key?" is a sharper interview question than it looks: the expected answer quantifies the birthday bound, then rejects the question's framing by separating uniqueness from unguessability, then names what v1 leaks. The general lesson — a format's look is not a security property — generalizes far beyond UUIDs.

## Assumption 3: "Random IDs Cannot Be Enumerated"

### The taught rule

Users' object ids are random, so an attacker cannot iterate them the way they could iterate `12345, 12346, 12347...`.

### The hidden assumptions

- "Random" is routinely applied to ids that are short, short-alphabet, or derived: a six-character alphanumeric short code is about 35.7 bits; a six-digit numeric code is 19.98 bits. Enumeration cost is a function of the *space*, not the generator — even a perfect CSPRNG cannot make 10^6 candidates unguessable.
- Derived ids fake randomness deterministically: `md5(email)`, `md5(counter)`, or hash-of-small-domain ids look opaque but are enumerable offline, because the candidate input space is small and hashing is free. Randomness of output cannot exceed entropy of input.
- Enumeration is also a rate problem: a 35.7-bit space is about 5.7 × 10^10 candidates — a month-scale sweep at 10,000 probes per second against a single valid code, and much faster when many codes are valid at once — so rate limiting is often the actual defense and must be sized against the id space.
- Sequential ids leak back in through side doors: export endpoints, iCal URLs, "download all" links, and bulk CSVs frequently expose the internal integer key even when the UI shows an opaque id, making the opaque layer decorative.

### Counterexample

A booking platform issues six-digit confirmation codes from a CSPRNG — perfect generator, tiny space. An attacker sweeps codes against the public "manage booking" endpoint: 10^6 candidates in under four minutes at 5,000 probes per second; found codes expose names, phone numbers, and travel dates. The same platform's UUIDv4 "share trip" links, by contrast, are unenumerable in practice — 122 CSPRNG bits put the sweep outside any attacker's lifetime. The contrast is the point: both ids came from the same generator, and only the width made one safe. The fix for the codes is width or alphabet (eight-plus characters), rate limiting on the lookup endpoint, and secondary verification for sensitive actions — entropy and rate control are complements, not substitutes.

### What changes when the assumption is removed

Corrected statement: *enumeration resistance is an entropy-budget claim — bits of real randomness against the attacker's request rate and sweep lifetime — and every leakage path (exports, embeds, logs) that exposes a stronger id weakens the weakest link for the whole resource.* Budget explicitly: 128 bits for capability URLs and tokens (per the [OWASP guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)), shorter codes only with rate limiting sized to their space. The [security-crypto chapter](security-crypto.md) covers the auth-flow side of the same budget.

### Consequences

"How would you attack a six-digit OTP?" is the adversarial form of this assumption and a complete seniority probe: enumerate the space, compute the rate, note the generator was never the weakness, then flip to defense (width, throttling, lockout). — security reasoning is arithmetic on entropy and rate, not adjective selection.

## Assumption 4: "Seeding Once at Boot Is Fine"

### The taught rule

Seed the random generator once when the process starts; thereafter it serves random numbers for the process's lifetime.

### The hidden assumptions

- Boot-time seeding inherits the boot environment's entropy: a fleet of identical VMs or containers starting within the same second, running identical images, seeds `srand(time(NULL))` identically — one random stream shared by every instance. Time, pid, and hostname seeds are all fleet-correlated under orchestration.
- `fork()` duplicates the parent's PRNG state verbatim: a pre-forked server or a process pool whose workers draw randomness continues the identical stream in every child, so two workers can mint the same token for different requests. Threads do not fix this — they share the state, which moves the problem to synchronization.
- Snapshot-and-restore (VM images, checkpoint/restore tools, some serverless runtimes) rewinds the generator to the snapshot's state; every restored instance replays the same outputs. The failure is structurally a fork.
- Historical operating systems could not provide strong boot-time randomness, which is why generators self-seeded from the clock; modern kernels expose `getrandom(2)` precisely to remove that decision, and runtimes initialize their CSPRNGs from it automatically — but the *non*-crypto generators (Assumption 1's suspects) still accept manual, weak seeds.

### Counterexample

A batch job scales to 64 containers from one image. Each container seeds a Mersenne Twister from `time(NULL)` at startup; the orchestrator starts them within the same second, so all 64 produce identical id sequences. The first cross-container deduplication check — written assuming ids are unique — silently passes duplicates through, and downstream analytics double-count events whose ids happen to collide across containers. Nobody misconfigured randomness; the deployment topology broke the seed assumption. The corrected pattern: derive all seeding from the OS CSPRNG (`getrandom(2)`/`/dev/urandom`, wrapped by Python's [`secrets` module](https://docs.python.org/3/library/secrets.html) and its equivalents), never seed from time or pid, and after fork or snapshot-restore re-instantiate generators rather than inheriting state. [RFC 4086](https://www.rfc-editor.org/rfc/rfc4086.txt) section 8 covers the boot-time-entropy problem directly.

### What changes when the assumption is removed

Corrected statement: *a PRNG's guarantees date from its seed; any process-lifecycle event that copies or rewinds state (fork, snapshot, image clone) resets the guarantee to zero unless the generator is re-instantiated from the OS CSPRNG.* Concretely: seed from the kernel, re-seed after fork (or make children open fresh generator instances), verify container images do not embed fixed seeds "for determinism", and reserve user-space generators for simulation — the two prior assumptions already removed them from the security path.

### Consequences

The interview probe "why did your horizontally scaled fleet mint duplicate ids?" rewards the candidate who can move between layers: seed correlation under orchestration, fork state copying, snapshot rewind — three mechanisms, one assumption. The identifier-scheme trade-offs this constrains (time-ordered versus random, coordinated versus stateless) are mapped in the sibling [Snowflake versus UUID comparison](../why-not-handbook/snowflake-vs-uuid.md).

## Interview Questions

1. **Why is MT19937 predictable, and what exactly does an attacker recover?** Its state is 624 32-bit words and the algorithm is public; observing 624 consecutive outputs recovers the state, after which all future (and past, given state) outputs are computable. Statistical quality does not imply unpredictability — prediction is a construction property.
2. **How much entropy should a session token have, and how many ids until a UUIDv4 collision is 50/50?** At least 64 bits from a CSPRNG, 128 where convenient (OWASP session guidance). For 122 random v4 bits, the birthday bound puts 50% collision odds near 2.6 × 10^18 draws — negligible with a healthy generator, meaningless with a broken one.
3. **A share link uses UUIDv1. What leaks, and what would you use instead?** The MAC address of the generating host and a 100-nanosecond timestamp are embedded in the id (RFC 4122/9562 layout), plus issuance volume across many links. Use CSPRNG-sourced v4 or a 128-bit token for capability URLs.
4. **Your six-digit booking codes are generated with `secrets`. Are they safe from enumeration?** No — the space is 10^6 regardless of generator quality; at thousands of probes per second it sweeps in minutes. Width/alphabet plus rate limiting and step-up verification is the fix; entropy and rate control complement each other.
5. **After a fleet of containers scaled up, ids duplicated across instances. Reconstruct the mechanism.** Identical images booting in the same interval seed a time-seeded PRNG identically (or fork/snapshot copied state), so instances share one random stream. Fix: seed from the OS CSPRNG, re-instantiate generators after fork or snapshot-restore.

## Key Takeaways

- Separate three properties that "random" conflates: statistical quality (simulation PRNGs), unpredictability (CSPRNG construction), and uniqueness (birthday bound on real entropy). Security needs the second; deduplication needs the third; neither implies the other.
- Library PRNGs are predictable by construction — MT19937 state recovery needs 624 outputs — and weak seeds (time, pid) shrink even strong algorithms to brute-forceable spaces.
- Uniqueness does not make an identifier secret: UUIDv1 publishes MAC and timestamp, and v4 is unguessable only if generated from a CSPRNG. Capability URLs are tokens, budgeted at 128 bits.
- Enumeration resistance is width times rate control: a perfect generator inside a six-digit space is still enumerable, and any endpoint that leaks a stronger id weakens the whole resource.
- Process lifecycle events — fork, snapshot restore, image cloning — copy or rewind generator state; only seeding from the OS CSPRNG and re-instantiating after such events keeps the guarantee.
- Identifier schemes are trade-offs, not defaults: random (unguessable, poor locality), time-ordered (locality, coordination, timing leaks) — and the choice is a storage and privacy decision.

## Cross-References

- [Security and crypto assumptions](security-crypto.md) — the endpoint-level audit (`Math.random()` as unpredictable) that this chapter's generator mechanics underlie.
- [Snowflake versus UUID](../why-not-handbook/snowflake-vs-uuid.md) — the scheme trade-off space (ordering, coordination, leakage) referenced by Assumptions 2 and 4.
- [Auth, identity, and sessions atlas](../connection-atlas/auth-identity-session.md) — where session tokens and capability URLs sit in the auth architecture.
- [URL shortener (system design)](../../interview/system-design/url-shortener.md) — id generation as a design decision with the same entropy/locality tension.
- [Cryptography](../../security/cryptography.md) — CSPRNG construction and entropy sources in depth.
- [Authentication](../../security/authentication.md) — session and token lifecycle around the identifiers audited here.
- [Caching assumptions](caching.md) — the inverse-popularity pattern that also governs which ids end up enumerable through exports and embeds.
- RFC 4086 (randomness requirements), RFC 4122 and RFC 9562 (UUID layout, including v1's MAC/timestamp embedding and v4's randomness requirements) are cited from rfc-editor.org; OWASP's [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) and Python's [`secrets`](https://docs.python.org/3/library/secrets.html) / [`random`](https://docs.python.org/3/library/random.html) documentation carry the prescriptive guidance.
