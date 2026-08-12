# Thermal Framework

## Overview

The Linux **thermal framework** provides a unified mechanism for monitoring
system temperatures and managing thermal constraints. It abstracts hardware
thermal sensors, cooling devices, and thermal policies into a coherent
software architecture that prevents hardware damage from overheating while
balancing performance.

The framework is essential for modern systems — from mobile phones and laptops
to servers and embedded devices — where thermal management directly impacts
performance, power consumption, and hardware longevity.

## Architecture

### Three Core Abstractions

The thermal framework is built on three primary abstractions:

```
+------------------+     +------------------+     +------------------+
|   Thermal Zone   |     |    Governor      |     |  Cooling Device  |
|  (temperature    |────▶|  (policy engine) |────▶|  (actuator: fan, |
|   source)        |     |                  |     |   CPU throttle)  |
+------------------+     +------------------+     +------------------+
```

1. **Thermal Zone**: represents a temperature source (sensor)
2. **Governor**: implements the thermal policy (when and how to cool)
3. **Cooling Device**: represents a device that can reduce heat generation
   or increase dissipation

### Sysfs Interface

All thermal framework components are exposed under `/sys/class/thermal/`:

```
/sys/class/thermal/
├── cooling_device0/
│   ├── type
│   ├── cur_state
│   ├── max_state
│   └── ...
├── thermal_zone0/
│   ├── type
│   ├── temp
│   ├── mode
│   ├── policy
│   ├── trip_point_0_temp
│   ├── trip_point_0_type
│   └── ...
├── thermal_zone1/
│   └── ...
└── ...
```

## Thermal Zones

### What a Thermal Zone Represents

A thermal zone represents a region of the system whose temperature is
monitored. Each zone has:

- **One or more temperature sensors** (hardware or virtual)
- **Trip points**: temperature thresholds that trigger actions
- **A governor**: the policy that determines how to respond
- **Bound cooling devices**: actuators controlled by the zone

### Trip Points

Trip points define temperature thresholds:

| Type           | Description                                        |
|----------------|----------------------------------------------------|
| `passive`      | Temperature at which passive cooling activates     |
| `active`       | Temperature at which active cooling (fans) activates|
| `hot`          | Temperature at which the system should shut down   |
| `critical`     | Temperature at which the kernel forces shutdown    |

Trip points are defined in the device tree, ACPI tables, or platform data:

```c
/* Device tree example */
thermal-zones {
    cpu_thermal: cpu-thermal {
        polling-delay-passive = <250>;  /* ms */
        polling-delay = <1000>;         /* ms */

        thermal-sensors = <&tsensor 0>;

        trips {
            cpu_alert0: trip0 {
                temperature = <85000>;  /* millidegrees C */
                hysteresis = <2000>;
                type = "passive";
            };
            cpu_alert1: trip1 {
                temperature = <95000>;
                hysteresis = <2000>;
                type = "hot";
            };
            cpu_crit: trip2 {
                temperature = <105000>;
                hysteresis = <2000>;
                type = "critical";
            };
        };

        cooling-maps {
            map0 {
                trip = <&cpu_alert0>;
                cooling-device = <&cpu0 THERMAL_NO_LIMIT THERMAL_NO_LIMIT>;
            };
        };
    };
};
```

### Thermal Zone Registration

```c
#include <linux/thermal.h>

struct thermal_zone_device *tz;
tz = thermal_zone_device_register(
    "my_thermal_zone",   /* name */
    num_trips,           /* number of trip points */
    mask,                /* trip point bitmask */
    data,                /* driver data */
    &ops,                /* thermal zone operations */
    &params,             /* thermal zone params */
    passive_delay,       /* polling delay in passive mode (ms) */
    polling_delay        /* polling delay in normal mode (ms) */
);
```

### Thermal Zone Operations

