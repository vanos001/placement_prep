# Stashing

## Basic Stashing

```bash
git stash                         # stash tracked changes
git stash push -m "WIP: feature"  # with message
git stash -u                      # include untracked files
git stash -a                      # include all (even ignored)
git stash --keep-index            # stash only unstaged changes
git stash --include-untracked     # same as -u
```

## Listing & Inspecting

```bash
git stash list                    # list all stashes
git stash list --oneline          # compact format
git stash show                    # summary of latest
git stash show -p                 # full diff of latest
git stash show stash@{2}          # specific stash
git stash list --stat             # file change stats
```

## Applying & Removing

```bash
git stash pop                     # apply + remove latest
git stash apply                   # apply without removing
git stash apply stash@{1}         # apply specific stash
git stash drop stash@{0}          # delete specific stash
git stash clear                   # delete all stashes
```

## Creating Branches from Stash

```bash
git stash branch new-branch       # create branch from stash
# Creates branch from the commit when stash was made
# Applies the stash on top
# Removes the stash if successful
```

Useful when you stashed on the wrong branch or the stash conflicts with current state.

## Partial Stashing

```bash
git stash push -p -m "partial stash"  # interactive (patch mode)
# Choose which hunks to stash
```

## Stash with Untracked Files

```bash
# By default, only tracked files are stashed
git stash -u                      # include untracked
git stash -a                      # include ignored too

# Stash only specific files
git stash push -- src/main.py src/utils.py
```

## Stash Workflow Examples

### Context Switch
```bash
# Working on feature, need to fix urgent bug
git stash push -m "feature progress"
git switch main
git switch -c hotfix/bug-123
# ... fix bug ...
git switch feature
git stash pop
```

### Pull with Stash
```bash
git stash
git pull --rebase
git stash pop
# Or better:
git pull --rebase --autostash
```

## Interview Questions

**Q: What is the difference between `git stash pop` and `git stash apply`?**
A: `pop` applies the stash and removes it from the stash list. `apply` applies without removing — useful when you want to apply the same stash to multiple branches.

**Q: How do you stash only staged changes?**
A: `git stash --keep-index` stashes only unstaged changes, keeping staged changes in place. To stash only staged changes: `git stash push -p` and select only staged hunks, or `git stash --keep-index` then `git stash push --cached` (the second approach requires care).

**Q: What happens to stashed untracked files?**
A: By default, `git stash` only stashes tracked files. Use `git stash -u` (or `--include-untracked`) to include untracked files. Use `git stash -a` to include ignored files too.

## References

- [Pro Git — Stashing and Cleaning](https://git-scm.com/book/en/v2/Git-Tools-Stashing-and-Cleaning)
- [Git stash documentation](https://git-scm.com/docs/git-stash)
