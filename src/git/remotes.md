# Remote Operations

## Remote Management

```bash
# List remotes
git remote
git remote -v              # with URLs

# Add a remote
git remote add origin https://github.com/user/repo.git
git remote add upstream https://github.com/original/repo.git

# Change remote URL
git remote set-url origin https://github.com/user/new-repo.git

# Remove a remote
git remote remove old-remote

# Rename a remote
git remote rename origin upstream
```

## Fetch

Download remote changes without modifying your working tree:

```bash
git fetch                        # fetch default remote
git fetch origin                 # fetch specific remote
git fetch --all                  # fetch all remotes
git fetch --prune                # remove stale remote tracking branches
git fetch origin main            # fetch specific branch
git fetch --tags                 # fetch all tags
git fetch --depth 1              # shallow fetch
```

After fetch:
- Remote tracking branches updated: `refs/remotes/origin/*`
- Your branches, working tree, and index unchanged

## Pull

`git pull` = `git fetch` + `git merge` (or `git rebase`):

```bash
git pull                         # fetch + merge
git pull --rebase                # fetch + rebase
git pull --rebase origin main    # rebase onto specific branch
git pull --no-rebase             # always merge (override config)
git pull --ff-only               # fail if merge would create merge commit
git pull --autostash             # stash before pull, pop after
```

**Recommended configuration:**
```bash
git config --global pull.rebase true
git config --global pull.ff only
```

## Push

Upload local commits to a remote:

```bash
git push                         # push current branch
git push origin main             # push specific branch
git push -u origin feature       # push and set upstream tracking
git push --force                 # force push (dangerous!)
git push --force-with-lease      # force only if no one else pushed
git push --tags                  # push all tags
git push origin --delete feature # delete remote branch
git push origin :feature         # same (old syntax)
```

### Force Push Safety

```bash
# Dangerous: overwrites remote history
git push --force

# Safer: only force if your local ref matches the remote
git push --force-with-lease
# Fails if someone else pushed since your last fetch
```

## Remote Tracking Branches

```bash
# See tracking relationships
git branch -vv
# * main   abc1234 [origin/main] Latest commit
#   dev    def5678 [origin/dev: ahead 2, behind 1] Another commit

# Set upstream
git branch -u origin/feature
git push -u origin feature       # push and set upstream
```

Tracking is stored in `.git/config`:
```ini
[branch "main"]
    remote = origin
    merge = refs/heads/main
```

## Multiple Remotes

```bash
# Fork workflow
git remote add upstream https://github.com/original/repo.git
git fetch upstream
git rebase upstream/main

# Push to multiple remotes
git remote add all https://github.com/user/repo.git
git remote set-url --add --push all https://github.com/user/repo.git
git remote set-url --add --push all https://gitlab.com/user/repo.git
git push all main
```

## Interview Questions

### Beginner

**Q: What is the difference between `git fetch` and `git pull`?**
A: `fetch` downloads remote changes without integrating them — your working tree stays the same. `pull` = `fetch` + `merge` (or `rebase`), integrating the changes into your current branch.

**Q: What does `git push -u origin feature` do?**
A: Pushes the `feature` branch to the `origin` remote and sets up tracking. After this, you can use `git push` and `git pull` without specifying the remote and branch.

### Intermediate

**Q: What is `--force-with-lease` and why is it safer than `--force`?**
A: `--force-with-lease` checks that the remote branch hasn't been updated by someone else since your last fetch. If it has, the push fails. This prevents accidentally overwriting others' work. `--force` blindly overwrites.

**Q: How do you keep a fork up to date?**
A: (1) `git remote add upstream <original-repo-url>`, (2) `git fetch upstream`, (3) `git rebase upstream/main` (or `git merge upstream/main`). Push the updated branch to your fork with `git push`.

### Advanced

**Q: How does Git resolve divergent histories on push?**
A: Git checks that the remote ref is an ancestor of your local ref. If not (histories diverged), the push is rejected. You must first integrate the remote changes (pull/rebase) before pushing. `--force` bypasses this check.

## References

- [Pro Git — Working with Remotes](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes)
- [Git remote documentation](https://git-scm.com/docs/git-remote)
