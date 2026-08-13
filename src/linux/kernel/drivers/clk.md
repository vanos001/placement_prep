# Clock Framework

## Overview

The Linux clock framework (also called the Common Clock Framework or CCF) provides a unified API for managing hardware clocks on embedded SoCs and other platforms. It handles clock sources, clock gates, PLLs (Phase-Locked Loops), dividers, and multiplexers, presenting them as a tree structure that consumers can query and control.

The clock framework was introduced to replace the ad-hoc clock management code scattered across ARM SoC platforms. Before CCF, each SoC vendor had its own clock implementation, leading to duplicated code and inconsistent behavior. CCF provides a single, standardized interface.

## Architecture

```
┌───────────────────────────────────────────┐
│            Consumer Drivers               │
│  (UART, SPI, I2C, display, audio, etc.)   │
├───────────────────────────────────────────┤
│              CCF API                      │
│  clk_prepare_enable / clk_set_rate / etc. │
├───────────────────────────────────────────┤
│              Clock Tree                   │
│  ┌─────┐  ┌──────┐  ┌────────┐           │
│  │ PLL │──│ Gate │──│ Divider│──→ output  │
│  └─────┘  └──────┘  └────────┘           │
│     │                                     │
│  ┌─────┐  ┌──────┐                       │
│  │ Mux │──│ Gate │──→ output              │
│  └─────┘  └──────┘                       │
├───────────────────────────────────────────┤
│           Platform Clock Drivers          │
│  (SoC-specific clock tree definitions)    │
└───────────────────────────────────────────┘
```

## Key Concepts

### Clock Types

| Type | Description | Example |
|------|-------------|---------|
| **Fixed-rate** | Constant frequency, no control | Crystal oscillator (24 MHz) |
| **Gate** | Enable/disable (on/off switch) | Clock gate for a peripheral |
| **Divider** | Divides parent frequency by a factor | CPU clock divider |
| **Multiplier** | Multiplies parent frequency | PLL multiplier |
| **Mux** | Selects one of N parent clocks | Clock source selector |
| **PLL** | Phase-Locked Loop, generates new frequency | System PLL |
| **Composite** | Combines mux + divider + gate | Complex peripheral clock |
| **Fractional** | Fractional divider (non-integer ratio) | Audio PLL |

### Clock Tree

Clocks form a tree (or DAG) structure:

```
osc_24m (fixed: 24 MHz)
├── pll_sys (PLL: 24 MHz → 1.2 GHz)
│   ├── cpu_clk (divider: 1.2 GHz / 1 = 1.2 GHz)
│   │   └── cpu_clk_gate (gate)
│   └── periph_clk (divider: 1.2 GHz / 4 = 300 MHz)
│       ├── uart_clk (gate)
│       ├── spi_clk (gate)
│       └── i2c_clk (divider: 300 MHz / 25 = 12 MHz)
└── osc_32k (fixed: 32.768 kHz)
    └── rtc_clk (gate)
```

## clk_hw API

The modern clock framework uses `struct clk_hw` as the base data structure for clock providers. Each clock type (gate, divider, mux, etc.) includes a `clk_hw` member.

### Provider (Registration)

```c
#include <linux/clk-provider.h>

/* Define a fixed-rate clock */
static struct clk_hw my_osc_hw = {
    .init = &(struct clk_init_data){
        .name = "my_osc",
        .ops = &clk_fixed_rate_ops,
        .parent_data = NULL,
        .num_parents = 0,
    },
};

/* Register the clock */
int clk_hw_register(struct device *dev, struct clk_hw *hw);

/* Unregister */
void clk_hw_unregister(struct clk_hw *hw);

/* Bulk registration */
int devm_clk_hw_register(struct device *dev, struct clk_hw *hw);
```

### Provider-Specific APIs

#### Fixed-Rate Clock

