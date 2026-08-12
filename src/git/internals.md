# Git Internals

Understanding Git's internal data model separates casual users from engineers who can confidently handle any Git situation. Git is fundamentally a **content-addressable filesystem** with a VCS built on top.

## The .git Directory

Every Git repository has a `.git` directory containing all version control data:

```
.git/
├── HEAD              # Points to current branch
├── config            # Repository configuration
├── description       # Used by GitWeb
├── hooks/            # Server/client-side scripts
├── index             # Staging area (binary file)
├── objects/          # All content (blobs, trees, commits, tags)
│   ├── pack/
│   └── info/
├── refs/             # Pointers to commits
│   ├── heads/        # Local branches
│   ├── tags/         # Tags
│   └── remotes/      # Remote tracking branches
├── logs/             # Reflog data
├── packed-refs       # Packed references (for performance)
└── info/
    └── exclude       # Local ignore patterns
```

## Git Objects

Git stores everything as one of four object types, identified by SHA-1 hashes:

### 1. Blob (Binary Large Object)

Stores **file content only** — no filename, no permissions, no directory structure.

```bash
# Manually create a blob
echo "Hello, Git" | git hash-object -w --stdin
# Output: 557db03de997c86a4a028e1ebd3a1ceb225be238

# Inspect a blob
git cat-file -p 557db03
# Output: Hello, Git

git cat-file -t 557db03
# Output: blob
```

**Key insight**: The same content always produces the same hash. Two files with identical content share a single blob object (deduplication).

### 2. Tree

Maps filenames to blobs. Represents a directory snapshot:

```bash
# Inspect a tree object
git cat-file -p HEAD^{tree}
# 100644 blob 8c01d8b...    .gitignore
# 040000 tree 4b825dc...    src
# 100644 blob 557db03...    README.md
```

Tree entry format:
```
<mode> <type> <hash>    <filename>
```

| Mode | Meaning |
|---|---|
| `100644` | Regular file |
| `100755` | Executable file |
| `120000` | Symbolic link |
| `040000` | Subdirectory (tree) |

### 3. Commit

Points to a tree (the snapshot) plus metadata:

```bash
git cat-file -p HEAD
# tree 4b825dc642cb6eb9a060e54bf899d15363dc0e37
# parent 7a1b2c3d4e5f...
# author John Doe <john@example.com> 1692000000 +0000
# committer John Doe <john@example.com> 1692000000 +0000
#
# Initial commit
```

A commit contains:
- **tree**: Root tree hash (the complete snapshot)
- **parent**: Previous commit(s) — merge commits have 2+ parents
- **author**: Who wrote the changes (with timestamp)
- **committer**: Who committed (can differ from author)
- **message**: Commit message

### 4. Tag Object

An annotated tag (lightweight tags are just refs, not objects):

```bash
git cat-file -p v1.0
# object 7a1b2c3d...
# type commit
# tag v1.0
# tagger John Doe <john@example.com>
#
# Release version 1.0
```

## How Objects Connect

```
Commit ──→ Tree ──→ Blob (README.md)
   │        ├──→ Blob (main.py)
   │        └──→ Tree (src/) ──→ Blob (utils.py)
   │
   └──→ Parent Commit ──→ Tree ──→ ...
```

Every commit captures a **complete snapshot** of the entire project (not a diff). Git achieves storage efficiency through:
1. **Packfiles**: Compress similar objects together using delta compression
2. **Deduplication**: Identical content → same hash → stored once

## Refs (References)

Refs are human-readable names pointing to commit hashes:

```bash
# Branches are just files containing a commit hash
cat .git/refs/heads/main
# 7a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b

# HEAD points to the current branch
cat .git/HEAD
# ref: refs/heads/main

# Detached HEAD points directly to a commit
# HEAD: 7a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
```

### Ref Namespace

