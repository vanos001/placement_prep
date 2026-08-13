# Linux Driver Model

The **Linux driver model** provides a unified framework for representing
devices, drivers, and buses in the kernel. It standardizes device
discovery, driver binding, power management, and user-space visibility
through **sysfs**. Every device and driver in the kernel participates
in this model.

---

## 1. Core Concepts

The driver model is built on three pillars:

```mermaid
graph TD
    BUS[bus_type] -->|matches| DRIVER[device_driver]
    BUS -->|enumerates| DEVICE[device]
    DRIVER -->|binds to| DEVICE
    DEVICE -->|registers with| BUS
    DRIVER -->|registers with| BUS
```

| Structure | Role |
|---|---|
| `struct device` | Represents a physical or virtual device |
| `struct device_driver` | Represents a driver that handles devices |
| `struct bus_type` | Represents a bus (PCI, USB, platform, etc.) |

### The Binding Process

1. A **bus** discovers a device (e.g., PCI enumeration).
2. The bus creates a `struct device` and registers it.
3. The kernel iterates registered drivers for that bus.
4. If a driver's `probe()` matches the device, it is **bound**.

---

## 2. Kobject — The Foundation

Every object in the driver model (`device`, `driver`, `bus`, `class`)
contains a **`kobject`** — the base type that provides:

- **Reference counting** (`kref`)
- **sysfs representation** (directory under `/sys/`)
- **Parent-child relationships** (hierarchy)
- **Release mechanism** (cleanup when refcount hits zero)

```c
struct kobject {
    const char      *name;
    struct kref     kref;
    struct list_head entry;
    struct kobject  *parent;
    struct kset     *kset;
    struct kobj_type *ktype;
    struct kernfs_node *sd;   /* sysfs entry */
};
```

### `kset` — Collections of Kobjects

A `kset` groups related kobjects together and provides a shared
`kobject` as their parent:

```c
struct bus_type pci_bus_type = {
    .name = "pci",
    .dev_groups = pci_dev_groups,
    .drv_groups = pci_drv_groups,
    .match = pci_bus_match,
    .probe = pci_device_probe,
    /* ... */
};
```

The bus's `kset` creates `/sys/bus/pci/` and all PCI devices appear
under `/sys/bus/pci/devices/`.

### `kobj_type` — Behavior

Defines how a kobject behaves (sysfs show/store, release):

```c
struct kobj_type {
    void (*release)(struct kobject *kobj);
    const struct sysfs_ops *sysfs_ops;
    struct attribute **default_attrs;
};
```

---

## 3. `struct device`

The `device` structure is the kernel's universal representation of a
hardware or virtual device:

```c
struct device {
    struct kobject          kobj;
    struct device           *parent;        /* parent device */
    const char              *init_name;     /* initial name */
    const struct device_type *type;         /* device class type */
    struct bus_type         *bus;           /* bus it's on */
    struct device_driver    *driver;        /* bound driver */
    void                    *platform_data; /* driver-private */
    void                    *driver_data;   /* driver-private (managed) */
    struct dev_pm_info      power;          /* power management */
    struct device_node      *of_node;       /* device tree node */
    /* ... */
};
```

### Key Relationships

```mermaid
graph TD
    DEV[device] -->|parent| PARENT[device]
    DEV -->|bus| BUS[bus_type]
    DEV -->|driver| DRV[device_driver]
    DEV -->|of_node| DT[device_node]
    DEV -->|class| CLASS[class]
    DEV -->|kobj| KOBJ[kobject → sysfs]
```

---

## 4. `struct device_driver`

```c
struct device_driver {
    const char              *name;
    struct bus_type         *bus;
    struct module           *owner;
    const struct of_device_id *of_match_table;
    const struct acpi_device_id *acpi_match_table;
    int (*probe)(struct device *dev);
    void (*remove)(struct device *dev);
    int (*suspend)(struct device *dev, pm_message_t state);
    int (*resume)(struct device *dev);
    /* ... */
};
```

### The `probe` Function

`probe()` is called when a device is matched to a driver. It is the
driver's initialization point:

