# How Dropbox Works

## Overview

Dropbox is a cloud storage and file synchronization service with 700+ million registered users and 15+ million paying subscribers. It synchronizes files across multiple devices in near real-time, handling conflict resolution, deduplication, and efficient delta sync. The core challenge is keeping files consistent across devices while minimizing bandwidth and storage.

## Key Requirements

### Functional
- Upload and download files (any type, up to 50 GB)
- Sync files across multiple devices in near real-time
- Share files and folders with other users
- File versioning (recover previous versions)
- Offline access (sync when reconnected)
- Search across files
- Paper (collaborative documents)

### Non-Functional
- **Scale**: 700M+ registered users, 15M+ paying, 500B+ files stored
- **Sync latency**: Changes visible on other devices within seconds
- **Reliability**: Zero data loss (files must never be corrupted or lost)
- **Bandwidth**: Minimize upload/download (delta sync, deduplication)
- **Storage**: Exabytes of data (deduplicated)
- **Availability**: 99.99%

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Desktop[Desktop Client]
        Mobile[Mobile App]
        Web[Web Interface]
    end

    subgraph "Frontend"
        LB[Load Balancer]
        API[API Servers]
    end

    subgraph "Core Services"
        MetadataSvc[Metadata Service]
        BlockSvc[Block Service]
        SyncSvc[Sync Service]
        SharingSvc[Sharing Service]
        SearchSvc[Search Service]
        NotifSvc[Notification Service]
    end

    subgraph "Storage"
        MetaDB[(Metadata DB<br/>MySQL/Sharded)]
        BlockStore[(Block Store<br/>S3/Custom)]
        Memcache[(Memcache)]
    end

    subgraph "Background Workers"
        Dedup[Deduplication Worker]
        Thumbnail[Thumbnail Generator]
        Indexer[Search Indexer]
    end

    Desktop --> LB
    Mobile --> LB
    Web --> LB
    LB --> API
    API --> MetadataSvc
    API --> BlockSvc
    API --> SyncSvc
    API --> SharingSvc
    MetadataSvc --> MetaDB
    MetadataSvc --> Memcache
    BlockSvc --> BlockStore
    SyncSvc --> NotifSvc
    MetaDB --> Indexer
    Indexer --> SearchSvc
```

## Deep Dive: File Sync Architecture

### The Block-Based Storage Model

Dropbox splits files into **4 MB blocks** for efficient storage and sync:

```mermaid
graph LR
    File["MyFile.docx<br/>(12 MB)"] --> Split["Split into blocks"]
    Split --> B1["Block 1<br/>(4 MB, hash: abc123)"]
    Split --> B2["Block 2<br/>(4 MB, hash: def456)"]
    Split --> B3["Block 3<br/>(4 MB, hash: ghi789)"]
    B1 --> Store["Block Store<br/>(S3)"]
    B2 --> Store
    B3 --> Store
    B1 --> Meta["Metadata DB<br/>(file → [block hashes])"]
    B2 --> Meta
    B3 --> Meta
```

**Why blocks?**
- **Deduplication**: If two users upload the same file, blocks are stored once
- **Delta sync**: Only changed blocks are transferred
- **Parallel upload**: Multiple blocks can be uploaded simultaneously
- **Resumable uploads**: If upload fails, only remaining blocks need retry

### Delta Sync (Incremental Sync)

When a file changes, Dropbox only syncs the changed blocks:

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Note over Client: File modified locally
    Client->>Client: Compute block hashes
    Client->>Server: Send hashes [abc123, xyz789, ghi789]
    Server->>Server: Compare with stored hashes
    Server-->>Client: Need block 2 (xyz789 is new)
    Client->>Server: Upload block 2 (4 MB)
    Server-->>Client: Sync complete
    
    Note over Client: Only 4 MB transferred<br/>instead of 12 MB
```

**How delta sync works:**
1. Client detects file change (filesystem watcher)
2. Client computes hash of each 4 MB block
3. Client sends block hashes to server
4. Server compares with stored hashes
5. Server requests only the changed/new blocks
6. Client uploads only those blocks
7. Server updates metadata

### File Watching (Desktop Client)

```mermaid
graph LR
    subgraph "Desktop Client"
        Watcher["Filesystem Watcher<br/>(inotify/FSEvents)"]
        Sync["Sync Engine"]
        LocalCache["Local Cache"]
    end

    Watcher -->|"File changed"| Sync
    Sync -->|"Compute hashes"| LocalCache
    Sync -->|"Upload delta"| Server["Server"]
    Server -->|"Download delta"| Sync
    Sync -->|"Write to disk"| LocalCache
```

**Platform-specific watchers:**
- **Linux**: inotify
- **macOS**: FSEvents
- **Windows**: ReadDirectoryChangesW

## Deep Dive: Metadata Service

The metadata service tracks all file information without storing actual file content.

```mermaid
graph TB
    subgraph "Metadata"
        User["User"] --> Folder["Folder"]
        Folder --> File1["File 1<br/>(hashes, size, mtime)"]
        Folder --> File2["File 2<br/>(hashes, size, mtime)"]
        Folder --> Subfolder["Subfolder/"]
    end
```

