# Infrastructure as Code Overview

Infrastructure as Code (IaC) is the practice of managing and provisioning infrastructure through machine-readable definition files instead of console clicks, tickets, and one-off shell scripts. The moment infrastructure is expressed as code it inherits every property that makes software manageable: it lives in version control, it is reviewed in pull requests, it can be tested, linted, scanned, and reproduced on demand. Interviewers use IaC questions to probe whether you understand the *invariants* — idempotency, state, convergence, drift — rather than the syntax of one tool. This page is the landscape map; the deep dives are [Terraform](./terraform.md) (provisioning), [Ansible](./ansible.md) (configuration management), and [Beyond Terraform](./beyond-terraform.md) (OpenTofu, Pulumi, CDK, Crossplane). A consolidated question bank lives in [IaC Interview Questions](./interview-questions.md).

## Why IaC Exists

Manual infrastructure fails in three predictable ways, and IaC exists to eliminate each one:

- **Drift** — live systems are mutated in place: someone opens port 443 in the console during an incident and never backports it. Months later staging and prod are different animals, and "it worked in staging" becomes a lie. IaC makes declared config the source of truth and turns drift into a detectable diff (`terraform plan`) instead of an archaeology project.
- **Repeatability** — without code every environment is a snowflake built by whoever was on call that week. Rebuilding a region after an outage, standing up a compliance-test environment, or expanding to a new region become multi-day human projects. With IaC they are a re-run of a reviewed pipeline.
- **Review culture** — console changes have no diff, no reviewer, no history, and no rollback plan. A pull request that changes one security-group rule gets reviewed by the networking owner *before* it merges, not flagged in an audit *after* it ships. IaC moves infrastructure onto the same collaboration rails as application code: branching, review, CI gates, tagged releases.

The economic summary interviewers like: IaC trades a one-time learning-and-migration cost for a permanently auditable, reproducible, cheaper-to-operate estate — *"infrastructure gets the same lifecycle as software."*

## Imperative vs Declarative

The deepest divide in the tool landscape is *who computes the path from current state to desired state*:

| Aspect | Imperative | Declarative |
|---|---|---|
| Approach | "How to do it" | "What I want" |
| Example | Bash scripts, Pulumi | Terraform, CloudFormation |
| State | You manage | Tool manages |
| Idempotency | Manual | Built-in |

In practice the line is blurrier than the table suggests. Pulumi is declarative at the engine level (it computes a diff against state) even though you *author* in an imperative language; Ansible is declarative per-module but procedural per-play (tasks run in written order). The interview-safe framing: **declarative tools own the desired state and the convergence logic; imperative tools execute steps and you own the convergence logic.** Declarative wins for infrastructure because the desired state of a fleet changes far less often than the code that describes it, and a diff-able declaration is reviewable in a way a 300-line script never is.

## Mutable vs Immutable Infrastructure

| Aspect | Mutable | Immutable |
|---|---|---|
| Updates | SSH + configure in place | Replace entire instance |
| Tools | Ansible, Puppet | Packer + Terraform |
| Drift | Common | Impossible |
| Rollback | Manual | Switch to old image |

Mutable configuration management (patch in place) maximizes speed of small fixes and works well for stateful or long-lived systems (databases, bare metal). Immutable infrastructure (bake a golden image with [Packer](../cloud/packer.md), then replace instances) maximizes consistency — every deploy is a fresh boot from a known artifact, so "that one weird box" cannot exist. Modern platform teams are usually hybrid: immutable for the compute fleet, mutable configuration for the stubborn remainder, all driven from the same Git repos.

## State Management Concepts

Most IaC interview questions about "state" reduce to four ideas:

