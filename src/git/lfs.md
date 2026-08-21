# Git LFS (Large File Storage)

Git LFS is an open-source Git extension, originally developed by Atlassian, GitHub, and others in 2015. It replaces large files (videos, datasets, compiled binaries) in Git repositories with text pointers, storing the actual content on a separate LFS server. This page covers the architecture, the pointer format, the bandwidth implications, and the production patterns.

## The Problem

Git stores every version of every file in the repository's history. For a 100 MB binary file changed 10 times, the repository grows by 1 GB. Operations (clone, push, pull) become slow.

```text
Standard Git:
  commit 1: file.mp4 (100 MB)
  commit 2: file.mp4 (100 MB)  ← entire new 100 MB stored
  commit 3: file.mp4 (100 MB)  ← another 100 MB
  ...
```

Git's design is for source code (small text files that change line-by-line). For binaries, the storage is wasted.

## Git LFS Architecture

Git LFS replaces large file contents with a small text "pointer" file in Git, storing the actual content on a separate LFS server:

```text
Repository (Git):
  file.mp4 (134 bytes - pointer file)
  Content:
    version https://git-lfs.github.com/spec/v1
    oid sha256:2c26b46b68ffc68ff3986...
    size 100000000

LFS server (separate):
  oid sha256:2c26b46b68ffc68ff3986... → actual 100 MB file content
```

When you clone or checkout:
1. Git fetches the pointer file (134 bytes).
2. Git LFS extension sees the pointer, fetches the actual content from the LFS server.
3. Git shows the actual file in your working tree.

When you commit:
1. `git add file.mp4` adds the file via the LFS filter (configured in `.gitattributes`).
2. The filter stores the actual content on the LFS server, gets an OID.
3. Git commits the pointer file (134 bytes), not the actual 100 MB.

## The .gitattributes File

```text
# .gitattributes
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
```

The patterns declare which files go through LFS. The `filter=lfs` directive tells Git to use the LFS filter for these file types.

## The Pointer Format

```text
version https://git-lfs.github.com/spec/v1
oid sha256:2c26b46b68ffc68ff3986cb48d4bb1a1e7ec1aa9c8c4ee2b3c5d6c5c8c0c5c1
size 100000000
```

- `version`: the LFS spec version.
- `oid`: the SHA-256 of the actual content (content-addressable).
- `size`: the content's size in bytes.

The pointer is small enough (~130 bytes) that Git's delta compression doesn't matter; each pointer is independent.

## The LFS Server

Git LFS communicates with the LFS server via HTTPS (default) or SSH. The protocol:
1. Client: "I want to download oid=2c26..." → Batch API request.
2. Server: returns the download URL (often a presigned S3 URL).
3. Client: downloads from the URL.

The server can be:
- **GitHub LFS**: GitHub-hosted; 1 GB free, $5/month per 50 GB.
- **GitLab LFS**: GitLab-hosted.
- **Self-hosted**: via git-lfs-transfer or a custom server.

## Production Patterns

### Pattern 1: Game Development

Game repositories have large binaries (textures, audio, video). LFS is standard:

```text
# .gitattributes
*.png filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.fbx filter=lfs diff=lfs merge=lfs -text
```

A game repo with 10 GB of binaries becomes a 100 MB Git repo (pointers) + 10 GB LFS storage.

### Pattern 2: ML Models

For ML model repositories with large checkpoint files:

```text
*.bin filter=lfs diff=lfs merge=lfs -text
*.h5 filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
```

The Hugging Face Hub uses a similar LFS-based system for storing model weights.

### Pattern 3: Media Archives

For video/audio archives where the binaries are versioned:
- Each video change is a new LFS object (100 MB).
- The Git repo's history grows slowly (just pointers).
- The LFS server stores all versions of the video.

## Common Pitfalls

1. **Forgetting to configure LFS before adding large files.** If you add a 100 MB file before configuring LFS in `.gitattributes`, the file goes into Git (not LFS). You have to migrate via `git lfs migrate import`.

2. **Forgetting that LFS history accumulates.** Every version of an LFS-tracked file is stored forever (unless pruned). For 10 versions of a 100 MB file, that's 1 GB on the LFS server.

3. **Forgetting that LFS bandwidth is metered.** GitHub's LFS is 1 GB/month free; $5/month per 50 GB. For large teams cloning the repo daily, this can be expensive.

4. **Forgetting that clones without LFS see only pointer files.** A user who doesn't have LFS installed sees the pointer (134 bytes) instead of the actual file. Document LFS setup in your README.

5. **Forgetting that LFS doesn't support partial clone well.** Git's partial clone (`--filter=blob:none`) skips Git objects, not LFS objects. Use `git lfs clone --include` to limit LFS downloads.

6. **Forgetting that LFS over SSH is configured differently than over HTTPS.** Self-hosted servers with SSH access need a special LFS URL; HTTPS is simpler.

## Comparison to Other Large File Solutions

| Solution | Description | Storage | Best for |
|----------|-------------|---------|----------|
| Git LFS | Pointers in Git; content in separate server | External | Git-native workflows |
| Git Annex | Similar to LFS; more flexible | Anywhere (local, cloud) | Decentralized |
| DVC (Data Version Control) | Not Git-integrated; manages data separately | Anywhere | ML/data science |
| Plain Git | Files in Git | Repository | Small files only |

Git LFS is the standard for Git-native workflows with large files. DVC is preferred for ML/data science where the storage is more flexible.

## References

- [Git LFS documentation](https://git-lfs.com/)
- [Git LFS GitHub](https://github.com/git-lfs/git-lfs)
- [Git LFS specification](https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md)
- [GitHub LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)
- [Atlassian: Git LFS tutorial](https://www.atlassian.com/git/tutorials/git-lfs)
- [DVC: alternative for ML](https://dvc.org/)
- [LWN: Git LFS overview (2020)](https://lwn.net/Articles/815575/)
