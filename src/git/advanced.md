# Advanced Git Operations

## Cherry-Pick

Apply a specific commit from one branch to another:

```bash
git cherry-pick abc1234           # apply one commit
git cherry-pick abc1234 def5678   # apply multiple commits
git cherry-pick abc1234..def5678  # apply range (exclusive start)
git cherry-pick abc1234^..def5678 # apply range (inclusive start)
```

Options:
```bash
git cherry-pick -n abc1234        # stage changes without committing
git cherry-pick -x abc1234        # add "(cherry picked from ...)" message
git cherry-pick --no-commit abc1234  # same as -n
git cherry-pick --abort            # abort on conflict
git cherry-pick --continue         # continue after resolving conflict
```

**Use cases:**
- Hotfix: cherry-pick a fix from development to production
- Backport: apply a feature to an older release branch
- Selective integration: apply specific commits without merging entire branch

## git revert

Create a new commit that undoes a specific commit:

```bash
git revert abc1234                # revert one commit
git revert HEAD                   # revert last commit
git revert HEAD~3..HEAD           # revert last 3 commits
git revert -n abc1234             # no auto-commit (stage only)
git revert --mainline 1 merge-hash  # revert a merge commit (keep 1st parent)
```

**Revert vs Reset:**

| | `git revert` | `git reset` |
|---|---|---|
| Mechanism | New commit that undoes changes | Moves branch pointer |
| History | Preserved (adds new commit) | Rewritten (commits removed) |
| Safe for shared branches | ✅ Yes | ❌ No |
| Working directory | Untouched | Can be modified |

## git reset

Move HEAD and optionally modify staging area and working directory:

```bash
git reset --soft HEAD~1   # move HEAD, keep index + working tree
git reset --mixed HEAD~1  # move HEAD, reset index, keep working tree (default)
git reset --hard HEAD~1   # move HEAD, reset index + working tree (dangerous!)
```

```
--soft:   HEAD moves only (staged changes remain staged)
--mixed:  HEAD + index moves (changes become unstaged)
--hard:   HEAD + index + working tree (everything discarded)
```

**Reset a single file:**
```bash
git reset HEAD file.txt        # unstage (move from index to working tree)
git restore --staged file.txt  # modern equivalent
```

## git reflog

Records all HEAD movements (and branch tips):

```bash
git reflog                    # HEAD reflog
git reflog show main          # branch reflog
git reflog --date=iso         # with timestamps
```

Output:
```
abc1234 HEAD@{0}: commit: Add feature X
def5678 HEAD@{1}: checkout: moving from dev to main
ghi9012 HEAD@{2}: commit: Fix bug Y
```

**Recovery with reflog:**
```bash
# Accidentally reset --hard
git reset --hard HEAD~5

# Find the commit before the reset
git reflog
# abc1234 HEAD@{1}: commit: Last good commit

# Recover
git reset --hard HEAD@{1}
# or
git cherry-pick abc1234
```

## git bisect

Binary search through commit history to find the commit that introduced a bug:

```bash
git bisect start
git bisect bad                  # current commit is bad
git bisect good abc1234         # this commit was good

# Git checks out a middle commit
# Test it, then mark:
git bisect good    # this commit works
git bisect bad     # this commit is broken

# Repeat until found
# Git reports: abc1234 is the first bad commit

git bisect reset    # return to original state
```

### Automated Bisect

```bash
git bisect start HEAD abc1234
git bisect run ./test-script.sh
# Script should exit 0 for good, 1-124 or 126-127 for bad, 125 for skip
```

### Bisect with a Script

```python
#!/usr/bin/env python3
# test_script.py
import subprocess
result = subprocess.run(["make", "test"], capture_output=True)
exit(0 if result.returncode == 0 else 1)
```

```bash
git bisect run python3 test_script.py
```

## git worktree

Work on multiple branches simultaneously without stashing:

```bash
# Create a new worktree
git worktree add ../hotfix-branch hotfix
git worktree add -b new-feature ../feature-work main

# List worktrees
git worktree list

# Remove a worktree
git worktree remove ../hotfix-branch
git worktree prune  # clean up stale worktrees
```

## git submodule

Include external repositories as subdirectories:

```bash
# Add a submodule
git submodule add https://github.com/lib/lib.git vendor/lib

# Clone repo with submodules
git clone --recurse-submodules https://github.com/user/repo.git

# Initialize submodules after clone
git submodule init
git submodule update

# Or combined
git submodule update --init --recursive

# Update submodules to latest
git submodule update --remote

# Remove a submodule
git submodule deinit vendor/lib
git rm vendor/lib
rm -rf .git/modules/vendor/lib
```

`.gitmodules` file:
```ini
[submodule "vendor/lib"]
    path = vendor/lib
    url = https://github.com/lib/lib.git
    branch = main
```

