# Git Workflows

## Trunk-Based Development

All developers commit to a single branch (main/trunk). Feature flags control incomplete features.

```
main: ──A──B──C──D──E──F──G──H──I──
         │     │        │     │
         └─F1──┘        └─F2──┘
         feature        feature
         (short-lived)  (short-lived)
```

**Rules:**
- Feature branches live < 2 days
- Merge via PR with code review
- Use feature flags for incomplete work
- CI/CD runs on every commit

**Pros:** Simple, fast integration, fewer merge conflicts
**Cons:** Requires feature flags, disciplined CI/CD

## GitFlow

```
main:    ──1.0───────────────────2.0────
              \                  /
release:       \──rc1──rc2──rc3─/
                    \       /
develop: ──A──B──C──D──E──F──G──H──
              \         /     \
feature:       └─f1─f2─┘       └─f3─f4─┘
```

**Branches:**
- `main`: production-ready code
- `develop`: integration branch
- `feature/*`: new features (branch from develop)
- `release/*`: release preparation (branch from develop)
- `hotfix/*`: production fixes (branch from main)

**Commands:**
```bash
git flow init
git flow feature start my-feature
git flow feature finish my-feature
git flow release start 1.1.0
git flow release finish 1.1.0
git flow hotfix start 1.0.1
git flow hotfix finish 1.0.1
```

**Pros:** Clear structure, supports scheduled releases
**Cons:** Complex, many long-lived branches, merge pain

## GitHub Flow

Simplified workflow centered on pull requests:

1. Create a branch from `main`
2. Make commits
3. Open a pull request
4. Code review + CI
5. Merge to `main`
6. Deploy

```
main: ──A──B──────M──C──────N──
         \       /    \     /
          └─f1─┘      └─f2┘
```

**Pros:** Simple, fast, PR-centric
**Cons:** No release branches, requires continuous deployment

## GitLab Flow

Combines GitHub Flow with environment branches:

```
main:      ──A──B──C──D──E──F──
                              \
pre-production:               ──G──H──
                                     \
production:                          ──I──J──
```

Features merge to `main`. Releases flow through environment branches.

## Forking Workflow

Common in open source:

1. Fork the repository
2. Clone your fork
3. Add upstream remote
4. Create a feature branch
5. Push to your fork
6. Open a PR from fork to upstream

```bash
git clone https://github.com/your-user/repo.git
git remote add upstream https://github.com/original/repo.git
git fetch upstream
git rebase upstream/main
git push origin feature
# Open PR on GitHub
```

## Comparison

| Workflow | Complexity | Best For | Release Strategy |
|---|---|---|---|
| Trunk-based | Low | Continuous deployment | Feature flags |
| GitFlow | High | Scheduled releases | Release branches |
| GitHub Flow | Low | Web apps, SaaS | Continuous deploy |
| GitLab Flow | Medium | Multi-environment | Environment branches |
| Forking | Medium | Open source | PR-based |

## Branch Naming Conventions

```
feature/TICKET-123-user-auth
bugfix/TICKET-456-fix-login
hotfix/TICKET-789-security-patch
release/v1.2.0
chore/update-dependencies
```

## Interview Questions

**Q: Compare GitFlow and trunk-based development.**
A: GitFlow uses long-lived branches (main, develop, feature, release, hotfix) for structured releases. Trunk-based uses short-lived branches merged to main with feature flags. GitFlow suits scheduled releases; trunk-based suits continuous deployment.

**Q: What is the GitHub Flow workflow?**
A: (1) Branch from main, (2) commit changes, (3) open a PR, (4) discuss and review, (5) deploy and test, (6) merge. It's simple and PR-centric, best for teams with continuous deployment.

**Q: How would you handle a hotfix in GitFlow?**
A: (1) Branch from `main` into `hotfix/*`, (2) fix the bug, (3) merge into both `main` and `develop`, (4) tag the merge on `main` with the new version.

## References

- [Atlassian — Comparing Workflows](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [GitFlow — Vincent Driessen](https://nvie.com/posts/a-successful-git-branching-model/)
- [Trunk-Based Development](https://trunkbaseddevelopment.com/)
- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
