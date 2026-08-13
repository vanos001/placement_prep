# Pinctrl — Pin Control Subsystem

The **pinctrl** subsystem is the Linux kernel framework for managing SoC
(System-on-Chip) pins. It handles **pin muxing** (selecting which function a
pin serves — e.g., UART TX vs GPIO) and **pin configuration** (electrical
properties like pull-up, drive strength, slew rate).

> **Header:** `include/linux/pinctrl/pinctrl.h`, `include/linux/pinctrl/pinmux.h`  
> **Key files:** `drivers/pinctrl/core.c`, `drivers/pinctrl/devicetree.c`  
> **DT bindings:** `Documentation/devicetree/bindings/pinctrl/`

---

## Why Pinctrl Exists

Modern SoCs have hundreds of pins that can serve multiple functions:

```
┌──────────────────────────────────────────────────────┐
│                    SoC Pin                            │
│                                                      │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐        │
│  │  UART   │     │  GPIO   │     │  SPI    │        │
│  │  TX     │     │  Pin 23 │     │  MOSI   │        │
│  └────┬────┘     └────┬────┘     └────┬────┘        │
│       │               │               │              │
│       └───────────────┼───────────────┘              │
│                       │                              │
│                  ┌────▼────┐                         │
│                  │ Pin Mux │                         │
│                  │ Select  │                         │
│                  └────┬────┘                         │
│                       │                              │
│                  ┌────▼────┐                         │
│                  │Physical │                         │
│                  │   Pin   │                         │
│                  └─────────┘                         │
└──────────────────────────────────────────────────────┘
```

Without pinctrl, each driver would need SoC-specific pin programming code.
Pinctrl provides:

1. **A unified API** for drivers to request pin configurations.
2. **Device tree integration** for describing pin setups declaratively.
3. **Runtime pin switching** (e.g., switch a pin from GPIO to I2C on demand).

---

## Core Concepts

### Pin Controller

A **pin controller** is a hardware block (or driver) that manages a set of pins.
Each SoC has at least one pin controller.

```c
struct pinctrl_desc {
    const char *name;
    const struct pinctrl_pin_desc *pins;
    unsigned int npins;
    const struct pinctrl_ops *pctlops;      /* pin control operations */
    const struct pinmux_ops *pmxops;        /* pin mux operations */
    const struct pinconf_ops *confops;      /* pin configuration ops */
    /* ... */
};
```

### Pin States

Devices define **pin states** that describe how their pins should be configured:

| State | Purpose |
|-------|---------|
| `default` | Normal operation |
| `init` | During driver probe (before device starts) |
| `sleep` | Low-power state |
| `idle` | Intermediate power state |
| `gpio` | Pin used as GPIO |
| `spi` | Pin used for SPI function |

### Device-Side API

Drivers request pin states via the pinctrl API:

```c
#include <linux/pinctrl/consumer.h>

struct pinctrl *pinctrl;
struct pinctrl_state *state_default;

/* Get pinctrl handle */
pinctrl = devm_pinctrl_get(dev);

/* Get a specific state */
state_default = pinctrl_lookup_state(pinctrl, "default");

/* Apply the state */
pinctrl_select_state(pinctrl, state_default);
```

---

## Pin Muxing

Pin muxing selects which **function** a pin serves. Each pin can typically
serve one of several functions (e.g., UART, SPI, GPIO, I2C).

### Pinmux Operations (Driver API)

```c
struct pinmux_ops {
    int (*request)(struct pinctrl_dev *pctldev, unsigned int pin);
    void (*free)(struct pinctrl_dev *pctldev, unsigned int pin);
    int (*get_functions_count)(struct pinctrl_dev *pctldev);
    const char *(*get_function_name)(struct pinctrl_dev *pctldev,
                                     unsigned int selector);
    int (*get_function_groups)(struct pinctrl_dev *pctldev,
                               unsigned int selector,
                               const char *const **groups,
                               unsigned int *num_groups);
    int (*set_mux)(struct pinctrl_dev *pctldev, unsigned int func_selector,
                   unsigned int group_selector);
    int (*gpio_request_enable)(struct pinctrl_dev *pctldev,
                               struct pinctrl_gpio_range *range,
                               unsigned int pin);
    void (*gpio_disable_free)(struct pinctrl_dev *pctldev,
                              struct pinctrl_gpio_range *range,
                              unsigned int pin);
    int (*gpio_set_direction)(struct pinctrl_dev *pctldev,
                              struct pinctrl_gpio_range *range,
                              unsigned int pin, bool input);
};
```