```c
static int my_probe(struct device *dev)
{
    struct my_data *data;

    data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    /* Initialize hardware */
    /* Register with subsystem (e.g., block, net, char) */

    dev_set_drvdata(dev, data);
    return 0;
}
```

### The `remove` Function

Called when the device is unbound or hot-unplugged:

```c
static void my_remove(struct device *dev)
{
    /* Unregister from subsystem */
    /* Release hardware resources */
}
```

---

## 5. Bus Types

Each bus (PCI, USB, I2C, SPI, platform, etc.) implements `bus_type`:

```c
struct bus_type {
    const char *name;
    int (*match)(struct device *dev, struct device_driver *drv);
    int (*probe)(struct device *dev);
    void (*remove)(struct device *dev);
    int (*uevent)(struct device *dev, struct kobj_uevent_env *env);
    const struct attribute_group **dev_groups;
    const struct attribute_group **drv_groups;
    /* ... */
};
```

### Common Bus Types

| Bus | Use Case | sysfs Path |
|---|---|---|
| `pci_bus_type` | PCI/PCIe devices | `/sys/bus/pci/` |
| `usb_bus_type` | USB devices | `/sys/bus/usb/` |
| `platform_bus_type` | SoC integrated peripherals | `/sys/bus/platform/` |
| `i2c_bus_type` | I2C devices | `/sys/bus/i2c/` |
| `spi_bus_type` | SPI devices | `/sys/bus/spi/` |
| `virtio_bus` | Virtio paravirtualized devices | `/sys/bus/virtio/` |
| `amba_bus` | ARM AMBA devices | `/sys/bus/amba/` |

### Match Function

The bus's `match()` determines if a driver can handle a device:

```c
static int pci_bus_match(struct device *dev, struct device_driver *drv)
{
    struct pci_dev *pci_dev = to_pci_dev(dev);
    struct pci_driver *pci_drv = to_pci_driver(drv);

    /* Match by vendor/device ID, class, subvendor, etc. */
    const struct pci_device_id *id;
    id = pci_match_id(pci_drv->id_table, pci_dev);
    return id != NULL;
}
```

---

## 6. sysfs Integration

Every `device`, `driver`, and `bus` with a `kobject` appears in sysfs:

```bash
$ ls /sys/bus/pci/devices/0000:00:1f.2/
boot_vga   class   config   device   driver_override
enable     irq     local_cpus  modalias  msi_bus
numa_node  power/  remove   rescan   resource
resource0  rom     subsystem  subsystem_vendor  uevent
vendor
```

### Device Attributes

Drivers can expose attributes via `dev_attr`:

```c
static ssize_t my_status_show(struct device *dev,
                              struct device_attribute *attr, char *buf)
{
    struct my_data *data = dev_get_drvdata(dev);
    return sysfs_emit(buf, "%d\n", data->status);
}
static DEVICE_ATTR_RO(my_status);

/* Register in probe: */
device_create_file(dev, &dev_attr_my_status);
```

This creates `/sys/bus/.../my_status` that user space can read.

### Uevents

When a device is added or removed, the kernel sends a **uevent** to
user space (udev/mdev). The `uevent` callback can add environment
variables:

```c
static int my_uevent(struct device *dev, struct kobj_uevent_env *env)
{
    add_uevent_var(env, "MY_VAR=value");
    return 0;
}
```

---

## 7. Platform Devices

For SoC peripherals that aren't discoverable (no enumeration protocol),
the kernel uses **platform devices**:

```c
static struct platform_device my_pdev = {
    .name = "my-device",
    .id = -1,
    .dev.platform_data = &my_pdata,
};

platform_device_register(&my_pdev);
```

Platform drivers match by name or device tree:

```c
static struct platform_driver my_pdrv = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my-device",
        .of_match_table = my_of_match,
    },
};

module_platform_driver(my_pdrv);
```

See [Device Tree](device-tree.md) for matching via device tree.

---

## 8. Hotplug

The driver model supports device hotplug (add/remove at runtime):

```mermaid
sequenceDiagram
    participant HW as Hardware Event
    participant BUS as Bus Driver
    participant DM as Driver Model
    participant DRV as Device Driver
    participant US as udev/mdev

    HW->>BUS: device appeared
    BUS->>DM: device_register()
    DM->>DM: bus->match()
    DM->>DRV: driver->probe()
    DRV->>DM: device initialized
    DM->>US: KOBJ_ADD uevent
    US->>US: create /dev node, load firmware
```

