# Git — Complete Reference for Placement Preparation

Git is the de facto version control system in software engineering. Understanding Git deeply — from its internal data model to advanced workflows — is essential for technical interviews and real-world engineering.

## Why Git Matters

- Every software company uses version control
- Git knowledge is tested in interviews (directly and indirectly)
- Understanding Git internals demonstrates systems thinking
- Branching strategies affect team productivity and deployment safety
- Git is a content-addressable filesystem — understanding it teaches fundamental CS concepts

## Chapter Outline

| Topic | Description |
|---|---|
| [Git Internals](./internals.md) | Objects, refs, HEAD, index, packfiles |
| [Git Fundamentals](./fundamentals.md) | init, clone, add, commit, status, log, diff |
| [Branching & Merging](./branching.md) | branches, merge, fast-forward, merge conflicts |
| [Rebasing](./rebasing.md) | rebase, interactive rebase, rebase vs merge |
| [Stashing](./stashing.md) | stash, stash pop, stash apply, stash branch |
| [Advanced Operations](./advanced.md) | cherry-pick, revert, reset, reflog, bisect |
| [Remote Operations](./remotes.md) | fetch, pull, push, remote tracking, upstream |
| [Tags & Releases](./tags.md) | lightweight tags, annotated tags, semver |
| [Git Hooks](./hooks.md) | pre-commit, pre-push, commit-msg, server-side |
| [Worktrees & Submodules](./worktrees-submodules.md) | worktree management, submodule workflows |
| [Git Workflows](./workflows.md) | trunk-based, GitFlow, GitHub Flow, release strategies |
| [GitHub & Code Review](./github.md) | PRs, code review, branch protection, Actions |
| [Git Interview Questions](./interview-questions.md) | common questions, traps, scenarios |
| [Git Cheat Sheet](./cheat-sheet.md) | quick reference for all commands |

## Git Architecture at a Glance

```
Working Directory  →  Staging Area (Index)  →  Repository (.git)  →  Remote
    (files)            (git add)                (git commit)         (git push)
```

## Key Concepts

| Concept | Description |
|---|---|
| **Blob** | Stores file content (not filename) |
| **Tree** | Maps filenames to blobs (like a directory) |
| **Commit** | Points to a tree + metadata (author, message, parent) |
| **Ref** | A pointer to a commit (branch, tag, HEAD) |
| **Index** | Staging area between working tree and repository |
| **HEAD** | Special ref pointing to the current branch/commit |

## References

- [Pro Git Book](https://git-scm.com/book/en/v2) — Official Git documentation
- [Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain) — Deep dive
- [Git Man Pages](https://git-scm.com/docs) — Official reference
- [Git Source Code](https://github.com/git/git) — The ultimate reference
