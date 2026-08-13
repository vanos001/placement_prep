# GitHub Actions

## Overview

GitHub Actions is a CI/CD platform integrated into GitHub. It automates build, test, and deployment workflows triggered by repository events.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Workflow** | YAML file defining automation (`.github/workflows/`) |
| **Event** | Trigger (push, pull_request, schedule, workflow_dispatch) |
| **Job** | Sequence of steps on a runner |
| **Step** | Individual task (run command or use action) |
| **Action** | Reusable unit of automation |
| **Runner** | Server that executes jobs (GitHub-hosted or self-hosted) |

## Workflow Structure

```yaml
name: CI Pipeline
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

env:
  NODE_VERSION: '20'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      
      - run: npm ci
      - run: npm test
      - run: npm run lint
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
  
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build
      - run: ./deploy.sh
```

## Common Patterns

### Caching

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Matrix Builds

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python: ['3.9', '3.10', '3.11', '3.12']
  fail-fast: false  # Don't cancel other jobs on failure
```

### Secrets

```yaml
steps:
  - name: Deploy
    env:
      API_KEY: ${{ secrets.API_KEY }}
    run: ./deploy.sh
```

### Reusable Workflows

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test
on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: '20'
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci && npm test

# Caller workflow
jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
```

## Best Practices

1. **Pin action versions** — Use SHA or specific tags (`@v4`)
2. **Cache dependencies** — Speed up builds significantly
3. **Use matrix testing** — Test across multiple versions
4. **Limit permissions** — Set `permissions: read-all` by default
5. **Use environments** — Protect production deployments
6. **Fail fast** — `fail-fast: true` for matrix (default)
7. **Timeout jobs** — Prevent runaway processes

## Interview Questions

1. **GitHub Actions vs Jenkins?** — GitHub Actions: cloud-native, YAML config, GitHub integration. Jenkins: self-hosted, Groovy plugins, more flexible.
2. **How to share artifacts between jobs?** — `actions/upload-artifact` and `actions/download-artifact`
3. **How to handle secrets?** — Repository/org/environment secrets, never hardcode
4. **Self-hosted runners?** — For custom hardware, private networks, GPU access. Security risk if public repo.
5. **How to speed up workflows?** — Caching, matrix parallelism, smaller Docker images, self-hosted runners
6. **What is a composite action?** — Reusable action combining multiple steps in one `action.yml`
7. **How to deploy to multiple environments?** — Use `environment` keyword, deployment protection rules
8. **Scheduled workflows?** — `on: schedule: cron: '0 0 * * *'`. Runs on default branch.
9. **How to debug workflows?** — Enable step debug logging (`ACTIONS_STEP_DEBUG`), `tmate` action
10. **Concurrency control?** — `concurrency: group: deploy-${{ github.ref }}` to prevent parallel deploys

## Related Topics

- [GitOps](./gitops.md) — Git-based deployment
- [Docker](../containers/docker.md) — Containerized CI
- [Kubernetes](../containers/kubernetes.md) — Deployment target
