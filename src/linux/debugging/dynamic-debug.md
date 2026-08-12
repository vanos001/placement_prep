# Dynamic Debug (dyndbg)

## Overview

**Dynamic debug** (`dyndbg`) is a Linux kernel feature that allows runtime enabling and disabling of kernel `pr_debug()` and `dev_dbg()` messages without recompiling the kernel. This is invaluable for debugging driver issues, subsystem behavior, and tracing specific code paths in production systems.

By default, most `pr_debug()` calls are compiled out or disabled. Dynamic debug lets you selectively activate them on a running system.

> **See also:** Kernel Logging, [ftrace](./ftrace.md), printk

---

## How It Works

### Compilation

When `CONFIG_DYNAMIC_DEBUG_CORE=y` (or `CONFIG_DYNAMIC_DEBUG=y`), the compiler converts `pr_debug()` calls into special structures embedded in a dedicated ELF section:

```c
/* What you write: */
pr_debug("Received %d bytes from %pI4\n", len, &addr);

/* What the compiler generates (simplified): */
if (DYNAMIC_DEBUG_BRANCH(descriptor))
    __dynamic_pr_debug(&descriptor, "Received %d bytes from %pI4\n",
                       len, &addr);
```

Each call site gets a `struct _ddebug` descriptor:

```c
struct _ddebug {
    const char *modname;       /* Module name */
    const char *function;      /* Function name */
    const char *filename;      /* Source file */
    const char *format;        /* Format string */
    unsigned int lineno:18;    /* Line number */
    unsigned int flags:8;      /* Control flags */
    /* ... */
};
```

### Control Interface

All dynamic debug control happens through a single file:

```
/sys/kernel/debug/dynamic_debug/control
```

---

## Control File Format

### Reading the Control File

```bash
# View all enabled call sites
cat /sys/kernel/debug/dynamic_debug/control

# Output format:
# filename:lineno [module]function flags format-string
# drivers/net/ethernet/intel/e1000e/netdev.c:1823 [e1000e]e1000_clean_rx_irq =_ "e1000e: %s: rx checksum %s\n"
```

### Flags Column

The flags field shows the current state:

| Flag | Meaning              |
|------|----------------------|
| `=`  | Disabled (default)   |
| `_`  | Enabled              |
| `p`  | Enabled with printk  |
| `f`  | Include function name|
| `l`  | Include line number  |
| `m`  | Include module name  |
| `t`  | Include thread ID    |

---

## Enabling and Disabling

### Query-Specification Pairs

The control interface uses `query-spec` pairs:

```
echo "<query> <flags>" > /sys/kernel/debug/dynamic_debug/control
```

### By Function

```bash
# Enable all pr_debug in a function
echo "func e1000_clean_rx_irq +p" > /sys/kernel/debug/dynamic_debug/control

# Disable
echo "func e1000_clean_rx_irq -p" > /sys/kernel/debug/dynamic_debug/control
```

### By File

```bash
# Enable all debug messages in a source file
echo "file drivers/net/ethernet/intel/e1000e/netdev.c +p" > /sys/kernel/debug/dynamic_debug/control

# Wildcards
echo "file drivers/net/e1000* +p" > /sys/kernel/debug/dynamic_debug/control
```

### By Module

```bash
# Enable all debug messages in a module
echo "module e1000e +p" > /sys/kernel/debug/dynamic_debug/control
```

### By Line Number

```bash
# Enable a specific line
echo "file net/ipv4/tcp_input.c line 4567 +p" > /sys/kernel/debug/dynamic_debug/control
```

### By Format String

```bash
# Enable messages containing a specific substring
echo "format \"checksum\" +p" > /sys/kernel/debug/dynamic_debug/control
```

### Combined Queries

```bash
# File + function
echo "file drivers/usb/core/usb.c func usb_submit_urb +p" > /sys/kernel/debug/dynamic_debug/control

# Module + format
echo "module iwlwifi format \"firmware\" +p" > /sys/kernel/debug/dynamic_debug/control
```

---

## Flag Modifiers

### Enable with Details

```bash
# Enable with function name and line number
echo "module e1000e +pflm" > /sys/kernel/debug/dynamic_debug/control
```

| Modifier | Effect                              |
|----------|-------------------------------------|
| `p`      | Enable the message (printk output)  |
| `f`      | Prepend function name               |
| `l`      | Prepend line number                 |
| `m`      | Prepend module name                 |
| `t`      | Prepend thread ID (TID)             |

### Disable All

