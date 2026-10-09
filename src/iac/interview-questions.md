# Infrastructure as Code Interview Questions

Eighteen questions in three difficulty bands, covering concepts, state, drift, modules, security, multi-environment structure, policy-as-code, tool choice, Ansible, and troubleshooting. Depth companions: [Terraform](./terraform.md), [Ansible](./ansible.md), [Beyond Terraform](./beyond-terraform.md), and the [IaC Overview](./README.md).

**How to use this page.** Answer each question out loud before reading the model answer — the graded skill is narrating a decision procedure, not reciting definitions. For scenario questions, always speak the diagnosis steps in order; interviewers score the process. Where a question has a deeper companion page, the answer names it.

## Question Map

| # | Question | Band | Companion |
|---|---|---|---|
| Q1 | What is IaC? | Foundations | [Overview](./README.md) |
| Q2 | Declarative vs imperative | Foundations | [Overview](./README.md) |
| Q3 | Push vs pull models | Foundations | [GitOps](../cloud/cicd/gitops.md) |
| Q4 | Mutable vs immutable | Foundations | [Overview](./README.md) |
| Q5 | State in a team | Terraform & State | [Terraform](./terraform.md) |
| Q6 | What a plan compares | Terraform & State | [Terraform](./terraform.md) |
| Q7 | `count` vs `for_each` | Terraform & State | [Terraform](./terraform.md) |
| Q8 | Testing IaC | Terraform & State | [Terraform](./terraform.md) |
| Q9 | What is drift | Drift & Multi-Env | [Terraform](./terraform.md) |
| Q10 | Reconciling a hotfix | Drift & Multi-Env | [Terraform](./terraform.md) |
| Q11 | Workspaces vs directories | Drift & Multi-Env | [Beyond Terraform](./beyond-terraform.md) |
| Q12 | Secrets in Terraform | Security & Governance | [Terraform](./terraform.md) |
| Q13 | Policy-as-code integration | Security & Governance | [Policy as Code](../cloud/policy-as-code.md) |
| Q14 | Tool-choice decision procedure | Tool Choice | [Beyond Terraform](./beyond-terraform.md) |
| Q15 | Dynamic inventories | Ansible | [Ansible](./ansible.md) |
| Q16 | Handlers vs tasks, idempotency | Ansible | [Ansible](./ansible.md) |
| Q17 | Stuck state lock | Troubleshooting | [Terraform](./terraform.md) |
| Q18 | Lost state file | Troubleshooting | [Terraform](./terraform.md) |

## Foundations (warm-up — must be fluent)

*What interviewers are actually testing:* vocabulary fluency and whether you can attach a trade-off to each term instead of a definition. Expect rapid-fire.

**Q1: What is Infrastructure as Code?**
A: Managing infrastructure through machine-readable config files rather than manual processes. Benefits: version control, reproducibility, automation, documentation, collaboration, drift detection.
The deeper framing interviewers want: infrastructure gets the same lifecycle as software — branching, pull requests, CI gates, tagged releases —
which turns "who changed what, when, and why" from an audit project into a `git log`.

**Q2: Declarative vs imperative — give one tool of each kind and explain the real difference.**
A: Declarative tools (Terraform, CloudFormation) let you state desired state and own the convergence logic: they compute the diff and the plan.
Imperative scripts (bash) execute steps and leave you owning convergence and idempotency by hand.
Nuance that earns credit: Pulumi is *authored* imperatively in a real language but its engine is *declarative* —
it diffs desired resources against state exactly like Terraform.
Separate the authoring model from the execution model and you have separated yourself from the mid-level pack.

**Q3: Push vs pull models of IaC — where does each fit?**
A: Push tools (Terraform, Ansible, Pulumi) are invoked by CI or operators and hold broad credentials; their drift window extends until the next run.
Pull models (Puppet/Chef agents, Kubernetes controllers, GitOps operators like Argo CD/Flux) reconcile continuously against declared state, bounding drift by the sync interval.
Provisioning is inherently push — there is no "VPC agent" to pull — while keeping deployed workloads in sync is naturally pull,
which is why mature organizations run both: Terraform pushing infrastructure, GitOps pulling workloads.

