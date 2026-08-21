# S3 Object Storage Internals

Amazon S3 (Simple Storage Service) is the original cloud object storage system, launched in 2006. It set the API standard that every other object store (Google Cloud Storage, Azure Blob Storage, MinIO, Ceph RGW, Backblaze B2) has adopted. This page covers the API surface, the consistency model evolution, the storage layering (cluster → blob → erasure-coded fragments), and the failure modes of running critical infrastructure on S3.

## The API

S3 exposes a REST API:

```http
PUT /my-bucket/path/to/object.txt HTTP/1.1
Host: s3.us-east-1.amazonaws.com
Content-Length: 1024
Content-Type: text/plain
x-amz-acl: private
Authorization: AWS4-HMAC-SHA256 ...

<1024 bytes of object content>
```

```http
GET /my-bucket/path/to/object.txt HTTP/1.1
Host: s3.us-east-1.amazonaws.com
Range: bytes=0-511
```

The canonical operations:
- **PUT object**: store a new object, max 5 TB.
- **GET object**: retrieve the whole object or a byte range.
- **HEAD object**: get metadata without the body.
- **DELETE object**: remove an object.
- **List bucket**: list objects in a bucket, paginated.
- **Multipart upload**: upload large objects in parts, supports resuming.
- **Presigned URL**: time-limited URL that grants a third party temporary access.

## Strong Consistency (since Dec 2020)

S3 originally offered **eventual consistency** for overwrite and delete: after a PUT, a subsequent GET might return the old version for up to several seconds. This was a conscious trade-off for S3's massive scale.