```c
#include <linux/clk-provider.h>

static struct clk_fixed_rate my_fixed_clk = {
    .fixed_rate = 24000000,  /* 24 MHz */
    .hw.init = &(struct clk_init_data){
        .name = "osc_24m",
        .ops = &clk_fixed_rate_ops,
    },
};

/* Register */
clk_hw_register_fixed_rate(NULL, "osc_24m", NULL, 0, 24000000);

/* Or with devm */
devm_clk_hw_register_fixed_rate(dev, "osc_24m", NULL, 0, 24000000);
```

#### Gate Clock

```c
static struct clk_gate my_gate = {
    .reg = base + CLK_ENABLE_REG,
    .bit_idx = 4,
    .lock = &my_lock,
    .hw.init = &(struct clk_init_data){
        .name = "uart_clk_gate",
        .ops = &clk_gate_ops,
        .parent_hws = (const struct clk_hw *[]){ &parent_hw },
        .num_parents = 1,
        .flags = CLK_SET_RATE_PARENT,
    },
};
```

#### Divider Clock

```c
static struct clk_divider my_div = {
    .reg = base + CLK_DIV_REG,
    .shift = 0,
    .width = 4,           /* 4-bit divider (1-16) */
    .lock = &my_lock,
    .hw.init = &(struct clk_init_data){
        .name = "cpu_clk_div",
        .ops = &clk_divider_ops,
        .parent_hws = (const struct clk_hw *[]){ &pll_hw },
        .num_parents = 1,
    },
};
```

#### Mux Clock

```c
static struct clk_mux my_mux = {
    .reg = base + CLK_MUX_REG,
    .shift = 0,
    .width = 2,           /* 2-bit mux (4 parents) */
    .lock = &my_lock,
    .hw.init = &(struct clk_init_data){
        .name = "sys_clk_mux",
        .ops = &clk_mux_ops,
        .parent_hws = (const struct clk_hw *[]){
            &osc_24m_hw,
            &pll_sys_hw,
            &pll_ddr_hw,
            &osc_32k_hw,
        },
        .num_parents = 4,
    },
};
```

#### Composite Clock

A composite clock combines mux, divider, and gate:

```c
static struct clk_composite my_composite = {
    .mux_hw = &my_mux.hw,
    .divider_hw = &my_div.hw,
    .gate_hw = &my_gate.hw,
};

static struct clk_hw * const composite_parents[] = {
    &osc_24m_hw,
    &pll_sys_hw,
};

CLK_HW_DEFINE_PARENTS(my_comp, composite_parents, &clk_composite_ops);
```

### Consumer API

Drivers consume clocks using a simple API:

```c
#include <linux/clk.h>

/* Get a clock reference */
struct clk *clk = clk_get(dev, "uart_clk");
/* Or by index */
struct clk *clk = devm_clk_get(dev, 0);
/* Or by optional clock (may be NULL) */
struct clk *clk = devm_clk_get_optional(dev, "aux_clk");

/* Prepare and enable */
clk_prepare_enable(clk);

/* Set rate (may adjust parent) */
clk_set_rate(clk, 115200 * 16);

/* Get current rate */
unsigned long rate = clk_get_rate(clk);

/* Disable and unprepare */
clk_disable_unprepare(clk);

/* Release */
clk_put(clk);  /* Not needed with devm_ variants */
```

### Consumer Convenience Functions

```c
/* Bulk operations */
struct clk_bulk_data clks[] = {
    { .id = "pclk" },
    { .id = "ref_clk" },
};

int ret = devm_clk_bulk_get(dev, ARRAY_SIZE(clks), clks);
if (ret)
    return ret;

clk_bulk_prepare_enable(ARRAY_SIZE(clks), clks);
/* ... use clocks ... */
clk_bulk_disable_unprepare(ARRAY_SIZE(clks), clks);
```

## Rate Control

### Clock Rate Negotiation

When a consumer calls `clk_set_rate()`, the framework propagates the rate request up the clock tree:

1. Consumer requests rate R from clock C.
2. C may need to adjust its parent's rate to achieve R.
3. The parent may adjust its parent, and so on.
4. The framework finds the best achievable rate.

The `CLK_SET_RATE_PARENT` flag determines whether a clock can propagate rate changes to its parent:

