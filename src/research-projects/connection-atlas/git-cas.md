# Git as Content-Addressable Storage: One Idea, Many Systems

## Overview

Git's genius is not version control — it is storage design. Every object Git stores (blob, tree, commit, tag) is named by the SHA-1 hash of its own content: `sha1("blob 12\0Hello, Git\n") = b7aec520dec0a7516c18eb4c68b64ae1eb9b5a5e` (verified in this repo's own [../../git/internals.md](../../git/internals.md)). Content addressing is a single decision that buys four properties at once: the *name* is derived from the *bytes* (naming), rehashing verifies the bytes (integrity), identical bytes share one object (dedup), and immutable names can be cached forever (cacheability). Once you see that, a dozen unrelated systems snap into focus: Nix's store, Docker/OCI layers, IPFS, Bitcoin's block chain, restic/borg backups, and the content-hashed `app.3f9a2c.js` your bundler emits. They are all the same machine.

This page explains Git's object model and content-addressable storage (CAS) independently, names the shared principle, and is honest about Git's deviations from naive CAS — packfiles, reachability-based GC, and the small mutable layer that makes a purely immutable store usable.

## The Two Sides, Independently

**Git's object model.** Four object types, all content-addressed. A **blob** holds file bytes (no name, no metadata — the name lives in the tree, which is why renames are free). A **tree** maps names and modes to blob/tree hashes — one per directory. A **commit** points to a root tree plus parent commits and metadata. Because a tree's hash covers its entries' hashes, and a commit's hash covers its tree's hash, the commit is the root of a **Merkle DAG**: changing one byte in one file changes that blob's hash, which changes the containing tree's hash, up to the root, which changes the commit hash. One 40-hex-digit string transitively authenticates the entire history it roots. Git then wraps this immutable core in deliberately *mutable* conveniences: refs (branch/tag names → commit hashes), the index (staging area), and the working tree.

**Content-addressable storage beyond Git.** Nix stores every build result at `/nix/store/<hash>-<name>`, where the hash covers the derivation's inputs — change a dependency and the store path changes, so different versions coexist without conflict and environments are reproducible by construction (the "purely functional deployment model," Dolstra 2006). Docker/OCI images are stacks of layer tars addressed by digest; `FROM node@sha256:…` pins not a tag but bytes. IPFS generalizes to a peer-to-peer CAS: files are chunked, chunks hashed (often content-defined chunking), the chunk hashes built into a DAG addressed by a CID, and anyone holding a CID can fetch and *verify* the bytes from any peer. Bitcoin links each block header to the previous block's hash and commits to transactions via a Merkle tree in the header. Backup tools (restic, borg) split files into deduplicated chunks and structure snapshots as hash-linked trees; a second snapshot of a mostly-unchanged filesystem adds only new chunks. Front-end CDNs cache `bundle.<contenthash>.js` with `Cache-Control: immutable` because the URL *is* the integrity check — a changed file necessarily has a changed URL, which is what makes cache invalidation trivial.

## The Shared Principle

**Hash the content, not the location.** Deriving identity from content rather than from name/path/timestamp unifies naming, integrity verification, deduplication, and cacheability into one function H(content) = name. The systems above differ in what they hash (file bytes, derivation inputs, layer tars, chunks, block headers) and in where they draw the DAG, not in the principle. Its corollary, the **Merkle property**, is what makes the idea scale: if a graph's node hashes cover their children's hashes, one root hash authenticates the entire graph, so integrity checks and comparisons ("do we have the same tree?") reduce to comparing/verifying a single digest.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS across Git, Nix, Docker, IPFS, restic, CDNs | BREAKS (per-system deviations from naive CAS) |
|---|---|---|
| Name = H(content); verify = recompute | Universal; tampering anywhere is detected at the root | Nix hashes are *input*-addressed by default: the store path promises the inputs, not the output bytes — a non-hermetic build can produce different outputs under the same name (content-addressed derivations remain experimental) |
| Identical content stored once | Blobs, layers, chunks, blocks all dedup | Git goes further than identical-content dedup: **packfiles delta-compress similar-but-different objects** (window search over likely-similar blobs), which naive CAS has no concept of |
| Immutable objects, so caches never invalidate | `immutable` CDN caching, Nix coexistence of versions, layer pull-by-digest | Git must still *delete*: objects orphaned by history rewriting (amend, rebase, reset) would accumulate forever in a pure CAS, so Git runs **reachability-based GC** — prune objects not reachable from refs/reflogs after a grace period (default ~2 weeks for reflog-referenced objects) |
| One root hash authenticates the DAG | Commits, CIDs, block headers, manifest digests | Git's *index* (staging area) and working tree are mutable state *outside* the CAS — the object store is immutable, but the tool's usability layer is not |
| Hash collision resistance | All systems assume H is collision-resistant | SHA-1 is formally broken (the SHAttered collision, 2017); Git responded with real-world hardening: collision detection in sha1dc (Git ≥ 2.13) and SHA-256 repository support (Git ≥ 2.29, transitional) — IPFS/Bitcoin use SHA-256-family digests |

The deepest conceptual break: **a naive CAS is append-only and immortal, but real systems need forgetting.** Git solves it with reachability (graph algorithm + reflog grace), IPFS with pinning (hold a CID or the GC may collect it), Docker with registry retention policies, restic with `forget`/`prune` commands. "Content addressing" names the immutability mechanism; *garbage collection policy* remains a per-system design decision layered on top — and it is where the systems differ most.

