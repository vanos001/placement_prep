# debugfs - The Kernel's Ad-Hoc Debugging Filesystem

debugfs is the kernel's dumping ground: a virtual filesystem where driver
authors expose internal state with no formatting rules and no ABI promises.
The documentation [J1] is blunt: unlike /proc (process information) or sysfs
(strict one-value-per-file), "debugfs has no rules at all" -- so that
everyone who needs to peek at a register or flip a driver flag does not
invent a private sysfs file that user space would depend on forever.

## Design constraints

- In-memory only: `debugfs_fill_super()` builds the tree with libfs's
  `simple_fill_super(sb, DEBUGFS_MAGIC, ...)` [S1]. Content is regenerated
  by kernel code on every read; nothing survives unmount or reboot.
- No stability contract: files there are explicitly "not a stable ABI" [J1],
  though the doc concedes interfaces should be designed "with the idea that
  they will need to be maintained forever" -- tooling grows dependencies.
- Debug-only: the Kconfig help ends with "If unsure, say N" [J6].
  `DEBUG_FS_ALLOW_NONE` can disable the facility at build time; the
  `debugfs=[on,off]` boot parameter overrides it at runtime.
- GPL-only: "the debugfs API is exported GPL-only to modules" [J1].
- Root-only by default: the debugfs root is accessible only to root [J1];
  `uid=`, `gid=`, `mode=` mount options can relax that (rarely wise).
- Tracing outgrew it: since kernel 4.1, ftrace's control files live in
  tracefs at `/sys/kernel/tracing`; mounting debugfs auto-mounts tracefs at
  `/sys/kernel/debug/tracing` for backward compatibility [J4]. One tree,
  two contracts -- tracefs is de-facto stable (perf, bcc, trace-cmd depend
  on it), the rest of debugfs stays explicitly unstable.

## The creation API

Include `<linux/debugfs.h>`. Every creator returns a `struct dentry *` for
cleanup, or an `ERR_PTR(-ERROR)`; `ERR_PTR(-ENODEV)` means the kernel lacks
debugfs and all functions are inert [J1]. `parent == NULL` places a node at
the debugfs root; Corbet's LWN tour [J2] is the friendliest overview.

```c
struct dentry *debugfs_create_dir(const char *name, struct dentry *parent);
struct dentry *debugfs_create_file(const char *name, umode_t mode,
        struct dentry *parent, void *data,
        const struct file_operations *fops);
```

`debugfs_create_file()` stores `data` in the inode's `i_private` field, so
one shared `file_operations` set can serve many files; handlers recover
context via `inode->i_private`. Only `read` and/or `write` are required
[J1]. Typed helpers skip `file_operations` entirely [J1]:

| Factory                        | Read format   | Write behavior                                        |
|--------------------------------|---------------|-------------------------------------------------------|
| debugfs_create_u8/u16/u32/u64  | decimal       | decimal, bound-checked                                |
| debugfs_create_x8/x16/x32/x64  | hexadecimal   | hexadecimal                                           |
| debugfs_create_bool            | `Y`/`N` line  | accepts y/n/1/0 case-insensitively; other input silently ignored |
| debugfs_create_atomic_t        | decimal       | sets the atomic_t                                     |
| debugfs_create_blob            | raw bytes     | none -- blob files are read-only by definition        |

Writability is a mode-bits decision: `0444` makes the kernel reject writes;
`0644` turns the file into a two-way variable. Files whose output exceeds
one page use the seq_file interface [J3]: set `.read = seq_read` and
implement a `.show` callback (`debugfs_create_devm_seqfile()` is the
device-managed wrapper). For hardware bring-up, `debugfs_create_regset32()`
takes a `debugfs_regset32` -- an array of `debugfs_reg32` name/offset
entries plus a `void __iomem *base` -- and prints offset, value, and name
per register [J1]: the canonical "read hardware state from user space"
workflow with no custom code beyond the register table.

## Kernel-module sketch

```c
#include <linux/debugfs.h>
#include <linux/module.h>

static u32 counter;
static bool enabled;

static int stats_show(struct seq_file *s, void *ignored)
{
        seq_printf(s, "counter=%u enabled=%s\n",
                   counter, enabled ? "Y" : "N");
        return 0;
}
DEFINE_SHOW_ATTRIBUTE(stats);       /* builds stats_fops from stats_show */

static int __init froboz_init(void)
{
        struct dentry *dir = debugfs_create_dir("froboz", NULL);
        debugfs_create_u32("counter", 0644, dir, &counter);
        debugfs_create_bool("enabled", 0644, dir, &enabled);
        debugfs_create_file("stats", 0444, dir, NULL, &stats_fops);
        return 0;
}
module_init(froboz_init);
```

With `DEBUG_FS_ALLOW_NONE`, creators can fail at runtime, so guard with
`IS_ERR_OR_NULL()` before populating children; `debugfs_remove_recursive()`
tears the tree down on module exit.