```c
struct thermal_zone_device_ops {
    int (*bind)(struct thermal_zone_device *, struct thermal_cooling_device *);
    int (*unbind)(struct thermal_zone_device *, struct thermal_cooling_device *);
    int (*get_temp)(struct thermal_zone_device *, int *temp);
    int (*set_trips)(struct thermal_zone_device *, int low, int high);
    int (*get_mode)(struct thermal_zone_device *, enum thermal_device_mode *);
    int (*set_mode)(struct thermal_zone_device *, enum thermal_device_mode);
    int (*get_trip_type)(struct thermal_zone_device *, int, enum thermal_trip_type *);
    int (*get_trip_temp)(struct thermal_zone_device *, int, int *);
    int (*set_trip_temp)(struct thermal_zone_device *, int, int);
    int (*get_trip_hyst)(struct thermal_zone_device *, int, int *);
    int (*set_trip_hyst)(struct thermal_zone_device *, int, int);
    int (*get_crit_temp)(struct thermal_zone_device *, int *);
    int (*set_emul_temp)(struct thermal_zone_device *, int);
};
```

The most critical callback is `get_temp()` — the driver must return the
current temperature in millidegrees Celsius.

### Thermal Zone Parameters

```c
struct thermal_zone_params {
    char governor_name[THERMAL_NAME_LENGTH];
    /* ... */
};
```

## Governors

Governors implement the thermal policy — they decide what actions to take
based on the current temperature relative to trip points.

### Step-Wise Governor

The simplest governor. It increases or decreases cooling state one step at
a time:

```
Temperature < trip - hysteresis  →  Decrease cooling by 1 step
Temperature > trip               →  Increase cooling by 1 step
Temperature in hysteresis band   →  No change
```

**Use case**: simple systems with linear cooling response.

### Power Allocator Governor

The most sophisticated governor, implementing a **PID controller** that
allocates power budget across multiple cooling devices:

```c
struct power_allocator_params {
    s32 err_integral;    /* PID integral term */
    s32 prev_err;        /* Previous error for derivative term */
    /* ... */
};
```

**How it works**:

1. Compute the **sustainable power** based on the current temperature and
   the target (first passive trip point)
2. Use a PID controller to determine the power budget:
   ```
   err = sustainable_power - current_power
   power_budget = sustainable_power + k_p * err + k_i * err_integral + k_d * d(err)/dt
   ```
3. Allocate the power budget across cooling devices proportionally to their
   power characteristics

**Device tree configuration**:

```c
&cpu_thermal {
    policy = "power_allocator";
    sustainable-power = <3000>;  /* milliwatts */
    k_p = <0>;
    k_i = <0>;
    k_d = <0>;
};
```

**Use case**: modern mobile devices, laptops, and servers where power
budgeting is more effective than step-wise throttling.

### User-Space Governor

Delegates thermal policy to a userspace daemon:

```bash
# Switch to user-space governor
echo user_space > /sys/class/thermal/thermal_zone0/policy

# Read temperature
cat /sys/class/thermal/thermal_zone0/temp
# 45000  (45°C)

# Control cooling device
echo 3 > /sys/class/thermal/cooling_device0/cur_state
```

