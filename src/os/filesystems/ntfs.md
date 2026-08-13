# NTFS (New Technology File System)

## Overview

**NTFS** is the primary filesystem for Windows NT and later (Windows 2000, XP, Vista, 7, 8, 10, 11, and Windows Server). It replaced FAT as the Windows default, adding journaling, security (ACLs), compression, encryption, and large volume/file support.

## Key Features

| Feature | Description |
|---------|-------------|
| **Journaling** | $LogFile for crash recovery |
| **ACLs** | Per-file access control lists (not just POSIX rwx) |
| **Compression** | Per-file transparent compression |
| **EFS** | Encrypting File System (per-file encryption) |
| **Sparse files** | Only allocate blocks for non-zero data |
| **Hard/symbolic links** | Supported (since NTFS 3.1) |
| **Alternate Data Streams** | Multiple data streams per file |
| **Max volume** | 256 TB (with 64 KB clusters) |
| **Max file** | 16 EB (theoretical), 256 TB (practical) |

## On-Disk Layout

```
┌──────────┬──────────────┬──────────────────────────────────┐
│  Boot    │  Master File │         Data Area                │
│  Sector  │  Table (MFT) │                                  │
│  (MBR)   │              │                                  │
└──────────┴──────────────┴──────────────────────────────────┘
```

### Key Structures

| Structure | Description |
|-----------|-------------|
| **Boot Sector** | BIOS parameter block, cluster size, MFT location |
| **$MFT** | Master File Table — array of file records |
| **$MFTMirr** | Backup of first 4 MFT entries |
| **$LogFile** | Journal for crash recovery |
| **$Volume** | Volume name, version, flags |
| **$AttrDef** | Attribute type definitions |
| **$Bitmap** | Cluster allocation bitmap |
| **$BadClus** | Bad cluster list |
| **$Root** | Root directory |

## Master File Table (MFT)

The MFT is the heart of NTFS — an array of **file records**, each 1024 bytes by default.

```
MFT:
┌────────────────────┬────────────────────┬────────────────┬─────────────┐
│ Entry 0: $MFT      │ Entry 1: $MFTMirr  │ Entry 2: $Log  │ Entry 3: ...│
│ Entry 4: $AttrDef  │ Entry 5: $Root     │ Entry 6: $Bitmap│ ...        │
│ Entry 15: $ObjId   │ Entry 16: file1.txt │ Entry 17: dir1 │ ...        │
└────────────────────┴────────────────────┴────────────────┴─────────────┘
```

Every file (including NTFS metadata files) has an MFT entry.

### File Record Structure

```
┌─────────────────────────────────────────────────────────┐
│ File Record Header (48 bytes)                           │
│   Magic: "FILE" | Update seq | Log seq number           │
│   Sequence number | Hard link count | First attr offset  │
│   Flags (in use, directory) | Used size | Alloc size     │
├─────────────────────────────────────────────────────────┤
│ $STANDARD_INFORMATION (16+ bytes)                       │
│   Creation time, modification time, access time         │
│   DOS permissions, owner SID, security ID               │
├─────────────────────────────────────────────────────────┤
│ $FILE_NAME (68+ bytes)                                  │
│   Parent directory ref | Filename (Unicode)             │
│   Namespace (POSIX, Win32, DOS)                         │
├─────────────────────────────────────────────────────────┤
│ $DATA                                                   │
│   For small files: data inline (< ~700 bytes)           │
│   For large files: runs (extents) pointing to clusters  │
├─────────────────────────────────────────────────────────┤
│ $INDEX_ROOT, $INDEX_ALLOC, $BITMAP (for directories)    │
└─────────────────────────────────────────────────────────┘
```

## NTFS Attributes

Every piece of information about a file is stored as an **attribute**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `$STANDARD_INFORMATION` | Resident | Timestamps, permissions, flags |
| `$FILE_NAME` | Resident | Filename(s), parent directory |
| `$DATA` | Resident/Non-resident | File content |
| `$INDEX_ROOT` | Resident | Small directory index (B-tree root) |
| `$INDEX_ALLOCATION` | Non-resident | Large directory index (B-tree leaves) |
| `$BITMAP` | Resident | Directory or index tracking |
| `$SECURITY_DESCRIPTOR` | Resident/Non-resident | ACLs |
| `$OBJECT_ID` | Resident | Unique file identifier |
| `$REPARSE_POINT` | Resident | Symlinks, mount points |

### Resident vs. Non-resident Attributes

```
Resident (small data, fits in MFT entry):
┌──────────────────────────┐
│ Attribute Header          │
│ Data: "Hello World"       │  ← stored directly in MFT
└──────────────────────────┘

Non-resident (large data, stored in clusters):
┌──────────────────────────┐
│ Attribute Header          │
│ Data Runs: [(start=100, len=5), (start=200, len=3)]  │  ← pointers to clusters
└──────────────────────────┘
```

## Data Runs (Extents)

Non-resident attributes use **data runs** to map logical clusters to physical clusters:

```
Data Run encoding:
  [length_size][offset_size][length][offset]

Example:
  Run 1: length=5, offset=100  → clusters 100-104
  Run 2: length=3, offset=+50  → clusters 150-152 (relative to previous)
  Run 3: length=10, offset=-20 → clusters 130-139
```

