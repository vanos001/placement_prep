# Git Hooks

Git hooks are scripts that run automatically at specific points in the Git workflow. They live in `.git/hooks/`.

## Client-Side Hooks

### pre-commit

Runs before a commit is created. Exit non-zero to abort.

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run linter
npm run lint
if [ $? -ne 0 ]; then
    echo "Linting failed. Fix errors before committing."
    exit 1
fi

# Check for debug statements
if git diff --cached --name-only | xargs grep -l "console.log\|debugger"; then
    echo "Debug statements found. Remove before committing."
    exit 1
fi
```

### commit-msg

Validates the commit message format:

```bash
#!/bin/bash
# .git/hooks/commit-msg

MSG=$(cat "$1")
PATTERN="^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: .{1,72}"

if ! echo "$MSG" | head -1 | grep -qE "$PATTERN"; then
    echo "Invalid commit message format."
    echo "Expected: <type>(<scope>): <subject>"
    echo "Example: feat(auth): add JWT validation"
    exit 1
fi
```

### prepare-commit-msg

Runs before the commit message editor opens:

```bash
#!/bin/bash
# .git/hooks/prepare-commit-msg

# Add branch name to commit message
BRANCH=$(git symbolic-ref --short HEAD)
if [[ "$BRANCH" =~ ^(feature|bugfix)/(.+) ]]; then
    TICKET="${BASH_REMATCH[2]}"
    sed -i.bak -e "1s/^/[$TICKET] /" "$1"
fi
```

### pre-push

Runs before `git push`:

```bash
#!/bin/bash
# .git/hooks/pre-push

# Run tests before pushing
npm test
if [ $? -ne 0 ]; then
    echo "Tests failed. Push aborted."
    exit 1
fi
```

### post-checkout

Runs after `git checkout` or `git switch`:

```bash
#!/bin/bash
# .git/hooks/post-checkout

# Install dependencies if package.json changed
PREV_HEAD=$1
NEW_HEAD=$2
if [ "$PREV_HEAD" != "$NEW_HEAD" ]; then
    if git diff --name-only "$PREV_HEAD" "$NEW_HEAD" | grep -q "package.json"; then
        echo "package.json changed. Running npm install..."
        npm install
    fi
fi
```

### pre-rebase

Runs before `git rebase`:

```bash
#!/bin/bash
# .git/hooks/pre-rebase
# Prevent rebasing main
BRANCH=$(git symbolic-ref --short HEAD)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "Cannot rebase the main branch!"
    exit 1
fi
```

## Server-Side Hooks

### pre-receive

Runs on the server before refs are updated:

```bash
#!/bin/bash
# pre-receive on server

while read oldrev newrev refname; do
    # Prevent force pushes to main
    if [ "$refname" = "refs/heads/main" ]; then
        if git merge-base --is-ancestor "$oldrev" "$newrev" 2>/dev/null; then
            : # fast-forward is OK
        else
            echo "Force push to main is not allowed!"
            exit 1
        fi
    fi

    # Check commit message format
    for commit in $(git rev-list "$oldrev".."$newrev"); do
        MSG=$(git log -1 --format=%s "$commit")
        if ! echo "$MSG" | grep -qE "^(feat|fix|docs|chore):"; then
            echo "Bad commit message: $MSG"
            exit 1
        fi
    done
done
```

### update

Runs once per ref being updated (like pre-receive but per-branch):

```bash
#!/bin/bash
# update on server
REFNAME=$1
OLDREV=$2
NEWREV=$3

if [ "$REFNAME" = "refs/heads/main" ]; then
    # Prevent force push
    if ! git merge-base --is-ancestor "$OLDREV" "$NEWREV"; then
        echo "Force push to main rejected"
        exit 1
    fi
fi
```

### post-receive

Runs after all refs are updated (server-side):

```bash
#!/bin/bash
# post-receive on server

# Send notification
while read oldrev newrev refname; do
    BRANCH=$(echo "$refname" | sed 's|refs/heads/||')
    AUTHOR=$(git log -1 --format="%an" "$newrev")
    MSG=$(git log -1 --format="%s" "$newrev")
    echo "$AUTHOR pushed to $BRANCH: $MSG" | mail -s "Git Push" team@company.com
done
```

## Shared Hooks

Hooks in `.git/hooks/` are not tracked. To share hooks:

### Method 1: hooksPath

```bash
# Store hooks in the repo
mkdir -p .githooks
# Put hooks in .githooks/

# Configure
git config core.hooksPath .githooks
```

### Method 2: Husky (JavaScript projects)

```bash
npm install husky --save-dev
npx husky init
# Creates .husky/ directory with hooks
```

## Popular Hook Tools

| Tool | Language | Purpose |
|---|---|---|
| **Husky** | JavaScript | Git hooks for Node.js projects |
| **pre-commit** | Python | Framework for managing pre-commit hooks |
| **lefthook** | Go | Fast Git hooks manager |
| **overcommit** | Ruby | Git hooks management framework |

## Interview Questions

**Q: What are Git hooks? Where are they stored?**
A: Hooks are scripts that run automatically at specific Git events (pre-commit, post-merge, pre-push, etc.). They're stored in `.git/hooks/` and are not tracked by Git. To share hooks, use `core.hooksPath` or tools like Husky.

**Q: How would you enforce commit message conventions?**
A: Use a `commit-msg` hook that validates the message format using regex. For example, checking for Conventional Commits format: `^(feat|fix|docs|chore)(\(.+\))?: .+`. Reject with `exit 1` if invalid.

**Q: What's the difference between client-side and server-side hooks?**
A: Client-side hooks (pre-commit, commit-msg, pre-push) run on the developer's machine. Server-side hooks (pre-receive, update, post-receive) run on the remote repository. Server-side hooks can enforce team-wide policies.

## References

- [Pro Git — Git Hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Git hooks documentation](https://git-scm.com/docs/githooks)
- [Husky](https://typicode.github.io/husky/)
- [pre-commit](https://pre-commit.com/)