```c
.flags = CLK_SET_RATE_PARENT,  /* Allow parent rate changes */
// or
.flags = 0,                    /* Don't touch parent rate */
```

### Rate Rounding

```c
/* Round to nearest achievable rate */
long rounded = clk_round_rate(clk, desired_rate);

/* Round up */
long rounded = clk_round_rate(clk, desired_rate); /* May round up or down */
/* Use clk_round_rate() to find best achievable rate before setting */
```

### Rate Change Notifications

Drivers can be notified when a clock rate changes:

```c
static int my_rate_notifier(struct notifier_block *nb,
                            unsigned long action,
                            void *data)
{
    struct clk_notifier_data *cnd = data;

    switch (action) {
    case PRE_RATE_CHANGE:
        /* Rate is about to change */
        break;
    case POST_RATE_CHANGE:
        /* Rate has changed */
        break;
    case ABORT_RATE_CHANGE:
        /* Rate change was aborted */
        break;
    }
    return NOTIFY_OK;
}

struct notifier_block nb = {
    .notifier_call = my_rate_notifier,
};

clk_notifier_register(clk, &nb);
```

## CLK_NOEFFECT

Some clock operations may be **no-ops** depending on the hardware:

```c
/* CLK_SET_RATE_NOEFFECT: rate change has no effect on this clock */
/* Used when a clock's rate is fixed despite having a divider */
.flags = CLK_SET_RATE_NOEFFECT,

/* CLK_PARENT_NOEFFECT: parent change has no effect */
/* Used when a mux has only one valid parent */
```

These flags optimize the clock tree by preventing unnecessary traversals.

### CLK_SET_RATE_NOEFFECT

When set, `clk_set_rate()` on this clock returns success but doesn't actually change the hardware. This is useful for:

- Clocks that are always at a fixed rate despite having a divider
- Clocks whose rate is controlled by firmware
- Debug/audit clocks that shouldn't affect hardware

### CLK_IGNORE_UNUSED

```c
.flags = CLK_IGNORE_UNUSED,
```

This tells the framework to **not disable** this clock during late init, even if no consumer has claimed it. Used for:

- Clocks that must always be on (e.g., debug clocks)
- Clocks whose consumers aren't probed yet
- Critical system clocks

### CLK_IS_CRITICAL

```c
.flags = CLK_IS_CRITICAL,
```

Similar to `CLK_IGNORE_UNUSED` but stronger: the clock cannot be disabled at all, even explicitly. Used for clocks that must never be turned off (e.g., DRAM controller clock).

## Clock Tree Debugging

### /sys/kernel/debug/clk/

The clock framework exposes detailed information via debugfs:

```bash
# List all clocks and their tree
cat /sys/kernel/debug/clk/clk_summary

# Output:
#  clock                         enable_cnt  prepare_cnt  rate        accuracy  phase
# -------------------------------------------------------------------------------------------------
#  osc_24m                       1           1            24000000    0         0
#    pll_sys                     1           1            1200000000  0         0
#      cpu_clk                   1           1            1200000000  0         0
#        cpu_clk_div             1           1            600000000   0         0
#      periph_clk                3           3            300000000   0         0
#        uart_clk                1           1            300000000   0         0
#        spi_clk                 1           1            300000000   0         0
#        i2c_clk                 1           1            12000000    0         0
#  osc_32k                       1           1            32768       0         0
#    rtc_clk                     1           1            32768       0         0

# Detailed clock info
cat /sys/kernel/debug/clk/uart_clk/clk_enable_count
cat /sys/kernel/debug/clk/uart_clk/clk_prepare_count
cat /sys/kernel/debug/clk/uart_clk/clk_rate
cat /sys/kernel/debug/clk/uart_clk/clk_accuracy
cat /sys/kernel/debug/clk/uart_clk/clk_phase
cat /sys/kernel/debug/clk/uart_clk/clk_flags
cat /sys/kernel/debug/clk/uart_clk/clk_parent
```

### clk_summary Fields

| Field | Description |
|-------|-------------|
| `enable_cnt` | Number of enables minus disables |
| `prepare_cnt` | Number of prepares minus unprepares |
| `rate` | Current frequency in Hz |
| `accuracy` | Accuracy in ppb (parts per billion) |
| `phase` | Phase offset in degrees |