```bash
echo "module e1000e -p" > /sys/kernel/debug/dynamic_debug/control
```

---

## Using dyndbg at Boot

### Boot Parameter

Enable debug for specific modules at boot time:

```bash
# In GRUB, add to kernel command line:
# e1000e.dyndbg=+p

# Or for multiple modules:
# dyndbg="module usbcore +p; module ehci_hcd +p"
```

### Module Parameter

Some modules support the `dyndbg` parameter:

```bash
# Load module with debug enabled
modprobe e1000e dyndbg=+p

# Or via module parameter
echo "+p" > /sys/module/e1000e/parameters/dyndbg
```

### Systemd Integration

```bash
# In /etc/modprobe.d/debug.conf
options e1000e dyndbg=+p

# Or as a systemd service
# /etc/systemd/system/debug-e1000e.service
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo "module e1000e +p" > /sys/kernel/debug/dynamic_debug/control'
```

---

## Code-Level Usage

### pr_debug()

```c
#include <linux/module.h>
#include <linux/printk.h>

static int my_function(int value)
{
    pr_debug("my_function called with value=%d\n", value);

    /* ... processing ... */

    pr_debug("my_function returning result=%d\n", result);
    return result;
}
```

### dev_dbg()

```c
#include <linux/device.h>

static int my_driver_probe(struct platform_device *pdev)
{
    dev_dbg(&pdev->dev, "probing device\n");
    dev_dbg(&pdev->dev, "resource count: %d\n", pdev->num_resources);
    /* ... */
}
```

### pr_debug vs. dev_dbg

| Macro       | Output Format                        |
|-------------|--------------------------------------|
| `pr_debug`  | `module: function: message`          |
| `dev_dbg`   | `device_name: message`               |
| `netdev_dbg`| `net_device: message`                |
| `pci_dbg`   | `pci_device: message`                |

### Conditional Debug

```c
/* Only enabled when DEBUG is defined at compile time */
#define DEBUG
pr_debug("This is always compiled in with DEBUG defined\n");

/* Or use dynamic_pr_debug explicitly */
if (dynamic_debug_enabled(descriptor))
    dynamic_pr_debug(&descriptor, "expensive format: %s\n",
                     expensive_to_string(obj));
```

---

## Query Syntax Reference

### Complete Query Grammar

```
query := <wildcard-spec> | <pair-query>
wildcard-spec := '*' | ''
pair-query := <pair-query> <pair>
pair := <keyword> '=' <value>
```

### Keywords

| Keyword  | Value             | Example                      |
|----------|-------------------|------------------------------|
| `func`   | Function name     | `func=my_func`               |
| `file`   | Source filename    | `file=drivers/usb/core.c`    |
| `module` | Module name       | `module=e1000e`              |
| `line`   | Line number range | `line=100-200` or `line=100` |
| `format` | Format substring  | `format="error"`             |

### Wildcard Examples

```bash
# All files matching a pattern
echo "file drivers/net/wireless/* +p" > /sys/kernel/debug/dynamic_debug/control

# All functions matching a pattern
echo "func usb_* +p" > /sys/kernel/debug/dynamic_debug/control

# Enable everything (use with caution!)
echo "+p" > /sys/kernel/debug/dynamic_debug/control

# Disable everything
echo "-p" > /sys/kernel/debug/dynamic_debug/control
```

---

## Practical Examples

### Debugging USB Issues

```bash
# Enable all USB core debugging
echo "module usbcore +p" > /sys/kernel/debug/dynamic_debug/control

# Just USB enumeration
echo "func usb_new_device +p" > /sys/kernel/debug/dynamic_debug/control

# Watch the output
dmesg -w | grep usb
```

### Debugging Network Drivers

```bash
# Enable Intel NIC debugging
echo "module e1000e +pflm" > /sys/kernel/debug/dynamic_debug/control

# Enable specific functions
echo "func e1000_xmit_frame +p" > /sys/kernel/debug/dynamic_debug/control
echo "func e1000_clean_rx_irq +p" > /sys/kernel/debug/dynamic_debug/control

# Watch with filtering
dmesg -w | grep -i e1000
```

### Debugging Filesystem Operations

```bash
# Enable ext4 debug
echo "module ext4 +p" > /sys/kernel/debug/dynamic_debug/control

# Just allocation paths
echo "func ext4_mb_new_blocks +p" > /sys/kernel/debug/dynamic_debug/control

# Just journal operations
echo "func jbd2_* +p" > /sys/kernel/debug/dynamic_debug/control
```

### Debugging Scheduler

