# /sys/class/mdio_bus

| Field | Value |
|---|---|
| Subsystem | MDIO bus core, drivers/net/phy/mdio_bus.c (class `mdio_bus_class` in mdio_bus_init()) |
| Config gate | builds as mdio-bus.o under CONFIG_MDIO_DEVICE in v5.10 (drivers/net/phy/Makefile); current master builds mdio_bus.o under CONFIG_PHYLIB |
| ABI documentation | Documentation/ABI/testing/sysfs-bus-mdio (What: entries dated January 2020) |
| Since | KernelVersion 5.6 (all statistics entries) |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration) |
| Ledger ID | SYSC-mdio_bus |

## What it represents

One device per MDIO bus (mii_bus), named after bus->id (mdio_bus.c dev_set_name). The class is the lookup view over MDIO buses; the same bus devices also appear under /sys/bus/mdio_bus/devices, where their PHY/MDIO children live. The ABI doc lists every attribute in both spellings, `/sys/bus/mdio_bus/devices/.../` and `/sys/class/mdio_bus/.../`.

## Relationship to the device model

The bus device is the parent of mdio_device and phy_device children bound on mdio_bus_type (drivers/net/phy/mdio_bus.c). Counters are collected in the bus `xfer` helpers, so statistics reflect the hardware bus traffic, not per-driver bookkeeping.

## Attributes (representative; source per row)

All attributes sit in a `statistics/` subdirectory (attribute group named "statistics", drivers/net/phy/mdio_bus.c).

| Attribute | R/W | Meaning (source: ABI testing/sysfs-bus-mdio) |
|---|---|---|
| `statistics/transfers` | RO | Total number of transfers for this MDIO bus |
| `statistics/errors` | RO | Total number of transfer errors for this bus |
| `statistics/writes` | RO | Total number of write transactions |
| `statistics/reads` | RO | Total number of read transactions |
| `statistics/transfers_<addr>` | RO | Transfers for one bus address |
| `statistics/errors_<addr>` | RO | Transfer errors for one bus address |
| `statistics/writes_<addr>` | RO | Write transactions for one bus address |
| `statistics/reads_<addr>` | RO | Read transactions for one bus address |

Per-address files exist for addresses 0 through 31 (attr groups generated in mdio_bus.c). Individual MDIO devices expose their own four-file `statistics/` group via mdio_bus_dev_groups.

## Safety and writes

Everything is read-only counters; no write path exists in the ABI doc or the source. Useful for spotting a wedged bus address. None observed on the read-only container host.

## References

- Documentation/ABI/testing/sysfs-bus-mdio
- drivers/net/phy/mdio_bus.c (v5.10 and master copies in source-cache; master file no longer registers the class)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [PHY drivers](../../kernel/drivers/phy.md), [net drivers](../../kernel/drivers/net-drivers.md)
