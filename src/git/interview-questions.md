# Git Interview Questions

## Beginner

### Q1: What is Git?
**A:** Git is a distributed version control system that tracks changes in files over time. Every developer has a complete copy of the repository including full history. It enables collaboration, branching, merging, and reverting changes.

### Q2: What is the difference between `git merge` and `git rebase`?
**A:** Merge creates a merge commit combining two branches, preserving the original history (non-linear). Rebase replays commits onto a new base, creating a linear history with new commit hashes. Merge is safe for shared branches; rebase is not.

### Q3: Explain the three areas of Git.
**A:** (1) Working directory — files you edit, (2) Staging area (index) — files marked for the next commit, (3) Repository (.git) — committed history. `git add` moves changes from working → staging. `git commit` moves from staging → repository.

### Q4: What is `git stash`?
**A:** Temporarily shelves changes in the working directory and staging area, reverting to a clean state. Use `git stash pop` to restore. Useful when you need to switch branches but aren't ready to commit.

### Q5: What is a detached HEAD?
**A:** When HEAD points directly to a commit instead of a branch. Commits made in this state are orphaned (not on any branch). Create a branch to keep them: `git switch -c new-branch`.

## Intermediate

### Q6: Explain `git reset --soft`, `--mixed`, and `--hard`.
**A:** All move HEAD to a specified commit. `--soft`: keeps staged + working changes (only HEAD moves). `--mixed`: unstages changes, keeps working directory (default). `--hard`: discards all changes — both staged and working.

### Q7: How does Git handle merge conflicts?
**A:** When both branches modify the same region differently, Git can't auto-merge. It marks conflicts with `<<<<<<<`, `=======`, `>>>>>>>` markers. You manually edit the file, `git add` it, then `git commit` to complete the merge.

### Q8: What is `git cherry-pick`?
**A:** Applies a specific commit from one branch to the current branch, creating a new commit with the same changes but a different hash. Useful for hotfixes and backports.

### Q9: How do you undo a pushed commit?
**A:** Use `git revert <commit-hash>` — it creates a new commit that undoes the changes. This is safe for shared branches because it doesn't rewrite history. Don't use `git reset` on pushed commits.

### Q10: What is `git bisect`?
**A:** Binary search through commit history to find which commit introduced a bug. Mark current as "bad," a known-good commit as "good." Git checks out middle commits for testing. Can be automated with `git bisect run <script>`.

### Q11: Explain the Git workflow you'd use for a team project.
**A:** (1) Create feature branch from main, (2) make small, focused commits, (3) rebase onto latest main before PR, (4) open PR for code review, (5) address feedback, (6) squash-merge or merge with --no-ff into main, (7) CI/CD deploys from main.

### Q12: What is the difference between `git fetch` and `git pull`?
**A:** `fetch` downloads remote changes without modifying your working tree (safe). `pull` = `fetch` + `merge` (or `rebase` with `--rebase`). Fetch lets you inspect changes before integrating.

## Advanced

### Q13: How does Git store data internally?
**A:** Git uses four object types: blob (file content), tree (directory structure), commit (snapshot + metadata), tag (annotated tag). All identified by SHA-1 hashes. Stored in `.git/objects/`, packed into packfiles for efficiency with delta compression.

### Q14: Explain `git reflog` and how it helps with recovery.
**A:** Reflog records all HEAD movements (commits, resets, checkouts, rebases). Even "deleted" commits exist in the object store. `git reflog` shows the history, then `git reset --hard HEAD@{n}` or `git cherry-pick` recovers them. Entries expire after 30-90 days.

### Q15: How does `git rebase -i` work internally?
**A:** (1) Saves the specified commits as patches, (2) resets HEAD to the target base, (3) replays each patch according to your instructions (pick, squash, fixup, drop, reword, edit). Each replayed commit gets a new hash because its parent changes.

### Q16: What is `rerere` and when is it useful?
**A:** `rerere` (reuse recorded resolution) remembers how you resolved merge conflicts. If the same conflict appears again (common during rebases), Git auto-applies the previous resolution. Enable with `git config rerere.enabled true`.

### Q17: How would you recover from a `git reset --hard` that discarded important work?
**A:** (1) `git reflog` to find the commit before the reset, (2) `git reset --hard HEAD@{1}` or `git cherry-pick <hash>` to recover. If reflog doesn't help: `git fsck --lost-found` finds orphaned objects. Act quickly — `git gc` prunes unreachable objects after 30 days.

### Q18: Explain Git's packfile mechanism.
**A:** Loose objects are stored individually. Over time, `git gc` packs them into packfiles using delta compression — similar objects store only differences. Pack index files enable fast O(log n) lookup. This reduces storage and speeds up network transfer.

### Q19: What is `--force-with-lease` and when should you use it?
**A:** Safer alternative to `--force`. It checks that the remote branch hasn't been updated since your last fetch. If someone else pushed, the push fails. Use after interactive rebase on a personal feature branch.

### Q20: How do submodules work internally?
**A:** A submodule is a Git repository nested inside another. The parent repo stores the submodule's commit hash as a special "gitlink" entry. `.gitmodules` maps paths to URLs. `git submodule update` checks out the recorded commit. Submodules are not auto-updated on pull.

## Scenario-Based Questions

### Q21: You accidentally committed to the wrong branch. How do you fix it?
**A:**
```bash
# Move the commit to the correct branch
git branch correct-branch          # save current position
git checkout wrong-branch
git reset --hard HEAD~1            # remove from wrong branch
git checkout correct-branch
git cherry-pick <commit-hash>      # apply to correct branch
```

### Q22: You need to split a large commit into smaller ones. How?
**A:** `git reset --soft HEAD~1` (keep all changes staged), then `git add -p` to stage hunks selectively, committing each logical piece separately.

### Q23: Two team members rebased the same branch. How do you resolve?
**A:** One person should `git rebase --onto origin/feature <old-base> feature` to replay their changes on top of the other's rebased branch. Or: `git pull --rebase origin feature` and resolve conflicts.

### Q24: You need to find when a specific line was introduced and why.
**A:** `git blame file.txt` shows who last modified each line and which commit. Use `git log --follow -p file.txt` to see the full history including renames. `git log -S "code"` searches for commits that added/removed that string.

### Q25: How do you handle large binary files in Git?
**A:** Use Git LFS (Large File Storage): `git lfs install && git lfs track "*.psd"`. LFS stores pointer files in Git and actual content on a separate server. Without LFS: use `.gitignore`, store binaries in artifact storage, or use `git annex`.

## Common Traps

| Trap | Reality |
|---|---|
| "Git tracks changes" | Git stores snapshots; diffs are computed on demand |
| "Branches are expensive" | Branches are 41-byte files (ref + newline) |
| "Deleted means gone" | Objects persist until GC'd (30+ days) |
| "Rebase = delete old commits" | Old commits exist in reflog until GC'd |
| "Merge commit = bad" | Merge commits preserve branch topology — useful for traceability |
| "git pull is safe" | `git pull --rebase` can cause surprises; prefer explicit fetch + merge/rebase |
| "Force push is always bad" | `--force-with-lease` is safe for personal branches |
| "Submodules update automatically" | They don't — manual `git submodule update` required |
| "git stash is a stack" | It is, but `stash@{n}` shifts on pop — use `stash apply` to keep |
| "Tags and branches are the same" | Tags don't move; branches advance with commits |