For USB:

```c
/* USB device plugged in */
usb_hub_port_connect()
  → usb_new_device()
    → device_add()
      → bus_for_each_drv() → match → probe
      → kobject_uevent(KOBJ_ADD)
```

---

## 9. Device Managed Resources (`devres`)

The kernel provides **managed resources** that are automatically freed
when the device is removed:

```c
/* Automatically freed on remove */
void *buf = devm_kmalloc(dev, size, GFP_KERNEL);
struct clk *clk = devm_clk_get(dev, "bus_clk");
int irq = devm_request_irq(dev, irq, handler, 0, "my", data);
void __iomem *base = devm_ioremap_resource(dev, res);
```

`devres` simplifies error handling in `probe()` — you don't need to
unwind allocations on failure.

---

## 10. Device Lifecycle Summary

```mermaid
stateDiagram-v2
    [*] --> Registered: device_add / device_register
    Registered --> Matched: bus->match()
    Matched --> Probed: driver->probe()
    Probed --> Active: device operational
    Active --> Suspended: system suspend
    Suspended --> Active: system resume
    Active --> Removed: device_del
    Removed --> [*]: cleanup
```

---

## Module Entry and Exit Points

From the kernel documentation at `docs.kernel.org/driver-api/basics.html`:

### module_init and module_exit

```c
module_init(x)  /* driver initialization entry point */
module_exit(x)  /* driver exit entry point */
```

`module_init()` will either be called during `do_initcalls()` (if builtin) or at module insertion time (if a module). There can only be one per module.

`module_exit()` wraps the driver clean-up code with `cleanup_module()` when used with `rmmod`. If the driver is statically compiled into the kernel, `module_exit()` has no effect.

### Module Reference Counting

```c
bool try_module_get(struct module *module);
void module_put(struct module *module);
```

`try_module_get()` attempts to increment a module's reference count, but fails if the module is being removed. This ensures graceful handling of userspace module removal requests.

Two forms of protection exist:
- **Direct protection**: Another entity has incremented the module reference
- **Implied protection**: Through sysfs/kernfs active references (e.g., sysfs store/read operations are guaranteed to exist while active)

### Managed Device Resources (devres)

Device-managed resources are automatically freed when the device is removed:

```c
/* Automatically freed on remove */
void *buf = devm_kmalloc(dev, size, GFP_KERNEL);
struct clk *clk = devm_clk_get(dev, "bus_clk");
int irq = devm_request_irq(dev, irq, handler, 0, "my", data);
void __iomem *base = devm_ioremap_resource(dev, res);
```

devres simplifies error handling in `probe()` — you don't need to unwind allocations on failure.

## Driver Subsystem APIs (from docs.kernel.org)

The kernel driver API documentation at `docs.kernel.org/driver-api/index.html` reveals the full scope of driver development interfaces. The driver API is organized into several categories:

### General Information for Driver Authors

- **Driver Basics**: Module entry/exit, reference counting, `try_module_get()`/`module_put()`
- **Driver Model**: The kobject/device/bus/driver framework described above
- **Device Links**: Dependencies between devices for ordering probe/remove
- **Device Drivers Infrastructure**: Common patterns and helpers
- **ioctl Based Interfaces**: Implementing device control interfaces
- **CPU and Device Power Management**: Suspend/resume, runtime PM

### Useful Support Libraries

The kernel provides several libraries for driver development:

| Library | Purpose |
|---------|--------|
| **Bus-Independent Device Accesses** | `ioread32()`, `iowrite32()`, `readb()`, `writeb()` |
| **dma-buf** | Buffer sharing and synchronization between devices |
| **Device Frequency Scaling (devfreq)** | Dynamic frequency adjustment |
| **Component Helper** | Aggregate drivers from multiple components |
| **VFIO** | Virtual Function I/O for user-space device drivers |
| **Userspace I/O (UIO)** | Map device memory to user space |

### Bus-Level Documentation