## Who populates /sys/kernel/debug

Verified against mainline sources; the tree is a cross-subsystem museum:

| Path                 | Created by             | Contents                                        |
|----------------------|------------------------|-------------------------------------------------|
| `gpio`               | gpiolib [S3]           | line per GPIO: number, direction, state         |
| `clk/clk_summary`    | clock framework        | rate/enable tree; per-clock `clk_rate` writable where hardware allows |
| `regulator/`         | regulator core         | `supply_map`, per-regulator state, `constraint_flags` |
| `iommu/`             | iommu core [S6]        | root for vendor register-dump subdirectories    |
| `dmaengine/`         | dmaengine core         | per-device/channel directories                  |
| `tracing/`           | tracefs automount [J4] | ftrace control files ([ftrace internals](../tracing/ftrace-internals.md)) |

Subtree deep dives live elsewhere in this repo: [clock framework](../drivers/clk.md),
[IOMMU](../drivers/iommu.md), [pinctrl debugfs](../drivers/pinctrl.md),
[PHY tuning](../drivers/phy.md), [sysfs comparison](../../observability/sysfs.md),
[perf tracepoints](perf-events.md), [sanitizers](sanitizers.md), and
[KUnit output](kunit.md). Correction to common lore: PM QoS is often listed
as a debugfs consumer, but mainline `kernel/power/qos.c` registers misc
devices (`/dev/cpu_dma_latency`) and creates no debugfs tree [S11].

## Error injection through debugfs

The fault-injection framework uses debugfs as its control panel [J5]. The
boot-time facilities `failslab`, `fail_page_alloc`, and `fail_make_request`
are tuned at runtime under `/sys/kernel/debug/fail*/`: `probability`
(percent chance per eligible call), `interval` (fail every Nth call; pair
with `probability=100`), `times`/`space` caps, and `task-filter`, which
restricts injection to processes with `make-it-fail`. `fail_function` goes
further: functions marked `ALLOW_ERROR_INJECTION()` return a chosen error
code on demand from `/sys/kernel/debug/fail_function/`; device variants
follow the same pattern (`nvme*/fault_inject`, `mmc0/fail_mmc_request`)
[J5]. This is how "impossible" driver paths get exercised -- and why a
toggle left on produces baffling one-in-a-hundred failures.

## Security posture

- Root-only by default [J1] is weaker than it sounds: a root compromise
  reads kernel pointers, register contents, and firmware dumps from debugfs,
  defeating KASLR for later stages. Mode choice matters too: `0444` for
  informational files, `0644` only for values meant to be changed, never
  world-writable knobs.
- The IOMMU case is instructive: enabling its debugfs makes the kernel print
  a boot banner that exposing internal structures "may compromise security
  on your system" [S6].
- Hardened kernels answer with `debugfs=off` or `DEBUG_FS_ALLOW_NONE` [J6];
  many production distro and Android kernels restrict debugfs to a 0700
  root-only mount or compile it out. Unmounting hides the tree but does not
  unregister debug hooks; remount `uid/gid/mode` options apply tree-wide
  [S1].

## Interface comparison

| Property        | debugfs           | sysfs                  | procfs            | tracefs             |
|-----------------|-------------------|------------------------|-------------------|---------------------|
| Contract        | none, unstable    | stable, one value/file | per-file legacy   | de-facto stable tooling interface |
| Backing         | libfs, in-memory  | kobjects               | assorted          | ring buffers        |
| Typical mount   | /sys/kernel/debug | /sys                   | /proc             | /sys/kernel/tracing |

## The interface, modeled

The stdlib-only, deterministic Python model below mirrors the mechanics:
typed node factories, `file_operations` dispatch, and the classic mistakes
-- writing a read-only node, feeding junk to a u64.

