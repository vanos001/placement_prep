# Git Workflow Assumptions: What "The History Is There" Silently Promises

## Overview

Git is a content-addressed database wearing a version-control interface, and most workflow assumptions are claims about that database made by people who have never looked at it as one. This chapter audits five: that history is immutable, that merge and rebase produce equivalent results modulo cosmetics, that a clean working tree means the work is pushed, that tags are immutable anchors, and that force-push only affects the person who runs it. Each is false in a specific, demonstrable way, and each failure mode has the same root: Git's actual guarantees are about *objects and references*, while workflow assumptions are about *narratives*. The database promises reachability, not narrative, and the gap between the two is where commits are lost, releases move, and teammates' days disappear.

The data-model mechanics — objects, hashes, DAG reachability, and why Git is structured this way — are the connection atlas's Git-CAS chapter; here the subject is what daily commands promise and what they actually do. The book chapters on internals, rebasing, tags, and remotes carry the command-level mechanics, and Pro Git is the canonical external reference. The five assumptions are ordered by how silently they fail: immutability at rewrite time, merge-vs-rebase at bisect time, clean-tree at handoff time, tags at release time, and force-push at other people's convenience — never the pusher's.

## Assumption 1: "Git History Is Immutable"

### The taught rule

A commit, once made, is permanent; the hash identifies it forever; history is an audit record.

### How it fails

Git's object store is append-mostly, not immutable in the narrative sense: commits become *unreachable*, not deleted. `commit --amend`, `rebase`, `reset --hard`, and `filter-repo` write new objects and move references, leaving the old objects until garbage collection prunes them (subject to reflog expiry — 90 days by default for reflog-reachable entries). What "immutable" actually buys is narrower: a given hash always refers to the same content, and nothing is destroyed *immediately*. The audit-record claim also fails because history is rewriteable by anyone with push rights: protected-branch rules are hosting-platform policy, not a property of Git, and a local repository has no policy layer at all. Hash identity also invites an over-claim: the same change applied on different bases yields different hashes — cherry-picks and rebases create content-similar but hash-distinct objects, which is why tooling that tracks "the same commit" across branches by hash breaks.

### Failure scenario

An engineer runs `git reset --hard HEAD~3` to discard three messy commits — then realizes the second contained the only copy of a fix. `git log` shows nothing, because log walks reachable history. The safety net works here: the reflog still references the commits for ~90 days, and recovery by hash restores the work — the mechanism the taught rule never mentions. It turns permanent only when time passes, or when a fresh clone (which has no reflog — reflogs are local and never pushed) runs `git gc --prune=now`, after which the objects survive only on clones that happened to fetch them. The corrected mental model: *hashes are immutable, history is not; durability comes from reachability (refs, reflogs, remote branches), and reflogs are per-clone local state that expires.*

### Detection heuristic and what to assume instead

Detection: before any history-rewriting operation, record the current head's hash in a scratch note or `git branch backup/pre-rebase-$(date +%s)` — a tag-like ref prevents GC; treat `git reflog` as a *local, expiring* recovery tool, not a backup. Corrected statement: *history is an expiring, rewriteable projection over an immutable object store; permanence is a property of references you create deliberately (branches, tags, pushed remotes), not of commits themselves.*

## Assumption 2: "Merge and Rebase Produce Equivalent Results Modulo Cosmetics"

### The taught rule

Whether you merge or rebase, the code ends up the same; it is a style preference (some teams like merge commits, some like straight lines).

### How it fails

The two operations produce *different DAGs with different properties*, and the properties matter operationally. A merge records both parent histories and one conflict resolution; bisect over the result converges on the merge commit itself, whose diff is often a franken-diff that explains little. A rebase linearizes: each commit is *re-created* on the new base with new hashes and per-commit conflict resolutions; the final tree can equal the merge's tree while every intermediate commit differs, and bisect lands on the first *rebased* commit that broke — which may not exist in the author's local history at all. Three second-order effects follow. *Conflict resolution multiplicity:* rebase resolves conflicts N times (once per commit), merge once — N chances to resolve inconsistently. *Semantic loss:* rebase erases the branch's true point of origin, so "this was built against the June base" is no longer answerable from history. *Test equivalence:* CI tests the final tree, which is equivalent — but bisect and archaeology test *commits*, which are not.

None of this says rebase is wrong; it says the choice is a trade between bisectability of a linear narrative and fidelity of the recorded process — a real decision, not cosmetics.

### Failure scenario

A feature branch rebases onto main three times over two weeks, each rebase re-resolving the same conflict slightly differently. The final tree is correct; CI is green; the merge lands as a fast-forward. Two months later, a memory regression is traced to a boundary in that file. Bisect walks the linear history and reports the whole feature's single squashed entrypoint as the culprit — a commit with a 40,000-line diff. The team needed to know which of six incremental commits changed the resolution order; that decomposition exists only in the author's abandoned local reflog, under different hashes. The corrected practice: pick rebase or merge per branch *before* starting, record the choice in the workflow doc, and when rebasing long-lived branches, squash at the end so the linear history's unit of investigation matches the author's unit of work — the mismatch is what made the bisect answer useless.

