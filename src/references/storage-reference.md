# Storage Systems Reference Library

This page is a verified index of primary sources for storage systems: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Local filesystems from ext4 to ZFS and Btrfs, distributed and parallel filesystems, the S3 object ecosystem, the block and device layers, backup and recovery, benchmarking, on-disk formats, and persistent memory — plus a two-track path from OSTEP to reading storage research.

The overlap contract: database engines (RocksDB, LevelDB, LMDB, WiredTiger) and columnar interchange formats (Parquet, Arrow) live in the [Database Systems index](./database-systems.md). This page owns filesystems — local, distributed and parallel — object storage, the block and device layers, backup and recovery, benchmarking, and on-disk formats. CXL and the new interconnect story belong to the [Computer Architecture index](./computer-architecture.md); this page keeps only the filesystem-side DAX note.

**64 entries** across 9 categories, plus **58 education & reference resources** (24 basic / 34 advanced), plus **8 video resources** and **8 conference sources**.

Every link HTTP-verified on **2026-10-08**.

> docs.redhat.com gates some manuals behind a login wall and the ACM Digital Library returns 403 to automated clients; both load normally in a browser. The Arch Wiki occasionally rate-limits automated clients. `git.kernel.org` cgit repos, `nfs.sourceforge.net`, `uefi.org` and the `lustre.org` sites return 403/429 to automated clients while loading normally in a browser. `io500.org` and `gnu.org` (the tar manual and Savannah) did not respond to automated checkers at verification time; all are long-stable canonical sources and load normally in a browser.

## Contents

