# MinIO Architecture

MinIO is an open-source object storage server, written in Go since 2014, exposing an S3-compatible API. It is designed to run on commodity hardware (a few SSDs in a 1U server) and to scale from a single-node deployment (laptop) to a multi-petabyte cluster of distributed nodes. This page covers the architecture, the erasure-coding storage layer, the IAM and bucket policy model, and the operational patterns that distinguish MinIO from Ceph RGW.

## The Design Goal: Simplicity

MinIO's tagline is "S3-compatible object storage on Kubernetes". The design philosophy:

- **One binary, one config**: `minio server /data` is the entire deployment command.
- **No external dependencies**: no PostgreSQL, no ZooKeeper, no etcd. The cluster state is in-memory and on disk.
- **Stateless nodes**: each MinIO server is independent; cluster membership is via DNS or a static config file.
- **Single-tenant by default**: IAM is per-deployment, not per-tenant. Multi-tenancy is achieved by running multiple MinIO instances.

This contrasts with Ceph, which requires monitors (mon), metadata servers (MDS), RADOS gateway (RGW), and a cluster-wide CRUSH map. MinIO's argument is that for the S3-compatible API use case (object storage, not block or file), the simpler model is sufficient.

## The Erasure-Coding Storage Layer

MinIO's data layer is **erasure-coded**, not replicated. Each object is split into data and parity shards using Reed-Solomon:

```text
Object: 1 MB
       ↓
Shards: 4 data + 2 parity shards (default), each ~250 KB
       ↓
6 shards distributed across 6 disks (one per disk)
       ↓
Read threshold: 4 (can read with any 4 of 6 shards)
       ↓
Write threshold: 4 (can write with any 4 of 6 disks up)
```

With 4 data + 2 parity, the cluster can lose 2 disks and still serve the data. Storage efficiency is 4/6 = 67%. With 8 data + 4 parity (12 disks total), efficiency is 8/12 = 75%.

MinIO's "storage class" lets you set different parity per prefix:

```bash
mc admin config set myminio/ env MINIO_STORAGE_CLASS_STANDARD=EC:4 MINIO_STORAGE_CLASS_RRS=EC:2
mc cp --storage-class REDUCED_REDUNDANCY ./file.txt myminio/mybucket/rr/file.txt
```

`REDUCED_REDUNDANCY` objects have lower durability (tolerate fewer disk failures) but better storage efficiency.

## The Cluster Topology

A MinIO cluster is a "distributed MinIO" deployment of N nodes:

```text
Node A: 4 disks    ┐
Node B: 4 disks    │  Erasure set = 12 disks across 3 nodes
Node C: 4 disks    ┘
```

MinIO groups disks into "erasure sets" of N disks (default 12-16). Each object is placed on one erasure set. With 12 disks per set and 4 data + 8 parity (or 8+4), the cluster can lose 8 of 12 disks and still serve the data.

The cluster can have multiple erasure sets; objects are distributed across sets in a round-robin (or hash-based) pattern. Adding nodes to the cluster creates new erasure sets; existing objects stay in their original sets.

## Server Pools and Tiering

MinIO added **server pools** (also called "tenant expansion") in 2022 to support multi-petabyte deployments:

- A server pool is a set of nodes (typically 4-32 nodes) that form an independent erasure set.
- Multiple server pools can be combined into one logical cluster.
- Object placement: by default, new objects go to the pool with most free space.
- Tiering: warm pool → cold pool (S3, GCS, Azure Blob) for lifecycle management.

```bash
mc admin tier add myminio/azure AZUREAzureCold \
  --endpoint https://myaccount.blob.core.windows.net \
  --access-key XXX --secret-key YYY --bucket cold-archive --prefix archive/

mc ilm rule add myminio/mybucket \
  --transition-days 90 --transition-tier AZUREAzureCold
```

After 90 days, objects are moved to Azure Blob storage (cheaper, slower). The S3 API against MinIO still works — MinIO transparently fetches from the cold tier on demand.

## The IAM Model

MinIO has its own IAM implementation that mirrors AWS IAM:

```bash
mc admin policy create myminio readonly ./readonly-policy.json
mc admin policy attach myminio readonly --user alice

# readonly-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::mybucket/*"]
    }
  ]
}
```

Policies use the same JSON format as AWS IAM policies, so existing AWS tooling (CloudFormation, Terraform) can manage MinIO IAM. The semantic differences:

- No resource-based policies (MinIO uses bucket policies only).
- No IAM roles (MinIO uses STS-style temporary credentials only).
- No SAML/OIDC integration in OSS edition (only in the commercial "Subsystem" product).

