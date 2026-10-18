# "We can always roll back the deploy, so the change is reversible"

## Overview

This page audits the sentence that makes risky deploys feel safe: the claim
that because the deployment system can roll back, the *change* is therefore
reversible. The reality is a sharp asymmetry that the sentence deletes: the
rollback button reverts *code*, but the change a deploy makes to the world is
mostly *data* — schema migrations have already executed, messages and emails
have already been sent, caches and downstream stores have already absorbed
the new writes, and external consumers have already integrated with the new
behavior. Reverting the binary returns you to an old program operating on a
new world, which is frequently worse than either state alone. The
consequence for review discipline is direct: a change that is reversible by
artifact is a category worth naming, and every category outside it needs a
written partial-reversal plan before it ships. This page states the claim
fairly, separates code reversibility from state
reversibility, and explains why the expand-contract migration pattern exists
precisely because rollback is partial. The worked counterexample is a
migration that rolls back "successfully" and leaves the system unable to
serve traffic.

## The Claim, Stated Fairly

The strongest common form of the claim is: "If the release goes wrong, we
just roll back — the deploy pipeline reverts to the previous artifact in
minutes, so no change we ship is permanent." Stated this way, the claim is
not carelessness; it reflects real capability. Blue-green and rolling
deployments genuinely can swap artifacts quickly, artifact registries retain
prior versions, and in the majority of releases the rollback path is the
fastest mitigation available and works exactly as advertised.

The claim deserves its fairness because rollback is real and saves teams
weekly. The question is whether "the deploy is reversible" honestly
compresses to "the change is reversible" — whether reverting the artifact
reverts the effects.

## Verdict

**Incomplete.** The claim is true in the regime where the change is
*computation only* — stateless logic, rendering, internal transformations —
and false to the degree that the change is *stateful*: any release that
moves data, changes schemas, emits side effects, or alters an external
contract leaves effects that the rollback button does not undo. The word
that carries the failure is "always": there is a well-defined class of
changes for which rollback returns you to a system that cannot work, because
the old code cannot operate on the new state.

## Why People Believe It

The kernel of truth is that artifact rollback works and works often. Most
deploys are logic changes, most logic changes are compatible with existing
state, and the visual feedback loop — deploy, watch dashboards, revert —
teaches that rollback is the undo key. Because the fast path is exercised
constantly and the failure path is rare, the distinction between reverting a
program and reverting a system-wide change stays theoretical until the day a
migration ships.

Teaching material reinforces the belief by treating "deploy" and "release"
as one event and "migration" as a footnote inside it. The deployment tool's
UI says "Rollback" next to every release, including releases that contain a
migration, with no warning that the button's guarantee stops at the artifact
layer. The fine print — that a rollback of a migration-backed release can be
*forbidden* — is documented in every migration tool's manual and read by
almost no one before the incident.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "The deploy rolls back" | True for the artifact: the pipeline can serve the previous binary quickly |
| "The change is reversible" | Only for pure logic; state changes (schema, data, caches) persist through an artifact revert |
| "Migrations roll back" | A down-migration that drops a column drops the data; "undo" destroys what the forward step created |
| "Side effects roll back" | Emails, webhook deliveries, payments, and queued messages already emitted are irreversible at the transport |
| "Caches roll back" | Poisoned or reshaped cache entries and derived stores keep serving old-code assumptions after revert |
| "The safe pattern" | Expand–contract: make a change that is safe under both old and new code, then remove the expansion after rollout |

The correct sentence: "Rollback reverts the code; the world keeps the
change. Reversibility is a property you design into the change — forward
compatible, expand-contract, side-effect-aware — not a property you get for
free from the deployment tool."

## Where It Breaks

**The migration counterexample, worked end to end.** Friday 14:00, a release
ships containing a migration that splits `users.name` into `first_name` and
`last_name` and drops `name` after a copy step. By 14:20, error rates climb
— a downstream consumer still reads `name` — and the on-call engineer clicks
rollback. The artifact reverts in four minutes. Error rates climb further:
the old code reads `name`, the column no longer exists, and every user
request now fails on a schema that the rollback did not restore. The only
honest mitigations are either a forward fix (re-add the column, backfill
from the split values where possible) or a restore from backup, which is a
catastrophe procedure measured in hours and losing hours of writes. The
rollback worked perfectly and made the outage worse.

