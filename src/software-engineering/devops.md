# DevOps & CI/CD

## Table of Contents

- [What is DevOps?](#what-is-devops)
- [Continuous Integration (CI)](#continuous-integration-ci)
- [Continuous Delivery vs Continuous Deployment](#continuous-delivery-vs-continuous-deployment)
- [Deployment Strategies](#deployment-strategies)
- [Pipelines](#pipelines)
- [Infrastructure as Code](#infrastructure-as-code)
- [Common Mistakes](#common-mistakes)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## What is DevOps?

DevOps is a set of **practices, culture, and tooling** that unify software
development (Dev) and operations (Ops). It aims to shorten the feedback loop between
writing code and running it in production, while keeping systems reliable.

Three core ideas:

- **Culture** — shared ownership: "you build it, you run it."
- **Automation** — everything repeatable (build, test, deploy) is automated.
- **Measurement** — decisions driven by observability, not opinion.

### The Three Ways (Gene Kim)

1. **Flow** — make work flow fast from left (dev) to right (ops); minimize handoffs.
2. **Feedback** — amplify feedback loops so problems surface early.
3. **Continual learning** — experiment, learn from failure, and improve.

## Continuous Integration (CI)

CI is the practice of **merging all developer changes into a shared mainline
frequently** (at least daily) and automatically building and testing each change.

A typical CI step:

1. Developer pushes a commit / opens a pull request.
2. CI checks out the code and builds it.
3. CI runs unit tests, linting, and static analysis.
4. CI reports pass/fail back to the developer.

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run lint
      - run: npm test
```

### Benefits

- Integration problems are caught early, while the change is still small.
- The mainline stays in a releasable state.
- Faster, more reliable releases with less manual testing.
- Failing tests block merges, protecting the codebase.

## Continuous Delivery vs Continuous Deployment

| | Continuous Delivery | Continuous Deployment |
|---|---|---|
| Definition | Every change is *ready* to be released | Every change *is* released automatically |
| Production release | Manual approval | Automatic, no human gate |
| Risk control | Human sign-off before deploy | Strong automated gates + rollback |
| Adoption | Very common | Advanced, high-trust teams |

A system can be "CD" (delivery) without being "continuous deployment."

## Deployment Strategies

| Strategy | How it works | Trade-offs |
|---|---|---|
| **Blue-Green** | Two identical environments; switch traffic at the router | Instant rollback; doubles infrastructure cost |
| **Canary** | Route a small % of traffic to the new version | Early signal with limited blast radius; slower rollout |
| **Rolling** | Replace instances incrementally | No extra infra; rollback is slower |
| **Recreate** | Tear down old, bring up new | Downtime; simplest |
| **Shadow** | Mirror production traffic to new version without serving it | Safe testing; complex |

### Feature Flags

Feature flags decouple **deployment** (code is live) from **release** (feature is
enabled). This enables:

- Trunk-based development with hidden work in progress.
- Instant kill-switch when a feature misbehaves.
- Gradual rollout by percentage or cohort.

## Pipelines

A pipeline is the sequence of automated stages code passes through:

```
commit → build → unit tests → static analysis → integration tests
       → deploy to staging → smoke tests → deploy to production
```

Principles:

- **Fail fast** — run the cheapest, most-likely-to-fail stages first.
- **Idempotent stages** — re-running a stage yields the same result.
- **Artifact-based** — build once, promote the same artifact through stages (never rebuild).
- **Everything as code** — the pipeline definition lives in the repository.

Common platforms: **GitHub Actions**, **GitLab CI**, **Jenkins**, **CircleCI**,
**Buildkite**, **Azure DevOps Pipelines**.

## Infrastructure as Code

With IaC, infrastructure is declared in versioned files rather than configured by hand:

```hcl
# Terraform example
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
}
```

Benefits: reproducibility, reviewability (PRs for infra), drift detection, and fast
environment recreation. Tools: **Terraform**, **Pulumi**, **Ansible**, **CloudFormation**,
**CDK**.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Rebuilding artifacts per stage | "Works on my machine" — inconsistent binaries |
| Manual deployments | Unrepeatable, error-prone, slow |
| Deploying without rollback plan | Long outages when things break |
| No feature flags | Can't disable a bad release quickly |
| Ignoring build times | Long pipelines discourage frequent integration |
| Secrets in pipeline logs | Credential leaks |

## Interview Questions

### Beginner
- What is CI, and why is it valuable?
- What is the difference between continuous delivery and continuous deployment?

### Intermediate
- Compare blue-green and canary deployments. When would you choose each?
- What is a feature flag, and how does it change your release process?

### Advanced
- How would you design a CI/CD pipeline that builds once and deploys to many environments?
- A deploy fails in production — walk through how you would respond.

### Common Traps
- Confusing continuous delivery with continuous deployment.
- Claiming "DevOps" is a job title rather than a set of practices.
- Overlooking rollback/rollforward procedures in a deploy plan.

## References

- [The Phoenix Project — Gene Kim](https://itrevolution.com/product/the-phoenix-project/)
- [Continuous Delivery — Humble & Farley](https://continuousdelivery.com/)
- [DORA — Accelerate State of DevOps](https://dora.dev/)
- [Martin Fowler — Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)
- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)

---

For cloud-focused CI/CD and container pipelines, see the
[Cloud CI/CD section](../cloud/cicd/README.md) of this book.
