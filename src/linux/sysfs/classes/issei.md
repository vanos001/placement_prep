# /sys/class/issei

| Field | Value |
|---|---|
| Subsystem | ISSE device class; the cached ABI file does not expand the acronym; contact Alexander Usyskin (Intel, same contact as the mei class); implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-issei` (9 What: entries) |
| Since | 7.2 (every entry: Date June 2026, KernelVersion 7.2) |
| Live (5.10.134 host) | class absent: /sys/class/issei does not exist; ABI is newer than the host kernel |
| Ledger ID | SYSC-issei |

## What it represents

A new Intel device class for probing an "ISSE" device and enumerating its
ISSE firmware clients. Contrary to the assumption that issei is old or
staging, the cached tree shows the opposite: the whole ABI file is dated
June 2026 with KernelVersion 7.2, i.e. it is one of the newest class
additions in the cached Documentation. The class holds one isseiN directory
per probed device, the ISSE firmware version, and an fw_clients tree with
one subdirectory per firmware client, keyed by client id.

## Relationship to the device model

The ABI describes a flat class view: isseiN directories created "for each
probed issei device", and fw_clients/<M> created "for each firmware client
on the probed issei device where M is the id of firmware client". The
client id is "its number in client enumeration order, starting from 1".
Everything else (bus attachment, parent device, char device) is not stated
in the cached tree; the implementation file is not cached, and no claim is
made here. The shared contact with the mei class suggests kinship, but the
cached issei text itself names no mei relationship.

## Attributes

All nine entries are read-only; the ABI marks none writable.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| fw_ver | RO | ISSE firmware version `<major>.<minor>.<milestone>.<build_no>` | always | ABI testing sysfs-class-issei, 7.2 |
| fw_clients/ | RO | directory holding all firmware clients on the device | always | ABI, 7.2 |
| fw_clients/<M>/id | RO | client id, enumeration order starting from 1 | per client | ABI, 7.2 |
| fw_clients/<M>/uuid | RO | universally unique identifier of the firmware client | per client | ABI, 7.2 |
| fw_clients/<M>/mtu | RO | maximum transmission unit of the client, in bytes | per client | ABI, 7.2 |
| fw_clients/<M>/ver | RO | version of the firmware client | per client | ABI, 7.2 |

## Safety and writes

Every documented file is read-only, so the class is safe to enumerate. No
ISSE device can exist on the 5.10.134 host (the ABI postdates that kernel),
so no live read was possible and no value example is reported. Because the
class is this new, treat the ABI file as the single authority; anything not
in it is unknown from the cached sources.

## References

- `Documentation/ABI/testing/sysfs-class-issei` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-issei
- sysfs-attrs.json entry `issei` (9 paths); live enumeration: class absent, kernel 5.10.134
- Related class page: [mei](./mei.md); coverage: [ledger](../ledger.md)