### Runtime Rate Control

```bash
# Some platforms allow changing clock rates via debugfs
echo 48000000 > /sys/kernel/debug/clk/uart_clk/clk_rate
```

## Common Clock Flags

| Flag | Description |
|------|-------------|
| `CLK_SET_RATE_PARENT` | Allow rate changes to propagate to parent |
| `CLK_SET_RATE_NOGATE` | Don't gate clock during rate change |
| `CLK_SET_RATE_NOEFFECT` | Rate change has no hardware effect |
| `CLK_IGNORE_UNUSED` | Don't disable during late init unused check |
| `CLK_IS_CRITICAL` | Never disable, even if requested |
| `CLK_OPS_PARENT_ENABLE` | Ensure parent is enabled before ops |
| `CLK_GET_RATE_NOCACHE` | Always read rate from hardware |
| `CLK_SET_RATE_UNGATE` | Ungate clock during rate change |
| `CLK_IS_BASIC` | Basic clock (not a composite) |
| `CLK_DUTY_CYCLE_PARENT` | Duty cycle follows parent |

## Platform Clock Driver Example

A typical SoC clock driver registers the entire clock tree:

```c
#include <linux/clk-provider.h>
#include <linux/platform_device.h>

static int my_soc_clk_probe(struct platform_device *pdev)
{
    struct device *dev = &pdev->dev;
    struct clk_hw *hw;
    struct clk_hw_onecell_data *clk_data;

    /* Allocate clock data */
    clk_data = devm_kmalloc(dev,
        struct_size(clk_data, hws, MY_NUM_CLKS), GFP_KERNEL);
    clk_data->num = MY_NUM_CLKS;

    /* Register fixed oscillator */
    hw = devm_clk_hw_register_fixed_rate(dev, "osc_24m", NULL, 0, 24000000);
    clk_data->hws[MY_CLK_OSC_24M] = hw;

    /* Register PLL */
    hw = devm_clk_hw_register_pll(dev, "pll_sys", "osc_24m", &pll_ops);
    clk_data->hws[MY_CLK_PLL_SYS] = hw;

    /* Register divider */
    hw = devm_clk_hw_register_divider(dev, "cpu_div", "pll_sys",
                                       0, base + CPU_DIV_REG, 0, 4, 0, NULL);
    clk_data->hws[MY_CLK_CPU_DIV] = hw;

    /* Register gate */
    hw = devm_clk_hw_register_gate(dev, "uart_gate", "periph_clk",
                                    0, base + UART_CLK_REG, 4, 0, NULL);
    clk_data->hws[MY_CLK_UART_GATE] = hw;

    /* Register the whole tree */
    return devm_of_clk_add_hw_provider(dev, of_clk_hw_onecell_get, clk_data);
}

static const struct of_device_id my_soc_clk_ids[] = {
    { .compatible = "myvendor,my-soc-clk" },
    { }
};

static struct platform_driver my_soc_clk_driver = {
    .probe = my_soc_clk_probe,
    .driver = { .name = "my-soc-clk", .of_match_table = my_soc_clk_ids },
};
```

### Device Tree Binding

```dts
osc_24m: oscillator {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <24000000>;
};

pll_sys: pll@1000 {
    compatible = "myvendor,my-soc-pll";
    #clock-cells = <0>;
    clocks = <&osc_24m>;
    reg = <0x1000 0x100>;
};

uart_clk: uart_clk@2000 {
    compatible = "myvendor,my-soc-clk";
    #clock-cells = <1>;
    clocks = <&pll_sys>;
    reg = <0x2000 0x100>;
};

/* Consumer */
uart0: serial@3000 {
    compatible = "myvendor,my-uart";
    clocks = <&uart_clk 0>;
    clock-names = "uart_clk";
    reg = <0x3000 0x100>;
};
```

## Clock Provider Callbacks

Each clock type implements these operations:

