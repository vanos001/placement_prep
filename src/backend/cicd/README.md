# CI/CD

Continuous Integration and Continuous Delivery automate the path from code commit to production deployment, reducing risk and increasing velocity.

## In This Section

- [GitHub Actions](./github-actions.md) — Workflow automation on GitHub
- [GitOps](./gitops.md) — Git as the single source of truth for infrastructure

## CI vs CD

| Aspect | Continuous Integration | Continuous Delivery |
|--------|----------------------|---------------------|
| Focus | Code quality | Deployment |
| Trigger | Every commit | Approved changes |
| Actions | Build, test, lint | Deploy to staging/production |
| Goal | Catch bugs early | Fast, safe releases |

## Pipeline Stages

```
Code → Build → Test → Stage → Approve → Deploy → Monitor
```
