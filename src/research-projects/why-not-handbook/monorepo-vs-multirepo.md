# Monorepo vs Multirepo: Atomic Coupling Against Autonomy at Scale

## Overview

Should many projects live in one version-control repository, or one repository per project? The question sounds like a git configuration choice, but it is a **coupling and coordination** decision. A monorepo makes a cross-service change a single commit: the API, its server, and its three clients move together, the type checker catches breaks before merge, and one bisects across the whole dependency graph. The price is scale — repository size strains VCS tooling, CI must learn to build only affected targets, and access control is coarse at the repository boundary. A multirepo grants each team a small kingdom: independent versioning, a private CI budget, clean ownership, and a read boundary that maps to team boundaries. The price is that atomicity becomes a human process — release trains, compatibility windows, and coordinated pull-request waves across repositories — and version skew accumulates silently at every contract edge.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **the monorepo converts coordination into tooling (build graphs, affected-target selection, atomic merges); the multirepo converts coordination into process (semver negotiation, PR trains, upgrade campaigns).** Neither dominates. Google and Meta run famous monorepos at extreme scale and built bespoke tooling to survive it; most open-source ecosystems run polyrepo because independent versioning *is* the product. Production organizations overwhelmingly live in the mixed middle — polyrepo with shared package registries, or monorepos with strict ownership directories — and the edge cases below show why the middle is not a compromise but the actual steady state.

## Step 1: The Problem and Its Constraints

The abstract shape: N services, libraries, and applications, owned by M teams, evolve against shared contracts. Constraints that decide the answer:

- **Change coupling.** Do services co-evolve weekly (a type change ripples through client and server), or do they stabilize behind contracts and drift apart for quarters? High coupling favors the monorepo's atomic commit; low coupling makes its coordination tooling overhead unearned.
- **Artifact distribution.** Are the outputs independently versioned products (libraries consumed by strangers, SDKs, CLIs) or internally deployed services? Multirepo's independent versioning is not overhead when the artifact *is* the release unit.
- **CI budget and build tooling appetite.** Monorepos need dependency-aware build systems that compute affected targets; without one, touching a shared utility triggers a full-repo build measured in hours. The tooling is an engineering investment with real staffing, not a config flag.
- **Access-control granularity.** Contractor isolation, proprietary modules, or regulated code segments require per-path read gating. Native git cannot do this within one repository; the VCS choice is sometimes an access-control decision in disguise.
- **Global reasoning needs.** Will engineers bisect a regression across service boundaries? Does anyone need to answer "what depends on this function?" exhaustively? The monorepo answers both mechanically.
- **Onboarding and tooling uniformity.** One clone-and-build recipe versus N of them; one lint/format/test matrix versus N diverging ones.

## Step 2: The Mechanisms

### Monorepo: one history, one build graph, atomic merges

- **Atomic cross-service change.** A single commit (or merge) can rename an API, update the server, and fix all clients. There is no window in which the repository is internally inconsistent, so there is no "deploy order" negotiation — the atomicity the commit provides at file level extends to the service graph.
- **The build graph is the architecture.** Systems of the Bazel class model every target and its dependencies; CI computes the transitive closure of a change and builds/tests only that. This is what makes 100,000-developer-scale monorepos possible — and what makes them fragile without it: the tooling is load-bearing, and building it (or adopting it) is the monorepo's true entry cost.
- **VCS scaling tax.** Full clones of a decade-old monorepo reach tens of gigabytes; history is global, so every developer pays for every team's past. Mitigations are structural: [sparse checkout](../../git/sparse-checkout-hosting.md), partial clones, and virtual filesystems that fetch blobs on demand (Google's and Meta's approaches are described in their engineering publications; see title-only citation below).
- **Global bisect and refactors.** A regression traced through service boundaries is found by bisecting one history. A global rename is one reviewed change, not a deprecation campaign. Type-level contracts break the build at merge time rather than at 3 a.m. in production.
- **Coarse access control and coarse ownership.** Read gating is repository-granular unless tooling adds path-based rules; CODEOWNERS-style files route review but do not gate reading. The repo boundary is also the trust boundary, which is why some organizations fragment *despite* wanting monorepo mechanics.

### Multirepo: independent versioning, boundaries you can draw on a chart

