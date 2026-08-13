# Device Tree Overlays

**Device Tree Overlays** (DT overlays) allow modifying the device tree at runtime
— adding, modifying, or removing nodes and properties without recompiling the
base device tree blob (DTB). This is essential for modular hardware, expansion
boards (HATs), and reconfigurable embedded systems.

> **Kernel support:** `CONFIG_OF_OVERLAY`  
> **Tools:** `dtc` (device tree compiler), `fdtoverlay`, `dtoverlay` (Raspberry Pi)  
> **DT spec:** DeviceTree.org Specification, Overlay Notes

---

## Why Overlays Exist

Traditionally, the device tree is compiled once at boot time:

```
┌─────────────────────────────────────────────────────┐
│         Traditional (Static) Device Tree            │
│                                                     │
│  .dts files ──► dtc ──► .dtb ──► bootloader ──►    │
│                                                     │
│  Fixed at build time. Change = recompile + reboot.  │
└─────────────────────────────────────────────────────┘
```

Overlays enable **dynamic** modification:

```
┌─────────────────────────────────────────────────────┐
│         Overlay-Based Device Tree                   │
│                                                     │
│  Base DTB (static)                                  │
│      +                                              │
│  Overlay 1 (.dtbo) ──► applied at boot/runtime      │
│  Overlay 2 (.dtbo) ──► applied at boot/runtime      │
│  ...                                                │
│      =                                              │
│  Combined device tree                               │
└─────────────────────────────────────────────────────┘
```

### Use Cases

- **Raspberry Pi HATs**: expansion boards declare their hardware via overlays.
- **BeagleBone Cape**: plug-in boards with custom hardware.
- **Modular SoMs**: different carrier boards need different peripheral configs.
- **Runtime reconfiguration**: enable/disable hardware features without reboot.

---

## Overlay Anatomy

An overlay is a device tree source file that describes **modifications** to apply
to a base device tree.

### Basic Structure

```dts
/dts-v1/;
/plugin/;   /* Required: marks this as an overlay */

/ {
    fragment@0 {
        target = <&i2c1>;           /* Node to modify */
        __overlay__ {
            /* Properties and child nodes to add */
            my-sensor@48 {
                compatible = "vendor,my-sensor";
                reg = <0x48>;
                interrupt-parent = <&gpio>;
                interrupts = <17 2>;  /* GPIO 17, falling edge */
            };
        };
    };

    fragment@1 {
        target = <&gpio>;
        __overlay__ {
            my-sensor-int {
                pins = "PIN_17";
                function = "gpio";
                bias-pull-up;
            };
        };
    };
};
```

### Fragment Syntax

Each `fragment@N` node describes one modification:

```
fragment@N {
    target = <&phandle>;              /* Target node by phandle */
    // OR
    target-path = "/path/to/node";    /* Target node by path */

    __overlay__ { ... };              /* Content to add/modify */
    // OR
    __dormant__ { ... };              /* Content when overlay is disabled */
};
```

| Field | Purpose |
|-------|---------|
| `target` | Phandle of the node to modify (preferred) |
| `target-path` | Full path of the node to modify (if no phandle) |
| `__overlay__` | Nodes/properties to add or modify |
| `__dormant__` | Nodes/properties when overlay is removed |

### Multiple Fragments

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&i2c1>;
        __overlay__ {
            /* Add a device on I2C bus 1 */
            sensor@50 {
                compatible = "vendor,temperature-sensor";
                reg = <0x50>;
            };
        };
    };

    fragment@1 {
        target = <&spi0>;
        __overlay__ {
            /* Add a device on SPI bus 0 */
            display@0 {
                compatible = "vendor,oled-display";
                reg = <0>;
                spi-max-frequency = <10000000>;
            };
        };
    };

    fragment@2 {
        target = <&gpio>;
        __overlay__ {
            /* Configure GPIO for display reset */
            display-reset {
                pins = "PIN_25";
                function = "gpio";
                output-low;
            };
        };
    };
};
```

### Conditionals

Overlays can use `__dormant__` for conditional inclusion:

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&i2c1>;
        __overlay__ {
            sensor@48 {
                compatible = "vendor,sensor-v1";
                reg = <0x48>;
            };
        };
    };

    /* This fragment only applies when explicitly enabled */
    fragment@1 {
        target = <&i2c1>;
        __dormant__ {
            sensor@49 {
                compatible = "vendor,sensor-v2";
                reg = <0x49>;
            };
        };
    };
};
```