**Q4: Mutable vs immutable infrastructure — when is mutable still the right call?**
A: Immutable (bake images, replace instances) eliminates drift and makes rollback a pointer flip, but assumes cattle-like, replaceable machines.
Mutable configuration management remains right for stateful or long-lived systems — databases, bare metal, edge boxes — where replacement is expensive and state lives locally.
Most real estates are hybrid, and the strong answer says so deliberately: immutable compute fleet, mutable config for the stubborn remainder, all driven from Git.

## Terraform & State (intermediate)

*What interviewers are actually testing:* whether you understand the state file as the load-bearing artifact — most production Terraform incidents are state incidents in disguise.

**Q5: How do you manage Terraform state in a team?**
A: (1) Remote state (S3, GCS, Terraform Cloud), (2) state locking (DynamoDB, GCS), (3) workspaces for environments, (4) never commit state files to git, (5) use `terraform import` for existing resources.
Add the 2020s polish to sound current: commit `.terraform.lock.hcl` so everyone resolves identical provider binaries,
enable backend versioning so state is restorable, and treat state files as secret-bearing artifacts with IAM-restricted access.

**Q6: What does a plan actually compare, and why can a plan lie?**
A: It refreshes live resource state from the provider APIs, then diffs three things: your config (desired), the state file (believed), and the refresh (actual).
A plan lies when run against stale state or a state file that does not match reality — a plan computed at 9am against a 5pm apply window describes a world that no longer exists.
That is why plans should run close to apply time, why CI should apply the *same* plan it reviewed (save with `-out`, apply the file, never recompute),
and why `-refresh=false` exists as a tool rather than a default.

**Q7: `count` vs `for_each` — where does `count` bite?**
A: `count` addresses instances by index, so inserting into the middle of the source list re-numbers subsequent instances and Terraform plans replacements of resources that logically didn't change — destructive for name-bound or stateful resources.
`for_each` keys by a stable identifier, so additions and removals touch only their own entry.
Default to `for_each` for collections; keep `count` for zero-or-one feature toggles (`count = var.enabled ? 1 : 0`) where renumbering is harmless.

**Q8: How do you test IaC?**
A: (1) `terraform validate` (syntax), (2) `terraform plan` (dry-run), (3) `tflint` (linting), (4) `checkov`/`tfsec` (security scanning), (5) `terratest` (integration tests), (6) policy-as-code (OPA, Sentinel).
Mention the pyramid shape: static checks on every PR, plan diffs posted to the PR for human review, expensive integration tests (real cloud, real teardown) only on merge to main.
For Ansible the equivalents are `--syntax-check`, `ansible-lint`, and Molecule for role testing.

## Drift & Multi-Environment (intermediate → advanced)

*What interviewers are actually testing:* operational maturity — drift is a process failure wearing a technical costume.

**Q9: What is drift in IaC?**
A: When real infrastructure diverges from the IaC config (e.g., someone manually changes a security group). Detected by `terraform plan`. Fixed by re-applying or importing changes. Prevented by RBAC (deny manual changes) and CI/CD pipelines.
The operational upgrade: schedule plan-based drift detection (nightly or per-merge) with alerts, so drift surfaces in hours instead of surfacing during the next incident.

**Q10: A hotfix was applied by hand during last month's incident and never codified. How do you reconcile?**
A: Decide intent first: check whether the change was legitimized anywhere (incident review, ticket, chat archaeology).
If it should stand, adopt it — write the config change, use an `import` block if the resource is not yet managed, and PR it like any change;
if it was a stopgap, converge back with `apply` and confirm with a clean plan.
Either way, close the process hole: drift means someone has a write path that bypasses the pipeline, so remediate the access and document break-glass.