| Ref | Location | Purpose |
|---|---|---|
| `refs/heads/*` | Local | Local branches |
| `refs/remotes/*` | Local | Remote tracking branches |
| `refs/tags/*` | Local | Tags |
| `refs/stash` | Local | Stash entry |
| `refs/notes/*` | Local | Git notes |

## The Index (Staging Area)

The index is a binary file (`.git/index`) that serves as the staging area:

```
Working Directory  ──git add──→  Index  ──git commit──→  Repository
   (your files)                (staged snapshot)          (permanent)
```

The index stores:
- File paths
- SHA-1 hashes of file content
- File permissions
- Timestamps (for detecting changes)

```bash
# Inspect the index
git ls-files --stage
# 100644 557db03... 0    README.md
# 100644 8c01d8b... 0    main.py
```

**Why the index exists**: It lets you craft commits selectively. You can stage part of a file's changes (`git add -p`), enabling clean, logical commits.

## HEAD

HEAD is a special ref that determines "where you are":

```bash
# Normal state: HEAD points to a branch
cat .git/HEAD
# ref: refs/heads/main

# Detached HEAD: HEAD points directly to a commit
git checkout abc1234
# You are in 'detached HEAD' state
```

When you commit:
- **Attached HEAD**: The branch ref advances to the new commit
- **Detached HEAD**: Only HEAD advances (no branch moves)

## SHA-1 Hashing

Git computes SHA-1 over:

```
blob:   "blob <size>\0<content>"
tree:   "tree <size>\0<entries>"
commit: "commit <size>\0<commit-data>"
```

```bash
# Compute a blob hash manually
echo -n "Hello, Git" | (printf "blob 11\0"; cat) | sha1sum
# 557db03de997c86a4a028e1ebd3a1ceb225be238
```

> **Note**: Git is transitioning to SHA-256 for new repositories.

## Packfiles

Loose objects are stored individually. Over time, Git packs them for efficiency:

```bash
# Manually trigger packing
git gc
```

Packfile format:
1. **Delta compression**: Stores only differences between similar objects
2. **Base objects**: Full content stored once; other objects reference deltas
3. **Pack index** (`.idx`): Enables fast lookup within packfiles

```
objects/
├── pack/
│   ├── pack-abc123.idx    # Index for fast lookup
│   └── pack-abc123.pack   # Packed objects
├── info/
└── 55/7db03...            # Loose object
```

## The Reflog

The reflog records where HEAD and branch tips have pointed:

```bash
git reflog
# 7a1b2c3 HEAD@{0}: commit: Add feature X
# 4d5e6f7 HEAD@{1}: checkout: moving from dev to main
# 8b9c0d1 HEAD@{2}: commit: Fix bug Y

# Reflog for a specific branch
git reflog main
```

Reflog entries expire (default: 90 days for reachable, 30 days for unreachable).

**Safety net**: `git reflog` lets you recover "lost" commits:

```bash
# Oops, accidental hard reset
git reset --hard HEAD~3

# Recover using reflog
git reflog
# Find the commit before the accident
git reset --hard HEAD@{1}
```

## How git add Works

```bash
git add file.txt
```

1. Computes SHA-1 hash of `file.txt` content
2. Stores content as a blob object in `.git/objects/`
3. Updates the index to map `file.txt` → blob hash

## How git commit Works

```bash
git commit -m "message"
```

1. Creates a tree object from the current index
2. Creates a commit object pointing to that tree + parent + metadata
3. Updates the current branch ref to point to the new commit
4. Updates HEAD (if attached to branch)

## How git diff Works

```bash
# Working directory vs Index (unstaged changes)
git diff

# Index vs Last commit (staged changes)
git diff --staged

# Between commits
git diff commit1 commit2
```

Git compares:
1. **Working tree ↔ Index**: Shows unstaged changes
2. **Index ↔ HEAD**: Shows staged changes
3. **Commit ↔ Commit**: Shows differences between snapshots

## How git merge Works (Internals)

```bash
git merge feature
```

