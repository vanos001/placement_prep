# /sys/class/mem

| Field | Value |
|---|---|
| Subsystem | Character device core; drivers/char/mem.c (mem_class, chr_dev_init) |
| Config gate | mem.o is obj-y in drivers/char/Makefile; per-minor gates: CONFIG_DEVMEM (mem), CONFIG_DEVPORT (port), CONFIG_PRINTK (kmsg) |
| ABI documentation | None (no What: entries anywhere in Documentation/ABI for /sys/class/mem) |
| Since | Source-established; the fixed minor map in mem.c devlist[] is the contract (MEM_MAJOR 1, include/uapi/linux/major.h) |
| Live (5.10.134 host) | 8 entries: full, kmsg, mem, null, port, random, urandom, zero |
| Ledger ID | SYSC-mem |

## What it represents

The classic memory pseudo-devices: /dev/null, /dev/zero, /dev/full,
/dev/random, /dev/urandom, /dev/kmsg, /dev/mem and /dev/port. chr_dev_init()
(fs_initcall) registers MEM_MAJOR 1 and creates one class device per entry of
the devlist[] table in mem.c, in the fixed minor slots shown below. The class
directory exists as the sysfs view of those devices; the actual read/write
semantics live in the file_operations referenced per minor (null_fops,
zero_fops, kmsg_fops, mem_fops, random_fops and so on), not in sysfs
attributes. There are no tunables in this class at all.

## Relationship to the device model

mem_class has a devnode callback that applies the per-minor mode from
devlist[] when devtmpfs creates the /dev node. The devlist in master marks
null, zero, full, random and urandom 0666, kmsg 0644, and mem and port 0
(root-only by default). Minor 4 (port) is skipped entirely when
!arch_has_dev_port(). The /dev nodes are the consumed interface; sysfs
provides dev, uevent and the standard links, and /sys/dev/char/<major:minor>
is the lookup twin. The misc class (major 10) is a different mechanism
(dynamically registered drivers), documented on its own page.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| null/dev | RO | 1:3 | live check (5.10.134); mem.c devlist[3] |
| zero/dev | RO | 1:5 | live check; mem.c devlist[5] |
| full/dev | RO | 1:7 | live check; mem.c devlist[7] |
| random/dev | RO | 1:8 | live check; mem.c devlist[8] |
| urandom/dev | RO | 1:9 | live check; mem.c devlist[9] |
| mem/dev | RO | 1:1 (CONFIG_DEVMEM) | live check; mem.c devlist[1] |
| port/dev | RO | 1:4 (CONFIG_DEVPORT, arch_has_dev_port) | live check; mem.c devlist[4] |
| kmsg/dev | RO | 1:11 (CONFIG_PRINTK), node mode 0644 | live check; mem.c devlist[11] |
| uevent | RO/RW | standard uevent file | device core |

Every row above is both a kernel-source fact (devlist[] order and majors) and
a live-verified value on the 5.10.134 host; the class adds no attributes of
its own beyond the device core set.

## Safety and writes

The class directory itself is inert: reads and writes go to the character
devices, not to sysfs files. The danger sits in the /dev twins: /dev/mem and
/dev/port give physical memory and I/O port access (CAP_SYS_RAWIO territory),
and /dev/kmsg accepts lines into the kernel log. None of that is reachable by
writing anything under /sys/class/mem. When auditing a host, compare the
class population against devlist[]: minors that are missing here but present
in /dev indicate devtmpfs caching from a differently configured kernel.

## References

- drivers/char/mem.c, include/uapi/linux/major.h, fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/mem (dev values per entry, read-only, kernel 5.10.134)
- Documentation/ABI: confirmed absence (grep for /sys/class/mem returns nothing)
- Sibling pages: [misc](./misc.md), [cpuid](./cpuid.md), [msr](./msr.md); coverage: [ledger](../ledger.md)