## git notes

Attach metadata to commits without changing their hash:

```bash
git notes add -m "Reviewed by: Alice" abc1234
git notes show abc1234
git notes list
git log --show-notes
```

## git blame

Track who changed each line and when:

```bash
git blame file.txt
git blame -L 10,20 file.txt     # specific lines
git blame -w file.txt            # ignore whitespace
git blame -C file.txt            # detect moved lines
git blame -M file.txt            # detect moved lines within file
```

## git grep

Search working tree (faster than system grep for Git repos):

```bash
git grep "TODO"                  # search working tree
git grep -n "TODO"               # with line numbers
git grep -c "TODO"               # count matches per file
git grep "TODO" HEAD~5           # search a specific commit
git grep -l "function" -- "*.py" # list matching files
git grep -p "class"              # show matching function context
```

## git archive

Create a tar/zip of a specific commit:

```bash
git archive --format=tar HEAD | gzip > release.tar.gz
git archive --format=zip -o release.zip v1.0
git archive --prefix=project/ HEAD | gzip > project.tar.gz
```

## git clean

Remove untracked files:

```bash
git clean -n          # dry run
git clean -f          # force remove untracked files
git clean -fd         # + directories
git clean -fX         # only ignored files
git clean -fx         # all untracked + ignored
git clean -i          # interactive mode
```

## git shortlog

Summarize `git log` output (useful for contributor stats):

```bash
git shortlog -sn        # count commits per author
git shortlog -sn --all  # across all branches
git shortlog HEAD~20    # last 20 commits
```

## git diff-tree

Low-level diff between tree objects:

```bash
git diff-tree --no-commit-id -r abc1234  # files changed in a commit
git diff-tree -p abc1234                  # patch output
```

## git rev-parse

Parse Git revision references:

```bash
git rev-parse HEAD              # full SHA
git rev-parse --short HEAD      # abbreviated
git rev-parse --verify HEAD     # verify it's a valid object
git rev-parse --show-toplevel   # repo root directory
git rev-parse --git-dir         # .git directory path
git rev-parse --abbrev-ref HEAD # current branch name
```

## git describe

Describe a commit using the nearest tag:

```bash
git describe                    # v1.2.3-14-g2414721
git describe --tags             # include lightweight tags
git describe --always           # fallback to hash if no tags
```

Format: `<tag>-<distance>-g<hash>`

## Interview Questions

### Beginner

**Q: What is `git cherry-pick` used for?**
A: Cherry-pick applies a specific commit from one branch to another. It's useful for: applying hotfixes to production, backporting features to release branches, or selectively integrating changes without a full merge.

**Q: How do you undo the last commit without losing changes?**
A: `git reset --soft HEAD~1` moves HEAD back one commit but keeps all changes staged. `git reset --mixed HEAD~1` (default) unstages the changes too. Both preserve the working directory.

### Intermediate

**Q: Explain `git bisect` and when you'd use it.**
A: Bisect performs a binary search through commit history to find the commit that introduced a bug. You mark the current commit as "bad" and a known-good commit as "good." Git checks out middle commits for you to test. For automation: `git bisect run ./test.sh`.

**Q: What is the difference between `git revert` and `git reset`?**
A: Revert creates a new commit that undoes changes (safe for shared history). Reset moves the branch pointer, potentially discarding commits (rewrites history). Use revert for public branches, reset for local cleanup.

### Advanced

**Q: How do you recover a deleted branch?**
A: Use `git reflog` to find the last commit on the deleted branch, then `git branch <name> <hash>` to recreate it. Example: `git reflog` → find `branch: Deleted branch feature` → `git branch feature abc1234`.

**Q: Explain `git worktree` and its use cases.**
A: Worktree allows multiple working directories for the same repository, each checked out to a different branch. Use cases: quickly context-switching between branches, hotfix while mid-development, running tests on one branch while coding on another. All worktrees share the same `.git/objects` (no duplication).

### Common Traps

1. **Cherry-pick creates duplicates**: The cherry-picked commit has a different hash. Subsequent merges may show conflicts with the "same" change.
2. **`reset --hard` is destructive**: Always check `git reflog` after accidents.
3. **Bisect requires a clean working tree**: Commit or stash changes before bisecting.
4. **Submodule updates are manual**: `git pull` doesn't update submodules — use `git submodule update --remote`.
5. **Worktree branch exclusivity**: A branch can only be checked out in one worktree at a time.

## References

- [Pro Git — Reset Demystified](https://git-scm.com/book/en/v2/Git-Tools-Reset-Demystified)
- [Pro Git — Searching](https://git-scm.com/book/en/v2/Git-Tools-Searching)
- [Pro Git — Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Pro Git — Worktrees](https://git-scm.com/docs/git-worktree)
