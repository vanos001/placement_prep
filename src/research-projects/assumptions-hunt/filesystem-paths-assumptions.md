# Filesystem Path Assumptions: What "Just Open the File" Silently Promises

## Overview

Every program that touches a file first has to name it, and the naming step runs on assumptions that feel too basic to check: that a path is a path on every operating system, that a file's name is just a string, that paths fit in whatever buffer or column holds them, and that the name checked a millisecond ago is the name being opened now. Each assumption breaks differently — a join with user input escapes its directory, a name that is legal on Linux is reserved on Windows, a deep dependency tree overruns a 260-character limit, and a world-writable directory turns a check-then-open sequence into an attacker-controlled write.

The deeper pattern is that *a path is not a string; it is a request for the operating system to perform a resolution*, and the resolution rules — separators, case folding, reserved names, component limits, symlink following, mount boundaries — belong to the filesystem, not to the programmer. Two sibling chapters cover the file's lifecycle from other angles: [temp files and atomicity](temp-files-and-atomicity.md) audits write-then-rename schemes, and [filesystem durability](filesystem-durability.md) audits flush and crash semantics. This chapter audits the name itself, in the collection's five-step pattern: the taught rule, the hidden assumptions, a concrete failure, the corrected contract, and the consequences for code review and interviews.

## Assumption 1: "A Path Is a Path"

### The taught rule

Paths are portable: `/var/log/app.log` on Unix and `C:\var\log\app.log` on Windows differ only in the separator character, so code can be written once with a little string handling and work everywhere.

### The hidden assumptions

