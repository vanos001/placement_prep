# T10 PI: End-to-End Data Integrity (DIF/DIX) from Host to Media

Every hop of a modern I/O path has error detection: link CRCs (SAS/FC/NVMe),
PCIe LCRC, NAND ECC, drive scrubbing, filesystem checksums. Each check only
guards its own segment. A byte flipped in a DMA buffer, a write steered to the
wrong LBA by a buggy multipath table, or a cache line lost in a drive's
volatile RAM passes every local check and still reaches media wrong. SCSI T10
Protection Information (PI, "DIF") closes that gap by attaching a small,
self-describing tag to every 512-byte logical block and requiring every node in
the path -- HBA, fabric, target, drive -- to be able to verify it. The Linux
kernel doc's framing: every node can verify the I/O and reject it if corrupted,
"allowing not only corruption prevention but also isolation of the point of
failure" [1].

## 1. The Gap: Every Link Has a Check, No Span Does

```text
   app buffer         HBA / DMA            fabric             drive RAM           NAND
+--------------+   +-------------+    +--------------+    +--------------+    +-------------+
| user page    |-->| DIX CRC     |--->| SAS/FC/NVMe  |--->| volatile     |--->| ECC-protected|
| (DRAM)       |   | engine      |    | link (CRC)   |    | write cache  |    | flash/platter|
+--------------+   +-------------+    +--------------+    +--------------+    +-------------+
       |                 |                  |                   |                  |
  FS csum at read    PI verified      per-frame CRC       PI verified        ECC fixes
  (btrfs) or never   here? (DIX)      only                here? (DIF)        bursts, not
  (ext4 default)                                                              misplaced IOs
```

| Corruption class | Typical cause | Who catches it without PI |
| --- | --- | --- |
| Bit rot in DRAM/DMA path | bad DIMM, HBA/NIC FIFO, connector | usually nobody until FS read-time check |
| Misdirected write | stale mapping entry, driver bug, fabric re-target | FS only if it checksums with block address |
| Dropped / lost write | power loss in volatile cache, queue loss | journal/DB recovery, sometimes nobody |
| Stale data served | drive cache desync after error reset | nobody below the FS |
| Torn sector | partial 512B write, no PLP | drive-dependent |

PI's three tag fields target the first three rows -- one corruption class per
field.

## 2. The Protection Information Tuple

Type-1/2/3 PI appends 8 bytes to each integrity interval (classically a
512-byte logical block; the 520-byte on-media unit is a sector with PI [1]):

```text
  0                   15 16                  31 32                                  63
  +---------------------+----------------------+-------------------------------------+
  |     GUARD TAG       |      APP TAG         |            REFERENCE TAG            |
  |  CRC-16/T10 (2 B)   |  opaque (2 B)        |  LBA / offset (4 B)                 |
  +---------------------+----------------------+-------------------------------------+
       protects data            host-owned            anchors data to a place,
       over the interval        or escape 0xFFFF      or escape 0xFFFFFFFF
```

