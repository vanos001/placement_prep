# Worktrees & Submodules

## Git Worktree

Work on multiple branches simultaneously without stashing or cloning multiple times.

### Creating Worktrees

```bash
# Create worktree for existing branch
git worktree add ../hotfix hotfix-branch

# Create worktree with new branch
git worktree add -b new-feature ../feature-work main

# Create at specific commit (detached HEAD)
git worktree add ../testing abc1234
```

### Managing Worktrees

```bash
git worktree list                    # list all worktrees
git worktree list --porcelain        # machine-readable
git worktree remove ../hotfix        # remove worktree
git worktree prune                   # clean stale worktrees
git worktree lock ../important       # prevent auto-prune
git worktree unlock ../important     # allow auto-prune
```

### Worktree Constraints

- A branch can only be checked out in **one worktree** at a time
- All worktrees share the same `.git/objects` (no content duplication)
- Each worktree has its own working directory and index
- Hooks are shared from the main repository

### Use Cases

1. **Hotfix while developing**: Create worktree for hotfix branch without stashing
2. **Run tests on different branch**: Test one branch while coding another
3. **Code review**: Check out PR branch in a separate directory
4. **Build multiple versions**: Simultaneously build different releases

### Worktree + Bare Repository

For server-like setups:

```bash
git clone --bare https://github.com/user/repo.git repo.git
cd repo.git
git worktree add ../main main
git worktree add ../dev dev
```

## Git Submodules

Include external Git repositories as subdirectories.

### Adding Submodules

```bash
git submodule add https://github.com/lib/lib.git vendor/lib
git submodule add -b main https://github.com/lib/lib.git vendor/lib
```

Creates:
- `.gitmodules` file (tracked)
- Entry in the index (gitlink)
- Cloned repo in the specified path

### Cloning with Submodules

```bash
# Option 1: --recurse-submodules
git clone --recurse-submodules https://github.com/user/repo.git

# Option 2: init + update after clone
git clone https://github.com/user/repo.git
cd repo
git submodule init
git submodule update

# Option 3: combined
git submodule update --init --recursive
```

### Updating Submodules

```bash
# Update to recorded commit
git submodule update

# Update to latest remote commit
git submodule update --remote

# Update specific submodule
git submodule update --remote vendor/lib

# Fetch and merge in submodule
cd vendor/lib
git pull origin main
cd ../..
git add vendor/lib
git commit -m "chore: update vendor/lib to latest"
```

### Removing Submodules

```bash
# Modern Git (2.35+)
git submodule deinit vendor/lib
git rm vendor/lib
rm -rf .git/modules/vendor/lib

# Manual cleanup
git config -f .gitmodules --remove-section submodule.vendor/lib
git config -f .git/config --remove-section submodule.vendor/lib
git rm --cached vendor/lib
rm -rf .git/modules/vendor/lib
rm -rf vendor/lib
git commit -m "chore: remove vendor/lib submodule"
```

### Submodule Pitfalls

| Issue | Description | Solution |
|---|---|---|
| **Forgotten init** | Submodule dir empty after clone | `git submodule update --init` |
| **Detached HEAD** | Submodules default to detached HEAD | Enter submodule, checkout branch |
| **Not updated** | `git pull` doesn't update submodules | `git submodule update --remote` |
| **Dirty submodule** | Uncommitted changes in submodule | Commit inside submodule first |
| **Recursive** | Submodules can have submodules | Use `--recursive` flag |
| **Partial clone** | CI may skip submodules | `--recurse-submodules` in CI |

### Submodule Configuration

`.gitmodules`:
```ini
[submodule "vendor/lib"]
    path = vendor/lib
    url = https://github.com/lib/lib.git
    branch = main
    shallow = true
```

### Subtree Merge (Alternative)

```bash
# Add subtree
git subtree add --prefix=vendor/lib https://github.com/lib/lib.git main --squash

# Update subtree
git subtree pull --prefix=vendor/lib https://github.com/lib/lib.git main --squash

# Push changes back to subtree repo
git subtree push --prefix=vendor/lib https://github.com/lib/lib.git main
```

### Submodule vs Subtree

| Aspect | Submodule | Subtree |
|---|---|---|
| Storage | Separate repo, pointer in parent | Merged into parent repo |
| History | Separate history | Mixed into parent history |
| Clone | Needs `--recurse-submodules` | Just works |
| Updates | Manual `submodule update` | `subtree pull` |
| Push back | Direct push from submodule | `subtree push` |
| Disk | Shared objects | Duplicated content |
| Complexity | Higher | Lower |

## Interview Questions

**Q: What is `git worktree` and why would you use it?**
A: Worktree allows multiple working directories for the same repo, each on a different branch. All share the same `.git/objects`. Use cases: hotfix while mid-development, running tests on one branch while coding another, building multiple versions simultaneously.

**Q: What are the pitfalls of Git submodules?**
A: (1) `git pull` doesn't update submodules — need `submodule update --remote`. (2) Submodules are in detached HEAD by default. (3) Empty submodule dirs after clone without `--recurse-submodules`. (4) Nested submodules need `--recursive`. (5) Removing submodules is complex (multiple config files to clean).

**Q: When would you choose subtree over submodule?**
A: Subtree is simpler when: the dependency rarely changes upstream, you want "just works" cloning, you don't need to push changes back, or you want a single repo for CI/CD. Submodule is better when: you need clear separation, want to track upstream independently, or the dependency has its own release cycle.

## References

- [Pro Git — Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Git Submodule Documentation](https://git-scm.com/docs/git-submodule)
- [Atlassian — Alternatives to Submodules](https://www.atlassian.com/git/tutorials/git-subtree)