---

## Compilation

### From Source to Binary

```bash
# Compile overlay source to binary
dtc -@ -I dts -O dtb -o my-overlay.dtbo my-overlay.dts

# Flags:
#   -@    Emit __symbols__ node (required for overlay references)
#   -I dts    Input format: device tree source
#   -O dtb    Output format: device tree blob
#   -o        Output file (use .dtbo extension)
```

### The `-@` Flag

The `-@` flag is critical for overlays. It tells `dtc` to:

1. Generate a `__symbols__` node with all labels.
2. Enable `target = <&phandle>` references to work.

```bash
# Without -@: overlay cannot reference base DT symbols
# With -@: overlay can use &i2c1, &gpio, etc.
dtc -@ -I dts -O dtb -o overlay.dtbo overlay.dts
```

### Using fdtoverlay (from dtc package)

```bash
# Apply overlay to base DTB
fdtoverlay -i base.dtb -o combined.dtb overlay1.dtbo overlay2.dtbo

# Check result
dtc -I dtb -O dts combined.dtb | less
```

### Preprocessing with CPP

Overlays often use `#include` for shared headers:

```bash
# Preprocess then compile
cpp -nostdinc -I include -undef -x assembler-with-cpp overlay.dts | \
    dtc -@ -I dts -O dtb -o overlay.dtbo -
```

---

## Applying Overlays at Boot

### Bootloader (U-Boot)

```bash
# In U-Boot:
load mmc 0:1 ${fdt_addr} base.dtb
load mmc 0:1 ${ovl_addr} my-overlay.dtbo
fdt apply ${ovl_addr}
booti ${kernel_addr} - ${fdt_addr}
```

### Bootloader (config.txt — Raspberry Pi)

```bash
# /boot/config.txt
dtoverlay=my-overlay
dtoverlay=i2c-sensor,sensor_addr=0x48

# With parameters
dtoverlay=my-overlay,param1=value1,param2=value2

# Disable an overlay
dtoverlay=
```

### GRUB

```bash
# In /boot/grub/grub.cfg or custom config
# GRUB doesn't directly support overlays, but you can:
# 1. Pre-apply overlays and use the combined DTB
# 2. Use a boot script that applies overlays before boot
```

---

## Applying Overlays at Runtime

### Sysfs Interface

```bash
# List available overlays (Raspberry Pi)
ls /boot/overlays/

# Apply via configfs (if available)
mkdir /sys/kernel/config/device-tree/overlays/my-overlay
echo my-overlay.dtbo > /sys/kernel/config/device-tree/overlays/my-overlay/path

# Remove overlay
rmdir /sys/kernel/config/device-tree/overlays/my-overlay
```

### Raspberry Pi `dtoverlay` Tool

```bash
# Apply overlay
sudo dtoverlay my-overlay

# Apply with parameters
sudo dtoverlay my-overlay sensor_addr=0x48

# List active overlays
dtoverlay -l

# Remove overlay
sudo dtoverlay -r my-overlay

# View overlay info
dtoverlay -h my-overlay
```

### Programmatic Application

```c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int apply_overlay(const char *overlay_path)
{
    int fd;
    int err;

    /* Write overlay to the configfs overlay manager */
    fd = open("/sys/kernel/config/device-tree/overlays/my-overlay/path",
              O_WRONLY);
    if (fd < 0) {
        perror("open overlay path");
        return -1;
    }

    err = write(fd, overlay_path, strlen(overlay_path));
    close(fd);

    return (err > 0) ? 0 : -1;
}
```