## Bucket Notification and Webhooks

MinIO supports S3-compatible event notifications:

```bash
mc admin config set myminio/ notify_webhook:1 \
  endpoint="https://my-hook.example.com/s3-event" \
  auth_type="bearer" auth_bearer="..."

mc event add myminio/mybucket arn:minio:sqs::1:webhook \
  --event put,delete
```

Every PUT/DELETE triggers an HTTP POST to the webhook with the event payload. This is the basis for MinIO-based data pipelines (e.g., trigger a Lambda on every new object).

## Production Patterns

**Single-node deployment** (laptop, dev box):
```bash
minio server /data
# Single node, single disk. No erasure coding. For dev only.
```

**Single-node multi-drive** (workstation):
```bash
minio server /data{1...4}
# Single node, 4 disks. Erasure-coded within the node.
```

**Distributed** (production):
```bash
minio server http://node{1...4}/data{1...4}
# 4 nodes, 4 disks each = 16-disk erasure set.
```

**Site replication** (multi-region):
```bash
mc admin replicate add myminio-east myminio-west
# Two sites, bi-directional replication. Reads are local, writes replicate.
```

Site replication is MinIO's equivalent of S3 Cross-Region Replication, but with bidirectional sync (S3's CRR is one-way). The replication is eventually consistent across sites.

## Performance

MinIO's published benchmarks (MinIO Performance for S3) on a 32-node cluster with 4 NVMe drives per node (128 drives total):

- Sequential PUT: 280 GB/s (with EC:4)
- Sequential GET: 320 GB/s
- Small object PUT (1 KB): 240,000 ops/sec
- Small object GET (1 KB): 320,000 ops/sec

These are S3-API operations, not raw disk throughput — the bottleneck is the Go HTTP layer and the Reed-Solomon encode/decode, not the disks.

## Comparison to Ceph RGW

| Aspect | MinIO | Ceph RGW |
|--------|-------|----------|
| Language | Go | C++ |
| Binary size | ~100 MB | ~500 MB+ (rgw + mon + osd) |
| External deps | None | Ceph mons required |
| Erasure coding | Yes (per-object RS) | Yes (RADOS-level EC) |
| Replication | Yes (site replication) | Yes (multi-site) |
| IAM | Built-in (S3-compatible) | Built-in (S3-compatible + Keystone) |
| Performance | Higher (simpler path) | Lower (more layers) |
| Operational complexity | Lower | Higher (Ceph expertise required) |
| Best for | S3-only deployments, simple ops | Mixed block/file/object, complex ops |

MinIO's "Go single binary, no external deps" makes it easy to deploy; Ceph's "C++ multiple daemons" makes it harder to deploy but supports block (RBD), file (CephFS), and object (RGW) on one cluster.

## Common Pitfalls

1. **Underestimating Go's GC pause on high-throughput workloads.** MinIO's Go runtime can see 50-100 ms GC pauses under memory pressure, which translates to occasional latency spikes on GET/PUT. Use GOMEMLIMIT and tune GOGC.

2. **Erasure sets that are too small.** The default 12-disk set means losing 4 disks (with EC:4) is recoverable. A 4-disk set with EC:2 can only lose 2 disks. For production, use at least 12-disk sets.

3. **Not planning for disk replacement.** When a disk fails, MinIO marks its shards as "missing" and starts healing them onto spare disks (or new disks). Healing 1 TB of data takes ~1 hour per TB on a 1 Gbps interconnect. Plan capacity for healing, not just steady-state.

4. **Mixing nodes with different disk sizes.** MinIO assumes all disks in an erasure set are the same size. Mixing 4 TB and 8 TB disks wastes 4 TB per 8 TB disk.

5. **Running MinIO without TLS in production.** The S3 protocol uses presigned URLs that include the signature; without TLS, the signature is sent over plain HTTP and is vulnerable to replay attacks. Use TLS termination at MinIO (or at a reverse proxy) in production.

## References

- [MinIO documentation](https://min.io/docs/minio/linux/index.html)
- [MinIO architecture documentation](https://min.io/resources/docs/MinIO-Architecture.pdf)
- [MinIO GitHub](https://github.com/minio/minio)
- [MinIO Erasure Coding: Quick Look](https://min.io/docs/minio/linux/operations/concepts/erasure-coding.html)
- [MinIO site replication](https://min.io/docs/minio/linux/operations/site-replication.html)
- [Ceph RGW vs MinIO: A comparison](https://min.io/product/overview/why-minio)
- [MinIO Subnet (commercial support)](https://min.io/subnet)
