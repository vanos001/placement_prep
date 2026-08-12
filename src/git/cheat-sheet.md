# Git Cheat Sheet

## Setup
```bash
git config --global user.name "Name"
git config --global user.email "email"
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global alias.lg "log --oneline --graph --all"
```

## Create & Clone
```bash
git init                          # new repo
git clone <url>                   # clone repo
git clone --depth 1 <url>         # shallow clone
git clone --branch dev <url>      # specific branch
```

## Basic Workflow
```bash
git status                        # check status
git status -s                     # short format
git add <file>                    # stage file
git add -p                        # interactive staging
git add .                         # stage all
git commit -m "message"           # commit
git commit --amend                # fix last commit
git diff                          # unstaged changes
git diff --staged                 # staged changes
```

## Branching
```bash
git branch                        # list local
git branch -a                     # list all
git branch <name>                 # create
git switch <name>                 # switch
git switch -c <name>              # create + switch
git branch -m <old> <new>         # rename
git branch -d <name>              # delete (merged)
git branch -D <name>              # delete (force)
git branch -vv                    # tracking info
```

## Merging & Rebasing
```bash
git merge <branch>                # merge
git merge --no-ff <branch>        # no fast-forward
git merge --squash <branch>       # squash merge
git merge --abort                 # abort merge
git rebase <branch>               # rebase
git rebase -i HEAD~5              # interactive rebase
git rebase --abort                # abort rebase
git rebase --continue             # continue after conflict
```

## Remote
```bash
git remote -v                     # list remotes
git remote add origin <url>       # add remote
git fetch                         # fetch changes
git fetch --prune                 # remove stale branches
git pull                          # fetch + merge
git pull --rebase                 # fetch + rebase
git push                          # push
git push -u origin <branch>       # push + set upstream
git push --force-with-lease       # safe force push
git push origin --delete <branch> # delete remote branch
```

## Stashing
```bash
git stash                         # stash changes
git stash -m "message"            # with message
git stash -u                      # include untracked
git stash list                    # list stashes
git stash show -p stash@{0}       # show diff
git stash pop                     # apply + remove
git stash apply stash@{0}         # apply (keep)
git stash drop stash@{0}          # delete
git stash branch <name>           # branch from stash
```

## History & Inspection
```bash
git log                           # full log
git log --oneline                 # compact
git log --graph --oneline --all   # visual graph
git log -p                        # with diffs
git log --stat                    # change stats
git log --author="Name"           # by author
git log --grep="term"             # search messages
git log -S "code"                 # search content
git show <commit>                 # show commit
git blame <file>                  # line-by-line history
git shortlog -sn                  # commit count per author
```

## Undo & Recovery
```bash
git restore <file>                # discard working changes
git restore --staged <file>       # unstage
git reset --soft HEAD~1           # undo commit, keep staged
git reset --mixed HEAD~1          # undo commit, unstage
git reset --hard HEAD~1           # undo commit, discard all
git revert <commit>               # safe undo (new commit)
git reflog                        # history of HEAD
git bisect start                  # start binary search
git bisect bad                    # mark current bad
git bisect good <commit>          # mark commit good
git bisect reset                  # end bisect
```

## Tags
```bash
git tag                           # list tags
git tag <name>                    # lightweight tag
git tag -a <name> -m "msg"        # annotated tag
git tag -d <name>                 # delete tag
git push origin <tag>             # push tag
git push --tags                   # push all tags
```

## Advanced
```bash
git cherry-pick <commit>          # apply specific commit
git worktree add <path> <branch>  # new worktree
git worktree list                 # list worktrees
git submodule add <url> <path>    # add submodule
git submodule update --init       # init submodules
git grep "pattern"                # search repo
git archive --format=zip HEAD     # export archive
git clean -fd                     # remove untracked
git gc                            # garbage collect
git describe                      # nearest tag + distance
git rev-parse HEAD                # full SHA
```

## Conflict Resolution
```
<<<<<<< HEAD
(your changes)
=======
(their changes)
>>>>>>> branch
```

```bash
# After resolving:
git add <file>
git commit
# Or abort:
git merge --abort
git rebase --abort
```

## Useful Aliases
```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.last "log -1 HEAD"
git config --global alias.unstage "restore --staged"
```

## Environment Variables
```bash
GIT_AUTHOR_NAME="Name"            # override author
GIT_AUTHOR_EMAIL="email"
GIT_COMMITTER_NAME="Name"         # override committer
GIT_COMMITTER_EMAIL="email"
GIT_EDITOR=vim                    # editor for messages
GIT_PAGER=less                    # pager for output
```
