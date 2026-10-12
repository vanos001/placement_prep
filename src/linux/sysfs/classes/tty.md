# /sys/class/tty

| Field | Value |
|---|---|
| Subsystem | TTY core; drivers/tty/tty_io.c (tty_class, console/active), drivers/tty/serial/serial_core.c (ttyS<x> serial attributes) |
| Config gate | CONFIG_TTY (drivers/tty/Makefile obj-$(CONFIG_TTY) += tty_io.o); serial group: CONFIG_SERIAL_CORE; tty0-63: CONFIG_VT |
| ABI documentation | Documentation/ABI/testing/sysfs-tty (17 What: entries) |
| Since | November 2010 (console/active, tty<x>/active); October 2012 (TIOCGSERIAL group); February 2020 (ttyS<x>/console) |
| Live (5.10.134 host) | 70 entries: console, ptmx, tty, ttyprintk, tty0-63, ttyS0-1; console/active = ttyS1; ttyS0 uartclk = 1843200, type = 4 |
| Ledger ID | SYSC-tty |

## What it represents

Every tty device the core knows about: the controlling terminals and their
helpers (tty at 5:0, console at 5:1, ptmx at 5:2), the 64 virtual consoles
tty0-63 registered by the VT driver, and serial ports ttyS<x> registered by
serial_core. The class mixes two very different populations: entries with
device-specific attributes (serial ports expose the TIOCGSERIAL state) and
bare class entries (tty, ptmx, ttyprintk) that carry only the core files dev,
uevent, power/, subsystem. Note the class covers console state but there is
no /sys/class/serial: serial ports surface only through this class.

## Relationship to the device model

tty_class is registered in tty_io.c (postcore_initcall) with a devnode
callback that marks the tty (5:0) and ptmx (5:2) nodes 0666 for devtmpfs.
tty_init() creates tty and console directly; console is created with
cons_dev_groups so it carries the active attribute. The VT console driver
(drivers/tty/vt/vt.c, CONFIG_VT) registers tty0 with vt_dev_groups (also
carrying active) and tty1-63 via tty_register_driver. serial_core attaches
tty_dev_attrs[] (14 attributes) to each ttyS<x>. The active files support
poll() to watch virtual-console switches (ABI, November 2010).

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| console/active | RO | configured console list, active device last; live: ttyS1; pollable | ABI, November 2010; tty_io.c DEVICE_ATTR(active) |
| tty<x>/active | RO | current active virtual console; live tty0/active = tty1 | ABI, November 2010 |
| ttyS<x>/uartclk | RO | uartclk = 16 x baud_base; live ttyS0 = 1843200 | ABI, September 2012 |
| ttyS<x>/type | RO | port type number; live ttyS0 = 4 = PORT_16550A (include/uapi/linux/serial.h) | ABI, October 2012 |
| ttyS<x>/line | RO | tty line number | ABI, October 2012 |
| ttyS<x>/port | RO | port I/O address | ABI, October 2012 |
| ttyS<x>/irq | RO | interrupt number | ABI, October 2012 |
| ttyS<x>/flags, xmit_fifo_size, custom_divisor | RO | port state fields | ABI, October 2012 |
| ttyS<x>/close_delay, closing_wait | RO | hundredths of a second; live close_delay = 50 | ABI, October 2012 |
| ttyS<x>/io_type, iomem_base, iomem_reg_shift | RO | register access shape | ABI, October 2012 |
| ttyS<x>/rx_trig_bytes | RW | RX FIFO trigger; 16550A allows 1/4/8/14, nearest lower wins | ABI, May 2014 |
| ttyS<x>/console | RW | boolean: attach/detach port as kernel console | ABI, February 2020 |
| dev | RO | major:minor; live console 5:1, ptmx 5:2 | tty_io.c device_create calls |
| (serial group source) | 13 RO + 1 RW | exposed "via sysfs rather than via ioctls" per the ABI file | serial_core.c tty_dev_attrs[] |

All 14 serial attributes are read-only except console. The ABI file documents
17 paths; the group table above covers them.

## Safety and writes

Reads are safe. Writes are console-relevant: ttyS<x>/console detaches or
re-attaches a kernel console (February 2020) and rx_trig_bytes retunes the
UART FIFO, so both change where kernel messages and serial input flow. The
active files are read-only but pollable, which is what exit-on-console-switch
daemons use. Entries without attributes (ptmx, tty) are not tunable here;
their behavior is ioctl/termios territory, not sysfs.

## References

- Documentation/ABI/testing/sysfs-tty (cached at source-cache/linux-sparse)
- drivers/tty/tty_io.c, drivers/tty/serial/serial_core.c, drivers/tty/vt/vt.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- include/uapi/linux/serial.h (PORT_16550A = 4)
- Live enumeration /sys/class/tty incl. console/active, ttyS0/* (read-only, kernel 5.10.134)
- Sibling pages: [net](./net.md), [mem](./mem.md); coverage: [ledger](../ledger.md)
