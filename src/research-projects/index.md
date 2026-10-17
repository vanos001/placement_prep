# Research Projects

## Overview

Six connected research collections that study how technical knowledge behaves under pressure: how interview questions escalate, where textbook rules silently depend on assumptions they never state, how concepts taught in separate courses share one mechanism, why plausible alternatives to a working design fail, how real production systems have actually broken, and which widely repeated claims are false or incomplete. Each collection was written against the existing chapters of this book and links to them instead of restating them; the six projects cross-link to each other whenever the same concept appears from a different angle.

The unifying method is **interrogation, not accumulation**. A reference chapter tells you what a B+tree is; the Follow-up Tree shows the seven questions an interviewer will ask after you say that; the Assumptions Hunt shows the conditions under which "indexes make reads faster" quietly stops being true; the Why-Not Handbook shows what a hash index would have cost you and why the B+tree won anyway; the Atlas shows why B-trees, LSM trees, and skip lists are one idea applied to different storage physics; and the Misconception project shows which part of the "hash lookup is O(1)" claim survives scrutiny. Reading a topic through all six lenses is the fastest way we know to convert memorized material into reasoning that survives follow-up questions.

## The Six Projects

| # | Project | The question it answers | Start with |
|---|---------|------------------------|------------|
| 1 | [Interview Follow-up Tree](./followup-tree/index.md) | Where does this question go after the first answer? | Any topic you already "know" |
| 2 | [Hidden Assumptions Hunt](./assumptions-hunt/index.md) | Under what conditions is the textbook rule actually true? | Any rule you have memorized |
| 3 | [Concept Connection Atlas](./connection-atlas/index.md) | What one mechanism hides inside two separately-taught topics? | Two topics you learned separately |
| 4 | [Why-Not Handbook](./why-not-handbook/index.md) | Why is the plausible alternative worse here — and when would it win? | Any design decision you defend |
| 5 | [Real-World Failure Casebook](./failure-casebook/index.md) | How did a real system with smart builders actually break? | Any incident you only know by name |
| 6 | [Misconception Elimination Project](./misconceptions/index.md) | Is this commonly repeated claim true, incomplete, or false? | Any claim you have repeated yourself |

## How to Use

- **Interview sprint (1–2 weeks per domain).** Take one domain — say, databases. Read the [index chain](./followup-tree/database-indexes.md) in the Follow-up Tree, then the database isolation chapter in the Assumptions Hunt, then the index-structure comparisons in the Why-Not Handbook, then the [index data-structures connection](./connection-atlas/db-indexes-data-structures.md) in the Atlas, finishing with the "indexes always make databases faster" misconception. Six passes over one domain at six depths.
- **Depth building.** Work through a whole collection end to end. The collections are ordered internally from most-familiar to most-specialized topics, and every chapter ends with transferable reasoning heuristics rather than a summary of facts.
- **Incident literacy.** Read the [Failure Casebook](./failure-casebook/index.md) cases in order — deployment failure, control-plane coupling, resource exhaustion, partition tolerance, and safety-critical races — and keep [postmortem culture](../sre/postmortem-culture.md) open beside it.
- **Before a system design round.** The Why-Not Handbook's decision frameworks and the Atlas's [backpressure](./connection-atlas/backpressure.md), [scheduling and queueing](./connection-atlas/scheduling-queueing.md), and [TCP/distributed failure detection](./connection-atlas/tcp-distributed-failure.md) chapters are the highest-density preparation.

## Coverage Status

Each project maintains its own Coverage Ledger (topics, sources, honest gaps) in its index. Summary as of the October research rounds (initial build + expansion):

| Project | Files | Words (approx.) | Ledger |
|---------|-------|-----------------|--------|
| Interview Follow-up Tree | 15 | ~42,500 | [Ledger](./followup-tree/index.md) |
| Hidden Assumptions Hunt | 15 | ~40,200 | [Ledger](./assumptions-hunt/index.md) |
| Concept Connection Atlas | 17 | ~34,600 | [Ledger](./connection-atlas/index.md) |
| Why-Not Handbook | 15 | ~37,300 | [Ledger](./why-not-handbook/index.md) |
| Real-World Failure Casebook | 13 | ~35,300 | [Ledger](./failure-casebook/index.md) |
| Misconception Elimination | 19 | ~29,600 | [Ledger](./misconceptions/index.md) |

Ninety-four chapters plus this hub — fourteen follow-up chains, fourteen assumption audits, sixteen cross-domain connections, nineteen comparisons, twelve sourced incident case histories, and eighteen audited misconceptions.

## Method and Standards

- **Duplication policy.** Existing chapters remain the canonical reference; these collections analyze, connect, escalate, and challenge that material rather than re-teach it. Where another collection in this set owns an angle, the chapter links instead of repeating.
- **Citation discipline.** Prefer primary sources — RFCs, standards drafts, official engine documentation, regulatory orders, first-party postmortems, and peer-reviewed papers. Every external claim in the Failure Casebook is tied to a numbered primary source; interpretation is labeled as interpretation. Sources that could not be URL-verified are cited by title and author only, and unverifiable details are omitted or marked, never invented.
- **Verification policy.** Counterexamples and worked numbers were checked before publication. Complexity claims distinguish worst-case, average-case, and amortized analysis. Mermaid diagrams follow the repository's v11 syntax conventions.

## Cross-References

- [Interview Preparation overview](../interview/overview.md) — the question banks these projects escalate from.
- [Engineering Trade-offs](../trade-offs/README.md) — quick-reference comparison tables; the Why-Not Handbook provides their mechanism-level backing.
- [Failure Modes](../failure-modes/README.md) — the generic pattern catalog; the Casebook documents the named incidents behind the patterns.
- [Postmortem Culture](../sre/postmortem-culture.md) — the reporting discipline the Casebook applies to historical incidents.
- [Reference Libraries](../references/README.md) — the verified primary-source indexes used during research.