### Detection heuristic and what to assume instead

Detection: ask "what is the natural unit of investigation?" before choosing the integration strategy for any history a regression may later be bisected through; with rebase, prefer squash-merge so the linear history's commits are self-contained units. Corrected statement: *merge and rebase produce the same tree with different histories — different commit granularity, different bisect behavior, different conflict-resolution multiplicity — and the choice should be made for the debugging workflow you will run later, not for the graph's appearance today.*

## Assumption 3: "A Clean Working Tree Means the Work Is Pushed"

### The taught rule

`git status` says "nothing to commit, working tree clean"; everything is saved and safe.

### How it fails

The working tree, the local repository, and the remote are three different storage layers, and "clean" describes only the first. Clean tree means: no uncommitted *modifications to tracked files* — it says nothing about (a) untracked files (`git status` lists them but a careless `git clean` or a `.gitignore` entry hides them entirely), (b) commits that exist only on local branches, ahead of upstream (visible via `git status -sb` or `git log @{u}..`), (c) stashed work (a stack of commits on a special ref — invisible in log, prunable by reflog expiry), and (d) detached-HEAD commits, referenced by nothing except HEAD's reflog entry — check out elsewhere and they are reachable only through reflog, gone on a fresh machine or after expiry. The classic handoff failure: "I finished, tree is clean, laptop reimaged" — with commits never pushed because the branch's upstream was never set, so a bare `git push` did nothing.

### Failure scenario

An engineer hotfixes from a detached SHA during an incident, commits twice, checks out main to verify, confirms a clean tree, and reimages the laptop that evening. The commits existed only in that clone: detached-HEAD work, no branch, no push, reflog destroyed with the disk; the production fix had to be reverse-engineered and re-authored. The post-incident policy: `git status -sb` (which surfaces ahead/behind) as the habit instead of `git status`, push immediately after any commit intended to survive, and a team norm that a "finished" task means *the remote has the commit*, not that the local tree is tidy.

### Detection heuristic and what to assume instead

Detection: end-of-day `git status -sb` on every repo (looking for ahead counts), `git stash list` before any cleanup, and CI-level hygiene: a bot that flags branches with unpushed commits older than a day. Corrected statement: *clean describes the working tree only; durability is a property of pushes — untracked files, stashes, and detached-HEAD commits live on the most expendable storage in the system, the laptop.*

## Assumption 4: "Tags Are Immutable Anchors"

### The taught rule

A tag marks a release forever; `v1.2.0` means the same commit today and in five years; deployments and provenance can anchor on tags.

### How it fails

Tags are references, and *movable* ones: a lightweight tag is a bare pointer; an annotated tag is an object (message, date, optional signature) pointing at a commit — but the *reference* can be deleted and recreated anywhere (`git tag -f`), and `git push --force` with a refspec moves it on the remote. Nothing in Git prevents this; protection is hosting-platform policy (protected tags) or signatures — and signatures authenticate *who created the tag object*, not that the reference still points at it. The consequence reaches beyond Git: CI pipelines and deploy systems that key on tags ("deploy on tag push") redeploy whatever the tag now names; artifact systems that tag images with the same version string inherit the ambiguity, since a Docker tag is mutable the same way; and checksum-based provenance anchored on "the v1.2.0 tag" silently re-anchors when the tag moves. Release automation adds the daily form: a script that re-tags `latest` during releases is force-moving a tag by design.

### Failure scenario

A release engineer rebuilds a release branch after a cherry-pick and re-points `v2.4.0` at the new commit with `git tag -f v2.4.0 && git push -f origin v2.4.0` — a documented "retagging" step in the team's process. Two downstream systems disagree: the artifact store published `v2.4.0` artifacts from the *first* commit (its tag-push hook fired then), while the deploy pipeline, triggered by the second push, deploys artifacts from the *second* commit under the same name. A customer's bug report cites "v2.4.0" and reproduces on one, not the other; the team spends two days discovering which SHA each consumer actually had. The corrected practice: versions are *names for one specific object forever* — a moved version tag is always a new version (v2.4.1 or v2.4.0-2) with its own tag, protected on the remote, and CI verifies tag signature plus target hash before publishing anything.

### Detection heuristic and what to assume instead

Detection: audit CI triggers for tag-based deployments, check that protected-tags is on for release patterns, and verify provenance by hash in artifact metadata, never by tag string alone. Corrected statement: *tags are mutable references with optional signatures; immutability comes from platform policy and from the discipline of never re-pointing a published name — anchor provenance on hashes, use tags as human-readable labels for those hashes.*

## Assumption 5: "Force-Push Only Affects Me"

### The taught rule

`git push --force` (or `--force-with-lease`) rewrites my branch; the pain is mine — my teammates just need to rebase.

### How it fails