**Metadata per file:**
```json
{
    "file_id": "uuid",
    "path": "/Documents/report.pdf",
    "size": 12582912,
    "blocks": ["abc123", "def456", "ghi789"],
    "mtime": "2024-01-15T10:30:00Z",
    "version": 5,
    "creator": "user_123",
    "shared_with": ["user_456", "user_789"]
}
```

**Sharding strategy:**
- Metadata DB is sharded by `user_id`
- Each user's files are on the same shard (enables efficient folder listings)
- MySQL with read replicas for each shard

## Deep Dive: Deduplication

Dropbox deduplicates at the block level:

```mermaid
graph TB
    User1["User A uploads report.pdf"] --> Hash["Compute block hashes"]
    User2["User B uploads report.pdf"] --> Hash
    Hash --> Check{"Block exists?"}
    Check -->|Yes| Skip["Skip upload<br/>(reference only)"]
    Check -->|No| Store["Store block"]
    Skip --> Meta["Update metadata"]
    Store --> Meta
```

**Deduplication stats:**
- Dropbox reported that deduplication saved ~90% of upload bandwidth
- Content-addressable storage: blocks are identified by their SHA-256 hash
- Two users uploading the same file → blocks stored once, metadata stored per user

## Deep Dive: Conflict Resolution

When the same file is edited on two devices simultaneously:

```mermaid
sequenceDiagram
    participant Device1
    participant Server
    participant Device2

    Device1->>Server: Upload: report.pdf (v5)
    Note over Device2: Also editing report.pdf
    Device2->>Server: Upload: report.pdf (v5)
    Server->>Server: Conflict detected!<br/>(same version, different content)
    Server-->>Device1: Sync: report.pdf (v5)
    Server-->>Device2: Sync: report (conflicting copy).pdf
    Note over Server: Creates conflict copy,<br/>notifies both users
```

**Conflict resolution strategy:**
1. **Last-writer-wins** for non-conflicting changes
2. **Conflict copies** when same file edited simultaneously on different devices
3. User is notified and can manually merge
4. Dropbox Paper uses **CRDTs** for real-time collaboration (no conflicts)

## Deep Dive: Sharing

```mermaid
graph TB
    Owner["File Owner"] --> ShareLink["Create Share Link"]
    ShareLink --> LinkDB["Link DB<br/>(token → file)"]
    
    Recipient["Recipient"] --> Access["Access via link"]
    Access --> LinkDB
    LinkDB --> File["File Content"]
    
    Owner --> ShareFolder["Share Folder"]
    ShareFolder --> Perms["Permission DB"]
    Perms --> Recipient2["Shared User"]
    Recipient2 --> Sync["Sync to their Dropbox"]
```

**Sharing types:**
- **Share link**: Anyone with the link can view/download
- **Shared folder**: Both users see the folder in their Dropbox (synced)
- **Paper collaboration**: Real-time collaborative editing

## Scalability

| Component | Strategy |
|-----------|---------|
| File storage | Block-based, deduplicated, S3 + custom block store |
| Metadata | MySQL sharded by user_id |
| Sync | Delta sync (only changed blocks) |
| Caching | Memcache for hot metadata |
| Search | Elasticsearch index |
| Notifications | WebSocket for real-time sync notifications |
| CDN | For shared link downloads |

## Trade-Offs

| Decision | Benefit | Cost |
|----------|---------|------|
| 4 MB blocks | Good dedup + delta sync | Overhead for small files |
| Block-level dedup | ~90% bandwidth savings | Hash computation overhead |
| Conflict copies | Never loses data | User must manually resolve |
| Filesystem watcher | Real-time sync | Platform-specific, can miss events |
| MySQL sharding | Strong consistency | Migration complexity |
| S3 for blocks | Durable, scalable | Higher cost than custom storage |

## Interview Tips

1. **Start with the sync problem** — "The core challenge is keeping files consistent across devices with minimal bandwidth"
2. **Explain block-based storage** — 4 MB blocks enable dedup and delta sync
3. **Discuss delta sync** — only changed blocks are transferred (hash comparison)
4. **Mention deduplication** — ~90% bandwidth savings, content-addressable storage
5. **Talk about conflict resolution** — conflict copies, not silent overwrites
6. **Don't forget metadata vs content separation** — metadata in MySQL, blocks in S3
7. **Mention filesystem watchers** — inotify/FSEvents for real-time change detection

## Key Takeaways

- Dropbox splits files into 4 MB blocks for efficient deduplication and delta sync.
- Delta sync: client sends block hashes, server requests only changed blocks (~90% bandwidth savings).
- Content-addressable storage: blocks identified by SHA-256 hash, enabling global deduplication.
- Metadata (file paths, block lists) stored in MySQL sharded by user_id; blocks stored in S3.
- Conflict resolution: create conflict copies rather than silently overwriting.
- Filesystem watchers (inotify/FSEvents) enable real-time change detection on desktop.
- Dropbox Paper uses CRDTs for real-time collaboration without conflicts.

## Cross-References

- [Distributed File System](../dfs.md)
- [Object Storage](../../../storage/object-storage.md)
- [Consistency Patterns](../consistency-patterns.md)
- [Key-Value Store](../kv-store.md)

