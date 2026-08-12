# Git Fundamentals

## Repository Setup

```bash
# Initialize a new repository
git init

# Clone an existing repository
git clone https://github.com/user/repo.git
git clone https://github.com/user/repo.git my-folder  # custom directory
git clone --depth 1 https://github.com/user/repo.git   # shallow clone
git clone --branch dev https://github.com/user/repo.git # specific branch
```

## Configuration

```bash
# Identity (required for commits)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# View all config
git config --list
git config --list --show-origin  # with file paths

# Repository-specific config
git config user.email "work@company.com"  # overrides global for this repo

# Useful defaults
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global core.autocrlf input  # Linux/Mac
git config --global core.autocrlf true   # Windows
git config --global rerere.enabled true  # Remember merge conflict resolutions
```

Config hierarchy (later overrides earlier):
1. System: `/etc/gitconfig`
2. Global: `~/.gitconfig`
3. Local: `.git/config`

## The Three Areas

```
Working Directory     Staging Area (Index)     Repository (.git)
   (files you edit)     (git add)                (git commit)
        ↑                     │                        │
        │                     │                        │
   git checkout /          git add                 git commit
   git restore            git reset HEAD           git log
```

## Staging & Committing

```bash
# Check status
git status
git status -s  # short format
git status --porcelain  # machine-readable

# Stage files
git add file.txt           # stage specific file
git add src/               # stage directory
git add -p                 # interactive staging (patch mode)
git add -u                 # stage all tracked modified files
git add .                  # stage everything (use carefully)

# Unstage files
git restore --staged file.txt  # modern way
git reset HEAD file.txt        # older way

# Commit
git commit -m "feat: add user authentication"
git commit -am "fix: resolve race condition"  # stage tracked + commit
git commit --amend            # modify last commit
git commit --amend --no-edit  # amend without changing message
git commit --allow-empty -m "trigger CI"  # empty commit
```

### Commit Message Conventions

```
<type>(<scope>): <subject>

<body>

<footer>
```

| Type | Usage |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting (no logic change) |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Build, CI, dependencies |
| `perf` | Performance improvement |

Example:
```
feat(auth): add JWT refresh token rotation

Implement automatic token rotation when the access token expires.
The refresh token is invalidated after use and a new pair is issued.

Closes #142
```

## Viewing History

```bash
# Basic log
git log
git log --oneline          # compact
git log --graph --oneline --all  # visual branch graph
git log -n 5               # last 5 commits
git log --since="2 weeks ago"
git log --author="John"
git log --grep="fix"       # search commit messages

# Show changes
git log -p                 # with diffs
git log --stat             # with file change stats
git log --word-diff        # word-level changes

# Specific commit
git show abc1234
git show abc1234:src/main.py  # file at that commit

# Blame
git blame file.txt
git blame -L 10,20 file.txt   # specific lines
```

## Diffing

```bash
# Working directory vs Index
git diff

# Index vs HEAD (staged changes)
git diff --staged
git diff --cached  # synonym

# Between commits
git diff abc1234 def5678
git diff main..feature

# Between branches
git diff main feature

# Stat summary
git diff --stat

# Specific file
git diff -- src/main.py
```

## Undoing Changes

```bash
# Discard working directory changes (dangerous!)
git restore file.txt
git checkout -- file.txt  # older way

# Unstage a file
git restore --staged file.txt

# Modify last commit
git commit --amend -m "new message"

# Undo commits (keep changes in working directory)
git reset --soft HEAD~1   # keep staged + working
git reset --mixed HEAD~1  # keep working (default)
git reset --hard HEAD~1   # discard everything (dangerous!)

# Revert a commit (creates new commit that undoes changes)
git revert abc1234
git revert HEAD  # revert last commit
```

### Reset vs Revert

| Aspect | `git reset` | `git revert` |
|---|---|---|
| History | Removes commits from history | Adds a new "undo" commit |
| Safe for shared branches | ❌ No | ✅ Yes |
| Working directory | Can modify | Untouched |
| Use case | Local cleanup | Public undo |

## .gitignore

```bash
# Patterns
*.log              # all .log files
build/             # build directory
!important.log     # negation: track this file
*.o                # object files
**/temp            # temp in any directory
doc/*.pdf          # PDFs in doc/ (not subdirs)
```

Common `.gitignore` patterns:
```
# Dependencies
node_modules/
vendor/
__pycache__/
*.pyc

# Build output
dist/
build/
*.o
*.exe

# Environment
.env
.env.local
*.key

# IDE
.vscode/
.idea/
*.swp
*~
.DS_Store
```

> **Tip**: Use [gitignore.io](https://www.toptal.com/developers/gitignore) for language-specific templates.

## git stash

```bash
git stash                     # stash tracked changes
git stash -m "WIP: feature"  # with message
git stash -u                  # include untracked files
git stash -a                  # include all (even ignored)

git stash list                # list all stashes
git stash show -p stash@{0}  # show stash diff
git stash pop                 # apply and remove latest stash
git stash apply stash@{1}    # apply without removing
git stash drop stash@{0}     # delete a stash
git stash clear               # delete all stashes

git stash branch new-branch   # create branch from stash
```

## git clean

```bash
git clean -n    # dry run (show what would be removed)
git clean -f    # remove untracked files
git clean -fd   # remove untracked files and directories
git clean -fx   # remove untracked and ignored files
```

## Aliases

```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.unstage "restore --staged"
git config --global alias.last "log -1 HEAD"
```

## Interview Questions

### Beginner

**Q: What is the difference between `git add .` and `git add -u`?**
A: `git add .` stages all changes (new, modified, deleted) in the current directory and subdirectories. `git add -u` stages only modifications and deletions of already-tracked files (no new files).

**Q: What does `git commit --amend` do?**
A: It replaces the last commit with a new commit that includes any currently staged changes. Use it to fix the last commit's message or add forgotten changes. Avoid amending commits that have been pushed.

### Intermediate

**Q: Explain `git reset --soft`, `--mixed`, and `--hard`.**
A: All move HEAD to a specified commit. `--soft`: keeps staged + working directory changes. `--mixed` (default): unstages changes but keeps working directory. `--hard`: discards all changes — both staged and working directory.

**Q: When would you use `git revert` instead of `git reset`?**
A: `revert` is safe for shared/public branches because it adds a new commit that undoes changes without rewriting history. `reset` rewrites history and should only be used on local, unpushed commits.

### Advanced

**Q: How does `git add -p` work internally?**
A: Git computes the diff between the working tree and the index, then presents each hunk interactively. You choose `y` (stage), `n` (skip), `s` (split), `e` (edit), etc. The selected hunks update the index, allowing partial staging of a file's changes.

**Q: What happens to orphaned commits after `git reset --hard`?**
A: They remain in the object database as unreachable objects. They can be recovered via `git reflog` until garbage collected (default: 30 days for unreachable objects, configurable via `gc.pruneExpire`).

## References

- [Pro Git — Recording Changes](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository)
- [Pro Git — Undoing Things](https://git-scm.com/book/en/v2/Git-Basics-Undoing-Things)
- [Pro Git — Git Stashing](https://git-scm.com/book/en/v2/Git-Tools-Stashing-and-Cleaning)
- [Git Documentation](https://git-scm.com/docs)
