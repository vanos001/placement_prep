# Build Caches and Reproducibility: Why Builds Lie

## Overview

A build is supposed to be a pure function from sources to artifacts. It almost never is. Toolchains drift, system libraries upgrade underneath you, tests pass locally and fail in CI, the artifact you shipped last quarter cannot be rebuilt bit-for-bit, and the cache everyone shares occasionally serves an object that was never correct for its key. The machinery meant to make builds fast — lockfiles, content-addressed caches, hermetic toolchains, artifact promotion, sharded CI — is also the machinery that makes builds *honest*, because speed without a complete input key is just a way to be wrong faster. The connection this page maps is that every one of these mechanisms is the content-addressing idea (hash the content, not the location) applied to compilation, and that "reproducibility" is precisely the property that makes a build cache safe to share.

The failure propagation is what makes this a production topic rather than a developer-comfort topic. A poisoned cache propagates a bad artifact to every consumer that trusts its key; a non-reproducible build severs the link between reviewed source and running binary, which turns incident response into archaeology; an incomplete cache key (the hidden input) converts a routine toolchain upgrade into a fleet of stale objects that all look fresh. The levers — complete keys over pinned toolchains, cache isolation across trust boundaries, build-once-promote-many — are all ways of making the build's input set *explicit*, because every "works on my machine" story is, at bottom, an undocumented input.

## The Systems, Independently

**Lockfiles.** A lockfile pins the transitive dependency graph: exact versions and (in mature ecosystems) hashes of every package, so that two builds at different times and machines resolve the same tree. Without a lock, the resolver picks "latest compatible" per run, and the *input set itself becomes nondeterministic* — the build is a function whose arguments change when you are not looking. Lockfiles plus integrity hashes also make the dependency tree content-addressable: verify each artifact against its recorded hash before use, and a compromised mirror or a corrupted download fails loudly instead of silently.

