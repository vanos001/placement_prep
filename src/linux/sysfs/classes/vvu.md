# /sys/class/vvu

| Field | Value |
|---|---|
| Subsystem | unknown from cached sources - no subsystem documentation found (see below); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files) |
| ABI documentation | none found in tree - recursive search of `Documentation/ABI/{stable,testing,obsolete,removed}` for "vvu" returns nothing |
| Since | not stated by any cached source |
| Live (5.10.134 host) | class present and empty: live-sys/class-list.txt records `vvu 0`; /sys/class/vvu verified empty live |
| Ledger ID | SYSC-vvu |

## What it represents

A sysfs class directory whose purpose cannot be established from the cached sources. What is verifiable: the 5.10.134 host kernel registers a class named `vvu`, and it contains no devices on this host (class-list.txt count 0, empty directory live). The name suggests a virtio/vhost-user related transport class, but no cached file states this, so the claim is not made here.

## Relationship to the device model

The class is registered early enough to exist with zero devices (like backlight, bsg or iommu on this host), which in the device model means a `struct class` was registered but no device was ever added to it in this configuration. Whether member directories would be class views of virtio devices, char-device backed, or plain control objects cannot be determined from the cached tree.

## Attributes

None verifiable. No ABI file, no Documentation mention, no MAINTAINERS entry, and the live directory is empty - so there is no attribute to cite. This page is deliberately a source-limited stub: it records the existence of the class on the live host and the negative search results, and nothing more.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| (none found) | -- | -- | -- | recursive ABI search + live enumeration returned no attributes |

## Safety and writes

No documented reads or writes. If the class is device-bearing on other systems, any safety statement would be speculation; on this host there is nothing to read or write beyond the empty directory itself. The safe engineering conclusion is: do not script against /sys/class/vvu without first establishing, on the target kernel, what driver registers it and what files appear when devices bind.

## References

- Live enumeration: /sys/class/vvu empty (kernel 5.10.134); live-sys/class-list.txt row `vvu 0`
- Negative search results (cached tree): `Documentation/ABI/` for "vvu" - no match; MAINTAINERS for "vvu" - no match
- Implementation: not in cached tree
- Coverage: [ledger](../ledger.md)