**Side effects have no down-migration.** A release changes an email flow and
duplicates a notification send; rolling back the code does not unsent the
email. A billing change emits double charges to a queue that a consumer is
already draining; the queue's contents survive the artifact revert, and
refunds are the remedy. Any system with outward effects discovers the
boundary of rollback exactly where the boundary of the *transaction* is:
inside the process, no; across the network and into the world, never. The
deployment pipeline is not a transaction manager, and "reversible" was a
property of the old transaction logs, not of the deploy.

**Caches and derived state lag the revert.** A release writes a new shape of
cached entity (new key layout, new embedded fields). The rollback returns the
old code, which parses the new-shaped entries and fails, or serves
half-migrated entries until TTLs expire. Schema-less caches are the classic
silent trap: the deployment diff shows no storage change, so the review sees
"reversible", while the cache migration has no rollback plan at all.
Stampedes compound it — the mass eviction that a fix requires can turn a
correctness incident into a capacity incident.

**Contracts flip under the revert.** A release teaches external consumers
new behavior: the webhook payload gains a field, the API tolerates a new
enum, the pagination semantics change for a week while clients adapt. Roll
the artifact back and those clients are now coupled to a behavior the old
code does not exhibit — the rollback itself becomes the breaking change.
This is the interface-level shadow of the state problem: the change
propagated into other people's code, and other people's code is never
covered by your pipeline's revert. Contract-testing discipline and
additive-only evolution exist for this reason: they bound how far a
behavior change can reach in the time a rollback needs to reach it.

**Why expand–contract exists.** The pattern is the institutional answer to
this audit: instead of one irreversible change, ship a sequence of reversible
ones. Expand: add the new column, keep the old, dual-write or backfill — a
state that old code tolerates. Migrate: move readers to the new shape while
the old shape still exists. Contract: remove the old column in a *later*
release, after the new code is fully rolled out and the old code is gone.
Every step is individually rollback-safe because no step leaves the system
unable to run the other version. The existence of the pattern is the
clearest evidence that "always reversible" was never true: teams needed a
discipline to make *some* changes reversible, because the button alone does
not.

## Practical Implications

- Classify every release before shipping: pure logic (rollback-friendly) or
  stateful (rollback is partial — write the incomplete-reversal list into
  the change review).
- Gate migrations out of the same trigger as code rollback: deploy schema
  changes on the expand–contract schedule, with the contract step scheduled
  after full rollout, never bundled with the feature release it enables.
- Treat outbound side effects as un-rollback-able: for any release that
  changes a send, a charge, or a webhook, ship the effect behind a flag and
  canary the emission path, because the only undo is compensation.
- Plan cache and derived-store compatibility explicitly: version cache keys
  or shapes so an artifact revert cannot be fed entries it cannot parse.
- Rehearse the "rollback is forbidden" branch: when the migration has run,
  the mitigation is forward fix or restore, and the on-call should know
  which one applies before Friday afternoon chooses for them.

## Interview Questions

### A release containing a destructive migration is failing in production. What does "roll back" mean here, and what do you actually do?

Rolling back the artifact reverts the binary but not the schema, so old code
will hit new state and the outage typically deepens. The real options are a
forward fix (restore compatibility, re-add what was dropped, backfill) or a
restore from backup, which costs RTO and RPO. A strong answer distinguishes
artifact rollback from state rollback and chooses the forward fix by default.

### Explain expand–contract migrations and why the pattern exists.

Because a single state change must be compatible with two versions of the
code during rollout, and no single migration can be safe for both while
being what you ultimately want. Expand adds the new state without removing
the old, migrate moves traffic, contract removes the old only after the old
code is gone. Every step is rollback-safe, which is exactly the property the
naive one-step migration lacks.

### Your service sent 50,000 duplicate payment notifications due to a bad release, and the code was rolled back within minutes. Why is the incident not over?