```python
# MODEL: a miniature debugfs -- in-memory tree, typed node factories,
# file_operations-style dispatch. Kernel habits: mode bits gate writes.
import errno

class DebugfsError(OSError): pass

class Node:
    def __init__(self, name, mode=0o444, children=None):
        self.name, self.mode = name, mode
        self.children = children or {}      # dirs only

class U64(Node):                    # debugfs_create_u64(): decimal in/out
    def __init__(self, name, mode, value=0):
        super().__init__(name, mode); self.value = value
    def read(self): return "%d\n" % self.value
    def write(self, data):
        try: v = int(data.strip())
        except ValueError: raise DebugfsError(errno.EINVAL, "bad u64 input")
        self.value = v % (1 << 64)

class Bool(Node):                   # debugfs_create_bool(): Y/N out
    def __init__(self, name, mode, value=False):
        super().__init__(name, mode); self.value = bool(value)
    def read(self): return "Y\n" if self.value else "N\n"
    def write(self, data):          # y/n/1/0 in; junk silently ignored
        s = data.strip().lower()
        self.value = {"y": True, "1": True, "n": False,
                      "0": False}.get(s, self.value)

class Blob(Node):                   # debugfs_create_blob(): read-only
    def __init__(self, name, data):
        super().__init__(name, 0o444); self.data = data
    def read(self): return self.data.decode("ascii")
    def write(self, data):
        raise DebugfsError(errno.EACCES, "write on read-only blob")

class SeqFile(Node):                # seq_file-backed: unbounded .show
    def __init__(self, name, show):
        super().__init__(name, 0o444); self.show = show
    def read(self): return "".join(self.show())
    def write(self, data):
        raise DebugfsError(errno.EINVAL, "no .write op registered")

def dispatch(node, op, data=None):  # file_operations dispatch
    if op == "read":
        return node.read()
    if not node.mode & 0o222:       # kernel gates write on the w-bits
        raise DebugfsError(errno.EACCES, "mode 0%o denies write" % node.mode)
    node.write(data)

def dump_tree(node, depth=0):
    out = [] if depth else [node.name]
    for name in sorted(node.children):
        child, pad = node.children[name], "  " * depth
        if child.children:                          # a directory
            out.append("%s%s/" % (pad, name))
            out.extend(dump_tree(child, depth + 1))
            continue
        desc = type(child).__name__
        if isinstance(child, U64): desc += " value=%d" % child.value
        if isinstance(child, Bool):
            desc += " value=%s" % ("Y" if child.value else "N")
        out.append("%s%s  %s 0%03o" % (pad, name, desc, child.mode))
    return out

root = Node("/sys/kernel/debug", 0o755, {})
froboz = Node("froboz", 0o755); root.children["froboz"] = froboz
counter = U64("counter", 0o644, 42); froboz.children["counter"] = counter
enabled = Bool("enabled", 0o644, True); froboz.children["enabled"] = enabled
froboz.children["fw_version"] = Blob("fw_version", b"Froboz FW 3.11\n")
froboz.children["stats"] = SeqFile("stats", lambda: [
    "packets=%d\n" % counter.value,
    "enabled=%s\n" % enabled.read().strip()])

for line in dump_tree(root):
    print(line)
print("--- interaction transcript ---")
print("$ cat counter      -> %s" % dispatch(counter, "read"), end="")
dispatch(counter, "write", "100")
print("$ echo 100 >counter-> %s" % dispatch(counter, "read"), end="")
print("$ cat stats        -> %s" % dispatch(froboz.children["stats"],
                                            "read"), end="")
dispatch(enabled, "write", "maybe")     # junk: silently ignored
print("$ echo maybe >enabled  value stays %s" % enabled.read().strip())
for node, data in ((froboz.children["fw_version"], "hack"), (counter, "oops")):
    try:
        dispatch(node, "write", data)
    except DebugfsError as e:
        print("$ echo %s >%-9s -> %s: %s" % (data, node.name,
                                             errno.errorcode[e.errno], e))
```

Running it prints the tree and a transcript, including both failure modes:

```text
/sys/kernel/debug
froboz/
  counter  U64 value=42 0644
  enabled  Bool value=Y 0644
  fw_version  Blob 0444
  stats  SeqFile 0444
--- interaction transcript ---
$ cat counter      -> 42
$ echo 100 >counter-> 100
$ cat stats        -> packets=100
enabled=Y
$ echo maybe >enabled  value stays Y
$ echo hack >fw_version -> EACCES: [Errno 13] mode 0444 denies write
$ echo oops >counter   -> EINVAL: [Errno 22] bad u64 input
```

EACCES models `debugfs_create_blob()`'s read-only rule; EINVAL is what a
kernel `.write` handler returns for bad input; the silent no-op on
`echo maybe >enabled` reproduces the documented bool semantics [J1].

## References

- [J1] DebugFS, kernel documentation -- <https://docs.kernel.org/filesystems/debugfs.html>
- [J2] J. Corbet, "An updated guide to debugfs," LWN -- <https://lwn.net/Articles/334546/>
- [J3] The seq_file interface, kernel documentation -- <https://docs.kernel.org/filesystems/seq_file.html>
- [J4] ftrace documentation (tracefs automount) -- <https://docs.kernel.org/trace/ftrace.html>
- [J5] Fault injection, kernel documentation -- <https://docs.kernel.org/fault-injection/fault-injection.html>
- [J6] lib/Kconfig.debug, DEBUG_FS options -- <https://raw.githubusercontent.com/torvalds/linux/master/lib/Kconfig.debug>
- [S1] fs/debugfs/inode.c -- <https://raw.githubusercontent.com/torvalds/linux/master/fs/debugfs/inode.c>
- [S3] drivers/gpio/gpiolib.c -- <https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpio/gpiolib.c>
- [S6] drivers/iommu/iommu-debugfs.c -- <https://raw.githubusercontent.com/torvalds/linux/master/drivers/iommu/iommu-debugfs.c>
- [S11] kernel/power/qos.c -- <https://raw.githubusercontent.com/torvalds/linux/master/kernel/power/qos.c>
