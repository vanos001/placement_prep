# Watchdog Timers

## Overview

A **watchdog timer** is a hardware or software mechanism that detects system hangs and automatically resets the system if the kernel fails to "pet" (service) the watchdog within a configured timeout. Watchdogs are essential for embedded systems, servers, and any unattended system where automatic recovery from hangs is required.

The Linux kernel provides a unified **watchdog subsystem** (`drivers/watchdog/`) that abstracts both hardware and software watchdog devices behind a common interface.

> **See also:** Kernel Panic, NMI Watchdog, System Reset

---

## Watchdog Subsystem Architecture

```
┌──────────────────────────────────────────┐
│              Userspace                    │
│   /dev/watchdog — ioctl, write, read     │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│         Watchdog Core (WDT)              │
│   drivers/watchdog/watchdog_core.c       │
│   ┌──────────────────────────────────┐   │
│   │  struct watchdog_device          │   │
│   │  - timeout, pretimeout           │   │
│   │  - ops (start, stop, ping)       │   │
│   │  - status flags                  │   │
│   └──────────────────────────────────┘   │
└──────────────────┬───────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
  ┌─────▼─────┐        ┌─────▼─────┐
  │  Software  │        │  Hardware  │
  │  Watchdog  │        │  Watchdog  │
  │  (softdog) │        │  (WDT)     │
  └───────────┘        └───────────┘
```

---

## /dev/watchdog Interface

### Opening the Watchdog

```c
#include <linux/watchdog.h>
#include <fcntl.h>
#include <sys/ioctl.h>

int fd = open("/dev/watchdog", O_WRONLY);
if (fd < 0) {
    perror("open");
    return 1;
}

/* Pet the watchdog */
write(fd, "\0", 1);

/* Close (stops watchdog if magic close is enabled) */
close(fd);
```

### Magic Close

When `CONFIG_WATCHDOG_MAGIC_CLOSE` is enabled:

- Writing `V` to `/dev/watchdog` before closing disables the watchdog
- Without the magic character, closing the fd **keeps the watchdog running**

```c
/* Disable watchdog on close */
write(fd, "V", 1);
close(fd);
```

### Watchdog ioctls

| ioctl                   | Description                          |
|------------------------|--------------------------------------|
| `WDIOC_GETTIMEOUT`     | Get current timeout (seconds)        |
| `WDIOC_SETTIMEOUT`     | Set timeout (seconds)                |
| `WDIOC_GETPRETIMEOUT`  | Get pretimeout value                 |
| `WDIOC_SETPRETIMEOUT`  | Set pretimeout value                 |
| `WDIOC_GETTIMELEFT`    | Get time left before reset           |
| `WDIOC_KEEPALIVE`      | Pet the watchdog                     |
| `WDIOC_GETSTATUS`      | Get watchdog status flags            |
| `WDIOC_GETBOOTSTATUS`  | Get boot status (was reset watchdog?)|
| `WDIOC_GETSUPPORT`     | Get watchdog_info struct             |

### Example: Configure and Pet

```c
#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/watchdog.h>
#include <unistd.h>

int main(void)
{
    int fd = open("/dev/watchdog0", O_RDWR);
    if (fd < 0) { perror("open"); return 1; }

    /* Set timeout to 30 seconds */
    int timeout = 30;
    ioctl(fd, WDIOC_SETTIMEOUT, &timeout);
    printf("Timeout set to %d seconds\n", timeout);

    /* Set pretimeout to 10 seconds (warning before reset) */
    int pretimeout = 10;
    ioctl(fd, WDIOC_SETPRETIMEOUT, &pretimeout);

    /* Get watchdog info */
    struct watchdog_info ident;
    ioctl(fd, WDIOC_GETSUPPORT, &ident);
    printf("Watchdog: %s (version %d)\n",
           ident.identity, ident.firmware_version);

    /* Pet the watchdog in a loop */
    while (1) {
        ioctl(fd, WDIOC_KEEPALIVE, NULL);
        printf("Watchdog pet\n");
        sleep(10);
    }

    /* Never reached, but for completeness: */
    write(fd, "V", 1);  /* Magic close */
    close(fd);
    return 0;
}
```

