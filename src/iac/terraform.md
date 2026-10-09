# Terraform

## HCL Syntax

```hcl
# Variables
variable "region" {
  type    = string
  default = "us-east-1"
}

# Provider
provider "aws" {
  region = var.region
}

# Resource
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  
  tags = {
    Name = "web-server"
  }
}

# Output
output "instance_ip" {
  value = aws_instance.web.public_ip
}
```

## Core Concepts

### Resources
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

### Data Sources
```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*"]
  }
}
```

### Modules
```hcl
# modules/vpc/main.tf
variable "cidr" { type = string }
resource "aws_vpc" "main" {
  cidr_block = var.cidr
}
output "vpc_id" { value = aws_vpc.main.id }

# Root module
module "vpc" {
  source = "./modules/vpc"
  cidr   = "10.0.0.0/16"
}
```

## Providers & Provider Locks

Terraform is a *compiler without a backend*: providers are plugins that speak each cloud's API, downloaded at `init` from the registry. Two hygiene rules follow:

- **Pin versions in code** — `required_providers` inside a `terraform` block declares the provider constraint (`~> 5.0`), so configs state what they were tested against.
- **Commit `.terraform.lock.hcl`** — generated at first `init`, it records the cryptographic checksums of the exact provider binaries selected. Committing it makes CI, teammates, and prod installs all resolve to bit-identical providers; deleting it (or regenerating casually with `terraform providers lock`) is how "works on my machine" plans happen. The lock file is per-working-directory and must be regenerated when you upgrade a provider deliberately.

```hcl
terraform {
  required_version = "~> 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}
```

Provider *upgrades* are deliberate events: bump the constraint, run `init -upgrade`, read the changelog and upgrade guide, plan, and expect deprecation churn (the AWS provider regularly renames resources as AWS deprecates APIs).

## State Management

```bash
# State file stores resource mappings
terraform state list
terraform state show aws_instance.web
terraform state mv aws_instance.web aws_instance.app
terraform state rm aws_instance.old

# Remote state (S3 backend)
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    dynamodb_table = "terraform-locks"  # state locking
  }
}
```

The state-manipulation commands are surgical tools — useful in recovery, dangerous as routine:

| Command | Purpose | Typical scenario |
|---|---|---|
| `state list` | Enumerate managed addresses | "What does Terraform actually own?" |
| `state show <addr>` | Dump one resource's stored attributes | Debugging a plan diff |
| `state mv <a> <b>` | Rewrite an address | Renaming a resource or moving it into a module without recreation |
| `state rm <addr>` | Forget a resource (keep it alive) | Handing ownership to another config/team |
| `state pull` | Emit raw state JSON | Backups, forensics, policy scans |

Each of these edits state *without* touching the cloud — after any of them, a full plan is mandatory to confirm the config, state, and reality agree. OpenTofu's `removed` block (see [Beyond Terraform](./beyond-terraform.md)) makes the `state rm` case declarative and reviewable.

The state file is Terraform's source of truth for *what it manages*: a mapping from resource addresses (`aws_instance.web`) to real IDs (`i-0abc123`), plus resource attributes and dependency metadata. Every plan is a three-way computation: **config (what you want) vs state (what Terraform believes exists) vs refresh (what actually exists)**. Three properties drive all the rules:

1. **It can contain secrets** — resource attributes (database passwords, private keys) are stored in plaintext unless the backend encrypts at rest and you treat state itself as sensitive. Never commit it to Git.
2. **It must be singleton per estate** — two writers with divergent state copies will desynchronize and destroy each other's resources. Hence remote backends and locking.
3. **It is recoverable infrastructure** — losing state does not destroy cloud resources, but it orphans them: Terraform no longer knows what it owns. Backends with versioning (S3 object versioning) turn catastrophe into a restore.

### State Backends & Locking