**Q11: Workspaces vs directory-per-environment — what do you recommend and why?**
A: Workspaces keep one config over many named states: zero duplication but weak isolation, and no visible per-env diff, so one merge reaches every environment.
Directory-per-env duplicates a thin root while sharing versioned modules, and buys separate state, separate IAM, separate CI, and visible divergence — which is why most production estates choose it.
The deciding axis is blast radius, not DRY; say that sentence and the question is won.

## Security & Governance (advanced)

*What interviewers are actually testing:* whether you know where the sensitive material *actually* flows — most confident answers stop at `sensitive = true`.

**Q12: Where do secrets end up in Terraform, and what actually protects them?**
A: Everywhere: the state file, saved plan files, outputs marked `sensitive` (which only redacts *display*), and `.tfvars` if you are careless.
Real protection is backend encryption plus tight state-access IAM, secrets fetched at runtime from Vault/SSM/KMS data sources so values never live in config,
and plan files treated as state-class artifacts.
Anyone who answers "`sensitive = true`" alone is describing a display feature, not a security control — that distinction is the actual test.

**Q13: How does policy-as-code integrate with a Terraform pipeline?**
A: Plans are machine-readable JSON (`terraform show -json tfplan`), so CI evaluates Rego (OPA/Conftest) or Sentinel policies against the plan before apply:
deny unencrypted RDS, deny `0.0.0.0/0` SSH, require cost-allocating tags.
Denials block the pipeline at PR time, turning compliance from a post-deployment audit into a pre-merge gate.
The same pattern applies to Kubernetes admission (Kyverno, Gatekeeper) — see [Policy as Code](../cloud/policy-as-code.md) for the engine landscape.

## Tool Choice (advanced)

*What interviewers are actually testing:* whether you can derive a recommendation from team topology instead of defending a brand.

**Q14: Your team asks: Terraform, Pulumi, CDK, or Crossplane? Give a decision procedure, not a preference.**
A: Decide on topology and authors: app teams writing application-shaped infrastructure in real languages → Pulumi, or CDK if AWS-only (it compiles to CloudFormation and inherits its state model).
Platform teams standardizing multi-cloud resource graphs → Terraform/OpenTofu; running an internal platform where developers self-serve via Kubernetes CRDs and drift should self-heal → Crossplane.
Most organizations honestly run two tools, and the OpenTofu fork (licence control) is a legitimate tiebreaker — the full comparison lives in [Beyond Terraform](./beyond-terraform.md).

## Ansible (intermediate)

*What interviewers are actually testing:* the agentless execution model — performance, idempotency, and inventory questions all reduce to "what happens on each run".

**Q15: What problem do dynamic inventories solve, and how do you debug one?**
A: They query the live source of truth — cloud APIs filtered by tag, CMDB, Consul — at run time, so playbooks target what actually exists instead of a hand-edited file that rots; essential in autoscaling estates where the host set changes hourly.
Debug with `ansible-inventory --graph` (and `--list`) to inspect the composed host/group view before running anything.
The follow-up is usually variable precedence across inventory layers — `group_vars`, `host_vars`, play vars, `extra_vars` — so have that ladder ready.

**Q16: Handlers vs tasks, and how do you make a `shell` task idempotent?**
A: Tasks execute in written order and return changed/ok/failed; handlers are notified by *changed* tasks, deduplicate, and run once at the end of the play — the mechanism that restarts a service only when its config actually changed.
Raw `shell`/`command` always report changed, so restore idempotency with `creates:` (skip if the artifact exists) or `changed_when:` (encode what counts as a change).
Citing either fix signals you understand the check-then-act idempotency model, not just the rule of thumb.

## Troubleshooting Scenarios (advanced — narrate the diagnosis)

*What interviewers are actually testing:* composure and process. Say the diagnosis steps out loud, in order, before touching anything — the fastest way to fail these is to jump to the fix.

