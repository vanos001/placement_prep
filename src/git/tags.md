# Tags & Releases

## Lightweight Tags

A simple pointer to a commit (no metadata):

```bash
git tag v1.0                      # tag current commit
git tag v1.0 abc1234              # tag specific commit
git tag -l "v1.*"                 # list matching tags
git tag -d v1.0                   # delete tag
```

## Annotated Tags

Full Git objects with metadata (recommended for releases):

```bash
git tag -a v1.0 -m "Release version 1.0"
git tag -a v1.0 abc1234 -m "Release version 1.0"

# Sign with GPG
git tag -s v1.0 -m "Signed release"
git tag -v v1.0                   # verify signature
```

Annotated tag object contains:
- Tag name
- Tagger (name, email, timestamp)
- Message
- Optional GPG signature
- Pointer to a commit

## Semantic Versioning

```
MAJOR.MINOR.PATCH

v1.2.3
│ │ └── Patch: bug fixes (backward compatible)
│ └──── Minor: new features (backward compatible)
└────── Major: breaking changes
```

Pre-release and build metadata:
```
v1.0.0-alpha.1
v1.0.0-beta.2
v1.0.0-rc.1
v1.0.0+build.123
```

## Pushing Tags

```bash
git push origin v1.0              # push specific tag
git push origin --tags             # push all tags
git push origin --delete v1.0     # delete remote tag
```

## Tags and Releases on GitHub

```bash
# Create a tag and push
git tag -a v1.0.0 -m "First stable release"
git push origin v1.0.0

# Then create a GitHub Release from the tag
# (via GitHub UI or gh CLI)
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes here"
```

## Listing and Filtering Tags

```bash
git tag                           # list all tags
git tag -l "v2.*"                 # pattern match
git tag --sort=-creatordate       # sort by date
git tag --merged main             # tags reachable from main
git log --oneline --decorate      # show tags in log
```

## Interview Questions

**Q: What is the difference between a lightweight and annotated tag?**
A: A lightweight tag is just a pointer to a commit (a file containing a hash). Annotated tag is a full Git object with tagger info, message, and optional GPG signature. Always use annotated tags for releases.

**Q: How do you move a tag to a different commit?**
A: Delete and recreate: `git tag -d v1.0 && git tag v1.0 <new-commit>`. If already pushed: `git push origin :refs/tags/v1.0 && git push origin v1.0`.

## References

- [Pro Git — Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [Semantic Versioning](https://semver.org/)