## A Concrete Worked Example

**The one-line-change commit.** A repo has 1,000 files across `src/` (`src/lib/` nested two levels). You edit one line of `src/lib/engine.py` and commit. New objects: 1 blob (new file bytes), 1 tree for `lib/`, 1 tree for `src/`, 1 root tree, 1 commit = **5 objects**. A naive "snapshot per commit" CAS would store all 1,000 file contents again = 1,000 blobs (+ trees): Git's Merkle structure reuses ~99.5% of storage *automatically*, with no delta algorithm involved — pure identical-content dedup through the DAG. Multiply by history depth: a 10,000-commit repo effectively stores changes, not states, without ever running a "diff" algorithm on the write path. (Deltas come later, in packing, as a secondary compression layer.)

**Dedup and integrity in the same number.** A team commits a 10 MB binary ten times with trivial edits between; if content repeats (e.g., rebuilt artifacts with identical bytes), the blob is stored once — 10 MB, not 100 MB. And any corruption of that blob — bit rot on a backup drive, a malicious edit — is caught by the tree that references it: the recomputed hash no longer matches the recorded 40-hex name. Integrity is not an added checksum layer; it *is* the naming scheme.

## When This Connection Is Useful

- **Problem-solving heuristics.** When you see "immutable," "digest," "pinned," or "content-defined chunking," immediately infer the full bundle: cheap verification, free dedup, permanent cacheability, append-only storage — and then ask the follow-up question that separates designs: *who collects the garbage?* (Git: reachability from refs. IPFS: pinning. restic: forget/prune. Nix: `nix-collect-garbage` with GC roots.)
- **Interview answers.** "Design a container registry / backup system / artifact store" becomes derivable: content-address objects → Merkle-DAG manifests → mutable tag layer over the immutable core → GC by reachability → serve by digest with immutable caching. "Why is `git rebase` cheap?" — only new objects are created; unchanged blobs/trees are shared by hash. "Why do CDNs cache hashed assets forever?" — name = content ⇒ invalidation is unnecessary, not hard. Saying "this is the same principle Git uses" with the mechanism, not just the label, is the differentiator.
- **Engineering decisions.** Prefer content-addressed artifacts in CI (cache keys = input hashes; correctness is automatic, not policy). Pin dependencies by digest, not mutable tags, when reproducibility matters. Treat "the store" as append-only and design GC explicitly — the most common CAS-in-production bug is unbounded growth because nobody designed the forgetting layer.

## Interview Questions

1. Compute Git's blob hash scheme for the string "Hello, Git\n" and explain what three problems (naming, integrity, dedup) the single SHA-1 solves at once.
2. Explain why changing one line of one file in a 1,000-file repo creates roughly five new objects. Where exactly does the storage reuse come from, and what algorithm does Git *not* run to get it?
3. Naive CAS never deletes. Describe Git's reachability-based GC, IPFS's pinning, and restic's forget/prune as three answers to the same problem — and state the trade each makes.
4. Nix store paths are input-addressed, Git commits are content-addressed. Why does this difference matter for build verification, and what do content-addressed derivations promise?
5. SHA-1 is broken (SHAttered, 2017). What did Git actually do in response, and why was the practical risk lower than the academic result suggests?

## Key Takeaways

- Content addressing — hash the content, not the location — unifies naming, integrity, dedup, and cacheability in one function; Git is its most-taught instantiation, not its only one.
- The Merkle property (node hashes cover children) makes one root digest authenticate an entire graph; this is why a commit hash pins a full history and a CID pins a file DAG.
- Git deviates from naive CAS in two load-bearing ways: packfile delta compression (similarity, not identity) and reachability-based GC (forgetting as a first-class mechanism).
- Every CAS system needs a garbage-collection policy layered on its immutability; the differences between Git, IPFS, Nix, restic, and Docker registries are mostly *forgetting policies*.
- Immutable names plus mutable pointers (refs, tags, GC roots) is the recurring architecture: a small mutable layer makes a large immutable store usable.

## Cross-References

- [../../git/internals.md](../../git/internals.md) — Git Internals — object model, hashing, and packing in full (source of the verified blob hash above).
- [../../git/advanced.md](../../git/advanced.md) — Advanced Git — reflog, rewrite history, and the reachability rules GC depends on.
- [../../references/storage-reference.md](../../references/storage-reference.md) — Storage Systems Reference — CAS-adjacent storage systems survey.
- [../../networks/cdn/how-it-works.md](../../networks/cdn/how-it-works.md) — How CDNs Work — immutable caching and cache-busting by content hash.
- [../../cloud/virtualization/vm-vs-container.md](../../cloud/virtualization/vm-vs-container.md) — VMs vs Containers — where image layers and digests fit in containerization.
- [./dependency-resolution.md](./dependency-resolution.md) — Dependency Resolution — content hashing as the correct incremental-rebuild oracle (Bazel/Nix).
- [./gc-memory-management.md](./gc-memory-management.md) — GC and Memory Management — reachability as the shared liveness definition.
- Nix: Dolstra, E., *The Purely Functional Software Deployment Model*, PhD thesis, Utrecht University, 2006.
- IPFS: Benet, J., "IPFS — Content Addressed, Versioned, P2P File System," arXiv:1407.3561, <https://arxiv.org/abs/1407.3561>.
- Git internals book: <https://git-scm.com/book/en/v2/Git-Internals-Git-Objects>; SHA-1 collision result: <https://shattered.io/>.