```c
struct clk_ops {
    /* Preparation (may sleep) */
    int (*prepare)(struct clk_hw *hw);
    void (*unprepare)(struct clk_hw *hw);

    /* Enable/disable (atomic, may not sleep) */
    int (*enable)(struct clk_hw *hw);
    void (*disable)(struct clk_hw *hw);
    int (*is_enabled)(struct clk_hw *hw);

    /* Rate management */
    unsigned long (*recalc_rate)(struct clk_hw *hw, unsigned long parent_rate);
    long (*round_rate)(struct clk_hw *hw, unsigned long rate,
                       unsigned long *parent_rate);
    int (*set_rate)(struct clk_hw *hw, unsigned long rate,
                    unsigned long parent_rate);

    /* Parent management */
    unsigned long (*recalc_accuracy)(struct clk_hw *hw,
                                     unsigned long parent_accuracy);
    u8 (*get_parent)(struct clk_hw *hw);
    int (*set_parent)(struct clk_hw *hw, u8 index);

    /* Phase management */
    int (*get_phase)(struct clk_hw *hw);
    int (*set_phase)(struct clk_hw *hw, int degrees);

    /* Duty cycle */
    int (*get_duty_cycle)(struct clk_hw *hw, struct clk_duty *duty);
    int (*set_duty_cycle)(struct clk_hw *hw, struct clk_duty *duty);
};
```

## prepare vs enable

The clock framework has two levels of activation:

| Operation | May Sleep | Purpose |
|-----------|-----------|---------|
| `clk_prepare()` | Yes | Enable clock output (may involve I2C/SPI) |
| `clk_enable()` | No | Gate the clock (atomic) |
| `clk_disable()` | No | Ungate the clock |
| `clk_unprepare()` | Yes | Disable clock output |

The prepare/enable split exists because some clock controllers are connected via slow buses (I2C, SPI). The `prepare` phase handles these slow operations and can sleep, while `enable` is a fast, atomic gate operation.

Most drivers use the combined `clk_prepare_enable()` / `clk_disable_unprepare()`.

## Common Pitfalls

1. **Missing CLK_SET_RATE_PARENT**: if you need to change a child clock's rate, ensure `CLK_SET_RATE_PARENT` is set on all clocks in the path to the oscillator.
2. **prepare/enable ordering**: always prepare before enable, and unprepare after disable. The combined functions handle this.
3. **Error handling**: check return values from `clk_get()`, `clk_prepare_enable()`, etc.
4. **Unused clocks**: the framework logs warnings for clocks that are prepared/enabled but not claimed. Use `CLK_IGNORE_UNUSED` if intentional.
5. **Rate rounding**: `clk_set_rate()` may set a different rate than requested. Always check with `clk_get_rate()`.

## Source Files

- `drivers/clk/clk.c` — core clock framework
- `drivers/clk/clk-fixed-rate.c` — fixed-rate clock
- `drivers/clk/clk-gate.c` — gate clock
- `drivers/clk/clk-divider.c` — divider clock
- `drivers/clk/clk-mux.c` — mux clock
- `drivers/clk/clk-composite.c` — composite clock
- `drivers/clk/clk-fixed-factor.c` — fixed-factor (multiply/divide)
- `include/linux/clk-provider.h` — provider API
- `include/linux/clk.h` — consumer API
- `drivers/clk/<vendor>/` — vendor-specific clock drivers

## Further Reading

- **Documentation/driver-api/clk.rst** — comprehensive clock framework documentation
- **Documentation/devicetree/bindings/clock/** — DT bindings for clocks
- **LWN: The common clock framework** — <https://lwn.net/Articles/514907/>
- **Mike Turquette's LPC presentation** — original CCF design overview
- **Device Tree Specification** — clock bindings
- **ARM SoC clock driver examples** — `drivers/clk/sunxi/`, `drivers/clk/rockchip/`, `drivers/clk/imx/`

## See Also

- Device Tree — hardware description
- Device Model — Linux device model
- Power Management — clock gating for power savings
- [Regulator Framework](../drivers/regulator.md) — voltage regulators
- [GPIO](../drivers/gpio.md) — GPIO subsystem