- It assumes the *separator is universal*. On POSIX only `/` separates components, and `\` is a legal character *inside* a file name; on Windows the Win32 layer accepts both in most APIs, but command shells, batch files, and some libraries split or join on `\` only — so a name containing a backslash that round-trips through a Windows tool arrives on Unix as a different name with an embedded separator.
- It assumes *absolute and relative are properties of the string*. Relative resolution depends on the process's current working directory, which is process-global mutable state: a library that calls `chdir` (or an accidental `os.chdir` in a config loader) re-points every relative path in the process, including ones already passed to other threads.
- It assumes *the trailing slash is decoration*. POSIX gives it meaning: `open("link/")` demands that `link` resolve to a directory, and tools that strip trailing slashes silently change the request — the classic source of "rm -rf $DIR/" behaving differently from `rm -rf $DIR`.
- It assumes *one namespace*: the same path string can resolve differently across mounts, bind mounts, containers, and user namespaces — a path valid inside the container is meaningless on the host, which is why volume mounting is where "it's just a path" fails in deployment as often as in code.

### Counterexample

A data pipeline stores per-day outputs under `base/2024-05-01/` and cleans them with a shell command built as `rm -rf "$BASE/$day/"`. An operator re-runs the cleanup for a day whose variable was set to an empty string in a retry path; the command becomes `rm -rf "$BASE/"` and deletes every output rather than one day's. The separator-and-suffix mechanics made the empty value invisible: the path still looked well-formed, and the request changed meaning at the boundary of a single character. The corrected contract: treat path building as construction with validated components (reject empty and path-separator characters in each component), prefer libraries that join and normalize rather than string concatenation, and pass absolute paths from configuration instead of relying on ambient working directory.

### What changes when the assumption is removed

Corrected statement: *a path is an OS-resolution request whose meaning depends on separators, working directory, trailing separators, and mounts; code that constructs paths must validate components, join through a library, and pin the working directory — because the same string can be three different requests on three systems.* The audit question is not "is the string right?" but "what will resolution do with this string on the target system?"

### Consequences

In interviews, "why is relative-path configuration fragile?" unfolds into the cwd-is-global answer and the container/mount namespace answer. In code review, string concatenation with `/` and unvalidated components is a finding by itself, independent of whether a traversal is reachable today.

## Assumption 2: "Names Are Just Names"

### The taught rule

A file name is an opaque string; if it is valid on one system it is valid on another, and `report.pdf` names the same file everywhere.

### The hidden assumptions

- *Case handling differs per filesystem.* macOS volumes are case-insensitive by default (APFS and HFS+), Linux ext4 is case-sensitive, and NTFS preserves case but compares case-insensitively. Names that differ only in case are distinct files on one system and the same file on another — so archives and clones can collide or split depending on the target.
- *Some names are reserved.* Windows reserves device names — `CON`, `PRN`, `AUX`, `NUL`, `COM1` through `COM9`, `LPT1` through `LPT9` — even with extensions, so `CON.txt` and `aux.c` are not ordinary files, and extraction or sync tooling that creates them fails or misbehaves; the platform's [naming documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file) also strips trailing dots and spaces from names.
- *Encoding is not normalization.* macOS historically stored HFS+ names normalization-decomposed, and Unicode has two visually identical spellings for `é` (one code point versus `e` plus a combining mark): two names that look identical are distinct names on a case-sensitive, normalization-preserving filesystem, and round-tripping archives through such systems has produced duplicate entries and lost updates.
- *Legal does not mean safe:* a name is data that later becomes code or command context — leading `-` becomes a flag to `rm`, `;` and `$( )` break unquoted shell expansion, and glob characters expand — so "just a name" assumes no downstream interpreter ever sees it.

### Counterexample

A sync tool extracts an archive uploaded from Linux onto a Windows server. The archive contains `aux.c` and `invoice..pdf ` (trailing space); the first is rejected as a reserved device name and the second is silently stored as `invoice..pdf` with the space stripped, so the sync record's checksum no longer matches the stored file and the next sync re-downloads it forever. Each failure came from a different hidden rule — reserved names, trailing-space stripping — and none produced an error that mentioned either. The corrected contract: sanitize names at ingestion (reject reserved device names and trailing dots/spaces for Windows targets, reject separators and control characters everywhere), and store files by generated identifiers rather than user-controlled names.

### What changes when the assumption is removed

Corrected statement: *a file name is interpreted by the filesystem, the shell, and every tool in between; validity is a per-target predicate covering case, reserved names, encoding, and downstream interpreters, and cross-platform storage must either normalize names to the intersection of target rules or address files by generated ids.* The cheap defense is a name validator at every trust boundary — the same reflex as validating any other user input, since a path is input with OS semantics attached.

### Consequences

The interview probe "what can go wrong writing a user-supplied filename to disk?" expects the list above, and the strongest answers end with "and the same string is a shell argument later" — the recognition that a name's audience is every interpreter on the way to the platter.

## Assumption 3: "Paths Fit and Are Safe to Join"

### The taught rule

Paths are strings; strings can be arbitrarily long; joining a directory with a filename (`base + "/" + name`) is arithmetic on text and cannot fail for interesting reasons.

### The hidden assumptions

- *Length limits are real and layered.* Windows' classic `MAX_PATH` is 260 characters total unless the `\\?\` prefix and long-path opt-in are used, while Linux allows roughly 4,096 bytes per path but caps each component at 255; deep dependency trees — a chain of 30 packages averaging 40 characters per directory level reaches 1,200 characters before any file — blow past 260 on Windows checkouts while passing on developer Macs and Linux.
- *Joining is resolution, not concatenation.* A component containing `..` or an absolute path overrides the base: `join(base, "../../etc/shadow")` escapes the base entirely. Path traversal is this assumption weaponized, and it does not require an attacker to be clever — only a code path that treats an untrusted string as a component.
- *Archives carry paths too.* The [Zip Slip class](https://github.com/snyk/zip-slip-vulnerability) (documented by Snyk in 2018 across many extraction libraries) shows archives whose entries contain `../` sequences; a naive extractor writes outside the target directory with the process's own permissions.
- *Symlinks join after the fact.* Path resolution follows symbolic links by default (the [path-resolution manual](https://man7.org/linux/man-pages/man7/path_resolution.7.html) specifies the semantics), so a symlink planted in a world-writable directory redirects a later write; defenses exist at the open level — `O_NOFOLLOW`, `O_EXCL` creation semantics per the [open(2) manual](https://man7.org/linux/man-pages/man2/open.2.html), and modern `openat2` resolve flags — but only for code that opts in.

### Counterexample

A report service saves uploads to `/srv/reports/<tenant>/<name>`, building the path with join. A tenant uploads `name = ../../../etc/cron.d/collector`; the join produces `/srv/reports/acme/../../../etc/cron.d/collector`, which resolution normalizes to `/etc/cron.d/collector`, and the service — running as root in its container — writes a scheduled job. The review that found it looked for SQL injection and template injection; the path was "just" a string. The corrected contract: after joining, verify the resolved path is still beneath the intended base (lexical check plus, better, an OS-level resolve flag), reject traversal components at ingestion, and extract archives with a library that validates entry names — the published Zip Slip guidance in one sentence.

### What changes when the assumption is removed

Corrected statement: *path length is a per-target budget (260 total on classic Windows, 255 per component on Linux), and path joining is resolution that must be confined — post-join containment checks and extraction-time validation are as mandatory as escaping in any other injection class.* Treat "path traversal" not as a filesystem curiosity but as the injection family it belongs to, with the same review reflex.

### Consequences

In security interviews, "how would you sandbox an extraction routine?" is answered with the containment checks and resolve flags above rather than with "validate the zip", and the [input-constraints](input-constraints.md) chapter's boundary discipline applies verbatim to path components: bounds, characters, and canonical form, checked before resolution, not after.

## Assumption 4: "What I Check Is What I Open"

### The taught rule

Check then act: `if file exists, open it` (or "if the path is a regular file, process it") is a sound pattern, because existence and type are stable properties of a file.

### The hidden assumptions

- *Existence is not an attribute; it is a moment.* Between the check and the open, another actor — another thread, another process, an attacker with write access to the directory — can replace, delete, or re-link the name. The check-then-act gap is the filesystem instance of the race the sibling [concurrency and scheduling](concurrency-and-scheduling.md) chapter audits, with the directory serving as shared mutable state.
- *`exists()` answers a different question than `open()` asks.* `stat`-based existence follows symlinks, so a dangling link reports "not exists" while `lstat` shows a live name and `rm` will happily remove it; conversely a file can exist but be unopenable — a directory, or a parent without execute permission.
- *Error codes conflate.* A missing intermediate component, a missing leaf, a permission failure on a parent, and a symlink loop all surface as variations of "open failed", and application layers frequently flatten them into one 404 — turning a permissions bug into a debugging session about data that "is definitely there".
- *Validity is namespace-local.* A path checked inside a container, a chroot, a mount namespace, or a different mount table names a different object — the check and the open must run in the same namespace, or the check is about a file that was never opened.

### Counterexample

A batch processor polls a shared spool directory: `if os.path.exists(job): with open(job) as f: process(f)`. Two workers run it concurrently against the same job, and a cleaner process rotates files in between: worker A passes `exists`, the cleaner replaces the file with a symlink to the archive, worker A opens the symlink target (a gigabyte archive, parsed as a job), while worker B's open returns `FileNotFoundError` for a name that passed its own check 2 milliseconds earlier. Both workers ran "sound" code; the directory was the shared variable nobody modeled. The corrected contract: open first with creation/exclusion semantics (`O_EXCL` to claim, `O_NOFOLLOW` to refuse links), operate on the *file descriptor* rather than the name, and let the open's error — not a prior check — decide control flow.

### What changes when the assumption is removed

Corrected statement: *existence, type, and permissions are properties of a resolved-at-a-moment name; the only stable handle is the descriptor returned by an open that itself enforces the preconditions (`O_EXCL`, `O_NOFOLLOW`), and error handling must distinguish the failure modes instead of flattening them.* Code that needs check-then-act semantics across actors needs the check inside the same atomic operation — or a lock, with all the caveats the [distributed-lock assumptions](distributed-lock-assumptions.md) chapter documents.

### Consequences

The interview question "why is `exists()` before `open()` a bug?" has a layered answer — race, symlink semantics, conflated errors, namespaces — and each layer maps to a defense. The general lesson matches the collection's method: the check was correct about the world at time t, and the program runs at time t plus delta.

## Interview Questions

1. **Why is building paths by string concatenation a defect even without an attacker?** Separators, working-directory dependence, trailing-slash semantics, and component validation are resolution concerns, not text concerns; concatenation silently mixes them. Use library joins with validated components, and ask what resolution will do with the result on the target OS.
2. **A filename works on Linux and fails to create on Windows. Give three distinct causes.** Reserved device names (`CON.txt`, `aux.c`), trailing dots or spaces stripped by Win32 rules, and length — a 260-character classic `MAX_PATH` limit versus Linux's 4,096-byte paths with 255-byte components. Case collisions are a fourth when the same tree round-trips.
3. **How does Zip Slip work, and what is the structural fix?** Archive entries carry `../` components, so a naive join-and-extract writes outside the destination with the process's permissions. Fix: validate or canonicalize every entry path against the destination and use extraction libraries that enforce containment — plus post-join containment checks in hand-rolled paths.
4. **Replace `if exists(p): open(p)` with something safe, and say why.** Open with `O_NOFOLLOW` (and `O_EXCL` when claiming), operate on the descriptor, and branch on the open's specific errors. Reasons: the check-then-act race, symlink-following semantics of `stat`, and conflated error codes that hide permission problems behind "not found".

## Key Takeaways

- A path is a resolution request with OS-defined semantics — separators, case, reserved names, limits, symlink following — not a string the program controls end to end.
- Name validity is per-target: case sensitivity, Windows reserved names and trailing-dot/space rules, and Unicode normalization all differ, so cross-platform storage should prefer generated identifiers.
- Path length is a budget (260 total on classic Windows; 255 per component on Linux), and deep dependency trees hit budgets that single files never do.
- Joining is resolution: traversal (`..`), absolute components, and symlink redirection all override the intended base, so containment must be checked after resolution or enforced by the open itself.
- Existence checks are momentary and racy; the descriptor obtained by an enforcing open is the only stable handle, and error codes must be distinguished rather than flattened into one "not found".

## Cross-References

- [Temp files and atomicity](temp-files-and-atomicity.md) — the write-then-rename lifecycle of the same files, from the atomicity angle this chapter deliberately excludes.
- [Filesystem durability](filesystem-durability.md) — flush and crash semantics: what survives once the path resolved and the write returned.
- [Input constraints](input-constraints.md) — the boundary-audit method (bounds, characters, canonical form) applied to path components as input.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — check-then-act races in general; the spool-directory failure above is the filesystem instance.
- [Distributed lock assumptions](distributed-lock-assumptions.md) — locks as the (caveated) alternative when check-then-act spans actors.
- [OS book: virtual file systems](../../os/filesystems/vfs.md) — the resolution machinery (vfs layer) that gives paths their operating-system semantics.
- The [Windows naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file), the [path_resolution(7)](https://man7.org/linux/man-pages/man7/path_resolution.7.html) and [open(2)](https://man7.org/linux/man-pages/man2/open.2.html) manuals, and Snyk's [Zip Slip research](https://github.com/snyk/zip-slip-vulnerability) are the primary sources for the semantics and limits above; all were fetched and verified this session.