This is NTFS's extent-based allocation, similar to ext4's extent tree.

## B-Tree Directories

NTFS directories use a B-tree indexed by filename:

```
$INDEX_ROOT (small directory):
┌─────────────────────────────────┐
│  Header: type, collation rule   │
│  B-tree entries:                │
│    "file1.txt" → MFT entry 16  │
│    "file2.txt" → MFT entry 17  │
│    "subdir" → MFT entry 18     │
└─────────────────────────────────┘

$INDEX_ALLOCATION (large directory):
  Overflow B-tree nodes for directories with many entries
```

**Advantage over linear directories** (like ext2): O(log n) lookup for large directories.

## NTFS Permissions (ACLs)

Unlike POSIX's 9-bit permissions, NTFS uses full **Access Control Lists**:

```
Security Descriptor:
  Owner: S-1-5-21-...-1001 (alice)
  Group: S-1-5-21-...-513  (Domain Users)
  DACL:
    ACE 1: S-1-5-21-...-1001 → Full Control
    ACE 2: S-1-5-21-...-513  → Read & Execute
    ACE 3: S-1-5-32-545      → Read & Execute (Users)
    ACE 4: S-1-1-0            → Read (Everyone)
```

Each ACE (Access Control Entry) specifies:
- **SID** (Security Identifier) — who
- **Access mask** — what permissions (read, write, execute, delete, etc.)
- **Type** — Allow or Deny

## EFS (Encrypting File System)

```powershell
# Encrypt a file
cipher /e secret.txt

# View encrypted files
cipher /c secret.txt
```

- Uses symmetric encryption (AES-128/256) per file
- File encryption key (FEK) encrypted with user's public key
- Recovery agent can decrypt with their key

## Alternate Data Streams (ADS)

NTFS allows multiple named data streams per file:

```powershell
# Write to alternate stream
echo "hidden data" > file.txt:secret

# Read from alternate stream
more < file.txt:secret

# List streams
dir /r file.txt
```

**Used by**: Windows for metadata (e.g., Zone.Identifier for downloaded files).

**Security concern**: Malware can hide data in ADS.

## Useful Commands

```powershell
# Check filesystem
chkdsk C: /f /r

# View NTFS info
fsutil fsinfo ntfsinfo C:

# Defragment
defrag C: /O

# Change permissions
icacls file.txt /grant alice:(R,W)

# Mount volume
mountvol D: \\?\Volume{guid}\
```

## Interview Questions

**Q1: What is the MFT and why is it important?**

The Master File Table (MFT) is NTFS's core metadata structure — an array of 1024-byte file records. Every file and directory has an entry. The MFT stores attributes like filenames, timestamps, permissions, and data extents. For small files, data is stored directly in the MFT entry (resident attribute). The MFT is essentially NTFS's equivalent of an inode table.

**Q2: How does NTFS store file data?**

Small files (< ~700 bytes) store data as a resident `$DATA` attribute within the MFT entry. Larger files use non-resident `$DATA` attributes with data runs — sequences of (start cluster, length) pairs that map logical clusters to physical clusters, similar to extents in ext4.

**Q3: What is the difference between NTFS permissions and POSIX permissions?**

POSIX uses a simple 9-bit model (rwx for owner/group/others). NTFS uses Access Control Lists (ACLs) with individual Access Control Entries (ACEs) that can allow or deny specific permissions to specific users or groups. NTFS also supports inheritance (permissions flow from parent directories) and auditing.

**Q4: What are Alternate Data Streams and what are the security implications?**

ADS allow multiple named data streams per file. The default stream is `$DATA`; you can add others like `file.txt:hidden`. ADS can be used to hide malware or data from basic file listing tools. Windows Defender and modern tools scan ADS, but many users aren't aware they exist.

**Q5: How does NTFS journaling work?**

NTFS uses the `$LogFile` to record all metadata changes before they're committed. On crash recovery, NTFS replays committed transactions and rolls back uncommitted ones. This ensures metadata consistency but doesn't guarantee data consistency (similar to ext4's `data=ordered` vs `data=journal` modes).

## Common Mistakes

- Confusing NTFS permissions with share permissions — they're different and both apply
- Not realizing that NTFS compression has a performance cost and doesn't compress well for already-compressed data
- Thinking `chkdsk` fixes data corruption — it fixes metadata/structure issues, not file content
- Forgetting that NTFS has a 256 TB volume limit (with 64 KB clusters) and 16 EB file limit (theoretical)

## Summary

- NTFS is the Windows filesystem with journaling, ACLs, compression, and encryption
- MFT (Master File Table) stores all metadata as attributes in file records
- Data runs provide extent-based allocation similar to ext4
- B-tree directories for efficient large directory lookups
- Full ACLs with deny entries and inheritance
- Alternate Data Streams provide multiple data channels per file
- Journaling via `$LogFile` ensures metadata consistency

## Cross-References

- [ext4](ext4.md) — Linux equivalent
- [Disk Allocation](disk-allocation.md) — extent-based allocation
- [Journaling](journaling.md) — crash consistency
- [Access Control](../security/access-control.md) — ACLs in depth
- [VFS](vfs.md) — NTFS in the Linux kernel via ntfs3 driver


## Cross References

- [Journaling](journaling.md)
- [VFS](vfs.md)
- [Disk Allocation](disk-allocation.md)