The side effects are durable: the notifications and any triggered downstream
actions persist outside the service's process boundary, and the queue may
still hold work the old code will process differently. Reversal now means
compensation — refunds, corrections, customer communication — driven from an
audit log, not from the deployment tool. Rollback bounds future damage; it
does not settle past damage.

### How do you decide whether a given change is "reversible by rollback"? Give the checklist.

One: does the release contain schema or data movement? Two: does it emit
outbound effects (email, payment, webhook, third-party API)? Three: does it
change cached or derived representations? Four: does it change a contract
external consumers integrated against? Zero yes answers means the artifact
revert is a genuine undo; each yes means a specific partial-reversal plan is
required, written down before ship.

## Key Takeaways

- Rollback reverts the artifact; the change's stateful effects — schema,
  data, messages, caches, contracts — survive it, and old code on new state
  can be worse than either alone.
- Destructive migrations make rollback forbidden, not merely slow; the
  down-migration drops data and the honest mitigation is forward fix.
- Side effects have no down path: compensation is the only undo, so the
  emission path needs flags and canaries more than the code path does.
- Expand–contract is the discipline that manufactures reversibility step by
  step; its existence is proof that rollback alone is partial.
- Ask "what does the world look like after the revert?" before shipping;
  if the answer includes any state the old code cannot run on, the change
  is not reversible yet.
- Name the reversibility category in review: "artifact-reversible" is a
  property to be earned by the checklist, not assumed from the tooling.

## Cross-References

- [Follow-up Tree: Zero-Downtime Migrations](../followup-tree/zero-downtime-migrations.md)
  — the escalation chain that drills the fix this audit motivates: this page
  establishes *why* rollback is partial, that ladder rehearses the
  deploy-gating, backfill, and contract-last ordering that makes changes
  safe to ship anyway.
- [Connection Atlas: Migrations & Deploy Coupling](../connection-atlas/migrations-deploy-coupling.md)
  — the mechanics of why schema changes couple deploys to databases; this
  page covers the reversibility semantics, that page covers the coupling
  and scheduling.
- [Misconception: "We have backups, so we can recover"](./backups-mean-recovery.md)
  — the adjacent recovery claim: backups restore after catastrophic loss
  and cannot selectively undo one release's writes; this page is about
  undoing a change, that one about restoring a system.
- [Misconception: "All tests pass, so the code is correct"](./green-tests-mean-correct.md)
  — the testing sibling: a green suite plus a green rehearsal of the
  rollback path still samples only the states you thought to test.
- [Schema Migrations](../../dbms/advanced/schema-migrations.md) — the
  engineering of migration safety, versioning, and down-strategies.
- [Canary Releases](../../sre/canary-releases.md) — bounding the blast
  radius of the stateful changes that rollback cannot fully reverse.
- [Failure Casebook: Knight Capital 2012](../failure-casebook/knight-capital-2012.md)
  — the deploy where "undo" was ambiguous: old code reactivated on new
  flags, and the reversal executed the damage again.
- [Why-Not Handbook: Canary vs Blue-Green](../why-not-handbook/canary-vs-blue-green.md)
  — the deployment strategies that make artifact rollback fast, and the
  limits of what fast reversion can mean.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- M. Kleppmann. *Designing Data-Intensive Applications*. O'Reilly, 2017 —
  Chapter 4's treatment of schema evolution and backward/forward
  compatibility, cited by title.
- Meta Engineering. *Orienting database changes at Facebook scale* and
  Shopify Engineering's schema-change guidance — industrial expand-contract
  practice, cited by title.
- U.S. Securities and Exchange Commission. *In the Matter of Knight Capital
  Americas LLC*, Administrative Proceeding File No. 3-15570, October 2013 —
  the release-process failure behind the $440M loss, cited by title.
- PostgreSQL Global Development Group. *PostgreSQL Documentation: ALTER
  TABLE* — which physical rewrites are transactional and why column drops
  are instantaneous and irreversible, cited by title.
- GitLab. *Post-mortem: GitLab.com database outage of January 31, 2017* —
  the recovery where the only "undo" was a restore, cited by title.