- **Desired state vs actual state** — the declaration (in Git) is what you want; the live world is what you have. The gap between them is the work to be done.
- **The state store** — tools like Terraform keep an extra artifact, a *state file*, mapping declared resources to real resource IDs. Ansible deliberately has none: it inspects live systems each run (stateless convergence). Kubernetes etcd is the state store for the cluster world.
- **Locking** — two writers converging on the same estate corrupt or race each other; locking serializes applies (S3+DynamoDB, Pulumi's backend, admission control in k8s).
- **Drift** — actual state moving without a declaration changing. Detected by re-planning or by continuous reconciliation; repaired by re-apply or by adopting the change into code.

Which tools keep a store — and what they can therefore do — explains most cross-tool behavior questions:

| Tool family | Persistent state store? | How it computes convergence |
|---|---|---|
| Terraform / OpenTofu / Pulumi | Yes — state file in a backend | Diff config vs state vs live (plan) |
| Ansible | No — inspects live hosts each run | Per-module check-then-act |
| Kubernetes / Crossplane | Yes — etcd, via declared objects | Controller reconciliation loop |
| Puppet / Chef | Server inventory (partial) | Agent pulls catalog, enforces it |

Tools with a store can *plan* — show you the work before doing it — but must protect that store (locking, encryption, backups). Tools without one are simpler to reason about but pay discovery cost on every run and cannot show a diff before acting. This single trade-off is the deepest idea in the section and answers half of all "why does tool X behave differently" questions.

## Push vs Pull Models

```text
Push:  CI/operator --apply--> [tool holds creds] --> Cloud APIs / nodes
Pull:  node/agent --poll--> declared state (Git/registry) --> converge self
```

| Aspect | Push (Terraform, Ansible, Pulumi) | Pull (Puppet/Chef agents, k8s controllers, GitOps: Argo CD, Flux) |
|---|---|---|
| Initiated by | CI or operator runs the tool | Node or controller reconciles continuously |
| Credentials | Tool holds broad cloud credentials | Nodes hold narrow read-only credentials |
| Drift window | Until the next apply (possibly forever) | Bounded by the reconciliation interval |
| Natural home | Provisioning, one-shot change sets | Continuous convergence, in-cluster config |

Neither model wins outright: provisioning a VPC is inherently a push (there is no "VPC agent" to pull), while keeping 500 deployed manifests in sync is naturally a pull. That is exactly why mature organizations run both — Terraform pushing infrastructure, GitOps pulling workloads — as covered in [GitOps](../cloud/cicd/gitops.md).

A second differentiator is **who holds credentials**: push tools need broad cloud credentials wherever they run (a compromised CI runner is an incident), while pull agents hold narrow read-only credentials and act only on their own scope. When an interviewer asks "why is GitOps more secure?", the honest answer is smaller credential blast radius plus bounded drift — not magic.

## The Tool Landscape

| Tool | Type | Language | Approach |
|---|---|---|---|
| **Terraform** | Provisioning | HCL | Declarative |
| **Ansible** | Configuration | YAML | Procedural |
| **Pulumi** | Provisioning | Any language | Imperative |
| **CloudFormation** | Provisioning | JSON/YAML | Declarative |
| **CDK** | Provisioning | Any language | Imperative → declarative |

The table above is the classic starter set; the full 2020s landscape adds a second ring of tools that matter in interviews:

| Tool | Niche | One-liner |
|---|---|---|
| **OpenTofu** | Terraform fork | Same HCL-and-state model, Linux Foundation, open licence ([opentofu.org](https://opentofu.org/)) |
| **Pulumi** | Dev-centric IaC | Real programming languages, engine still diffs state ([pulumi.com](https://www.pulumi.com/)) |
| **CDK / CDKTF** | App-team IaC | Languages compile down to CloudFormation / Terraform |
| **Crossplane** | Platform IaC | Infrastructure as Kubernetes CRDs, continuously reconciled |
| **Ansible** | Config management | Agentless SSH, procedural plays, no state file |
| **Cloud-init** | First boot | The bootstrap step before configuration management takes over |
| **Packer** | Image building | Bakes the golden images immutable fleets boot from |

```text
            ┌──────────────────── lifecycle of a machine ────────────────────┐
            │                                                                 │
  Packer    │   Terraform / OpenTofu / Pulumi / Crossplane                    │   Ansible
  bakes     │ → provisions network + compute (declarative, stateful)       →  │   configures
  image     │   Cloud-init runs at first boot                               │   running hosts
            └─────────────────────────────────────────────────────────────────┘
```

The boundary question — "which tool where" — is a standard interview probe; the canonical answer is Terraform (or a sibling) for *provisioning*, Ansible for *configuration*, Packer for *images*, as detailed in [Beyond Terraform](./beyond-terraform.md).

Read the two tables together and the landscape organizes into four questions: **provision vs configure** (Terraform-family vs Ansible), **DSL vs real language** (HCL vs Pulumi/CDK), **single cloud vs multi-cloud** (CloudFormation/CDK vs Terraform-family), and **push vs continuous reconcile** (one-shot tools vs Crossplane/GitOps). Every tool in the landscape is a point in that 4-axis space, which is why "compare tool X and Y" questions are answerable even for tools you have never installed.

## The IaC Maturity Ladder

| Level | Name | Behaviour | Signature smell |
|---|---|---|---|
| 0 | Manual | Console clicks, SSH | "Works on prod only"; no rebuild possible |
| 1 | Scripted | Ad-hoc bash/scripts in a wiki | Scripts rot; only the author dares run them |
| 2 | Declarative | Terraform/Ansible code in Git | State on a laptop; drift quietly ignored |
| 3 | Pipelined | CI plans on PR, applies on main | Plan posted to the PR; no human terminals |
| 4 | Governed | Policy-as-code gates, drift alerts | OPA/Sentinel checks; module registry |
| 5 | Platform | Self-service golden paths | Devs order infra via portal/CRDs, never touch IaC |

Interviews rarely name the ladder, but "where is your team on it and what is the next step" is exactly what a seniority probe is measuring. Moving from 2 to 3 (pipeline-only applies, humans lose terminal access to prod) is the transition most organizations are stuck in front of, because it is as much a process change as a tooling one. Levels 4–5 connect to [Policy as Code](../cloud/policy-as-code.md) and platform engineering.

When asked to place a team, look for the tell: if engineers can name which resources are manually managed, they are at level 2; if plan diffs appear on PRs, level 3; if a PR cannot merge because a policy denied an unencrypted volume, level 4. Describing *your own* position honestly — including the manually-managed exceptions everyone has — reads far better than claiming level 5.

## How Interviews Test IaC

Expect five archetypes, roughly in seniority order:

1. **Definitional** — declarative vs imperative, mutable vs immutable, push vs pull. Cheap; get them fluent.
2. **Mechanism** — what a state file contains, why locking exists, how a plan is computed, what "idempotent" means for a module. See [Terraform](./terraform.md).
3. **Design** — structure Terraform for three environments and forty services; module boundaries; workspaces vs directories. The graded part is trade-off articulation, not the layout you pick — say what each alternative costs.
4. **Debugging** — lost/corrupt state, stuck lock, a provider upgrade breaking a plan, unexplained drift. These are story questions: name the diagnosis steps out loud.
5. **Judgment** — Terraform vs Pulumi vs CDK vs Crossplane; when Ansible alone is fine; where policy-as-code belongs. The correct answer is a decision procedure, not a brand.

For the design archetype, a concrete prompt looks like: "Forty microservices, three environments, two clouds — lay out the repos, the state files, and the CI gates, and justify who can apply what." Strong candidates sketch repo layout, state boundaries, and the review/policy gates as three separate diagrams-in-words before arguing any tool choice.

## What IaC Does Not Solve

Honest answers about limits read as senior:

- **Runtime behavior** — IaC provisions and configures; it does not make an application resilient. Availability comes from architecture (retries, failover, capacity), and a perfectly IaC-managed stack can still fall over.
- **Secrets lifecycle by itself** — IaC can create vaults and IAM bindings, but rotating the values inside is a separate mechanism (rotation policies, lambdas, vault tooling).
- **Cost discipline** — declarative config makes spend *visible* (tagged, reviewable), but waste needs FinOps practice: rightsizing, budgets, lifecycle rules.
- **Institutional knowledge** — code documents *what* exists, not *why*; ADRs and runbooks still carry the reasoning that a resource block cannot.

Behavioral mirror: "tell me about a time infrastructure code saved (or burned) you" — have a drift or state story ready. The consolidated bank is in [IaC Interview Questions](./interview-questions.md).

## Three Stories to Have Ready

Scenario questions are answered best from a rehearsed skeleton, not improv:

- **The drift story** — a manual console change, how a plan surfaced it, whether you adopted or reverted it, and the access fix that prevented the next one (arc: detect → decide intent → reconcile → close the hole).
- **The state incident** — a corrupt, locked, or lost state file; emphasize that resources were never destroyed, recovery ran through backend versioning or imports, and the fix was versioned locked backends (arc: restore → rebuild → prevent).
- **The migration story** — introducing IaC (or a second tool) into a live estate: one subsystem first, import existing resources, dual-run briefly, dated decommission plan (arc: increment → adopt → converge → decommission).

Each skeleton has four beats and takes under two minutes to tell; practice all three until the beats are automatic.

## Cross-References

- [Terraform](./terraform.md) — HCL, state, plan/apply lifecycle, modules, footguns.
- [Ansible](./ansible.md) — inventories, playbooks, roles, idempotency model, performance.
- [Beyond Terraform](./beyond-terraform.md) — OpenTofu fork, Pulumi, CDK, Crossplane, Terragrunt decision tree.
- [IaC Interview Questions](./interview-questions.md) — 18-question graded bank.
- [GitOps](../cloud/cicd/gitops.md) — the pull-model endgame for workloads.
- [Policy as Code](../cloud/policy-as-code.md) — OPA, Kyverno, Sentinel guarding IaC outputs.
- [Packer](../cloud/packer.md) — image baking, the piece IaC provisioning deliberately does not own.

## Interview Questions

**Q: What problem does IaC actually solve — in one sentence each for drift, repeatability, and review?**
A: Drift: declared config becomes the source of truth, so divergence is a visible diff instead of an archaeology project. Repeatability: any environment becomes a re-run of a reviewed pipeline instead of a human rebuild. Review: infrastructure changes flow through pull requests with diffs, reviewers, and CI gates, like any other code.

**Q: Is Ansible declarative or imperative? And Pulumi?**
A: Ansible is *procedural overall* (tasks execute in written order) but each module is declarative (it asserts a desired end state), so plays converge when modules are idempotent. Pulumi is *authored* imperatively in a real language but is declarative at the engine level: your program registers desired resources, and the engine diffs against state like Terraform. The safe answer is to name both layers — authoring model vs execution model.

**Q: Why do teams combine Terraform and Ansible instead of picking one?**
A: They occupy different lifecycle stages: Terraform provisions the estate (networks, compute, managed services) with a persistent state file, while Ansible configures what runs *on* the hosts, needing no state store because it inspects live systems. Terraform deliberately avoids in-place guest configuration; Ansible deliberately avoids cloud resource graphs. The seam is real but manageable — and increasingly the configuration half is replaced by baked images and Kubernetes.

**Q: Your org is at maturity level 2 (IaC in Git, but humans apply from laptops). What is the next move and why is it hard?**
A: Move to level 3: plan on every PR, apply only from CI on merge, and revoke human write access to production state. It is hard because it is organizational, not technical — on-call engineers lose the "just fix it in the console/terminal" escape hatch, so break-glass procedures, drift alerting, and pipeline reliability must exist *before* the access cut. Stage it subsystem by subsystem rather than as a big-bang lockdown.

## References

- HashiCorp Terraform documentation: <https://developer.hashicorp.com/terraform/docs>
- OpenTofu — the open-source Terraform fork: <https://opentofu.org/>
- Pulumi — IaC in real languages: <https://www.pulumi.com/>
- Ansible documentation: <https://docs.ansible.com/>