- **Version independence.** Each repository releases on its own cadence; consumers pin versions and upgrade deliberately. Contracts between repositories are enforced by semver and integration tests, not by the compiler — which means contracts *can drift* because nothing forces the consumer to update.
- **The cross-repo atomic change does not exist.** Changing an API and its consumers requires a PR train: add backward-compatible support, release, migrate consumers across N repositories, release those, then remove the old path. Each step is a human-scheduled event with its own review and deploy; the *compatibility window* is the process's atomicity substitute.
- **Ownership and access are crisp.** Repository boundaries are team boundaries: CI budgets, deploy pipelines, and read access all align. This is why multirepo is the natural shape for open source — the version boundary is the product boundary.
- **Tooling diverges by default.** Each repository grows its own build scripts, lint configs, and CI idioms. Unification (shared lint packages, golden templates) is a standing maintenance cost that the monorepo gets once instead of N times.
- **Version skew is the silent liability.** Consumers upgrade lazily; a producer's security patch reaches 80% of consumers in a week and the last 5% never. Nothing in the multirepo model *detects* skew — it surfaces as an incident.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Monorepo | Multirepo |
|----------|----------|-----------|
| Cross-service atomic change | Single commit/merge | PR train + compatibility window |
| Contract enforcement | Compiler/type-checker at merge | Semver + integration tests at runtime |
| Rollback of a change | Revert one commit | Revert + re-release across N repos, or pin-bump |
| Global bisect | One history | Archaeology across pinned versions |
| CI scope | Affected-target graph (tooling required) | Whole repo (small by construction) |
| VCS size/history | Global; needs sparse/partial clone | Local; small clones |
| Access control | Coarse (repo-granular) | Crisp (per-repo) |
| Tooling uniformity | One ecosystem, one place to fix | N ecosystems; drift by default |
| Dependency updates | One merge | N upgrade PRs; skew accumulates |
| Onboarding | Clone + one build recipe | N recipes; per-repo context |

The **enforcement-point relocation** deserves the arrow drawn: both models enforce contracts, but at different times with different blast radii. The monorepo enforces at merge time via the type system and build graph — failures are cheap, loud, and pre-deployment. The multirepo enforces at runtime via semver discipline and integration tests — failures are expensive, quiet, and post-deployment, because a consumer that never upgraded is a valid citizen of the graph. The monorepo trades setup cost for permanently cheaper failure; the multirepo trades per-change coordination cost for team autonomy, and pays for that autonomy in skew incidents.

## Step 4: When Each Wins

**The monorepo wins** when: services co-evolve (shared platform, tightly coupled product surface); the org needs global refactors and atomic contract changes routinely; cross-service regressions must be bisectable; and the org will fund build-graph tooling and VCS scaling work as first-class engineering. The decisive signal is change coupling measured, not felt: if a typical product change touches three repositories, the coordination tax is already being paid — the monorepo just makes it visible and mechanical.

**The multirepo wins** when: artifacts are independently versioned products consumed by outsiders (libraries, SDKs, open source — independent versioning is the deliverable, not overhead); teams genuinely stabilize behind stable contracts; access-control boundaries must match team boundaries (contractors, regulated code); and the org is small enough that duplicated tooling costs less than one build-infrastructure team. Autonomy is a real good: it is not stubbornness that keeps infrastructure teams separate from product teams, it is a different review culture and a different failure tolerance.

**The honest hybrid menu** — where production systems actually live:
- **Polyrepo with shared packages.** The dominant real-world shape: independent repositories plus a package registry (internal npm/PyPI/Maven) for shared code. The shared package re-introduces a coupling bus — and with it, exactly the upgrade-campaign problem the monorepo's atomic merge solves for free (edge case below).
- **Monorepo with strict ownership directories.** One repository, path-based CODEOWNERS, per-directory CI scoping, and sparse-checkout workflows; access control remains coarse, which is the boundary where some orgs stop.
- **Grouped monorepos ("polyrepo by domain").** A repository per business domain containing its services and clients — atomic within a domain, multirepo across domains. The coupling question is answered per boundary, which is usually how coupling actually distributes.

## Step 5: Edge Cases and Counterexamples

- **The shared package that never reached 2.0.** A polyrepo org ships `common-lib`; v2 fixes a critical flaw but requires each service owner to migrate call sites. Two years later, 31 of 34 services are on v2 — and the remaining three are owned by teams that dissolved, so v1 support cannot be dropped and v2's fix must be backported forever. The monorepo would have converted this into one reviewed commit; the polyrepo converted it into an organizational hostage negotiation. The mixed model does not eliminate the coordination problem — it relocates it into a maintenance deadlock that is harder to see.
- **Monorepo CI collapse without a build graph.** A 200-service monorepo uses per-directory CI scripts; a change to a shared utility triggers all 200 pipelines. Build queues hit four hours, engineers start batching unrelated changes into single PRs to amortize wait time, and review quality collapses — the CI failure *causes* worse merge hygiene. The fix (affected-target computation) is not an optimization; it is the difference between a monorepo and a shared directory.
- **The skew incident a monorepo would have caught at merge.** A producer adds a required field with a default; three consumers pinned to old majors send the old shape. Tests pass per-repo, production fails intermittently on the one consumer that never upgraded — discovered by customers. In a monorepo, the type change breaks all consumers at merge time, and the fix ships as one atomic change. The multirepo did not prevent the bug; it deferred it past every gate designed to catch bugs.
- **Access control forces fragmentation.** An org consolidates everything into a monorepo, then hires contractors who must not read payments code. Git has no per-path read gating; the choices are fragmented repositories for sensitive code, or third-party gating proxies that reimplement repository boundaries. The endgame is a "monorepo" that is actually several repositories glued by tooling — a reminder that read boundaries are a hard constraint the coupling argument cannot override.
- **Global bisect as the superpower.** A production regression appears after a deploy wave. In a monorepo, one bisect over one history localizes the cross-service culprit in hours, because the intermediate commits include *both* sides of every contract change. In a polyrepo, the same investigation reconstructs a timeline from five repositories' release tags and pinned versions — each an approximation. The monorepo's advantage is not speed polish; it is that the dependency graph's history exists in one causally ordered place.

