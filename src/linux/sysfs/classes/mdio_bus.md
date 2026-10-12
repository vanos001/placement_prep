# /sys/class/mdio_bus

| Field | Value |
|---|---|
| Subsystem | MDIO bus core, drivers/net/phy/mdio_bus.c; the cached v5.10 copy (`mdio_bus_510.c`) defines `struct class mdio_bus_class` named "mdio_bus" with the `statistics` attribute group; current master builds `mdio_bus.o` under the fetched `Makefile` |
| Config gate | v5.10: `CONFIG_MDIO_DEVICE` (fetched `mdio_bus_510_Makefile`: `obj-$(CONFIG_MDIO_DEVICE) += mdio-bus.o`; `phy-Kconfig-510` line 19 `select MDIO_DEVICE`); current master: `CONFIG_PHYLIB` (fetched `Makefile`: `obj-$(CONFIG_PHYLIB) += mdio_bus.o`) |
| ABI documentation | `Documentation/ABI/testing/sysfs-bus-mdio` (statistics; KernelVersion 5.6) and `Documentation/ABI/testing/sysfs-class-net-phydev` (per-PHY-device attributes, documented with `/sys/class/mdio_bus/<bus>/<device>/` What: paths) |
| Since | 5.6 for the bus statistics group; per-PHY attributes 3.8-6.17 (see table) |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration; no MDIO bus on the container host) |
| Ledger ID | SYSC-mdio_bus |

## What it represents

One device per MDIO bus (mii_bus), named after the bus id. The class is the lookup view over MDIO bus devices; the same devices also appear under `/sys/bus/mdio_bus/devices`, and their PHY/MDIO children are matched on `mdio_bus_type`. The v5.10 source registers the class with a per-bus `statistics/` attribute group, counters accumulated by the bus transfer helpers -- so the numbers reflect real hardware bus traffic.

## Relationship to the device model

Bus devices carry `mdio_bus_groups` (the `statistics/` group per `mdio_bus_510.c`); MDIO devices and PHY devices attached to a bus carry their own four-file statistics group (`mdio_bus_dev_groups`) and the phydev attributes below. `of_mdio_find_bus()` in the same file looks buses up through this class by name and OF node, which is why the class exists: cross-driver bus discovery.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../statistics/transfers` | RO | total transfers for the bus | always | ABI testing `sysfs-bus-mdio` (5.6); `mdio_bus_510.c` |
| `.../statistics/{errors,writes,reads}` | RO | transfer errors / write transactions / read transactions for the bus | always | ABI testing `sysfs-bus-mdio` |
| `.../statistics/{transfers,errors,writes,reads}_<addr>` | RO | same four counters per bus address (addresses 0-31, generated groups) | always | ABI testing `sysfs-bus-mdio`; `mdio_bus_510.c` |
| `<bus>/<device>/phy_id` | RO | 32-bit PHY identifier from enumeration, hexadecimal | PHY devices, 3.8 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/phy_interface` | RO | interface mode string (mii, gmii, sgmii, rgmii-*, 1000base-x, ...) | PHY devices, 3.15 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/phy_has_fixups` | RO | boolean: any fixup workaround ran | PHY devices, 3.15 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/attached_dev` | RO | symlink to the attached network device | PHY devices, 4.13 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/phy_standalone` | RO | boolean: PHYLINK standalone mode; created only when true | PHYLINK-only PHYs, 5.3 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/phy_dev_flags` | RO | 32-bit hex mask of consumer-passed config bits (debug aid, unstable placement) | PHY devices, 5.13 | ABI testing `sysfs-class-net-phydev` |
| `<bus>/<device>/c45_phy_ids/mmd<n>_device_id` | RO | per-MMD 32-bit C45 identifiers, hexadecimal | C45 PHYs, 6.17 | ABI testing `sysfs-class-net-phydev` |

## Safety and writes

Everything documented is a read-only counter or identifier; no write path exists in either ABI file or the cached source. Useful for spotting a wedged bus address: compare `statistics/errors_<addr>` against `transfers_<addr>`.

## References

- `Documentation/ABI/testing/sysfs-bus-mdio`, `Documentation/ABI/testing/sysfs-class-net-phydev` (cached copies)
- [sysfs-bus-mdio online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-bus-mdio), [sysfs-class-net-phydev online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-net-phydev)
- Fetched: `mdio_bus.c`, `mdio_bus_510.c`, `mdio_bus_510_Makefile`, `Makefile`, `phy-Kconfig-510`
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-mdio_bus