- [1. Linux filesystems](#1-linux-filesystems) — 10
- [2. ZFS family](#2-zfs-family) — 4
- [3. Distributed & parallel filesystems](#3-distributed--parallel-filesystems) — 9
- [4. Object storage & the S3 ecosystem](#4-object-storage--the-s3-ecosystem) — 6
- [5. Block, volume & device layers](#5-block-volume--device-layers) — 10
- [6. Backup, snapshot & disaster recovery](#6-backup-snapshot--disaster-recovery) — 7
- [7. Benchmarking, observability & hardware health](#7-benchmarking-observability--hardware-health) — 7
- [8. Formats, interchange & embedded](#8-formats-interchange--embedded) — 6
- [9. Persistent memory & new buses](#9-persistent-memory--new-buses) — 5
- [Education & reference implementations](#education--reference-implementations) — 58 (24 basic / 34 advanced)
- [Research papers & open-access literature](#research-papers--open-access-literature) — 28
- [Video courses, channels & talks](#video-courses-channels--talks) — 8
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 8


## 1. Linux filesystems

### ext4

- **Docs:** [docs.kernel.org/filesystems/ext4](https://docs.kernel.org/filesystems/ext4/)
- **Developer / API:** [e2fsprogs (git.kernel.org)](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/)
- **Source:** [github.com/torvalds/linux — fs/ext4](https://github.com/torvalds/linux/tree/master/fs/ext4)
- **SDKs & repos:** tune2fs, dumpe2fs, debugfs, e2fsck — the userland toolbox every rescue story uses
- **Downloadable / offline:** Kernel docs build from source (`make htmldocs`); ext4(5) man page
- *Note:* The default Linux filesystem. Read the journal and delayed-allocation docs once — most "my disk is slow" interview questions end here.

### XFS

- **Docs:** [docs.kernel.org/filesystems/xfs](https://docs.kernel.org/filesystems/xfs/)
- **Developer / API:** [xfsprogs (git.kernel.org)](https://git.kernel.org/pub/scm/fs/xfs/xfsprogs-dev.git/)
- **Source:** [github.com/torvalds/linux — fs/xfs](https://github.com/torvalds/linux/tree/master/fs/xfs)
- **SDKs & repos:** xfs_admin, xfs_repair, xfs_bmap, xfs_io — xfs_io alone teaches you the syscall surface
- **Downloadable / offline:** Kernel docs + xfsprogs man pages
- *Note:* The scale-out workhorse: huge files, huge filesystems, rock-solid repair tooling. Default on RHEL for a reason.

### Btrfs

- **Docs:** [btrfs.readthedocs.io](https://btrfs.readthedocs.io/en/latest/)
- **Developer / API:** [btrfs.readthedocs.io — developer section](https://btrfs.readthedocs.io/en/latest/)
- **Source:** [github.com/kdave/btrfs-progs](https://github.com/kdave/btrfs-progs)
- **SDKs & repos:** btrfs-progs; kernel tree under fs/btrfs
- **Downloadable / offline:** Sphinx docs + btrfs(8), btrfs-send(8) man pages
- *Note:* Copy-on-write with checksums, snapshots, and send/receive in the mainline kernel. RAID5/6 reputation is historical but still interview-bait — see honest notes.

### F2FS

- **Docs:** [docs.kernel.org/filesystems/f2fs.html](https://docs.kernel.org/filesystems/f2fs.html)
- **Source:** [github.com/torvalds/linux — fs/f2fs](https://github.com/torvalds/linux/tree/master/fs/f2fs)
- **SDKs & repos:** f2fs-tools — [git.kernel.org — jaegeuk/f2fs-tools](https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git/) (mkfs.f2fs)
- **Downloadable / offline:** Kernel doc + man pages
- *Note:* Samsung's flash-friendly filesystem: log-structured where it helps, aware of FTL behaviour. The answer to "design a filesystem for an SSD or eMMC".

### bcachefs

- **Docs:** [bcachefs.org](https://bcachefs.org/)
- **Source:** [github.com/koverstreet/bcachefs](https://github.com/koverstreet/bcachefs)
- **SDKs & repos:** [bcachefs-tools](https://github.com/koverstreet/bcachefs-tools) — format, mount, multi-device management
- **Downloadable / offline:** Online docs; man pages with the tools
- *Note:* Copy-on-write with full journaling, erasure coding and caching, descended from bcache. Young and still churning — watch it, verify before deploying.

### overlayfs

- **Docs:** [docs.kernel.org/filesystems/overlayfs.html](https://docs.kernel.org/filesystems/overlayfs.html)
- **Source:** [github.com/torvalds/linux — fs/overlayfs](https://github.com/torvalds/linux/tree/master/fs/overlayfs)
- **SDKs & repos:** upperdir / lowerdir / merged — the mechanism under every container image layer
- **Downloadable / offline:** Kernel doc
- *Note:* Read the redirect model (upper vs lower, copy-up) and container image layers stop being mysterious.

### tmpfs

- **Docs:** [docs.kernel.org/filesystems/tmpfs.html](https://docs.kernel.org/filesystems/tmpfs.html)
- **Source:** [github.com/torvalds/linux — mm/shmem.c](https://github.com/torvalds/linux/tree/master/mm/shmem.c)
- **SDKs & repos:** RAM-backed, swap-backed; `/dev/shm`, `size=` mount option
- **Downloadable / offline:** Kernel doc + mount(8)
- *Note:* Files count against memory and swap, not disk. The classic "why did my container OOM on /tmp" question.

### squashfs

- **Docs:** [docs.kernel.org/filesystems/squashfs.html](https://docs.kernel.org/filesystems/squashfs.html)
- **Source:** [github.com/plougher/squashfs-tools](https://github.com/plougher/squashfs-tools)
- **SDKs & repos:** mksquashfs, unsquashfs — inside Live ISOs, container base images, embedded firmware
- **Downloadable / offline:** Compress a whole root filesystem into one read-only image
- *Note:* Read-only and highly compressed. Pair with overlayfs when you need writability on top.

### exFAT

- **Docs:** [exfatprogs (userspace tools)](https://github.com/exfatprogs/exfatprogs)
- **Source:** [github.com/torvalds/linux — fs/exfat](https://github.com/torvalds/linux/tree/master/fs/exfat)
- **SDKs & repos:** The interop filesystem for SD cards and USB drives
- **Downloadable / offline:** Kernel doc + mount(8)
- *Note:* No journal, no POSIX permissions, no extended attributes. Know why you are using it — Microsoft's spec is indexed in category 8.

### NFS

- **Docs:** [nfs.sourceforge.net (Linux NFS HOWTO)](https://nfs.sourceforge.net/)
- **Developer / API:** [docs.kernel.org/filesystems/nfs](https://docs.kernel.org/filesystems/nfs/)
- **Source:** [github.com/torvalds/linux — fs/nfs](https://github.com/torvalds/linux/tree/master/fs/nfs)
- **SDKs & repos:** [nfs-utils](https://github.com/linux-nfs/nfs-utils) — mountd, exportfs, showmount
- **Downloadable / offline:** HOWTO + exports(5), nfs(5) man pages
- *Note:* The network filesystem you will actually be asked about. v3's stateless model vs v4's stateful one is a standing interview question.


## 2. ZFS family

### OpenZFS documentation

- **Docs:** [openzfs.github.io/openzfs-docs](https://openzfs.github.io/openzfs-docs/)
- **Developer / API:** [openzfs.github.io/openzfs-docs — tuning & performance chapters](https://openzfs.github.io/openzfs-docs/)
- **Source:** [github.com/openzfs/zfs](https://github.com/openzfs/zfs)
- **SDKs & repos:** zfs, zpool, zed CLIs; zfs(8) and zpool(8) man pages
- **Downloadable / offline:** Full docs site plus man pages ship with the distribution packages
- *Note:* The vocabulary factory: CoW, checksums, snapshots, send/recv, RAID-Z, ARC/L2ARC/ZIL/SLOG. Learn the words once and half of storage interviews become pattern-matching.

### OpenZFS source

- **Docs:** [github.com/openzfs/zfs](https://github.com/openzfs/zfs)
- **Source:** [github.com/openzfs/zfs](https://github.com/openzfs/zfs)
- **SDKs & repos:** One codebase, two platforms: Linux and FreeBSD; module + userland split
- **Downloadable / offline:** In-repo man pages
- *Note:* CDDL-licensed, which is why it never merged into the mainline Linux kernel — see honest notes.

### ZFSBootMenu

- **Docs:** [zfsbootmenu.org](https://zfsbootmenu.org/)
- **Source:** [github.com/zbm-dev/zfsbootmenu](https://github.com/zbm-dev/zfsbootmenu)
- **SDKs & repos:** Boot environments as a system-rollback mechanism
- **Downloadable / offline:** Online docs
- *Note:* Snapshots you can boot. The clearest demonstration of what boot environments actually buy you.

### ZFS on FreeBSD

- **Docs:** [docs.freebsd.org/en/books/handbook/zfs](https://docs.freebsd.org/en/books/handbook/zfs/)
- **Source:** [github.com/freebsd/freebsd-src — sys/contrib/openzfs](https://github.com/freebsd/freebsd-src)
- **SDKs & repos:** The ZFS chapter of the FreeBSD Handbook
- **Downloadable / offline:** Handbook as HTML/PDF/EPUB
- *Note:* Cross-reference: FreeBSD ships OpenZFS in the base system, and the Handbook's ZFS chapter is the clearest operator guide anywhere.


## 3. Distributed & parallel filesystems

### Ceph

- **Docs:** [docs.ceph.com/en/latest](https://docs.ceph.com/en/latest/)
- **Developer / API:** [docs.ceph.com/en/latest — developer guide](https://docs.ceph.com/en/latest/dev/developer_guide/)
- **Source:** [github.com/ceph/ceph](https://github.com/ceph/ceph)
- **SDKs & repos:** RADOS, RBD, CephFS, RGW; librados/librbd bindings in C++, Python, Go
- **Downloadable / offline:** Versioned docs per release; `ceph` CLI help is a doc set of its own
- *Note:* The unified storage platform: block, object and POSIX file over one RADOS cluster. Pin doc links to `/en/latest` — version-scoped URLs rot. Start with the architecture chapter.

### Ceph source

- **Docs:** [github.com/ceph/ceph](https://github.com/ceph/ceph)
- **Source:** [github.com/ceph/ceph](https://github.com/ceph/ceph)
- **SDKs & repos:** CRUSH placement, BlueStore object store — the two reading targets
- **Downloadable / offline:** In-repo docs
- *Note:* CRUSH is the interview topic: consistent-hashing's smarter, crush-map-aware cousin.

### GlusterFS

- **Docs:** [docs.gluster.org](https://docs.gluster.org/)
- **Source:** [github.com/gluster/glusterfs](https://github.com/gluster/glusterfs)
- **SDKs & repos:** Translator architecture; brick/volume model; FUSE-mounted
- **Downloadable / offline:** Versioned administration guides
- *Note:* A userspace distributed filesystem with humbler, more legible ambitions than Ceph. Good for understanding translator-based design.

### Lustre

- **Docs:** [lustre.org/documentation](https://lustre.org/documentation/)
- **Developer / API:** [lustre.org — wiki & roadmap](https://wiki.lustre.org/)
- **Source:** [git.whamcloud.com — fs/lustre-release.git](https://git.whamcloud.com/?p=fs/lustre-release.git)
- **SDKs & repos:** MGS/MDS/M DT/OSS/OST vocabulary; the HPC workhorse behind most Top500 scratch filesystems
- **Downloadable / offline:** Operations manuals per release
- *Note:* Where exascale computing keeps its bytes. Read for the metadata-server vs object-storage-target split.

### BeeGFS

- **Docs:** [beegfs.io](https://www.beegfs.io/)
- **Developer / API:** [beegfs.io — documentation portal](https://www.beegfs.io/)
- **Source:** — (open-source releases published by the vendor; see docs)
- **SDKs & repos:** Metadata targets + storage targets; container-based quickstart
- **Downloadable / offline:** Online docs per version
- *Note:* Parallel filesystem with a transparent, well-documented architecture. The easiest parallel FS to stand up in a lab.

### SeaweedFS

- **Docs:** [github.com/seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)
- **Developer / API:** [github.com/seaweedfs/seaweedfs — wiki](https://github.com/seaweedfs/seaweedfs/wiki)
- **Source:** [github.com/seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)
- **SDKs & repos:** Filer, FUSE mount, S3 gateway, volume servers; inspired by Facebook's Haystack paper
- **Downloadable / offline:** In-repo wiki
- *Note:* O(1) disk reads for billions of small files — the Haystack idea, implemented and running.

### JuiceFS

- **Docs:** [juicefs.com/docs](https://juicefs.com/docs/)
- **Developer / API:** [juicefs.com/docs — reference](https://juicefs.com/docs/)
- **Source:** [github.com/juicedata/juicefs](https://github.com/juicedata/juicefs)
- **SDKs & repos:** Metadata engine (Redis/TiKV/SQL) + object storage = POSIX filesystem; CSI driver for Kubernetes
- **Downloadable / offline:** Online docs
- *Note:* The cloud-native equation in one product: metadata service plus dumb object store equals a real filesystem. Read to see what the metadata layer must actually guarantee.

### Garage

- **Docs:** [garagehq.deuxfleurs.fr](https://garagehq.deuxfleurs.fr/)
- **Developer / API:** [garagehq.deuxfleurs.fr — reference manual](https://garagehq.deuxfleurs.fr/documentation/reference-manual/)
- **Source:** [git.deuxfleurs.fr — Deuxfleurs/garage](https://git.deuxfleurs.fr/Deuxfleurs/garage)
- **SDKs & repos:** S3-compatible, geo-distributed, self-hostable, Rust
- **Downloadable / offline:** Online book
- *Note:* Small-scale, multi-site S3 with an unusually honest design doc about quorum and consistency trade-offs.

### HDFS

- **Docs:** [hadoop.apache.org/docs/stable](https://hadoop.apache.org/docs/stable/)
- **Developer / API:** [hadoop.apache.org/docs/stable — Hadoop FileSystem API & WebHDFS](https://hadoop.apache.org/docs/stable/)
- **Source:** [github.com/apache/hadoop](https://github.com/apache/hadoop)
- **SDKs & repos:** NameNode/DataNode, 128 MB blocks, replication, rack awareness; WebHDFS REST
- **Downloadable / offline:** Full docs per release
- *Note:* The granddaddy. The HDFS Architecture page is still the best introduction to block-replicated distributed filesystems.


## 4. Object storage & the S3 ecosystem

### MinIO

- **Docs:** [min.io/docs/minio/linux](https://min.io/docs/minio/linux/index.html)
- **Developer / API:** [min.io/docs/minio/linux — SDK & API docs](https://min.io/docs/minio/linux/index.html)
- **Source:** [github.com/minio/minio](https://github.com/minio/minio)
- **SDKs & repos:** [mc](https://github.com/minio/mc) client; S3-compatible API in a single Go binary
- **Downloadable / offline:** Single-binary deployment; docs online
- *Note:* S3 on your laptop and in your lab. The fastest way to develop against an S3 dialect without a cloud account.

### Ceph RADOS Gateway (RGW)

- **Docs:** [docs.ceph.com/en/latest — radosgw](https://docs.ceph.com/en/latest/radosgw/)
- **Source:** [github.com/ceph/ceph](https://github.com/ceph/ceph)
- **SDKs & repos:** S3- and Swift-compatible gateways backed by RADOS
- **Downloadable / offline:** Versioned docs
- *Note:* When your Ceph cluster needs to speak S3. Read next to the MinIO docs to compare gateway designs.

### SeaweedFS S3 gateway

- **Docs:** [github.com/seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)
- **Source:** [github.com/seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)
- **SDKs & repos:** S3-compatible gateway on the filer; buckets over volume servers
- **Downloadable / offline:** In-repo docs
- *Note:* Cross-reference — the main entry is in category 3. Read alongside Backblaze B2 and MinIO to compare S3 dialects.

### Backblaze B2

- **Docs:** [backblaze.com/b2/docs](https://www.backblaze.com/b2/docs/)
- **Developer / API:** [backblaze.com/b2/docs — native API reference](https://www.backblaze.com/b2/docs/)
- **Source:** — (proprietary service; CLI is open)
- **SDKs & repos:** [B2_Command_Line_Tool](https://github.com/Backblaze/B2_Command_Line_Tool); S3-compatible endpoint
- **Downloadable / offline:** Online docs
- *Note:* Cheap cloud object storage with a real spec. Their Drive Stats and Storage reports (name-only) are the best public data on disk failure rates.

### rclone

- **Docs:** [rclone.org/docs](https://rclone.org/docs/)
- **Developer / API:** [rclone.org/rc — remote-control API](https://rclone.org/rc/)
- **Source:** [github.com/rclone/rclone](https://github.com/rclone/rclone)
- **SDKs & repos:** 40+ backends; `rclone serve s3/webdav`; rsync semantics for the cloud
- **Downloadable / offline:** Man page + full online docs
- *Note:* The universal object-storage adapter. Its per-provider pages document exactly how each S3 dialect differs — a goldmine for integration debugging.

### Amazon S3

- **Docs:** [docs.aws.amazon.com/s3](https://docs.aws.amazon.com/s3/)
- **Developer / API:** [docs.aws.amazon.com/s3 — API reference within](https://docs.aws.amazon.com/s3/)
- **Source:** — (proprietary service)
- **SDKs & repos:** aws-cli, boto3, aws-sdk-* — the API everyone else copies
- **Downloadable / offline:** AWS docs support per-section offline/PDF export
- *Note:* The de facto standard. Versioning, lifecycle rules, storage classes and consistency semantics are the interview canon.


## 5. Block, volume & device layers

### LVM2

- **Docs:** [sourceware.org/lvm2](https://sourceware.org/lvm2/)
- **Source:** [sourceware.org/git — lvm2.git](https://sourceware.org/git/?p=lvm2.git)
- **SDKs & repos:** pvcreate/vgcreate/lvcreate; snapshots, thin provisioning, stripes, mirrors
- **Downloadable / offline:** lvm(8), lvmthin(7) man pages
- *Note:* The volume layer every sysadmin interview assumes. Do one pv→vg→lv walkthrough by hand and it never leaves you.

### device-mapper

- **Docs:** [docs.kernel.org/admin-guide/device-mapper](https://docs.kernel.org/admin-guide/device-mapper/)
- **Source:** [github.com/torvalds/linux — drivers/md](https://github.com/torvalds/linux/tree/master/drivers/md)
- **SDKs & repos:** dm-linear, dm-mirror, dm-thin, dm-verity, dm-crypt — the table-driven block layer
- **Downloadable / offline:** Kernel docs
- *Note:* The framework LVM, cryptsetup and verity are built on. `dmsetup table` on a running system is the fastest way to see it.

### dm-crypt / cryptsetup

- **Docs:** [gitlab.com/cryptsetup/cryptsetup](https://gitlab.com/cryptsetup/cryptsetup)
- **Developer / API:** [gitlab.com/cryptsetup/cryptsetup — FAQ & docs in-repo](https://gitlab.com/cryptsetup/cryptsetup)
- **Source:** [gitlab.com/cryptsetup/cryptsetup](https://gitlab.com/cryptsetup/cryptsetup)
- **SDKs & repos:** LUKS2 header format, token plugins, cryptsetup-reencrypt
- **Downloadable / offline:** In-repo docs + man pages
- *Note:* Disk encryption is a block-layer problem, not a filesystem problem — this project is the proof.

### md (multiple device) RAID

- **Docs:** [docs.kernel.org/admin-guide/md.html](https://docs.kernel.org/admin-guide/md.html)
- **Source:** [github.com/torvalds/linux — drivers/md](https://github.com/torvalds/linux/tree/master/drivers/md)
- **SDKs & repos:** mdadm is the userspace interface (next entry); /proc/mdstat is the state view
- **Downloadable / offline:** Kernel doc + md(4) man page
- *Note:* Software RAID 0/1/5/6/10 with online reshape. Know the difference between md RAID and LVM mirroring.

### mdadm

- **Docs:** mdadm(8) man page — authoritative and complete (inline reference, no web copy needed)
- **Source:** [git.kernel.org — utils/mdadm](https://git.kernel.org/pub/scm/utils/mdadm/mdadm.git/)
- **SDKs & repos:** `--detail --scan --monitor`; ARRAY lines in mdadm.conf
- **Downloadable / offline:** Man pages
- *Note:* mdadm is the interface to md. Learn the three states — clean, degraded, rebuilding — and what each means for your data.

### NVMe specifications

- **Docs:** [nvmexpress.org — specifications](https://nvmexpress.org/specifications/)
- **Source:** — (industry spec body)
- **SDKs & repos:** Base 2.x spec, NVMe-oF, ZNS (zoned namespaces) — the three names to know
- **Downloadable / offline:** Spec PDFs downloadable free after registration
- *Note:* Read the admin-vs-I/O command set split and the queue-pair model. NVMe-oF extends the same command set over a network — that symmetry is the insight.

### nvme-cli

- **Docs:** [github.com/linux-nvme/nvme-cli](https://github.com/linux-nvme/nvme-cli)
- **Source:** [github.com/linux-nvme/nvme-cli](https://github.com/linux-nvme/nvme-cli)
- **SDKs & repos:** [libnvme](https://github.com/linux-nvme/libnvme); `nvme list`, `nvme smart-log`, `nvme format`
- **Downloadable / offline:** Man page per subcommand
- *Note:* The hands-on tool for every NVMe admin question. `nvme smart-log` is the NVMe answer to smartctl.

### SPDK

- **Docs:** [spdk.io/doc](https://spdk.io/doc/)
- **Developer / API:** [spdk.io/doc — API & application docs](https://spdk.io/doc/)
- **Source:** [github.com/spdk/spdk](https://github.com/spdk/spdk)
- **SDKs & repos:** Userspace NVMe driver, event framework, pollers, bdev layer
- **Downloadable / offline:** Docs + examples in-repo
- *Note:* Kernel-bypass storage: where the "put the whole stack in userspace" school lives, with the latency numbers to argue for it.

### Linux SCSI target (LIO / targetcli)

- **Docs:** [linux-iscsi.org](https://linux-iscsi.org/)
- **Source:** [github.com/open-iscsi/open-iscsi](https://github.com/open-iscsi/open-iscsi) (initiator; the target lives in the kernel tree under drivers/target)
- **SDKs & repos:** targetcli shell; iSCSI, FC and vSCSI fabric modules on LIO
- **Downloadable / offline:** Online docs
- *Note:* How Linux exports block devices over iSCSI. Interview question "what is an iSCSI LUN" becomes trivial once you have created one with targetcli.

### virtio (virtio-blk)

- **Docs:** [docs.oasis-open.org — virtio 1.2](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)
- **Source:** — (OASIS specification)
- **SDKs & repos:** Virtqueues; split/packed ring layouts; how every VM talks to its disks
- **Downloadable / offline:** Spec HTML and PDF, free
- *Note:* Read the virtqueue description once and virtual machine I/O stops being magic.


## 6. Backup, snapshot & disaster recovery

### BorgBackup

- **Docs:** [borgbackup.readthedocs.io](https://borgbackup.readthedocs.io/en/stable/)
- **Source:** [github.com/borgbackup/borg](https://github.com/borgbackup/borg)
- **SDKs & repos:** Dedup, compression, authenticated encryption; SSH as the transport
- **Downloadable / offline:** Sphinx docs + man pages
- *Note:* What you reach for on a single box. Its docs explain dedup better than most papers.

### Restic

- **Docs:** [restic.net](https://restic.net/)
- **Developer / API:** [restic.net — design document & REST backend docs](https://restic.net/)
- **Source:** [github.com/restic/restic](https://github.com/restic/restic)
- **SDKs & repos:** Native cloud backends (S3, B2, Azure, GCS), snapshots, dedup, encryption
- **Downloadable / offline:** Docs online + man page
- *Note:* Designed for cloud backends from day one. The design document explains why the repo format looks the way it does.

### Kopia

- **Docs:** [kopia.io/docs](https://kopia.io/docs/)
- **Developer / API:** [kopia.io/docs — policy & API docs](https://kopia.io/docs/)
- **Source:** [github.com/kopia/kopia](https://github.com/kopia/kopia)
- **SDKs & repos:** Client-side encryption, policies, KopiaUI desktop app
- **Downloadable / offline:** Online docs
- *Note:* Restic's closest cousin with a stronger policy model. Compare the two repo formats for a good design discussion.

### rsync

- **Docs:** [rsync.samba.org](https://rsync.samba.org/)
- **Source:** [github.com/RsyncProject/rsync](https://github.com/RsyncProject/rsync)
- **SDKs & repos:** Delta-transfer algorithm; rsync(1) and rsyncd.conf(5)
- **Downloadable / offline:** Man pages
- *Note:* Not a backup system by itself — no history, no verification — but the delta algorithm is the interview question that launched a thousand explanations.

### ZFS send/recv

- **Docs:** [openzfs.github.io/openzfs-docs](https://openzfs.github.io/openzfs-docs/)
- **Source:** [github.com/openzfs/zfs](https://github.com/openzfs/zfs)
- **SDKs & repos:** Incremental streams (`zfs send -i`), raw sends of encrypted datasets, resume tokens
- **Downloadable / offline:** zfs-send(8), zfs-recv(8) man pages
- *Note:* Replication by streaming block trees, not files. The model every "database shipping WAL" discussion is secretly comparing against.

### Btrfs send/receive

- **Docs:** [btrfs.readthedocs.io](https://btrfs.readthedocs.io/en/latest/)
- **Source:** [github.com/kdave/btrfs-progs](https://github.com/kdave/btrfs-progs)
- **SDKs & repos:** btrfs-send(8), btrfs-receive(8); incremental streams from snapshots
- **Downloadable / offline:** Man pages
- *Note:* The same idea as ZFS send/recv, mainline in Linux. Snapshots + send is the Linux-native replication story.

### Velero

- **Docs:** [velero.io](https://velero.io/)
- **Developer / API:** [velero.io/docs](https://velero.io/docs/)
- **Source:** [github.com/vmware-tanzu/velero](https://github.com/vmware-tanzu/velero)
- **SDKs & repos:** Kubernetes cluster-state backup; plugins for cloud volume snapshots; restic/kopia integration for PVs
- **Downloadable / offline:** Online docs
- *Note:* Cluster state plus persistent volumes. The standard answer to "how do you back up Kubernetes".


## 7. Benchmarking, observability & hardware health

### fio

- **Docs:** [github.com/axboe/fio](https://github.com/axboe/fio)
- **Developer / API:** [github.com/axboe/fio — HOWTO](https://github.com/axboe/fio/blob/master/HOWTO.rst)
- **Source:** [github.com/axboe/fio](https://github.com/axboe/fio)
- **SDKs & repos:** Job files; engines: libaio, io_uring, psync, rbd, http; see the examples/ directory
- **Downloadable / offline:** fio(1) man page + in-repo HOWTO
- *Note:* THE storage benchmark. Every performance interview question reduces to "describe this workload in a fio job": iodepth, blocksize, random vs sequential, read vs write mix.

### blktrace / blkparse

- **Docs:** [git.kernel.org — axboe/blktrace.git](https://git.kernel.org/pub/scm/linux/kernel/git/axboe/blktrace.git/)
- **Source:** [git.kernel.org — axboe/blktrace.git](https://git.kernel.org/pub/scm/linux/kernel/git/axboe/blktrace.git/)
- **SDKs & repos:** blkparse, btt — see I/O the way the block layer sees it
- **Downloadable / offline:** Man pages in-repo
- *Note:* Pairs with iostat: iostat tells you averages, blktrace shows you the actual request stream with timestamps.

### sysstat (iostat, sar)

- **Docs:** [github.com/sysstat/sysstat](https://github.com/sysstat/sysstat)
- **Source:** [github.com/sysstat/sysstat](https://github.com/sysstat/sysstat)
- **SDKs & repos:** `iostat -x 1` is the first command on any slow box; sar for history
- **Downloadable / offline:** Man pages
- *Note:* %util is a trap on fast devices — see honest notes. await and queue depth carry the real signal.

### smartmontools

- **Docs:** [smartmontools.org](https://www.smartmontools.org/)
- **Source:** [github.com/smartmontools/smartmontools](https://github.com/smartmontools/smartmontools)
- **SDKs & repos:** smartctl — SMART attributes, self-tests, error logs; NVMe health via nvme-cli
- **Downloadable / offline:** Man pages + drivedb database
- *Note:* The low-level disk health tool. Companion: hdparm (name-only) — the other veteran for drive parameters and timings.

### ioping

- **Docs:** [github.com/koct9i/ioping](https://github.com/koct9i/ioping)
- **Source:** [github.com/koct9i/ioping](https://github.com/koct9i/ioping)
- **SDKs & repos:** ping for storage — latency distribution in one command
- **Downloadable / offline:** Man page
- *Note:* The fastest way to feel the difference between NVMe, SATA and network block storage. Run it before reading any whitepaper.

### IO500

- **Docs:** [io500.org](https://io500.org/)
- **SDKs & repos:** The HPC storage benchmark; full result lists published with configurations
- **Downloadable / offline:** Lists and submission data online
- *Note:* Shows what "fast filesystem" means at scale: metadata operations and IOPS, not just bandwidth. Read the winning submissions' configs.

### filebench

- **Docs:** [github.com/filebench/filebench](https://github.com/filebench/filebench)
- **Source:** [github.com/filebench/filebench](https://github.com/filebench/filebench)
- **SDKs & repos:** Workload models (fileserver, varmail, oltp) in its own workload language
- **Downloadable / offline:** In-repo man pages + workload files
- *Note:* Older than fio but still the standard way to model whole application I/O patterns rather than raw device limits.


## 8. Formats, interchange & embedded

### SQLite file format

- **Docs:** [sqlite.org/fileformat2.html](https://www.sqlite.org/fileformat2.html)
- **Developer / API:** [sqlite.org/fileformat2.html](https://www.sqlite.org/fileformat2.html)
- **Source:** — (the database engine itself lives in the Database Systems index)
- **SDKs & repos:** B-tree pages, WAL frames, freelist, schema layer — documented byte by byte
- **Downloadable / offline:** The spec is a single complete HTML page
- *Note:* This entry is the **on-disk format**; the DBMS index covers the database itself. One of the very few file formats with a complete, readable, current specification.

### GNU tar

- **Docs:** [gnu.org/software/tar/manual](https://www.gnu.org/software/tar/manual/)
- **Source:** [cgit.savannah.gnu.org — tar.git](https://cgit.savannah.gnu.org/git/tar.git)
- **SDKs & repos:** POSIX ustar/pax vs GNU extensions; --one-file-system, --listed-incremental
- **Downloadable / offline:** Manual as HTML/PDF/info
- *Note:* The format that outlived tapes. Incremental backup semantics, block size and device independence are all in here.

### Filesystem Hierarchy Standard (FHS)

- **Docs:** [refspecs.linuxfoundation.org/FHS_3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- **SDKs & repos:** Where /etc, /var, /usr, /srv must be — and why
- **Downloadable / offline:** Single HTML document
- *Note:* Distributions deviate from it; interviews do not. One afternoon to read, permanent vocabulary gain.

### exFAT specification

- **Docs:** [learn.microsoft.com — exFAT specification](https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification)
- **Source:** — (Microsoft-published spec)
- **SDKs & repos:** The published spec that made the Linux exFAT implementation possible
- **Downloadable / offline:** Online HTML
- *Note:* Spec-versus-field drift in action: SD cards in the wild disagree with Microsoft's own document in instructive ways.

### JEDEC standards (eMMC / UFS)

- **Docs:** [jedec.org](https://www.jedec.org/) — search for JESD84 (eMMC) and JESD220 (UFS)
- **Source:** — (standards body)
- **SDKs & repos:** eMMC and UFS — the embedded flash standards inside every phone and most IoT boards
- **Downloadable / offline:** Standards purchasable; some documents free after registration
- *Note:* Paywalled. You rarely need more than knowing which standard applies and what the layering (device, partition, boot areas) is.

### UEFI specifications (GPT)

- **Docs:** [uefi.org — specifications](https://uefi.org/specifications)
- **Source:** — (UEFI Forum)
- **SDKs & repos:** The UEFI spec defines the GPT partition table; ACPI and Secure Boot documents also live here
- **Downloadable / offline:** Spec PDFs free
- *Note:* Read only the partition-table section: protective MBR, GPT header, entry array, backup copy. That layout is interview-canonical.


## 9. Persistent memory & new buses

### PMDK

- **Docs:** [pmem.io/pmdk](https://pmem.io/pmdk/)
- **Developer / API:** [pmem.io/pmdk — man pages for libpmem & libpmemobj](https://pmem.io/pmdk/)
- **Source:** [github.com/pmem/pmdk](https://github.com/pmem/pmdk)
- **SDKs & repos:** libpmem, libpmemobj, pmempool, pmreorder
- **Downloadable / offline:** Docs + man pages
- *Note:* The programming model that made "byte-addressable storage" concrete: flushes, fences, transactions at memory speed.

### libpmemobj

- **Docs:** [pmem.io/pmdk](https://pmem.io/pmdk/) — the libpmemobj portion
- **Developer / API:** [pmem.io/pmdk — libpmemobj API](https://pmem.io/pmdk/)
- **Source:** [github.com/pmem/pmdk](https://github.com/pmem/pmdk)
- **SDKs & repos:** Transactional object store, persistent pointers, allocator with layout awareness
- **Downloadable / offline:** Man pages
- *Note:* The hardware it targeted (Optane) was discontinued, but the crash-consistency ideas are permanent — the cleanest education in what memory-speed persistence demands.

### DAX

- **Docs:** [docs.kernel.org/filesystems/dax.html](https://docs.kernel.org/filesystems/dax.html)
- **Source:** [github.com/torvalds/linux](https://github.com/torvalds/linux) — fs/dax.c
- **SDKs & repos:** Direct access: mmap bypasses the page cache entirely
- **Downloadable / offline:** Kernel doc
- *Note:* CXL and the wider new-interconnect story are owned by the [Computer Architecture index](./computer-architecture.md) — this page keeps only the filesystem-side DAX note.

### NVDIMM admin guide

- **Docs:** [docs.kernel.org — NVDIMM driver API](https://docs.kernel.org/driver-api/nvdimm/index.html)
- **Source:** [github.com/torvalds/linux](https://github.com/torvalds/linux) — drivers/nvdimm
- **SDKs & repos:** pmem namespaces, labels, modes; ndctl companion below
- **Downloadable / offline:** Kernel docs
- *Note:* Region vs namespace, and why "pmem" and "blk" modes existed. The kernel-side counterpart to the PMDK view.

### ndctl

- **Docs:** [github.com/pmem/ndctl](https://github.com/pmem/ndctl)
- **Source:** [github.com/pmem/ndctl](https://github.com/pmem/ndctl)
- **SDKs & repos:** Namespace management, region/label model; daxctl for device-DAX
- **Downloadable / offline:** Man pages
- *Note:* libnvdimm's userland. Even with Optane gone, the tooling remains the reference for how the kernel models persistent regions.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*24 resources across 6 topics.*


#### The one book to start with

- **[OSTEP — persistence & file-system chapters](https://pages.cs.wisc.edu/~remzi/OSTEP/)** — Free and complete. The file-system chapters (files, directories, crash consistency, log-structured filesystems) are the syllabus for every storage interview.
- **[OpenZFS documentation](https://openzfs.github.io/openzfs-docs/)** — The ZFS primer. Read "Getting started", then skim the tuning chapters once you have a pool running.
- **[Brendan Gregg's filesystem & lower-level pages](https://www.brendangregg.com/)** — Filesystem analysis, iostat interpretation and storage methodology from the systems-performance reference.


#### Filesystem fundamentals

- **[Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)** — Where everything lives and why. One afternoon to read.
- **[Linux man-pages](https://man7.org/linux/man-pages/)** — Sections 2, 5 and 8 carry the storage interface.
- **[mount(8) and mkfs(8)](https://man7.org/linux/man-pages/man8/mount.8.html)** — The two commands every storage question hides behind.
- **[Arch Wiki — File systems](https://wiki.archlinux.org/title/File_systems)** — Community-maintained, practical, occasionally stale. See honest notes.
- **[Red Hat storage documentation](https://docs.redhat.com/)** — The RHEL storage administration guides are superb operator material; some manuals sit behind a login wall.


#### Tools to learn alongside

- **[rsync](https://rsync.samba.org/)** — The first backup tool everyone learns. Learn `--dry-run` before anything else.
- **[smartmontools](https://www.smartmontools.org/)** — `smartctl -a` on any disk you own. Learn to read SMART attributes.
- **[util-linux](https://github.com/util-linux/util-linux)** — lsblk, blkid, findmnt: the geometry-reading tools.
- **[LVM2](https://sourceware.org/lvm2/)** — Do one pvcreate → vgcreate → lvcreate walkthrough by hand.
- **[GNU tar](https://www.gnu.org/software/tar/manual/)** — The archive format that outlived tapes.


#### Distro & operator guides

- **[Linux Storage Stack Diagram (Thomas-Krenn wiki)](https://wiki.thomas-krenn.com/en/Linux_Storage_Stack_Diagram)** — One picture of the whole I/O stack, from syscall to device. Print it.
- **[Debian Administrator's Handbook](https://debian-handbook.info/)** — Free book; the disk and filesystem chapters are grounded and honest.
- **[Ubuntu Server documentation](https://ubuntu.com/server/docs)** — Filesystem and disk sections for a second vendor view.
- **[Linux kernel admin guide](https://docs.kernel.org/admin-guide/)** — The user-facing half of the kernel docs, including device-mapper.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which storage papers matter. Curated, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language; the storage entries are excellent.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. Follow the citation trail from the GFS paper forward.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF.


#### First hands-on steps

- **[Linux Kernel Labs — filesystem labs](https://linux-kernel-labs.github.io/)** — VFS and filesystem exercises with prepared QEMU setups.
- **[Restic quick start](https://restic.net/)** — Back up a directory to a local repo in five commands; then read the design document.
- **[ioping](https://github.com/koct9i/ioping)** — Latency is the first thing to feel, not read about.


### Advanced

*34 resources across 6 topics.*


#### Filesystem internals & the kernel tree

- **[Kernel documentation — filesystems](https://docs.kernel.org/filesystems/)** — Every filesystem's kernel doc in one tree. Start with ext4, xfs, btrfs and overlayfs.
- **[Btrfs developer documentation](https://btrfs.readthedocs.io/en/latest/)** — The developer section covers on-disk format and tree internals.
- **[OpenZFS performance & tuning docs](https://openzfs.github.io/openzfs-docs/)** — Pool tuning, ARC sizing, recordsize. Same docs root, deeper chapters.
- **XFS documentation by the XFS maintainers** — name-only: Darrick Wong's XFS write-ups and the xfs.org wiki; they explain on-disk format changes as they land.
- **F2FS design paper** — name-only: "F2FS: A New File System for Flash Storage" by Kim et al. (Samsung); find it via the venues below.
- **[LWN.net filesystem & storage coverage](https://lwn.net/)** — The best reporting on what is actually changing in Linux storage, with the why.


#### Distributed storage in depth

- **[Ceph architecture](https://docs.ceph.com/en/latest/architecture/)** — RADOS, CRUSH, monitors, placement groups. The chapter to read twice.
- **[HDFS documentation](https://hadoop.apache.org/docs/stable/)** — The HDFS Architecture page inside is the canonical block-replication write-up.
- **[Lustre documentation](https://lustre.org/documentation/)** — Operations manuals; the metadata-server/object-target split you will hear about in HPC.
- **[GlusterFS administration guide](https://docs.gluster.org/)** — Translator architecture and volume types, documented cleanly.
- **[JuiceFS documentation](https://juicefs.com/docs/)** — What a metadata engine must guarantee when the data lives in object storage.


#### Performance engineering

- **[fio examples](https://github.com/axboe/fio/tree/master/examples)** — Job files for every engine. Copy, modify, run, reason.
- **[SPDK documentation](https://spdk.io/doc/)** — Userspace NVMe drivers, pollers, the bdev layer.
- **[blktrace](https://git.kernel.org/pub/scm/linux/kernel/git/axboe/blktrace.git/)** — Read the request stream with timestamps; pair with btt for latency breakdowns.
- **[sysstat](https://github.com/sysstat/sysstat)** — `iostat -x 1` under load; sar for the long view.
- **[filebench](https://github.com/filebench/filebench)** — Model whole application workloads, not just devices.
- **[IO500](https://io500.org/)** — What metadata performance means at HPC scale; winning configs are public.


#### Storage for database people

- **CMU 15-445 storage lectures** — name-only: the storage and B-tree lectures are the best video treatment of pages, buffer pools and heap files.
- **[Readings in Database Systems (the Red Book)](https://www.redbook.io/)** — Stonebraker-edited canon with commentary; the storage papers are the backbone.
- **[Jepsen analyses](https://jepsen.io/analyses)** — How distributed stores actually fail under partitions and crashes. Read several before trusting any consistency claim.
- **LevelDB → RocksDB → LMDB reading path** — belongs to the [Database Systems index](./database-systems.md); start there, then compare engine assumptions against filesystem behaviour here.
- **NVMe specification reading guide** — name-only: queue pairs, admin vs I/O commands, namespaces; read the base spec's overview chapters before any vendor whitepaper.


#### Research venues for storage

- **[USENIX FAST](https://www.usenix.org/conference/fast25)** — The File and Storage Technologies conference: THE storage venue. Everything open access.
- **[USENIX OSDI](https://www.usenix.org/conference/osdi26)** — Flagship systems venue; storage papers every year, papers free.
- **[ACM SOSP](https://sosp.org/)** — The other flagship; recent proceedings open via ACM OA.
- **[USENIX ATC](https://www.usenix.org/conference/atc25)** — Applied systems work; all papers free.
- **[EuroSys](https://www.eurosys.org/)** — Partially open via ACM OA; strong storage tracks.
- **[USENIX HotStorage](https://www.usenix.org/conference/hotstorage25)** — The workshop layer: short papers, new ideas, open access.


#### Hardware, specs & low level

- **[NVMe specifications](https://nvmexpress.org/specifications/)** — Free PDFs: base spec, NVMe-oF, ZNS.
- **[virtio specification](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)** — Virtqueues; how VM I/O actually travels.
- **[UEFI specifications (GPT)](https://uefi.org/specifications)** — The partition-table layout every systems interview assumes.
- **[PMDK](https://pmem.io/pmdk/)** — The persistent-memory programming model.
- **[DAX kernel documentation](https://docs.kernel.org/filesystems/dax.html)** — Direct access from filesystem to memory, bypassing the page cache.
- **[cryptsetup / dm-crypt](https://gitlab.com/cryptsetup/cryptsetup)** — LUKS2 on-disk format; encryption at the block layer.


## Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems and storage work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, SoCC, ASPLOS, POPL and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA, SC and the IEEE journals; MSST papers also surface here
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture and storage authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### USENIX FAST

- **Docs:** [usenix.org/conference/fast25](https://www.usenix.org/conference/fast25)
- **SDKs & repos:** File and Storage Technologies — THE dedicated storage venue
- **Downloadable / offline:** Every paper free, immediately, usually with talk recordings
- *Note:* Fully open. If you read one venue's last decade of papers, make it this one. Conference URLs are year-scoped — see honest notes.

### USENIX OSDI

- **Docs:** [usenix.org/conference/osdi26](https://www.usenix.org/conference/osdi26)
- **SDKs & repos:** The flagship systems venue; filesystem and distributed-storage papers appear every edition
- **Downloadable / offline:** Every paper free, plus talk recordings
- *Note:* Alternates with SOSP. Start with the best-paper awards from the last five years.

### ACM SOSP

- **Docs:** [sosp.org](https://sosp.org/)
- **SDKs & repos:** The other flagship OS venue, running since 1967 — FFS (1981), LFS (1991) and GFS (2003) all appeared here
- **Downloadable / offline:** Recent proceedings open via ACM OA
- *Note:* Historically where most of the field's landmark papers appeared.

### USENIX ATC

- **Docs:** [usenix.org/conference/atc25](https://www.usenix.org/conference/atc25)
- **SDKs & repos:** Annual Technical Conference — applied systems work, storage heavy
- **Downloadable / offline:** All papers free
- *Note:* Where a lot of real production-storage engineering gets published.

### EuroSys

- **Docs:** [eurosys.org](https://www.eurosys.org/)
- **SDKs & repos:** The leading European systems conference, with strong storage tracks
- **Downloadable / offline:** Proceedings via ACM OA — partially open
- *Note:* Often more practical and implementation-focused than OSDI.

### ACM SoCC

- **Docs:** [dl.acm.org/conference/socc](https://dl.acm.org/conference/socc)
- **SDKs & repos:** ACM Symposium on Cloud Computing — where object-store and cloud-storage papers land
- **Downloadable / offline:** Via the ACM DL; ACM Open papers free, others paywalled
- *Note:* dl.acm.org 403s automated clients; loads in a browser. Check the SoCC website and USENIX mirrors for open copies first.

### USENIX HotStorage

- **Docs:** [usenix.org/conference/hotstorage25](https://www.usenix.org/conference/hotstorage25)
- **SDKs & repos:** The storage workshop attached to USENIX's calendar — short papers, position work
- **Downloadable / offline:** Open access, like all USENIX workshops
- *Note:* Where ideas appear one or two years before they become FAST papers.

### MSST

- *Note:* The Mass Storage Systems and Technologies conference — decades of storage research, originally with NASA. No stable open archive: search "MSST proceedings" by year. Name-only by design.

### The Google File System (SOSP 2003)

- **Docs:** [research.google/pubs](https://research.google/pubs/) — search the title
- **Downloadable / offline:** Free PDF via research.google or the authors' pages
- *Note:* The paper that made "build the filesystem for your workload" legitimate. Every distributed-filesystem design doc since is in dialogue with it — read it before HDFS, Ceph or SeaweedFS.

### "A Fast File System for UNIX" (SOSP 1981)

- *Note:* McKusick, Joy, Leffler and Fabry's FFS paper — the origin of the Berkeley Fast File System and of half the vocabulary (cylinder groups, inodes as objects of study). Name-only: free copies are easy to find via Papers We Love or a web search.

### "The Design and Implementation of a Log-Structured File System" (SOSP 1991)

- *Note:* Sprite LFS, by Rosenblum and Ousterhout. Name-only. Every SSD-era design and every LSM-tree engine is downstream of this one; it is the most-cited filesystem paper for a reason.

### The ZFS papers

- **Docs:** [openzfs.github.io/openzfs-docs](https://openzfs.github.io/openzfs-docs/)
- **Downloadable / offline:** OpenZFS docs + man pages
- *Note:* The original Sun white papers ("ZFS: The Last Word in File Systems" era) circulate freely; the maintained starting point is OpenZFS's own documentation, which carries the design forward with the code.

### Amazon DynamoDB & Aurora storage notes

- **Docs:** — (see the Database Systems index)
- *Note:* The Dynamo (SOSP 2007) and Aurora (SIGMOD 2017) storage papers are indexed in the [Database Systems Reference Library](./database-systems.md). This page owns filesystems and the storage stack; that page owns engines. Cross-reference when a question crosses the boundary.


---

## Video courses, channels & talks

*8 resources across 1 group.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[Kernel Recipes](https://www.youtube.com/@KernelRecipes)** — Annual Paris kernel conference: maintainer-level talks on schedulers, filesystems and mm.
- **[linux.conf.au](https://www.youtube.com/@linuxconfau)** — linux.conf.au talks: kernel, filesystems and low-level systems depth.
- **[The Linux Foundation](https://www.youtube.com/@LinuxFoundationOrg)** — The Linux Foundation channel: kernel and LF event recordings.
- **[Ceph](https://www.youtube.com/@CephStorage)** — Official Ceph channel: RADOS, RGW, CephFS talks and community calls.
- **[USENIX](https://www.youtube.com/@USENIX)** — Conference recordings for most USENIX papers — free video, the fastest route into a systems paper.
- **[InfoQ](https://www.youtube.com/@InfoQ)** — Conference keynotes and architecture talks — good for orientation, verify specifics elsewhere.
- **[Linux Plumbers Conference](https://www.youtube.com/@linuxplumbers)** — Filesystem and block-layer tracks; where btrfs, XFS and io_uring design gets argued in public.
- **[ScyllaDB](https://www.youtube.com/@ScyllaDB)** — Storage-engine performance talks, heavy on NVMe and io_uring measurement.

*Note:* Storage video is almost entirely conference footage: FAST/ATC/USENIX for research, kernel recipes and LCA for implementation.

## Conference videos, notes & archives

*8 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

FAST is the storage venue, and it is fully open; everything else comes from the kernel tracks.

### Conference channels & video archives

- **[USENIX FAST '26](https://www.usenix.org/conference/fast26)** — The storage conference: open proceedings, video for most talks.
- **[USENIX ATC '26](https://www.usenix.org/conference/atc26)** — Applied storage and filesystem papers; open.
- **[Linux Plumbers Conference](https://lpc.events/)** — Filesystem and block-layer microconferences; where io_uring and btrfs design gets decided.
- **[linux.conf.au](https://linux.conf.au/)** — Filesystem and storage tracks, recordings on the channel above.
- **[SNIA](https://www.snia.org/)** — The storage standards body: tutorial slides, webinars and the persistent-memory material nobody else publishes.
- **[OpenZFS](https://openzfs.org/)** — Project site for ZFS; summit recordings and documentation.
- **[FOSDEM video archive](https://video.fosdem.org/)** — Storage and filesystem devrooms.

### Notes, proceedings & paper-adjacent archives

- **[USENIX ;login:](https://www.usenix.org/publications/login/)** — Storage operations write-ups, easier to skim than FAST papers.

## If you only do three things

1. **Write one fio job that describes a real workload** — your database's write pattern, not "sequential 1 MB read". Then run ioping, iostat -x and blktrace while it runs and explain every number you see.
2. **Read the Ceph architecture chapter and the HDFS design page back to back.** The two canonical distributed-storage documents; together they cover CRUSH-style placement and block replication.
3. **Master one filesystem's toolbox end to end** — create it, fill it, snapshot it, corrupt a copy, recover it, then send/recv it elsewhere. Do it for ext4/XFS with LVM, and again for ZFS or Btrfs.

## Honest notes

- **Tunables are version-specific.** ext4 and XFS defaults change across kernel releases; never quote a default (journal commit interval, allocation groups) without naming the version. The kernel docs are per-release — read the one matching your kernel.
- **Btrfs's reputation lags its reality — in both directions.** RAID5/6 write-hole caveats are historical but real; correctness work has landed since. Check the current docs, not a 2018 blog post, and know which btrfs-progs/kernel pair you are running.
- **ZFS is CDDL and will not be in the mainline Linux kernel.** OpenZFS ships out-of-tree (DKMS or packaged). Interviewers ask this; "GPL and CDDL are incompatible" is the one-line answer, and FreeBSD shipping it in base is the interesting contrast.
- **docs.redhat.com hides some manuals behind login walls.** The RHEL storage guides are worth the friction, but Arch Wiki plus kernel docs cover most of the same ground openly.
- **The Linux NFS HOWTO is stale; the man pages are not.** For current NFS behaviour trust exports(5), nfs(5) and the kernel docs over the SourceForge HOWTO.
- **Ceph documentation URLs are version-scoped.** Pin to `/en/latest` (or an exact release) — bare `docs.ceph.com` paths rot, and features move between releases.
- **The Arch Wiki is community-maintained.** Excellent, but verify anything version-sensitive against the kernel or project docs; it occasionally rate-limits automated clients too.
- **Specs and implementations drift.** NVMe spec revisions, exFAT's published spec vs real SD cards, and virtio feature bits all disagree with deployed devices somewhere. When a device "violates the spec", it usually has a firmware quirk — and smartmontools/quirk tables are where it is documented.
- **iostat %util is meaningless on fast devices.** On NVMe the device is always nearly 100% "utilized" while barely loaded. Use await, queue depth and IOPS/latency distributions instead.
- **Conference URLs are year-scoped.** `usenix.org/conference/fast25` and `hotstorage25` will eventually be joined by newer years; if a link 404s, navigate from `usenix.org/conferences`.
- **Bot-blocked sources kept on purpose:** the ACM Digital Library (403 to automated clients) and docs.redhat.com (login walls) load normally in a browser. JEDEC standards are paywalled — the names and layering are what interviews need, not the PDFs.

---

## Related sections of this book

- [Database Systems Reference Library](./database-systems.md) — owns the database engines (RocksDB, LevelDB, LMDB, WiredTiger) and columnar formats (Parquet, Arrow) this index deliberately excludes
- [Operating Systems Reference Library](./operating-systems.md) — the kernel-side view: syscalls, VFS, page cache and the kernel documentation tree
- [Computer Architecture Reference Library](./computer-architecture.md) — owns CXL, NVMe-adjacent silicon and the new-interconnect story
- [Storage internals chapters](../storage/block-storage.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