* **Guard tag**: CRC-16, polynomial 0x8BB7, MSB-first, initial value 0x0000,
  no reflection, xorout 0 (catalogue check value for "123456789" is 0xD0DB --
  the demo below proves it). A cheaper, weaker option for the same slot is the
  Internet (1's-complement) checksum; it misses 16-bit word swaps a CRC catches.
* **App tag**: opaque to the device; host software may carry anything. Escape
  0xFFFF means "unchecked" -- the kernel defines `T10_PI_APP_ESCAPE` and
  `T10_PI_REF_ESCAPE` for exactly this [2].
* **Reference tag**: in Type 1 it carries the logical block address; a verifier
  compares it to the LBA where the block actually sits, converting "data is
  self-consistent" into "data is in the right place".

For larger intervals and fabrics, mainline also carries a 16-byte extended
tuple (`struct crc64_pi_tuple`): 8-byte guard (CRC-64/NVME), 2-byte app tag,
6-byte 48-bit reference tag, escape 0xFFFFFFFFFFFF [2]. A 16-bit guard over a
4 KiB interval has visibly worse detection odds than over 512 B -- hence the
extended formats.

## 3. DIF Types 1, 2, 3

| Type | Reference tag meaning | Checked? | Typical deployment |
| --- | --- | --- | --- |
| 0 | none (plain I/O) | n/a | unprotected volumes |
| 1 | LBA of the block | ref vs actual location | end-to-end on disks, NVMe namespaces |
| 2 | LBA + block offset seeded from a 32-byte CDB | checked | arrays with coherent command routing (READ(32)/WRITE(32)) |
| 3 | no defined meaning | not checked | intermediate caches that renumber blocks (DRAM cache) |

The kernel header comment is explicit: Type 2 "uses 32-byte commands to seed
the latter [the reference tag]", and Type 3 "defines the contents of the guard
tag only" [2]. Type 3 exists so an appliance can cache blocks in DRAM without
knowing where they will land: guard still travels with data, ref is filled in
later. One SBC-3 subtlety: for Type 1/2 the device checks the ref tag against
the addressed LBA on writes, so a host cannot lie about placement -- the drive
itself becomes an enforcement point.

## 4. DIX: Host-Side Striping of Protection Information

DIF as a media format (520-byte sectors) is only half the story. SCSI Data
Integrity Extensions (DIX) let the host generate and check PI, so corruption
between the application and the HBA is covered too. The HBA computes the guard
while DMAing data, and PI travels in a separate metadata stream, interleaved at
an agreed interval (commonly 4 KiB):

```text
  4 KiB DIX interval, PI in separate metadata pages:

  data buffer:  | 512B | 512B | 512B | 512B | 512B | 512B | 512B | 512B |
  meta buffer:  |        guard|app|ref  x 8 tuples           |  pad  |
                     HBA CRC engine writes guard per interval,
                     then both streams hit the wire as 520B sectors
```

The kernel doc describes the wire format: 8 bytes of protection information per
sector, stored in 520-byte sectors on disk, data and integrity metadata
"interleaved when transferred between the controller and target" [1].
Operationally DIX has a narrow support surface: it needs a PI-capable HBA (the
classic deployments are SAS controllers of the mpt3sas class and FC HBAs) and a
target accepting 520-byte sectors, and it does not compose with arbitrary
device-mapper stacking -- which is why most Linux deployments you will actually
meet use DIF without DIX, with the block layer doing host-side work.

## 5. Where the Check Actually Runs

| Placement | Who computes/verifies | Cost | Failure isolation |
| --- | --- | --- | --- |
| Drive/target (DIF) | drive firmware + media format | none for host | catches fabric + drive-internal |
| HBA offload (DIX) | DMA-time CRC engine | ~zero CPU | adds app->HBA span |
| Block layer software | bio-integrity walk on a work context | real CPU + memory | everything below FS, no special HBA needed |
| Filesystem | btrfs-style crc32c at read/scrub | CPU on every read | latest detection point, months late [1] |

In Linux the block layer's integrity profile is now described by queue limits,
not callbacks: `struct blk_integrity` carries `csum_type`
(`BLK_INTEGRITY_CSUM_IP/CRC/CRC64`), `interval_exp` (DIX interval as a power of
two), `tag_size`, `metadata_size`, and flags such as `BLK_INTEGRITY_REF_TAG`
and `BLK_INTEGRITY_DEVICE_CAPABLE`. Profile names appearing in
`/sys/block/<dev>/integrity/format` are generated from those fields [3]:

| Profile | Guard | Ref tag | Tuple |
| --- | --- | --- | --- |
| T10-DIF-TYPE1-CRC | CRC-16/T10 | checked vs LBA | 8 B |
| T10-DIF-TYPE3-CRC | CRC-16/T10 | unchecked | 8 B |
| T10-DIF-TYPE1-IP / -TYPE3-IP | Internet checksum | checked / unchecked | 8 B |
| EXT-DIF-TYPE1-CRC64 / -TYPE3-CRC64 | CRC-64/NVME | checked (48-bit) / unchecked | 16 B |

The walking code lives in `block/t10-pi.c`: generate or verify each tuple via
`crc_t10dif_update()` / `crc64_nvme()`, honor the escapes, seed the reference
tag from the request's start sector as
`lower_32_bits(sector >> (interval_exp - 9))` -- 48 bits for the extended tuple
[4]. Tags must be re-seeded as a request splits across non-contiguous LBAs,
which is why the walk is incremental over the bio-integrity payload (`bip`)
attached to each bio -- see the bio page for those mechanics. Two sysfs
switches, `read_verify` and `write_generate`, toggle the software path's work
per disk. Drivers historically registered `generate_fn`/`verify_fn` callbacks;
mainline replaced those (still present in v6.9) with the queue-limit profile
above, moving the work into the generic walk.

## 6. NVMe PI: Metadata in the Extended LBA

NVMe carries the same 8-byte tuple (or the 16-byte 64-bit-guard variant) as
namespace metadata, either appended to each logical block in an extended LBA
(one PRP/SGL entry covers data+metadata) or in a separate metadata buffer.
Control knobs, all verified in the mainline driver [5]:

| Field | Where | Effect |
| --- | --- | --- |
| DPS (PI type 1/2/3) | Identify Namespace | same semantics as SBC-3 types |
| PRACT | RW command | 1 = controller inserts/strips PI (remap path) |
| ELBAF guard type | NVM Command Set | 16B guard (CRC-16), 32B, 64B guard (CRC-64/NVME), qualified PI |
| PI first / offset | Identify Namespace | metadata at start vs end of the extended LBA |

Driver comments spell out two properties: "The NVMe over Fabrics specification
only supports metadata as part of the extended data LBA" [5] -- fabrics
end-to-end protection rides the extended-LBA format -- and "PI can always be
supported as we can ask the controller to simply insert/strip it" [5]: a drive
re-maps 512B+8B namespaces onto 4 KiB NAND pages transparently, no
reformatting, unlike SAS where PI adoption meant 520-byte sectors that host
software and DM layers must tolerate (see [nvme.md](../nvme.md) for the
controller-side picture).

## 7. What PI Catches -- and What It Does Not

The demo implements the Type-1 tuple exactly as specified and walks five
scenarios. The punchline is scenario 4: PI is not a lost-write detector for
same-LBA rewrites -- a stale sector is self-consistent. Closing that gap needs
an app-tag convention (scenario 5), which is what DIX stacks and some databases
do with epoch numbers.

```python
# T10 DIF in miniature: 520-byte sector = 512 B data + 8 B Protection Information
POLY = 0x8BB7

def crc16_t10dif(data, crc=0x0000):
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ POLY) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc

assert crc16_t10dif(b"123456789") == 0xD0DB   # CRC-16/T10-DIF catalogue check value

def make_pi(lba, payload, app=0x0000):
    return (crc16_t10dif(payload).to_bytes(2, "big")   # guard tag
            + app.to_bytes(2, "big")                   # app tag (host-owned)
            + lba.to_bytes(4, "big"))                  # ref tag = LBA (Type 1)

def verify(lba, sector, expect_app=None):
    payload = sector[:512]
    guard = int.from_bytes(sector[512:514], "big")
    app   = int.from_bytes(sector[514:516], "big")
    ref   = int.from_bytes(sector[516:520], "big")
    if guard != crc16_t10dif(payload):
        return "REJECT  guard mismatch -> data corrupted somewhere below the FS"
    if ref != lba:
        return "REJECT  ref tag %d != expected LBA %d -> misdirected write" % (ref, lba)
    if expect_app is not None and app != expect_app:
        return "REJECT  app tag epoch %d != expected %d -> stale/lost write" % (app, expect_app)
    return "PASS    guard ok, ref tag ok"

media = {}                                    # media[lba] -> full 520 B sector
def write(lba, payload, app=0):
    media[lba] = payload + make_pi(lba, payload, app)

write(1003, b"acct=42 balance=100" + b"\x00" * 493)
write(1007, b"acct=42 balance=0"   + b"\x00" * 495)
print("1 clean read :", verify(1003, media[1003]))

bad = bytearray(media[1003]); bad[17] ^= 0x04           # one flipped bit below drive ECC
print("2 bit rot    :", verify(1003, bytes(bad)))
print("3 misdirect  :", verify(1007, media[1003]))      # 1003's sector landed in 1007's slot

write(1003, b"acct=42 balance=500" + b"\x00" * 493)     # host THINKS this landed...
media[1003] = b"acct=42 balance=100" + b"\x00" * 493 + make_pi(1003, b"acct=42 balance=100" + b"\x00" * 493)
print("4 lost write :", verify(1003, media[1003]), "(blind spot)")

old = media[1003][:512] + make_pi(1003, media[1003][:512], app=7)   # DIX stamped epoch 7
print("5 epoch check:", verify(1003, old, expect_app=9))

data, pi = 512, 8
print("6 overhead   : %.2f%% capacity tax, %.2f%% usable, %.1f MiB PI per 1 GiB of data"
      % (100 * pi / (data + pi), 100 * data / (data + pi), 1024 * pi / data))
```

Output (real run):

```text
1 clean read : PASS    guard ok, ref tag ok
2 bit rot    : REJECT  guard mismatch -> data corrupted somewhere below the FS
3 misdirect  : REJECT  ref tag 1003 != expected LBA 1007 -> misdirected write
4 lost write : PASS    guard ok, ref tag ok (blind spot)
5 epoch check: REJECT  app tag epoch 7 != expected 9 -> stale/lost write
6 overhead   : 1.54% capacity tax, 98.46% usable, 16.0 MiB PI per 1 GiB of data
```

| Detector | Bit rot in flight | Misdirected write | Lost write | Detects at |
| --- | --- | --- | --- | --- |
| T10 DIF Type 1 | yes | yes | same-LBA: no | every hop that verifies |
| DIF + DIX epoch app tag | yes | yes | yes (epoch mismatch) | every hop |
| btrfs crc32c (default) | yes (data path only) | yes (csum keyed per block) | no | read time or scrub [6] |
| drive ECC | media-level only | no | no | at the drive |

Btrfs is the instructive contrast: the FS itself computes and verifies crc32c
(default; xxhash/sha256/blake2 since kernel 5.5 [6]) into a separate checksum
tree, with online scrub. That catches corruption from any lower layer -- but
only when the FS touches the data, and the kernel integrity doc calls that the
structural weakness: detection "could potentially be months after the data was
written. At that point the original data that the application tried to write is
most likely lost" [1]. PI moves the guarantee below the FS and evaluates it at
every hop. Neither catches scenario 4 without an epoch convention.

**Filesystem status, mid-2026**: neither ext4 nor XFS generate or verify T10 PI
themselves; PI is set up by the device/driver, checked by the block layer, and
both filesystems simply inherit (or refuse to stack) the integrity profile via
queue limits. What pulled FS attention toward PI is atomic writes: XFS gained
large atomic writes (`RWF_ATOMIC`) in the 6.16 cycle (2025), and hardware-PI
verification was floated as a building block for cheap large atomic writes --
list discussion, not a shipped ext4/XFS PI feature. dm-integrity provides
block-level checksums in its own metadata format, not T10 PI tuples. App-level
checksums (PostgreSQL page CRCs, WAL) remain complementary -- see
[storage-internals.md](./storage-internals.md).

## 8. Cost Model and When to Enable

Scenario 6 is the capacity math: 8 per 520 is a 1.54% capacity tax (16 MiB of
PI per GiB of data). The software path adds a CRC per interval on write and
read plus memory for the bio-integrity payload; CRC-64/NVME variants keep the
idea viable at 4 KiB+ intervals. Guidance:

* Misdirected-write paranoia is the strongest argument: active/active
  multipathing fabrics, or fleets burned once by a mapping bug, get an
  independent hardware-checked LBA witness on every block.
* NVMe with PRACT=1 is nearly free: the controller strips/inserts, and the
  namespace still exposes clean 512B/4KiB blocks.
* Full DIX is niche (PI-capable HBAs + 520B media that many DM/MD layers
  reject); fleets typically run DIF without DIX, or software bio-integrity on
  plain 512B/4KiB media.
* Disable `read_verify`/`write_generate` only as a measured trade-off -- off
  means "reject at the right hop" decays back into mystery corruption.

## 9. Interview Angles

* Why three tags? Guard = "the bytes are the bytes", ref = "they are where we
  put them", app = "they are from the write I think".
* Why is a dropped write to the same LBA invisible to Type-1 PI, and what
  closes the gap (app-tag epochs, DB page checksums + WAL)?
* What changes with 64-bit guard? Same design, 48-bit ref tags, CRC-64/NVME --
  the integrity interval outgrew what 16 bits can defend.

## Cross-links

* [Storage internals](./storage-internals.md) -- PI's place in the end-to-end
  checksum ladder (app -> FS -> block -> device).
* [Block layer bios](../../linux/kernel/block/bio.md) -- bio-integrity payload
  mechanics and the (older) driver registration API.
* [NVMe](../nvme.md) -- controller queues, namespaces, metadata plumbing.

## References

1. Linux kernel docs, "Data Integrity" (DIF/DIX architecture, 520-byte sectors, interleaved transfer, read-time-check critique): <https://docs.kernel.org/block/data-integrity.html>
2. Linux kernel source, `include/linux/t10-pi.h` (tuple structs, Type 0-3 enum, escapes, 48-bit ref helpers): <https://github.com/torvalds/linux/blob/master/include/linux/t10-pi.h>
3. Linux kernel source, `block/blk-integrity.c` (profile names T10-DIF-TYPE1-CRC ... EXT-DIF-TYPE3-CRC64, csum types, sysfs): <https://github.com/torvalds/linux/blob/master/block/blk-integrity.c>
4. Linux kernel source, `block/t10-pi.c` (generate/verify walk, CRC-16/T10 via `crc_t10dif_update`, CRC-64/NVME guard, ref-tag seeding): <https://github.com/torvalds/linux/blob/master/block/t10-pi.c>
5. Linux kernel source, `drivers/nvme/host/core.c` (DPS/PRACT/ELBAF handling, extended LBAs, fabrics metadata constraint): <https://github.com/torvalds/linux/blob/master/drivers/nvme/host/core.c>
6. Btrfs documentation, "Checksumming" (crc32c default, xxhash/sha256/blake2 since kernel 5.5, scrub): <https://btrfs.readthedocs.io/en/latest/Checksumming.html>

Normative SCSI source: T10 SBC-3 clause 4.22 "Protection Information" defines
the guard/app/ref semantics used here; the current SBC-3 working draft
(sbc3r36) is linked from the T10 drafts index at
<https://www.t10.org/drafts.htm>, and NVMe PI formats come from the NVM Command
Set Specification at nvmexpress.org. Both sites serve bot-check interstitials
to scripted fetches, so they were verified via the official indexes and
kernel-source cross-references rather than direct PDF pulls.