---

## Overlay Parameters

Overlays can accept parameters to customize behavior:

### Defining Parameters

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&i2c1>;
        __overlay__ {
            sensor@48 {
                compatible = "vendor,sensor";
                reg = <0x48>;
                /* These can be overridden by parameters */
                /* Defined via __overrides__ */
            };
        };
    };

    __overrides__ {
        /* Parameter name → target property */
        sensor_addr = <&sensor>,"reg:0";
        sensor_int = <&sensor>,"interrupts:0";
        label = <&sensor>,"label";
    };
};
```

### Parameter Syntax

```
__overrides__ {
    param_name = <&target>,"property:offset";
};
```

| Component | Meaning |
|-----------|---------|
| `param_name` | Name used on the command line |
| `<&target>` | Phandle of the node to modify |
| `"property"` | Property name in that node |
| `:offset` | Byte offset within the property (for multi-cell values) |

### Using Parameters

```bash
# Raspberry Pi
dtoverlay=my-sensor-overlay sensor_addr=0x49 sensor_int=17
```

---

## Real-World Examples

### Raspberry Pi I2C Sensor HAT

```dts
/dts-v1/;
/plugin/;

/ {
    compatible = "brcm,bcm2835";

    fragment@0 {
        target = <&i2c_arm>;
        __overlay__ {
            #address-cells = <1>;
            #size-cells = <0>;
            status = "okay";

            bme280@76 {
                compatible = "bosch,bme280";
                reg = <0x76>;
                pinctrl-names = "default";
                pinctrl-0 = <&bme280_pins>;
            };
        };
    };

    fragment@1 {
        target = <&gpio>;
        __overlay__ {
            bme280_pins: bme280-pins {
                brcm,pins = <4>;
                brcm,function = <0>;    /* input */
                brcm,pull = <2>;        /* pull-up */
            };
        };
    };

    __overrides__ {
        addr = <&bme280>,"reg:0";
        int_pin = <&bme280>,"interrupts:0",
                  <&bme280_pins>,"brcm,pins:0";
    };
};
```

### SPI Display Overlay

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&spi0>;
        __overlay__ {
            #address-cells = <1>;
            #size-cells = <0>;
            status = "okay";

            pinctrl-names = "default";
            pinctrl-0 = <&spi0_pins &display_pins>;

            display@0 {
                compatible = "ilitek,ili9341";
                reg = <0>;
                spi-max-frequency = <32000000>;
                dc-gpios = <&gpio 25 0>;
                reset-gpios = <&gpio 24 0>;
                rotation = <90>;
            };
        };
    };

    fragment@1 {
        target = <&gpio>;
        __overlay__ {
            display_pins: display-pins {
                pins = "PIN_24", "PIN_25";
                function = "gpio";
                drive-strength = <4>;
            };
        };
    };
};
```

### UART Overlay

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&uart1>;
        __overlay__ {
            status = "okay";
            pinctrl-names = "default";
            pinctrl-0 = <&uart1_pins>;
        };
    };

    fragment@1 {
        target = <&gpio>;
        __overlay__ {
            uart1_pins: uart1-pins {
                pins = "PIN_14", "PIN_15";  /* TX, RX */
                function = "uart1";
                bias-pull-up;
            };
        };
    };
};
```

### GPIO LED Overlay

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target-path = "/";
        __overlay__ {
            my_leds {
                compatible = "gpio-leds";
                status = "okay";

                led0 {
                    label = "my-led";
                    gpios = <&gpio 17 0>;   /* GPIO 17, active high */
                    default-state = "off";
                    linux,default-trigger = "heartbeat";
                };
            };
        };
    };

    fragment@1 {
        target = <&gpio>;
        __overlay__ {
            led0_pin: led0-pin {
                pins = "PIN_17";
                function = "gpio";
                output-low;
            };
        };
    };

    __overrides__ {
        led_gpio = <&led0>,"gpios:4",
                   <&led0_pin>,"pins:0";
    };
};
```

