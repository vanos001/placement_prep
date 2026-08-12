# Rebasing

## What Is Rebase?

Rebase rewrites commit history by moving a sequence of commits to a new base commit. It produces a **linear history** unlike merge's non-linear topology.

```
Before rebase:                     After rebase:
A---B---C (main)                   A---B---C (main)
     \                                   \
      D---E---F (feature)                D'---E'---F' (feature)
```

The commits D', E', F' are **new commits** (different hashes) with the same changes.

## Basic Rebase

```bash
git switch feature
git rebase main
# Replays feature commits on top of main
```

Steps Git performs internally:
1. Finds common ancestor (merge base) of feature and main
2. Saves feature commits as temporary patches
3. Resets feature to point at main's tip
4. Replays each patch as a new commit

## Interactive Rebase

The most powerful Git tool for cleaning up history:

```bash
git rebase -i HEAD~5    # rebase last 5 commits
git rebase -i main      # rebase since diverging from main
```

Opens an editor with:
```
pick a1b2c3d feat: add user model
pick d4e5f6a feat: add user API
pick g7h8i9j fix: typo in user model
pick k0l1m2n feat: add user validation
pick o3p4q5r wip: debugging
```

### Interactive Commands

| Command | Short | Effect |
|---|---|---|
| `pick` | `p` | Keep commit as-is |
| `reword` | `r` | Keep commit, edit message |
| `edit` | `e` | Pause at this commit (amend) |
| `squash` | `s` | Meld into previous commit, keep message |
| `fixup` | `f` | Meld into previous commit, discard message |
| `drop` | `d` | Remove commit entirely |
| `exec` | `x` | Run shell command after this commit |

### Common Interactive Rebase Patterns

**Squash related commits:**
```
pick a1b2c3d feat: add user model
squash d4e5f6a feat: add user API
squash g7h8i9j fix: typo in user model
# Result: one clean commit
```

**Reorder commits:**
```
pick k0l1m2n feat: add user validation  # moved up
pick a1b2c3d feat: add user model
pick d4e5f6a feat: add user API
```

**Edit a past commit:**
```
edit a1b2c3d feat: add user model  # pause here
pick d4e5f6a feat: add user API
# Git pauses → make changes → git commit --amend → git rebase --continue
```

**Drop a commit:**
```
pick a1b2c3d feat: add user model
drop o3p4q5r wip: debugging  # remove this
```

## Rebase onto a Different Branch

```bash
# Move feature branch to start from a different base
git rebase --onto main old-base feature
```

Example:
```
Before:
A---B (main)
     \
      C---D (old-base)
           \
            E---F (feature)

git rebase --onto main old-base feature

After:
A---B (main)
     \
      E'---F' (feature)
```

## Rebase vs Merge

### The Debate

**Merge advocates**:
- Preserves true history
- Safe for shared branches
- Clear integration points

**Rebase advocates**:
- Clean, linear history
- Easier `git bisect`
- Simpler `git log`

### Best Practice: Rebase + Merge

Many teams use this workflow:
1. **Rebase** feature branch onto latest main (clean up history)
2. **Merge** feature into main with `--no-ff` (preserve integration point)

```bash
# On feature branch
git rebase main
# Resolve any conflicts

# Switch to main
git switch main
git merge --no-ff feature
```

## Handling Rebase Conflicts

```bash
git rebase main
# CONFLICT in src/main.py

# 1. Resolve the conflict in the file
# 2. Stage the resolution
git add src/main.py
# 3. Continue rebase
git rebase --continue

# Or abort if things go wrong
git rebase --abort

# Or skip this commit
git rebase --skip
```

## Autosquash

Automatically reorder fixup commits:

```bash
# Create a fixup commit
git commit --fixup=a1b2c3d

# Later, interactive rebase with autosquash
git rebase -i --autosquash main
# The fixup commit is automatically positioned and marked
```

## Rebase Configuration

```bash
# Auto-stash before rebase
git config --global rebase.autostash true

# Auto-squash by default
git config --global rebase.autosquash true

# Update refs on rebase
git config --global rebase.updateRefs true
```

## Pull with Rebase

```bash
git pull --rebase
# Equivalent to: git fetch + git rebase origin/main

# Set as default for this branch
git config --global branch.autoSetupRebase always

# Or for all branches
git config --global pull.rebase true
```

## Interview Questions

### Beginner

**Q: What is the difference between `git merge` and `git rebase`?**
A: Merge creates a merge commit combining two branches, preserving the original history. Rebase replays commits from one branch onto another, creating a linear history with new commit hashes.

**Q: When should you NOT use rebase?**
A: Never rebase commits that have been pushed to a shared branch. Rebasing rewrites commit hashes, which causes problems for collaborators who have based work on the original commits.

### Intermediate

**Q: How do you squash the last 3 commits into one?**
A: `git rebase -i HEAD~3`. In the editor, mark the second and third commits as `squash` (or `fixup`). Save and edit the combined commit message.

**Q: What is `git rebase --onto` used for?**
A: It rebases commits onto a new base, specifying which commits to move. Useful for transplanting a subset of commits: `git rebase --onto target source feature` moves commits from `source..feature` onto `target`.

### Advanced

**Q: You started a rebase and hit many conflicts. How do you safely abort?**
A: `git rebase --abort` returns to the state before the rebase started. If you've already resolved some conflicts and want to keep progress: `git rebase --continue`. To skip a problematic commit: `git rebase --skip`.

**Q: Explain the `rerere` feature in the context of rebasing.**
A: `rerere` (reuse recorded resolution) records conflict resolutions. When rebasing repeatedly onto a changing main, the same conflicts may recur. With `rerere` enabled, Git automatically applies previous resolutions, saving significant time.

### Common Traps

1. **Rebasing shared branches**: Creates divergent histories for collaborators.
2. **Forgetting `--abort`**: You can always abort a rebase in progress.
3. **Losing commits**: Use `git reflog` to recover if you accidentally drop commits.
4. **Rebase vs merge in pull requests**: Some teams prefer merge commits in PRs for traceability.
5. **Interactive rebase order**: Commits are listed oldest-first (bottom-to-top), opposite of `git log`.

## References

- [Pro Git — Rebasing](https://git-scm.com/book/en/v2/Git-Branching-Rebasing)
- [Git rebase documentation](https://git-scm.com/docs/git-rebase)
- [Atlassian — Merging vs Rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)
