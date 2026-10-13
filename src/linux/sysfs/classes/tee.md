# /sys/class/tee

| Field | Value |
|---|---|
| Subsystem | TEE (Trusted Execution Environment) subsystem, `drivers/tee/` (core builds as `tee.o`: `obj-$(CONFIG_TEE) += tee.o`, torvalds/linux master) |
| Config gate | `CONFIG_TEE` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-tee` (2 What entries) |
| Since | 6.10 (`rpmb_routing_model`); 6.19 (`revision`) |
| Live (5.10.134 host) | class absent: no `/sys/class/tee` directory, no TEE registered |
| Ledger ID | SYSC-tee |

## What it represents

One directory per TEE instance, named `tee{,priv}X` -- i.e. `tee0` /
`teepriv0` device pairs (client and private/supplicant sides). The class is
thin by design: the real interface is the `/dev/tee*` ioctl set (host
header `/usr/include/linux/tee.h` defines `TEE_IOC_VERSION`,
`TEE_IOC_SHM_ALLOC`, `TEE_IOC_SHM_REGISTER`, `TEE_IOC_OPEN_SESSION`,
`TEE_IOC_INVOKE`, `TEE_IOC_CANCEL`, `TEE_IOC_CLOSE_SESSION`,
`TEE_IOC_SUPPL_RECV`, `TEE_IOC_SUPPL_SEND`, plus the
`TEE_IOCTL_LOGIN_*` client credentials). The two sysfs attributes serve
boot-time decisions: `rpmb_routing_model` exists explicitly so systemd can
decide whether tee-supplicant is needed in the initramfs (value "user"
routes RPMB frames through userspace; "kernel" routes through the kernel
RPMB subsystem; absence means assume "user"). `revision` (6.19) is a
diagnostics-only driver-reported revision string.

## Relationship to the device model

`/sys/class/tee/tee{,priv}X` is a class view over TEE devices under
`/sys/devices/...` (OP-TEE firmware nodes, or virtual TEEs). There is no
tee bus; the client API is the char device. The revision attribute's ABI
text draws the boundary explicitly: use `TEE_IOC_VERSION` for capability
and compatibility checks, never `revision`. Related confidential-computing
machinery that reuses TEE concepts is the TEE Security Manager: sibling
page [tsm](./tsm.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `tee{,priv}X/rpmb_routing_model` | RO | `user` or `kernel`; absent means assume `user` | always per ABI (6.10) | ABI testing `sysfs-class-tee` |
| `tee{,priv}X/revision` | RO | driver-reported revision string; "for diagnostics only" | always per ABI (6.19) | ABI testing `sysfs-class-tee` |

## Safety and writes

Both documented attributes are read-only and safe to read. All TEE state
changes -- sessions, shared-memory registration, invocation of trusted
applications -- happen through the ioctl interface on `/dev/teeX`, not
through sysfs; sysfs exposes nothing writable. The `rpmb_routing_model`
read has a security-adjacent consumer: deciding whether early userspace
must run tee-supplicant, with the ABI prescribing the absent-file default
("user") to stay conservative.

## References

- `Documentation/ABI/testing/sysfs-class-tee` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-tee)
- `/usr/include/linux/tee.h` (host header: `TEE_IOC_*`, `TEE_IOCTL_LOGIN_*`)
- `drivers/tee/Makefile` (torvalds/linux master; fetched obj line)
- `Documentation/driver-api/tee.rst` exists upstream (probed, not in sparse cache)
- Ledger row SYSC-tee; `/sys/class/tee` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [tsm](./tsm.md)