---

## Overlay Manipulation with libfdt

For programmatic overlay creation or manipulation:

```c
#include <libfdt.h>
#include <libfdt_overlay.h>

/* Apply an overlay to a base FDT */
int apply_overlay(void *base_fdt, void *overlay_fdt)
{
    int err;

    /* Expand base FDT to make room for overlay additions */
    err = fdt_open_into(base_fdt, base_fdt,
                        fdt_totalsize(base_fdt) +
                        fdt_totalsize(overlay_fdt));
    if (err) return err;

    /* Apply the overlay */
    err = fdt_overlay_apply(base_fdt, overlay_fdt);
    if (err) return err;

    return 0;
}
```

---

## Debugging Overlays

### Check if Overlay Applied

```bash
# View active overlays (Raspberry Pi)
dtoverlay -l

# View combined device tree
dtc -I dtb -O dts /sys/firmware/fdt | less

# Or from dtb file
dtc -I dtb -O dts /boot/bcm2711-rpi-4-b.dtb | less
```

### Common Errors

```bash
# "FDT_ERR_NOTFOUND" — target node not found
# → Check that the base DT contains the target node
# → Verify phandle references

# "FDT_ERR_NOSPACE" — not enough room
# → Expand the base FDT before applying

# "FDT_ERR_BADOVERLAY" — malformed overlay
# → Compile with -@ flag
# → Check syntax with: dtc -I dts -O dtb overlay.dts

# Overlay applies but device doesn't work
# → Check dmesg for driver probe errors
# → Verify hardware connections match the overlay
```

### Verbose Overlay Application

```bash
# Raspberry Pi: debug overlay loading
sudo dtoverlay -v my-overlay

# Kernel log
dmesg | grep -i "of_overlay\|overlay\|OF: "
```

---

## Kernel Config

```
CONFIG_OF=y                    # Device tree support
CONFIG_OF_OVERLAY=y            # Overlay support
CONFIG_OF_DYNAMIC=y            # Dynamic device tree modifications
CONFIG_OF_RESOLVE=y            # Phandle resolution
CONFIG_OF_CONFIGFS=y           # Configfs-based overlay management
```

---

## Overlay Best Practices

1. **Use `-@` flag** when compiling overlays — always.
2. **Keep overlays small** — one function per overlay.
3. **Use `__overrides__`** for configurable parameters.
4. **Test with `fdtoverlay`** before deploying to hardware.
5. **Name fragments clearly** — `fragment@0`, `fragment@1`, etc.
6. **Document parameters** — include comments describing each parameter.
7. **Handle removal** — use `__dormant__` for cleanup if the overlay is removable.

---

## Relation to Other Subsystems

- **Device Tree Overlays** modify the base [Device Tree](/embedded/device-tree).
- **[Pinctrl](/kernel/drivers/pinctrl)** configurations are commonly added via overlays.
- **GPIO** pin assignments are defined in overlays.
- **U-Boot** applies overlays before passing the DTB to the kernel.
- **[devicetree.org](https://devicetree.org/)** maintains the DT specification.

---

## Further Reading

- [Kernel docs: Dynamic DeviceTree](https://www.kernel.org/doc/html/latest/devicetree/overlay-notes.html)
- [DeviceTree Specification](https://devicetree.org/specifications/)
- [Raspberry Pi Device Tree Overlays](https://www.raspberrypi.com/documentation/computers/configuration.html#part2)
- [dtc (device tree compiler)](https://git.kernel.org/pub/scm/utils/dtc/dtc.git)
- [LWN: Device tree overlays (2013)](https://lwn.net/Articles/574922/)
- [BeagleBone Cape overlays](https://docs.beagleboard.org/latest/boards/beaglebone/ai/capes/)
- See also: [Device Tree](/embedded/device-tree), [Pinctrl](/kernel/drivers/pinctrl), [GPIO](/kernel/drivers/gpio), [U-Boot](/embedded/uboot)