---

## Software Watchdog (softdog)

### Overview

`softdog` is a software-based watchdog module. It uses a kernel timer to simulate a hardware watchdog. If the kernel hangs (timer can't fire), the system reboots.

```bash
# Load the module
modprobe softdog

# Verify
ls -l /dev/watchdog*
```

### Module Parameters

| Parameter    | Default | Description                         |
|-------------|---------|-------------------------------------|
| `soft_margin`| 60     | Timeout in seconds before reboot    |
| `nowayout`  | 0       | If 1, watchdog can't be disabled    |
| `soft_noboot`| 0      | If 1, log panic instead of reboot   |

```bash
# Load with custom timeout
modprobe softdog soft_margin=30

# Or set at runtime
echo 30 > /sys/class/watchdog/watchdog0/timeout
```

### Limitations

- **Not a true hardware watchdog** — depends on the kernel scheduler
- Won't detect hard hangs where the CPU is stuck (use NMI watchdog for that)
- Good for: process hangs, kernel soft lockups
- Not good for: hardware failures, CPU lockups

---

## Hardware Watchdog (WDT) Devices

### Common Hardware Watchdog Drivers

| Driver          | Hardware                           |
|-----------------|------------------------------------|
| `iTCO_wdt`     | Intel TCO (most Intel platforms)   |
| `sp5100_tco`   | AMD SP5100/SB8x0                   |
| `w83627hf_wdt` | Winbond/Nuvoton Super I/O          |
| `hpwdt`        | HP ProLiant iLO                    |
| `ipmi_wdog`    | IPMI/BMC watchdog                  |
| `broadcom_wdt` | Broadcom SoCs (Raspberry Pi)       |
| `bcm2835_wdt`  | BCM2835 (Raspberry Pi)             |
| `imx2_wdt`     | i.MX SoC watchdog                  |
| `omap_wdt`     | TI OMAP watchdog                   |
| `stm32_iwdg`  | STM32 Independent Watchdog         |

### Intel TCO Watchdog

```bash
# Load the driver
modprobe iTCO_wdt

# Check status
cat /sys/class/watchdog/watchdog0/timeout
cat /sys/class/watchdog/watchdog0/timeleft

# The TCO watchdog has hardware pretimeout support
echo 10 > /sys/class/watchdog/watchdog0/pretimeout
```

### IPMI Watchdog

For servers with BMC/IPMI:

```bash
modprobe ipmi_watchdog

# Configure via module parameters
modprobe ipmi_watchdog action=reset timeout=30 pretimeout=10 preaction=pre_none

# Or via sysfs
echo 30 > /sys/class/watchdog/watchdog0/timeout
```

---

## sysfs Interface

### Watchdog Attributes

```bash
ls /sys/class/watchdog/watchdog0/

# Key files:
cat /sys/class/watchdog/watchdog0/name         # Driver name
cat /sys/class/watchdog/watchdog0/timeout      # Current timeout (seconds)
cat /sys/class/watchdog/watchdog0/pretimeout   # Pretimeout (seconds)
cat /sys/class/watchdog/watchdog0/timeleft     # Time remaining
cat /sys/class/watchdog/watchdog0/state        # active/inactive
cat /sys/class/watchdog/watchdog0/bootstatus   # Last reset cause
```

### Setting Attributes

```bash
# Change timeout
echo 30 > /sys/class/watchdog/watchdog0/timeout

# Set pretimeout (warning before reset)
echo 10 > /sys/class/watchdog/watchdog0/pretimeout

# Start/stop watchdog
echo 1 > /sys/class/watchdog/watchdog0/state   # Start
echo 0 > /sys/class/watchdog/watchdog0/state   # Stop (if nowayout=0)
```

---

## Pretimeout

### Concept

The **pretimeout** feature adds a warning period before the watchdog fires. When the pretimeout expires:

1. A **pretimeout handler** is called (default: panic, or custom)
2. The system gets a chance to log diagnostics or save state
3. After the full timeout, the watchdog resets the system

```
Timeline:
  0s                pretimeout         full timeout
  |──────────────────|──────────────────|
  |  Normal operation|  Pretimeout      |  Reset
  |  (petting)       |  warning         |
```

### Pretimeout Handlers

| Handler   | Action                                  |
|-----------|-----------------------------------------|
| `panic`   | Trigger kernel panic (default)          |
| `pre_none`| No action (just log)                    |
| `pretime` | Log pretimeout event                    |

```bash
# Set pretimeout handler
echo "pre_none" > /sys/class/watchdog/watchdog0/pretimeout governor

# Available governors
cat /sys/class/watchdog/watchdog0/pretimeout_available_governors
```

### Custom Pretimeout Handler

```c
/* Kernel code: register a pretimeout handler */
#include <linux/watchdog.h>

static void my_pretimeout_handler(struct watchdog_device *wdd)
{
    pr_crit("WATCHDOG PRETIMEOUT: system about to reset!\n");
    /* Dump diagnostics, save crash info, etc. */
    dump_stack();
}

static const struct watchdog_ops my_wdt_ops = {
    .owner      = THIS_MODULE,
    .start      = my_wdt_start,
    .stop       = my_wdt_stop,
    .ping       = my_wdt_ping,
    .set_timeout = my_wdt_set_timeout,
};
```

---

## Watchdog Kernel Configuration

### Kconfig Options

```
CONFIG_WATCHDOG=y              # Enable watchdog subsystem
CONFIG_WATCHDOG_CORE=y         # Core framework
CONFIG_WATCHDOG_NOWAYOUT=0     # Allow disabling watchdog
CONFIG_SOFT_WATCHDOG=m         # Software watchdog module
CONFIG_I6300ESB_WDT=m          # Intel 6300ESB watchdog
CONFIG_IPMI_WATCHDOG=m         # IPMI watchdog
CONFIG_BCM2835_WDT=m           # Raspberry Pi watchdog
```

### Device Tree (Embedded)

```dts
/* Typical ARM SoC watchdog */
wdt: watchdog@44e35000 {
    compatible = "ti,omap3-wdt";
    reg = <0x44e35000 0x100>;
    interrupts = <91>;
    clocks = <&l4_wkup_clkctrl OMAP4_WDT_TIMER2_CLKCTRL 0>;
    power-domains = <&prm_per>;
};
```

---

## Systemd Integration

### watchdog.service

systemd can automatically pet the watchdog:

```ini
# /etc/systemd/system.conf
RuntimeWatchdogSec=20
RuntimeWatchdogPreSec=10
ShutdownWatchdogSec=10min
```

### Service Watchdog

Individual services can use watchdog notifications:

```ini
[Service]
WatchdogSec=30
Type=notify
ExecStart=/usr/bin/my-daemon
```

The daemon must call `sd_notify(0, "WATCHDOG=1")` periodically.

### systemd-analyze watchdog

```bash
# Show watchdog configuration
systemd-analyze watchdog

# Output:
# System watchdog: /dev/watchdog0
# Hardware watchdog: iTCO_wdt
# Timeout: 30s
# Pretimeout: 10s
```

---

## Embedded Use Cases

### Raspberry Pi

```bash
# Load the BCM2835 watchdog
modprobe bcm2835_wdt

# Set timeout
echo 15 > /sys/class/watchdog/watchdog0/timeout

# Pet with systemd
echo "RuntimeWatchdogSec=10" >> /etc/systemd/system.conf
```

### Custom Embedded System

```bash
# Minimal watchdog script
#!/bin/sh
while true; do
    echo 1 > /dev/watchdog0  # Pet
    sleep 5
done
```

### Buildroot/Yocto

```
# In buildroot config
BR2_PACKAGE_WATCHDOG=y
BR2_PACKAGE_WATCHDOG_CONF="timeout=30"
```

---

## NMI Watchdog (Separate Concept)

The **NMI watchdog** is not related to `/dev/watchdog`. It uses Non-Maskable Interrupts to detect CPU lockups:

```bash
# Enable NMI watchdog
echo 1 > /proc/sys/kernel/nmi_watchdog

# Or at boot
# nmi_watchdog=1
```

When a CPU is stuck with interrupts disabled, the NMI watchdog triggers a panic with a stack trace.

> **See also:** NMI Watchdog, Soft Lockup Detection

---

## Debugging Watchdog Resets

### Boot Status

```bash
# Check if last reset was caused by watchdog
cat /sys/class/watchdog/watchdog0/bootstatus

# Or via dmesg
dmesg | grep -i watchdog
```

### Common Reset Causes

| Boot Status Bit | Meaning                    |
|-----------------|----------------------------|
| `WDIOF_OVERHEAT`| Reset due to overheating   |
| `WDIOF_EXTERN1` | External signal 1          |
| `WDIOF_EXTERN2` | External signal 2          |
| `WDIOF_POWERUNDER` | Power failure           |
| `WDIOF_CARDRESET` | Card previously reset    |

### Watchdog Daemon Logs

```bash
# Check watchdog daemon logs
journalctl -u watchdog

# Or with verbose logging
watchdog -v -f /dev/watchdog0
```

---

## Watchdog Daemon Patterns

### Simple Watchdog Daemon

```c
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/watchdog.h>
#include <unistd.h>
#include <signal.h>
#include <sys/stat.h>

static int wdt_fd = -1;
static volatile int running = 1;

void handle_signal(int sig) {
    running = 0;
}

int health_check(void) {
    /* Implement your health checks here */
    /* Return 1 if healthy, 0 if not */

    /* Check critical processes */
    if (system("pgrep critical_daemon > /dev/null") != 0)
        return 0;

    /* Check disk space */
    struct statfs fs;
    if (statfs("/", &fs) == 0) {
        if (fs.f_bavail < fs.f_blocks * 5 / 100)  /* < 5% free */
            return 0;
    }

    /* Check network connectivity */
    if (system("ping -c 1 -W 2 gateway > /dev/null 2>&1") != 0)
        return 0;

    return 1;
}

int main(void) {
    int timeout = 30;

    /* Open watchdog */
    wdt_fd = open("/dev/watchdog0", O_RDWR);
    if (wdt_fd < 0) {
        perror("open watchdog");
        return 1;
    }

    /* Set timeout */
    ioctl(wdt_fd, WDIOC_SETTIMEOUT, &timeout);

    /* Daemonize */
    if (daemon(0, 0) < 0) {
        perror("daemon");
        close(wdt_fd);
        return 1;
    }

    /* Signal handling */
    signal(SIGTERM, handle_signal);
    signal(SIGINT, handle_signal);

    /* Main loop */
    while (running) {
        if (health_check()) {
            /* Pet the watchdog */
            ioctl(wdt_fd, WDIOC_KEEPALIVE, NULL);
        } else {
            /* Health check failed - don't pet */
            /* Watchdog will reset the system */
            fprintf(stderr, "Health check failed!\n");
        }
        sleep(timeout / 3);  /* Pet at 1/3 of timeout */
    }

    /* Clean shutdown */
    write(wdt_fd, "V", 1);  /* Magic close */
    close(wdt_fd);
    return 0;
}
```

### Watchdog with Pretimeout Warning

```c
#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/watchdog.h>
#include <unistd.h>

int main(void) {
    int fd = open("/dev/watchdog0", O_RDWR);
    if (fd < 0) return 1;

    /* Set timeout to 60 seconds */
    int timeout = 60;
    ioctl(fd, WDIOC_SETTIMEOUT, &timeout);

    /* Set pretimeout to 40 seconds (20s warning before reset) */
    int pretimeout = 40;
    ioctl(fd, WDIOC_SETPRETIMEOUT, &pretimeout);

    /* Set pretimeout handler to panic */
    /* This triggers a kernel panic before the hard reset */
    /* allowing kdump to capture a crash dump */
    char *governor = "panic";
    /* Note: governor is set via sysfs, not ioctl */

    printf("Timeout: %d, Pretimeout: %d\n", timeout, pretimeout);
    printf("System will panic at %d seconds, reset at %d seconds\n",
           timeout - pretimeout, timeout);

    while (1) {
        ioctl(fd, WDIOC_KEEPALIVE, NULL);
        sleep(10);
    }

    return 0;
}
```

## Watchdog in Production Systems

### Server Watchdog Configuration

```bash
#!/bin/bash
# production-watchdog.sh - Server watchdog setup

# Load hardware watchdog
modprobe iTCO_wdt

# Configure timeout
echo 60 > /sys/class/watchdog/watchdog0/timeout
echo 40 > /sys/class/watchdog/watchdog0/pretimeout

# Set pretimeout governor
echo "panic" > /sys/class/watchdog/watchdog0/pretimeout_governor

# Configure systemd watchdog
cat > /etc/systemd/system.conf.d/watchdog.conf << EOF
[Manager]
RuntimeWatchdogSec=30
RuntimeWatchdogPreSec=20
ShutdownWatchdogSec=5min
EOF

systemctl daemon-reload

echo "Watchdog configured:"
systemd-analyze watchdog
```

### Embedded Linux Watchdog

```bash
#!/bin/sh
# /etc/init.d/watchdog - Embedded watchdog script

WATCHDOG_DEV=/dev/watchdog0
TIMEOUT=30
CHECK_INTERVAL=10

start() {
    echo "Starting watchdog daemon"
    # Set timeout
    echo $TIMEOUT > /sys/class/watchdog/watchdog0/timeout

    # Start watchdog petting in background
    while true; do
        # Check system health
        if check_health; then
            echo 1 > $WATCHDOG_DEV
        fi
        sleep $CHECK_INTERVAL
    done &
    echo $! > /var/run/watchdog.pid
}

check_health() {
    # Check memory usage
    local mem_free=$(awk '/MemFree/ {print $2}' /proc/meminfo)
    if [ "$mem_free" -lt 10240 ]; then
        return 1
    fi

    # Check load average
    local load=$(cat /proc/loadavg | awk '{print $1}' | cut -d. -f1)
    if [ "$load" -gt 10 ]; then
        return 1
    fi

    # Check critical filesystem
    if ! mountpoint -q /data; then
        return 1
    fi

    return 0
}

stop() {
    echo "Stopping watchdog daemon"
    if [ -f /var/run/watchdog.pid ]; then
        kill $(cat /var/run/watchdog.pid)
        rm /var/run/watchdog.pid
    fi
    # Magic close
    echo V > $WATCHDOG_DEV
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
esac
```

## Watchdog and kdump Integration

When a watchdog fires, you often want a crash dump for post-mortem analysis:

```bash
# Configure kdump to capture watchdog-triggered panics
# /etc/default/grub
GRUB_CMDLINE_LINUX="crashkernel=256M softlockup_panic=1"

# Configure watchdog to panic before reset
echo 1 > /proc/sys/kernel/softlockup_panic
echo "panic" > /sys/class/watchdog/watchdog0/pretimeout_governor

# Enable kdump
systemctl enable kdump
systemctl start kdump

# After watchdog reset, analyze crash dump
# crash /var/crash/*/vmlinux /var/crash/*/vmcore
```

## Watchdog Testing

```bash
# Test watchdog timeout
#!/bin/bash
# test-watchdog.sh - Verify watchdog resets the system

# Open watchdog and DON'T pet it
exec 3>/dev/watchdog0
# Don't write anything
# System should reset after timeout

# For software testing, simulate a hang:
# 1. Start a CPU-intensive task
while true; do :; done &

# 2. Disable preemption (kernel only)
# This simulates a soft lockup

# Monitor for watchdog message
dmesg -w | grep -i watchdog
```

## Further Reading

- [Linux kernel source: `drivers/watchdog/`](https://elixir.bootlin.com/linux/latest/source/drivers/watchdog/)
- [kernel.org: Watchdog](https://www.kernel.org/doc/html/latest/watchdog/watchdog-api.html)
- [watchdog(8) man page](https://man7.org/linux/man-pages/man8/watchdog.8.html)
- [watchdog-api.txt](https://www.kernel.org/doc/html/latest/watchdog/watchdog-api.html)
- [systemd: Watchdog](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Raspberry Pi Watchdog](https://www.raspberrypi.com/documentation/computers/configuration.html#watchdog)

> **Related topics:** NMI Watchdog, Kernel Panic, System Reset, Device Drivers