In December 2020, AWS announced [strong read-after-write consistency](https://aws.amazon.com/blogs/aws/amazon-s3-update-strong-read-after-write-consistency/) for all S3 operations at no extra cost. The mechanism:

- A `PUT` returns `200 OK` only after the object's index entry is durably replicated.
- A `GET` always reads from the latest index entry.
- The replication tier uses a quorum protocol internally; only after a quorum confirms the write does S3 return success.

Strong consistency applies to single-key operations only. **Multi-key operations** (list-after-write across multiple keys, atomic rename of multiple objects, etc.) remain eventually consistent. S3 has no transactions.

## The Storage Layer

S3 internally is layered:

```text
Object (user-visible)
   │
   ▼
Storage Node (a few per datacenter)
   │
   ▼
Blob (the object's bytes, sharded into ~10 MB chunks)
   │
   ▼
Erasure-coded fragments (4+2 RS per blob shard)
   │
   ▼
Disk (HDD with SSD cache tier)
```

- **Object → Blob**: each S3 object is stored as one or more "blobs" in the storage backend. Blobs are 10-100 MB chunks; large objects are split.
- **Blob → Erasure shards**: each blob is Reed-Solomon erasure-coded into N data + M parity fragments (e.g., 10+2 or 12+4). The fragments are distributed across different failure domains (racks, buildings).
- **Shards → Disks**: each shard is stored on a separate disk. The cluster topology ensures no two shards of the same blob are on the same physical disk.

For a 1 GB object with 10+2 erasure coding, the storage overhead is ~20% — 1.2 GB of stored data. Replication (3×) would require 3 GB. The erasure-coding trade-off is better storage density at the cost of higher CPU on read/write.

## The Index Tier

S3's metadata (object key, version, size, ACL, tags, etc.) is stored separately from the data:

```text
Client ── PUT object ──→ S3 Front-End
   │
   ├──── Data path: split into blob shards, erasure-code, write to storage nodes
   │
   └──── Metadata path: insert/update index entry in DynamoDB-style KV store
                          ↓
                       Quorum commit
                          ↓
                       Return 200 OK to client
```

The index tier is a distributed B-tree or LSM-tree (Amazon hasn't disclosed the exact internal structure) keyed by `(bucket, key, version)`. Strong consistency is achieved by writing the data and the index in a single quorum-commit transaction.

## Multipart Upload

For large objects (>5 GB) and for unreliable clients, S3 supports multipart upload:

1. Client calls `POST /bucket/key?uploads` to initiate. S3 returns an `UploadId`.
2. Client uploads parts via `PUT /bucket/key?partNumber=N&uploadId=...`. Each part is 5 MB - 5 GB.
3. Client calls `POST /bucket/key?uploadId=...` with the list of parts to complete the upload.
4. S3 concatenates the parts into a single object.

If any part fails, the client can retry just that part. If the client never completes the upload, the parts remain in S3's staging area until they're explicitly aborted (or auto-expired after 30 days).

The trade-off: each part is a separate object in S3's internal storage, and completing the upload requires copying them into the final blob. For very large uploads (TB), this completion step can take 30-60 seconds.

## Versioning and Lifecycle

S3 buckets can enable **versioning**: every PUT creates a new version of the object instead of overwriting. The full version history is retained until lifecycle rules delete old versions.

Lifecycle rules automate object deletion:

```json
{
  "Rules": [
    {
      "Status": "Enabled",
      "Prefix": "logs/",
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"},
        {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 730}
    }
  ]
}
```

The lifecycle moves objects between storage classes (cheaper, slower, less-durable) as they age, then expires them. The "GLACIER" classes are physically stored on tape or in cold-storage HDDs; restoring an object from GLACIER takes 1-12 hours.

## Storage Classes

| Class | Cost (vs STANDARD) | Latency | Use case |
|-------|---------------------|---------|-----------|
| STANDARD | 1× | 10-30 ms | Hot data, frequent access |
| STANDARD_IA | 0.5× | 10-30 ms | Infrequent access (30+ days), retrieval fee |
| ONE_ZONE_IA | 0.4× | 10-30 ms | Single-AZ, lower durability (99.9999999%) |
| GLACIER_IR | 0.4× | 1-5 min | Glacier with instant retrieval for small objects |
| GLACIER | 0.1× | 1-12 hr | Long-term archive, async retrieval |
| DEEP_ARCHIVE | 0.03× | 12-48 hr | Compliance archive, very rare retrieval |
| INTELLIGENT_TIERING | variable | variable | Auto-moves objects between tiers based on access patterns |

The trade-off: cost vs. retrieval latency vs. durability. STANDARD is 11×9s durability (99.999999999%); ONEZONE_IA is 9×9s (99.999999%). For most workloads, STANDARD is the default.

## Pitfalls

1. **No atomic rename across keys.** `PUT bucket/key2` then `DELETE bucket/key1` is two operations; a crash between them leaves both keys pointing to the same data. There is no transactional rename.

2. **List operations are eventually consistent for newly created objects.** A `List` immediately after a `PUT` may not include the new object. (Single-key operations are strongly consistent, but List is not.)

3. **No partial reads from GLACIER.** A GET from GLACIER first triggers a "restore" job (1-12 hours), then the object is available in STANDARD for a TTL (1-30 days). The first GET is a "submit restore job" call, not a content GET.

4. **Bucket names are global.** S3 bucket names share a single global namespace. If `my-company-logs` is taken in another AWS account, you cannot create it. Use unique prefixes (UUID, company name).

5. **The 5 GB limit on single PUT.** Objects larger than 5 GB require multipart upload. Naive client libraries will fail or hang on uploads of >5 GB; production code must use the multipart API explicitly or via a library that does.

6. **Error responses can be misleading.** A `503 Slow Down` means the bucket's rate limit is hit (default 3,500 PUT/sec per partition). The fix is to use a hash-prefixed key naming scheme (e.g., `01/key`, `02/key`) to spread objects across S3's internal partitions.

## Comparison to Other Object Stores

| Store | Strong consistency | Cost (vs S3 STANDARD) | Open source |
|-------|--------------------|------------------------|-------------|
| S3 | Yes (since Dec 2020) | 1× | No |
| GCS | Yes | 0.8-1.1× | No |
| Azure Blob | Yes (hot/cool tiers) | 0.7-1.2× | No |
| MinIO | Yes | 0.2-0.5× (self-hosted) | Yes (AGPL) |
| Ceph RGW | Yes (since Reef) | 0.3-0.7× (self-hosted) | Yes (LGPL) |
| Backblaze B2 | Yes | 0.2× | No |

MinIO and Ceph RGW are S3-compatible: their API mimics S3, so client code targeting S3 works against them. The trade-off is operational cost (running the cluster) vs. S3's per-GB price.

## References

- [Amazon S3 documentation](https://docs.aws.amazon.com/s3/)
- [Strong read-after-write consistency announcement](https://aws.amazon.com/blogs/aws/amazon-s3-update-strong-read-after-write-consistency/)
- [S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [Wong, "Amazon S3: The first 15 years"](https://www.youtube.com/watch?v=1I4K0qzlGhA) (re:Invent talk)
- [The original Dynamo paper (used for S3's index)](https://www.cs.ucsb.edu/~suri/psdir/dynamo.pdf) (SOSP 2007)
- [S3 API reference](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Operations_Amazon_Simple_Storage_Service.html)
- [Ceph RGW: S3-compatible API](https://docs.ceph.com/en/latest/radosgw/s3/)