**Build caches, hermetic builds, artifact promotion, CI shards.** A *build cache* maps a key — ideally the hash of all inputs: sources, flags, toolchain version, environment — to a previously built output, local (ccache) or remote (Bazel's remote cache, Gradle build cache, sccache). A *hermetic build* is one whose input set is complete and closed: the compiler, standard library, and every tool come from pinned, hashed artifacts (container images, toolchain manifests), so the key cannot miss an input that varies between machines. *Artifact promotion* builds once and moves the *same bits* through dev → staging → prod, attesting identity at each gate, instead of rebuilding per stage and hoping the environments agree. *CI shards* split the work across machines that share the cache — which is safe exactly to the degree that keys are complete and the cache is inside one trust boundary. Sharding also has a scheduling coupling to the cache: shards that start simultaneously all miss the same shared prefixes and stampede the builders, so mature setups order or seed shards (shard 1 builds the common core first) — the thundering-herd-on-a-cold-cache pattern from CDN origins, recreated inside CI.

## How the Chain Feeds Each Other

The pipeline: sources + lockfile + pinned toolchain → resolution (verify hashes) → dependency graph → schedule (topological order) → per-node cache lookup (hit: download and verify; miss: build and upload under the input hash) → link/package → artifact → promote through environments with the hash as identity. Every stage feeds the next through hashes: the lockfile fixes the input set, the hermetic toolchain fixes the environment inputs, the graph fixes the order, and the cache turns the whole thing into a memoized function. CI shards are consumers and producers of the same cache, so shard N's hit rate depends on shard 1 having already uploaded shared prefixes — which is why sharding and caching are one design decision, not two.

Shared invariants: **key completeness** — every input that can change the output is in the hash, or the cache can serve wrong answers; **verification on every fetch** — content is checked against its key (the hash *is* the address), so corruption and collisions are detectable; **one trust boundary per cache** — artifacts from untrusted code (fork PRs) must not be able to poison keys that trusted builds will consume. A fourth invariant is *recoverability*: because every cache entry is derivable from its inputs by definition, a cache is the one storage system you are always allowed to delete — which is why "just clear the cache" is a legitimate incident response here and heresy almost everywhere else.

## The Shared Principle

**A build system is a memoized function over an explicit input graph, and reproducibility is exactly the statement that the function is pure — same input hash, bit-identical output — which is the precondition for sharing the memo table between machines, humans, and months.** This is the content-addressing principle from [git-cas.md](./git-cas.md) applied to compilation: hash content, address by hash, get immutability, dedup, and integrity for free. Git commits and build outputs are the same shape of object — (hash(inputs) → artifact) — which is why a commit SHA and a build artifact SHA can be glued into one provenance chain. The memoization itself is the incremental-computation pattern: the dependency graph, dirty propagation, and memoized results of any build system are the spreadsheet-recalc algorithm with a remote cache bolted on. And the hash-bucket lookup under every cache is a hash table with the usual concerns — load, collisions — plus one new concern: a *collision or key alias here silently substitutes a wrong program*, so key design is the data-structures problem with security consequences (the hashing foundations live in [../followup-tree/hash-tables.md](../followup-tree/hash-tables.md)).

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| Git/content addressing | Hash inputs → immutable, dedupable, verifiable objects; Merkle-DAG transitivity transfers (output hash covers all transitive inputs) | Build inputs include *context Git never sees* — toolchain version, OS, environment variables, clock — so "hash the files" is necessary but nowhere near sufficient; hermeticity exists to close that gap |
| Memoization | Dependency graph + dirty propagation + memo table transfers from incremental compilation | A build "result" is not a scalar: outputs are trees with permissions, symlinks, and timestamps, so canonicalizing output for hashing is its own problem (tar-reproducibility, normalized mtimes) |
| Caches | Same hit/miss/fill/evict loop and stampede hazards as any cache | Cache *correctness* dominates cache *hit rate* here: a CDN serving slightly stale HTML is a nuisance; a cache serving a binary built from different sources is a supply-chain incident |
| Lockfile as cache key | Pinning makes the resolution step deterministic | A lockfile pins package sources but not the *toolchain that compiles them* — two layers of pinning (deps and tools) are both required, and teams routinely do only one |

## Failure Propagation

**Cache poisoning.** The nightmare path: an untrusted fork-PR build runs with access to the shared remote cache; its build script uploads a malicious artifact under a key that (by incomplete hashing — say, missing a compiler flag) collides with a key the next release build will look up. The release build "hits," downloads, verifies the hash matches the key — the system is functioning exactly as designed — and ships the wrong program. Propagation is *silent and total*: every consumer of that key inherits the artifact, every later build is "clean," and the only detectors are signature/attestation checks on artifacts (who built this, from what invocation?) or the rare reproducibility audit that rebuilds from source and diffs. The sibling failure is credential leakage through caches: build logs and artifacts are shared widely; a secret that leaked into a compiled object or a published cache is now readable by everyone the cache is readable by.

**Non-reproducibility and stale keys.** When builds are not reproducible, the binary in production is not provably the binary that was reviewed; the emergency hotfix "rebuild the same commit" produces *different bits*, and rollback means archaeology (which artifact, built when, from what?). Incomplete keys propagate more mundanely: the toolchain image is upgraded from 1.2 to 1.3, but the cache key only hashes sources; every object compiled by 1.2 still looks fresh, and the fleet now runs a mixture — "works on my machine" deployed at scale, with a heisenbug that depends on which CI runner happened to fill the cache.

## A Concrete Worked Example

**The arithmetic of a cache with a hidden input.** Monorepo: 12,000 source files, full build 20 minutes on 32 cores; median change touches 40 files. With a complete-key remote cache, a typical build recomputes ~2% of nodes: 20 min × 0.02 ≈ 24 s plus link — CI p50 drops by 50×, and 200 engineers × 30 builds/week × 18 minutes saved ≈ 900 engineer-hours per week of returned time. Now remove one input from the key: the build runs `clang` from the host OS, which the distro just bumped from 15 to 16. Objects compiled before the bump remain "valid"; the first build after the bump reuses ~98% stale objects and *passes*, because the compiler change only miscompiles one templated header used by the payments service. The artifact ships, the bug appears only in payments, and the cache ensures the wrong binary is *perfectly stable* — every rebuild reproduces the bug. Cost of the hidden input: a week of debugging against a heisenbug whose root cause is a key; cost of the fix was one line (`hash the toolchain into the key`) before the fact. That ratio — invisible until it fires, trivial when explicit — is the entire economic argument for hermetic builds.

## Design Levers

- **Content-addressed caches with complete keys.** Hash sources, flags, toolchain version, and relevant environment into the key; verify content on every fetch; treat "key completeness review" as part of build-file review — a new input (codegen, env var, plugin) must enter the hash or be proven irrelevant.
- **Pinned toolchains and hermetic execution.** The compiler, linker, and tools come from hashed, versioned artifacts (container image digests, toolchain manifests) — the second lockfile, and the one that makes keys complete in practice.
- **Lockfiles with integrity hashes, updated deliberately.** Resolution is deterministic; upgrades are explicit diffs; a checksum mismatch is a security event, not a warning.
- **Build once, promote everywhere.** One artifact per source revision, carried through dev → staging → prod with attestations (who built it, from what inputs); no rebuild-per-stage, so "what is running in prod?" has a hash as its answer.
- **Trust boundaries in the cache.** Untrusted builds (fork PRs) read the cache but write to an isolated namespace; release keys are only writable by the release pipeline; artifacts entering release keys carry signatures from the build service.
- **Garbage collection as a designed cost.** Content-addressed stores accumulate unreferenced objects — every stale toolchain's outputs, every reverted branch's artifacts — so caches need an explicit GC (liveness = referenced by a recent build or a protected branch) with the same trade-offs Git's own GC has: cheap appends now, and a periodic, tuned reclamation pass that must never race a live build reading an object it just fetched.

## Interview Questions

1. Explain why a remote build cache is only as safe as its key. Enumerate five inputs that naive keys omit, and for each give the failure it produces when it changes.
2. What exactly does "reproducible build" promise, and why is that promise the precondition for build-once-promote-many? What incident response capability does it restore?
3. Design the cache-access policy for a CI system that builds both untrusted fork PRs and trusted release branches. Which direction of trust (read vs write) is dangerous, and why?
4. A lockfile pins dependencies but your team still sees "works on my machine." What is the missing pin, and how do container digests and toolchain manifests close the gap?
5. Connect the memoized-build view to incremental computation generally: what plays the role of the dependency graph, the dirty mark, and the memo table, and where does the analogy strain?

## Key Takeaways

- A build is a memoized function over an input graph; a build cache is only as trustworthy as the completeness of its key — every "works on my machine" is an undocumented input.
- Reproducibility (same input hash → bit-identical output) is what makes caches shareable and rebuilds meaningful; without it, reviewed source and running binary are unlinked and rollback is archaeology.
- Cache poisoning propagates silently through exactly the mechanism that makes caches fast — trust the key, get the wrong bits — so trust boundaries, signatures, and attestation are cache features, not add-ons.
- Lockfiles pin the dependency tree, hermetic toolchains pin the environment; both layers of pinning are required for key completeness, and teams that do only one still get burned.
- The whole apparatus is the content-addressing principle — hash the content, not the location — with one sharpening: in a build cache, a key collision or alias executes a different program, so hashing is a security mechanism here.

## Cross-References

- [./git-cas.md](./git-cas.md) — Git as a Content-Addressed Store — the same hash-the-content principle: Merkle DAGs, immutability, dedup, integrity, and its costs.
- [./dependency-resolution.md](./dependency-resolution.md) — Dependency Resolution — the topological scheduling of the build graph and how cycles and version selection break it.
- [./incremental-computation.md](./incremental-computation.md) — Incremental Computation — dirty propagation and memoized results; the build cache is that pattern with a remote memo table.
- [../followup-tree/hash-tables.md](../followup-tree/hash-tables.md) — Hash Tables — the hashing and bucketing foundations under every content-addressed key, plus collision reasoning.
- [../../git/internals.md](../../git/internals.md) — Git Internals — the object model that makes commits content-addressed and the provenance chain glueable to build artifacts.
- [../../compilers/README.md](../../compilers/README.md) — Compilers Track — the compilation pipeline whose caching and hermeticity this page treats as one memoized function.