**Q17: CI reports "Error acquiring the state lock". What now?**
A: Do not force-unlock first: identify the lock holder from backend metadata — the DynamoDB item or lock file records the operation ID and timestamp —
and check whether that apply is still running; wait if so.
If it is a genuinely dead run, `terraform force-unlock <lock-id>` (or deleting the lock file) is safe only after confirming no process is mid-apply.
Prevention: applies only from CI with per-run lock metadata, and no human ever applies to shared state from a laptop.

**Q18: The state file is gone (deleted bucket, no backup). Walk me through recovery.**
A: Cloud resources still exist — you have lost Terraform's *memory*, not the estate, and saying that opening sentence calmly is half the answer.
Recover in order: restore the most recent backend version (S3 versioning, Terraform Cloud history) if any;
otherwise rebuild state by importing existing resources (`import` blocks at scale, `-generate-config-out` to draft the config),
then run a full plan and expect a long session of attribute reconciliation.
The answer they want next is prevention: versioned, locked, encrypted backends, restricted write access, and periodic state backups.

## How Answers Get Scored

Across all bands, scoring follows the same pattern:

1. **Structure** — did you name a decision procedure or diagnosis order, or jump to an answer? Scenarios especially reward the spoken checklist.
2. **Trade-offs** — did you state what the alternative costs? "Directories per env because blast radius beats DRY" beats "we use directories".
3. **Currency** — do you know the 2020s shifts (OpenTofu fork, S3-native locking, policy gates in CI)? One current reference per answer is plenty.
4. **Honesty** — "I have not run Crossplane in production, but architecturally..." scores higher than bluffing; interviewers probe one level deeper than your claim.

## Follow-Up Chains to Expect

Interviewers rarely stop at the first answer; each question opens a drill-down path. Anticipate the second and third hop:

- **State** → "what's inside the state file?" (addresses, attributes, dependencies, secrets) → "two people applied at once — what happened?" (locking, or a corrupt state and the restore story) → "why not commit state to Git?" (secrets, race on merge, no locking).
- **Drift** → "how would you *prevent* it, not detect it?" (pipeline-only apply, RBAC, no console write paths) → "what about changes made by autoscaling or the cloud itself?" (ignore-life-cycle tags, hourly bumps, and which attributes a plan deliberately ignores).
- **Modules** → "when do you *not* extract a module?" (single caller, one resource — extraction is ceremony) → "how do you version a shared module safely?" (tags, changelogs, consumers pin, upgrade is a PR per consumer).
- **Ansible** → "your play fails on host 37 of 300 — what do you do?" (`--limit`, `--start-at-task`, fix-forward vs re-run; check mode after fix) → "how do you make the fleet converge without another 40-minute run?" (fact caching, tags, narrower plays).
- **Tool choice** → "you picked X — what would make you migrate off it?" (licence, ecosystem stagnation, team language shift) → "and how would you migrate?" (one subsystem, import into the new state model, dated decommission of the old pipeline).

Having the chain rehearsed converts a stressful follow-up into a chance to show depth — the difference between a mid and a senior signal is almost always the second hop.

## Cross-References

- [Terraform](./terraform.md) — state, lifecycle, modules, footguns behind most answers above.
- [Ansible](./ansible.md) — inventories, handlers, idempotency model, performance.
- [Beyond Terraform](./beyond-terraform.md) — OpenTofu, Pulumi, CDK, Crossplane comparisons.
- [IaC Overview](./README.md) — landscape, maturity ladder, push vs pull.
- [Policy as Code](../cloud/policy-as-code.md) — OPA/Kyverno/Sentinel gate design.

## References

- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Ansible Documentation](https://docs.ansible.com/)
- [OpenTofu](https://opentofu.org/) and [Pulumi](https://www.pulumi.com/) — the alternatives' own docs for decision questions.