### Device Tree Muxing

```dts
/* Pin controller node */
&pinctrl {
    uart0_pins: uart0-pins {
        pins = "PIN_A_TX", "PIN_A_RX";
        function = "uart0";
    };

    spi0_pins: spi0-pins {
        pins = "PIN_B_MOSI", "PIN_B_MISO", "PIN_B_CLK", "PIN_B_CS";
        function = "spi0";
    };

    i2c1_pins: i2c1-pins {
        pins = "PIN_C_SDA", "PIN_C_SCL";
        function = "i2c1";
    };
};

/* Device node using the pins */
&uart0 {
    pinctrl-names = "default";
    pinctrl-0 = <&uart0_pins>;
    status = "okay";
};

&spi0 {
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&spi0_pins>;
    pinctrl-1 = <&spi0_sleep_pins>;
};
```

### Pin Groups

Pin controllers organize pins into **groups** for convenience:

```c
/* Group: all UART0 pins */
static const unsigned uart0_pins[] = { 10, 11 };  /* TX, RX */
static const unsigned uart0_pins_flow[] = { 10, 11, 12, 13 };  /* TX, RX, RTS, CTS */

static const struct pingrp_desc my_pin_groups[] = {
    PINGROUP("uart0", uart0_pins, uart0_mux),
    PINGROUP("uart0_flow", uart0_pins_flow, uart0_mux),
};
```

---

## Pin Configuration

Pin configuration sets electrical properties of pins.

### Configuration Parameters

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| `bias-disable` | No pull resistor | Default state |
| `bias-pull-up` | Internal pull-up | 20kΩ, 50kΩ |
| `bias-pull-down` | Internal pull-down | 20kΩ, 50kΩ |
| `drive-strength` | Output current | 2mA, 4mA, 8mA, 16mA |
| `input-schmitt-enable` | Schmitt trigger input | Boolean |
| `slew-rate` | Signal transition speed | 0=slow, 1=fast |
| `output-low` | Drive pin low | GPIO output |
| `output-high` | Drive pin high | GPIO output |

### Device Tree Configuration

```dts
&pinctrl {
    uart0_pins: uart0-pins {
        pins = "PIN_A_TX", "PIN_A_RX";
        function = "uart0";
        drive-strength = <8>;           /* 8mA */
        bias-pull-up;                   /* internal pull-up */
        input-schmitt-enable;           /* schmitt trigger */
    };

    spi0_pins: spi0-pins {
        pins = "PIN_B_MOSI", "PIN_B_CLK";
        function = "spi0";
        drive-strength = <12>;          /* 12mA (fast SPI) */
        bias-disable;
    };

    gpio_pins: gpio-pins {
        pins = "PIN_D_0", "PIN_D_1";
        function = "gpio";
        drive-strength = <4>;
        bias-pull-down;
        input-schmitt-enable;
    };
};
```

### Pinconf Operations

```c
struct pinconf_ops {
    bool is_generic;
    int (*pin_config_get)(struct pinctrl_dev *pctldev, unsigned int pin,
                          unsigned long *config);
    int (*pin_config_set)(struct pinctrl_dev *pctldev, unsigned int pin,
                          unsigned long *configs, unsigned int num_configs);
    int (*pin_config_group_get)(struct pinctrl_dev *pctldev,
                                unsigned int selector,
                                unsigned long *config);
    int (*pin_config_group_set)(struct pinctrl_dev *pctldev,
                                unsigned int selector,
                                unsigned long *configs,
                                unsigned int num_configs);
};
```

---

## GPIO Ranges

GPIO and pinctrl are separate subsystems that must coordinate. **GPIO ranges**
map GPIO numbers to pin controller pins:

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  GPIO Subsystem          Pinctrl Subsystem           │
│  ┌─────────────┐        ┌─────────────┐             │
│  │ GPIO 0-31   │◄──────►│ Pins 0-31   │             │
│  │ (gpiochip0) │  range │ (pinctrl0)  │             │
│  └─────────────┘        └─────────────┘             │
│                                                      │
│  ┌─────────────┐        ┌─────────────┐             │
│  │ GPIO 32-63  │◄──────►│ Pins 32-63  │             │
│  │ (gpiochip1) │  range │ (pinctrl1)  │             │
│  └─────────────┘        └─────────────┘             │
└──────────────────────────────────────────────────────┘
```

### Registering GPIO Ranges

```c
#include <linux/pinctrl/pinctrl.h>