Force-push changes a shared namespace, and every consumer of that namespace has state keyed on it. *Collaborators:* their local branches diverge; the common outcome is a new commit stacked on the pre-rewrite base, which the next force-push discards. *CI and automation:* pipelines that cache by branch name can build from a stale checkout fetched before the rewrite, publishing artifacts that match no current ref. *Name-keyed deployments:* environments deployed "from branch X" deploy whatever X names at deploy time — a force-push between two deploy steps deploys two different histories under one change ticket. *Open PRs:* force-pushing rewrites the review record — comments anchored to old commits' lines point at rebase-created replacements, weakening review context exactly where it matters most. And force-pushes to *default* branches rewrite the history every future clone sees — every consumer, not just collaborators.

The rescue here is `--force-with-lease`, which fails if the remote ref moved since your last fetch — it protects *you* from overwriting someone else's push, though it does nothing for the consumers of the rewritten history. The tooling asymmetry is the point: the pusher has reflog safety; everyone else has "hope you hadn't started."

### Failure scenario

A developer force-pushes a rebased `feature/search` to "clean up the history." A teammate had pushed two commits an hour earlier — the force-push erases them from the remote. The teammate's local copy still has them, but their next `git pull --rebase` lands both commits into the rewritten history in a form nobody reviewed, authorship dissolved. Two days later, a revert targeting a remembered commit range matches nothing in the rewritten history and fails silently, surfacing only when the feature reappears after the next merge. The corrected policy: force-push only to branches you solely own, named so by convention (`dev/<initials>/...`); shared branches get `--force-with-lease` at most, with a team announcement; and reverts always target content by hash verified against the current graph, not by remembered range.

### Detection heuristic and what to assume instead

Detection: enable platform settings that log and, where possible, restrict force-pushes per-branch; alert on force-push to shared and default branches; require `--force-with-lease` in tooling defaults so the unguarded form is the deliberate exception. Corrected statement: *a force-push rewrites a namespace others build on — commits, review threads, CI caches, and name-keyed deployments all key on it; the rewrite's blast radius is every consumer of the branch, and the safety net (reflog) exists only on machines that had the old commits.*

## Interview Questions

1. **You ran `git reset --hard` and lost commits. What actually happened, and what are the recovery paths in order?** The commits became unreachable, not deleted: check `git reflog` (local, expires ~90 days), recover by hash, and create a branch on the SHA to make it reachable — while remembering that fresh clones have no reflog and `gc` prunes.
2. **Why isn't merge-vs-rebase just style? Explain the bisect difference.** Merge preserves the author's commit decomposition and one conflict resolution; rebase re-creates commits with new hashes and per-commit resolutions. Bisect over a linearized history lands on rebased commits that never existed in the author's history — squash-merge fixes the unit mismatch, and the choice should serve the debugging workflow.
3. **`git status` says clean. Name four kinds of work it does not cover.** Untracked (especially ignored) files; unpushed commits on branches ahead of upstream; stashes; and detached-HEAD commits referenced only by reflog. Durability is pushes, not tidiness.
4. **What does a signed tag actually guarantee, and what doesn't it prevent?** It authenticates the tag object's creator and content at creation time; it does not prevent the *reference* from being deleted, re-pointed, or recreated unsigned. Protection comes from platform policy and hash-anchored provenance.
5. **Design the team rules under which force-push is safe.** Sole-ownership branch naming, `--force-with-lease` as the tooling default, restricted/alerted force-pushes on shared and default branches, and the discipline that rewrites of review branches invalidate line-anchored review comments — announce, then rewrite.

## Key Takeaways

- Hashes are immutable; history is not — commits are pruned by reachability and reflog expiry, so permanence is a property of references you create deliberately.
- Merge and rebase produce the same tree with different histories: commit granularity, bisect targets, and conflict-resolution multiplicity all differ — choose for the debugging workflow, and squash when the units must match.
- A clean working tree says nothing about durability; pushes, stashes, untracked files, and detached-HEAD commits live on different layers with different lifetimes — `status -sb` and immediate pushes are the habit.
- Tags are mutable references with optional signatures; releases should be anchored by hash with protected, never-re-pointed tags, because every name-keyed consumer inherits a moved tag silently.
- Force-push rewrites a namespace whose consumers (collaborators, CI caches, name-keyed deploys, review threads) key on it — `--force-with-lease` protects the pusher; policy protects everyone else.

## Cross-References

- [Git as a content-addressed store](../connection-atlas/git-cas.md) — the data model (objects, hashes, reachability) behind every assumption audited here.
- [Git internals](../../git/internals.md) — the book chapter on objects, refs, and reflogs as they actually work.
- [Rebasing](../../git/rebasing.md) — the book chapter on rebase mechanics that Assumption 2 audits from the workflow side.
- [Tags](../../git/tags.md) — annotated versus lightweight, signing, and the mutability Assumption 4 builds on.
- [Remotes](../../git/remotes.md) — tracking branches, push semantics, and where the ahead/behind counts come from.
- [Pro Git](https://git-scm.com/book/en/v2) — the canonical external reference (verified), whose internals chapter covers reflog and recovery in depth.