**Use case**: custom thermal management daemons (e.g., Android's thermal HAL).

### Bang-Bang Governor

A binary governor — cooling is either fully on or fully off based on trip
point thresholds:

```
Temperature > trip  →  Cooling ON  (max state)
Temperature < trip - hysteresis  →  Cooling OFF (state 0)
```

**Use case**: simple fan control.

### Governor Selection

```bash
# List available governors
cat /sys/class/thermal/thermal_zone0/available_policies

# Change governor
echo power_allocator > /sys/class/thermal/thermal_zone0/policy
```

## Cooling Devices

### Types of Cooling Devices

| Type                 | Implementation                     | Description              |
|----------------------|------------------------------------|--------------------------|
| CPU frequency throttle| `cpufreq_cooling`                 | Reduces CPU clock speed  |
| CPU idle injection   | `intel_powerclamp` / `idle_inject`| Forces CPU idle periods  |
| Fan speed control    | `fan` (hwmon)                     | Adjusts fan RPM          |
| GPU throttle         | Platform-specific                 | Reduces GPU clock/power  |
| Device power control | Platform-specific                 | Powers down devices      |
| Memory bandwidth    | `mem_cooling`                     | Limits memory bandwidth  |

### CPU Frequency Cooling

The most common cooling device. It limits CPU frequency to reduce heat:

```c
/* Registration */
struct thermal_cooling_device *cdev;
cdev = cpufreq_cooling_register(policy);

/* Or via device tree binding */
/* cooling-device = <&cpu0 THERMAL_NO_LIMIT THERMAL_NO_LIMIT>; */
```

States correspond to frequency limits:

```
State 0: Maximum frequency (no throttling)
State 1: One step below maximum
...
State N: Minimum frequency (maximum throttling)
```

### CPU Idle Injection Cooling

Forces CPUs into idle states to reduce power (and thus heat) without
changing frequency:

```c
/* intel_powerclamp: injects idle periods */
/* Idle injection ratio determines cooling level */
/* 0% = no idle (no cooling), 100% = always idle (maximum cooling) */
```

**Advantages over frequency throttling**:
- Maintains burst performance (frequency stays high during active periods)
- More predictable power reduction
- Works on CPUs without fine-grained frequency control

### Custom Cooling Devices

Drivers can register custom cooling devices:

```c
static struct thermal_cooling_device_ops my_cooling_ops = {
    .get_max_state = my_get_max_state,
    .get_cur_state = my_get_cur_state,
    .set_cur_state = my_set_cur_state,
};

struct thermal_cooling_device *cdev;
cdev = thermal_cooling_device_register(
    "my_cooler",    /* name */
    data,           /* driver data */
    &my_cooling_ops /* operations */
);
```

## Hardware Monitoring Integration

### hwmon Bridge

The thermal framework integrates with the **hwmon** (hardware monitoring)
subsystem:

```bash
# hwmon exposes temperature sensors under /sys/class/hwmon/
cat /sys/class/hwmon/hwmon0/temp1_input
# 45000  (45°C)
```

Many thermal zone drivers read temperature from hwmon sensors.

### ACPI Thermal Zones

On x86 systems, ACPI provides thermal zone definitions:

```bash
# ACPI thermal zones
ls /sys/class/thermal/thermal_zone*
# /sys/class/thermal/thermal_zone0  (TZ00)
# /sys/class/thermal/thermal_zone1  (TZ01)

# Read ACPI thermal zone
cat /sys/class/thermal/thermal_zone0/temp
```

ACPI thermal zones are handled by `drivers/thermal/acpi/thermal.c`.

### Device Tree Thermal Zones

On ARM/embedred systems, thermal zones are defined in the device tree and
parsed by the generic thermal framework:

```c
/* Device tree thermal sensor driver */
static const struct of_device_id my_sensor_of_match[] = {
    { .compatible = "vendor,thermal-sensor" },
    { /* sentinel */ }
};
```

## Intel-Specific Thermal Features

### x86 Package Thermal Throttling

Intel CPUs have per-package thermal management:

```bash
# Check package thermal status
cat /sys/devices/system/cpu/cpu0/thermal/throttle/package_0/total_time_ms

# Per-core thermal throttling
cat /sys/devices/system/cpu/cpu0/thermal/throttle/core_0/total_time_ms
```

### Intel DPTF (Dynamic Platform and Thermal Framework)

DPTF is Intel's comprehensive thermal management platform, often implemented
as an ACPI-based thermal driver in the kernel.

### Intel RAPL (Running Average Power Limit)

RAPL provides power limiting that can be used for thermal management:

```bash
# RAPL power limits
cat /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw
# 25000000  (25W)
```

## ARM Thermal Features

### SCPI Thermal Sensors

ARM systems using SCPI (System Control and Processing Interface) firmware:

```c
/* SCPI thermal driver */
scpi_sensor_get_value(sensor_id, &temperature);
```

### SoC-Specific Drivers

Most ARM SoCs have dedicated thermal drivers:

- **Samsung Exynos**: `exynos_thermal.c`
- **Rockchip**: `rockchip_thermal.c`
- **MediaTek**: `mtk_thermal.c`
- **Qualcomm**: `qcom-spmi-temp-alarm.c`, `tsens.c`
- **Allwinner**: `sun8i_thermal.c`

## Thermal Emergency Handling

### Critical Temperature Shutdown

When temperature reaches the critical trip point, the framework initiates
an emergency shutdown:

```c
static void handle_thermal_trip(struct thermal_zone_device *tz, int trip)
{
    enum thermal_trip_type type;
    tz->ops->get_trip_type(tz, trip, &type);

    if (type == THERMAL_TRIP_CRITICAL) {
        pr_emerg("Critical temperature reached (%d C), shutting down!\n",
                 temperature / 1000);
        orderly_poweroff(true);
    }
}
```

### Thermal Notification

The framework sends notifications to registered users:

```c
/* Register for thermal notifications */
register_thermal_notifier(&my_notifier);

/* Notifier callback */
int my_callback(struct notifier_block *nb, unsigned long event, void *data) {
    switch (event) {
    case THERMAL_CRITICAL:
        /* Handle critical temperature */
        break;
    case THERMAL_TZ_TRIP:
        /* Handle trip point crossing */
        break;
    }
    return NOTIFY_OK;
}
```

## Monitoring and Debugging

### Temperature Reading

```bash
# All thermal zones
for tz in /sys/class/thermal/thermal_zone*; do
    echo "$(basename $tz): $(cat $tz/type) = $(cat $tz/temp) mC"
done

# Specific zone
cat /sys/class/thermal/thermal_zone0/temp
# 45000  (45°C)
```

### Trip Point Configuration

```bash
# Read trip points
cat /sys/class/thermal/thermal_zone0/trip_point_0_temp
cat /sys/class/thermal/thermal_zone0/trip_point_0_type

# List all trip points
grep -H . /sys/class/thermal/thermal_zone0/trip_point_*_type
```

### Cooling Device Status

```bash
# List cooling devices
for cd in /sys/class/thermal/cooling_device*; do
    echo "$(basename $cd): $(cat $cd/type) state=$(cat $cd/cur_state)/$(cat $cd/max_state)"
done
```

### Thermal Statistics

```bash
# Throttling statistics
cat /sys/devices/system/cpu/cpu0/thermal/throttle/core_0/total_time_ms
cat /sys/devices/system/cpu/cpu0/thermal/throttle/package_0/total_time_ms
```

### Debugfs

Some drivers expose additional thermal debugging via debugfs:

```bash
# Enable thermal debugging
echo 'thermal:7' > /sys/kernel/debug/dynamic_debug/control
dmesg | grep thermal
```

## Common Configurations

### Laptop Thermal Management

```bash
# Set passive cooling trip point
echo 80000 > /sys/class/thermal/thermal_zone0/trip_point_0_temp

# Use power_allocator for balanced performance
echo power_allocator > /sys/class/thermal/thermal_zone0/policy

# Control fan manually (if supported)
echo 2 > /sys/class/hwmon/hwmon1/pwm1_enable  # manual
echo 150 > /sys/class/hwmon/hwmon1/pwm1       # 0-255
```

### Server Thermal Management

```bash
# Conservative cooling for noise reduction
echo step_wise > /sys/class/thermal/thermal_zone0/policy

# Monitor all zones
watch -n 1 'for tz in /sys/class/thermal/thermal_zone*; do echo "$(cat $tz/type): $(cat $tz/temp)mC"; done'
```

### Embedded/IoT

```bash
# Tight thermal control
echo 75000 > /sys/class/thermal/thermal_zone0/trip_point_0_temp
echo power_allocator > /sys/class/thermal/thermal_zone0/policy
echo 2000 > /sys/class/thermal/thermal_zone0/sustainable_power
```

## See Also

- [vmpressure](../memory/vmpressure.md) — another graduated notification
  subsystem
- [local_lock](../sync/local-lock.md) — per-CPU synchronization in
  thermal drivers
- [Kernel Lockdown](../../security/lockdown.md) — restrictions on thermal
  debugfs access

## Further Reading

- **Kernel source**: `drivers/thermal/`
- **Documentation**: `Documentation/driver-api/thermal/`
- **Device tree bindings**: `Documentation/devicetree/bindings/thermal/`
- **LWN article**: ["The thermal framework"](https://lwn.net/Articles/573600/) —
  framework overview
- **LWN article**: ["A new thermal governor: power_allocator"](https://lwn.net/Articles/643087/) —
  PID-based thermal management
- **commit a9b6690**: "thermal: add generic cpu cooling implementation" —
  CPU cooling device introduction
- **ARM thermal documentation**: ARM SCPI and DTPM specifications