static struct pinctrl_gpio_range my_gpio_range = {
    .name   = "my-gpio-chip",
    .id     = 0,
    .base   = 0,          /* GPIO base number */
    .pin_base = 0,        /* pin controller pin base */
    .npins  = 32,         /* number of pins */
    .gc     = &my_gpio_chip,
};

/* Register with pin controller */
pinctrl_add_gpio_range(pctldev, &my_gpio_range);
```

### Device Tree GPIO Range

```dts
&pinctrl {
    gpio-ranges = <&pinctrl 0 0 32>,   /* GPIO 0-31 → pins 0-31 */
                  <&pinctrl 32 32 16>;  /* GPIO 32-47 → pins 32-47 */
};
```

### GPIO Request Flow

```
gpio_request(gpio_num)
    │
    ▼
gpiochip request → pinctrl_gpio_request()
    │
    ▼
Pin controller checks:
    - Is this pin available? (not used by another function)
    - Switch pin to GPIO mode (if muxing needed)
    - Apply GPIO-specific configuration
```

---

## Pin States and Power Management

Pin states are especially important for power management:

```dts
&pinctrl {
    /* Active state */
    uart0_active: uart0-active {
        pins = "PIN_A_TX", "PIN_A_RX";
        function = "uart0";
        drive-strength = <8>;
        bias-pull-up;
    };

    /* Sleep state (low power) */
    uart0_sleep: uart0-sleep {
        pins = "PIN_A_TX", "PIN_A_RX";
        function = "gpio";          /* switch to GPIO */
        drive-strength = <2>;       /* minimal drive */
        bias-pull-down;             /* pull-down to save power */
        output-low;                 /* drive low */
    };
};

&uart0 {
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&uart0_active>;
    pinctrl-1 = <&uart0_sleep>;
};
```

### Runtime Pin State Switching

```c
/* Driver switches pins for suspend */
static int my_device_suspend(struct device *dev)
{
    struct pinctrl *pinctrl = dev_get_pinctrl(dev);
    struct pinctrl_state *sleep_state;

    sleep_state = pinctrl_lookup_state(pinctrl, "sleep");
    pinctrl_select_state(pinctrl, sleep_state);

    return 0;
}

/* Driver switches pins for resume */
static int my_device_resume(struct device *dev)
{
    struct pinctrl *pinctrl = dev_get_pinctrl(dev);
    struct pinctrl_state *default_state;

    default_state = pinctrl_lookup_state(pinctrl, "default");
    pinctrl_select_state(pinctrl, default_state);

    return 0;
}
```

The PM core handles this automatically if `pinctrl-names` includes `"sleep"`.

---

## Pin Control in Device Tree: Full Example

```dts
/ {
    /* SoC-level pin controller */
    pinctrl: pinctrl@ff780000 {
        compatible = "vendor,soc-pinctrl";
        reg = <0xff780000 0x1000>;
        #pinctrl-cells = <1>;

        /* Pin definitions */
        pins {
            uart0_tx: uart0-tx {
                pins = "gpio10";
                function = "uart0";
                drive-strength = <8>;
                bias-pull-up;
            };

            uart0_rx: uart0-rx {
                pins = "gpio11";
                function = "uart0";
                bias-disable;
                input-schmitt-enable;
            };

            i2c0_sda: i2c0-sda {
                pins = "gpio20";
                function = "i2c0";
                drive-strength = <4>;
                bias-pull-up;
            };

            i2c0_scl: i2c0-scl {
                pins = "gpio21";
                function = "i2c0";
                drive-strength = <4>;
                bias-pull-up;
            };

            spi0_pins: spi0-pins {
                pins = "gpio30", "gpio31", "gpio32", "gpio33";
                function = "spi0";
                drive-strength = <12>;
                bias-disable;
            };

            /* Pin group (convenience) */
            uart0_pins: uart0-pins {
                pins = "gpio10", "gpio11";
                function = "uart0";
                drive-strength = <8>;
            };
        };

        /* GPIO ranges */
        gpio-ranges = <&pinctrl 0 0 64>;
    };
};

/* Devices reference pin states */
&uart0 {
    pinctrl-names = "default";
    pinctrl-0 = <&uart0_pins>;
    status = "okay";
};