The standard AWS pattern is **S3 for storage + DynamoDB for locking**: S3 gives durability, encryption, and versioned history; DynamoDB gives a cheap lock row so concurrent applies fail fast with a "state locked" error instead of racing. `use_lockfile` (S3-native locking, adopted broadly in 2024–2025) is replacing the DynamoDB leg, but interviewers still expect the S3+DynamoDB pairing as the classic answer. Alternatives: Terraform Cloud/HCP (state + policy + run queue), Postgres, GCS/Azure Blob (native locking). **Local state is acceptable only for throwaway sandboxes** — it cannot be locked, cannot be shared, and one `rm` ends your estate's history.

### The Plan/Apply Lifecycle in Depth

```text
init → validate → plan ──(review/PR)──→ apply → state updated
              ↑                                      │
              └────── refresh (next plan) ←──────────┘
```

- `plan` starts with a **refresh**: it calls each provider's read API to sync state with reality, then diffs desired-vs-synced. A plan against stale state lies, which is why `plan -refresh=false` exists for read-only-credential situations and why plans on very large estates are slow.
- Plans are addressed by **resource address**; understanding addresses (`aws_instance.web`, `module.vpc.aws_subnet.app[2]`) is what makes targeted operations legible.
- **Targeted applies** (`-target=resource`) apply a subgraph only. They exist for surgical recovery (extracting a stuck resource) and are a smell in normal flow: they silently skip dependency edges, so the saved state no longer reflects the whole config's plan — the classic cause of "partially applied" estates. Use them to get unstuck, then immediately run a full plan.
- `apply` re-computes the plan unless handed a saved plan file (`terraform plan -out=tfplan` then `apply tfplan`) — the CI-safe pattern, since it guarantees what was reviewed is what runs.

### Dependency Graph & Ordering

Ordering comes from the graph, not from file layout: a resource referencing `aws_subnet.app.id` depends on it implicitly, and file/line position is irrelevant. Only genuinely invisible dependencies need explicit edges:

```hcl
resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  # IAM policy attachment must exist before the instance boots,
  # but nothing in the config references it
  depends_on = [aws_iam_role_policy.logging]
}
```

`depends_on` should be rare — every explicit edge serializes the plan and hides the dependency from readers, so it is a documented-exception construct, not a habit. `terraform graph` (or `terraform plan -out` plus visualization tooling) renders the DAG; on large estates graph size, not API latency, is often what makes plans slow, and the fix is usually splitting state (more, smaller roots), not tuning flags. Replacement ordering is where `lifecycle` blocks matter: `create_before_destroy` swaps the order for name-bound resources, `prevent_destroy` refuses the plan outright — both standard interview follow-ups.

### Modules & Composition Patterns

Modules are directories with their own inputs/outputs; `source` accepts local paths, Git URLs, registry entries (`hashicorp/consul/aws`), and S3/HTTP tarballs. The composition rules that scale:

- **Version registry modules** — pin `version = "1.4.2"` like any dependency; floating `source` is how a module bump becomes an incident. Internal module registries (or Git tags) give you review control over shared modules.
- **Composition hierarchy** — leaf modules (network, database) stay provider-generic and small; composition roots (per-environment roots calling leaf modules) hold the only environment-specific values; shared values flow *down* via variables and *up* via outputs, never sideways.
- **Semantic contracts** — a module's `variables.tf` is its API. Changing a variable's default silently changes every caller's plan, which is why module repos use changelogs and tags.
- **Beware module sprawl** — a wrapper module with one resource and one caller is ceremony; the rule of thumb is extract when a second consumer appears.

### Workspaces vs Directory-per-Environment

| Aspect | Workspaces | Directory per environment |
|---|---|---|
| Layout | One config, many named states | Config copied/varied per env dir |
| Env drift risk | High — one config silently feeds all envs | Low — envs diverge explicitly, diffs are visible |
| Code duplication | None | Some (mitigated by shared modules) |
| Blast radius | One bad push can touch every workspace | Separate roots, separate state, separate CI |
| Promotion flow | Weak (same code by definition) | Strong (image/variable promotion, PR per env) |

