# GitHub & Code Review

## Pull Requests

### Creating Effective PRs

```bash
# Push branch and create PR via CLI
git push -u origin feature/auth
gh pr create --title "feat: add JWT authentication" --body "
## Changes
- Add JWT token generation and validation
- Implement refresh token rotation
- Add middleware for route protection

## Testing
- Unit tests for token generation
- Integration tests for auth flow
- Manual testing with Postman

Closes #142
"
```

### PR Best Practices

- **Small, focused PRs**: < 400 lines of code changes
- **Clear title**: Follow Conventional Commits
- **Description**: What, why, how, testing done
- **Link issues**: `Closes #123`, `Fixes #456`
- **Screenshots**: For UI changes
- **Draft PRs**: For work-in-progress feedback

### PR Template

```markdown
## Description
Brief description of changes.

## Motivation
Why these changes are needed.

## Changes
- Change 1
- Change 2

## Testing
How to verify these changes work.

## Screenshots
(if applicable)

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Self-reviewed
```

## Code Review

### As a Reviewer

**What to look for:**
1. **Correctness**: Does it do what it claims?
2. **Edge cases**: Are boundary conditions handled?
3. **Error handling**: Are failures handled gracefully?
4. **Performance**: Any obvious inefficiencies?
5. **Security**: Any vulnerabilities?
6. **Readability**: Is the code clear?
7. **Tests**: Adequate coverage?

**Review etiquette:**
- Be specific and constructive
- Explain *why*, not just *what*
- Distinguish blockers from suggestions
- Use prefixes: `nit:`, `suggestion:`, `question:`, `blocker:`
- Praise good code too

### As an Author

- Self-review before requesting review
- Respond to every comment
- Don't take feedback personally
- Explain your reasoning when disagreeing
- Mark resolved conversations

## Branch Protection

Configure via GitHub Settings → Branches:

```yaml
# Branch protection rules for main
required_status_checks:
  strict: true
  contexts:
    - ci/build
    - ci/test
    - ci/lint

required_pull_request_reviews:
  required_approving_review_count: 2
  dismiss_stale_reviews: true
  require_code_owner_reviews: true

enforce_admins: true
restrictions:
  teams:
    - maintainers
```

### CODEOWNERS

`.github/CODEOWNERS`:
```
# Default owners
*       @team-leads

# Frontend
/src/frontend/   @frontend-team
*.css            @frontend-team

# Backend
/src/api/        @backend-team
*.sql            @database-team

# Infrastructure
/terraform/      @devops-team
Dockerfile       @devops-team
```

## GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm test
      - run: npm run lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
```

### Common CI Patterns

```yaml
# Matrix testing
strategy:
  matrix:
    node-version: [18, 20, 22]
    os: [ubuntu-latest, windows-latest]

# Caching
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

# Secrets
- run: npm publish
  env:
    NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## GitHub CLI

```bash
# PR operations
gh pr create
gh pr list
gh pr view 142
gh pr checkout 142
gh pr merge 142 --squash
gh pr diff 142

# Issue operations
gh issue create --title "Bug" --body "Description"
gh issue list --assignee @me
gh issue close 123

# Release
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes"

# Repo operations
gh repo clone user/repo
gh repo view
```

## Interview Questions

**Q: What makes a good pull request?**
A: Small and focused (< 400 lines), clear title and description, linked issues, test coverage, self-reviewed before requesting review, screenshots for UI changes.

**Q: How do you handle code review disagreements?**
A: (1) Explain your reasoning with technical justification, (2) be open to the reviewer's perspective, (3) suggest a quick call if text discussion stalls, (4) if still disagreeing, escalate to a tech lead, (5) document the decision.

**Q: What is CODEOWNERS and why is it useful?**
A: CODEOWNERS maps file patterns to teams/individuals who automatically get requested for review. It ensures the right people review changes to their areas of expertise, improving code quality and knowledge sharing.

## References

- [GitHub Docs — Pull Requests](https://docs.github.com/en/pull-requests)
- [GitHub Docs — Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
