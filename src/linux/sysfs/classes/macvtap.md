# /sys/class/macvtap

| Field | Value |
|---|---|
| Subsystem | not documentable from cached sources; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | none found in tree (rg over the whole cached linux-sparse checkout: 0 occurrences of "macvtap") |
| Since | not stated in cached sources |
| Live (5.10.134 host) | class directory present, 0 devices (empty) |
| Ledger ID | SYSC-macvtap |

## What it represents

This page is deliberately minimal. The class name is real -- the 5.10.134
host registers /sys/class/macvtap -- but the cached kernel sources contain
no ABI entry, no overview text, and no driver documentation for it, and the
class is empty on this host (no macvtap interfaces are configured in the
container). Per the encyclopedia's no-fabrication rule, nothing beyond that
is asserted. Network interfaces themselves are enumerated under
/sys/class/net (see [net](./net.md)); whatever per-interface files a
macvtap device exposes would appear there, not in this empty class.

## Relationship to the device model

Nothing observable on the live host: /sys/class/macvtap exists as an empty
directory (checked read-only), so there are no device subdirectories, no
symlinks, and no attribute files to describe. No cached-tree source
describes the device-model wiring of this class; no claims are made.

## Attributes

No attribute can be cited for this class from the cached tree or observed
on the live host; the table is intentionally empty.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| (none citable) | -- | -- | -- | rg over cached linux-sparse tree: 0 matches for macvtap; live class dir empty |

## Safety and writes

There is nothing to read or write: the class directory on this host
contains zero entries. No capability requirements, write semantics, or
hazards can be documented from the available sources. If a macvtap device
is ever created on a future host, re-document this page from live
inspection and a kernel tree that contains the driver, not from memory.

## References

- Live enumeration: /sys/class/macvtap (empty, read-only, kernel 5.10.134); source-cache/live-sys/class-list.txt row "macvtap 0"
- Negative evidence: rg -i 'macvtap' over /home/z/my-project/source-cache/linux-sparse -- 0 matches (Documentation and top-level files)
- sysfs-attrs.json: no macvtap entry
- Related page: [net](./net.md); coverage: [ledger](../ledger.md)