| Bus | Description |
|-----|-------------|
| **PCI** | PCI/PCIe device driver API |
| **USB** | Universal Serial Bus driver API |
| **I2C/SMBus** | Inter-IC bus for low-speed peripherals |
| **SPI** | Serial Peripheral Interface |
| **I3C** | Improved Inter-Integrated Circuit |
| **Virtio** | Paravirtualized device driver API |
| **Auxiliary Bus** | For sub-devices that don't have their own bus |
| **CXL** | Compute Express Link |
| **Firewire** | IEEE 1394 driver interface |
| **W1** | Dallas 1-wire bus |

### Subsystem-Specific APIs

The kernel includes driver APIs for many specialized subsystems:

- **GPIO**: General Purpose Input/Output control
- **Regulator**: Voltage and current regulator framework
- **Clock**: Common clock framework
- **Thermal**: Temperature monitoring and cooling
- **PWM**: Pulse-Width Modulation interface
- **PHY**: Generic PHY framework for physical layer devices
- **Pinctrl**: Pin control and multiplexing
- **FPGA**: FPGA manager, bridge, and region interfaces
- **NVMEM**: Non-Volatile Memory device framework
- **Media**: V4L2, DVB, and CEC subsystem APIs
- **Input**: Input subsystem (keyboards, mice, touchscreens)
- **SCSI**: SCSI subsystem driver interface
- **MMC/SD/SDIO**: Memory card support
- **InfiniBand/RDMA**: Remote DMA interfaces

### Module Entry and Exit Points

From `docs.kernel.org/driver-api/basics.html`:

```c
module_init(x)  /* driver initialization entry point */
module_exit(x)  /* driver exit entry point */
```

`module_init()` is called during `do_initcalls()` (if builtin) or at module insertion time (if a module). `module_exit()` wraps clean-up code with `cleanup_module()` when used with `rmmod`.

### Module Reference Counting

```c
bool try_module_get(struct module *module);
void module_put(struct module *module);
```

`try_module_get()` increments a module's reference count but fails if the module is being removed. Two forms of protection exist:
- **Direct protection**: Another entity has incremented the module reference
- **Implied protection**: Through sysfs/kernfs active references

## Further Reading

- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux kernel docs — Driver Model](https://docs.kernel.org/driver-api/driver-model/index.html)
- [Linux kernel docs — Driver Basics](https://docs.kernel.org/driver-api/basics.html)
- [Linux kernel docs — Driver API Index](https://docs.kernel.org/driver-api/index.html) — Complete driver API reference
- [LWN: The Linux device model](https://lwn.net/Articles/23953/)
- [LWN: kobjects and sysfs](https://lwn.net/Articles/23953/)
- [kernel.org — drivers/base/](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/base)

## Related Topics

- [Character Devices](char-devices.md) — cdev and file_operations
- [PCI Subsystem](pci.md) — PCI bus type
- [USB Subsystem](usb.md) — USB bus type
- [Device Tree](device-tree.md) — platform device matching
- [Kernel APIs](../apis.md) — memory allocation and concurrency

## Device Tree Integration

The Device Tree (DT) is a data structure for describing hardware, used extensively on ARM, RISC-V, and other architectures where hardware isn't self-enumerating (unlike PCI).

### Device Tree Source Example

```dts
/* Simplified SoC device tree */
/ {
    compatible = "myvendor,myboard";
    model = "My Development Board";

    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        cpu@0 {
            device_type = "cpu";
            compatible = "arm,cortex-a53";
            reg = <0>;
        };
    };

    soc {
        compatible = "simple-bus";
        #address-cells = <1>;
        #size-cells = <1>;
        ranges;

        uart0: serial@10010000 {
            compatible = "myvendor,myuart";
            reg = <0x10010000 0x1000>;
            interrupts = <10 4>;
            clocks = <&clk_uart>;
            status = "okay";
        };

        i2c0: i2c@10020000 {
            compatible = "myvendor,myi2c";
            reg = <0x10020000 0x1000>;
            #address-cells = <1>;
            #size-cells = <0>;

            sensor@48 {
                compatible = "myvendor,tempsensor";
                reg = <0x48>;
            };
        };
    };
};
```

### Device Tree Matching in Drivers

```c
static const struct of_device_id my_driver_of_match[] = {
    { .compatible = "myvendor,myuart" },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, my_driver_of_match);

static struct platform_driver my_driver = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my-driver",
        .of_match_table = my_driver_of_match,
    },
};
module_platform_driver(my_driver);
```

### Accessing DT Properties in Drivers

```c
#include <linux/of.h>
#include <linux/of_device.h>

static int my_probe(struct platform_device *pdev)
{
    struct device_node *np = pdev->dev.of_node;
    u32 reg_base, irq;
    const char *label;

    /* Read properties */
    if (of_property_read_u32(np, "reg", &reg_base)) {
        dev_err(&pdev->dev, "missing reg property\n");
        return -EINVAL;
    }

    of_property_read_string(np, "label", &label);

    irq = platform_get_irq(pdev, 0);
    if (irq < 0) return irq;

    dev_info(&pdev->dev, "base=%x irq=%u label=%s\n",
             reg_base, irq, label ?: "(none)");
    return 0;
}
```

## PCI Subsystem

PCI (Peripheral Component Interconnect) is a bus standard for connecting peripherals. PCI Express (PCIe) is the modern serial version.

### PCI Device Identification

```bash
# List all PCI devices
lspci
# 00:00.0 Host bridge: Intel Corporation 440FX - 82441FX PMC [Natoma]
# 00:01.0 ISA bridge: Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]
# 00:01.1 IDE interface: Intel Corporation 82371SB PIIX3 IDE [Natoma/Triton II]
# 00:02.0 VGA compatible controller: Device 1234:1111 (rev 02)
# 00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet

# Detailed info
lspci -v -s 00:03.0

# Kernel view
ls /sys/bus/pci/devices/0000\:00\:03.0/
# config  device  driver  enable  irq  resource  vendor  class  ...

# PCI device configuration space (first 64 bytes)
xxd /sys/bus/pci/devices/0000\:00\:03.0/config | head -4
```

### PCI Driver Structure

```c
static const struct pci_device_id my_pci_ids[] = {
    { PCI_DEVICE(VENDOR_ID, DEVICE_ID) },
    { PCI_DEVICE_CLASS(NETWORK_CLASS, NETWORK_MASK) },
    { 0, }
};
MODULE_DEVICE_TABLE(pci, my_pci_ids);

static int my_pci_probe(struct pci_dev *pdev,
                        const struct pci_device_id *id)
{
    int err;

    /* Enable the device */
    err = pci_enable_device(pdev);
    if (err) return err;

    /* Request memory regions */
    err = pci_request_regions(pdev, "my-driver");
    if (err) goto disable;

    /* Map BAR0 */
    void __iomem *base = pci_iomap(pdev, 0, 0);
    if (!base) goto release;

    /* Read/write hardware registers */
    u32 val = ioread32(base + REG_OFFSET);
    iowrite32(val | FLAG, base + REG_OFFSET);

    pci_set_drvdata(pdev, base);
    return 0;

release:
    pci_release_regions(pdev);
disable:
    pci_disable_device(pdev);
    return -ENODEV;
}

static struct pci_driver my_pci_driver = {
    .name = "my-pci",
    .id_table = my_pci_ids,
    .probe = my_pci_probe,
    .remove = my_pci_remove,
};
module_pci_driver(my_pci_driver);
```

## DMA (Direct Memory Access)

DMA allows devices to transfer data directly to/from memory without CPU involvement.

### DMA Mapping API

```c
#include <linux/dma-mapping.h>

static int my_probe(struct device *dev)
{
    /* Set DMA mask (addressable bits) */
    if (dma_set_mask_and_coherent(dev, DMA_BIT_MASK(64))) {
        dma_set_mask_and_coherent(dev, DMA_BIT_MASK(32));
    }

    /* Allocate DMA-coherent buffer */
    void *buf = dma_alloc_coherent(dev, PAGE_SIZE,
                                    &dma_handle, GFP_KERNEL);
    if (!buf) return -ENOMEM;

    /* buf = CPU virtual address, dma_handle = device address */
    /* Pass dma_handle to hardware for DMA transfers */
    /* Read from buf after device completes DMA */

    /* Free */
    dma_free_coherent(dev, PAGE_SIZE, buf, dma_handle);
    return 0;
}
```

### Streaming DMA (for existing buffers)

```c
/* Map an existing buffer for DMA */
dma_addr_t dma = dma_map_single(dev, skb->data, skb->len, DMA_TO_DEVICE);
if (dma_mapping_error(dev, dma)) goto error;

/* Device can now read from 'dma' address */
/* After DMA completes: */
dma_unmap_single(dev, dma, skb->len, DMA_TO_DEVICE);
```

## Interrupt Handling

### Requesting IRQs

```c
#include <linux/interrupt.h>

static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    struct my_data *data = dev_id;

    /* Check if this device generated the interrupt */
    u32 status = ioread32(data->base + IRQ_STATUS_REG);
    if (!(status & IRQ_BIT))
        return IRQ_NONE;  /* Not ours */

    /* Acknowledge interrupt */
    iowrite32(status, data->base + IRQ_STATUS_REG);

    /* Schedule bottom half (tasklet, workqueue, or threaded IRQ) */
    tasklet_schedule(&data->tasklet);

    return IRQ_HANDLED;
}

/* In probe(): */
int irq = platform_get_irq(pdev, 0);
err = devm_request_irq(dev, irq, my_irq_handler,
                       IRQF_SHARED, "my-device", data);
```

### Threaded IRQs

```c
/* Threaded IRQ handler runs in process context (can sleep) */
static irqreturn_t my_threaded_irq(int irq, void *dev_id)
{
    /* Can use mutexes, allocate memory, etc. */
    struct my_data *data = dev_id;
    process_pending_work(data);
    return IRQ_HANDLED;
}

err = devm_request_threaded_irq(dev, irq,
                                my_hard_irq,      /* top half (atomic) */
                                my_threaded_irq,   /* bottom half (threaded) */
                                IRQF_SHARED, "my-device", data);
```

## Character Device Registration

```c
#include <linux/cdev.h>
#include <linux/fs.h>

static const struct file_operations my_fops = {
    .owner = THIS_MODULE,
    .read = my_read,
    .write = my_write,
    .open = my_open,
    .release = my_release,
    .unlocked_ioctl = my_ioctl,
};

static int my_probe(struct platform_device *pdev)
{
    dev_t devno;
    struct cdev *cdev;

    /* Allocate device number */
    alloc_chrdev_region(&devno, 0, 1, "my-device");

    /* Initialize and add cdev */
    cdev = cdev_alloc();
    cdev->ops = &my_fops;
    cdev_add(cdev, devno, 1);

    /* Create device node */
    device_create(my_class, &pdev->dev, devno, NULL, "mydev");

    return 0;
}
```

See [Character Devices](char-devices.md) for complete details.

## I2C and SPI Drivers

### I2C Driver

```c
static const struct of_device_id my_i2c_of_match[] = {
    { .compatible = "myvendor,tempsensor" },
    { }
};

static int my_i2c_probe(struct i2c_client *client)
{
    /* Read from device */
    s32 temp = i2c_smbus_read_word_data(client, TEMP_REG);
    dev_info(&client->dev, "Temperature: %d\n", temp);
    return 0;
}

static struct i2c_driver my_i2c_driver = {
    .driver = {
        .name = "my-sensor",
        .of_match_table = my_i2c_of_match,
    },
    .probe = my_i2c_probe,
};
module_i2c_driver(my_i2c_driver);
```

### SPI Driver

```c
static int my_spi_probe(struct spi_device *spi)
{
    u8 tx_buf[] = { 0x9F };  /* Read JEDEC ID */
    u8 rx_buf[3];

    struct spi_transfer xfer = {
        .tx_buf = tx_buf,
        .rx_buf = rx_buf,
        .len = sizeof(tx_buf),
    };

    spi_sync_transfer(spi, &xfer, 1);
    dev_info(&spi->dev, "JEDEC ID: %02x%02x%02x\n",
             rx_buf[0], rx_buf[1], rx_buf[2]);
    return 0;
}

static struct spi_driver my_spi_driver = {
    .driver = {
        .name = "my-spi-device",
        .of_match_table = my_spi_of_match,
    },
    .probe = my_spi_probe,
};
module_spi_driver(my_spi_driver);
```