Small shops and preview environments fit workspaces; **production estates overwhelmingly prefer directories (or repo-per-env) sharing versioned modules**, because independent state, independent IAM, and visible per-env diffs beat DRY. The interview point: workspaces optimize for *less duplication*, directories optimize for *isolation* — pick per blast radius, not per aesthetics.

### Importing Existing Resources

```hcl
# Terraform 1.5+ declarative import block (plan-able, reviewable)
import {
  to = aws_instance.legacy_web
  id = "i-0abc123def456"
}

resource "aws_instance" "legacy_web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
}
```

The `import` block replaces the old `terraform import` CLI one-liner: the import becomes part of the plan, reviewable in the PR, and `terraform plan -generate-config-out=generated.tf` can even draft the matching resource config from the live object. Importing is *adoption, not reconciliation* — it records ownership without changing the resource, so the first post-import plan usually shows attribute fixes to converge. Bulk adoption (thousands of resources) is where tooling like the `import` block plus generated config pays off.

## Workflow

```bash
terraform init          # Initialize, download providers
terraform plan          # Preview changes
terraform apply         # Apply changes
terraform destroy       # Destroy all resources
terraform import        # Import existing resources
terraform fmt           # Format files
terraform validate      # Validate syntax
```

In a pipelined org, humans run `fmt`, `validate`, and `plan` locally; CI runs them authoritatively on PRs; only the pipeline applies to shared state. `destroy` is guarded by enablement flags and policy checks precisely because it needs no confirmation loop in automation.

## Drift Detection

```bash
# Detect manual changes
terraform plan  # Shows differences between state and real infrastructure

# Fix drift
terraform apply  # Reconciles real infrastructure with config
```

Beyond ad-hoc plans, production setups schedule `plan` (nightly or per-merge) and alert on non-empty diffs — drift dashboards ship in Terraform Cloud, Atlantis, and the GitOps-adjacent tooling. When drift is found you have two reconciliations: **re-apply** (the manual change was wrong; converge back to code) or **adopt** (the change was right; codify it, e.g. during an incident hotfix, then commit it). The org-level fix is boring: humans should not have write paths to production that bypass the pipeline, so drift becomes rare rather than continuously managed.

## Policy Hooks: Sentinel & OPA

Plan outputs are machine-readable, which makes them policy-checkable *before* any credential touches an API:

- **Sentinel** — HashiCorp's embedded policy language, first-class in Terraform Cloud/Enterprise: policies run against the plan (and config/state) at the `soft-mandatory` or `hard-mandatory` level, e.g. "deny `aws_instance` without `encrypted = true`", "deny S3 buckets without versioning".
- **OPA/Rego** — the open-source route: tools like Conftest evaluate Rego policies against the JSON plan (`terraform show -json tfplan`) in CI, giving the same gate without HashiCorp licensing. The repo's [Policy as Code](../cloud/policy-as-code.md) page covers the engine landscape in depth.
- Either way the shape is identical: **plan JSON in, allow/deny out, denial blocks apply.** Interview answer: policy-as-code turns compliance review from a post-deployment audit into a pre-merge gate.

## Production Footguns

- **State corruption** — concurrent applies without locking, or someone `sed`-ing the JSON. Mitigate: remote backend + locking + versioning; recover: restore the prior state version, re-plan, `state mv/rm` and `import` what changed.
- **Provider upgrades** — a `~> 5.x` float plus an `init -upgrade` in CI can reformat resources against deprecated APIs; pin, upgrade deliberately, read upgrade guides, and keep the lock file committed.
- **`count` vs `for_each`** — `count` addresses instances by *index*, so inserting an item into the middle of a list re-numbers everything downstream (`web[2]` becomes a different machine) and can trigger destructive replacements. `for_each` keys by a stable map key, so additions/removals touch only their own entry. Default to `for_each` for collections; `count` remains fine for "0 or 1" feature flags (`count = var.enabled ? 1 : 0`).
- **Secrets in state** — even with `sensitive = true` (which only redacts *display*), values land in state plaintext; encrypt backends, restrict access, prefer Vault/SSM data sources so the secret never transits config.
- **`create_before_destroy` gaps** — replacement of a resource with a name/ID constraint (IAM role names, static IPs) fails without `lifecycle` blocks; know which of your resources are name-bound.
- **Local-exec sprawl** — `local-exec` provisioners hide mutation in opaque scripts and break the plan promise; treat every one as a design smell to be refactored into providers or null_resource with explicit triggers.

