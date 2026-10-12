# /sys/class/scsi_device

| Field | Value |
|---|---|
| Subsystem | SCSI midlayer per-device class; the only cached attributes are UFS driver additions documented in `sysfs-driver-ufs`; core implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no SCSI Kconfig is cached and the ABI entries name no config symbol (not verified); the documented attributes additionally require a UFS device (ufshcd driver) |
| ABI documentation | `Documentation/ABI/testing/sysfs-driver-ufs` (the only ABI file with `class/scsi_device` What: paths) |
| Since | February 2018 for all documented attributes (entries dated February 2018; `dyn_cap_needed` entry dated March 2018) |
| Live (5.10.134 host) | class present with 0 entries: directories exist but no SCSI device is attached in the container |
| Ledger ID | SYSC-scsi_device |

## What it represents

The per-SCSI-device (logical unit) class of the SCSI midlayer. Each entry corresponds to one LUN seen through one SCSI host/target/lun path. The cached ABI documentation does not describe the generic midlayer attributes; it documents only the UFS-specific extensions that the UFS driver hangs off `device/`: the `dyn_cap_needed` counter and a `unit_descriptor/` subdirectory mirroring the UFS 2.1 unit descriptor parameters (block geometry, provisioning, queue depth, write protection, boot LUN information). For non-UFS disks those files simply do not exist.

## Relationship to the device model

SCSI devices are the third level of the SCSI object hierarchy (host -> target -> device); the same objects are reachable under `/sys/bus/scsi/devices/H:C:I:L`, with the class directory providing a flat view. Block devices (sd, sr, st) are children of these scsi_device objects; the UFS `unit_descriptor` files live on the scsi_device side, while the UFS host controller attributes live under `/sys/bus/platform/drivers/ufshcd` per the same ABI file.

## Attributes

All documented attributes are read-only; presence is conditional on UFS hardware.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `*/device/dyn_cap_needed` | RO | amount of physical memory needed to be removed from the physical memory resources pool of the LUN | UFS devices | ABI testing `sysfs-driver-ufs` |
| `*/device/unit_descriptor/logical_block_size` | RO | size of addressable logical blocks, exponent base 2 | UFS devices | ABI testing `sysfs-driver-ufs` |
| `*/device/unit_descriptor/logical_block_count` | RO | total number of addressable logical blocks | UFS devices | ABI testing `sysfs-driver-ufs` |
| `*/device/unit_descriptor/{erase_block_size,provisioning_type,large_unit_granularity}` | RO | erase block size; thin provisioning type; LUN granularity | UFS devices | ABI testing `sysfs-driver-ufs` |
| `*/device/unit_descriptor/{lun_queue_depth,lun_write_protect,lun_memory_type,data_reliability}` | RO | queue depth; write protection status; memory type; power-failure write behavior | UFS devices | ABI testing `sysfs-driver-ufs` |
| `*/device/unit_descriptor/{boot_lun_id,psa_sensitive,context_capabilities,physical_memory_resource_count,wb_buf_alloc_units}` | RO | boot LUN info; PSA sensitivity; context capabilities; total physical memory resources; write booster buffer allocation | UFS devices | ABI testing `sysfs-driver-ufs` |

Every description defers to "UFS specifications 2.1" for the full parameter semantics.

## Safety and writes

All documented attributes are read-only, per the ABI file's repeated "The file is read only." sentence. No writes are defined for this class in the cached tree; the writable UFS controls (power levels, flags) belong to the ufshcd platform device, not the scsi_device. The generic per-device attributes of the midlayer are not covered by any cached ABI file and are deliberately not listed.

## References

- `Documentation/ABI/testing/sysfs-driver-ufs` (cached copy; 15 What: entries under `/sys/class/scsi_device`)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-ufs)
- Companion pages: [scsi_host](./scsi_host.md), [scsi_disk](./scsi_disk.md), [bsg](./bsg.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-scsi_device