1. Finds the merge base (common ancestor)
2. Computes diff: base → current branch
3. Computes diff: base → feature branch
4. Applies both sets of changes
5. If no conflicts: creates a merge commit with 2 parents
6. If conflicts: pauses for manual resolution

```
      C1---C2---C3 (main)
     /         \
A---B            M (merge commit)
     \         /
      F1---F2---F3 (feature)
```

## How git rebase Works (Internals)

```bash
git rebase main
```

1. Finds the common ancestor (merge base)
2. Saves current branch commits as patches
3. Resets current branch to target (main)
4. Replays each patch as a new commit
5. New commits have different hashes (different parent/tree)

```
Before:                    After:
A---B---C---D (main)       A---B---C---D (main)
     \                           \
      E---F---G (feature)        E'---F'---G' (feature)
```

## How git clone Works

```bash
git clone https://github.com/user/repo.git
```

1. Creates directory and initializes `.git`
2. Fetches all objects from the remote
3. Creates remote tracking branches (`refs/remotes/origin/*`)
4. Checks out the default branch (usually `main`)

## Shallow Clones

```bash
git clone --depth 1 https://github.com/user/repo.git
```

- Only fetches the latest commit (no full history)
- Useful for CI/CD and large repositories
- Cannot see full log or push to new branches

## Interview Questions

### Beginner

**Q: What is the difference between `git pull` and `git fetch`?**
A: `fetch` downloads remote changes without modifying your working tree. `pull` = `fetch` + `merge` (or `fetch` + `rebase` with `--rebase`).

**Q: What is a detached HEAD state?**
A: When HEAD points directly to a commit instead of a branch. Commits made in this state will be orphaned unless you create a branch.

### Intermediate

**Q: How does Git store file content? What makes it efficient?**
A: Git stores content as blob objects identified by SHA-1 hashes. Efficiency comes from: (1) deduplication — identical content shares one blob, (2) packfiles with delta compression, (3) zlib compression of loose objects.

**Q: What is the difference between a merge commit and a regular commit?**
A: A merge commit has two (or more) parent commits, representing the convergence of branches. A regular commit has one parent (or zero for the root commit).

**Q: Explain the three-way merge algorithm.**
A: Git finds the merge base (common ancestor), computes the diff from base to each branch tip, and applies both sets of changes. If the same region was modified differently, a conflict occurs.

### Advanced

**Q: How does Git's reflog help with disaster recovery?**
A: The reflog records all HEAD movements. Even after `reset --hard` or `branch -d`, the commits still exist in the object database and can be recovered via `reflog` → `checkout` or `cherry-pick`. Objects are retained for at least 30 days (configurable via `gc.reflogExpire`).

**Q: What happens internally when you `git gc`?**
A: (1) Loose objects are packed into packfiles with delta compression, (2) unreachable objects older than the grace period are pruned, (3) reflog entries are expired, (4) stale temporary files are removed, (5) pack index files are regenerated if needed.

**Q: How does Git handle content-addressable storage at scale?**
A: Git uses a fanout directory structure for objects (first 2 hex chars as directory). Packfiles group related objects with delta compression. The pack index enables O(log n) lookup. For very large repos, Git supports promisor repos and partial clones that fetch objects on demand.

### Common Traps

1. **"Git tracks changes"** — No, Git stores snapshots. It computes diffs on the fly.
2. **"Branches are expensive"** — Branches are just 41-byte files (ref + newline).
3. **"Deleted commits are gone"** — They persist in the object store until garbage collected.
4. **"Rebase rewrites history"** — It creates new commits with new hashes. The old ones still exist until GC'd.
5. **"Merge and rebase do the same thing"** — Merge preserves history topology; rebase linearizes it.

## References

- [Pro Git — Git Internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain)
- [Git Objects Documentation](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [Git Internals PDF by Scott Chacon](https://github.com/pluralsight/git-internals-pdf)
- [Git Source Code: object.c](https://github.com/git/git/blob/master/object.c)