## Interview Questions

**Q: What is Terraform state and why is it needed?**
A: State maps Terraform config to real-world resources. It tracks metadata, enables performance (knows what changed), and supports collaboration (remote state with locking). Without state, Terraform wouldn't know which resources to update vs create vs delete.

**Q: How do you handle secrets in Terraform?**
A: (1) Use `sensitive = true` on variables, (2) store secrets in Vault/SSM and use `data` sources, (3) never commit `.tfvars` with secrets, (4) use remote state with encryption, (5) mark outputs as sensitive. Note that `sensitive = true` only hides values from CLI output — the values still exist in state plaintext, so backend encryption and access control are the real boundary.

**Q: What is the difference between `terraform plan` and `terraform apply`?**
A: `plan` is a dry-run that shows what changes will be made without applying them. `apply` executes those changes. Always review `plan` output before `apply`. `terraform apply -auto-approve` skips the confirmation prompt (use in CI/CD only).

**Q: Walk me through what `terraform plan` actually does, in order.**
A: First it refreshes: reads the live state of every managed resource via providers and syncs the state file with reality. Then it builds the dependency graph from config, diffs desired-vs-refreshed, and emits create/update/replace/destroy actions in dependency order. Nothing is written to the cloud — but the state *is* updated with refreshed values unless you use `-refresh=false`, which surprises people. A plan computed against stale state is a lie, which is why plans should run close to apply time.

**Q: Why is `.terraform.lock.hcl` committed, and what breaks if it isn't?**
A: It pins the exact provider binary checksums selected at init, so CI, teammates, and production all resolve bit-identical providers. Without it, each run re-resolves the newest version matching the constraint, so a provider release can change your plan between review and apply — the classic "the plan changed on its own" incident. Upgrading providers then becomes a deliberate lock-file regeneration with a reviewable diff.

**Q: `count` vs `for_each` — when does `count` hurt you?**
A: `count` indexes instances by position, so inserting into the middle of the source list re-numbers every later instance and Terraform plans replacements of resources that didn't logically change — destructive for name-bound or stateful resources. `for_each` keys by a stable identifier, so adds and removals touch only their own entry. Rule of thumb: `for_each` for collections, `count` only for 0-or-1 toggles.

**Q: Workspaces or directory-per-environment — how do you choose and why?**
A: Workspaces give one config over many states: minimal duplication but weak isolation, one bad merge reaching every environment, and no visible per-env diff. Directories-per-env duplicate a thin root while sharing versioned modules: separate state, separate IAM, separate CI, visible divergence — which is why most production estates choose them. The deciding question is blast radius, not DRY.

**Q: You discover production drift on a security group that was opened during last month's incident. Walk me through handling it.**
A: First establish intent: check whether the change was legitimized anywhere (incident review, ticket) — if yes, adopt it into code via a PR (and remove the over-broad rule if it was a stopgap). If not, re-apply to converge back to the declared state and confirm with a follow-up plan. Either way, close the loop organizationally: the drift means someone has a write path that bypasses the pipeline, so remediate the access, and add scheduled plan-based drift alerts so the next divergence is caught in hours, not months.

## References

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [OpenTofu documentation](https://opentofu.org/docs/) — fork differences incl. state encryption and `removed` blocks
