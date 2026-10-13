# /sys/class/cxl

| Field | Value |
|---|---|
| Subsystem | IBM CAPI (Coherent Accelerator) AFU driver for POWER; userspace library https://github.com/ibm-capi/libcxl; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/removed/sysfs-class-cxl` -- "The cxl driver was removed in 6.15"; all attributes dated September 2014 - May 2018, "removed February 2025" |
| Since | September 2014 (first entries); driver removed in 6.15, ABI moved to removed/ February 2025 |
| Live (5.10.134 host) | class absent: /sys/class/cxl does not exist in this container |
| Ledger ID | SYSC-cxl |

## What it represents

The sysfs view of CAPI-attached accelerator AFUs (accelerator function
units) on POWER hardware, as used through libcxl. The removed ABI retains
the full layout: slave contexts (/sys/class/cxl/afu0.0s), master contexts
(afu0.0m), AFU configuration records (cr<config num>), and card directories
(card0). Unrelated to the newer CXL.mem subsystem under /sys/bus/cxl
(`Documentation/ABI/testing/sysfs-bus-cxl`, cached separately); the shared
three-letter name is the only overlap.

## Relationship to the device model

The removed ABI's preamble records the device-model trick worth remembering:
"attributes that are shared between devices are stored in the directory
pointed to by the symlink device/. For example, the real path of the
attribute /sys/class/cxl/afu0.0s/irqs_max is
/sys/class/cxl/afu0.0s/device/irqs_max, i.e. /sys/class/cxl/afu0.0/irqs_max."
So slave-context directories were views whose shared attributes physically
lived on the parent AFU device. The ABI also notes AFU configuration records
"will show up here (if present)" as PCIe-like config records under cr<N>.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| <afu>/afu_err_buf | RO | AFU error buffer, application-specific contents | slave contexts | ABI removed sysfs-class-cxl |
| <afu>/irqs_max | RW | decimal cap on userspace-requestable interrupts (e.g. 2037 default); must be >= irqs_min | slave contexts | ABI removed |
| <afu>/irqs_min | RO | minimum interrupts for CAPI_START_WORK; omittable via num_interrupts field | slave contexts | ABI removed |
| <afu>/mmio_size | RO | decimal size of MMIO space userspace may mmap | slave contexts | ABI removed |
| <afu>/modes_supported | RO | one per line: "dedicated_process", "afu_directed" | slave contexts | ABI removed |
| <afu>/mode | RW | current AFU mode from modes_supported; writable only with no attached user contexts | slave contexts | ABI removed |
| <afu>/prefault_mode | RW | none / work_element_descriptor / all; hashed page table MMU only | slave contexts | ABI removed |
| <afu>/reset | WO | write 1 to reset AFU when no contexts active | slave contexts | ABI removed |
| <afu>/api_version, api_version_compatible | RO | decimal kernel/user API version and lowest supported version | slave contexts | ABI removed |
| <afu>/cr<config num>/{vendor,device,class,config} | RO | hex IDs of the PCIe-like AFU config record; config is raw binary | if records present | ABI removed |
| <afu>m/mmio_size, pp_mmio_len, pp_mmio_off | RO | master-context MMIO size, per-process MMIO length and offset | master contexts | ABI removed |
| <card>/{caia_version,psl_revision,base_image,image_loaded,psl_timebase_synced,tunneled_ops_supported} | RO | card identity and capability strings/flags | card dirs | ABI removed |
| <card>/load_image_on_perst | RW | none/user/factory: what PERST loads | card dirs | ABI removed |
| <card>/perst_reloads_same_image | RW | 0/1 trust flag for PERST reloads | card dirs | ABI removed |
| <card>/reset | WO | write 1 = PERST (no active contexts); write -1 = force PERST | card dirs | ABI removed |

## Safety and writes

Moot in practice: the interface no longer exists in kernels since 6.15 and
the whole class is historical. When it lived, writes reset hardware, changed
AFU modes, and forced card PERST (-1 bypassing the active-context check).
Do not confuse this removed class with /sys/bus/cxl.

## References

- `Documentation/ABI/removed/sysfs-class-cxl` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/removed/sysfs-class-cxl
- sysfs-attrs.json entry `cxl` (23 paths); live enumeration: class absent, kernel 5.10.134
- Related cached file: `Documentation/ABI/testing/sysfs-bus-cxl` (different subsystem); coverage: [ledger](../ledger.md)