## Step 6: Decision Framework

1. **Is the artifact independently versioned and consumed by outsiders?** Yes → multirepo; independent versioning is the product, not overhead.
2. **Do services change together weekly?** Yes → monorepo direction; the coordination tax is already being paid, so make it mechanical.
3. **Is fine-grained read access a hard requirement?** Yes → multirepo (or accept fragmentation); native git cannot gate reads within a repository.
4. **Will the org fund build-graph tooling and VCS scaling as products?** No → do not start a large monorepo; the entry cost is the tooling, not the directory layout.
5. **How many repositories does a typical change touch?** Three or more → consolidate toward a monorepo or grouped monorepos; one → multirepo is fine as is.
6. **Default in doubt:** start polyrepo for autonomous teams with stable contracts, add shared packages cautiously (they are a coupling bus), and consolidate into grouped monorepos when cross-repo PR trains exceed what review culture can absorb — then revisit annually, because the coupling pattern moves as the org does.

## Interview Questions

1. **What problem does a monorepo solve that shared packages in a polyrepo do not?** Atomicity. A cross-service change lands as one commit, enforced by the type checker at merge; with packages, the same change is an upgrade campaign across repositories whose consumers may never complete — version skew is undetectable until it is an incident. Packages re-introduce a coupling bus without the enforcement point.
2. **Why is "affected-target computation" load-bearing for a monorepo, not an optimization?** Without it, any change to shared code triggers full-repo CI; queues grow until engineers batch unrelated changes to amortize waits, degrading review quality. The build graph is what keeps the repo's atomicity affordable at scale — it is the mechanism that converts one big repository back into many effectively-independent build units.
3. **Name a case where multirepo is not just acceptable but the correct design.** Artifacts consumed by strangers: libraries, SDKs, open-source tools. Independent versioning *is* the release contract; consumers pin and upgrade deliberately. A monorepo would couple the artifact's release cadence to unrelated teams' churn.
4. **Your monorepo must host code contractors must not read. What are your options, and what does that reveal?** Fragment sensitive code into separate repositories, or deploy third-party gating that reimplements repo boundaries. It reveals that read boundaries are a hard constraint independent of coupling economics — the monorepo question is partly an access-control decision, and the honest answer sometimes fragments the repo anyway.
5. **Compare where each model enforces inter-service contracts, and the failure that follows.** Monorepo: at merge time, via compiler/build graph — loud, cheap, pre-deployment failure. Multirepo: at runtime, via semver and integration tests — quiet, expensive, post-deployment failure when a consumer never upgrades. The models trade enforcement cost against enforcement certainty.

## Key Takeaways

- The real variables are **change coupling** and **who consumes the artifact**: co-evolving services with internal consumers favor monorepo mechanics; independently versioned products favor multirepo boundaries.
- Each model relocates coordination: the monorepo converts it into tooling (build graphs, atomic merges, global bisect); the multirepo converts it into process (PR trains, semver windows, upgrade campaigns). Neither deletes it.
- The monorepo enforces contracts at merge time; the multirepo defers enforcement to runtime — cheap-loud versus quiet-expensive is the recurring trade.
- Shared packages in a polyrepo are a coupling bus: they recreate the upgrade campaign the monorepo solved, minus the enforcement point.
- The production steady state is mixed — grouped monorepos, polyrepo with registries, monorepos with ownership directories — because coupling distributes unevenly across org boundaries.

## Cross-References

- [Monolith vs Microservices](./monolith-vs-microservices.md) — the sibling comparison: the same coordination question one layer above, at the deployment boundary.
- [Git Workflow Assumptions](../assumptions-hunt/git-workflow-assumptions.md) — the silent promises ("the history is there") that repository strategy makes to every workflow built on it.
- [Git Workflows](../../git/workflows.md) — branching and release conventions inside either repository shape.
- [Git Internals](../../git/internals.md) — why history size, cloning, and partial fetch behave as described.
- [Sparse Checkout and Hosting](../../git/sparse-checkout-hosting.md) — the VCS-scaling mitigations large monorepos require.
- [Worktrees and Submodules](../../git/worktrees-submodules.md) — git's native attempts at multi-project layouts, and their limits.
- [Architecture Trade-offs](../../trade-offs/architecture-tradeoffs.md) — the quick-reference table for repository and service boundaries.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
- [Pro Git, 2nd edition](https://git-scm.com/book/en/v2) — the VCS mechanics underlying both strategies.
- [Martin Fowler: Microservices](https://martinfowler.com/articles/microservices.html) — the organizational-decomposition context in which this choice sits.
- Google and Meta's monorepo engineering publications ("Why Google Stores Billions of Lines of Code in a Single Repository"; "Scaling Mercurial at Facebook") — the virtual-filesystem and tooling evidence, cited by title.
