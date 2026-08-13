# Branching & Merging

## What Is a Branch?

A branch in Git is a **lightweight, movable pointer** to a commit. It's stored as a 41-byte file containing a SHA-1 hash:

```bash
cat .git/refs/heads/main
# 7a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
```

When you commit on a branch, the branch pointer advances automatically.

## Branch Operations

```bash
# Create
git branch feature              # create without switching
git checkout -b feature         # create and switch
git switch -c feature           # modern alternative

# List
git branch                      # local branches
git branch -r                   # remote branches
git branch -a                   # all branches
git branch -v                   # with last commit
git branch --merged             # merged into current
git branch --no-merged          # not yet merged

# Switch
git switch main                 # modern
git checkout main               # traditional

# Rename
git branch -m old-name new-name
git branch -m new-name          # rename current branch

# Delete
git branch -d feature           # safe: only if merged
git branch -D feature           # force: delete even if unmerged

# Set upstream
git branch -u origin/feature    # set tracking branch
git branch --set-upstream-to=origin/feature
```

## Merging

### Fast-Forward Merge

When the target branch is a direct ancestor of the source branch — no new commits on the target since the divergence point:

```
Before:
main:    A --- B --- C
                  \
feature:           D --- E

After (git merge feature):
main:    A --- B --- C --- D --- E
```

```bash
git switch main
git merge feature
# Fast-forward
```

Git simply moves the branch pointer forward. No merge commit is created.

### Three-Way Merge

When both branches have diverged:

```
Before:
main:    A --- B --- C --- F
                  \
feature:           D --- E

After (git merge feature):
main:    A --- B --- C --- F --- M
                  \             /
feature:           D --- E ----
```

```bash
git switch main
git merge feature
# Merge made by the 'ort' strategy.
```

Git creates a **merge commit** (M) with two parents.

### Merge Strategies

```bash
git merge -s ort feature      # default (renamed from 'recursive')
git merge -s ours feature     # keep current branch's version
git merge -s recursive -X ours feature   # favor current on conflicts
git merge -s recursive -X theirs feature # favor incoming on conflicts
```

### Merge Options

```bash
git merge feature --no-ff      # always create merge commit (no fast-forward)
git merge feature --squash     # stage changes but don't commit
git merge feature --no-commit  # merge but don't auto-commit
git merge feature --abort      # abort merge, restore pre-merge state
git merge feature --ff-only    # only merge if fast-forward is possible
```

## Merge Conflicts

When the same region is modified differently on both branches:

```bash
git merge feature
# CONFLICT (content): Merge conflict in src/main.py
# Automatic merge failed; fix conflicts and then commit the result.
```

Conflict markers in the file:
```python
<<<<<<< HEAD
def greet(name):
    return f"Hello, {name}!"
=======
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
>>>>>>> feature
```

### Resolving Conflicts

```bash
# 1. Edit the file (choose or combine changes)
# 2. Stage the resolved file
git add src/main.py

# 3. Complete the merge
git commit

# Or use a merge tool
git mergetool
```

### Conflict Resolution Tools

```bash
git config --global merge.tool vimdiff
git config --global mergetool.keepBackup false

# Popular tools: vimdiff, meld, kdiff3, VS Code, IntelliJ
```

### Preventing Conflicts

- Pull/rebase frequently
- Keep branches short-lived
- Communicate about shared files
- Use small, focused commits
- Modularize code to reduce overlap

## Merge vs Rebase

| Aspect | Merge | Rebase |
|---|---|---|
| History | Non-linear (preserves topology) | Linear (rewrites history) |
| Merge commit | Created | Not created |
| Safe for shared branches | ✅ Yes | ❌ No |
| Commit hashes | Unchanged | New hashes |
| `git bisect` | Harder (merge noise) | Easier (linear) |
| Traceability | Clear branch origins | Lost branch context |

### When to Use Each

**Use merge when:**
- Working on shared/public branches
- You want to preserve the exact history
- Feature branch is shared with others
- You want clear visibility of integration points

**Use rebase when:**
- Cleaning up local commits before sharing
- Maintaining a clean linear history
- Updating a feature branch with latest main
- Individual workflow (not shared branches)

### The Golden Rule

> **Never rebase commits that have been pushed to a shared branch.**

Rebasing rewrites commit hashes. If someone has based work on the old hashes, rebasing causes divergence.

## Octopus Merge

Merging multiple branches at once:

```bash
git merge feature1 feature2 feature3
```

Used primarily for merging many topic branches that don't conflict. Common in integration branches.

## Fast-Forward vs No-Fast-Forward

Many teams prefer `--no-ff` to always create merge commits:

```bash
git config --global merge.ff false  # always no-ff
```

Benefits:
- Every merge is traceable in the log
- `git revert` can undo an entire feature by reverting the merge commit
- Preserves the branch topology in history

## Interview Questions

### Beginner

**Q: What is the difference between `git branch` and `git checkout -b`?**
A: `git branch feature` creates a branch but stays on the current branch. `git checkout -b feature` (or `git switch -c feature`) creates and switches to the new branch.

**Q: What is a fast-forward merge?**
A: When the target branch hasn't moved since the source branch diverged, Git simply moves the pointer forward — no merge commit needed. This is possible when the target branch is a direct ancestor of the source.

### Intermediate

**Q: How do you resolve a merge conflict?**
A: (1) Open the conflicted file and look for conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`). (2) Decide which changes to keep (or combine them). (3) Remove the conflict markers. (4) `git add` the resolved file. (5) `git commit` to complete the merge.

**Q: Why might you prefer `--no-ff` merges?**
A: `--no-ff` always creates a merge commit, preserving the branch topology. This makes it easy to: identify feature boundaries in history, revert an entire feature with one `git revert`, and understand when branches were integrated.

### Advanced

**Q: What is `rerere` and when is it useful?**
A: `rerere` (reuse recorded resolution) remembers how you resolved merge conflicts. If the same conflict appears again (common when rebasing), Git automatically applies the previous resolution. Enable with `git config rerere.enabled true`.

**Q: How does Git's `ort` merge strategy differ from the old `recursive` strategy?**
A: `ort` (Ostensibly Recursive's Twin) is the default since Git 2.34 (Nov 2021). It's faster, uses less memory, and handles directory renames better. It produces the same results as `recursive` for most cases but handles edge cases more efficiently.

### Common Traps

1. **Merging the wrong direction**: `git merge main` (on feature) vs `git merge feature` (on main) — know which branch you're on!
2. **Forgetting `--no-ff`**: Fast-forward merges lose branch topology.
3. **Resolving conflicts incorrectly**: Always test after resolving.
4. **Merge vs rebase on shared branches**: Rebase rewrites history — don't do it on shared branches.
5. **Aborting a merge too late**: Use `git merge --abort` before committing.

## References

- [Pro Git — Branching](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell)
- [Pro Git — Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
- [Git merge documentation](https://git-scm.com/docs/git-merge)
