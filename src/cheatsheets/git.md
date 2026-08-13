# Git Cheatsheet

## 🔧 Setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.editor vim
git config --list
```

## 📦 Repository

```bash
git init                    # Initialize new repo
git clone <url>             # Clone remote repo
git clone <url> <dir>       # Clone into specific directory
git remote add origin <url> # Add remote
git remote -v               # List remotes
```

## 📝 Basic Workflow

```bash
git status                  # Show working tree status
git add <file>              # Stage specific file
git add .                   # Stage all changes
git add -p                  # Stage patches interactively
git commit -m "message"     # Commit with message
git commit -am "message"    # Stage + commit tracked files
git push                    # Push to remote
git pull                    # Fetch + merge from remote
git fetch                   # Fetch without merging
```

## 📜 History

```bash
git log                     # Full log
git log --oneline           # Compact log
git log --graph --oneline   # Visual branch graph
git log -5                  # Last 5 commits
git log --author="name"     # Filter by author
git log --since="2024-01-01" # Filter by date
git log --stat              # Show file changes
git log -p                  # Show diffs
git show <commit>           # Show specific commit
git blame <file>            # Show who changed each line
```

## 🌿 Branching

```bash
git branch                  # List local branches
git branch -a               # List all branches
git branch <name>           # Create branch
git checkout <name>         # Switch branch
git checkout -b <name>      # Create + switch
git switch <name>           # Switch (modern)
git switch -c <name>        # Create + switch (modern)
git branch -d <name>        # Delete merged branch
git branch -D <name>        # Force delete branch
git branch -m <old> <new>   # Rename branch
```

## 🔀 Merging

```bash
git merge <branch>          # Merge branch into current
git merge --no-ff <branch>  # Merge with merge commit
git merge --squash <branch> # Squash merge (stage only)
git merge --abort           # Abort merge
```

## 🔄 Rebasing

```bash
git rebase <branch>         # Rebase current onto branch
git rebase -i HEAD~3        # Interactive rebase (last 3 commits)
git rebase --abort          # Abort rebase
git rebase --continue       # Continue after resolving

# Interactive rebase commands:
# pick   = use commit
# reword = use commit, edit message
# edit   = use commit, stop for amending
# squash = use commit, meld into previous
# fixup  = like squash, discard message
# drop   = remove commit
```

## ↩️ Undoing

```bash
git reset HEAD <file>       # Unstage file
git checkout -- <file>      # Discard changes (dangerous!)
git restore <file>          # Discard changes (modern)
git restore --staged <file> # Unstage (modern)

git reset --soft HEAD~1     # Undo commit, keep changes staged
git reset --mixed HEAD~1    # Undo commit, keep changes unstaged
git reset --hard HEAD~1     # Undo commit, discard changes (dangerous!)

git revert <commit>         # Create new commit that undoes changes
git revert HEAD             # Revert last commit
```

## 📋 Stashing

```bash
git stash                   # Stash changes
git stash push -m "message" # Stash with message
git stash list              # List stashes
git stash pop               # Apply + remove latest stash
git stash apply             # Apply without removing
git stash apply stash@{2}  # Apply specific stash
git stash drop stash@{0}   # Delete specific stash
git stash clear             # Delete all stashes
```

## 🏷️ Tags

```bash
git tag                     # List tags
git tag <name>              # Create lightweight tag
git tag -a <name> -m "msg"  # Create annotated tag
git tag -d <name>           # Delete tag
git push origin <tag>       # Push tag
git push --tags             # Push all tags
```

## 🔍 Diff

```bash
git diff                    # Unstaged changes
git diff --staged           # Staged changes
git diff <branch1> <branch2> # Between branches
git diff <commit1> <commit2> # Between commits
git diff HEAD~3             # Changes in last 3 commits
```

## 🧹 Cleanup

```bash
git clean -n                # Show untracked files to delete
git clean -f                # Delete untracked files
git gc                      # Garbage collection
git prune                   # Remove unreachable objects
```

## 🌐 Remote Operations

```bash
git push origin <branch>    # Push branch to remote
git push -u origin <branch> # Push + set upstream
git push --force            # Force push (dangerous!)
git push --force-with-lease # Safer force push
git pull --rebase           # Pull with rebase instead of merge
git remote prune origin     # Remove stale remote branches
```

## 💡 Common Workflows

### Feature Branch
```bash
git switch main
git pull
git switch -c feature/my-feature
# ... work ...
git add .
git commit -m "feat: add my feature"
git push -u origin feature/my-feature
# Create PR on GitHub/GitLab
```

### Sync Fork
```bash
git remote add upstream <original-repo-url>
git fetch upstream
git switch main
git merge upstream/main
git push
```

### Fix Last Commit
```bash
# Amend message
git commit --amend -m "new message"

# Add forgotten file
git add forgotten-file.txt
git commit --amend --no-edit
```

## ⚡ Quick Reference

| Command | Description |
|---------|-------------|
| `git add -p` | Stage patches interactively |
| `git commit --amend` | Modify last commit |
| `git stash` | Save uncommitted changes |
| `git rebase -i` | Interactive rebase |
| `git reset --soft HEAD~1` | Undo commit, keep changes |
| `git reflog` | Show all HEAD movements |
| `git bisect start` | Binary search for bugs |
| `git cherry-pick <hash>` | Apply specific commit |

## 🔗 Cross-References

- [Linux Cheatsheet](./linux.md) — Command-line tools
- [Architecture Cheatsheet](./architecture.md) — CI/CD, deployment