&i2c0 {
    pinctrl-names = "default", "high-speed";
    pinctrl-0 = <&i2c0_sda &i2c0_scl>;
    pinctrl-1 = <&i2c0_hs_sda &i2c0_hs_scl>;
    status = "okay";
};
```

---

## Common Pin Controller Drivers

| Driver | SoC Vendor | File |
|--------|-----------|------|
| `pinctrl-bcm2835` | Broadcom (Raspberry Pi) | `drivers/pinctrl/bcm/pinctrl-bcm2835.c` |
| `pinctrl-sunxi` | Allwinner | `drivers/pinctrl/sunxi/pinctrl-sunxi.c` |
| `pinctrl-tegra` | NVIDIA Tegra | `drivers/pinctrl/tegra/pinctrl-tegra.c` |
| `pinctrl-qcom` | Qualcomm | `drivers/pinctrl/qcom/pinctrl-*.c` |
| `pinctrl-meson` | Amlogic | `drivers/pinctrl/meson/pinctrl-meson.c` |
| `pinctrl-rockchip` | Rockchip | `drivers/pinctrl/pinctrl-rockchip.c` |
| `pinctrl-imx` | NXP i.MX | `drivers/pinctrl/freescale/pinctrl-imx.c` |
| `pinctrl-stm32` | STMicroelectronics | `drivers/pinctrl/stm32/pinctrl-stm32.c` |

---

## Debugging

### View Current Pin States

```bash
# Debugfs interface (if available)
cat /sys/kernel/debug/pinctrl/pinctrl-maps
cat /sys/kernel/debug/pinctrl/pinctrl-handles

# Pin status
cat /sys/kernel/debug/pinctrl/pinctrl@ff780000/pins
cat /sys/kernel/debug/pinctrl/pinctrl@ff780000/pinmux-pins
cat /sys/kernel/debug/pinctrl/pinctrl@ff780000/pinconf-pins
```

### Debugfs Output Example

```
Registered pinctrl groups:
  group: uart0-pins
    pin 10 (gpio10): function uart0
    pin 11 (gpio11): function uart0

Requested pin 10:
  device: uart0
  function: uart0
  hog: no

Pin config pins:
  pin 10 (gpio10): bias-pull-up drive-strength=8
  pin 11 (gpio11): bias-disable input-schmitt-enable
```

### Common Issues

```bash
# "could not get pinctrl state"
# → Device tree pinctrl-0 reference is wrong
# → Pin controller driver not loaded

# "pin already requested"
# → Another driver already claimed this pin
# → Check: cat /sys/kernel/debug/pinctrl/*/pinmux-pins

# "invalid pin group"
# → Pin name in DT doesn't match driver's pin table
# → Check: cat /sys/kernel/debug/pinctrl/*/pins
```

---

## Consumer API Summary

```c
/* Get pinctrl handle for a device */
struct pinctrl *devm_pinctrl_get(struct device *dev);

/* Look up a named state */
struct pinctrl_state *pinctrl_lookup_state(struct pinctrl *p,
                                           const char *name);

/* Apply a pin state */
int pinctrl_select_state(struct pinctrl *p, struct pinctrl_state *state);

/* Release (managed versions auto-release) */
void pinctrl_put(struct pinctrl *p);

/* GPIO-specific */
int pinctrl_gpio_request(unsigned gpio);
void pinctrl_gpio_free(unsigned gpio);
int pinctrl_gpio_direction_input(unsigned gpio);
int pinctrl_gpio_direction_output(unsigned gpio, int value);
```

---

## Relation to Other Subsystems

- **pinctrl** configures pins; **GPIO** uses pins as general-purpose I/O.
- **pinctrl** selects functions; individual **bus drivers** (SPI, I2C, UART) use the selected function.
- **Device tree** describes pin configurations; **pinctrl** applies them.
- **Clock framework** often works alongside pinctrl (e.g., enabling a clock for a pin function).

---

## Further Reading

- [Kernel docs: Pinctrl subsystem](https://www.kernel.org/doc/html/latest/driver-api/pinctrl.html)
- [Kernel docs: Pinctrl bindings](https://www.kernel.org/doc/html/latest/devicetree/bindings/pinctrl/pinctrl-bindings.html)
- [LWN: The pin control subsystem (2012)](https://lwn.net/Articles/503785/)
- [pinctrl API reference](https://elixir.bootlin.com/linux/latest/source/include/linux/pinctrl/consumer.h)
- [Device tree pinctrl examples](https://github.com/torvalds/linux/tree/master/Documentation/devicetree/bindings/pinctrl)
- See also: [GPIO](/kernel/drivers/gpio), [Device Tree](/embedded/device-tree), [Device Tree Overlays](/embedded/dt-overlays)
