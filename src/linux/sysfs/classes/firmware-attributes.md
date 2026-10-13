# /sys/class/firmware-attributes

| Field | Value |
|---|---|
| Subsystem | firmware attributes class (BIOS configuration interface); class device drivers include Dell `dell-wmi-sysman`, Lenovo `think-lmi`, HP; implementation files not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-firmware-attributes` (11 What entries) |
| Since | 5.11 (core, authentication, pending_reboot, reset_bios: February 2021); debug_cmd 5.14; save_settings 6.6; HP SPM entries 5.18 |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/firmware-attributes |
| Ledger ID | SYSC-firmware-attributes |

## What it represents

A sysfs interface for systems-management software to read and change BIOS/firmware configuration options on supported systems (the ABI was introduced by Dell, with documented vendor extensions for HP and Lenovo). Under a driver instance directory sit `attributes/*` (typed settings), an `authentication/` subtree (BIOS admin, power-on and vendor-specific credentials) and per-vendor extras.

## Relationship to the device model

The class path is `/sys/class/firmware-attributes/<driver>/...` where the top directory is the registering driver instance (the ABI shows `thinklmi` in examples). Attribute directories are dynamic per BIOS setting; which files exist inside depends on the attribute's `type` (mandatory) - `enumeration`, `integer`, `string`, plus HP's `ordered-list` - and on vendor extensions. Password changes and pending-reboot transitions emit KOBJ_CHANGE uevents for management daemons.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `attributes/*/type` | RO | `enumeration`/`integer`/`string`/HP `ordered-list`; mandatory | per attribute | ABI, 5.11 |
| `attributes/*/current_value` | RW | current setting; mandatory | per attribute | ABI, 5.11 |
| `attributes/*/default_value`, `display_name`, `display_name_language_code` | RO | default and localized name | optional | ABI, 5.11 |
| `attributes/*/possible_values` | RO | semicolon-separated valid values | `enumeration` type | ABI, 5.11 |
| `attributes/*/min_value`, `max_value`, `scalar_increment` | RO | integer bounds and step | `integer` type | ABI, 5.11 |
| `attributes/*/max_length`, `min_length` | RO | string length bounds | `string` type | ABI, 5.11 |
| `attributes/*/dell_modifier`, `dell_value_modifier` | RO | dependency rules like `[SuppressIfNot:AutoOn=SelectDays]` | Dell systems | ABI, 5.11 |
| `authentication/<mech>/is_enabled`, `role`, `mechanism` | RO | 0/1; role `bios-admin`, `power-on`, `system-mgmt`, `HDD`, `NVMe`; `password` or `certificate` | auth object | ABI, 5.11 |
| `authentication/<mech>/current_password`, `new_password` | WO | session password entry and reset | password mechanism | ABI, 5.11 |
| `authentication/<mech>/certificate`, `signature`, `save_signature`, `certificate_thumbprint`, `certificate_to_password` | mixed | BASE64 certificate material for signing-server auth | certificate mechanism | ABI, 5.11 |
| `authentication/SPM/kek`, `SPM/sk` | WO | x509 DER kek <= 4095 bytes; RSA modulus sk | HP SPM | ABI, 5.18 |
| `authentication/SPM/status` | RO | JSON state report | HP SPM | ABI, 5.18 |
| `attributes/pending_reboot` | RO | 1 if a reboot is needed to apply changes; emits KOBJ_CHANGE | driver | ABI, 5.11 |
| `attributes/reset_bios` | RW | `builtinsafe`, `lastknowngood`, `factory`, `custom` (current in brackets) | driver | ABI, 5.11 |
| `attributes/save_settings` | RW | `single`/`bulk`/`save` (Lenovo 48-save limit workaround) | Lenovo | ABI, 6.6 |
| `attributes/debug_cmd` | WO | vendor-debug commands to BIOS | Lenovo | ABI, 5.14 |
| `attributes/Sure_Start/audit_log_entries`, `audit_log_entry_count` | RO | BIOS audit log contents; count,size,max triple | HP | ABI, 5.18 |

## Safety and writes

This is the machine's firmware policy surface. Writes to `current_value` change BIOS settings stored in NVRAM; `reset_bios` can wipe configuration to factory defaults; `debug_cmd` sends raw debug commands to the BIOS (ABI: use only when the BIOS vendor recommends it). Password handling is session-based by design: write `current_password`, perform changes, then clear it; when an admin password is set, attribute writes need that validation. Certificate changes require a reboot to take effect. Lenovo's `save_settings` bulk mode locks further attribute writes after `save` (permissions error) to protect the 48-save hardware limit.

## References

- `Documentation/ABI/testing/sysfs-class-firmware-attributes` (cached copy; 495 lines, 11 What entries)
- Implementation (`drivers/platform/x86` firmware-attributes class and vendor drivers): not in cached tree
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/firmware-attributes absent (kernel 5.10.134, read-only enumeration)