```bash
# Enable scheduler debug (very verbose!)
echo "kernel/sched/core.c +p" > /sys/kernel/debug/dynamic_debug/control

# Just load balancing
echo "func load_balance +p" > /sys/kernel/debug/dynamic_debug/control
```

---

## Performance Impact

### Minimal When Disabled

When dynamic debug messages are disabled (the default), the overhead is minimal:
- One branch instruction per call site
- The `struct _ddebug` descriptor is in a separate ELF section (not in hot cache lines)

### Verbose When Enabled

When enabled, each message:
- Acquires the `logbuf_lock` (or ` printk_lock` in newer kernels)
- Formats the string
- Writes to the ring buffer
- May trigger console output

**Best practice:** Enable only the specific call sites you need.

---

## Scripting and Automation

### Bash Script: Temporary Debug Session

```bash
#!/bin/bash
# debug_session.sh — Enable debugging, wait, then disable

MODULE="$1"
DURATION="${2:-60}"

if [ -z "$MODULE" ]; then
    echo "Usage: $0 <module> [duration_seconds]"
    exit 1
fi

CONTROL="/sys/kernel/debug/dynamic_debug/control"

# Enable
echo "module $MODULE +p" > "$CONTROL"
echo "Enabled debug for module: $MODULE"

# Wait
echo "Collecting for $DURATION seconds..."
sleep "$DURATION"

# Disable
echo "module $MODULE -p" > "$CONTROL"
echo "Debug disabled."

# Save output
dmesg > "debug_${MODULE}_$(date +%Y%m%d_%H%M%S).log"
```

### Python: Programmatic Control

```python
#!/usr/bin/env python3
"""Control dynamic debug programmatically."""

CONTROL = "/sys/kernel/debug/dynamic_debug/control"

def dyndbg_enable(query: str):
    with open(CONTROL, 'w') as f:
        f.write(f"{query} +p\n")

def dyndbg_disable(query: str):
    with open(CONTROL, 'w') as f:
        f.write(f"{query} -p\n")

def dyndbg_list(query: str = "") -> str:
    """Read current state, optionally filtered."""
    with open(CONTROL, 'r') as f:
        lines = f.readlines()
    if query:
        keyword, value = query.split('=', 1)
        lines = [l for l in lines if value in l]
    return ''.join(lines)

# Example usage
dyndbg_enable("module e1000e")
# ... do something ...
dyndbg_disable("module e1000e")
```

---

## Troubleshooting

### Control File Not Found

```bash
# Ensure debugfs is mounted
mount -t debugfs none /sys/kernel/debug

# Ensure CONFIG_DYNAMIC_DEBUG is enabled
zcat /proc/config.gz | grep DYNAMIC_DEBUG
```

### No Output Appearing

1. Check that the module is loaded: `lsmod | grep <module>`
2. Verify messages are enabled: `cat /sys/kernel/debug/dynamic_debug/control | grep <query>`
3. Check `dmesg` log level: `dmesg -n 8`
4. Verify the function actually uses `pr_debug()` (not `printk()`)

### Too Much Output

```bash
# Be more specific with queries
echo "file drivers/usb/core/usb.c line 500 +p" > /sys/kernel/debug/dynamic_debug/control

# Or use rate limiting (in code)
pr_debug_ratelimited("message: %d\n", value);
```

---

## Advanced Techniques

### Combining with ftrace

Dynamic debug can be combined with ftrace for more detailed tracing:

```bash
# Enable dynamic debug messages via ftrace
# First, enable ftrace for print events
echo 1 > /sys/kernel/tracing/events/enable

# Then enable dynamic debug
module e1000e +p" > /sys/kernel/debug/dynamic_debug/control

# Use trace-cmd to capture with timing
sudo trace-cmd record -e print -p nop sleep 5
sudo trace-cmd report | head -50
```

### Filtering with grep and awk

```bash
# Enable debug and capture with timestamp filtering
echo "module iwlwifi +p" > /sys/kernel/debug/dynamic_debug/control

# Capture and filter by timestamp
dmesg -T | awk '/iwlwifi/ && /2024-01-15 10:3[0-9]/' > filtered.log

# Extract specific fields from dyndbg output
dmesg | grep 'e1000e' | awk '{print $1, $3, $5, $0}' | column -t

# Count debug messages per function
dmesg | grep -oP '\[.*?\] \K\S+' | sort | uniq -c | sort -rn | head
```

### Dynamic Debug in Containers

When debugging kernel modules from containers:

