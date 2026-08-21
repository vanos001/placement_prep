# GitLab CI/CD

GitLab CI/CD is the built-in continuous integration and continuous deployment system for GitLab, available since GitLab 8.0 (2015). It's integrated with GitLab's source code management, providing a single platform for code, CI, and CD. This page covers the architecture, the `.gitlab-ci.yml` model, the runner types, and the comparison to GitHub Actions.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  GitLab (the application)                                   │
│  - Web UI for pipeline visualization                         │
│  - Schedule jobs on Runners                                 │
│  - Stores build artifacts                                    │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ job dispatch                 │ job results
        ▼                              ▼
┌──────────────────────────────┐    ┌──────────────────────┐
│  Shared Runners (GitLab-managed)│    │  Specific Runners (self-hosted)│
│  - Per-month minute quota       │    │  - You manage the VMs      │
└──────────────────────────────┘    └──────────────────────┘
        │                              │
        ▼                              ▼
    Docker containers              Docker / Shell / K8s
```

GitLab CI uses "Runners" — separate processes that execute jobs. Runners can be shared (GitLab-managed) or specific (self-hosted).

## The .gitlab-ci.yml Model

A pipeline is defined in `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - test
  - deploy

variables:
  IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

build:
  stage: build
  image: docker:20
  services:
    - docker:20-dind
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
  artifacts:
    paths:
      - build-info.json

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -f k8s/
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  environment:
    name: production
    url: https://my-app.example.com
```

Key concepts:
- **stages**: ordered list; jobs in the same stage run in parallel; stages run sequentially.
- **jobs**: individual tasks (e.g., build, test, deploy).
- **script**: shell commands to run.
- **image**: the Docker image to run in.
- **services**: additional Docker containers (e.g., docker-in-docker, databases).
- **variables**: env vars (built-in or custom).
- **rules**: when to run the job (branch, MR, etc.).
- **artifacts**: files to save and pass to subsequent jobs.
- **environment**: deploy target (used for tracking and rollback).

## Runner Types

### Shared Runners

GitLab-managed runners, available to all projects (with a monthly minute quota on gitlab.com).

Pros: zero setup; suitable for open-source projects.

Cons: limited quota; shared with other users (slow during peak).

### Specific Runners

Self-hosted runners, registered to a specific project or group.

```bash
# Install GitLab Runner
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
sudo chmod +x /usr/local/bin/gitlab-runner

# Register
sudo gitlab-runner register
# Enter the URL (https://gitlab.com/) and the registration token from your project's CI/CD settings.
```

Pros: unlimited minutes; full control over the environment.

Cons: you manage the infrastructure.

### Runner Executors

Runners can use different "executors":
- **Shell**: runs jobs in the runner's shell (no isolation; legacy).
- **Docker**: runs jobs in Docker containers (default; recommended).
- **Kubernetes**: runs jobs as Pods in a K8s cluster.
- **Docker Machine**: dynamically provisions Docker VMs (legacy autoscaling).

## CI/CD Features

### Environments and Deployments

```yaml
deploy:
  stage: deploy
  environment:
    name: production
    url: https://my-app.example.com
  script:
    - kubectl apply -f k8s/
```

GitLab tracks deployments per environment; you can roll back to previous deployments.

### Manual Approvals

```yaml
deploy:
  stage: deploy
  when: manual  # requires manual click
  script:
    - kubectl apply -f k8s/
```

The job only runs when someone clicks "Run" in the GitLab UI. Useful for production deployments.

### Scheduled Pipelines

Schedule pipelines to run periodically (e.g., nightly tests):

```bash
# In GitLab UI: CI/CD > Schedules > New schedule
# Cron: "0 2 * * *" (every day at 2am)
# Branch: main
```

### Merge Request Pipelines

```yaml
rules:
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

Jobs with this rule run only on MR pipelines (not on push to main). Useful for tests that should run pre-merge.

### Caching

```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .npm/
    - node_modules/
```

The cache is shared across jobs in the same branch; speeds up subsequent runs.

## Production Use Cases

### Multi-Environment Promotion

```yaml
stages:
  - build
  - test
  - deploy-staging
  - deploy-prod

deploy-staging:
  stage: deploy-staging
  environment:
    name: staging
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - kubectl apply -f k8s/staging/

deploy-prod:
  stage: deploy-prod
  environment:
    name: production
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  when: manual  # require approval
  script:
    - kubectl apply -f k8s/production/
```

Build → test → staging (auto) → production (manual approval).

### Container Image Build

```yaml
build:
  image: docker:20
  services:
    - docker:20-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

Builds and pushes to GitLab's built-in container registry.

### Infrastructure as Code (Terraform)

```yaml
deploy-infra:
  image: hashicorp/terraform:latest
  script:
    - terraform init
    - terraform plan -out=tfplan
    - terraform apply -auto-approve tfplan
  artifacts:
    paths:
      - tfplan
```

## Comparison to GitHub Actions

| Aspect | GitLab CI | GitHub Actions |
|--------|-----------|----------------|
| Origin | GitLab 2015 | GitHub 2019 |
| Configuration | .gitlab-ci.yml | .github/workflows/*.yml |
| Runners | Shared + Specific (self-hosted) | GitHub-hosted + self-hosted |
| Container Registry | Built-in | GitHub Container Registry |
| Environments | First-class | Limited |
| UI | Built-in | Built-in (Actions tab) |
| Pricing | Free for open-source; per-user pricing for private | Free for open-source; per-minute for private |
| Best for | All-in-one (code + CI + CD) | GitHub-centric workflows |

Both are mature CI/CD systems; the choice depends on the platform (GitLab vs. GitHub).

## Common Pitfalls

1. **Forgetting that shared runners have a quota.** On gitlab.com, free tier has 400 minutes/month; paid tiers have more. For heavy workloads, use specific runners.

2. **Forgetting that Docker-in-Docker requires privileged mode.** The `docker:20-dind` service needs privileged containers; configure the runner with `privileged = true`.

3. **Forgetting that artifacts expire.** Default artifact retention is 30 days; older artifacts are deleted. Set `expire_in: 1 week` for shorter or `expire_in: never` for permanent.

4. **Forgetting that rules replaced `only`/`except`.** Older syntax (`only: master`) is deprecated; use `rules:`.

5. **Forgetting that the runner needs network access to GitLab.** Self-hosted runners must reach GitLab's API. Configure firewalls accordingly.

6. **Forgetting that environment tracking requires `environment:` field.** Without it, GitLab doesn't track deployments; no rollback feature.

## References

- [GitLab CI/CD documentation](https://docs.gitlab.com/ee/ci/)
- [.gitlab-ci.yml reference](https://docs.gitlab.com/ee/ci/yaml/)
- [GitLab Runners](https://docs.gitlab.com/runner/)
- [GitLab Environments and Deployments](https://docs.gitlab.com/ee/ci/environments/)
- [GitLab vs GitHub Actions](https://about.gitlab.com/devops-tools/github-vs-gitlab.html)
- [LWN: GitLab CI overview (2021)](https://lwn.net/Articles/815575/)