```bash
# Container needs CAP_SYS_ADMIN or debugfs mounted
# Mount debugfs in container
docker run --privileged -v /sys/kernel/debug:/sys/kernel/debug myimage

# Or more granularly
docker run --cap-add=SYS_ADMIN \
  -v /sys/kernel/debug/dynamic_debug/control:/sys/kernel/debug/dynamic_debug/control \
  myimage

# From container, enable debug
module e1000e +p" > /sys/kernel/debug/dynamic_debug/control
```

### Debug Workflow for Kernel Modules

A systematic approach to debugging kernel module issues:

```bash
#!/bin/bash
# workflow.sh - Systematic dynamic debug workflow

MODULE="$1"
ISSUE="$2"  # e.g., "probe", "init", "io"

CONTROL="/sys/kernel/debug/dynamic_debug/control"

if [ -z "$MODULE" ]; then
    echo "Usage: $0 <module> [issue]"
    exit 1
fi

echo "=== Step 1: Check if module is loaded ==="
lsmod | grep "$MODULE"

echo "=== Step 2: Enable all debug for module ==="
echo "module $MODULE +pflm" > "$CONTROL"

echo "=== Step 3: Reproduce the issue ==="
echo "Press Enter after reproducing..."
read -r

echo "=== Step 4: Collect debug output ==="
LOG="debug_${MODULE}_$(date +%Y%m%d_%H%M%S).log"
dmesg | grep -i "$MODULE" > "$LOG"
echo "Debug saved to: $LOG"

echo "=== Step 5: Disable debug ==="
echo "module $MODULE -p" > "$CONTROL"

echo "=== Step 6: Summary ==="
grep -c "." "$LOG"
echo "messages captured"
```

### Performance-Sensitive Debugging

When debugging performance-critical paths:

```bash
# Use pr_debug_ratelimited() in code to avoid flooding
# pr_debug_ratelimited("value: %d\n", val);

# Enable only specific lines to minimize overhead
echo "file drivers/net/e1000e/netdev.c line 1823 +p" > \
    /sys/kernel/debug/dynamic_debug/control

# Enable debug for a short window
module e1000e +p" > /sys/kernel/debug/dynamic_debug/control
sleep 0.5
echo "module e1000e -p" > /sys/kernel/debug/dynamic_debug/control

# Use perf to correlate with dynamic debug
perf record -g -e cycles -- sleep 1 &
module e1000e +p" > /sys/kernel/debug/dynamic_debug/control
sleep 1
echo "module e1000e -p" > /sys/kernel/debug/dynamic_debug/control
wait
perf report
```

### Dynamic Debug vs printk Levels

| Feature | Dynamic Debug (dyndbg) | printk Levels |
|---------|----------------------|---------------|
| Compile-time | Messages compiled in | Messages compiled in |
| Runtime control | Per-call-site | Per-message level |
| Overhead when disabled | One branch per site | None |
| Granularity | Function/file/module/line | Global level only |
| Production use | Excellent | Risky (too verbose) |
| Output destination | Same as printk | Same (kmsg, console) |

### Common dyndbg Patterns

```bash
# Pattern 1: Debug a specific driver during probe
echo "func my_driver_probe +pflm" > /sys/kernel/debug/dynamic_debug/control

# Pattern 2: Debug error paths only
echo "format \"error\" +p" > /sys/kernel/debug/dynamic_debug/control
echo "format \"fail\" +p" > /sys/kernel/debug/dynamic_debug/control

# Pattern 3: Debug initialization sequence
echo "file drivers/mydriver/core.c +p" > /sys/kernel/debug/dynamic_debug/control

# Pattern 4: Debug network path
echo "func tcp_rcv_established +p" > /sys/kernel/debug/dynamic_debug/control
echo "func tcp_sendmsg +p" > /sys/kernel/debug/dynamic_debug/control

# Pattern 5: Debug with timestamps for latency analysis
dmesg -T | grep my_func | awk '{print $1, $2, $NF}' | sort
```

## Further Reading

- [Linux kernel source: `lib/dynamic_debug.c`](https://elixir.bootlin.com/linux/latest/source/lib/dynamic_debug.c)
- [kernel.org: Dynamic Debug](https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html)
- [LWN: Dynamic debug](https://lwn.net/Articles/434832/)
- [Dynamic Debug HOWTO](https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html)
- [printk documentation](https://www.kernel.org/doc/html/latest/core-api/printk-basics.html)

> **Related topics:** [ftrace](./ftrace.md), Kernel Logging, printk Basics, Debugging Tools
